"""Prepare a PRIVATE r119 OCCL candidate from exact selected authored bytes.
No geometry/AI edits, conversion, staging, admission or guest. Output contains
private geometry proof and must never be committed or published.
"""
from pathlib import Path
import importlib.util,json,math,struct,hashlib,zlib,argparse,collections
from fractions import Fraction as F
ap=argparse.ArgumentParser();ap.add_argument('--input',required=True);ap.add_argument('--output',required=True);ap.add_argument('--world-tris',required=True);args=ap.parse_args()
inp=Path(args.input);out=Path(args.output);decoder=Path(args.world_tris)
expected={
'ps2-world.re4mesh':'9dd036b326212d0052d7126f6aaea1c616a304f519933be103fe3c512a92eecd',
'ps2-world.r4pw':'63b76c14a3a0cdc1fefb5d6b4daf56b38c80504d98bd686d2dfb8d74d42ba03b',
'ps2-world.ids':'745d8e8be79e651c078b3850ae856721aa2f5a374a15b5acbb1136a7c1462cb6',
'room.r4rc':'7291b689c4a254c59dc2cad4ef4bf856d42487f00cac907fa4d79e5208ed2f64'}
for name,sha in expected.items():assert hashlib.sha256((inp/name).read_bytes()).hexdigest()==sha,name
assert hashlib.sha256(decoder.read_bytes()).hexdigest()=='71a7a6cb8ff183663bf9e3c54c6d60d0c5f65cd3bda27eda635f9a376f1d14db'
assert not out.exists();out.mkdir()
sp=importlib.util.spec_from_file_location('world',decoder);w=importlib.util.module_from_spec(sp);sp.loader.exec_module(w);pkg=w.Pkg(inp)
p=(inp/'ps2-world.r4pw').read_bytes()
for i in range(len(pkg.pmeta)):
 m=struct.unpack_from('<IIHHBBBB',p,32+16*i)
 if m[7]:pkg.pmeta[i]=(3,m[5]) # no marked/unsupported source corners

def key(t):
 a,b,c=t[:3],t[3:6],t[6:9];return(t[10],t[9],min((a,b,c),(b,c,a),(c,a,b)))
common=set.intersection(*[{key(t) for t in pkg.occluders(k,with_field=True)} for k in range(3)])
def area(poly):return abs(sum(a[0]*b[1]-a[1]*b[0] for a,b in zip(poly,poly[1:]+poly[:1])))
def clip(poly,a,b,inside):
 out=[]
 def d(p):return (b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0])
 for s,e in zip(poly,poly[1:]+poly[:1]):
  ds,de=d(s),d(e);si=ds>=0 if inside else ds<=0;ei=de>=0 if inside else de<=0
  if si:out.append(s)
  if si!=ei:
   t=ds/(ds-de);out.append((s[0]+t*(e[0]-s[0]),s[1]+t*(e[1]-s[1])))
 return out if len(out)>=3 and area(out)>0 else []
def subtract(poly,tri):
 remain=poly;outside=[]
 for a,b in zip(tri,tri[1:]+tri[:1]):
  q=clip(remain,a,b,False)
  if q:outside.append(q)
  remain=clip(remain,a,b,True)
  if not remain:break
 return outside
