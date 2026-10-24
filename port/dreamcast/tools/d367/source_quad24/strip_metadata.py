"""Targeted SOURCE metadata only. DEFAULT no private reads; no occlusion calls.
No builder, asset output, whole scene discovery, sourcePanel or runtime path.
"""
import argparse
from fractions import Fraction as Q
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import stat
import struct
import subprocess
import time
import zlib

FORMAT_SOURCE='64f256b083f734dfc685cdcf0ad244867fb57a18'
INTEGRATION='fb254e82ee6f9a3d9e34d53d1d442348a46b9cf2'
FORMAT_PINS={
 'port/dreamcast/room/instanced_mesh.hpp':'e9f0d7fd0bd977b1aa9334a5718dcfb9d93e6c5616fecc8f11bdcadfca5db019',
 'port/dreamcast/room/room_package.hpp':'0f68e9b943e018af1c1b67022d2f5774fed8f829c3a4e094b52fceccac9aa0fe',
 'port/dreamcast/game/platform/native_static.cpp':'e23dda292ae37aff409bd66228c0a2edf80c27536ba477b9b9a51c1cc19113eb',
 'port/dreamcast/tools/ps2_strip_groups.py':'c89c4700b98dc4cb572f2c916df6058a749d900aed388c44a1d3dcc606b5efd6'}
RAW_BASE='/mnt/c/Flycast-Evidence/re4-dreamcast/interior-vis23-20261023/'
INPUT_BASE=RAW_BASE+'I001-fb254-lod-surface-r6/prepared/inputs/'
RAW={
 'mesh':(INPUT_BASE+'ps2-world.re4mesh',793216,'31ec2e15faca0f171b1ae94290ecc22153eb06d256b6b6ef965bde3315f674b1'),
 'policy':(INPUT_BASE+'ps2-world.r4pw',16448,'27a3dc3980df13f4dcaf97186e919821e6e0ebd6aa74ded1695c03b6d92b916b'),
 'original_policy':(INPUT_BASE+'original.r4pw',16448,'dccc680b038d7da2e299a1f518ea440c4793f504d34b14a1217c7944f74d3e70'),
 'ids':(INPUT_BASE+'ps2-world.ids',256,'8999b49ce73627e5b62d50f07f0936552c7c7645713e4183078577f3ca5189ba'),
 'coverage':(RAW_BASE+'original-chunks75-private-root-r1/report.json',6658809,'3de238f0ab60d055e22bfc68e7ef3a32aac813751ad5941487ceab37068c2037'),
 'prepared':(RAW_BASE+'triangle-partition24-private-plan-r3/report.json',4891119,'24ef9acac6f1b616f832aa7a1cd36cce656cccb8ac51f4efa3e2f3e049bda324')}
ALLOWLIST=((0, 121, 121, 186, 190, 0, 812, 32), (1, 123, 123, 188, 192, 0, 822, 48), (2, 91, 91, 159, 163, 1, 725, 4), (3, 195, 195, 254, 258, 0, 1005, 4), (4, 128, 128, 195, 199, 0, 831, 55), (5, 217, 217, 275, 279, 0, 1046, 38), (6, 94, 94, 161, 165, 0, 736, 32), (7, 166, 166, 161, 165, 0, 736, 32), (8, 94, 94, 161, 165, 0, 735, 40), (9, 166, 166, 161, 165, 0, 735, 40), (10, 91, 91, 160, 164, 1, 733, 45), (11, 128, 128, 195, 199, 0, 834, 60), (12, 127, 127, 194, 198, 0, 829, 80), (13, 127, 127, 194, 198, 0, 830, 64), (14, 194, 194, 253, 257, 0, 1003, 24), (15, 155, 155, 221, 225, 0, 908, 71), (16, 156, 156, 222, 226, 0, 909, 64), (17, 128, 128, 195, 199, 0, 835, 46), (18, 94, 94, 161, 165, 0, 737, 20), (19, 166, 166, 161, 165, 0, 737, 20), (20, 209, 209, 268, 272, 0, 1022, 22), (21, 221, 221, 278, 282, 1, 1053, 14), (22, 194, 194, 252, 256, 1, 1002, 16), (23, 91, 91, 160, 164, 1, 734, 14), (24, 217, 217, 275, 279, 0, 1047, 4))
PROFILE='ORIGINAL_STRIP_METADATA_25_V1'
LIMITS=dict(targets=25,originals=889,corner_records=6400,strips=4096,index_bytes=262144,
            enclosing_let_records=4096,part_levels=1024,input_bytes=12582912,
            compute_seconds=30,wall_seconds=45,address_bytes=268435456,output_bytes=4194304,tail_bytes=65536,jobs=1)
