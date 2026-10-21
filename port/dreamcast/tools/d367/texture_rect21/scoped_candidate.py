#!/usr/bin/env python3
"""Append scoped private texture keys and rebind only their native R4PW parts."""
from pathlib import Path
import argparse,ctypes,hashlib,json,shutil,struct,sys,zlib
HERE=Path(__file__).resolve().parent;sys.path[:0]=[str(HERE),str(HERE.parent),str(HERE.parents[1])]
import texpack
from vram.vq_pak import read_pak
import world_bindings as world
import mipmap_vq as mip

def sha(b):return hashlib.sha256(b).hexdigest()
def keystr(k):return '%08x-%08x'%k
def scoped_key(key,package_sha):
 return struct.unpack('<II',hashlib.sha256(b'RE4DC_WORLD_RECT21_COMPACT_V1\0'+struct.pack('<II',*key)+bytes.fromhex(package_sha)).digest()[:8])
def rebind(blob,mapping):
 rows=world.inspect_sidecar(blob);out=bytearray(blob);changed=[]
 for row in rows:
  key=row['key']
  if key not in mapping:continue
  assert [row['width'],row['height']]==[128,64]
  new=mapping[key];at=32+row['part']*16;struct.pack_into('<II',out,at,*new)
  assert bytes(out[at+8:at+16])==blob[at+8:at+16]
  changed.append(dict(part=row['part'],original_key=key,scoped_key=keystr(new),width=row['width'],height=row['height'],render_pass=row['render_pass']))
 if changed:struct.pack_into('<I',out,20,zlib.crc32(out[32:])&0xffffffff)
 after=world.inspect_sidecar(bytes(out));assert len(rows)==len(after)
 for old,new in zip(rows,after):
  for field in ['width','height','render_pass','cull','texture','flags','part']:assert old[field]==new[field]
 allowed=set(range(20,24))
 for r in changed:allowed.update(range(32+r['part']*16,40+r['part']*16))
 assert all(a==b or i in allowed for i,(a,b) in enumerate(zip(blob,out)))
 return bytes(out),changed

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 for k in ['pack','compact','binding-root','coverage','oracle','out']:ap.add_argument('--'+k,type=Path,required=True)
 ap.add_argument('--write-pack',action='store_true');a=ap.parse_args();assert not a.out.exists(),'Preserve existing output'
 if shutil.disk_usage('/mnt/c').free<18.5*1024**3:raise SystemExit('C preflight requires18.5GiB; preserve source-only work')
 source=a.pack.read_bytes();texpack.verify(source);base=read_pak(source);assert len(base)==6501
 receipt=json.loads((a.compact/'receipt.json').read_text());assert receipt['source_pack_sha256']==sha(source)
 coverage=json.loads(a.coverage.read_text());assert coverage['source_pack_sha256']==sha(source)
 occupied=set(base)|{tuple(int(x,16) for x in r['key'].split('-')) for r in coverage['loose_and_quality_rows']}|{(0x3662c0aa,0xc9e71c00),(0xfefdf580,0xf15c1f47)}
 lib=ctypes.CDLL(str(a.oracle));call=lib.mipmap_oracle_decode;call.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_uint,ctypes.c_uint,ctypes.c_int,ctypes.c_uint,ctypes.c_void_p,ctypes.c_size_t]
 mapping={};added={};proofs=[];table=[]
 for row in receipt['selected']:
  old=tuple(int(x,16) for x in row['key'].split('-'));blob=(a.compact/'packages'/(row['key']+'.re4tex')).read_bytes();assert sha(blob)==row['candidate_sha256'];new=scoped_key(old,sha(blob));assert new not in occupied,'Immutable key collision';occupied.add(new);mapping[row['key']]=new;added[new]=blob
  assert row['source_sha256']==sha(base[old]) and row['logical']==[128,64] and row['physical']==[64,64] and row['uv_scale']==[1.,1.]
  native=mip.read_native_vq(blob);assert native.size==64 and native.texture[3]==0 and native.texture[6]==4;assert native.codebook==base[old][144:2192];levels=[]
  for level in range(7):
   side=1<<level;buf=(ctypes.c_ubyte*(side*side*4))();assert call(native.payload,len(native.payload),0,64,1,level,buf,len(buf))==len(buf);assert bytes(buf)==bytes(c for p in mip.decode_level(native,side) for c in p);levels.append(side)
  proofs.append(dict(original_key=row['key'],scoped_key=keystr(new),source_sha256=sha(base[old]),candidate_sha256=sha(blob),decoded_levels=levels,candidate_crc32=native.header[8],logical=[128,64],physical=[64,64],uv_scale=[1.,1.],rounded_candidate=3424,rounded_original=4096))
  table.append('{0x%08xU,0x%08xU,128U,64U,{64U,64U,%dU,%dU,2U,%dU,0x%08xU},1.0f,1.0f},'%(new[0],new[1],native.texture[3],native.texture[6],len(native.payload),native.header[8]))
 assert len(added)==17
 a.out.mkdir(parents=True);(a.out/'textures').mkdir()
 for key,blob in added.items():(a.out/'textures'/(keystr(key)+'.re4tex')).write_bytes(blob)
 worlds=[];bound=set()
 binding=json.loads((a.binding_root/'bindings.json').read_text());assert binding['source_pack_sha256']==sha(source)
 for item in binding['matched_worlds']:
  p=a.binding_root/'inputs'/item['path'];blob=p.read_bytes();assert sha(blob)==item['sha256'];new,changes=rebind(blob,mapping)
  if not changes:continue
  assert item['path'].split('/')[2] in ['r100','r103']
  path=a.out/item['path'];path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(new)
  worlds.append(dict(path=item['path'],source_sha256=sha(blob),candidate_sha256=sha(new),size=len(new),changed_parts=changes,source_body_crc32=struct.unpack_from('<I',blob,20)[0],candidate_body_crc32=struct.unpack_from('<I',new,20)[0]))
  bound.update(v['scoped_key'] for v in changes)
 assert bound==set(map(keystr,added))
 # Every selected alias is now reached only through native sidecar remapping.
 assert all(key not in base for key in added)
 count=None;pack_sha=None;pack_bytes=None;archive_delta=None
 if a.write_pack:
  if shutil.disk_usage('/mnt/c').free<18.5*1024**3:raise SystemExit('C guard before pack')
  combined=dict(base);combined.update(added);pak,count=texpack.build(combined);texpack.verify(pak);parsed=read_pak(pak)
  assert len(parsed)==6518 and all(parsed[k]==v for k,v in base.items()) and all(parsed[k]==v for k,v in added.items())
  if shutil.disk_usage('/mnt/c').free-len(pak)<18*1024**3:raise SystemExit('C guard reserves18GiB after pack')
  (a.out/'tex.pak').write_bytes(pak);pack_sha=sha(pak);pack_bytes=len(pak);archive_delta=len(pak)-len(source)
 (a.out/'scoped_representations.inc').write_text('// Scoped compact17 candidate keys; original-key experiments stay unselected.\n'+'\n'.join(table)+'\n')
 r=dict(schema='re4dc-rect21-native-scoped-1',source_pack_sha256=sha(source),candidate_pack_sha256=pack_sha,source_pack_bytes=len(source),candidate_pack_bytes=pack_bytes,archive_delta=archive_delta,original_members_exact=6501,appended_members=17,candidate_pack_members=count,namespace='SHA256(RE4DC_WORLD_RECT21_COMPACT_V1 NUL + original pair LE + candidate SHA256)[0:8] as pair LE',reserved_atlas_keys=['3662c0aa-c9e71c00','fefdf580-f15c1f47'],coverage_sha256=sha(a.coverage.read_bytes()),binding_receipt_sha256=sha((a.binding_root/'bindings.json').read_bytes()),compact_receipt_sha256=sha((a.compact/'receipt.json').read_bytes()),selected=proofs,worlds=worlds,independent_mip_decodes=sum(len(v['decoded_levels']) for v in proofs),selected_rounded_before=69632,selected_rounded_after=58208,selected_rounded_delta=-11424,possible_original_plus_candidate_rounded=127840,limits=['Private source/decoder/pack/sidecar gate only; no full program, rendered scene, performance or hardware acceptance.','All original keys/packages stay exact. Selected candidate IDs are only in two changed R4PW copies; no source/actor/generic references change.','Candidate requests shrink, archive grows, and any original copies still loaded can coexist. Actual peak and main/VRAM budgets remain open.','WORLD_RECT21 stays default0; data input must be staged only with the guarded qualified source.'])
 (a.out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:r[k] for k in ['original_members_exact','appended_members','candidate_pack_members','archive_delta','independent_mip_decodes']}))
if __name__=='__main__':main()
