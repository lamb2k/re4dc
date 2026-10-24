"""Read-only cumulative inode census. No stage, cleanup, guest or SDK."""
from pathlib import Path
import hashlib,json,os
HERE=Path(__file__).resolve().parent
ROOTS=[
 '/mnt/c/Flycast-Evidence/re4-dreamcast/gc-motion24-20261024/qa-memory-media-aab-v1',
 '/root/probe/gc-motion24-qa-media-v1',
 '/mnt/c/Flycast-Evidence/re4-dreamcast/gc-motion24-20261024/kos-census-media-v1',
 '/root/probe/gc-motion24-kos-census-media-v1',
 '/mnt/c/Game Dev/Emulators/codex-lanes/gc-motion24/qa-memory-media-prep',
 '/mnt/c/Game Dev/Emulators/codex-lanes/gc-motion24/kos-census-media-prep-v1',
 str(HERE)]
def census(roots):
 seen={};rows=[];total=0
 for name in roots:
  root=Path(name);assert not root.is_symlink();logical=unique=files=0;large=[]
  for p in sorted(root.rglob('*')):
   assert not p.is_symlink(),str(p)
   if not p.is_file():continue
   s=p.stat();key=(s.st_dev,s.st_ino);files+=1;logical+=s.st_size
   if key not in seen:seen[key]=str(p);total+=s.st_size;unique+=s.st_size
   if s.st_size>=100*1024**2:large.append(dict(path=str(p),bytes=s.st_size,dev=s.st_dev,ino=s.st_ino,nlink=s.st_nlink,first=seen[key]))
  rows.append(dict(root=name,exists=root.exists(),files=files,logical_bytes=logical,new_unique_bytes=unique,large=large))
 return dict(roots=rows,unique_bytes=total,cap_bytes=4*1024**3,remaining=4*1024**3-total,within_cap=total<=4*1024**3)
if __name__=='__main__':print(json.dumps(census(ROOTS),indent=1))
