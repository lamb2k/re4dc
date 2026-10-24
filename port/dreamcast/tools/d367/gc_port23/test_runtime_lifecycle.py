from pathlib import Path
import subprocess
import tempfile
import unittest
from test_runtime_hooks import function

HERE = Path(__file__).resolve().parent
GAME = HERE.parents[2] / 'game'


class RuntimeLifecycleTests(unittest.TestCase):
    def test_actual_ui_helpers_and_audio_mutex_publication(self):
        ui = (GAME / 'platform/native_ui.cpp').read_text()
        audio = (GAME / 'platform/audio_aica.cpp').read_text()
        lifecycle = ui[ui.index('// GC_ASSET_LIFECYCLE_BEGIN'):ui.index('// GC_ASSET_LIFECYCLE_END')]
        admission = function(audio, 'extern "C" unsigned re4dc_gcasset_audio_admission(')
        checkpoint = audio[audio.index('    gcasset_audio_checkpoints|='):audio.index('#endif', audio.index('    gcasset_audio_checkpoints|='))]
        fixture = r'''
#include "gc_asset_lifecycle.h"
#include <cassert>
#include <cstdarg>
#include <cstdio>
#include <string>
#include <initializer_list>
using namespace re4dc_gcasset;
std::string logs;bool mutex_held;unsigned locks,unlocks;
extern "C" void re4dc_log(const char*fmt,...){assert(!mutex_held);char text[256];va_list ap;va_start(ap,fmt);vsnprintf(text,sizeof text,fmt,ap);va_end(ap);logs+=text;}
unsigned gcasset_audio_checkpoints;int g_lock;
void mutex_lock(int*){assert(!mutex_held);mutex_held=true;++locks;}
void mutex_unlock(int*){assert(mutex_held);mutex_held=false;++unlocks;}
''' + admission + r'''
unsigned frame=10,resets;struct Entry{bool pending=false;};Entry entries[1];CheckedAsset asset;
void gcasset_texture_flush(Entry&e){assert(!mutex_held);if(e.pending){emitted_checked(Texture,asset);e.pending=false;}}
void gcasset_packet_reset(){assert(!mutex_held);++resets;}
namespace re4dc_gcasset{void member_flush(){assert(!mutex_held);}void payload_flush_all(){assert(!mutex_held);}void bank_pump(){assert(!mutex_held);}bool ensure_disc_catalog(){assert(!mutex_held);return true;}}
''' + lifecycle + r'''
void audio_step_checkpoint(){mutex_lock(&g_lock);
''' + checkpoint + r'''
mutex_unlock(&g_lock);}
int main(){unsigned char bytes[]={1,2,3};CatalogRow row{"texture","title",fingerprint(bytes,3),Unknown};assert(install(&row,1));asset=bind_checked("texture","title",row.digest);
 gcasset_startup();assert(gcasset_visit_live && logs.find("phase=startup visit=1")!=std::string::npos);
 entries[0].pending=true;audio_step_checkpoint();re4dc_gcasset_finish();
 assert(logs.find("phase=startup visit=1 kind=texture")!=std::string::npos && logs.find("checked=1f6")!=std::string::npos);
 assert(logs.find("wired=1f6")!=std::string::npos); // static geometry/weapon coverage is deliberately unfinished
 unsigned old_resets=resets;re4dc_gcasset_finish();assert(resets==old_resets); // successful repeated retirement is idempotent
 logs.clear();re4dc_gcasset_room_enter(0x111);assert(gcasset_visit_serial==2 && logs.find("room=0111 visit=2")!=std::string::npos);
 entries[0].pending=true;audio_step_checkpoint();re4dc_gcasset_finish();assert(logs.find("room=0111 visit=2 kind=texture")!=std::string::npos);
 logs.clear();re4dc_gcasset_room_enter(0x113);re4dc_gcasset_finish();assert(logs.find("checked=136")!=std::string::npos); // missing actual audio flush is not checked
 logs.clear();re4dc_gcasset_room_enter(0x117);re4dc_gcasset_room_enter(0x118);assert(logs.find("room-enter-without-retire")!=std::string::npos);re4dc_gcasset_finish();
 gcasset_visit_serial=~0U;logs.clear();re4dc_gcasset_room_enter(0x119);assert(!gcasset_visit_live && logs.find("visit-serial-exhausted")!=std::string::npos);
 assert(locks==unlocks && !mutex_held);
}
'''
        # Successful direct retire calls the same finalizer only after the
        # movie owner refusal, before member and package lifetime retirement.
        retire = function(ui, 'extern "C" void re4dc_ui_retire_room()')
        self.assertLess(retire.index('movie arena active'), retire.index('re4dc_gcasset_finish()'))
        self.assertLess(retire.index('re4dc_gcasset_finish()'), retire.index('member_retire_transient'))
        init = function(ui, 'extern "C" void re4dc_ui_init()')
        self.assertIn('if(ready)gcasset_startup();', init)
        with tempfile.TemporaryDirectory(prefix='gc-port23-lifecycle-', dir='/dev/shm') as temporary:
            root = Path(temporary);(root / 'fixture.cpp').write_text(fixture);executable = root / 'fixture'
            subprocess.run(['g++', '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror',
                            '-DRE4DC_GC_ASSET_GATE=1', '-DRE4DC_NATIVE_MES=1',
                            '-I', str(GAME / 'platform/include'), str(root / 'fixture.cpp'),
                            str(GAME / 'platform/gc_asset_gate.cpp'), '-o', str(executable)], check=True)
            subprocess.run(['/lib64/ld-linux-x86-64.so.2', str(executable)], check=True)


if __name__ == '__main__':unittest.main()
