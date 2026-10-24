#!/usr/bin/env python3
"""Execute the real terminal audio state and extracted mutex boundary on host.

This proves ordering controls only, not SH4 linking, a whole terminal fence or
KOS memory. The actual detached-reader RAII is compiled with a blocked fill.
"""
from pathlib import Path
import subprocess, tempfile, unittest
ROOT=Path(__file__).resolve().parents[5]
PLATFORM=ROOT/'port/dreamcast/game/platform'

def function(text, signature):
    start=text.index(signature);brace=text.index('{',start);depth=1;i=brace+1
    while depth:
        depth += (text[i]=='{')-(text[i]=='}');i+=1
    return text[start:i]

class TerminalAudio(unittest.TestCase):
    def test_actual_state_and_boundary(self):
        audio=(PLATFORM/'audio_aica.cpp').read_text()
        quiesce=function(audio,'extern "C" unsigned re4dc_gcasset_audio_quiesce(')
        admission=function(audio,'extern "C" unsigned re4dc_gcasset_audio_admission(')
        handoff=function(audio,'extern "C" unsigned re4dc_gcasset_audio_handoff(')
        reader=function(audio,'__attribute__((unused)) void* str_main(')
        exit_guard=function(reader,'    struct GcAssetReaderExit')+';'
        step=function(audio,'void audio_step()')
        guard=step[step.index('    if(gcasset_audio_stop.stopped())'):step.index('\n#endif',step.index('    if(gcasset_audio_stop.stopped())'))]
        self.assertLess(step.index(guard),step.index('re4dc_audio_pend_run();'))
        self.assertLess(reader.index(exit_guard[:-1]),reader.index('str_index_load()'))
        self.assertNotIn('reader_exited()',reader.replace(exit_guard[:-1],''))
        self.assertGreater(reader.index('str_fill(1, gen)'),reader.index('if(gcasset_audio_stop.stopped())return nullptr;'))
        code=r"""
#include <cassert>
#include <atomic>
#include <mutex>
#include <thread>
#include "include/gc_asset_audio_stop.h"
std::mutex irq_lock;
struct HostCritical {HostCritical(){irq_lock.lock();}~HostCritical(){irq_lock.unlock();}};
using Stop=re4dc_gcasset::AudioStop<HostCritical>;
static_assert(sizeof(Stop)==4);
std::mutex g_lock;
void mutex_lock(std::mutex* p){p->lock();}
void mutex_unlock(std::mutex* p){p->unlock();}
Stop gcasset_audio_stop;
unsigned gcasset_audio_checkpoints=0, closes=0, opens=0, faults=0;
namespace re4dc_gcasset {
void close_audio_admission(){++closes;}
void open_audio_admission(){++opens;}
bool handoff_audio_admission(unsigned,unsigned){++opens;return true;}
void unresolved(Consumer,const char*){++faults;}
}
"""+quiesce+'\n'+admission+'\n'+handoff+r"""
void actual_reader_scope(std::atomic<bool>& entered,std::atomic<bool>& release){
"""+exit_guard+r"""
    GcAssetReaderExit exit;
    entered.store(true);
    while(!release.load())std::this_thread::yield();
}
void actual_step_admission(unsigned& callbacks){
    mutex_lock(&g_lock);
"""+guard+r"""
    ++callbacks;
    mutex_unlock(&g_lock);
}
int main(){
    // Real work holds the reader lease. Queue emptiness must not bypass it.
    assert(gcasset_audio_stop.reader_starting());
    assert(!gcasset_audio_stop.reader_starting());
    std::atomic<bool> entered{false}, release{false};
    std::thread reader([&]{actual_reader_scope(entered,release);});
    while(!entered.load())std::this_thread::yield();
    unsigned checkpoints=0xabcdef;
    assert(!re4dc_gcasset_audio_quiesce(&checkpoints));
    assert(closes==0 && checkpoints==0xabcdef && gcasset_audio_stop.stopped());
    unsigned callbacks=0;actual_step_admission(callbacks);assert(callbacks==0);
    assert(!gcasset_audio_stop.reader_starting());
    release.store(true);reader.join();
    gcasset_audio_checkpoints=192;
    assert(re4dc_gcasset_audio_quiesce(&checkpoints));
    assert(checkpoints==192 && closes==1);
    re4dc_gcasset_audio_admission(1);re4dc_gcasset_audio_handoff(7,8);
    assert(opens==0 && faults==2);
    // A creation failure releases exactly its claim; stop still cannot reopen.
    Stop failed;
    assert(failed.reader_starting());failed.reader_exited();failed.request();
    assert(failed.reader_idle() && !failed.reader_starting());
    // Stop-versus-detached-create race: either refused or charged until exit.
    for(unsigned i=0;i<100;++i){
        Stop state;bool accepted=false;
        std::thread a([&]{accepted=state.reader_starting();});
        std::thread b([&]{state.request();});a.join();b.join();
        assert(state.stopped());assert(state.reader_idle()!=accepted);
        if(accepted)state.reader_exited();
        assert(state.reader_idle() && !state.reader_starting());
    }
    // g_lock fences the *last complete* audio callback before idle is returned.
    gcasset_audio_stop={};gcasset_audio_checkpoints=0;
    std::atomic<bool> inside{false}, finish{false}, polling{false};
    unsigned result=0;
    std::thread last([&]{std::lock_guard<std::mutex> lock(g_lock);inside=true;
        while(!finish.load()){std::this_thread::yield();}
        gcasset_audio_checkpoints=192;});
    while(!inside.load())std::this_thread::yield();
    std::thread stop([&]{polling=true;result=re4dc_gcasset_audio_quiesce(&checkpoints);});
    while(!polling.load()){std::this_thread::yield();}
    finish=true;
    last.join();stop.join();assert(result==1 && checkpoints==192);
}
"""
        with tempfile.TemporaryDirectory(prefix='gc-terminal-audio24-') as directory:
            d=Path(directory);cpp=d/'actual.cpp';cpp.write_text(code)
            subprocess.run(['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-pthread','-DRE4DC_GC_ASSET_GATE=1','-I',str(PLATFORM),str(cpp),'-o',str(d/'actual')],check=True,timeout=45)
            subprocess.run([str(d/'actual')],check=True,timeout=15)

    def test_off_header_empty(self):
        p=subprocess.run(['g++','-E','-P','-x','c++','-DRE4DC_GC_ASSET_GATE=0','-'],input='#include "include/gc_asset_audio_stop.h"\n',text=True,capture_output=True,cwd=PLATFORM,check=True,timeout=15)
        self.assertEqual(p.stdout.strip(),'')

if __name__=='__main__':unittest.main()
