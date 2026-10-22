"""Changed candidate-image controller guards only; no native child/image jobs."""
import ast,copy,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import owned_windows_fresh1760_image_job as c

class ImageControllerTests(unittest.TestCase):
 def setUp(self):self.temp=tempfile.TemporaryDirectory();self.base=Path(self.temp.name)
 def tearDown(self):self.temp.cleanup()
 def save(self,name,data):
  p=self.base/name;p.write_text(json.dumps(data));return p
 def bindings(self):
  parent=self.base/'parent';parent.write_bytes(b'data-seal');source=self.base/'source';source.write_bytes(b'source-seal');writer=self.base/'writer.py';writer.write_text('#synthetic');reader=self.base/'reader.py';reader.write_text('#synthetic reader');eh='a'*64;bh='b'*64
  q=dict(ELF_sha256=eh,programme_sha256=bh);ind=dict(q);consumer=dict(q,source=c.SOURCE,new_programme_qualified=True,all_consumer_gates_qualified=True);tool=dict(source=c.SOURCE,qualified=True,complete_actual_exec_plugin_tool_closure=True,new_unit_pre_post=True);m=dict(runtime_source=c.SOURCE,ELF=dict(sha256=eh),programme_sha256=bh)
  refs={}
  for n,r in [('qualification',q),('independent',ind),('consumer',consumer),('tool_closure',tool),('manifest',m)]:p=self.save(n+'.json',r);refs[n]=dict(path=str(p),sha256=c.sha(p))
  admission=self.save('admission.json',dict(schema='qualified792-programme-stage-admission-v1',qualified=True,source=c.SOURCE,**refs));ip=self.save('image-plan.json',dict(schema='fresh1760-paired-image-plan-v1',source=c.SOURCE,programme=m,data_unit=dict(path=str(parent),sha256=c.sha(parent)),programme_admission=dict(path=str(admission),sha256=c.sha(admission)),arms=dict(M1=dict(predicted=dict(bytes=4096,sha256='c'*64))),image_bytes=4096,proposal=dict(exact_uncompressed_forecast_bytes=16781312),source_sha256={writer.name:c.sha(writer),reader.name:c.sha(reader)}))
  plan=dict(expected_image_bytes=4096,expected_image_sha256='c'*64,uncompressed_forecast_bytes=16781312,source=c.SOURCE,arm='M1',image_plan_path=str(ip),image_plan_sha256=c.sha(ip),programme_admission_path=str(admission),programme_admission_sha256=c.sha(admission),ELF_sha256=eh,programme_sha256=bh,consumer_sha256=refs['consumer']['sha256']);inputs={str(p):c.sha(p)for p in(parent,source,writer,reader,ip,admission)};inputs.update({r['path']:r['sha256']for r in refs.values()});constants=dict(PARENT_SEAL=parent,PARENT_SEAL_SHA=c.sha(parent),SOURCE_SEAL=source,SOURCE_SEAL_SHA=c.sha(source),WRITER=writer,WRITER_SHA=c.sha(writer),READER=reader,READER_SHA=c.sha(reader));return plan,inputs,constants
 def test_exact_future_image_programme_consumer_metadata_join(self):
  p,i,k=self.bindings()
  with patch.multiple(c,**k):self.assertEqual(c.require_image_bindings(p,i)['image_bytes'],4096)
 def test_missing_mismatched_null_or_changed_future_identities_refuse(self):
  p,i,k=self.bindings()
  with patch.multiple(c,**k):
   for field in('ELF_sha256','programme_sha256','consumer_sha256','image_plan_sha256'):
    for value in(None,'0'*64):
     q={**p,field:value}
     with self.subTest(field=field,value=value),self.assertRaises((ValueError,KeyError)):c.require_image_bindings(q,i)
   for field,value in(('arm','M0'),('source','old650')):
    with self.subTest(field=field),self.assertRaises(ValueError):c.require_image_bindings({**p,field:value},i)
 def validate_fixture(self):
  root=self.base/'candidate';root.mkdir();allocdir=self.base/'alloc';allocdir.mkdir();exe=self.base/'python.exe';exe.write_bytes(b'SYNTHETIC_NOT_EXECUTABLE');writer=self.base/'writer.py';writer.write_text('#synthetic');controller_sha=c.sha(c.__file__);child=allocdir/'child.json';imageplan=self.base/'bound.json';imageplan.write_text('{}');a=dict(stage_authorized=True,candidate_contract_valid=True,source=c.SOURCE,arm='M1',plan_sha256=c.sha(imageplan),writer_source_sha256=c.sha(writer),allocation_cap_bytes=c.PACK_CAP,metadata_cap_bytes=c.METADATA_CAP,peer_reserved_bytes=67108864,runtime_floor_bytes=c.BASE_FLOOR,inner_seconds=120,approved_output_root=str(root),controller_path=str(Path(c.__file__).absolute()),controller_source_sha256=controller_sha,allocation_id='SYNTHETIC_NO_AUTHORITY');child.write_text(json.dumps(a));outputs=[str(root/'gdemu')]+[str(root/'gdemu'/n)for n in('track01.bin','track02.raw','disc.gdi','track03.iso')]+[str(root/'full-readback.json'),str(root/'child-result.json')];plan=dict(schema='fresh1760-candidate-controller-plan-v1',approved_output_root=str(root),approved_payload_roots=[],receipt=str(root/'controller.json'),log=str(root/'controller.log'),new_outputs=outputs,argv=[str(exe),str(writer),'write','--plan',str(imageplan),'--plan-sha256',c.sha(imageplan),'--allocation',str(child),'--allocation-sha256',c.sha(child),'--arm','M1'],cwd=str(self.base),input_sha256={str(exe):c.sha(exe),str(writer):c.sha(writer),str(child):c.sha(child)},child_allocation_path=str(child),child_allocation_sha256=c.sha(child),image_plan_path=str(imageplan),image_plan_sha256=c.sha(imageplan),absolute_seconds=130,inner_seconds=120,peer_reserved_bytes=67108864,max_output_bytes=c.PACK_CAP,metadata_cap_bytes=c.METADATA_CAP,log_limit_bytes=1024,ELF_sha256='a'*64,programme_sha256='b'*64,consumer_sha256='c'*64,programme_admission_sha256='d'*64)
  pp=allocdir/'plan.json';pp.write_text(json.dumps(plan));a=dict(allocated=True,plan_sha256=c.sha(pp),controller_sha256=controller_sha,approved_output_root=str(root),allocation_id='SYNTHETIC_NO_AUTHORITY',approved_payload_roots=[],max_output_bytes=c.PACK_CAP,metadata_cap_bytes=c.METADATA_CAP,peer_reserved_bytes=67108864,runtime_floor_bytes=c.BASE_FLOOR+67108864,writer_source_sha256=c.sha(writer),child_allocation_sha256=c.sha(child),data_unit_seal_sha256=c.PARENT_SEAL_SHA,source_unit_seal_sha256=c.SOURCE_SEAL_SHA);a.update({k:plan[k]for k in('image_plan_sha256','programme_admission_sha256','ELF_sha256','programme_sha256','consumer_sha256')});ap=allocdir/'outer.json';ap.write_text(json.dumps(a));return plan,pp,ap,dict(PRODUCTION=root,ALLOCATIONS=allocdir,WRITER=writer,WRITER_SHA=c.sha(writer))
 def test_fixed_candidate_paths_argv_and_limits(self):
  plan,pp,ap,k=self.validate_fixture()
  with patch.multiple(c,**k),patch.object(c,'require_cache_environment',return_value={}),patch.object(c,'require_image_bindings',return_value={}):
   self.assertEqual(c.validate(pp,c.sha(pp),ap,c.sha(ap))[1],k['PRODUCTION'])
   mutations=[('approved_output_root',str(self.base/'M0')),('approved_payload_roots',[str(self.base/'mirror')]),('max_output_bytes',c.PACK_CAP+1),('metadata_cap_bytes',c.METADATA_CAP+1),('schema','wrong'),('absolute_seconds',131),('inner_seconds',121),('argv',plan['argv']+['--extra']),('new_outputs',plan['new_outputs'][:-1])]
   for key,value in mutations:
    q={**plan,key:value};pp.write_text(json.dumps(q))
    with self.subTest(key=key),self.assertRaises(ValueError):c.validate(pp,c.sha(pp),ap,c.sha(ap))
 def test_plan_builder_emits_only_metadata_exact_child_argv_nooverwrite(self):
  import types
  import fresh1760_controller_plan as h
  plan,pp,ap,k=self.validate_fixture();install=self.base/'controller.py';install.write_bytes(Path(c.__file__).read_bytes());refs={}
  for name in('qualification','independent','consumer','tool_closure','manifest'):
   f=self.save('builder-'+name+'.json',{});refs[name]=dict(path=str(f),sha256=c.sha(f))
  ad=self.save('builder-admission.json',refs);ip=self.save('builder-image.json',dict(programme_admission=dict(path=str(ad),sha256=c.sha(ad)),programme=dict(ELF=dict(sha256='a'*64),programme_sha256='b'*64),source_sha256={},image_bytes=4096,arms=dict(M1=dict(predicted=dict(sha256='c'*64))),proposal=dict(exact_uncompressed_forecast_bytes=16781312)))
  child=Path(plan['child_allocation_path']);ca=json.loads(child.read_text());ca.update(controller_path=str(install),controller_source_sha256=c.sha(install),plan_sha256=c.sha(ip));child.write_text(json.dumps(ca));parent=self.base/'data-seal';parent.write_text('sourcefixture');seal=self.base/'source-seal';seal.write_text('sourcefixture');out=k['ALLOCATIONS']/'built-plan.json';exe=Path(plan['argv'][0])
  with patch.multiple(c,**k,PARENT_SEAL=parent,SOURCE_SEAL=seal),patch.object(c,'require_image_bindings',return_value={}),patch.object(h,'INSTALL',install),patch.object(h,'os',types.SimpleNamespace(name='nt',fsync=os.fsync)):
   r=h.build(ip,c.sha(ip),child,c.sha(child),exe,out);written=json.loads(out.read_text());self.assertEqual(written['argv'],[str(exe),str(k['WRITER']),'write','--plan',str(ip),'--plan-sha256',c.sha(ip),'--allocation',str(child),'--allocation-sha256',c.sha(child),'--arm','M1']);self.assertEqual(r['status'],'METADATA_PLAN_ONLY_NO_OUTPUTS_OR_JOB');self.assertFalse((k['PRODUCTION']/'gdemu').exists())
   with self.assertRaises(ValueError):h.build(ip,c.sha(ip),child,c.sha(child),exe,out)
 def test_changed_metadata_and_aggregate_charge_counts_native_allocation(self):
  tree=ast.parse(Path(c.__file__).read_text());run=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='run');fn=next(n for n in run.body if isinstance(n,ast.FunctionDef)and n.name=='size_tree');root=self.base/'charge';root.mkdir();(root/'gdemu').mkdir();(root/'gdemu/image.part').write_bytes(b'x');(root/'log').write_bytes(b'm')
  class FakeC:
   @staticmethod
   def set_last_error(n):pass
   @staticmethod
   def get_last_error():return 0
  class D:
   def __init__(self):self.value=0
  class Native:
   @staticmethod
   def GetCompressedFileSizeW(path,high):return 8192
  FakeC.byref=lambda x:x
  scope=dict(root=root,plan=dict(approved_payload_roots=[]),Path=Path,D=D,C=FakeC,k=Native(),result=dict(unsupported_unc_allocation={}),FINAL_METADATA_HEADROOM=0,METADATA_CAP=8192)
  exec(compile(ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])),'<actualsize_tree>','exec'),scope);self.assertEqual(scope['size_tree'](),16384)
  scope['METADATA_CAP']=8191
  with self.assertRaisesRegex(RuntimeError,'metadata'):scope['size_tree']()
 def test_core_native_lifecycle_source_is_inherited(self):
  old=Path(c.__file__).parent/'accepted1760_controller_reference.py'
  if not old.exists():old=Path('/mnt/c/Game Dev/Emulators/codex-lanes/castle-controls21/owned-windows-1760-native-c-pack-job.py')
  if not old.exists():self.skipTest('reference supplied in sealed unit')
  def f(path):return {n.name:ast.dump(n,include_attributes=False)for n in ast.parse(path.read_text()).body if isinstance(n,ast.FunctionDef)}
  before=f(old);after=f(Path(c.__file__))
  for name in('sha','canonical','within','require_cache_environment','native','main'):self.assertEqual(before[name],after[name],name)
  def nested(path):
   run=next(n for n in ast.parse(path.read_text()).body if isinstance(n,ast.FunctionDef)and n.name=='run');return {n.name:ast.dump(n,include_attributes=False)for n in run.body if isinstance(n,ast.FunctionDef)}
  before=nested(old);after=nested(Path(c.__file__))
  for name in before:
   if name!='size_tree':self.assertEqual(before[name],after[name],name)
if __name__=='__main__':unittest.main(verbosity=2)
