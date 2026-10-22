#!/usr/bin/env python3
"""Source only143 native inputs; derive7151 SHA table from actual verified1618."""
import argparse,collections,gzip,hashlib,json,mmap,os,struct,sys,zlib
from pathlib import Path
from file_charge import WinPin,safe_path
from native_c_source_binding21 import proof
from plan_append1596 import reader
from plan_append1760 import alpha_candidate
PARENT=r'C:\Flycast-Evidence\re4-dreamcast\texture21-benchmark-20261021\append1760-plan-01'
PARENT_SEAL='274ee1916fede1ae636f9aa210ea0500f9b33804855347c55ed42f726f9ca79d'
BASE=r'C:\Game Dev\Emulators\re4-assets-private\texture-append1618-20261022-v3-native-c'
ALPHA=r'C:\Flycast-Evidence\re4-dreamcast\texture-rect21-20261021\next142-alpha-batch-01'
REPEAT=r'C:\Flycast-Evidence\re4-dreamcast\texture-rect21-20261021\alpha-repeat16-batch-01'
BASE_SHA='d43d1c81ba2e70ab0177c6c97867fd39c95d68a114b727601b3eadd14e6aaf08'
TARGET='1838d97ae07637fa47beed574033e2d4f79595f86fb024ace6e6e7cc752f6477'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def emit(p,v):
 with p.open('x')as f:json.dump(v,f,indent=2);f.write('\n')
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
 if os.name!='nt'or not sys.dont_write_bytecode or os.environ.get('PYTHONDONTWRITEBYTECODE')!='1':raise ValueError('native source proof and bytecode-disabled startup required')
 if a.out.exists():raise FileExistsError('preserve143 source namespace')
 parent=Path(PARENT)
 if sha(parent/'UNIT-SHA256SUMS')!=PARENT_SEAL:raise ValueError('exact1760 UNIT seal')
 for line in(parent/'UNIT-SHA256SUMS').read_text().splitlines():
  h,n=line.split('  ',1);p=Path(n)
  if p.is_absolute()or'..'in p.parts or sha(parent/p)!=h:raise ValueError('1760 sealed input drift')
 plan=json.loads((parent/'PLAN1760.json').read_text());add=json.loads((parent/'APPENDED-142.json').read_text());base=Path(BASE)/'tex.pak';ident=proof.verified_file(base,Path(BASE),BASE_SHA);base_table=bytearray();identity_digest=hashlib.sha256();base_index=None
 known=reader(Path(r'\\wsl.localhost\Ubuntu-24.04\root\probe\codex-texture-atlas21\port\dreamcast\tools\d367\texpack.py'))
 with WinPin(base,BASE_SHA),base.open('rb')as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ)as view:
  if known.verify(view)[0]!=7151:raise ValueError('actual base known reader')
  base_index=bytes(view[2048:116736])
  for i in range(7151):
   k0,k1,off,n=struct.unpack_from('<4I',view,2048+16*i);h=hashlib.sha256(view[off:off+n]).digest();base_table+=h;identity_digest.update(('%08x-%08x %d %s\n'%(k0,k1,n,h.hex())).encode())
 if identity_digest.hexdigest()!=plan['actual1618']['member_identity_digest']or hashlib.sha256(base_index).hexdigest()!=plan['actual1618']['index_sha256']:raise ValueError('all7151 identities retained from actual1760 virtual proof')
 files=[dict(source_group='actual1618',key=None,c_source_path=str(base),c_source_root=BASE,relative_path='tex.pak',member_refs=7151,sha256=BASE_SHA,**{k:v for k,v in ident.items()if k!='sha256'})];ids={(ident['native_identity']['volume_serial'],ident['native_identity']['file_index'])};groups=collections.Counter()
 for r in add:
  path=Path(r['windows_path']);root=Path(REPEAT if r['semantic_source']=='repeat16'else ALPHA);safe_path(path,root);proof.require_same_path(path,root/r['relative_path']);b=path.read_bytes();alpha_candidate(b,{**r,'package_bytes':r['bytes'],'candidate_sha256':r['sha256'],'candidate_crc32':r['body_crc32'],'scoped_key':r['key']});p=proof.verified_file(path,root,r['sha256']);identity=(p['native_identity']['volume_serial'],p['native_identity']['file_index'])
  if identity in ids:raise ValueError('native143 source alias')
  ids.add(identity);groups[r['semantic_source']]+=1;files.append(dict(source_group='final142',c_source_path=str(path),c_source_root=str(root),member_refs=1,**{k:v for k,v in r.items()if k not in('absolute_path','windows_path','source_root')},**{k:v for k,v in p.items()if k!='sha256'}))
 if len(files)!=143 or dict(groups)!={'compact119':119,'repeat16':16,'missing7':7}:raise ValueError('exact143/119+16+7 source contract')
 record=dict(schema='1760-native-C-143-source-map-v1',status='SOURCE_ONLY_NEW_WRITER_NOT_ALLOCATED',roots=dict(actual1618=BASE,alpha142=ALPHA,repeat16=REPEAT),parent_input_seal_path=str(parent/'UNIT-SHA256SUMS'),parent_input_seal_sha256=PARENT_SEAL,parent_pack_sha256=BASE_SHA,parent7151_member_identity_digest=identity_digest.hexdigest(),parent_index_sha256=hashlib.sha256(base_index).hexdigest(),parent_member_sha256_binary=dict(path=str(a.out/'PARENT-7151-SHA256.bin'),sha256=hashlib.sha256(base_table).hexdigest(),bytes=len(base_table)),files=files,expected=dict(pack_sha256=TARGET,pack_bytes=162555904,members=7293,mips_if_selected=1760,index_sectors=57,data_offset=118784),holds=['29worlds PRIVATE UNSELECTED/source792default0/11f200held','all143 actualC sources only; no615file source replay/fallback/copies','no pack/programme/image/guest/adoption'])
 a.out.mkdir();(a.out/'PARENT-7151-SHA256.bin').write_bytes(base_table);raw=gzip.compress((json.dumps(record,sort_keys=True,separators=(',',':'))+'\n').encode(),mtime=0);(a.out/'NATIVE-SOURCES-143.json.gz').write_bytes(raw)
 emit(a.out/'NATIVE143-PROOF.json',dict(status='PASS_SOURCE_ONLY_NATIVE143',files=143,source_groups=dict(groups),native143_unique_singlelink_FileID_finalpath_mtime_fullSHA=True,all7151_member_identity_digest=identity_digest.hexdigest(),base_index_sha256=hashlib.sha256(base_index).hexdigest(),source_manifest_sha256=hashlib.sha256(raw).hexdigest(),member_binary_sha256=hashlib.sha256(base_table).hexdigest(),large_bytes_written=0,asset_copies=0))
 print(json.dumps(dict(manifest_sha256=hashlib.sha256(raw).hexdigest(),member_binary_sha256=hashlib.sha256(base_table).hexdigest(),metadata_bytes=len(raw)+len(base_table),files=143)))
if __name__=='__main__':main()