OWN=('strip_metadata.py','test_strip_metadata.py','STRIP-METADATA.md')

class Refuse(ValueError):pass

def sha(raw):return hashlib.sha256(raw).hexdigest()
def token(value):return sha(json.dumps(value,sort_keys=True,separators=(',',':')).encode())
def check(deadline):
 if time.monotonic()>=deadline:raise Refuse('COMPUTE_DEADLINE')
def extent(off,n,width,size,head=0):
 if any(type(x)is not int or x<0 for x in (off,n,width,size,head)) or off<head or off>size or n>(size-off)//max(width,1) or width==0:
  raise Refuse('OFFSET_EXTENT')
 return off+n*width

def uq(x):
 x=Q(x)
 if max(x.numerator.bit_length(),x.denominator.bit_length())>256:raise Refuse('EXACT_OPERAND_BITS')
 return x

def serialize(v):
 if type(v) in (str,int):return v
 if type(v)is Q:return str(v)
 if type(v)is tuple:return [serialize(x) for x in v]
 raise Refuse('INVENTORY_SERIALIZATION')

def digest(parents,binding):
 raw=json.dumps(serialize((binding,tuple(parents))),separators=(',',':')).encode('ascii')
 if len(raw)>1048576:raise Refuse('INVENTORY_BYTES')
 return sha(raw)

def header(data):
 if type(data)is not bytes or len(data)<112:raise Refuse('MESH_HEADER')
 h=struct.unpack_from('<4s19I',data)
 if h[0]!=b'R4IM' or h[1]not in (2,3) or h[2]!=len(data) or h[16]!=2 or h[19]!=0:raise Refuse('MESH_PROFILE_ENCODING')
 if zlib.crc32(data[80:])&0xffffffff!=h[3]:raise Refuse('MESH_CRC')
 for count,off,width in zip(h[4:10],h[10:16],(68,36,28,12,1,4)):extent(off,count,width,len(data),112)
 if not 1<=h[9]<=16:raise Refuse('PALETTE')
 lod=struct.unpack_from('<8I',data,80)
 for off,count,width in ((lod[2],h[5],8),(lod[3],lod[0],20),(lod[4],lod[1],12)):extent(off,count,width,len(data),112)
 if lod[5]:extent(lod[5],h[4],1,len(data),112)
 if lod[6]:extent(lod[6],8,4,len(data),112)
 return h,lod

def policy_header(data,h):
 if type(data)is not bytes or len(data)<32:raise Refuse('POLICY_HEADER')
 p=struct.unpack_from('<4s7I',data)
 if p[0]!=b'R4PW' or p[1]!=1 or p[3]!=h[5] or p[4]!=h[4] or 32+16*p[3]+52*p[2]!=len(data):raise Refuse('POLICY_EXTENT_IDENTITY')
 if zlib.crc32(data[32:])&0xffffffff!=p[5]:raise Refuse('POLICY_CRC')
 return p

def let_record(data,h,li):
 if type(li)is not int or not 0<=li<h[6]:raise Refuse('LET_ID')
 off=h[12]+28*li;l=struct.unpack_from('<IIIHH6H',data,off);fv,fs,sb,n,sc=l[:5];indexed=bool(sc&32768)
 if not 1<=n<=256 or fv>=h[7] or (indexed and h[1]!=3) or (indexed and fs&1):raise Refuse('LET_ENCODING')
 extent(fs,(2*n if indexed else 0)+sb,1,h[8])
 if not indexed:extent(fv,n,1,h[7])
 return l,off,indexed

