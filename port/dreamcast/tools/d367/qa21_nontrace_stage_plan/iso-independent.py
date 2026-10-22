"""Small read-only ISO9660/Rock-Ridge/Joliet parser independent of fp_iso.
Plain2048-byte track only, absolute extents at45000. No write/extract API.
"""
import os,struct
BASE=45000;BLOCK=2048

def both(data,offset):
 le=struct.unpack_from('<I',data,offset)[0];be=struct.unpack_from('>I',data,offset+4)[0]
 if le!=be:raise ValueError('ISO mirrored-endian mismatch')
 return le

def rr(rec):
 size=rec[32];offset=33+size+(0 if size%2 else 1);parts=[]
 while offset+4<=len(rec):
  length=rec[offset+2]
  if length<4 or offset+length>len(rec):raise ValueError('invalid system-use entry')
  if rec[offset:offset+2]==b'NM':parts.append(rec[offset+5:offset+length])
  offset+=length
 return os.fsdecode(b''.join(parts)) if parts else None

class ISO:
 def __init__(self,read,size):
  if size%BLOCK:raise ValueError('plain2048 track required')
  self.get=read;self.size=size;self.descriptors=[];self.roots=[]
  for sector in range(16,48):
   d=self.bytes(sector*BLOCK,BLOCK)
   if d[1:6]!=b'CD001' or d[6]!=1:raise ValueError('invalid ISO descriptor')
   if d[0] in (1,2):
    count=both(d,80)
    if count*BLOCK>size:raise ValueError('volume exceeds track')
    self.descriptors.append(dict(offset=sector*BLOCK,kind=d[0],blocks=count))
    if d[0]==1 or d[88:91] in (b'%/@',b'%/C',b'%/E'):
     self.roots.append((d[0],both(d[156:190],2),both(d[156:190],10)))
   if d[0]==255:break
  else:raise ValueError('no bounded descriptor terminator')
  if not any(k==1 for k,_,_ in self.roots):raise ValueError('primary tree required')
 def bytes(self,start,length):
  if start<0 or length<0 or start+length>self.size:raise ValueError('ISO range outside track')
  b=self.get(start,length)
  if len(b)!=length:raise ValueError('short ISO read')
  return b
 def entries(self,kind=1):
  roots=[r for r in self.roots if r[0]==kind]
  if len(roots)!=1:raise ValueError('tree unavailable/ambiguous')
  _,extent,size=roots[0];queue=[('',extent,size)];seen=set();result=[]
  while queue:
   prefix,extent,size=queue.pop(0)
   if extent in seen:continue
   seen.add(extent)
   data=self.bytes((extent-BASE)*BLOCK,size);i=0
   while i<len(data):
    length=data[i]
    if not length:i=(i//BLOCK+1)*BLOCK;continue
    if length<34 or i+length>len(data) or i%BLOCK+length>BLOCK:raise ValueError('invalid directory record')
    rec=data[i:i+length];offset=(extent-BASE)*BLOCK+i;i+=length
    raw=rec[33:33+rec[32]]
    if raw in (b'\x00',b'\x01'):continue
    rock=rr(rec) if kind==1 else None
    name=rock or (os.fsdecode(raw) if kind==1 else raw.decode('utf-16-be'))
    name=name.split(';')[0]
    if kind==1 and rock is None:name=name.rstrip('.')
    path=prefix+'/'+name;ext=both(rec,2);n=both(rec,10);directory=bool(rec[25]&2)
    if (ext-BASE)*BLOCK<0 or (ext-BASE)*BLOCK+n>self.size:raise ValueError('file extent outside track')
    row=dict(path=path,extent=ext,bytes=n,directory=directory,record_offset=offset,kind=kind)
    result.append(row)
    if directory:queue.append((path,ext,n))
  if len({r['path'] for r in result})!=len(result):raise ValueError('duplicate ISO paths')
  return result
