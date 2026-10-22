#!/usr/bin/env python3
"""NEW1618v3 explicit native-C source binding; no copies or fallback."""
import os,sys
if not sys.dont_write_bytecode:raise RuntimeError("root must disable bytecode before local imports")
import argparse,ctypes,hashlib,importlib.util,json,mmap,os,shutil,stat,struct,sys,time,zlib
from pathlib import Path
from file_charge import entries,publish_no_replace,roundup,safe_path
from mipmap_pair_plan import local
from immutable_append1600_writer import resolve as resolve1600
from root_pack_stream21 import source_stream as _verified_stream,coalesce
from native_c_source_binding21 import NativeCBinding

APPEND1618_SEAL='0eb5233f21ed050d1cf1dc8aef0a6f8277292d60409122e074b525d4636d43ac'
PACK_SHA='d43d1c81ba2e70ab0177c6c97867fd39c95d68a114b727601b3eadd14e6aaf08'
PACK_BYTES=160159744;CAP=332902400;FLOOR=18*1024**3+64*1024**2;PEER=64*1024**2
READER_SHA='199fb53bc3855ba3c831e4f9013c1e8fd4383cf36615803cbc29acacedcf5bbf'
CHUNK=1048576
DEPENDENCIES={'immutable_append1618_native_c_v3_writer.py','immutable_append1618_buffered_v2_writer.py','immutable_append1600_writer.py','file_charge.py','mipmap_pair_plan.py','root_pack_stream21.py','plan_append1618_native_c_sources.py','native_c_source_binding21.py'}
STREAM_HELPER_SHA='3e6c20648b641421c2dce8ed7948a9a550483da2b463cf19ab0b7a9deaccbbfc'
def charge_result(n,low,high,error):
 logical=roundup(n,4096)
 if low==0xffffffff and error:
  if error in(1,50,120):return logical
  raise OSError(error,'native allocation query failed closed')
 return max(logical,low+(high<<32))
def file_charge(path,n):
 logical=roundup(n,4096)
 if os.name!='nt':return logical
 k=ctypes.WinDLL('kernel32',use_last_error=True);k.GetCompressedFileSizeW.argtypes=[ctypes.c_wchar_p,ctypes.POINTER(ctypes.c_uint32)];k.GetCompressedFileSizeW.restype=ctypes.c_uint32
 high=ctypes.c_uint32();ctypes.set_last_error(0);low=k.GetCompressedFileSizeW(str(path),ctypes.byref(high))
 return charge_result(n,low,high.value,ctypes.get_last_error())
