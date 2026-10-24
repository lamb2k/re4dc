"""Read-only frozen source discovery, no target/compiler/guest operations."""
from pathlib import Path
import subprocess,json
ROOT=Path('/root/work/lanes/gc-motion24')
assert subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()=='aab201ceac0e18107f64a3212398afe916793327'
for arm in ['off','on']:
 p=Path('/dev/shm/gc-motion24-kos-census-v1-2g7teq3g')/arm/'command.json'
 tokens=json.loads(p.read_text());print(arm+' relevant caller tokens: '+str([s for s in tokens if s.split('=')[0] in ['AICA_STREAMS','AICA_AUDIO','DVD_FDCACHE','GC_ASSET_GATE','GC_ASSET_MOTION_UNKNOWN','GC_ASSET_CATALOG_SHA256','LEON_HAND_PACK','LEON_HAND_RETAIN','COARSE_LEON','MOTION_FAST_READ','KOS_CENSUS','ROOMCYCLE','ROUTE_MOVIE','ACTOR_TRANSACTION']]))
for relative,needles,context in [
 ('port/dreamcast/game/ui_bridge.cpp',['audit(0)','audit(1)','audit(2)'],3),
 ('port/dreamcast/game/platform/audio_aica.cpp',['start_thread();','void AXInit','void* audio_main'],7),
 ('port/dreamcast/game/platform/native_ui.cpp',['gcasset_texture_fingerprint(','gcasset_room_enter'],3),
 ('port/dreamcast/game/platform/native_motion.cpp',['storage::read_file','storage::read_slice','fast_key_read('],4),
 ('port/dreamcast/game/platform/include/texpack_index.inc',['open','close','file_t','Reader'],3),
 ('port/dreamcast/room/texture_package.cpp',['fs_open','fs_close','read_file'],4),
 ('port/dreamcast/game/platform/native_ui.cpp',['gcasset_startup();'],5),
 ('src/game/game.cpp',['re4dc_room_enter','gameRoomMemInit'],5),
]:
 lines=(ROOT/relative).read_text().splitlines();print('\nFILE '+relative)
 wanted=set()
 for i,line in enumerate(lines):
  if any(n in line for n in needles):wanted.update(range(max(0,i-context),min(len(lines),i+context+1)))
 for i in sorted(wanted):print(str(i+1)+': '+lines[i])
print('\nGC/motion-adjacent files with direct opens:')
for p in (ROOT/'port/dreamcast/game').rglob('*'):
 if not p.is_file() or p.suffix not in ['.cpp','.c','.inc','.h']:continue
 text=p.read_text(errors='replace')
 if not any(n in text for n in ['RE4DC_GC_ASSET_GATE','RE4DC_GC_ASSET_MOTION_UNKNOWN']) and not any(n in p.name for n in ['storage','texture','texpack','motion']):continue
 if not any(n in text for n in ['fs_open(','fs_open (','fopen(']):continue
 print(str(p.relative_to(ROOT)))
 for i,line in enumerate(text.splitlines()):
  if any(n in line for n in ['fs_open(','fs_open (','fs_close(','fopen(','fclose(']):print(str(i+1)+': '+line)
