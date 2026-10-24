"""Root read-only inventory of obsolete qualified 7a compiler intermediates."""
from pathlib import Path
import re,hashlib,json,os
ROOT=Path('/root/probe/lanes/route');OUT=Path('/mnt/c/Game Dev/Emulators/codex-lanes/world-emit23/OLD-7A-OBJECTS-INVENTORY-v1.json')
SOURCE='7a3af776ff8c14070f96272cd48074e5895d0490'
pattern=r'out-(?:fpwe23[RLBE]7a3a(?:[gcmn]W|gP)|we23[RLBE]7a3ar[PT])'
rows=[];units=[]
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
for d in sorted(ROOT.iterdir()):
 if not re.fullmatch(pattern,d.name):continue
 assert d.resolve()==d and not d.is_symlink()
 assert (d/'stack.txt').read_text().strip()==SOURCE and not (d/'missing.txt').read_text().strip()
 keep=[d/'re4dc-game.elf',*sorted(d.glob('*.ovl'))];assert len(keep)==15
 units.append({'unit':str(d),'stack':sha(d/'stack.txt'),'keep':{p.name:{'sha256':sha(p),'size':p.stat().st_size} for p in keep}})
 obj=d/'obj';assert obj.resolve()==obj and obj.is_dir()
 for p in sorted(obj.rglob('*')):
  if not p.is_file() or p.suffix not in ['.o','.d']:continue
  assert p.resolve()==p and not any(x.is_symlink() for x in p.parents if x!=Path('/'))
  # Retain renderer/actor/cache objects as extra actual-code evidence.
  if any(x in p.name for x in ['native_static','native_actor','coarse_actor','bfc','backface','cache']):continue
  st=p.stat()
  if st.st_nlink!=1:continue
  rows.append({'path':str(p),'size':st.st_size,'allocated':st.st_blocks*512,'sha256':sha(p),'dev':st.st_dev,'inode':st.st_ino,'mtime_ns':st.st_mtime_ns,'nlink':st.st_nlink})
assert len(units)==25
result={'source':SOURCE,'read_only':True,'units':units,'files':rows,'count':len(rows),'bytes':sum(x['size'] for x in rows),'allocated':sum(x['allocated'] for x in rows),'scope':'Only old root-owned7a .o/.d single-link rebuildables, retain main/all14 overlays/source/profiles/logs and renderer/actor/cache object evidence; no cleanup performed.'}
with OUT.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps({k:result[k] for k in ['read_only','count','bytes','allocated']}))