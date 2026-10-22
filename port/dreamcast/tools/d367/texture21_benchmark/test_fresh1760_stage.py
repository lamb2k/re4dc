import copy,hashlib,json,os,struct,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import fresh1760_stage as w
from fresh1760_readback import verify_image

def H(b):return hashlib.sha256(b).hexdigest()
class Pins:
 def read(self,path,offset,n):
  with Path(path).open('rb')as f:f.seek(offset);b=f.read(n)
  if len(b)!=n:raise ValueError('truncated fixture')
  return b
class Guard:
 def check(self,*a,**kw):pass

def record(name,extent,size,isdir=False):
 n=33+len(name)+(0 if len(name)%2 else 1);b=bytearray(n);b[0]=n;b[2:10]=w.both32(extent);b[10:18]=w.both32(size);b[25]=2 if isdir else 0;b[28:32]=b'\1\0\0\1';b[32]=len(name);b[33:33+len(name)]=name;return b

class FreshWriterTests(unittest.TestCase):
 def setUp(self):self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
 def tearDown(self):self.temp.cleanup()
 def fixture(self):
  root=self.root;b=bytearray(23*2048);b[16*2048:16*2048+7]=b'\1CD001\1';b[17*2048]=255;b[16*2048+80:16*2048+88]=w.both32(23);r=record(b'\0',45020,2048,True);b[16*2048+156:16*2048+156+len(r)]=r
  files={};patches=[dict(start=16*2048+80,before=w.both32(23).hex(),after=w.both32(25).hex())];rows=[];off=20*2048
  for i,(name,old,new)in enumerate([(b'A.BIN',b'oldA',b'newAAA'),(b'1ST_READ.BIN',b'oldboot',b'newboot')]):
   path='/'+name.decode();rec=record(name,45021+i,len(old));b[off:off+len(rec)]=rec;b[(21+i)*2048:(21+i)*2048+len(old)]=old;files[path]=dict(extent=45021+i,bytes=len(old),sha256=H(old));source=root/('source'+str(i));source.write_bytes(new);rows.append(dict(path=path,start=(23+i)*2048,source_path=str(source),source_offset=0,bytes=len(new),reserved_bytes=2048,sha256=H(new)))
   for delta,before,after in [(2,rec[2:10],w.both32(45023+i)),(10,rec[10:18],w.both32(len(new)))]:patches.append(dict(start=off+delta,before=before.hex(),after=after.hex()))
   off+=len(rec)
  base=root/'base.iso';base.write_bytes(b);baseline=root/'baseline.json';baseline.write_text(json.dumps(dict(files=files)))
  small={}
  for name in ('track01.bin','track02.raw','disc.gdi'):
   f=root/name;f.write_bytes(name.encode());small[name]=dict(path=str(f),bytes=f.stat().st_size,sha256=w.sha(f))
  plan=dict(base=dict(path=str(base),bytes=len(b),sha256=H(b)),baseline=dict(path=str(baseline),sha256=w.sha(baseline)),file_count=2,record_count=2,image_bytes=25*2048,source='SYNTHETIC_NOT_PROGRAMME',programme=dict(programme_sha256='fixture',ELF=dict(sha256='fixture')),held=[],smalltracks=small,arms=dict(M1=dict(append=rows,patches=patches)))
  blob=b''.join(w.stream_image(plan,'M1',Pins(),Guard()));plan['arms']['M1']['predicted']=dict(bytes=len(blob),sha256=H(blob));return plan,blob
 def output(self,blob):p=self.root/'image.iso';p.write_bytes(blob);return p
 def test_relocated_stream_and_independent_full_readback(self):
  p,b=self.fixture();report=verify_image(self.output(b),p,'M1',Guard());self.assertTrue(report['all_file_SHA']);self.assertEqual(report['file_count'],2);self.assertEqual(report['PVD_blocks'],25);self.assertEqual(len(report['explicit_relocated_paths']),2)
 def test_patch_crosses_chunk_boundary(self):
  p,b=self.fixture()
  with patch.object(w,'CHUNK',32770):self.assertEqual(b''.join(w.stream_image(p,'M1',Pins(),Guard())),b)
 def test_before_overlap_outside_and_base_hash_refuse(self):
  p,b=self.fixture()
  for mode in ('before','overlap','outside','basehash'):
   q=copy.deepcopy(p)
   if mode=='before':q['arms']['M1']['patches'][0]['before']='00'*8
   if mode=='overlap':q['arms']['M1']['patches'].append(q['arms']['M1']['patches'][0])
   if mode=='outside':q['arms']['M1']['patches'][0]['start']=p['base']['bytes']+100
   if mode=='basehash':q['base']['sha256']='0'*64
   with self.subTest(mode=mode),self.assertRaises(ValueError):b''.join(w.stream_image(q,'M1',Pins(),Guard()))
 def test_append_gap_sha_reservation_truncation_refuse(self):
  p,b=self.fixture()
  for mode in ('gap','sha','reserve','truncate'):
   q=copy.deepcopy(p);r=q['arms']['M1']['append'][0]
   if mode=='gap':r['start']+=2048
   if mode=='sha':r['sha256']='0'*64
   if mode=='reserve':r['reserved_bytes']=1
   if mode=='truncate':r['source_offset']=999
   with self.subTest(mode=mode),self.assertRaises(ValueError):b''.join(w.stream_image(q,'M1',Pins(),Guard()))
 def test_independent_member_directory_PVD_smalltrack_and_base_refusals(self):
  p,blob=self.fixture()
  for mode in ('member','directory','pvd','small','base'):
   q=copy.deepcopy(p);bad=bytearray(blob)
   if mode=='member':bad[23*2048]^=1
   if mode=='directory':bad[20*2048+18]^=1
   if mode=='pvd':bad[16*2048+90]^=1
   if mode=='small':(self.root/'disc.gdi').write_bytes(b'changed')
   if mode=='base':
    base=Path(q['base']['path']);old=base.read_bytes();base.write_bytes(b'X'+old[1:])
   q['arms']['M1']['predicted']['sha256']=H(bad);out=self.output(bad)
   with self.subTest(mode=mode),self.assertRaises(ValueError):verify_image(out,q,'M1',Guard())
   if mode=='small':(self.root/'disc.gdi').write_bytes(b'disc.gdi')
   if mode=='base':base.write_bytes(old)
 def budget(self):return w.Budget([self.root],1024**2,0,10,free=lambda:2**40,reserve=4096,charge=lambda p,n:(n+4095)//4096*4096)
 def test_write_no_overwrite_and_failed_readback_partial_preserved(self):
  target=self.root/'out';target.write_bytes(b'preserve')
  with self.assertRaises(FileExistsError):w.write_one(target,iter([b'new']),3,H(b'new'),lambda p:{},self.budget())
  self.assertEqual(target.read_bytes(),b'preserve');target=self.root/'failed'
  def reject(p):raise ValueError('independent gate')
  with self.assertRaises(ValueError):w.write_one(target,iter([b'new']),3,H(b'new'),reject,self.budget())
  self.assertFalse(target.exists());self.assertEqual(target.with_name('failed.part').read_bytes(),b'new')
 def test_downstream_guard_failure_closes_generator_immediately(self):
  closed=[]
  def source():
   try:yield b'body'
   finally:closed.append(True)
  class Refuse:
   def claim(self,p):pass
   def check(self,*a):raise RuntimeError('quota')
  with self.assertRaises(RuntimeError):w.write_one(self.root/'fail',source(),4,H(b'body'),lambda p:{},Refuse())
  self.assertEqual(closed,[True]);self.assertEqual((self.root/'fail.part').read_bytes(),b'')
 def test_prospective_cap_and_deadline_refuse(self):
  g=w.Budget([self.root],4096,0,10,free=lambda:2**40,reserve=4096,charge=lambda p,n:0);p=self.root/'x';g.claim(p)
  with self.assertRaises(RuntimeError):g.check(p,1)
  g=w.Budget([self.root],2**20,0,0,free=lambda:2**40)
  with self.assertRaises(RuntimeError):g.check()
 def test_programme_old_source_or_unqualified_before_payload_reads(self):
  with self.assertRaises(ValueError):w.qualified_programme(dict(schema='qualified792-programme-stage-admission-v1',qualified=True,source='old650'))
  with self.assertRaises(ValueError):w.qualified_programme(dict(schema='qualified792-programme-stage-admission-v1',qualified=False,source=w.SOURCE))
 def test_linked_consumer_and_tool_closure_are_required_before_outputs(self):
  a=dict(schema='qualified792-programme-stage-admission-v1',qualified=True,source=w.SOURCE,qualification={},independent={},consumer={},tool_closure={},manifest={})
  q=dict(runtime_source=w.SOURCE,full_source_programme_gate=True,source_inputs_immutable=True);ind=dict(canonical_runtime_source=w.SOURCE,fullprogram_source_gate=True,source_or_external_inputs_changed_during_unit=False)
  for consumer,tool,message in [(dict(source=w.SOURCE,new_programme_qualified=False),{},'consumer'),(dict(source=w.SOURCE,new_programme_qualified=True,all_consumer_gates_qualified=True),dict(source=w.SOURCE,qualified=True,complete_actual_exec_plugin_tool_closure=True,new_unit_pre_post=False),'closure')]:
   with self.subTest(message=message),patch.object(w,'hash_spec',side_effect=[q,ind,consumer,tool,{}]),self.assertRaisesRegex(ValueError,message):w.qualified_programme(a)
 def test_root_allocation_exact_scope_no_credit_and_candidate_first(self):
  controller=self.root/'controller.py';controller.write_text('# synthetic controller not executable allocation\n');plan=self.root/'plan.json';plan.write_text('{}');child=self.root/'child.json';pair=self.root/'pair'
  a=dict(stage_authorized=True,candidate_contract_valid=True,source=w.SOURCE,arm='M1',plan_sha256=w.sha(plan),writer_source_sha256=w.sha(w.__file__),allocation_cap_bytes=w.CAP,metadata_cap_bytes=w.META_CAP,peer_reserved_bytes=w.PEER,runtime_floor_bytes=w.FLOOR,inner_seconds=120,approved_output_root=str(pair/'M1'),controller_path=str(controller),controller_source_sha256=w.sha(controller),allocation_id='SYNTHETIC_NOT_ROOT_AUTHORITY')
  with patch.object(w,'CONTROLLER',str(controller)),patch.object(w,'PAIR_ROOT',str(pair)),patch.object(w,'ALLOCATION_ROOT',str(self.root)):
   child.write_text(json.dumps(a));self.assertEqual(w.root_allocation({},plan,w.sha(plan),child,w.sha(child),'M1')[0],pair/'M1')
   for field,value in [('allocation_cap_bytes',w.CAP+1),('stage_authorized',False),('compression_credits',{'imaginary':1}),('writer_source_sha256','0'*64),('controller_source_sha256','0'*64)]:
    bad={**a,field:value};child.write_text(json.dumps(bad))
    with self.subTest(field=field),self.assertRaises(ValueError):w.root_allocation({},plan,w.sha(plan),child,w.sha(child),'M1')
   a.update(arm='M0',approved_output_root=str(pair/'M0'));child.write_text(json.dumps(a))
   with self.assertRaises(ValueError):w.root_allocation({},plan,w.sha(plan),child,w.sha(child),'M0')
 def test_local_dependency_binding_and_metadata_quota(self):
  sources=self.root/'sources';sources.mkdir();(sources/'fresh1760_stage.py').write_text('import dependency\n');(sources/'fresh1760_readback.py').write_text('');(sources/'dependency.py').write_text('VALUE=1\n');before=w.source_pins(sources);self.assertEqual(set(before),{'fresh1760_stage.py','fresh1760_readback.py','dependency.py'});(sources/'dependency.py').write_text('VALUE=2\n');self.assertNotEqual(before,w.source_pins(sources))
  g=w.StageBudget([self.root],2**20,0,10,free=lambda:2**40,reserve=4096,charge=lambda p,n:(n+4095)//4096*4096);out=self.root/'metadata';g.claim(out)
  with patch.object(w,'META_CAP',4096),self.assertRaises(ValueError):g.check(out,1)
 @unittest.skipUnless(os.name=='nt','native Windows handles')
 def test_native_source_identity_and_mtime_rebinding(self):
  p=self.root/'native';p.write_bytes(b'source');e=dict(path=str(p),bytes=6,sha256=w.sha(p))
  with w.NativePins([e],record=True)as pins:e['native']=pins.proofs[str(p)];self.assertEqual(pins.read(str(p),0,6),b'source')
  with w.NativePins([e])as pins:self.assertEqual(pins.read(str(p),0,6),b'source')
  st=p.stat();os.utime(p,ns=(st.st_atime_ns,st.st_mtime_ns+1000000000))
  with self.assertRaises(ValueError):
   with w.NativePins([e]):pass
if __name__=='__main__':unittest.main(verbosity=2)