rows=[]
for field,z0 in [(5,18700),(7,19180)]:
 tris=[];source=[]
 for fld,cull,vs in sorted(common):
  if fld!=field or cull!=2 or any(abs(v[2]-z0)>250 for v in vs):continue
  a,b,c=vs;u=[b[i]-a[i] for i in range(3)];v=[c[i]-a[i] for i in range(3)];n=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]];length=math.sqrt(sum(x*x for x in n))
  if not length or (n[2]/length<.999 or abs(n[1])/length>.01):continue
  tri=[(F(v[0]),F(v[1])) for v in vs]
  if sum(a[0]*b[1]-a[1]*b[0] for a,b in zip(tri,tri[1:]+tri[:1]))<0:tri.reverse()
  tris.append(tri);source.append(vs)
 print('field',field,'source tris',len(tris),flush=True)
 x0=111600 if field==5 else 115700;y0=2300;step=300;covered=set()
 for iy in range(9):
  for ix in range(10):
   x=x0+ix*step;y=y0+iy*step;remain=[[(F(x),F(y)),(F(x+step),F(y)),(F(x+step),F(y+step)),(F(x),F(y+step))]]
   for tri in tris:
    remain=[p for poly in remain for p in subtract(poly,tri)]
    if not remain:break
   if not remain:covered.add((ix,iy))
 # Greedy exact-covered rectangles, no sample-based union proof.
 panels=[]
 while covered:
  best=None
  for ix,iy in sorted(covered):
   for width in range(1,11-ix):
    for height in range(1,10-iy):
     if width*height<2 or (best and width*height<=best[0]):continue
     cells={(x,y) for x in range(ix,ix+width) for y in range(iy,iy+height)}
     if cells<=covered:best=(width*height,ix,iy,width,height,cells)
  if not best:break
  _,ix,iy,width,height,cells=best;covered-=cells
  #100mm tangent inset; normal slab retains250mm legacy allowance.
  l=x0+ix*step+100;rr=x0+(ix+width)*step-100;b=y0+iy*step+100;t=y0+(iy+height)*step-100
  if rr-l<400 or t-b<400:continue
  panels.append({'corners':[[l,b,z0],[rr,b,z0],[rr,t,z0],[l,t,z0]],'half':250,'side':1,'fields':[field],'grid_rectangle':[ix,iy,width,height]})
 rows.append({'field':field,'plane_z':z0,'source_common_triangles':source,'panels':panels,'coverage':'exact rational polygon subtraction; identical cyclic triangles in all three package LOD selections;100mm tangent inset'})
 print('panels',panels,flush=True)
(out/'geometry-proof.json').write_text(json.dumps(rows,indent=2)+'\n')

p=out/'geometry-proof.json';rows=json.loads(p.read_text())
for row in rows:
 for panel in row['panels']:
  xmin,xmax=(110000,114000) if row['field']==5 else (114000,118000)
  ymin=panel['corners'][0][1]-24000;ymax=panel['corners'][0][1]+24000
  for half in range(250,2001,50):
   minfront=1e9
   for a,b,c in row['source_common_triangles']:
    a,b,c=[list(map(F,v)) for v in [a,b,c]];u=[b[i]-a[i] for i in range(3)];v=[c[i]-a[i] for i in range(3)];n=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]];norm=math.sqrt(float(sum(x*x for x in n)))
    for x in [xmin,xmax]:
     for y in [ymin,ymax]:
      e=[F(x),F(y),F(row['plane_z']+half+50)];d=sum(n[i]*(e[i]-a[i]) for i in range(3));minfront=min(minfront,float(d)/norm)
   if minfront>100:break
  assert minfront>100
  panel['half']=half;panel['candidate_cell']=[28 if row['field']==5 else 29,7];panel['frontside_min_mm']=minfront;panel['frontside_eye_box']=[xmin,xmax,ymin,ymax,row['plane_z']+half+50,22000]
  print(row['field'],'half',half,'min',minfront)
p.write_text(json.dumps(rows,indent=2)+'\n')


# Coincident full world vertices share the same quantized coordinate/grid and
# placement. Their emitted positions are identical on both sides of a seam.
# Exact cancellation leaves no patch boundary within100mm of either panel.
for row in rows:
 edges=collections.Counter()
 for a,b,c in row['source_common_triangles']:
  a,b,c=map(tuple,[a,b,c])
  for u,v in [(a,b),(b,c),(c,a)]:
   if edges[v,u]:edges[v,u]-=1
   else:edges[u,v]+=1
 unmatched=[edge for edge,n in edges.items() for _ in range(n)]
 for panel in row['panels']:
  l,b,_=panel['corners'][0];rr,t,_=panel['corners'][2]
  for a,c in unmatched:
   assert not(max(a[0],c[0])>=l-100 and min(a[0],c[0])<=rr+100 and max(a[1],c[1])>=b-100 and min(a[1],c[1])<=t+100)
  panel['unmatched_boundary_clearance_Linf_mm']=100
 row['unmatched_source_edges']=len(unmatched)
 # Absolute operands BEFORE any placement/grid cancellation, over all u16
 # inputs, bind the runtime world gamma/rho envelope to this exact mesh.
 for mi,field,A in pkg.placements:
  if field==row['field']:
   mesh=pkg.meshes[mi]
   operand=[math.ceil(abs(A[a][3])+sum(abs(A[a][c])*(abs(mesh['origin'][c])+abs(mesh['step'][c])*65535) for c in range(3))) for a in range(3)]
   row['absolute_world_operand_bound']=operand