def sha(path):
 with Path(path).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def json_new(path,value):
 with path.open('x')as f:json.dump(value,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
def sealed(root,digest):
 if sha(root/'SHA256SUMS')!=digest:raise ValueError('immutable composition seal changed')
 for line in(root/'SHA256SUMS').read_text().splitlines():
  h,name=line.split('  ',1);rel=Path(name)
  if rel.is_absolute()or'..'in rel.parts or sha(root/rel)!=h:raise ValueError('composition metadata changed '+name)

def environment(plan):
 if not sys.dont_write_bytecode or os.environ.get('PYTHONDONTWRITEBYTECODE')!='1':raise ValueError('root BOTH bytecode environment prerequisites required')
 prefix=sys.pycache_prefix;expected=Path(plan['metadata_root']).absolute()/'pycache'
 if not prefix or not Path(prefix).is_absolute()or Path(prefix).absolute()!=expected or os.environ.get('PYTHONPYCACHEPREFIX')!=str(expected):raise ValueError('exact fresh absolute charged pycache prefix required')
 safe_path(expected,Path(plan['metadata_root']).absolute())
 if expected.exists()or expected.is_symlink():raise ValueError('preserve existing pycache prefix; fresh root namespace required')
 return str(expected)

def resolve(plan):
 root=local(plan['delta1618']);sealed(root,APPEND1618_SEAL)
 d=json.loads((root/'plan/PLAN1618.json').read_text());frozen=local(d['frozen1600']['plan_path'])
 if sha(frozen)!=d['frozen1600']['plan_sha256']:raise ValueError('exact inherited1600 plan changed')
 if sha(Path(__file__).parent/'immutable_append1600_writer.py')!=d['frozen1600']['writer_sha256']:raise ValueError('inherited1600 resolver changed')
 _h,_i,prior=resolve1600(json.loads(frozen.read_text()));rows={r['key']:r for r in prior};twid=local(d['twid18']['path'])
 for r in json.loads((root/'plan/APPENDED-18-TWID.json').read_text()):
  key=r['key']
  if key in rows or r['source']!='next18twid':raise ValueError('18 TWID key collision/source')
  rows[key]={**r,'path':safe_path(twid/r['relative_path'],twid),'source_root':twid,'source_offset':0}
 head=(root/'plan/expected-header.bin').read_bytes();index=(root/'plan/expected-index.bin').read_bytes()
 if len(head)!=2048 or len(index)!=56*2048 or head[:8]!=b'RE4PAK1\0'or struct.unpack_from('<5I',head,8)!=(1,7151,2048,116736,zlib.crc32(index)&0xffffffff)or any(head[28:])or any(index[7151*16:]):raise ValueError('1618 header/index contract')
 ordered=[];cursor=116736
 for i in range(7151):
  a,b,off,n=struct.unpack_from('<4I',index,i*16);key='%08x-%08x'%(a,b);r=rows.pop(key)
  if off!=cursor or n!=r['bytes']or not n or n>16*1024**2:raise ValueError('1618 extent/size contract')
  ordered.append({**r,'offset':off});cursor+=roundup(n,2048)
 if rows or cursor!=PACK_BYTES or [r['key']for r in ordered]!=sorted(r['key']for r in ordered)or d['expected']['pack_sha256']!=PACK_SHA:raise ValueError('complete7151 membership/hash')
 return head,index,ordered

class Budget:
 """Prospective all-root charge; filesystem queries only every0.2s or forced."""
 def __init__(self,roots,cap,floor,seconds,*,clock=time.perf_counter,free=None,reserve=131072,charge=file_charge):
  self.roots=[Path(r).absolute()for r in roots];self.cap=cap;self.floor=floor;self.seconds=seconds;self.clock=clock;self.free=free or(lambda:shutil.disk_usage('C:\\').free);self.reserve=reserve;self.start=clock();self.last=None;self.sizes={};self.other=0;self.probes=0;self.native={};self.charge=charge
  for i,r in enumerate(self.roots):
   for old in self.roots[:i]:
    if r==old or r.is_relative_to(old)or old.is_relative_to(r):raise ValueError('allocation roots overlap')
 def root_for(self,path):
  path=Path(path).absolute();found=[r for r in self.roots if path.is_relative_to(r)]
  if len(found)!=1:raise ValueError('outside explicit allocation roots')
  return found[0]
 def check(self,path=None,upcoming=0,force=False):
  if self.clock()-self.start>=self.seconds:raise RuntimeError('inner writer deadline reached')
  if upcoming<0:raise ValueError('negative prospective write')
  if path is not None:
   path=safe_path(Path(path),self.root_for(path))
   if path not in self.sizes:raise ValueError('unowned output write')
  if force or self.last is None or self.clock()-self.last>=.2:
   if self.free()<self.floor:raise RuntimeError('fresh C runtime/peer floor breached')
   self.other=0
   for root in self.roots:
    if root.exists():
     for p,n in entries(root):
      if p not in self.sizes:self.other+=self.charge(p,n)
      elif n!=self.sizes[p]:raise RuntimeError('owned partial size changed externally')
      else:self.native[p]=self.charge(p,n)
   self.probes+=1;self.last=self.clock()
  if self.clock()-self.start>=self.seconds:raise RuntimeError('inner deadline reached during filesystem probe')
  charge=self.other+self.reserve+sum(max(roundup(n+(upcoming if p==path else 0),4096),self.native.get(p,0)+(upcoming if p==path else 0))for p,n in self.sizes.items())
  if charge>self.cap:raise RuntimeError('prospective aggregate quota breached')
  return charge
 def claim(self,path):
  path=Path(path).absolute();safe_path(path,self.root_for(path))
  if path.exists()or path.is_symlink()or path in self.sizes:raise FileExistsError('preserve existing output')
  self.sizes[path]=0;return path
 def commit(self,path,n):self.sizes[Path(path).absolute()]+=n
 def published(self,source,target):
  source=Path(source).absolute();target=Path(target).absolute();self.sizes[target]=self.sizes.pop(source);self.native[target]=self.native.pop(source,0)

def source_stream(head,index,rows,guard,binding=None):
 if binding is None:raise ValueError('explicit native C binding required; no fallback')
 return coalesce(_verified_stream(head,index,rows,guard,safe_path=safe_path,chunk=CHUNK,max_shared=8,opener=binding.open),chunk=CHUNK)

def inspect_pack(path,head,index,rows,expected_size,expected_sha,known,guard):
 guard.check(force=True)
 if path.stat().st_size!=expected_size:raise ValueError('pack length differs')
 with path.open('rb')as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ)as view:
  count,crc=known.verify(view)
  if count!=len(rows)or view[:2048]!=head or view[2048:2048+len(index)]!=index:raise ValueError('known reader/header/index gate')
  h=hashlib.sha256()
  for pos in range(0,len(view),CHUNK):guard.check();h.update(view[pos:pos+CHUNK])
  if h.hexdigest()!=expected_sha:raise ValueError('full expected SHA differs')
  for r in rows:
   member=hashlib.sha256()
   for pos in range(r['offset'],r['offset']+r['bytes'],CHUNK):guard.check();member.update(view[pos:min(pos+CHUNK,r['offset']+r['bytes'])])
   if member.hexdigest()!=r['sha256']:raise ValueError('member readback SHA differs')
 return dict(known_reader=True,members=count,index_crc32=crc,sha256=expected_sha,bytes=expected_size,all_member_SHA=True)