def decode(data,h,li,owned_ranges):
 l,off,indexed=let_record(data,h,li);fv,fs,sb,n,sc=l[:5];table_bytes=2*n if indexed else 0
 pool=struct.unpack_from('<%dH'%n,data,h[14]+fs) if indexed else tuple(range(n))
 for index in pool:
  v=fv+index
  if v>=h[7] or not any(lo<=v<hi for lo,hi in owned_ranges):raise Refuse('PART_VERTEX_POOL_IDENTITY')
 begin=h[14]+fs+table_bytes;end=begin+sb;pos=begin;strips=[];triangles=[];native=[];occ=[];boundaries={0}
 while pos<end:
  start=pos-begin;count=data[pos];pos+=1
  if count<3 or count>end-pos:raise Refuse('STRIP_LENGTH')
  indices=tuple(data[pos:pos+count]);pos+=count
  if any(i>=n for i in indices):raise Refuse('STRIP_LOCAL_INDEX')
  if len(strips)>=LIMITS['strips']:raise Refuse('STRIP_COUNT_CAP')
  strips.append(dict(ordinal=len(strips),byte_start=start,byte_end=pos-begin,indices=indices,restart=True))
  for k in range(count-2):
   a,b,c=indices[k:k+3];ref=(a,b,c) if k%2==0 else (c,b,a);nt=(a,b,c) if k%2==0 else (b,a,c)
   if len(triangles)>=LIMITS['originals']:raise Refuse('ORIGINAL_OCCURRENCE_CAP')
   triangles.append(ref);native.append(nt);occ.append((len(strips)-1,k,bool(k&1)))
  boundaries.add(pos-begin)
 if len(strips)!=(sc&32767):raise Refuse('STRIP_COUNT')
 corners=tuple(struct.unpack_from('<6H',data,h[13]+12*(fv+i)) for i in pool)
 return dict(record=l,record_offset=off,indexed=indexed,pool_offsets=tuple(pool),global_vertex_indices=tuple(fv+i for i in pool),
             table_bytes=table_bytes,strip_begin=begin,strip_bytes=sb,strips=tuple(strips),triangles=tuple(triangles),native=tuple(native),occurrences=tuple(occ),
             corners=corners,boundaries=boundaries)

def owner(data,h,lod,policy,p,physical):
 pi,field,part,cluster,level,li=physical
 if not 0<=pi<p[2] or not 0<=part<h[5] or not 0<=cluster<lod[0]:raise Refuse('PHYSICAL_OWNER_RANGE')
 po=32+16*p[3]+52*pi;pl=struct.unpack_from('<HH12f',policy,po);mi=pl[0]
 if mi>=h[4] or pl[1]!=field or not all(math.isfinite(f) for f in pl[2:]):raise Refuse('PLACEMENT_IDENTITY')
 mo=h[10]+68*mi;mr=struct.unpack_from('<HBBHHIII12f',data,mo)
 if not mr[6]<=part<mr[6]+mr[7] or mr[6]+mr[7]>h[5]:raise Refuse('PART_OWNER')
 pro=h[11]+36*part;pr=struct.unpack_from('<IIBBBBII4f',data,pro)
 if pr[5]!=0 or pr[6]+pr[7]>h[6] or not pr[6]<=li<pr[6]+pr[7]:raise Refuse('LET_PART_OWNER')
 if pr[7]>LIMITS['enclosing_let_records']:raise Refuse('ENCLOSING_PART_CAP')
 first,nc=struct.unpack_from('<II',data,lod[2]+8*part)
 if first+nc>lod[0] or not first<=cluster<first+nc:raise Refuse('CLUSTER_PART_OWNER')
 cl=struct.unpack_from('<6HII',data,lod[3]+20*cluster);fl,nl=cl[6:]
 if not 1<=nl<=LIMITS['part_levels'] or fl+nl>lod[1] or not 0<=level<nl:raise Refuse('LEVEL_OWNER')
 levels=tuple(struct.unpack_from('<IIf',data,lod[4]+12*(fl+i)) for i in range(nl))
 if any(start+count>h[6] or not math.isfinite(error) for start,count,error in levels):raise Refuse('LEVEL_EXTENT')
 if not levels[level][0]<=li<levels[level][0]+levels[level][1]:raise Refuse('LET_EFFECTIVE_LEVEL_OWNER')
 # Only enclosing part metadata, not other scene geometry. Indexed references
 # must point into one of this part's actual non-indexed backing ranges.
 ranges=[]
 for index in range(pr[6],pr[6]+pr[7]):
  lr,_,ix=let_record(data,h,index)
  if not ix:ranges.append((lr[0],lr[0]+lr[3]))
 if not ranges:raise Refuse('NO_AUTHENTICATED_PART_BACKING')
 operands=policy[po+4:po+52]+data[mo+20:mo+44]
 if len(operands)!=72:raise Refuse('AFFINE_OPERAND_BYTES')
 floats=struct.unpack('<18f',operands)
 if not all(math.isfinite(f) for f in floats) or not all(f>0 for f in floats[15:18]):raise Refuse('AFFINE_GRID')
 exact=tuple(uq(x) for x in floats);af=tuple(exact[4*i:4*i+4] for i in range(3));org=exact[12:15];step=exact[15:18]
 det=uq(af[0][0]*(af[1][1]*af[2][2]-af[1][2]*af[2][1])-af[0][1]*(af[1][0]*af[2][2]-af[1][2]*af[2][0])+af[0][2]*(af[1][0]*af[2][1]-af[1][1]*af[2][0]))
 if det==0:raise Refuse('SINGULAR_AFFINE')
 def world(corner):
  xyz=tuple(uq(org[k]+uq(step[k]*corner[k])) for k in range(3))
  return tuple(uq(af[i][3]+sum((uq(af[i][k]*xyz[k]) for k in range(3)),Q(0))) for i in range(3))
 return dict(placement_offset=po,mesh_index=mi,mesh_offset=mo,part_offset=pro,part_record=pr,levels=levels,
             ranges=tuple(ranges),operands=operands,affine_sha256=sha(operands),world=world)

