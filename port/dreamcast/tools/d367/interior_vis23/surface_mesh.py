"""Small read-only R4IM3/R4PW decoder for exact source topology; no conversion.
Layout matches current room/instanced_mesh.hpp and pinned r4im.py reference.
"""
from pathlib import Path
import struct
class Pkg:
 def __init__(self,mesh,policy):
  self.m=Path(mesh).read_bytes();raw=Path(policy).read_bytes();h=struct.unpack_from('<4s15I4I',self.m)
  self.magic,self.version,self.mesh_bytes,self.mesh_crc,self.nmesh,self.npart,self.nlet,self.nvert,self.nstrip,self.npal,self.o_mesh,self.o_part,self.o_let,self.o_vert,self.o_strip,self.o_pal=h[:16]
  if self.magic!=b'R4IM' or self.version!=3 or self.mesh_bytes!=len(self.m):raise ValueError('Unsupported mesh/header extent')
  self.ncl,self.nlv,self.o_plod,self.o_cl,self.o_lv=struct.unpack_from('<5I',self.m,80)
  self.meshes=[]
  for i in range(self.nmesh):
   x=struct.unpack_from('<HBBHHIII12f',self.m,self.o_mesh+68*i);self.meshes.append(dict(bin=x[0],first_part=x[6],part_count=x[7],origin=x[8:11],step=x[11:14],bmin=x[14:17],bmax=x[17:20]))
  self.parts=[]
  for i in range(self.npart):
   x=struct.unpack_from('<IIBBBBII4f',self.m,self.o_part+36*i);self.parts.append(dict(first_let=x[6],let_count=x[7]))
  self.plod=[struct.unpack_from('<II',self.m,self.o_plod+8*i) for i in range(self.npart)]
  self.clusters=[]
  for i in range(self.ncl):
   x=struct.unpack_from('<6HII',self.m,self.o_cl+20*i);self.clusters.append(dict(bmin=x[:3],bmax=x[3:6],first_level=x[6],level_count=x[7]))
  self.levels=[struct.unpack_from('<IIf',self.m,self.o_lv+12*i) for i in range(self.nlv)]
  self.lets=[]
  for i in range(self.nlet):
   x=struct.unpack_from('<IIIHH6H',self.m,self.o_let+28*i);self.lets.append(dict(first_vertex=x[0],first_strip=x[1],strip_bytes=x[2],vc=x[3],sc=x[4],bmin=x[5:8],bmax=x[8:11]))
  self.verts=[struct.unpack_from('<6H',self.m,self.o_vert+12*i) for i in range(self.nvert)]
  hp=struct.unpack_from('<4s7I',raw);self.sidecar_crc=hp[5]
  if hp[0]!=b'R4PW' or hp[3]!=self.npart or len(raw)!=32+hp[3]*16+hp[2]*52:raise ValueError('Policy layout extent mismatch')
  self.pmeta=[]
  for i in range(hp[3]):
   x=struct.unpack_from('<IIHHBBBB',raw,32+i*16);self.pmeta.append(dict(crc=x[0],fnv=x[1],w=x[2],h=x[3],pass_=x[4],cull=x[5]))
  self.placements=[]
  for i in range(hp[2]):
   x=struct.unpack_from('<HH12f',raw,32+hp[3]*16+52*i);self.placements.append(dict(mesh=x[0],placement=x[1],affine=[list(x[2+4*k:6+4*k]) for k in range(3)]))
 def let_tris(self,li):
  x=self.lets[li];start=self.o_strip+x['first_strip'];pos=start
  if x['sc']&0x8000:
   offsets=struct.unpack_from('<%dH'%x['vc'],self.m,pos);pos+=x['vc']*2
  else:offsets=range(x['vc'])
  corners=[self.verts[x['first_vertex']+i] for i in offsets];end=pos+x['strip_bytes'];triangles=[];strips=0
  if end>len(self.m):raise ValueError('Strip extent')
  while pos<end:
   n=self.m[pos];pos+=1;ix=self.m[pos:pos+n];pos+=n;strips+=1
   if pos>end or any(i>=len(corners) for i in ix):raise ValueError('Invalid strip index/extent')
   for k in range(n-2):triangles.append((ix[k],ix[k+1],ix[k+2]) if k%2==0 else (ix[k+2],ix[k+1],ix[k]))
  if strips!=(x['sc']&0x7fff):raise ValueError('Strip count mismatch')
  return corners,triangles
