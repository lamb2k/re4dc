"""Stage resource accounting; every failed output remains charged, no exclusions."""
import os,shutil,stat
from pathlib import Path
GiB=1024**3;MiB=1024**2
CAP=int(1.2*GiB);RUNTIME=18*GiB+64*MiB;ADMISSION=18*GiB+CAP+200*MiB

def charge(st):return max(st.st_size,getattr(st,'st_blocks',0)*512)

def measure(root,lstat=os.lstat):
 root=Path(root);total=0;files=[]
 if not root.exists():return {'bytes':0,'entries':[]}
 stack=[root]
 while stack:
  p=stack.pop()
  try:st=lstat(p)
  except FileNotFoundError:continue
  if stat.S_ISLNK(st.st_mode):raise ValueError('stage symlink forbidden')
  if stat.S_ISDIR(st.st_mode):
   total+=charge(st)
   try:stack.extend(p.iterdir())
   except FileNotFoundError:continue
  elif stat.S_ISREG(st.st_mode):
   if st.st_nlink!=1:raise ValueError('stage hardlinks forbidden')
   n=charge(st);total+=n;files.append({'path':str(p),'logical':st.st_size,'allocated':getattr(st,'st_blocks',0)*512,'charged':n})
  else:raise ValueError('unexpected stage filesystem object')
 return {'bytes':total,'entries':files}

class Guard:
 def __init__(self,root,free=lambda:shutil.disk_usage('/mnt/c').free,cap=CAP):
  self.root=Path(root);self.free=free;self.cap=cap;self.peak=0;self.minimum=None
 def check(self,extra=0,admission=False):
  usage=measure(self.root);free=self.free();self.peak=max(self.peak,usage['bytes']);self.minimum=free if self.minimum is None else min(self.minimum,free)
  if usage['bytes']+extra>self.cap:raise RuntimeError('cumulative stage cap including failures')
  if free<(ADMISSION if admission else RUNTIME+extra):raise RuntimeError('fresh C admission/runtime floor or next-write reserve')
  return usage