def parse_sg(data,h,policy_crc,decoded,li):
 """PUBLIC optional parser only; CLI has NO authenticated actualSG path to read."""
 if type(data)is not bytes or len(data)<32 or len(data)>262144:raise Refuse('SG_SIZE')
 w=struct.unpack_from('<4s7I',data)
 if w[0]!=b'R4SG' or w[1]!=1 or w[2]!=h[6] or not 1<=w[3]<=8 or w[4]!=h[3] or w[5]!=h[2] or w[6]!=policy_crc or len(data)!=32+16*w[2]*w[3] or zlib.crc32(data[32:])&0xffffffff!=w[7]:raise Refuse('SG_HEADER')
 if not 0<=li<h[6]:raise Refuse('SG_LET_ID')
 prev=0;result=[]
 for index in range(w[3]):
  off=32+16*(li*w[3]+index);g=struct.unpack_from('<8H',data,off);end=g[6];lo=g[7]&255;hi=g[7]>>8
  if end<prev or end>decoded['strip_bytes'] or prev not in decoded['boundaries'] or end not in decoded['boundaries']:raise Refuse('SG_STRIP_BOUNDARY')
  if end!=prev:
   if lo>hi or hi>=len(decoded['corners']) or any(g[k]>g[k+3] for k in range(3)):raise Refuse('SG_CORNER_RANGE')
   for strip in decoded['strips']:
    if prev<=strip['byte_start']<end:
     for v in strip['indices']:
      if not lo<=v<=hi or any(not g[k]<=decoded['corners'][v][k]<=g[k+3] for k in range(3)):raise Refuse('SG_INPUT_ENCLOSURE')
  result.append(dict(record_bytes=data[off:off+16].hex(),strip_start=prev,strip_end=end,empty=end==prev,corner_lo=lo,corner_hi=hi));prev=end
 if prev!=decoded['strip_bytes']:raise Refuse('SG_COMPLETE_STRIPS')
 return tuple(result)

