"""Root read-only inventory of completed qualified 49ad compiler intermediates."""
from pathlib import Path
import re,hashlib,json,os
ROOT=Path('/root/probe/lanes/route');OUT=Path('/mnt/c/Game Dev/Emulators/codex-lanes/world-emit23/CURRENT-49AD-OBJECTS-INVENTORY-v1.json')
SOURCE='49ad20f9932d638ddb7becf5db6f86b92e0a76a2'
pattern=r'out-(?:fpwe23[RLBE]49ad(?:[gcmn]W|gP)|we23[RLBE]49adr[PT])'
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
result={'source':SOURCE,'read_only':True,'units':units,'files':rows,'count':len(rows),'bytes':sum(x['size'] for x in rows),'allocated':sum(x['allocated'] for x in rows),'scope':'Only completed root-owned49ad .o/.d single-link rebuildables, retain main/all14 overlays/source/profiles/logs and renderer/actor/cache object evidence; no cleanup performed.'}
with OUT.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps({k:result[k] for k in ['read_only','count','bytes','allocated']}))