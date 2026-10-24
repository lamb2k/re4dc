from pathlib import Path
import subprocess,json,hashlib,re
repo=Path('/root/work/lanes/dedup-offline23-next')
base=subprocess.check_output(['git','-C',str(repo),'rev-parse','origin/t15/int'],text=True).strip()
out={'source':base,'no_build_guest_stage':True,'files':{},'old_outputs':[]}
for name in ('port/dreamcast/game/platform/native_static.cpp','port/dreamcast/game/platform/include/scenery_chunk_select.inc','port/dreamcast/game/scenery19.mk','port/dreamcast/game/logiclod20.mk','port/dreamcast/tools/d367/rr/recipe.conf','port/dreamcast/tools/d367/fullplay/fp_run.py','port/dreamcast/tools/d367/trace_lock.sh'):
 try: data=subprocess.check_output(['git','-C',str(repo),'show',base+':'+name],stderr=subprocess.DEVNULL)
 except subprocess.CalledProcessError: continue
 out['files'][name]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
keys=('ACTOR_SETUP_LEAN','SCENERY_SELECT_ONLY','SCENERY_REPLAY_LEAN','SCENERY_SUBMIT_BATCH','SCENERY_SELECT_LEAN2','SCENERY_EMIT_PREFETCH','SCENERY_UV_SNAPSHOT','WORLD_METER','QA_MENU','PC_SAMPLER','SCN_CENSUS','ALIVE_CAP','R101_ALIVE_CAP','PS2_WORLD_TRANSITION_OWNER','MESH_LOD_PX','SCENERY_FAR_LOD','ARENA_FIT_KOS_BYTES')
for label in ('soN','soY','soX'):
 p=Path('/root/probe/lanes/route')/('out-'+label+'rW')
 rec={'label':label,'present':p.is_dir(),'knobs':{},'discs':{}}
 q=p/'resolved-knobs.txt'
 if q.exists():
  for ln in q.read_text().splitlines():
   k,sep,v=ln.partition('=')
   if sep and k in keys:rec['knobs'][k]=v
  rec['resolved_sha256']=hashlib.sha256(q.read_bytes()).hexdigest()
 q=p/'elf.sha256'
 if q.exists():rec['recorded_elf_sha256']=q.read_text().split()[0]
 for s in ('b1','s2','f1','f2'):
  d=Path('/root/work/lanes/select-only23-scratch/discs')/(label+'-'+s)/'gdemu'
  rec['discs'][s]=all((d/f).is_file() for f in ('disc.gdi','track01.bin','track02.raw','track03.bin'))
 out['old_outputs'].append(rec)
so=Path('/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/so23')
out['reusable_harness']={str(p.relative_to(so)):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in [so/'run1.sh',so/'runpair.sh',so/'an.py',so/'pixm.py',so/'build.sh',*sorted((so/'scenes').glob('*.txt'))]}
out['old_tree']={'head':subprocess.check_output(['git','-C','/root/work/lanes/select-only23','rev-parse','HEAD'],text=True).strip(),'status':subprocess.check_output(['git','-C','/root/work/lanes/select-only23','status','--short'],text=True).splitlines()}
dest=Path('/mnt/c/Game Dev/Emulators/codex-lanes/world-emit23/preflight-pins.json')
dest.write_text(json.dumps(out,indent=2)+'\n')
for r in out['old_outputs']:print(json.dumps(r))
print('PINNED',base)