def target(mesh,h,lod,policy,p,original,ids,t):
 physical=tuple(t['physical']);o=owner(mesh,h,lod,policy,p,physical);d=decode(mesh,h,physical[-1],o['ranges'])
 if tuple(t['authored_counts'])!=tuple(row[1] for row in o['levels']):raise Refuse('ORIGINAL_LOD_COUNTS')
 if o['operands'].hex()!=t['affine_operand_bytes_hex'] or o['affine_sha256']!=t['affine_sha256']:raise Refuse('ORIGINAL_AFFINE_BINDING')
 if not 0<=physical[1]<len(ids) or ids[physical[1]]!=t['original_target']['owner']:raise Refuse('OWNER_IDS')
 parents=t['parents'];xyz=tuple(o['world'](v) for v in d['corners']);records=[];decoded=[]
 if len(parents)!=len(d['triangles']):raise Refuse('COMPLETE_ORIGINAL_OCCURRENCES')
 for ordinal,(tri,expected) in enumerate(zip(d['triangles'],parents)):
  occurrence=(*physical,ordinal);positions=tuple(xyz[i] for i in tri)
  if tuple(expected['occurrence'])!=occurrence or tuple(expected['indices'])!=tri or expected['affine_sha256']!=o['affine_sha256'] or tuple(tuple(Q(v) for v in pt) for pt in expected['positions_exact'])!=positions:raise Refuse('ORIGINAL_WINDING_INDICES_AFFINE_POSITIONS')
  records.append((occurrence,tri,o['affine_sha256'],positions))
  decoded.append(dict(occurrence=occurrence,indices=tri,native_cyclic_indices=d['native'][ordinal],strip_position=d['occurrences'][ordinal],repeated_index_degenerate=len(set(tri))<3))
 actual=digest(tuple(records),t['source_binding_sha256'])
 if actual!=t['original_inventory_sha256']:raise Refuse('COMPLETE_ORIGINAL_INVENTORY_DIGEST')
 part=physical[2];meta_off=32+16*part;meta=struct.unpack_from('<IIHH4B',policy,meta_off)
 if meta[4]>2 or meta[5]>2 or not 1<=meta[2]<=1024 or not 1<=meta[3]<=1024:raise Refuse('MATERIAL_DESCRIPTOR')
 lv=d['record'];fv=lv[0]
 corners=tuple(dict(local=i,global_pool=fv+pool,bytes=mesh[h[13]+12*(fv+pool):h[13]+12*(fv+pool+1)].hex(),quantized=corner) for i,(pool,corner) in enumerate(zip(d['pool_offsets'],d['corners'])))
 return dict(rank=t['rank'],physical=physical,original_inventory_sha256=actual,affine72_bytes=o['operands'].hex(),affine_sha256=o['affine_sha256'],owner=ids[physical[1]],
             source_header_offsets=dict(mesh=o['mesh_offset'],part=o['part_offset'],meshlet=d['record_offset'],material=meta_off,placement=o['placement_offset']),placement_bytes=policy[o['placement_offset']:o['placement_offset']+52].hex(),mesh_record_bytes=mesh[o['mesh_offset']:o['mesh_offset']+68].hex(),
             mesh_part_bytes=mesh[o['part_offset']:o['part_offset']+36].hex(),meshlet_bytes=mesh[d['record_offset']:d['record_offset']+28].hex(),
             material=dict(record_offset=meta_off,policy_bytes=policy[meta_off:meta_off+16].hex(),original_policy_bytes=original[meta_off:meta_off+16].hex(),crc=meta[0],fnv=meta[1],width=meta[2],height=meta[3],pass_=meta[4],cull=meta[5],texture=meta[6],reserved=meta[7],runtime_header_commit='UNQUALIFIED'),
             enclosing_let_record_visits=o['part_record'][7],enclosing_level_records=len(o['levels']),effective_level=physical[4],authored_levels=o['levels'],indexed=d['indexed'],pool_offsets=d['pool_offsets'],corners=corners,strips=d['strips'],originals=tuple(decoded),
             source_bytes=dict(meshlet_header=28,part_header=36,material_record=16,placement=52,strip_stream=d['strip_bytes'],pool_offset_table=d['table_bytes'],corner_reference_slots=len(corners)),
             spans=dict(strip=(d['strip_begin'],d['strip_begin']+d['strip_bytes']),pool_table=(h[14]+lv[1],h[14]+lv[1]+d['table_bytes']),vertices=tuple((h[13]+12*i,h[13]+12*(i+1)) for i in d['global_vertex_indices'])),
             optional_strip_groups=None,optional_strip_groups_reason='NO_AUTHENTICATED_SIDECAR_PIN_IN_INSPECTED_MANIFESTS',actual_selected_groups=None,
             current_transform_corners=None,modelled_ms=None,runtime_admitted=False)

def extract(mesh,policy,original,ids,report,allowlist,deadline):
 h,lod=header(mesh);p=policy_header(policy,h);po=policy_header(original,h)
 if po[2:5]!=p[2:5] or len(ids)!=256:raise Refuse('POLICY_IDENTITY')
 ts=report['targets']
 if not 1<=len(ts)<=25 or len({tuple(t['physical']) for t in ts})!=len(ts):raise Refuse('COMPLETE_UNIQUE_TARGET_ROSTER')
 if tuple((t['rank'],*t['physical'],len(t['parents'])) for t in ts)!=tuple(allowlist):raise Refuse('FIXED_TARGET_ALLOWLIST')
 rows=[];corner_count=strip_count=index_bytes=original_count=let_visits=level_records=0
 for t in ts:
  check(deadline);row=target(mesh,h,lod,policy,p,original,ids,t)
  corner_count+=len(row['corners']);strip_count+=len(row['strips']);index_bytes+=sum(len(s['indices']) for s in row['strips']);original_count+=len(row['originals'])
  let_visits+=row['enclosing_let_record_visits'];level_records+=row['enclosing_level_records']
  if let_visits>LIMITS['enclosing_let_records'] or level_records>LIMITS['part_levels'] or original_count>LIMITS['originals']:raise Refuse('WHOLE_ENCLOSING_ORIGINAL_CAP')
  if corner_count>LIMITS['corner_records'] or strip_count>LIMITS['strips'] or index_bytes>LIMITS['index_bytes']:raise Refuse('WHOLE_TARGET_RECORD_CAP')
  rows.append(row)
 check(deadline)
 return dict(classification='ORIGINAL_STRIP_MATERIAL_METADATA_ONLY',targets=tuple(rows),target_count=len(rows),original_occurrences=original_count,
             physical_corner_records=corner_count,physical_strip_records=strip_count,physical_index_bytes=index_bytes,
             source_headers=dict(mesh_header_bytes=mesh[:112].hex(),policy_header_bytes=policy[:32].hex(),original_policy_header_bytes=original[:32].hex()),
             selected_source_storage=dict(unique_strip_stream_bytes=union_bytes(row['spans']['strip'] for row in rows),
                 unique_index_table_bytes=union_bytes(row['spans']['pool_table'] for row in rows),
                 unique_compact_vertex_bytes=union_bytes(span for row in rows for span in row['spans']['vertices']),
                 physical_compact_corner_reference_bytes=12*corner_count,
                 unique_meshlet_header_bytes=28*len({row['source_header_offsets']['meshlet'] for row in rows}),
                 unique_part_header_bytes=36*len({row['source_header_offsets']['part'] for row in rows}),
                 unique_material_record_bytes=16*len({row['source_header_offsets']['material'] for row in rows}),
                 new_runtime_representation=None),
             optional_sg='UNAVAILABLE_NO_PIN',actual_transform_delta=None,actual_header_delta=None,modelled_ms=None,yield_gate='UNESTABLISHED',runtime_admitted=False)

