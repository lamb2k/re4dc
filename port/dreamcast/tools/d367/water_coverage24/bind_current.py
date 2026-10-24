#!/usr/bin/env python3
"""Bind the selected current r100 authored surfaces to actual original PS2 BIN geometry.
Read-only, original data kept private; never authorizes a material or texture source.
"""
import argparse,collections,hashlib,importlib.util,json,math,pathlib,resource,signal,struct,zlib
ROOT=pathlib.Path(__file__).resolve().parents[5]
PINS={'mesh':'130bac7969255f0bf31d5f9226cee21a33415103f044f0fdc7dda3607ffc89bb','sidecar':'07acc55b2b009abd8368af2880c556272cf6de41595908739afc589baceab6cd','ids':'c4394a5fb19f0a89bcef4f42134d4cfa7dff7619a8368c9a7a967fdca7011cb3','smd':'a3718d4e470e17a40769accdb7a2552a8058d79397051279b9b4b6a9ae8768da'}
def sha(d):return hashlib.sha256(d).hexdigest()
def canon(tri):return min(tuple(tri[i:]+tri[:i]) for i in range(3))
def nondeg(tri):return len(set(tri))==3

def main():
 p=argparse.ArgumentParser()
 for k in PINS:p.add_argument('--'+k,type=pathlib.Path,required=True)
 p.add_argument('--out',type=pathlib.Path,required=True);a=p.parse_args();resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,256*1024*1024));signal.alarm(120)
 if a.out.exists():raise ValueError('output exists')
 data={};refs={}
 for k in PINS:
  path=getattr(a,k);d=path.read_bytes()
  if sha(d)!=PINS[k]:raise ValueError('selected input pin changed: '+k)
  data[k]=d;refs[k]={'path':str(path),'bytes':len(d),'sha256':sha(d)}
 m,p,ids,smd=[data[k] for k in ('mesh','sidecar','ids','smd')];h=struct.unpack_from('<4s19I',m);ph=struct.unpack_from('<4s7I',p);ih=struct.unpack_from('<4s3I',ids)
 assert h[0]==b'R4IM' and h[1]==3 and h[2]==len(m) and zlib.crc32(m[80:])==h[3]
 assert ph[0]==b'R4PW' and ph[1]==1 and zlib.crc32(p[32:])==ph[5] and ph[3:5]==(h[5],h[4])
 assert ih[:3]==(b'R4ID',1,283)
 sp=importlib.util.spec_from_file_location('water_current_ps2bin',ROOT/'port/dreamcast/tools/ps2_bin.py');B=importlib.util.module_from_spec(sp);sp.loader.exec_module(B)
 base=32+16*ph[3];lh=struct.unpack_from('<8I',m,80);bindings=[]
 for wanted in (0,1):
  matches=[]
  for i in range(ph[2]):
   row=struct.unpack_from('<HH12f',p,base+52*i)
   if row[1]==wanted:matches.append((i,row))
  assert len(matches)==1
  ordinal,pl=matches[0];assert ids[16+pl[1]]==wanted
  mr=struct.unpack_from('<HBBHHIII12f',m,h[10]+68*pl[0]);assert mr[7]==1
  part=mr[6];meta=struct.unpack_from('<IIHHBBBB',p,32+16*part)
  f=struct.unpack_from('<12fBBBBIII',smd,16+64*wanted);assert f[4:7]==(0.,0.,0.) and f[15]==wanted
  binbase=struct.unpack_from('<I',smd,4)[0];binstart=binbase+struct.unpack_from('<I',smd,binbase+4*f[12])[0]
  # parse_bin follows only the actual BIN's header/material/node spans. The SMD
  # remainder is read-only backing; immutable original full-file hash is pinned.
  model=B.parse_bin(smd[binstart:]);assert mr[3]==sum(len(s['verts']) for node in model.nodes for s in node['segments'])
  original=[]
  for mat,tri in B.triangles(model):
   pts=[tuple(v['p'][j]*f[8+j]+f[j] for j in range(3)) for v in tri]
   if nondeg(pts):original.append(pts)
  source_vertices=sorted({v for tri in original for v in tri});actual=[];maxerr=0.;maxuv=0.
  source_uvs=collections.defaultdict(list)
  for _,tri in B.triangles(model):
   for v in tri:
    pos=tuple(v['p'][j]*f[8+j]+f[j] for j in range(3))
    source_uvs[pos].append(tuple(x/256. for x in v['raw']['uv']))
  partrow=struct.unpack_from('<IIBBBBII4f',m,h[11]+36*part)

  fc,nc=struct.unpack_from('<II',m,lh[2]+8*part)
  for ci in range(fc,fc+nc):
   cluster=struct.unpack_from('<6HII',m,lh[3]+20*ci);fm,nm,error=struct.unpack_from('<IIf',m,lh[4]+12*cluster[6]);assert error==0.
   for li in range(fm,fm+nm):
    let=struct.unpack_from('<IIIHH6H',m,h[12]+28*li);first,fs,nb,nv,sc=let[:5];off=h[14]+fs
    if sc&0x8000:indices=struct.unpack_from('<%dH'%nv,m,off);off+=2*nv
    else:indices=range(nv)
    corners=[]
    for vi in indices:
     q=struct.unpack_from('<6H',m,h[13]+12*(first+vi));local=[mr[8+j]+q[j]*mr[11+j] for j in range(3)]
     world=tuple(sum(pl[2+4*r+j]*local[j] for j in range(3))+pl[2+4*r+3] for r in range(3))
     nearest=min(source_vertices,key=lambda v:sum((v[j]-world[j])**2 for j in range(3)));err=max(abs(nearest[j]-world[j]) for j in range(3));maxerr=max(maxerr,err)
     if err>max(mr[11:14])+0.1:raise ValueError('current vertex differs beyond quantization')
     uv=tuple(partrow[8+j]+q[3+j]*partrow[10+j] for j in range(2))
     uverr=min(max(abs(v[j]-uv[j]) for j in range(2)) for v in source_uvs[nearest]);maxuv=max(maxuv,uverr)
     corners.append(nearest)
    end=off+nb
    while off<end:
     n=m[off];off+=1;strip=m[off:off+n];off+=n
     for j in range(n-2):
      tri=[corners[strip[j]],corners[strip[j+1]],corners[strip[j+2]]]
      if j&1:tri.reverse()
      if nondeg(tri):actual.append(tri)
    assert off==end
  source_counts=collections.Counter(canon(tri) for tri in original);actual_counts=collections.Counter(canon(tri) for tri in actual)
  exact=source_counts==actual_counts
  bindings.append({'source_object_id':wanted,'source_placement':wanted,'source_bin':f[12],'current_placement_ordinal':ordinal,'current_mesh':pl[0],'current_part':part,'triangles':len(actual),'triangle_multiset_and_winding_match':exact,'original_triangles':len(original),'source_triangles_not_in_current':sum((source_counts-actual_counts).values()),'current_triangles_not_in_source':sum((actual_counts-source_counts).values()),'max_position_axis_error_mm':maxerr,'max_raw_uv_div256_axis_error':maxuv,'uv_projection':'Current converter rawUV/256 correspondence only; original PS2 VU/GIF final UV normalization and target replacement scale are not independently proved. No screen projection/refraction UV fabricated.','current_material':{'texture_key':'%08x-%08x'%meta[:2],'width':meta[2],'height':meta[3],'pass':meta[4],'cull':meta[5],'source_texture_index':meta[6]},'missing_material_state':['live source object alpha240','actual PS2 TexBlend target ownership','independently accepted PS2 target contributors','target lifetime and completed fence']})
 result={'schema':'current-r100-water-geometry-v1','inputs':refs,'current_sidecar_crc':'%08x'%ph[5],'ids_source_policy_crc':'%08x'%ih[3],'ids_crc_equals_current':ih[3]==ph[5],'ids_compatibility':'Runtime WORLD_RECT21 reviewed remap required; this report does not forge or bypass CRC','bindings':bindings,'all_original_triangles_exact':all(x['triangle_multiset_and_winding_match'] for x in bindings),'interpretation':'Bounded original PS2 source geometry correspondence for the named selected-current1697 files; not automatic current-programme qualification or GC-ASSET provenance, dynamic material correctness, look or performance.'}
 a.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'bindings':bindings,'sha256':sha(a.out.read_bytes())}))
if __name__=='__main__':main()
