#!/usr/bin/env python3
"""PLAN ONLY: qualify explicit existing C mirrors; no assets copied or adopted."""
import argparse,collections,ctypes,gzip,hashlib,json,ntpath,os,struct,sys,time
from pathlib import Path
import immutable_append1618_buffered_v2_writer as w
from file_charge import WinPin,safe_path

PARENT_PLAN_SHA='ea1c588868ac9e4717e90b8cfdb51a070d56273b66a104973d07a61334994710'
BASE_SHA='89ef27a767fcee529c3ac6ca07fef5a8f9a3e2515f38eda63b61c8929fb0be62'
ROOTS={
 'canonical1004':r'C:\Game Dev\Emulators\re4-assets-private\texture-canonical1004-20261021',
 'next415':r'C:\Flycast-Evidence\re4-dreamcast\texture-rect21-20261021\next415-batch-01',
 'next177':r'C:\Flycast-Evidence\re4-dreamcast\texture-rect21-20261021\next177-batch-01',
 'next4':r'C:\Flycast-Evidence\re4-dreamcast\texture-rect21-20261021\next4-vertical-batch-01',
 'next18twid':r'C:\Flycast-Evidence\re4-dreamcast\texture-rect21-20261021\next18-twiddled-batch-01'}
SEALS={'next415':'49010939c9dea59c2fc18bef0995b23d27e57edfd37aa1222a11e74fa352e624','next177':'3ce4276121e366c8435e576de8f4567535565524bb7422936cd32031af6a27a6','next4':'b42f88622b901d336cb0d32013c6918c8c9fe8bccc98968a9aa1e75f7ce15657','next18twid':'21b8650a3dfd80d8c6fc2c8e7b0f6fc278a88ce85b7e2db40dd5487dde788b4c'}
EXPECTED_FILES={'canonical1004':1,'next415':415,'next177':177,'next4':4,'next18twid':18}

def canonical_c(value):
 s=str(value)
 if s.startswith('\\\\?\\'):s=s[4:]
 if ntpath.splitdrive(s)[0].lower()!='c:'or not ntpath.isabs(s):raise ValueError('explicit local C file required; no UNC/relative source')
 return ntpath.normcase(ntpath.normpath(s))
def require_same_path(expected,observed):
 if canonical_c(expected)!=canonical_c(observed):raise ValueError('native final path differs; alias refused')
def final_name(held):
 fn=held.k.GetFinalPathNameByHandleW;fn.argtypes=[ctypes.c_void_p,ctypes.c_wchar_p,ctypes.c_uint32,ctypes.c_uint32];fn.restype=ctypes.c_uint32;buf=ctypes.create_unicode_buffer(32768);n=fn(held.h,buf,len(buf),0)
 if not n or n>=len(buf):raise ctypes.WinError(ctypes.get_last_error())
 return buf.value
def verified_file(path,root,expected_sha):
 safe_path(path,root);canonical_c(path)
 with WinPin(path,expected_sha)as held:
  final=final_name(held);require_same_path(path,final);info=held.INFO()
  if not held.k.GetFileInformationByHandle(held.h,ctypes.byref(info)):raise ctypes.WinError(ctypes.get_last_error())
  return dict(sha256=held.sha256,native_identity=held.initial,last_write_filetime=info.written.lo+(info.written.hi<<32),native_final_path=final)
def producer_pins():
 pins={};members={}
 for group,digest in SEALS.items():
  p=Path(ROOTS[group])/'SHA256SUMS.txt';safe_path(p,Path(ROOTS[group]))
  if w.sha(p)!=digest:raise ValueError('explicit C producer seal drift '+group)
  entries={}
  for line in p.read_text().splitlines():
   h,rel=line.split('  ',1)
   if Path(rel).is_absolute()or'..'in Path(rel).parts or rel in entries:raise ValueError('producer manifest path/duplicate')
   entries[rel.replace('\\','/')]=h
  pins[group]=dict(path=str(p),sha256=digest);members[group]=entries
 return pins,members
def map_rows(rows,manifests):
 mapped=[];files={};ids=collections.Counter()
 for r in rows:
  group=r['source']
  if group not in ROOTS:raise ValueError('no explicit source mirror for group')
  relative=Path(r['path']).relative_to(r['source_root']);root=Path(ROOTS[group]);path=root/relative
  if relative.is_absolute()or'..'in relative.parts:raise ValueError('outside declared mirror')
  if group=='canonical1004':
   if relative.as_posix()!='tex.pak':raise ValueError('exact canonical archive path required')
   expected=BASE_SHA
  else:
   expected=r['sha256']
   if relative.as_posix()!='textures/'+r['key']+'.re4tex'or manifests[group].get(relative.as_posix())!=expected:raise ValueError('file not pinned by exact C producer manifest')
  key=str(r['path'])
  if key not in files:
   files[key]=dict(source_group=group,old_source_path=key,c_source_path=str(path),c_source_root=str(root),relative_path=relative.as_posix(),expected_file_sha256=expected,member_refs=0,body_crc32=r.get('body_crc32'));ids[group]+=1
  elif files[key]['c_source_path']!=str(path)or files[key]['expected_file_sha256']!=expected:raise ValueError('inconsistent shared source mapping')
  files[key]['member_refs']+=1;mapped.append({**r,'path':path,'source_root':root})
 if len(mapped)!=7151 or len(files)!=615 or dict(ids)!=EXPECTED_FILES:raise ValueError('exact7151member/615file/five-root mapping required')
 return mapped,files