def union_bytes(ranges):
 ranges=sorted((lo,hi) for lo,hi in ranges if hi>lo)
 end=0;total=0
 for lo,hi in ranges:
  if lo<0 or hi<lo:raise Refuse('SOURCE_SPAN')
  total+=max(0,hi-max(lo,end));end=max(end,hi)
 return total

def signature_runs(row,signature,allowed_mask):
 """Describe EXISTING source strip windows only. NO candidate encoding/emission."""
 n=len(row['originals']);masks=[None]*n
 if type(allowed_mask)is not int or not 0<=allowed_mask<=7:raise Refuse('ALLOWED_DOMAIN_MASK')
 seen_masks=set()
 for group in signature['groups']:
  mask=group['mask'];ordinals=group['ordinals'];indices=group['original_oriented_indices']
  if type(mask)is not int or mask in seen_masks or mask<0 or mask>7 or mask&~allowed_mask or not ordinals or len(ordinals)!=len(indices):raise Refuse('SIGNATURE_DOMAIN_GROUP')
  seen_masks.add(mask)
  for ordinal,tri in zip(ordinals,indices):
   if type(ordinal)is not int or not 0<=ordinal<n or masks[ordinal]is not None or tuple(tri)!=tuple(row['originals'][ordinal]['indices']):raise Refuse('SIGNATURE_ORIGINAL_BIJECTION')
   masks[ordinal]=mask
 if any(x is None for x in masks):raise Refuse('INCOMPLETE_SIGNATURE_ORIGINALS')
 by_strip={}
 for original,mask in zip(row['originals'],masks):by_strip.setdefault(original['strip_position'][0],[]).append((original,mask))
 runs=[];domain=[]
 for strip in row['strips']:
  seq=by_strip[strip['ordinal']]
  if tuple(x['strip_position'][1] for x,m in seq)!=tuple(range(len(strip['indices'])-2)):raise Refuse('SOURCE_STRIP_OCCURRENCE_ORDER')
  first=0
  while first<len(seq):
   last=first+1
   while last<len(seq) and seq[last][1]==seq[first][1]:last+=1
   runs.append(dict(source_strip=strip['ordinal'],mask=seq[first][1],original_ordinals=tuple(x['occurrence'][-1] for x,m in seq[first:last]),
                    source_triangle_first=first,source_triangle_count=last-first,source_start_parity=bool(first&1),
                    source_corner_window=strip['indices'][first:last+2],source_corner_window_references=last-first+2,
                    emitted_representation=None,winding_restart_handling='NOT_DESIGNED'))
   first=last
 for bit in range(3):
  whole=mixed=any_draw=covered_references=0;retained=set();covered=set()
  for strip in row['strips']:
   seq=by_strip[strip['ordinal']];flags=[bool(mask&(1<<bit)) for _,mask in seq]
   whole+=int(all(flags));mixed+=int(any(flags) and not all(flags));any_draw+=int(not all(flags))
   if all(flags):covered_references+=len(strip['indices'])
   for (original,mask),hidden in zip(seq,flags):(covered if hidden else retained).update(original['indices'])
  domain.append(dict(domain_index=bit,fully_nominally_covered_source_strips=whole,mixed_source_strips=mixed,source_strips_with_any_retained_originals=any_draw,
                     index_references_in_fully_covered_source_strips=covered_references,exclusive_covered_local_slots=tuple(sorted(covered-retained)),
                     actual_transform_delta=None,actual_header_delta=None,modelled_ms=None))
 return dict(original_signature_masks=tuple(masks),source_strip_signature_runs=tuple(runs),signature_run_count=len(runs),
             boundaries_inside_existing_strips=len(runs)-len(row['strips']),source_corner_window_references=sum(r['source_corner_window_references'] for r in runs),
             source_window_count_is_not_encoded_or_transformed_cost=True,domains=tuple(domain),runtime_admitted=False)

