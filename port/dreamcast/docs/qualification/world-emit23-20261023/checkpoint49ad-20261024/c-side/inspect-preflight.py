from pathlib import Path
import subprocess,json,hashlib
r=Path('/root/work/lanes/dedup-offline23-next')
sha=subprocess.check_output(['git','-C',str(r),'rev-parse','origin/t15/int'],text=True).strip()
g=lambda p: subprocess.check_output(['git','-C',str(r),'show',sha+':'+p],text=True)
s=g('port/dreamcast/game/platform/native_static.cpp')
for a,b in [(6090,6135),(6200,6300),(6340,6388)]:
 print('LINES',a,b);print('\n'.join(f'{i+1}: {v}' for i,v in enumerate(s.splitlines()) if a<=i+1<=b))
print('CENSUS OUTPUT');print('\n'.join(f'{i+1}: {v}' for i,v in enumerate(s.splitlines()) if 'scnc:' in v or 'scn_cen[' in v))
print('BUILD INVENTORY')
for x in ('soN','soY','soX'):
 p=Path('/root/probe/lanes/route')/('out-'+x+'rW')
 rec={'label':x,'present':p.is_dir(),'files':{},'discs':{}}
 for f in ('re4dc-game.elf','elf.sha256','resolved-knobs.txt','candidate.txt'):
  q=p/f
  if q.exists():
   rec['files'][f]={'bytes':q.stat().st_size}
   if f!='re4dc-game.elf':
    t=q.read_text(errors='replace')
    rec['files'][f]['excerpt']='\n'.join(z for z in t.splitlines() if any(k in z for k in ('SCENERY_','ACTOR_SETUP_LEAN','WORLD_METER','PC_SAMPLER','source','commit','SHA','dc87')) or f=='elf.sha256')[:5500]
 for scene in ('b1','s2','f1','f2'):
  q=Path('/root/work/lanes/select-only23-scratch/discs')/(x+'-'+scene)/'gdemu'
  rec['discs'][scene]=all((q/f).exists() for f in ('disc.gdi','track01.bin','track02.raw','track03.bin'))
 print(json.dumps(rec))
print('SELECT TREE')
print(subprocess.check_output(['git','-C','/root/work/lanes/select-only23','status','--short'],text=True))
print(subprocess.check_output(['git','-C','/root/work/lanes/select-only23','rev-parse','HEAD'],text=True))
