from pathlib import Path
import hashlib
def stream_manifest(track,iso):
 tr=iso.Track(track,45000);got={};extents={}
 try:
  for name,extent,size in iso.files(tr):
   key=name.lstrip('/');assert key not in got and not Path(key).is_absolute() and '..' not in Path(key).parts,key
   h=hashlib.sha256();remain=size;lba=extent
   while remain:
    n=min(remain,1<<20);blob=tr.read_bytes(lba,n);assert len(blob)==n;h.update(blob);remain-=n;lba+=n//2048
   got[key]=dict(size=size,sha256=h.hexdigest());extents[key]=dict(lba=extent,size=size)
  ip=tr.read(45000,16)
 finally:tr.f.close()
 return got,extents,ip