def attach_coverage(result,coverage,prepared):
 if coverage.get('source')!='b99aa45028038ad6ad9374819358412d9f66f09b' or coverage.get('profile')!='SOURCE_QUAD24_ORIGINAL_TRIANGLE_PARTITIONS_FINITE75_V1' or coverage.get('halt')is not None or len(coverage['results'])!=75 or len(coverage['signatures'])!=25:raise Refuse('FROZEN_COMPLETE_COVERAGE_PROFILE')
 allowed=0
 if tuple(d['size_mm'] for d in coverage['domains'])!=(2000,500,250):raise Refuse('ORDERED_COVERAGE_DOMAINS')
 for i,d in enumerate(coverage['domains']):
  if d['status']=='NOMINAL_CELL_UNION_ONLY':
   deps=d['global_full_panel_dependencies']
   if not d['all25_complete'] or type(deps)is not list or len(deps)>16 or len(set(deps))!=len(deps):raise Refuse('GLOBAL_COVERAGE_DEPENDENCIES')
   allowed|=1<<i
 targets={t['rank']:t for t in prepared['targets']};signatures={g['rank']:g for g in coverage['signatures']}
 if set(targets)!=set(range(25)) or set(signatures)!=set(targets):raise Refuse('EXACT_COVERAGE_TARGETS')
 seen=set()
 for row in coverage['results']:
  case=row['case'];key=tuple(case)
  if len(case)!=10 or key in seen or case[0]not in targets or tuple(case[1:7])!=tuple(targets[case[0]]['physical']) or tuple(case[-3:-1])!=('hut',647) or case[-1]not in (2000,500,250):raise Refuse('EXACT_COVERAGE_CASES')
  seen.add(key)
  if row.get('complete_originals')!=len(targets[case[0]]['parents']) or row.get('inventory_sha256')!=targets[case[0]]['original_inventory_sha256'] or row.get('partial_discarded') or not row.get('started'):raise Refuse('COMPLETE_COVERAGE_INVENTORY')
 for row in result['targets']:row['nominal_fragmentation']=signature_runs(row,signatures[row['rank']],allowed)
 return dict(source=coverage['source'],report_sha256=RAW['coverage'][2],classification='FROZEN_NOMINAL_METADATA_NO_RUNTIME_ADMISSION',allowed_domain_mask=allowed,
             total_source_signature_runs=sum(r['nominal_fragmentation']['signature_run_count'] for r in result['targets']),
             boundaries_inside_existing_strips=sum(r['nominal_fragmentation']['boundaries_inside_existing_strips'] for r in result['targets']),
             actual_encoded_header_delta=None,actual_transform_delta=None,modelled_ms=None)

def read_pin(pin):
 path,size,expected=pin
 fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
 try:
  before=os.fstat(fd)
  if not stat.S_ISREG(before.st_mode) or before.st_size!=size or size>LIMITS['input_bytes']:raise Refuse('PIN_SIZE_TYPE')
  chunks=[];left=size+1
  while left:
   block=os.read(fd,min(left,1048576))
   if not block:break
   chunks.append(block);left-=len(block)
  raw=b''.join(chunks);after=os.fstat(fd)
  if (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)!=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns) or len(raw)!=size or sha(raw)!=expected:raise Refuse('PIN_BYTES_OR_STAMP_CHANGED')
  return raw
 finally:os.close(fd)

def own_sources(repo,source):
 if type(source)is not str or len(source)!=40 or any(x not in '0123456789abcdef' for x in source):raise Refuse('EXACT_SOURCE_COMMIT')
 folder=Path(__file__).resolve().parent;pins={}
 for name in OWN:
  path=folder/name;rel=path.relative_to(repo.resolve()).as_posix();raw=path.read_bytes()
  if raw!=subprocess.check_output(['git','-C',str(repo),'show',source+':'+rel]):raise Refuse('OWN_SOURCE_DRIFT')
  pins[name]=sha(raw)
 for path,expected in FORMAT_PINS.items():
  raw=subprocess.check_output(['git','-C',str(repo),'show',FORMAT_SOURCE+':'+path])
  if sha(raw)!=expected:raise Refuse('FORMAT_SOURCE_DRIFT')
 return pins

