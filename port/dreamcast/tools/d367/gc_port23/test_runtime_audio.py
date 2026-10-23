from pathlib import Path
import subprocess
import tempfile
import unittest
from test_runtime_hooks import function

HERE = Path(__file__).resolve().parent
GAME = HERE.parents[2] / 'game'


class RuntimeAudioTests(unittest.TestCase):
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
