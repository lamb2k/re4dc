#!/usr/bin/env python3
"""Bounded immutable1600 writer adapter. Default resolves only; root allocation required."""
import argparse,ctypes,hashlib,importlib.util,json,mmap,os,shutil,stat,struct,sys,time,zlib
from pathlib import Path
from file_charge import entries,publish_no_replace,roundup,safe_path
from mipmap_pair_plan import local

PARENT_SEAL='51d6bf3bc48c7f244fbdf14a3ff813738e117ecc7b7e6c50bbac3e1bed1296c7'
DELTA_SEAL='12a8a1f817f888635c6be0eedfa531a73a616d057c282527997e405db71a4b4d'
PACK_SHA='d7fed6373143961f232eb99df952afefd301010529ed8e62149a2023d0244b6e'
PACK_BYTES=160122880;CAP=332828672;FLOOR=18*1024**3+64*1024**2;PEER=64*1024**2
READER_SHA='199fb53bc3855ba3c831e4f9013c1e8fd4383cf36615803cbc29acacedcf5bbf'
CHUNK=1048576
DEPENDENCIES={'immutable_append1600_writer.py','file_charge.py','mipmap_pair_plan.py'}
def file_charge(path,n):
 logical=roundup(n,4096)
 if os.name!='nt':return logical
 k=ctypes.WinDLL('kernel32',use_last_error=True);k.GetCompressedFileSizeW.argtypes=[ctypes.c_wchar_p,ctypes.POINTER(ctypes.c_uint32)];k.GetCompressedFileSizeW.restype=ctypes.c_uint32
 high=ctypes.c_uint32();ctypes.set_last_error(0);low=k.GetCompressedFileSizeW(str(path),ctypes.byref(high))
 if low==0xffffffff and ctypes.get_last_error():return logical # UNC unsupported: no credit.
 return max(logical,low+(high.value<<32))