def write_one(target,blocks,expected_size,expected_sha,readback,guard):
 target=Path(target).absolute();partial=target.with_name(target.name+'.part')
 if target.exists()or target.is_symlink():raise FileExistsError('preserve existing final')
 guard.claim(partial);h=hashlib.sha256();n=0
 fd=os.open(partial,os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_NOFOLLOW',0),0o600)
 try:
  with os.fdopen(fd,'wb',buffering=0)as out:
   identity=os.fstat(out.fileno())
   for block in blocks:
    if n+len(block)>expected_size:raise ValueError('per-pack byte limit')
    guard.check(partial,len(block));written=out.write(block);guard.commit(partial,written);n+=written;h.update(block[:written])
    if written!=len(block):raise OSError('short output write')
   os.fsync(out.fileno())
 finally:
  close=getattr(blocks,"close",None)
  if close:close()
 if n!=expected_size or h.hexdigest()!=expected_sha:raise ValueError('stream length/expected SHA differs; preserve partial')
 proof=readback(partial);current=partial.stat()
 if(current.st_dev,current.st_ino,current.st_size)!=(identity.st_dev,identity.st_ino,n):raise ValueError('owned verified partial identity changed')
 publish_no_replace(partial,target);guard.published(partial,target);after=target.stat()
 if(after.st_dev,after.st_ino,after.st_size)!=(identity.st_dev,identity.st_ino,n):raise ValueError('published owned identity differs')
 return proof
def copy_blocks(source,guard):
 with source.open('rb')as f:
  for b in iter(lambda:f.read(CHUNK),b''):guard.check();yield b

def allocation(plan_path,plan_sha,path,digest,plan):
 if sha(path)!=digest or sha(plan_path)!=plan_sha:raise ValueError('allocation/plan SHA changed')
 a=json.loads(path.read_text())
 required={'allocated':True,'writer_plan_sha256':plan_sha,'writer_source_sha256':sha(__file__),'aggregate_cap_bytes':CAP,'runtime_floor_bytes':FLOOR,'peer_reserved_bytes':PEER,'inner_seconds':51,'approved_output_root':plan['metadata_root'],'approved_payload_roots':plan['payload_roots'],'prior_failed_controller_sha256':plan['prior_failed_controller_sha256'],'c_source_manifest_path':plan['c_source_manifest_path'],'c_source_manifest_sha256':plan['c_source_manifest_sha256']}
 if any(a.get(k)!=v for k,v in required.items())or not a.get('allocation_id')or a.get('controller_sha256')!=plan['controller_sha256']or not re_hash(plan['controller_sha256']):raise ValueError('exact root child allocation required')
 if a.get('compression_credits'):raise ValueError('new namespace compression credit refused')
 return a
def re_hash(value):return isinstance(value,str)and len(value)==64 and all(c in'0123456789abcdef'for c in value)

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--plan',type=Path,required=True);ap.add_argument('--plan-sha256',required=True);ap.add_argument('--allocation-receipt',type=Path);ap.add_argument('--allocation-sha256');ap.add_argument('--execute',action='store_true');a=ap.parse_args()
 if sha(a.plan)!=a.plan_sha256:raise ValueError('adapter plan changed')
 plan=json.loads(a.plan.read_text());environment(plan)
 if sha(Path(__file__).parent/'root_pack_stream21.py')!=STREAM_HELPER_SHA:raise ValueError('main stream helper changed')
 if set(plan['source_sha256'])!=DEPENDENCIES:raise ValueError('exact source dependency set required')
 for name,h in plan['source_sha256'].items():
  if Path(name).name!=name or sha(Path(__file__).parent/name)!=h:raise ValueError('adapter source dependency changed')
 head,index,rows=resolve(plan);binding=NativeCBinding.load(plan);rows=binding.map_rows(rows);binding.preflight();known_path=local(plan['known_reader']);
 if sha(known_path)!=READER_SHA:raise ValueError('known reader changed')
 spec=importlib.util.spec_from_file_location('reviewed_texpack',known_path);known=importlib.util.module_from_spec(spec);spec.loader.exec_module(known)
 if not a.execute:print(json.dumps(dict(status='CHECK_ONLY_UNALLOCATED',members=len(rows),bytes=PACK_BYTES,sha256=PACK_SHA,large_bytes_written=0)));return
 if os.name!='nt'or a.allocation_receipt is None or not a.allocation_sha256:raise ValueError('native allocated controller invocation required')
 if sha(local(plan['prior_failed_controller_path']))!=plan['prior_failed_controller_sha256']:raise ValueError('preserved failedv1 controller receipt changed')
 root_a=allocation(a.plan,a.plan_sha256,a.allocation_receipt,a.allocation_sha256,plan);payload=[Path(p).absolute()for p in plan['payload_roots']];meta=Path(plan['metadata_root']).absolute()
 if len(payload)!=2 or any(p.exists()or p.is_symlink()for p in payload)or not meta.is_dir():raise ValueError('fresh explicit payload roots/root-prepared metadata required')
 for root in payload:
  if root==meta or root in meta.parents or meta in root.parents:raise ValueError('payload/metadata root overlap')
 for output in payload+[meta]:
  safe_path(output,output)
  for source in {r['source_root'] for r in rows}|{a.plan.parent,known_path.parent,Path(__file__).parent}:
   if output==source or output in source.parents or source in output.parents:raise ValueError('output/source namespaces overlap')
 guard=Budget(payload+[meta],CAP,FLOOR+PEER,51);guard.check(force=True)
 if shutil.disk_usage('C:\\').free<FLOOR+PEER+CAP:raise RuntimeError('fresh complete two-pack admission headroom required')
 result={'status':'FAILED','allocation':root_a,'writer_sha256':sha(__file__),'scope':'Immutable private archive only; no world/programme/target selection'}
 try:
  for root in payload:root.mkdir();json_new(root/'OWNED-PROCESS.json',dict(pid=os.getpid(),writer_sha256=sha(__file__),allocation_id=root_a['allocation_id']))
  inspect=lambda p:inspect_pack(p,head,index,rows,PACK_BYTES,PACK_SHA,known,guard)
  first=payload[0]/'tex.pak';mirror=payload[1]/'tex.pak'
  result['primary']=write_one(first,source_stream(head,index,rows,guard,binding),PACK_BYTES,PACK_SHA,inspect,guard)
  result['mirror']=write_one(mirror,copy_blocks(first,guard),PACK_BYTES,PACK_SHA,inspect,guard)
  with first.open('rb')as x,mirror.open('rb')as y:
   while True:
    guard.check();left=x.read(CHUNK);right=y.read(CHUNK)
    if left!=right:raise ValueError('mirror byte comparison differs')
    if not left:break
  guard.check(force=True);result.update(status='PASS',byte_exact_mirror=True,expensive_probes=guard.probes,all_parent7133_preserved=True,all_new18_immutable=True,c_source_manifest_sha256=plan['c_source_manifest_sha256'],native_C_sources_bound=615)
 except BaseException as exc:
  result['error']=type(exc).__name__+': '+str(exc)
  try:json_new(meta/'child-result.json',result)
  except BaseException as receipt_error:print('receipt failure: '+repr(receipt_error),file=sys.stderr)
  raise
 else:json_new(meta/'child-result.json',result)
 print(json.dumps(result))
if __name__=='__main__':main()
