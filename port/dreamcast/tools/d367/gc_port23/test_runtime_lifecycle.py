from pathlib import Path
import subprocess
import tempfile
import unittest
from test_runtime_hooks import function

HERE = Path(__file__).resolve().parent
GAME = HERE.parents[2] / 'game'


class RuntimeLifecycleTests(unittest.TestCase):
    def test_current_audits_and_gc_room_hook_composition(self):
        current = (GAME / 'ui_bridge.cpp').read_text()
        incoming = subprocess.check_output(['git', '-C', str(GAME.parents[2]), 'show',
            'd5c1ceab9e06461462669b3ce1d28a379747a74a:port/dreamcast/game/ui_bridge.cpp'], text=True)
        include = '#include "platform/include/gc_asset_lifecycle.h"\n'
        guard = '''#if RE4DC_GC_ASSET_GATE
    if(pG)re4dc_gcasset_room_enter((unsigned(pG->stage_no)<<8)|pG->room_no);
    else re4dc_gcasset::unresolved(re4dc_gcasset::Ui,"room-without-global");
#endif
'''
        def check_projection(text):
            self.assertEqual(text.count(include), 1)
            self.assertEqual(text.count(guard), 1)
            self.assertEqual(text.replace(include, '').replace(guard, ''), incoming)
        check_projection(current)
        enter = next(line for line in current.splitlines(keepends=True) if 're4dc_cache_p2_diag_enter(' in line)
        for mutation in [current + 're4dc_gcasset_room_enter(0);\n',
                         current.replace('#if RE4DC_GC_ASSET_GATE\n', '#if 1\n'), current.replace(enter, '')]:
            with self.assertRaises(AssertionError):check_projection(mutation)
        self.assertEqual(current.count('re4dc_cache_p2_diag_'), 3)
        for path in ['port/dreamcast/game/kos_cache_p2.mk', 'port/dreamcast/game/platform/kos_cache_p2_diag.cpp',
                     'port/dreamcast/docs/KOS_CACHE_P2_DIAG_20261023.md',
                     'port/dreamcast/tools/d367/kos_cache_audit/test_cache_diag.py']:
            expected = subprocess.check_output(['git', '-C', str(GAME.parents[2]), 'show',
                'd5c1ceab9e06461462669b3ce1d28a379747a74a:' + path])
            self.assertEqual((GAME.parents[2] / path).read_bytes(), expected)

    def test_actual_ui_helpers_and_audio_mutex_publication(self):
        ui = (GAME / 'platform/native_ui.cpp').read_text()
        audio = (GAME / 'platform/audio_aica.cpp').read_text()
        bridge = (GAME / 'ui_bridge.cpp').read_text()
        lifecycle = ui[ui.index('// GC_ASSET_LIFECYCLE_BEGIN'):ui.index('// GC_ASSET_LIFECYCLE_END')]
        admission = function(audio, 'extern "C" unsigned re4dc_gcasset_audio_admission(')
        handoff = function(audio, 'extern "C" unsigned re4dc_gcasset_audio_handoff(')
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
unsigned actor_starts;extern "C" void re4dc_gcasset_actor_startup(){assert(!mutex_held);++actor_starts;}
extern "C" void re4dc_log(const char*fmt,...){assert(!mutex_held);char text[256];va_list ap;va_start(ap,fmt);vsnprintf(text,sizeof text,fmt,ap);va_end(ap);logs+=text;}
unsigned gcasset_audio_checkpoints;int g_lock;
void mutex_lock(int*){assert(!mutex_held);mutex_held=true;++locks;}
void mutex_unlock(int*){assert(mutex_held);mutex_held=false;++unlocks;}
''' + admission + '\n' + handoff + r'''
unsigned frame=10,resets;struct Entry{bool pending=false;};Entry entries[1];CheckedAsset asset;bool inject_audio;
void gcasset_texture_flush(Entry&e){assert(!mutex_held);if(e.pending){emitted_checked(Texture,asset);e.pending=false;}}
void gcasset_packet_reset(){assert(!mutex_held);++resets;}
namespace re4dc_gcasset{void member_flush(){assert(!mutex_held);}void payload_flush_all(){assert(!mutex_held);}void bank_pump(){assert(!mutex_held);if(inject_audio){inject_audio=false;mutex_lock(&g_lock);queued_checked(audio_ticket(),SoundBank,asset);mutex_unlock(&g_lock);}}bool ensure_disc_catalog(){assert(!mutex_held);return true;}}
''' + lifecycle + r'''
struct Global{unsigned stage_no=1,room_no=0x11,room_id=0x111;}global;Global*pG=&global;
unsigned room_frames;bool steady_logged,heap_live=true,movie_can_retire=true;unsigned cache_enters,cache_leaves;
void re4dc_cache_p2_diag_enter(unsigned room){assert(room==pG->room_id);++cache_enters;}
void re4dc_cache_p2_diag_leave(unsigned room){assert(room==pG->room_id);++cache_leaves;}
bool re4dc_movie_world_before_room_retire(){return movie_can_retire;}
void re4dc_missing(const char*){}
void re4dc_room4_open(){heap_live=true;}void re4dc_room4_close(){heap_live=false;}
bool re4dc_room4_state(unsigned*a,unsigned*b,unsigned*c,unsigned*d,unsigned*e){*a=1;*b=*c=*d=*e=0;return heap_live;}
void re4dc_motion_retire_all(){}void re4dc_effect_retire_room(){}
void re4dc_ui_retire_room(){re4dc_gcasset_retire();}void audit(unsigned){}
''' + function(bridge, 'extern "C" void re4dc_room_enter()') + '\n' + function(bridge, 'extern "C" void re4dc_room_leave()') + r'''
void audio_step_checkpoint(){mutex_lock(&g_lock);
''' + checkpoint + r'''
mutex_unlock(&g_lock);}
int main(){unsigned char bytes[]={1,2,3};CatalogRow row{"texture","title",fingerprint(bytes,3),Unknown};assert(install(&row,1));asset=bind_checked("texture","title",row.digest);
 gcasset_startup();assert(gcasset_visit_live && actor_starts==1 && logs.find("phase=startup visit=1")!=std::string::npos);
 entries[0].pending=true;audio_step_checkpoint();inject_audio=true;re4dc_gcasset_retire();
 assert(logs.find("phase=startup visit=1 kind=texture")!=std::string::npos && logs.find("checked=1f6")!=std::string::npos);
 assert(logs.find("wired=1f6")!=std::string::npos); // static geometry/weapon coverage is deliberately unfinished
 assert(gcasset_phase==GcTransition && gcasset_visit_serial==2);
 unsigned old_resets=resets;re4dc_gcasset_retire();assert(resets==old_resets); // successful repeated retirement is idempotent
 assert(logs.find("phase=transition visit=2 kind=texture")!=std::string::npos && logs.find("consumer=sound_bank")!=std::string::npos);
 logs.clear();audio_step_checkpoint();re4dc_room_enter();assert(gcasset_visit_serial==3 && logs.find("room=0111 visit=3")!=std::string::npos);
 movie_can_retire=false;re4dc_room_leave();assert(gcasset_visit_live);movie_can_retire=true; // refusal cannot print END
 heap_live=false;re4dc_room_leave();assert(gcasset_visit_live);heap_live=true;
 entries[0].pending=true;audio_step_checkpoint();re4dc_room_leave();assert(gcasset_phase==GcTransition && gcasset_visit_serial==4 && logs.find("room=0111 visit=3 kind=texture")!=std::string::npos);
 assert(logs.find("from_room=0111 transition_reason=room-retire")!=std::string::npos);
 assert(cache_enters==1 && cache_leaves==1); // audit leave remains after its original refusal guards
 logs.clear();audio_step_checkpoint();re4dc_gcasset_room_enter(0x113);re4dc_gcasset_finish();assert(logs.find("checked=136")!=std::string::npos); // missing actual audio flush is not checked
 logs.clear();re4dc_gcasset_room_enter(0x117);re4dc_gcasset_room_enter(0x118);assert(logs.find("room-enter-without-transition")!=std::string::npos);re4dc_gcasset_finish();
 gcasset_visit_serial=~0U;logs.clear();re4dc_gcasset_room_enter(0x119);assert(!gcasset_visit_live && logs.find("visit-serial-exhausted")!=std::string::npos);
 assert(locks==unlocks && !mutex_held);
}
'''
        # Successful direct retire calls the same finalizer only after the
        # movie owner refusal, before member and package lifetime retirement.
        retire = function(ui, 'extern "C" void re4dc_ui_retire_room()')
        self.assertLess(retire.index('movie arena active'), retire.index('re4dc_gcasset_retire()'))
        self.assertLess(retire.index('re4dc_gcasset_retire()'), retire.index('member_retire_transient'))
        init = function(ui, 'extern "C" void re4dc_ui_init()')
        self.assertIn('if(ready)gcasset_startup();', init)
        with tempfile.TemporaryDirectory(prefix='gc-port23-lifecycle-', dir='/dev/shm') as temporary:
            root = Path(temporary);(root / 'fixture.cpp').write_text(fixture);executable = root / 'fixture'
            subprocess.run(['g++', '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror',
                            '-DRE4DC_GC_ASSET_GATE=1', '-DRE4DC_GC_ASSET_COARSE_LEON=1', '-DRE4DC_NATIVE_MES=1',
                            '-DRE4DC_MOVIE_WORLD_ARENA=1', '-DRE4DC_KOS_CACHE_P2_DIAG=1',
                            '-I', str(GAME / 'platform/include'), str(root / 'fixture.cpp'),
                            str(GAME / 'platform/gc_asset_gate.cpp'), '-o', str(executable)], check=True)
            subprocess.run(['/lib64/ld-linux-x86-64.so.2', str(executable)], check=True)


if __name__ == '__main__':unittest.main()