# Bind every certificate edge to the SAME quantized position/grid/placement.
# Retain actual source part/meshlet/triangle alternatives for each selected LOD.
assert [len(row["source_common_triangles"]) for row in rows]==[20,19]
certificate=[]
for row in rows:
 matches=[(mi,A) for mi,field,A in pkg.placements if field==row['field']]
 assert len(matches)==1
 mi,A=matches[0];mesh=pkg.meshes[mi]
 G=[[mesh['step'][0],0,0,mesh['origin'][0]],[0,mesh['step'][1],0,mesh['origin'][1]],[0,0,mesh['step'][2],mesh['origin'][2]]];M=w._mul(A,G)
 vertex_sources={};need={};sources=[]
 wanted={tuple(map(tuple,vs)):i for i,vs in enumerate(row['source_common_triangles'])}
 for level in range(3):
  covered=0
  for part in range(mesh['first_part'],mesh['first_part']+mesh['part_count']):
   if pkg.pmeta[part]!=(0,2):continue
   fc,cc=pkg.plod[part]
   for cluster in range(fc,fc+cc):
    first,count=pkg.clusters[cluster];fm,mc=pkg.levels[first+min(level,count-1)]
    for li in range(fm,fm+mc):
     corners,tris=pkg.let_tris(li)
     world=[[M[r][0]*q[0]+M[r][1]*q[1]+M[r][2]*q[2]+M[r][3] for r in range(3)] for q in corners]
     for ti,(a,b,c) in enumerate(tris):
      vs=min((tuple(world[a]),tuple(world[b]),tuple(world[c])),(tuple(world[b]),tuple(world[c]),tuple(world[a])),(tuple(world[c]),tuple(world[a]),tuple(world[b])))
      if vs not in wanted:continue
      bit=1<<wanted[vs];covered|=bit
      fv,fs,sb,vc,sc=pkg.lets[li];start=pkg.o_strip+fs+(2*vc if sc&0x8000 else 0)
      offset=0;triangle=0
      while triangle+pkg.m[start+offset]-2<=ti:
       n=pkg.m[start+offset];triangle+=n-2;offset+=n+1
      assert offset<sb
      need[part,li,offset]=need.get((part,li,offset),0)|bit
      sources.append({'level':level,'cluster':cluster,'part':part,'meshlet':li,'triangle':ti,'strip_byte_offset':offset,'coverage_bit':wanted[vs]})
      for index in [a,b,c]:
       point=tuple(world[index]);identity=(mi,tuple(corners[index]))
       if point in vertex_sources:assert vertex_sources[point]==identity
       else:vertex_sources[point]=identity
  assert covered==(1<<len(wanted))-1
 row['source_identity']={'mesh':mi,'one_placement':True,'one_grid':True,'world_vertex_to_quantized_identity_bijective':True,'unique_vertices':len(vertex_sources)}
 row['source_triangles_by_lod']=sources
 row['required_meshlet_alternatives']=[{'part':part,'meshlet':li,'strip':offset,'mask':mask} for (part,li,offset),mask in sorted(need.items())]
 for (part,li,offset),mask in sorted(need.items()):certificate.append((row['field'],part,li,offset,mask))
 operand=[sum(abs(F(A[a][c]))*(abs(F(mesh['origin'][c]))+abs(F(mesh['step'][c]))*65535) for c in range(3))+abs(F(A[a][3])) for a in range(3)]
 row['absolute_world_operand_bound']=[(x.numerator+x.denominator-1)//x.denominator for x in operand]
assert [r['absolute_world_operand_bound'] for r in rows]==[[114546,6015,19155],[118646,6015,19630]]
header='\n'.join(['#pragma once','#include <cstdint>','namespace actor_visibility23::r119 {','struct Need {unsigned short field,part,meshlet,strip;std::uint32_t mask;};','inline constexpr Need needs[]={']+['{%d,%d,%d,%d,0x%xU},'%x for x in certificate]+['};','inline constexpr unsigned full[]={0xfffffU,0x7ffffU};','inline constexpr float operands[]={118646,6015,19630};','}'])+'\n'
(out/'actor_visibility23_r119_certificate.h').write_text(header)

p.write_text(json.dumps(rows,indent=2)+'\n')

proof=json.loads((out/'geometry-proof.json').read_text());panels=[p for row in proof for p in row['panels']];old=(inp/'room.r4rc').read_bytes();n=struct.unpack_from('<I',old,12)[0];secs=[]
for i in range(n):
 rec=list(struct.unpack_from('<4sHH6I',old,64+i*32));secs.append((rec,old[rec[3]:rec[3]+rec[4]]))
rec,oc=next(x for x in secs if x[0][0]==b'OCCL');vw,vh,div=struct.unpack_from('<3H',oc);crc=struct.unpack_from('<I',oc,12)[0];assert crc==0xfb5072f8
np=len(panels);new=struct.pack('<6HIHHHH8x',vw,vh,div,np,np,2400,crc,np,300,100,np)
for i,p in enumerate(panels):new+=struct.pack('<13fbBH',*[v for xyz in p['corners'] for v in xyz],p['half'],p['side'],1,i)
cells=bytearray(4*vw*vh)
for i,panel in enumerate(panels):
 cx,cz=panel['candidate_cell'];assert 0<=cx<vw and 0<=cz<vh
 struct.pack_into('<HBB',cells,4*(cz*vw+cx),i,1,0)
new+=cells+struct.pack('<'+str(np)+'H',*range(np))+struct.pack('<'+str(np)+'H',*[p['fields'][0] for p in panels]);assert len(new)==32+56*np+4*vw*vh+4*np
certificate_header=out/'actor_visibility23_r119_certificate.h'
certificate_header.write_text(certificate_header.read_text()+'#define ACTOR_VISIBILITY23_OCCL_CRC 0x%08xU\n'%zlib.crc32(new))
head=bytearray(old[:64]);body=bytearray(b'\0'*(32*n));offset=64+len(body)
newsecs=[]
for i,(rec,data) in enumerate(secs):
 if rec[0]==b'OCCL':data=new;rec[5]=np;rec[6]=56
 pad=(-offset)%16;body+=bytes(pad);offset+=pad;rec[3]=offset;rec[4]=len(data);body[i*32:i*32+32]=struct.pack('<4sHH6I',*rec);body+=data;offset+=len(data);newsecs.append({'tag':rec[0].decode().rstrip(chr(0)),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
struct.pack_into('<I',head,16,64+len(body));struct.pack_into('<I',head,48,zlib.crc32(body));candidate=bytes(head)+body
(out/'room.r4rc').write_bytes(candidate);(out/'OCCL.bin').write_bytes(new);(out/'geometry-proof.json').write_text(json.dumps(proof,indent=2))
receipt={'kind':'PRIVATE METADATA CANDIDATE; NOT ADMITTED / NO GUEST','input_binding':json.loads((inp/'binding.json').read_text()),'runtime_logical_crc':hex(crc),'physical_r4pw_crc':'0xa79895c4','panels':panels,'sections':newsecs,'output_bytes':len(candidate),'output_sha256':hashlib.sha256(candidate).hexdigest(),'admission_pending':['actual world numeric cohort bridge / source review','current dynamic/source/current camera/fog integration and matched pixel controls'],'preserved_sections_byte_identical':[x['tag'] for x in newsecs if x['tag']!='OCCL']}
(out/'candidate.json').write_text(json.dumps(receipt,indent=2));print(json.dumps({k:v for k,v in receipt.items() if k not in ['input_binding','panels']},indent=2));print('header',struct.unpack_from('<4sHH4IHHIii2fI',candidate))
