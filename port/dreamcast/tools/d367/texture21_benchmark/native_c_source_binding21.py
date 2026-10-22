"""Explicit frozen615-source binding; no fallback, asset copies or path adoption."""
import ctypes,gzip,hashlib,json,ntpath,os
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
import plan_append1618_native_c_sources as proof

MANIFEST_PATH=r'C:\Flycast-Evidence\re4-dreamcast\texture21-benchmark-20261021\append1618-native-c-source-plan-01\SOURCE-FILES-615.json.gz'
MANIFEST_SHA='c52705fc04df93f5b34564c62db980030b0abe9a938f166ddeef4f63be1c3970'
PACK_SHA='d43d1c81ba2e70ab0177c6c97867fd39c95d68a114b727601b3eadd14e6aaf08'
D=ctypes.c_uint32
class FT(ctypes.Structure):_fields_=[('lo',D),('hi',D)]
class INFO(ctypes.Structure):_fields_=[('attrs',D),('created',FT),('accessed',FT),('written',FT),('volume',D),('sizehi',D),('sizelo',D),('links',D),('indexhi',D),('indexlo',D)]
_KERNEL=None
def integer(v):return type(v)is int
def validate_record(record):
 if record['schema']!='1618-native-C-source-map-v1'or record['status']!='SOURCE_PLAN_ONLY_NOT_ADOPTED'or record['root_map']!=proof.ROOTS:raise ValueError('exact source615 schema/roots')
 if record['expected']!=dict(pack_sha256=PACK_SHA,pack_bytes=160159744,members=7151,files=615,mips_if_selected=1618,index_sectors=56,data_offset=116736):raise ValueError('same1618 expected identities required')
 files=record['files']
 if not isinstance(files,list)or len(files)!=615:raise ValueError('exact615 source files')
 old={};new={};ids=set();counts={g:0 for g in proof.ROOTS}
 for e in files:
  group=e['source_group']
  if group not in proof.ROOTS or proof.canonical_c(e['c_source_root'])!=proof.canonical_c(proof.ROOTS[group]):raise ValueError('undeclared C source root')
  rel=e['relative_path']
  if ntpath.isabs(rel)or ntpath.splitdrive(rel)[0]or'..'in rel.replace('\\','/').split('/'):raise ValueError('source-relative path escape')
  proof.require_same_path(e['c_source_path'],ntpath.join(proof.ROOTS[group],rel));proof.require_same_path(e['c_source_path'],e['native_final_path'])
  if e['sha256']!=e['expected_file_sha256']or len(e['sha256'])!=64 or any(c not in'0123456789abcdef'for c in e['sha256']):raise ValueError('exact source fullSHA')
  ident=e['native_identity'];required={'volume_serial','file_index','link_count','logical_bytes','creation_time'}
  if set(ident)!=required or not all(integer(v)for v in ident.values())or ident['link_count']!=1 or ident['file_index']<=0 or ident['logical_bytes']<=0 or not integer(e['last_write_filetime'])or e['last_write_filetime']<=0:raise ValueError('native source identity/mtime/singlelink')
  if group=='canonical1004':
   if rel!='tex.pak'or e['sha256']!=proof.BASE_SHA or e['member_refs']!=6537 or ident['logical_bytes']!=156248064 or e['body_crc32']is not None:raise ValueError('exact base archive')
  elif not rel.startswith('textures/')or e['member_refs']!=1 or not integer(e['body_crc32']):raise ValueError('exact appended source member')
  key=proof.canonical_c(e['c_source_path']);identity=(ident['volume_serial'],ident['file_index'])
  if e['old_source_path']in old or key in new or identity in ids:raise ValueError('duplicate source/native alias')
  old[e['old_source_path']]=e;new[key]=e;ids.add(identity);counts[group]+=1
 if counts!=proof.EXPECTED_FILES:raise ValueError('five fixed source group counts')
 for group,digest in proof.SEALS.items():
  p=record['producer_manifest_pins'][group]
  if p['sha256']!=digest:raise ValueError('producer provenance changed')
  proof.require_same_path(p['path'],ntpath.join(proof.ROOTS[group],'SHA256SUMS.txt'))
 return old,new