def grant_binding(source,review_sha,out):
 return dict(issuer='/root',approved=True,scope='ORIGINAL_STRIP_METADATA_FIXED25_ONLY',profile=PROFILE,source=source,review_sha256=review_sha,
             format_source=FORMAT_SOURCE,integration=INTEGRATION,format_pins=FORMAT_PINS,raw_inputs=RAW,allowlist=ALLOWLIST,limits=LIMITS,
             output=str(out.resolve()),private_occlusion_predicates=0,new_rays=0,runtime_admitted=False,optional_sg='UNAVAILABLE_NO_PIN')

def authorize(args):
 if any(v is None for v in (args.grant,args.grant_sha256,args.review,args.review_sha256)):raise Refuse('NEW_ROOT_GRANT_AND_REVIEW_REQUIRED')
 grant=read_pin((str(args.grant),args.grant.stat().st_size,args.grant_sha256));read_pin((str(args.review),args.review.stat().st_size,args.review_sha256))
 if token(json.loads(grant))!=token(grant_binding(args.expected_source,args.review_sha256,args.out)):raise Refuse('ROOT_GRANT_SCOPE_SOURCE_INPUTS_CAPS_MISMATCH')

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--repo',type=Path,required=True);ap.add_argument('--expected-source',required=True);ap.add_argument('--out',type=Path,required=True)
 ap.add_argument('--execute',action='store_true');ap.add_argument('--grant',type=Path);ap.add_argument('--grant-sha256');ap.add_argument('--review',type=Path);ap.add_argument('--review-sha256')
 args=ap.parse_args();start=time.monotonic();resource.setrlimit(resource.RLIMIT_AS,(268435456,)*2)
 if args.out.exists() or args.out.resolve().is_relative_to(args.repo.resolve()) or any(args.out.resolve().is_relative_to(Path(x[0]).parent.resolve()) for x in RAW.values()):raise Refuse('EXCLUSIVE_EXTERNAL_OUTPUT')
 pins=own_sources(args.repo,args.expected_source)
 result=dict(classification='HELD_SOURCE_ONLY_ZERO_PRIVATE_READS',source=args.expected_source,profile=PROFILE,source_pins=pins,limits=LIMITS,
             grant_template=grant_binding(args.expected_source,'<independent-review-sha256>',args.out),private_input_reads=0,private_occlusion_predicates=0,new_rays=0,runtime_admitted=False)
 if args.execute:
  authorize(args)
  try:
   if sum(x[1] for x in RAW.values())>LIMITS['input_bytes']:raise Refuse('WHOLE_INPUT_CAP')
   buffers={}
   for name,pin in RAW.items():
    check(start+30);result['private_input_read_attempts']=result.get('private_input_read_attempts',0)+1
    buffers[name]=read_pin(pin);result['private_input_reads']+=1
   report=json.loads(buffers.pop('prepared'));coverage=json.loads(buffers.pop('coverage'));check(start+30)
   value=extract(buffers['mesh'],buffers['policy'],buffers['original_policy'],buffers['ids'],report,ALLOWLIST,start+30)
   value['frozen_coverage_metadata']=attach_coverage(value,coverage,report);check(start+30)
   if value['target_count']!=25 or value['original_occurrences']!=889:raise Refuse('COMPLETE25_889_REQUIRED')
   result.update(value)
  except (OSError,ValueError,KeyError,IndexError,TypeError,struct.error,MemoryError,OverflowError) as error:
   result.update(classification='UNKNOWN_EXTRACTION_REFUSED_NO_PARTIAL_TARGETS',reason='MEMORY_ALLOCATION' if isinstance(error,(MemoryError,OverflowError)) else str(error))
 result['seconds']=time.monotonic()-start;result['peak_kib']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
 raw=(json.dumps(result,indent=1,default=str)+'\n').encode()
 if len(raw)+65536>4194304 or time.monotonic()-start>=45:raise Refuse('OUTPUT_WALL_CAP_NO_PUBLISH')
 args.out.mkdir();(args.out/'report.json').write_bytes(raw);print(json.dumps(dict(classification=result['classification'],report_sha256=sha(raw),seconds=result['seconds'])))

if __name__=='__main__':main()
