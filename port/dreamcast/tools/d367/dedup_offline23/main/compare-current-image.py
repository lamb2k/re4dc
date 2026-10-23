import subprocess,hashlib,json,tempfile
from pathlib import Path
O=Path('/root/probe/lanes/route'); obj='/opt/toolchains/dc/sh-elf/bin/sh-elf-objcopy'
with tempfile.TemporaryDirectory(prefix='dd3-image-read-',dir='/dev/shm') as tmp:
 blobs=[]
 for name in ('dd23af09on2rW','dd23daabnowrW'):
  out=Path(tmp)/(name+'.bin');subprocess.run([obj,'-R','.stack','-O','binary',str(O/('out-'+name)/'re4dc-game.elf'),str(out)],check=True);blobs.append(out.read_bytes())
 A,B=blobs
 assert len(A)==len(B) and len(A)>1000000
 d=[i for i,(x,y) in enumerate(zip(A,B)) if x!=y]
 expected=A.replace(b'af09f0a2',b'daabb0db')
 res=dict(old_sha256=hashlib.sha256(A).hexdigest(),current_sha256=hashlib.sha256(B).hexdigest(),bytes=len(A),different_bytes=len(d),same_after_qa_source_label_only=expected==B,old_label_occurrences=A.count(b'af09f0a2'))
 print(json.dumps(res))
 Path('/mnt/c/Flycast-Evidence/re4-dreamcast/dedup-offline23-20261023/current-image-label-comparison.json').write_text(json.dumps(res,indent=2)+'\n')