def sha(path):
 with Path(path).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def json_new(path,value):
 with path.open('x')as f:json.dump(value,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
def sealed(root,digest):
 if sha(root/'SHA256SUMS')!=digest:raise ValueError('immutable composition seal changed')
 for line in(root/'SHA256SUMS').read_text().splitlines():
  h,name=line.split('  ',1);rel=Path(name)
  if rel.is_absolute()or'..'in rel.parts or sha(root/rel)!=h:raise ValueError('composition metadata changed '+name)

def resolve(plan):
 parent=local(plan['parent1596']);delta=local(plan['delta1600']);sealed(parent,PARENT_SEAL);sealed(delta,DELTA_SEAL)
 p=json.loads((parent/'plan/PLAN.json').read_text());d=json.loads((delta/'plan/PLAN1600.json').read_text())
 if d['expected']['pack_sha256']!=PACK_SHA or d['expected']['pack_bytes']!=PACK_BYTES:raise ValueError('wrong1600 family')
 base=local(p['base']['path']);rows={};appended={r['key']:r for r in json.loads((parent/'plan/APPENDED-592.json').read_text())};roots={n:local(v)for n,v in p['append']['roots'].items()};roots['next4']=local(d['four']['path'])
 for line in(parent/'plan/MEMBERS-7129.tsv').read_text().splitlines():
  key,n,h,_off,old,source=line.split('\t')
  if key in rows:raise ValueError('duplicate inherited key')
  r=dict(key=key,bytes=int(n),sha256=h,source=source)
  if source=='canonical1004':r.update(path=base,source_root=base.parent,source_offset=int(old),descriptor_hex=None,body_crc32=None)
  else:
   meta=appended[key];r.update(path=safe_path(roots[source]/meta['relative_path'],roots[source]),source_root=roots[source],source_offset=0,descriptor_hex=meta['descriptor_hex'],body_crc32=meta['body_crc32'])
  rows[key]=r
 for meta in json.loads((delta/'plan/APPENDED-4.json').read_text()):
  key=meta['key']
  if key in rows:raise ValueError('new immutable key collides')
  rows[key]=dict(key=key,bytes=meta['bytes'],sha256=meta['sha256'],source='next4',path=safe_path(roots['next4']/meta['relative_path'],roots['next4']),source_root=roots['next4'],source_offset=0,descriptor_hex=meta['descriptor_hex'],body_crc32=meta['body_crc32'])
 head=(delta/'plan/expected-header.bin').read_bytes();index=(delta/'plan/expected-index.bin').read_bytes()
 if len(head)!=2048 or len(index)!=56*2048 or head[:8]!=b'RE4PAK1\0'or struct.unpack_from('<5I',head,8)!=(1,7133,2048,116736,zlib.crc32(index)&0xffffffff)or any(head[28:])or any(index[7133*16:]):raise ValueError('header/index contract')
 ordered=[];cursor=116736
 for i in range(7133):
  a,b,off,n=struct.unpack_from('<4I',index,i*16);key='%08x-%08x'%(a,b);r=rows.pop(key)
  if off!=cursor or n!=r['bytes']or not n or n>16*1024**2:raise ValueError('extent or size contract')
  ordered.append({**r,'offset':off});cursor+=roundup(n,2048)
 if rows or cursor!=PACK_BYTES or [r['key']for r in ordered]!=sorted(r['key']for r in ordered):raise ValueError('complete sorted membership')
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

def source_stream(head,index,rows,guard):
 yield head;yield index
 for r in rows:
  path=Path(r['path']);safe_path(path,r['source_root'])
  if path.is_symlink():raise ValueError('symlink source refused')
  digest=hashlib.sha256();crc=0;done=0
  with path.open('rb')as src:
   src.seek(r['source_offset'])
   while done<r['bytes']:
    guard.check();b=src.read(min(CHUNK,r['bytes']-done))
    if not b:raise ValueError('source member truncated')
    if done==0 and r.get('descriptor_hex')is not None:
     if len(b)<144 or b[:8]!=b'RE4DCTX\0'or b[48:144].hex()!=r['descriptor_hex']or struct.unpack_from('<I',b,36)[0]!=r['body_crc32']:raise ValueError('sealed append descriptor/header changed')
    if r.get('descriptor_hex')is not None:crc=zlib.crc32(b[max(0,48-done):],crc)
    digest.update(b);done+=len(b);yield b
  if digest.hexdigest()!=r['sha256']or(r.get('descriptor_hex')is not None and crc&0xffffffff!=r['body_crc32']):raise ValueError('immutable member SHA/bodyCRC changed')
  if r['bytes']%2048:yield bytes((-r['bytes'])%2048)

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
 with os.fdopen(fd,'wb',buffering=0)as out:
  identity=os.fstat(out.fileno())
  for block in blocks:
   if n+len(block)>expected_size:raise ValueError('per-pack byte limit')
   guard.check(partial,len(block));written=out.write(block);guard.commit(partial,written);n+=written;h.update(block[:written])
   if written!=len(block):raise OSError('short output write')
  os.fsync(out.fileno())
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
 required={'allocated':True,'writer_plan_sha256':plan_sha,'writer_source_sha256':sha(__file__),'aggregate_cap_bytes':CAP,'runtime_floor_bytes':FLOOR,'peer_reserved_bytes':PEER,'inner_seconds':51,'approved_output_root':plan['metadata_root'],'approved_payload_roots':plan['payload_roots']}
 if any(a.get(k)!=v for k,v in required.items())or not a.get('allocation_id')or a.get('controller_sha256')!=plan['controller_sha256']or not re_hash(plan['controller_sha256']):raise ValueError('exact root child allocation required')
 if a.get('compression_credits'):raise ValueError('new namespace compression credit refused')
 return a
def re_hash(value):return isinstance(value,str)and len(value)==64 and all(c in'0123456789abcdef'for c in value)

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--plan',type=Path,required=True);ap.add_argument('--plan-sha256',required=True);ap.add_argument('--allocation-receipt',type=Path);ap.add_argument('--allocation-sha256');ap.add_argument('--execute',action='store_true');a=ap.parse_args()
 if sha(a.plan)!=a.plan_sha256:raise ValueError('adapter plan changed')
 plan=json.loads(a.plan.read_text())
 if set(plan['source_sha256'])!=DEPENDENCIES:raise ValueError('exact source dependency set required')
 for name,h in plan['source_sha256'].items():
  if Path(name).name!=name or sha(Path(__file__).parent/name)!=h:raise ValueError('adapter source dependency changed')
 head,index,rows=resolve(plan);known_path=local(plan['known_reader']);
 if sha(known_path)!=READER_SHA:raise ValueError('known reader changed')
 spec=importlib.util.spec_from_file_location('reviewed_texpack',known_path);known=importlib.util.module_from_spec(spec);spec.loader.exec_module(known)
 if not a.execute:print(json.dumps(dict(status='CHECK_ONLY_UNALLOCATED',members=len(rows),bytes=PACK_BYTES,sha256=PACK_SHA,large_bytes_written=0)));return
 if os.name!='nt'or a.allocation_receipt is None or not a.allocation_sha256:raise ValueError('native allocated controller invocation required')
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
  result['primary']=write_one(first,source_stream(head,index,rows,guard),PACK_BYTES,PACK_SHA,inspect,guard)
  result['mirror']=write_one(mirror,copy_blocks(first,guard),PACK_BYTES,PACK_SHA,inspect,guard)
  with first.open('rb')as x,mirror.open('rb')as y:
   while True:
    guard.check();left=x.read(CHUNK);right=y.read(CHUNK)
    if left!=right:raise ValueError('mirror byte comparison differs')
    if not left:break
  guard.check(force=True);result.update(status='PASS',byte_exact_mirror=True,expensive_probes=guard.probes,all_current6537_preserved=True,all_new596_immutable=True)
 except BaseException as exc:
  result['error']=type(exc).__name__+': '+str(exc)
  try:json_new(meta/'child-result.json',result)
  except BaseException as receipt_error:print('receipt failure: '+repr(receipt_error),file=sys.stderr)
  raise
 else:json_new(meta/'child-result.json',result)
 print(json.dumps(result))
if __name__=='__main__':main()
