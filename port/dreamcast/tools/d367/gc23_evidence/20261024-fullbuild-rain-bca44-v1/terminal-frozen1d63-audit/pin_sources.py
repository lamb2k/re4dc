from pathlib import Path
import subprocess,json,hashlib
sha='1d63cffe3a232c402418f2f2d919e7abae476957';repo='/root/work/lanes/gc-port23';out=Path('/mnt/c/Game Dev/Emulators/codex-lanes/gc-port23/terminal-next-audit');game='port/dreamcast/game/'
paths=[game+'platform/'+p for p in ['gc_asset_disc.cpp','gc_asset_gate.cpp','gc_asset_audio.cpp','gc_asset_members.cpp','gc_asset_payloads.cpp','native_ui.cpp','native_actor_fast.cpp','native_movie.cpp','native_movie_stream.c','audio_aica.cpp','audio_strm.cpp','audio_stub.cpp','dvd.cpp','dvd_read_safe.cpp','os.cpp','include/gc_asset_index.inc','include/gc_asset_gate.h','include/gc_asset_lifecycle.h','include/gc_asset_static.h','include/native_io.h']]
paths += [game+p for p in ['coarse_actor_leon_hands.inc','dbgwarp_bridge.cpp','bench.cpp','ui_bridge.cpp']]+['port/dreamcast/room/gpu_lifecycle.cpp']
paths += ['src/game/'+p for p in ['main.cpp','main_sub.cpp','scheduler.cpp','dvd.cpp','read.cpp','snd.cpp','snd_sub0.cpp','snd_str2.cpp','model.cpp']]
paths += ['port/dreamcast/tools/d367/gc_port23/'+p for p in ['test_runtime_hooks.py','LIFECYCLE.md']]
rows=[]
for p in paths:
 b=subprocess.check_output(['git','-C',repo,'show',sha+':'+p]); candidates=[Path('/dev/shm/gc-static-review1d63/source')/p,Path('/dev/shm/gc-terminal-next1d63/source')/p];c=next((c for c in candidates if c.is_file()),None)
 assert c and c.read_bytes()==b,p
 rows.append({'path':p,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'git_blob':subprocess.check_output(['git','-C',repo,'rev-parse',sha+':'+p],text=True).strip()})
external=[]
for p in [Path('/mnt/c/Game Dev/Emulators/codex-lanes/gc-port23/NEXT-LINK-COVERAGE.md'),Path('/root/probe/lanes/route/out-rrfb254e8rP/resolved-knobs.txt')]:
 b=p.read_bytes();external.append({'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'scope':'external documentation/profile, not frozen git source'})
sdk=[]
for p in ['kernel/arch/dreamcast/fs/fs_iso9660.c','kernel/arch/dreamcast/sound/snd_stream.c','kernel/arch/dreamcast/hardware/spu.c','kernel/arch/dreamcast/hardware/g2bus.c','kernel/arch/dreamcast/hardware/cdrom.c','kernel/thread/thread.c','kernel/thread/mutex.c']:
 f=Path('/root/work/kos-re4dc-d367')/p;b=f.read_bytes();sdk.append({'path':str(f),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'scope':'read-only provider source, no SDK execution'})
data={'source':sha,'runtime_edited':False,'source_rows':rows,'external':external,'provider_source':sdk}
(out/'source-pins.json').write_text(json.dumps(data,indent=2)+'\n');print('verified exact git bytes:',len(rows),'source files; external',len(external),'provider',len(sdk));print(external)