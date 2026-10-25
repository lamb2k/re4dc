from pathlib import Path
import subprocess
import tempfile
import unittest
from test_runtime_hooks import function

HERE = Path(__file__).resolve().parent
GAME = HERE.parents[2] / 'game'


class RuntimeAudioTests(unittest.TestCase):
    def test_actual_stream_entry_capture_and_bounds(self):
        # gc-catalog24b (coordinator 10-24 option a): one identity per AIS1 entry,
        # hashed at its first open: record + intro groups + loop groups.
        source = (GAME / 'platform/audio_aica.cpp').read_text()
        start = source.index('re4dc_gcasset::Digest g_strEntDigest[kStrEntMax];')
        entry = source[start:source.index('#endif\nbool str_index_load()', start)]
        fixture = r'''
#include "gc_asset_audio.h"
#include <cassert>
#include <cstdio>
#include <cstring>
#include <vector>
#include <sys/types.h>
using u8=unsigned char;using u32=unsigned;using file_t=int;file_t g_strFile=1;u32 g_strCacheOfs;
struct StrEnt { u32 sbb_ofs, rate, flags, nch, a_samples, b_samples, a_ofs, b_ofs; };
const int kStrEntMax=4;StrEnt g_strEnt[kStrEntMax];
unsigned reads,success,failures;unsigned offset;
unsigned char file_bytes[65536];re4dc_gcasset::Digest received;
off_t fs_seek(file_t,off_t target,int whence){assert(whence==SEEK_SET);if(target>65536)return -1;offset=unsigned(target);return offset;}
ssize_t fs_read(file_t,void* out,unsigned bytes){++reads;if(offset+bytes>65536)return 0;memcpy(out,file_bytes+offset,bytes);offset+=bytes;return bytes;}
extern "C" void re4dc_log(const char*,...){}
namespace re4dc_gcasset{void stream_source(const Digest& d){++success;received=d;}void stream_source_failed(){++failures;}}
''' + entry + r'''
int main(){for(unsigned i=0;i<sizeof file_bytes;++i)file_bytes[i]=u8(i%251);
 g_strEnt[0]={0x10,32000,1,2,4096,8192,4096,12288};   // intro 1 group, loop 2 groups of 4096 B
 std::vector<u8> want((const u8*)&g_strEnt[0],(const u8*)&g_strEnt[0]+32);
 want.insert(want.end(),file_bytes+4096,file_bytes+8192);want.insert(want.end(),file_bytes+12288,file_bytes+20480);
 gcasset_stream_entry(&g_strEnt[0]);
 assert(success==1 && !failures && !memcmp(received.bytes,re4dc_gcasset::fingerprint(want.data(),unsigned(want.size())).bytes,32));
 const unsigned r=reads;gcasset_stream_entry(&g_strEnt[0]);assert(success==2 && reads==r);   // hashed once
 g_strEnt[1]={0x20,32000,0,1,4096,0,70000,0};gcasset_stream_entry(&g_strEnt[1]);assert(failures==1 && success==2);
 gcasset_stream_entry(&g_strEnt[1]);assert(failures==2 && reads==r);   // a failed entry is not re-read
 std::printf("stream entry identity ok\n");
}
'''
        with tempfile.TemporaryDirectory(prefix='gc-port23-stream-entry-', dir='/dev/shm') as temporary:
            root = Path(temporary);(root / 'fixture.cpp').write_text(fixture);executable = root / 'fixture'
            subprocess.run(['g++', '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror',
                            '-DRE4DC_GC_ASSET_GATE=1', '-I', str(GAME / 'platform/include'),
                            str(root / 'fixture.cpp'), str(GAME / 'platform/gc_asset_gate.cpp'), '-o', str(executable)], check=True)
            subprocess.run(['/lib64/ld-linux-x86-64.so.2', str(executable)], check=True)

    def test_actual_stream_ready_start_and_channel_rejection(self):
        source = (GAME / 'platform/audio_aica.cpp').read_text()
        start = function(source, 'if (s.state == kStrReady && s.want) {')
        fixture = r'''
#include "gc_asset_audio.h"
#include <cassert>
using u32=unsigned;using u64=unsigned long long;using u16=unsigned short;
constexpr unsigned kStrReady=2,kStrPlaying=3,kStrChBytes=24576,kStrHalfSamples=24576,g_strRing=4096,g_nowMs=1;
struct RegWriter{};struct Ent{unsigned rate;};struct Mix{unsigned pan;};struct V{struct VS{Mix mix;}vs;};
struct Stream{unsigned state,want,asset_generation;unsigned char nch;int ch[2];Ent* e;V* v[2];u64 rate_q10,t0;u16 sent_tl[2];unsigned play_cont[2];};
struct Stats{unsigned str_starts;}S;
unsigned phase,starts,allocations;bool reject;
int chn_alloc(){return reject && ++allocations==2?-1:3;}void str_keyoff(RegWriter&){assert(!phase);}
u16 aica_freq_reg(unsigned){return 0;}u16 dipan(unsigned){return 0;}u16 str_tl(unsigned){return 0;}
u64 timer_us_gettime64(){return 42;}
void re4dc_log(const char*,...){assert(phase==2);}
template<class... Args>void ch_start(Args&&...){assert(phase==1);++starts;}
namespace re4dc_gcasset {
AudioUse stream_ticket(unsigned generation){assert(!phase && generation==77);phase=1;return {};}
void played(const AudioUse&){assert(phase==1 && starts);phase=2;}
}
void flush(Stream& s){RegWriter w;unsigned key=0;
''' + start + r'''
}
int main(){Ent e{32000};V voice{};Stream s{};s.state=kStrReady;s.want=1;s.nch=2;s.asset_generation=77;s.ch[0]=s.ch[1]=-1;s.e=&e;s.v[0]=s.v[1]=&voice;
flush(s);assert(phase==2 && starts==2 && s.state==kStrPlaying && S.str_starts==1);
phase=starts=0;s.state=1;flush(s);assert(!phase && !starts); // prefill-ready is not playback
s.state=kStrReady;s.want=0;flush(s);assert(!phase && !starts);
s.want=1;s.ch[0]=s.ch[1]=-1;reject=true;flush(s);assert(!phase && !starts && s.state==kStrReady); // no accepted channel pair
}
'''
        with tempfile.TemporaryDirectory(prefix='gc-port23-stream-', dir='/dev/shm') as temporary:
            root = Path(temporary);(root / 'fixture.cpp').write_text(fixture);executable = root / 'fixture'
            subprocess.run(['g++', '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror',
                            '-DRE4DC_GC_ASSET_GATE=1', '-I', str(GAME / 'platform/include'),
                            str(root / 'fixture.cpp'), '-o', str(executable)], check=True)
            subprocess.run(['/lib64/ld-linux-x86-64.so.2', str(executable)], check=True)

    def test_actual_dvd_success_error_and_completion_fragments(self):
        source = (GAME.parents[2] / 'src/game/dvd.cpp').read_text()
        body = function(source, 'void cDvdQueue::readMain()')
        start = body.index('    case 2:\n        if (chk(0x02000000))')
        finish = body.index('            switch ((*ph)->type)', start)
        fragment = body[start:finish] + '\n        }\n        break;\n'
        fixture = r'''
#include "gc_asset_audio.h"
#include <cassert>
#include <cstdio>
#include <cstdarg>
#include <cstring>
#include <string>
using namespace re4dc_gcasset;
std::string logs;unsigned char DVD_BUFF[128];unsigned copied;
extern "C" void re4dc_log(const char* fmt,...){char text[256];va_list ap;va_start(ap,fmt);vsnprintf(text,sizeof text,fmt,ap);va_end(ap);logs+=text;}
void OSReport(const char*){}
using u32=unsigned;
struct DvdHeader{unsigned type,size;};
struct Queue {
    DvdHeader header{};unsigned step=2,flags=0,m_Rno0=1,m_be_flag=0,m_LeftSize=0,m_DivReadSize=0,m_TransAddr=0,m_Offset=0;
    bool chk(unsigned bit){return flags&bit;}
    void transfer(void*,u32,u32 bytes){copied+=bytes;memset(DVD_BUFF,0xcc,sizeof DVD_BUFF);}
    void begin(unsigned part,unsigned bytes){header={part,bytes};m_LeftSize=bytes;step=2;m_Offset=m_TransAddr=0;
        RE4DC_GCA_BANK_BEGIN(this,0,part,header.size);}
    void advance(){DvdHeader* head=&header;DvdHeader** ph=&head;
        void(Queue::*trans_proc_tbl[])(void*,u32,u32)={&Queue::transfer,&Queue::transfer,&Queue::transfer,&Queue::transfer};
        switch(step){
''' + fragment + r'''
        }
    }
};
std::string hex(const Digest& digest){std::string result;char byte[3];for(unsigned i=0;i<32;++i){snprintf(byte,sizeof byte,"%02x",digest.bytes[i]);result+=byte;}return result;}
int main(){assert(install(nullptr,0));Queue q;q.begin(1,64);q.m_DivReadSize=32;
    memset(DVD_BUFF,1,sizeof DVD_BUFF);q.flags=0x02000000;q.advance();assert(!copied && q.step==2);
    q.flags=0x200000;q.advance();assert(!copied && q.step==1); // original retry, no diagnostic piece accepted
    q.flags=0;q.step=2;q.advance();assert(copied==32 && q.step==3);
    q.flags=0x01000000;q.advance();assert(q.m_LeftSize==64); // DMA/ARQ completion still pending
    q.flags=0;q.advance();assert(q.m_LeftSize==32);memset(DVD_BUFF,1,sizeof DVD_BUFF);q.step=2;q.advance();q.advance();assert(!q.m_LeftSize);
    unsigned char expected_mram[64];memset(expected_mram,1,sizeof expected_mram);
    unsigned char expected_aram[128]{};unsigned magic=0x31434941,total=32;memcpy(expected_aram,&magic,4);memcpy(expected_aram+8,&total,4);expected_aram[96]=3;
    q.begin(2,256);q.m_DivReadSize=128;memcpy(DVD_BUFF,expected_aram,128);q.advance();q.advance();
    // The original transfer filled DVD_BUFF with stale bytes. Padding-only
    // callbacks must not read those bytes, just as SND_PAD_SKIP behaves.
    q.step=2;q.advance();q.advance();assert(!q.m_LeftSize);assert(copied==320);
    bank_pump();begin(0x111,1,Required);const auto use=bank_ticket(0,bank_generation(0));played(use);pump();end(1);
    assert(logs.find("sha256="+hex(fingerprint(expected_mram,64)))!=std::string::npos);
    assert(logs.find("sha256="+hex(fingerprint(expected_aram,128)))!=std::string::npos);
    assert(logs.find("errors=0")!=std::string::npos);
}
'''
        with tempfile.TemporaryDirectory(prefix='gc-port23-dvd-', dir='/dev/shm') as temporary:
            root = Path(temporary);(root / 'fixture.cpp').write_text(fixture);executable = root / 'fixture'
            subprocess.run(['g++', '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror',
                            '-DRE4DC_GC_ASSET_GATE=1', '-I', str(GAME / 'platform/include'),
                            str(root / 'fixture.cpp'), str(GAME / 'platform/gc_asset_audio.cpp'),
                            str(GAME / 'platform/gc_asset_gate.cpp'), '-o', str(executable)], check=True)
            subprocess.run(['/lib64/ld-linux-x86-64.so.2', str(executable)], check=True)

    def test_actual_ax_and_syn_accepted_keyon_blocks(self):
        source = (GAME / 'platform/audio_aica.cpp').read_text()
        ax = function(source, 'if (v.dirty & 1) {')
        syn = function(source, 'if ((n.dirty & 1) && s) {')
        fixture = r'''
#include "gc_asset_audio.h"
#include <cassert>
using u32=unsigned;using u16=unsigned short;
unsigned phase,starts;
struct RegWriter{};
struct Block{unsigned asset_generation;};Block g_blk[14];
struct Voice{unsigned dirty;int blk,ch;u32 aica,len,loop,loop_start,play_cont;u16 sent_tl,sent_pan,sent_freq;};
struct Channel{unsigned pan;};struct Synth{int blk;unsigned gen;Channel ch[16];};
struct Note{unsigned dirty,ch,aica,len,loop,lsa,play_cont,ch_midi,ar,d1r,dl,rr,seen_gen,released;u16 sent_tl,sent_freq;};
int synth_block(const Synth*){return -1;}u16 note_tl(const Note&,const Synth*){return 0;}u16 note_freq(const Note&,const Synth*){return 0;}u16 dipan(unsigned x){return x;}
template<class... Args>void ch_start(Args&&...){assert(phase==1);phase=2;++starts;}
namespace re4dc_gcasset {
AudioUse bank_ticket(unsigned bank,unsigned generation){assert(phase==0);assert(bank==2 && generation==77);phase=1;return {};}
void played(const AudioUse&){assert(phase==2);phase=3;}
}
void ax(Voice& v){RegWriter w;u16 tl=0,pan=0,freq=0;
''' + ax + r'''
}
void syn(Note& n,Synth* s){RegWriter w;
''' + syn + r'''
}
int main(){g_blk[2].asset_generation=77;Voice v{};v.dirty=1;v.blk=2;ax(v);assert(phase==3 && starts==1);
phase=0;v.dirty=2;ax(v);assert(!phase && starts==1); // ready/mix update is not a new key-on
Synth s{};s.blk=2;Note n{};n.dirty=1;syn(n,&s);assert(phase==3 && starts==2);
phase=0;n.dirty=0;syn(n,&s);assert(!phase && starts==2);
}
'''
        with tempfile.TemporaryDirectory(prefix='gc-port23-keyon-', dir='/dev/shm') as temporary:
            root = Path(temporary);(root / 'fixture.cpp').write_text(fixture);executable = root / 'fixture'
            subprocess.run(['g++', '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror',
                            '-DRE4DC_GC_ASSET_GATE=1', '-I', str(GAME / 'platform/include'),
                            str(root / 'fixture.cpp'), '-o', str(executable)], check=True)
            subprocess.run(['/lib64/ld-linux-x86-64.so.2', str(executable)], check=True)

    def test_bounded_source_parts_and_accepted_queue(self):
        with tempfile.TemporaryDirectory(prefix='gc-port23-audio-', dir='/dev/shm') as temporary:
            executable = Path(temporary) / 'fixture'
            subprocess.run(['g++', '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror',
                            '-DRE4DC_GC_ASSET_GATE=1', '-DRE4DC_GC_ASSET_TEST=1', '-I', str(GAME / 'platform/include'),
                            str(HERE / 'test_audio.cpp'), str(GAME / 'platform/gc_asset_audio.cpp'),
                            str(GAME / 'platform/gc_asset_gate.cpp'), '-o', str(executable)], check=True)
            subprocess.run(['/lib64/ld-linux-x86-64.so.2', str(executable)], check=True)


if __name__ == '__main__':unittest.main()
