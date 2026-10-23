"""Pinned virtual original base; no recovery, image allocation or process on import."""
from pathlib import Path
import hashlib,importlib.util,json,sys
from contextlib import contextmanager
import contracts as c
SIDECAR=dict(size=79,sha256='45d028c921308a0263a323ddccce96396227b46794e23a61f9b10fb5684214f9')
ORIGINAL=dict(size=c.ORIGINAL_ISO_BYTES,sha256=c.ORIGINAL_ISO_SHA)
MEMBERS={'base.json','track01-template.iso','track02.raw','track03.iso','track03.sha256'}

def verify_metadata():
 seal=c.RECOVERY/'SOURCE-SEAL.json'
 if c.sha(seal)!=c.RECOVERY_SHA:raise ValueError('exact recovery source seal required')
 records={str(seal):c.RECOVERY_SHA}
 for name,row in json.loads(seal.read_text())['files'].items():
  path=c.RECOVERY/name
  if Path(name).name!=name or path.stat().st_size!=row['bytes']or c.sha(path)!=row['sha256']:raise ValueError('recovery source member changed')
  records[str(path)]=row['sha256']
 manifest=c.local(c.VIRTUAL_MANIFEST)
 if c.sha(manifest)!=c.VIRTUAL_MANIFEST_SHA:raise ValueError('exact verified virtual manifest required')
 m=json.loads(manifest.read_text());records[str(manifest)]=c.VIRTUAL_MANIFEST_SHA
 if(m.get('status'),m.get('base_size'),m.get('base_sha256'),m.get('recovery_source_seal_sha256'))!=('EXACT_ORIGINAL_NATIVE_BASE_VIRTUAL_RECONSTRUCTION',c.ORIGINAL_ISO_BYTES,c.ORIGINAL_ISO_SHA,c.RECOVERY_SHA):raise ValueError('virtual original base identity differs')
 expected=dict(path=c.ACTOR_ISO,size=c.ACTOR_ISO_BYTES,sha256=c.ACTOR_ISO_SHA)
 if m.get('actor')!=expected or c.local(c.ACTOR_ISO).stat().st_size!=c.ACTOR_ISO_BYTES:raise ValueError('retained actor dependency differs')
 inverse=c.local(m['inverse_plan']['path']);result=manifest.with_name('recovery-result.json')
 if m['inverse_plan']['sha256']!=c.INVERSE_PLAN_SHA or c.sha(inverse)!=c.INVERSE_PLAN_SHA or c.sha(result)!=c.RECOVERY_RESULT_SHA:raise ValueError('completed recovery proof differs')
 completed=json.loads(result.read_text())
 if completed.get('status')!='EXACT_ORIGINAL_BASE_AND_SELECTED_ARCHIVES_VERIFIED'or completed.get('recovered_base_sha256')!=c.ORIGINAL_ISO_SHA or completed.get('virtual_base_manifest_sha256')!=c.VIRTUAL_MANIFEST_SHA:raise ValueError('actual recovery completion absent')
 for key,expected in(('2158','2c3803b2e938bc3649865b72be6c3304be41a22f88d90b4215b28cba724aec7b'),('813','f46cec291f5f27d53eceaeebd0672e869e0bbad4cd1861e1016faeabb0f30211')):
  if completed['archives'][key]['recovered_target_sha256']!=expected:raise ValueError('original archive recovery incomplete')
 records[str(inverse)]=c.INVERSE_PLAN_SHA;records[str(result)]=c.RECOVERY_RESULT_SHA
 return m,records

def bind_inputs(pin):
 m,records=verify_metadata()
 for path,digest in records.items():pin(dict(path=path,sha256=digest))
 # Full actor hashing belongs to actual helper validation/copy, never import or source controls.
 pin(dict(path=c.ACTOR_ISO,sha256=c.ACTOR_ISO_SHA))
 return dict(path=c.VIRTUAL_MANIFEST,sha256=c.VIRTUAL_MANIFEST_SHA,actor=m['actor'],inverse_plan=m['inverse_plan'],recovery_source_seal_sha256=c.RECOVERY_SHA,recovery_result_sha256=c.RECOVERY_RESULT_SHA)

def logical_inventory(actual,expected):
 """The external cleanup sidecar is preserved separately, never promoted to an original member."""
 if set(expected)!=MEMBERS or expected['track03.iso']!=ORIGINAL:raise ValueError('exact original five-member inventory required')
 wanted={k:v for k,v in expected.items()if k!='track03.iso'};wanted['track03.iso.sha256']=SIDECAR
 if actual!=wanted:raise ValueError('retained physical members/sidecar differ; original ISO must remain absent')
 return dict(expected)

def load_inverse():
 verify_metadata()
 for name in('recover','inverse'):
  path=c.RECOVERY/(name+'.py')
  if name in sys.modules:
   if Path(sys.modules[name].__file__).resolve()!=path.resolve():raise ValueError('foreign recovery module already loaded')
  else:
   spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
 return sys.modules['inverse']

def copy_stream(source,destination,expected,guard=lambda:None):
 """One fresh destination, bounded chunks, exact source length and whole-base hash."""
 h=hashlib.sha256();size=0
 with Path(destination).open('xb')as writer:
  while raw:=source.read(1024**2):
   if not isinstance(raw,bytes)or len(raw)>1024**2 or size+len(raw)>expected['size']:raise ValueError('virtual stream shape/size cap')
   writer.write(raw);h.update(raw);size+=len(raw);guard()
 if dict(size=size,sha256=h.hexdigest())!=expected:raise ValueError('copied virtual original base length/hash differs')
 return dict(size=size,sha256=h.hexdigest())

def copy_original_iso(destination,expected,guard=lambda:None):
 if expected!=ORIGINAL:raise ValueError('exact original base required')
 inverse=load_inverse()
 with inverse.open_verified_base(c.VIRTUAL_MANIFEST,c.VIRTUAL_MANIFEST_SHA)as reader:return copy_stream(reader,destination,expected,guard)

def source_account_roots(work):return(c.HERE,c.PREPARED,c.PREDECESSOR,c.ADAPTER,c.CENSUS,c.MEMORY_REFERENCE,c.RECOVERY,work)

class ReadOnlyComposite:
 """The original four input/LBA proofs over a verified high stream and unchanged low template."""
 base=45000
 raw=False
 def __init__(self,high,low):self.high=high;self.low=low
 def read(self,lba,n=1):
  if type(lba)is not int or type(n)is not int or n<0 or n*2048>2*1024**2:raise ValueError('bounded original composite sector read required')
  result=bytearray()
  for sector in range(lba,lba+n):
   if sector<self.base:raw=self.low.read(sector,1)
   else:self.high.seek((sector-self.base)*2048);raw=self.high.read(2048)
   if len(raw)!=2048:raise ValueError('short original composite sector')
   result.extend(raw)
  return bytes(result)
 def read_bytes(self,lba,size):
  if type(size)is not int or size<0:raise ValueError('exact byte extent required')
  return self.read(lba,(size+2047)//2048)[:size]
 def close(self):self.low.f.close()

@contextmanager
def open_original_composite(fp,template):
 inverse=load_inverse()
 with inverse.open_verified_base(c.VIRTUAL_MANIFEST,c.VIRTUAL_MANIFEST_SHA)as image:
  low=fp.Track(str(template),0)
  if low.raw:low.f.close();raise ValueError('plain unchanged low template required')
  composite=ReadOnlyComposite(image,low)
  try:yield composite
  finally:composite.close()