def bind_identities(files):
 seen=set()
 for f in files.values():
  proof=verified_file(Path(f['c_source_path']),Path(f['c_source_root']),f['expected_file_sha256']);identity=proof['native_identity'];key=(identity['volume_serial'],identity['file_index'])
  if key in seen:raise ValueError('source aliases share native file identity')
  seen.add(key);f.update(proof)
 return len(seen)

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--parent-plan',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
 if os.name!='nt'or not sys.dont_write_bytecode or os.environ.get('PYTHONDONTWRITEBYTECODE')!='1':raise ValueError('native source-only proof requires bytecode disabled before startup')
 if a.out.exists():raise FileExistsError('preserve source-plan namespace')
 if w.sha(a.parent_plan)!=PARENT_PLAN_SHA or w.sha(Path(w.__file__))!='84acd018745b6bbe5048ac760e2ff090efd53c1306f78f0514c2d250c22d8eb8':raise ValueError('frozen v2 source/plan changed')
 p=json.loads(a.parent_plan.read_text());head,index,old=w.resolve(p);pins,manifests=producer_pins();rows,files=map_rows(old,manifests)
 if bind_identities(files)!=615:raise ValueError('native source identity count')
 start=time.perf_counter()
 class Guard:
  last=0.;calls=0
  def check(self,*args,**kwargs):
   self.calls+=1
   if time.perf_counter()-start>=51:raise RuntimeError('source-only51s ceiling')
   if time.perf_counter()-self.last>=.2:
    if w.shutil.disk_usage('C:\\').free<w.FLOOR+w.PEER:raise RuntimeError('fresh C source-peer floor')
    self.last=time.perf_counter()
   if time.perf_counter()-start>=51:raise RuntimeError('source ceiling after filesystem query')
 g=Guard();h=hashlib.sha256();sizes=[]
 for b in w.source_stream(head,index,rows,g):h.update(b);sizes.append(len(b))
 elapsed=time.perf_counter()-start
 if h.hexdigest()!=w.PACK_SHA or sum(sizes)!=w.PACK_BYTES or len(sizes)!=153:raise ValueError('mapped C-only actual virtual pack differs')
 record=dict(schema='1618-native-C-source-map-v1',status='SOURCE_PLAN_ONLY_NOT_ADOPTED',root_map=ROOTS,producer_manifest_pins=pins,parent_v2_plan=dict(path=str(a.parent_plan),sha256=PARENT_PLAN_SHA),parent_member_identity='Frozen1618 finalindex+inherited1600 member/source SHA resolver unchanged; all7151SHA and614canonicaldescriptor/bodyCRC verified through mainhelper3e6c',files=list(files.values()),expected=dict(pack_sha256=h.hexdigest(),pack_bytes=w.PACK_BYTES,members=7151,files=615,mips_if_selected=1618,index_sectors=56,data_offset=116736),limits=['0newassetcopies; all615existingexplicitCfiles only','noUNCdata source fallback/no guess/search/no frozenv2mutation','future adoption must explicitly bind this source map and revalidate native identities/fullSHA/path scope','all29world/650proposals UNSELECTED/r11f+r200+r107AREAholds; alpha142excluded','sourcehostread/hash is not fullwriter/readback throughput or game performance'])
 compressed=gzip.compress((json.dumps(record,sort_keys=True,separators=(',',':'))+'\n').encode(),mtime=0)
 if 2*len(compressed)+65536>512*1024:raise ValueError('sourceunit metadata forecast exceeds512KiB')
 a.out.mkdir();(a.out/'SOURCE-FILES-615.json.gz').write_bytes(compressed)
 w.json_new(a.out/'SUMMARY.json',dict(status='SOURCE_PLAN_ONLY_C_MIRRORS_VERIFIED_UNSELECTED',parent_plan_sha256=PARENT_PLAN_SHA,source_manifest_sha256=hashlib.sha256(compressed).hexdigest(),producer_manifest_pins=pins,roots=ROOTS,files_by_group=EXPECTED_FILES,native615_unique_singlelink_files=True,all7151_member_SHA_and614_bodyCRC=True,zero_UNC_asset_reads_in_mapped_virtual=True,virtual_pack_sha256=h.hexdigest(),bytes=w.PACK_BYTES,chunks=len(sizes),source_host_virtual_seconds=elapsed,source_guard_calls=g.calls,asset_copies=0,large_bytes_written=0,adopted=False,source_metadata_gzip_bytes=len(compressed),physical_or_game_performance_acceptance=False))
 print(json.dumps(dict(status='PASS_PLAN_ONLY_NATIVE_C_SOURCES',sha256=h.hexdigest(),files=615,chunks=len(sizes),source_host_virtual_seconds=elapsed,manifest_gzip_bytes=len(compressed),source_manifest_sha256=hashlib.sha256(compressed).hexdigest(),asset_copies=0,adopted=False)))
if __name__=='__main__':main()
