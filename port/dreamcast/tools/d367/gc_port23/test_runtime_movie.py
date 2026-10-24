"""Actual movie upload-owner API and accepted packet observer, RAM only."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from test_runtime_hooks import function

HERE = Path(__file__).resolve().parent
GAME = HERE.parents[2] / 'game'


class RuntimeMovieTests(unittest.TestCase):
    def test_actual_stream_command_observer_and_queue(self):
        source = (GAME / 'platform/native_movie_stream.c').read_text()
        observer = source[source.index('// GC_ASSET_MOVIE_STREAM_BEGIN'):source.index('// GC_ASSET_MOVIE_STREAM_END')]
        fixture = r'''
#include "gc_asset_movie_stream.h"
#include "gc_asset_gate.h"
#include <cassert>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <string>
using namespace re4dc_gcasset;
std::string logs;bool g2;
extern "C" void re4dc_log(const char*fmt,...){assert(!g2);char text[256];va_list ap;va_start(ap,fmt);vsnprintf(text,sizeof text,fmt,ap);va_end(ap);logs+=text;}
constexpr int SND_STREAM_MAX=4;constexpr unsigned AICA_RAM_START=4096,AICA_RAM_END=2*1024*1024,AICA_CMDSTR_CHANNEL_SIZE=96,AICA_CMD_CHAN=1,AICA_CH_CMD_START=1,AICA_CH_START_DELAY=2,AICA_CH_START_SYNC=4,AICA_SM_16BIT=0;
using snd_stream_hnd_t=int;using snd_stream_callback_t=void*(*)(int,int,int*);
struct aica_channel_t{unsigned cmd,base,type,length,loop,loopstart,loopend,freq;};
struct aica_cmd_t{unsigned size,cmd,timestamp,cmd_id;aica_channel_t cmd_data[1];};
struct strchan_t{int initted;unsigned channels,type,bitsize,frequency,buffer_size;int ch[2];unsigned spu_ram_sch[2];snd_stream_callback_t get_data;void*req_data;unsigned queueing;void*filters;};
strchan_t streams[4];unsigned max_channels=2,submitted,reject_at;
#define TAILQ_FIRST(x) (*(x))
int snd_sh4_to_aica(void*,unsigned){assert(!g2);g2=true;++submitted;g2=false;return submitted==reject_at?-1:0;}
#if RE4DC_CABIN_SOURCE
int cabin_stream_command(void*p,unsigned n){return snd_sh4_to_aica(p,n);}
#endif
''' + observer + r'''
void* callback(int,int,int*){return nullptr;}
void commands(unsigned stop=3,bool corrupt=false){
 aica_cmd_t command{};command.size=AICA_CMDSTR_CHANNEL_SIZE;command.cmd=AICA_CMD_CHAN;
 auto& c=command.cmd_data[0];c.cmd=AICA_CH_CMD_START|AICA_CH_START_DELAY;c.type=AICA_SM_16BIT;c.length=16384;c.loop=1;c.loopend=16384;c.freq=32000;
 for(unsigned i=0;i<stop;++i){command.cmd_id=i<2?unsigned(streams[0].ch[i]):((1u<<streams[0].ch[0])|(1u<<streams[0].ch[1]));
  c.base=i<2?streams[0].spu_ram_sch[i]:0;if(i==2)c.cmd=AICA_CH_CMD_START|AICA_CH_START_SYNC;
  if(corrupt && i==0)++c.base;
  gcasset_movie_command(&command,AICA_CMDSTR_CHANNEL_SIZE);
 }
}
unsigned rows(){unsigned count=0;std::size_t at=0;while((at=logs.find("GC-ASSET v=",at))!=std::string::npos){++at;++count;}return count;}
void start(){submitted=0;gcasset_movie_start_begin(0,32000,1);}
int main(){auto&s=streams[0];s.initted=1;s.channels=2;s.bitsize=16;s.frequency=32000;s.buffer_size=32768;s.ch[0]=3;s.ch[1]=4;s.spu_ram_sch[0]=4096;s.spu_ram_sch[1]=4096+32768;s.get_data=callback;
 unsigned char bytes[]={1,2,3};CatalogRow row{"movie","00001",fingerprint(bytes,3),Unknown};assert(install(&row,1));auto token=bind_checked("movie","00001",row.digest);
 begin(0x111,1,Required);re4dc_gcasset_movie_stream_arm(0,77,token.value);start();commands();gcasset_movie_start_end();assert(!rows());pump();end(1);
 assert(rows()==1 && logs.find("consumer=movie")!=std::string::npos && logs.find("errors=0")!=std::string::npos);
 // Failed API start emits no command, takes no ticket and produces no use.
 logs.clear();begin(0x111,2,Required);start();gcasset_movie_start_end();end(2);assert(!rows() && logs.find("errors=0")!=std::string::npos);
 // Every partial/rejected/malformed actual command sequence is terminal failure.
 for(unsigned mode=0;mode<5;++mode){logs.clear();begin(0x111,3+mode,Required);re4dc_gcasset_movie_stream_arm(0,77,token.value);start();
  if(mode==0)reject_at=2;
  if(mode==1)re4dc_gcasset_movie_stream_cancel(0);
  if(mode==2)re4dc_gcasset_movie_stream_arm(0,78,token.value); // source replacement during prefill
  commands(mode==3?2:3,mode==4);gcasset_movie_start_end();pump();end(3);
  assert(!rows() && logs.find("errors=0")==std::string::npos);reject_at=0;
 }
 // Retired catalog token cannot be resurrected by an accepted command sequence.
 retire_catalog();assert(install(&row,1));logs.clear();begin(0x111,9,Required);re4dc_gcasset_movie_stream_arm(0,79,token.value);start();commands();gcasset_movie_start_end();pump();end(4);assert(!rows());
 // Closing room admission between ticket and completion cannot relabel this use.
 token=bind_checked("movie","00001",row.digest);logs.clear();begin(0x111,10,Required);re4dc_gcasset_movie_stream_arm(0,80,token.value);start();commands(1);end(5);
 begin(0x113,11,Required);gcasset_movie_start_end();pump();end(6);assert(!rows());
}
'''
        with tempfile.TemporaryDirectory(prefix='gc-port23-movie-audio-', dir='/dev/shm') as temporary:
            root = Path(temporary);(root / 'fixture.cpp').write_text(fixture);executable = root / 'fixture'
            for cabin in (0, 1):
                subprocess.run(['g++', '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror',
                                '-DRE4DC_GC_ASSET_GATE=1', f'-DRE4DC_CABIN_SOURCE={cabin}',
                                '-I', str(GAME / 'platform/include'), str(root / 'fixture.cpp'),
                                str(GAME / 'platform/gc_asset_gate.cpp'), str(GAME / 'platform/gc_asset_audio.cpp'), '-o', str(executable)], check=True)
                subprocess.run(['/lib64/ld-linux-x86-64.so.2', str(executable)], check=True)

    def test_actual_full_container_capture_and_read_rejection(self):
        source = (GAME / 'platform/native_movie.cpp').read_text()
        start = source.index('    // One extra immutable container read')
        capture = source[start:source.index('#endif', start)]
        fixture = r'''
#include "gc_asset_gate.h"
#include <cassert>
#include <cstdio>
#include <cstring>
#include <sys/types.h>
using namespace re4dc_gcasset;using file_t=int;constexpr int O_RDONLY=0;
unsigned char file_bytes[1536];unsigned offset,opens,closes,reads,errors;bool io_owner,pin=true,short_read,bad_size,open_fail;
struct Re4dcIoScope{Re4dcIoScope(){assert(!io_owner);io_owner=true;}~Re4dcIoScope(){io_owner=false;}};
struct{unsigned id=1;const char*path="/cd/movie/test";CheckedAsset asset;}m;
file_t fs_open(const char*,int){assert(io_owner);++opens;offset=0;return open_fail?-1:1;}
off_t fs_total(file_t){assert(io_owner);return bad_size?1535:1536;}
ssize_t fs_read(file_t,void*out,unsigned bytes){assert(io_owner);++reads;if(short_read)return 0;assert(offset+bytes<=1536);memcpy(out,file_bytes+offset,bytes);offset+=bytes;return bytes;}
int fs_close(file_t){assert(io_owner);++closes;return 0;}
namespace re4dc_gcasset{bool ensure_disc_catalog(){assert(!io_owner);return pin;}}
extern "C" void re4dc_log(const char*,...){assert(!io_owner);++errors;}
void capture(){const unsigned size=1536;
''' + capture + r'''
}
int main(){for(unsigned i=0;i<1536;++i)file_bytes[i]=i%251;CatalogRow row{"movie","00001",fingerprint(file_bytes,1536),Unknown};assert(install(&row,1));
capture();assert(m.asset.value && opens==1 && closes==1 && reads==3 && !errors);AssetDescription d{};assert(describe_checked(m.asset,&d) && !memcmp(d.digest.bytes,row.digest.bytes,32));
short_read=true;capture();assert(!m.asset.value && errors==1 && closes==2);short_read=false;
bad_size=true;capture();assert(!m.asset.value && errors==2 && closes==3);bad_size=false;
open_fail=true;capture();assert(!m.asset.value && errors==3 && closes==3);open_fail=false;
pin=false;capture();assert(!m.asset.value && opens==4); // no source attribution without a valid pinned catalog
}
'''
        with tempfile.TemporaryDirectory(prefix='gc-port23-movie-file-', dir='/dev/shm') as temporary:
            root = Path(temporary);(root / 'fixture.cpp').write_text(fixture);executable = root / 'fixture'
            subprocess.run(['g++', '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror',
                            '-DRE4DC_GC_ASSET_GATE=1', '-I', str(GAME / 'platform/include'),
                            str(root / 'fixture.cpp'), str(GAME / 'platform/gc_asset_gate.cpp'), '-o', str(executable)], check=True)
            subprocess.run(['/lib64/ld-linux-x86-64.so.2', str(executable)], check=True)

    def test_actual_picture_owner_upload_and_accepted_packet(self):
        ui = (GAME / 'platform/native_ui.cpp').read_text()
        states = ui[ui.index('using GcAssetPacketState='):ui.index('void gcasset_packet_emitted(')]
        metadata = ui[ui.index('struct GcAssetMovieProof {'):ui.index('#endif', ui.index('struct GcAssetMovieProof {'))]
        api = ui[ui.index('// GC_ASSET_MOVIE_API_BEGIN'):ui.index('// GC_ASSET_MOVIE_API_END')]
        draw = function(ui, 'void movie_draw(){')
        fixture = r'''
#include "gc_asset_payloads.h"
#include "gc_asset_packet_cursor.h"
#include <cassert>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <string>
using namespace re4dc_gcasset;
bool sq_held;std::string logs;
extern "C" void re4dc_log(const char* fmt,...){assert(!sq_held);char text[256];va_list ap;va_start(ap,fmt);const int n=vsnprintf(text,sizeof text,fmt,ap);va_end(ap);assert(n>=0 && unsigned(n)<256);logs+=text;}
struct Re4dcModelPart{const void* model;const void* info;};
struct Package{struct Header{unsigned texture_count=0;}head;bool upload_complete()const{return true;}const Header&header()const{return head;}void*pvr_texture(unsigned)const{return nullptr;}};
struct Entry{bool valid=false;Package package;};Entry entries[1];
void gcasset_texture_emitted(Entry*,Consumer){assert(false);}
using pvr_ptr_t=void*;struct pvr_poly_hdr_t{unsigned words[8];};
struct pvr_vertex_t{unsigned flags;float x,y,z,u,v;unsigned argb,oargb;};
struct pvr_poly_cxt_t{struct{unsigned culling;}gen;struct{unsigned comparison,write;}depth;struct{unsigned src,dst;}blend;struct{unsigned uv_clamp;}txr;};
constexpr unsigned PVR_LIST_TR_POLY=2,PVR_TXRFMT_YUV422=0,PVR_TXRFMT_NONTWIDDLED=0,PVR_FILTER_BILINEAR=0,PVR_CULLING_NONE=0,PVR_DEPTHCMP_ALWAYS=0,PVR_DEPTHWRITE_DISABLE=0,PVR_BLEND_ONE=1,PVR_BLEND_ZERO=0,PVR_UVCLAMP_UV=0;
constexpr unsigned PVR_CMD_VERTEX=0xe0000000,PVR_CMD_VERTEX_EOL=0xf0000000;
void* movie_texture=(void*)0xa4002000;unsigned movie_width=288,movie_height=192,movie_upload_serial;bool movie_picture;
void pvr_poly_cxt_txr(pvr_poly_cxt_t*,unsigned,unsigned,unsigned,unsigned,void*,unsigned){}
void pvr_poly_compile(pvr_poly_hdr_t* h,pvr_poly_cxt_t*){*h={};h->words[0]=0x80000008;h->words[3]=(unsigned(reinterpret_cast<std::uintptr_t>(movie_texture))&0x007fffffU)/8;}
namespace re4dc{namespace render{void begin_pvr_packet(pvr_vertex_t* p,unsigned& count,const pvr_poly_hdr_t&h){memcpy(p,&h,32);count=1;}}}
#define RE4DC_UI_X(x) (x)
#define RE4DC_UI_Y(y) (y)
''' + states + '\n' + function(ui, 'void gcasset_packet_emitted(') + '\n' + metadata + '\n' + api + r'''
bool discard,wrong_pointer,wrong_extent;
void stream_send(const void* packet,unsigned bytes){if(discard)return; // actual observer runs after sq_unlock
 if(wrong_extent)gcasset_packet_emitted(packet,bytes-32,2,gcasset_packet_consumer);
 else if(wrong_pointer){alignas(32) unsigned copy[40];memcpy(copy,packet,bytes);gcasset_packet_emitted(copy,bytes,2,gcasset_packet_consumer);}
 else gcasset_packet_emitted(packet,bytes,2,gcasset_packet_consumer);
 sq_held=false;}
''' + draw + r'''
unsigned rows(){unsigned count=0;std::size_t at=0;while((at=logs.find("GC-ASSET v=",at))!=std::string::npos){++at;++count;}return count;}
int main(){unsigned char payload[]={1,2,3};auto digest=fingerprint(payload,sizeof payload);CatalogRow row{"movie","00001",digest,Unknown};assert(install(&row,1));auto asset=bind_checked("movie","00001",digest);
 auto owner=re4dc_gcasset_movie_bind(movie_texture,288,192,asset.value);assert(owner);
 begin(0x111,1,Required);movie_draw();end(1);assert(!rows()); // no completed upload
 logs.clear();begin(0x111,2,Required);re4dc_gcasset_movie_begin_upload(owner,movie_texture);movie_picture=true;++movie_upload_serial;
 re4dc_gcasset_movie_uploaded(owner,movie_texture,288,192,asset.value);assert(!rows());movie_draw();end(2);
 assert(rows()==1 && logs.find("consumer=movie")!=std::string::npos && logs.find("provenance=unknown")!=std::string::npos && logs.find("errors=0")!=std::string::npos);
 // Accepted packets must be exactly the scoped pointer and extent.
 for(unsigned mode=0;mode<3;++mode){logs.clear();begin(0x111,3+mode,Required);discard=mode==0;wrong_pointer=mode==1;wrong_extent=mode==2;movie_draw();end(3);assert(!rows());}
 discard=wrong_pointer=wrong_extent=false;
 // An unannounced write/version change, stale owner, wrong dimensions or asset cannot be blessed.
 ++movie_upload_serial;logs.clear();begin(0x111,6,Required);movie_draw();end(4);assert(!rows());
 re4dc_gcasset_movie_begin_upload(owner+1,movie_texture);re4dc_gcasset_movie_uploaded(owner,movie_texture,288,192,asset.value);assert(!gcasset_movie.upload);
 re4dc_gcasset_movie_begin_upload(owner,movie_texture);re4dc_gcasset_movie_uploaded(owner,movie_texture,289,192,asset.value);assert(!gcasset_movie.upload);
 re4dc_gcasset_movie_begin_upload(owner,movie_texture);re4dc_gcasset_movie_uploaded(owner,movie_texture,288,192,asset.value+1);assert(!gcasset_movie.upload);
 // Free/reallocation at the same address revokes old owner and upload versions.
 gcasset_movie_forget();auto next=re4dc_gcasset_movie_bind(movie_texture,288,192,asset.value);assert(next!=owner);
 re4dc_gcasset_movie_begin_upload(owner,movie_texture);re4dc_gcasset_movie_uploaded(owner,movie_texture,288,192,asset.value);assert(!gcasset_movie.upload);
 re4dc_gcasset_movie_begin_upload(next,movie_texture);re4dc_gcasset_movie_uploaded(next,movie_texture,288,192,asset.value);assert(gcasset_movie.upload);
 // No ambient movie-texture range exemption outside movie_draw's scope.
 logs.clear();begin(0x111,7,Required);unsigned packet[16]{};packet[0]=0x80000008;packet[3]=0x2000/8;packet[8]=PVR_CMD_VERTEX_EOL;
 stream_send(packet,64);end(4);assert(!rows() && logs.find("unmapped-texture-address")!=std::string::npos);
 gcasset_movie_serial=~0U;assert(!re4dc_gcasset_movie_bind(movie_texture,288,192,asset.value));
}
'''
        with tempfile.TemporaryDirectory(prefix='gc-port23-movie-', dir='/dev/shm') as temporary:
            root = Path(temporary);(root / 'fixture.cpp').write_text(fixture);executable = root / 'fixture'
            subprocess.run(['g++', '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror',
                            '-DRE4DC_GC_ASSET_GATE=1', '-DRE4DC_PVR_STREAM=1',
                            '-I', str(GAME / 'platform/include'), str(root / 'fixture.cpp'),
                            str(GAME / 'platform/gc_asset_gate.cpp'), str(GAME / 'platform/gc_asset_members.cpp'),
                            str(GAME / 'platform/gc_asset_payloads.cpp'), '-o', str(executable)], check=True)
            subprocess.run(['/lib64/ld-linux-x86-64.so.2', str(executable)], check=True)


if __name__ == '__main__':unittest.main()