class NativeCBinding:
 def __init__(self,record):self.record=record;self.by_old,self.by_c=validate_record(record)
 @classmethod
 def load(cls,plan):
  if plan.get('c_source_manifest_path')!=MANIFEST_PATH or plan.get('c_source_manifest_sha256')!=MANIFEST_SHA:raise ValueError('mandatory exact C source manifest pin')
  raw=Path(MANIFEST_PATH).read_bytes()
  if len(raw)!=64427 or hashlib.sha256(raw).hexdigest()!=MANIFEST_SHA:raise ValueError('C source manifest bytes changed')
  decoded=gzip.decompress(raw)
  if len(decoded)>2*1024**2:raise ValueError('bounded source metadata required')
  return cls(json.loads(decoded))
 def map_rows(self,rows):
  mapped=[];counts={k:0 for k in self.by_old}
  for r in rows:
   e=self.by_old.get(str(r['path']))
   if e is None or r['source']!=e['source_group']:raise ValueError('unmapped source; no fallback')
   if r['source']!='canonical1004'and(r['sha256']!=e['sha256']or r.get('body_crc32')!=e['body_crc32']or r['bytes']!=e['native_identity']['logical_bytes']or r['source_offset']!=0):raise ValueError('appended member contract changed')
   if r['source_offset']<0 or r['source_offset']+r['bytes']>e['native_identity']['logical_bytes']:raise ValueError('source member extent')
   counts[e['old_source_path']]+=1;mapped.append({**r,'path':Path(e['c_source_path']),'source_root':Path(e['c_source_root'])})
  if len(mapped)!=7151 or any(counts[k]!=e['member_refs']for k,e in self.by_old.items()):raise ValueError('complete7151 member source coverage')
  return mapped
 def preflight(self):
  pins,members=proof.producer_pins()
  if pins!=self.record['producer_manifest_pins']:raise ValueError('actual producer provenance changed')
  for e in self.by_old.values():
   if e['source_group']!='canonical1004'and members[e['source_group']].get(e['relative_path'])!=e['sha256']:raise ValueError('source missing from producer manifest')
   actual=proof.verified_file(Path(e['c_source_path']),Path(e['c_source_root']),e['sha256'])
   if actual['native_identity']!=e['native_identity']or actual['last_write_filetime']!=e['last_write_filetime']:raise ValueError('native source identity/fullSHA preflight changed')
   proof.require_same_path(actual['native_final_path'],e['native_final_path'])
  return len(self.by_old)
 @contextmanager
 def open(self,path):
  e=self.by_c.get(proof.canonical_c(path))
  if e is None:raise ValueError('unknown C source; no fallback')
  f=Path(path).open('rb')
  try:
   check_handle(f,e)
   yield f
  finally:
   try:
    if not f.closed:check_handle(f,e)
   finally:f.close()

def check_handle(file,expected):
 global _KERNEL
 if os.name!='nt':raise OSError('native source handle binding requires Windows')
 import msvcrt
 if _KERNEL is None:
  _KERNEL=ctypes.WinDLL('kernel32',use_last_error=True);_KERNEL.GetFileInformationByHandle.argtypes=[ctypes.c_void_p,ctypes.POINTER(INFO)];_KERNEL.GetFileInformationByHandle.restype=ctypes.c_int
 k=_KERNEL;handle=msvcrt.get_osfhandle(file.fileno());info=INFO()
 if not k.GetFileInformationByHandle(handle,ctypes.byref(info)):raise ctypes.WinError(ctypes.get_last_error())
 actual=dict(volume_serial=info.volume,file_index=info.indexlo+(info.indexhi<<32),link_count=info.links,logical_bytes=info.sizelo+(info.sizehi<<32),creation_time=info.created.lo+(info.created.hi<<32));written=info.written.lo+(info.written.hi<<32)
 if info.attrs&0x10 or actual!=expected['native_identity']or written!=expected['last_write_filetime']:raise ValueError('opened C source native identity/mtime changed')
 final=proof.final_name(SimpleNamespace(k=k,h=handle));proof.require_same_path(final,expected['c_source_path']);proof.require_same_path(final,expected['native_final_path'])
