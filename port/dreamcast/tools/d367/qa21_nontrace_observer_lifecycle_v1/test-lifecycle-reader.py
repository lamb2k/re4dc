"""Captured sparse terminal-control + adversarial host-only pointer fixtures; no native API."""
import copy,hashlib,importlib.util,json,pathlib,struct,tempfile,time,unittest
P=pathlib.Path(__file__).parent;OLD=P.parent/'qa21_nontrace_return_door_v2'
def load(n,f):
 s=importlib.util.spec_from_file_location(n,f);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def resolve(n):
 if __import__('os').name=='nt':return pathlib.Path(n)
 w=pathlib.PureWindowsPath(n);return (pathlib.Path('/mnt/c') if w.drive.lower()=='c:' else pathlib.Path('/'))/pathlib.Path(*w.parts[1:])
a=load('new_reader',P/'observer-v2.py');o=load('new_observe',P/'observe.py');core=load('same_controller',P/'controller-core.py')
fixture=json.loads((P/'captured-terminal-fixture.json').read_text());profile=json.loads((P/'guest-profile-v2.json').read_text());binding=json.loads(resolve(profile['observer']['binding']).read_text());layout=json.loads(resolve(profile['observer']['layout']).read_text());source=json.loads(resolve(binding['source_contract']).read_text())
class Fixture:
 def __init__(self):self.reads={k:bytes.fromhex(v) for k,v in fixture['reads'].items()};self.raw_calls=[];self.reader=a.Reader(self.raw,fixture['observer_symbols'],layout,binding['elf_sha256'],source_contract=source,expected_source=binding['source_candidate'])
 def raw(self,p,n):self.raw_calls.append((p,n));return self.reads[hex(p)+':'+str(n)]
 def pointer(self,which,value):
  r=self.reader;sy=r.sy
  if which=='arm':addr=sy['_ItemMgr']+r.off('cItemMgr','pArm')
  elif which=='body':addr=r.read(sy['_pPL'],'I')+r.off('cPlayer','Body')
  elif which=='system':addr=sy['_pSys']
  else:raise AssertionError(which)
  self.reads[hex(addr)+':4']=struct.pack('<I',value)
 def sample_harness(self,cap,pointer=None,recover=False,post_failure=False,unrelated=False):
  obs=o.Observer.__new__(o.Observer);obs.cap=pathlib.Path(cap);obs.binding=binding;obs.layout=layout;obs.handle=1;obs.ram=1;obs.last=copy.deepcopy(fixture['expected_snapshot']);obs.started=time.monotonic();obs.last_log=0;obs.last_key=None;obs.buffer=None;obs.pid=58596;obs.start=134371191038655230;obs.adapter=o.a.Reader(self.raw,fixture['observer_symbols'],layout,binding['elf_sha256'],source_contract=source,expected_source=binding['source_candidate']);obs.phases=[];obs.bulk=0
  # Production sample uses o.a.RAMRangeError; Reader above deliberately belongs to it.
  original=self.reads.copy()
  def live(p,n):
   if p==0x8c000000 and n==16*1024**2:
    obs.bulk+=1
    if pointer and not(recover and obs.bulk>1):self.pointer(pointer,0xffffffff)
    else:self.reads=original.copy()
    if unrelated:raise ValueError('unrelated transport/ABI failure')
    return b'host-only sparse-fixture bulk token'
   return self.raw(p,n)
  def require(phase):
   obs.phases.append(phase)
   if post_failure and phase.startswith('after snapshot'):obs.last=None;obs.buffer=None;raise EOFError('owned observer PID ended/changed/unavailable '+phase)
  obs.live_read=live;obs.require_live=require;return obs
class Lifecycle(unittest.TestCase):
 def test_actual_terminal_fixture_matches_existing_reader_control_exactly(self):
  f=Fixture();row=f.reader.snapshot();row.update(f.reader.actor_chain());self.assertEqual(row,fixture['expected_snapshot']);self.assertEqual(row['global']['frame'],671);self.assertEqual(row['global']['room'],0x101);self.assertFalse(row['manager_valid']);self.assertEqual(fixture['state_sha256'],'640c9dadddf5b42a5b9b58e2781cbda3b797b0ac439b0ae78b180a10f7986ee0')
 def check_pointer(self,which,typ,member):
  f=Fixture();f.pointer(which,0xffffffff)
  with self.assertRaises(a.RAMRangeError) as cm:f.reader.snapshot()
  d=cm.exception.as_dict();self.assertEqual(d['kind'],'RAMRangeError');self.assertEqual(d['field_context']['structure'],typ);self.assertEqual(d['field_context']['member'],member);self.assertEqual(d['field_context']['base'],'0xffffffff');self.assertGreaterEqual(int(d['address'],16),0xffffffff);self.assertGreater(d['bytes'],0);self.assertTrue(all(0x8c000000<=p<=0x8d000000-n for p,n in f.raw_calls))
 def test_arm_invalid_pointer_records_field_extent_before_any_bad_rawread(self):self.check_pointer('arm','ItemWork','id')
 def test_body_invalid_pointer_records_field_extent_before_any_bad_rawread(self):self.check_pointer('body','cPlBody','pHeadData')
 def test_system_invalid_pointer_records_field_extent_before_any_bad_rawread(self):self.check_pointer('system','SystemWork','region')
 def test_four_invalid_attempts_clear_old_row_no_inputs_no_witness_and_check_post_identity(self):
  with tempfile.TemporaryDirectory() as d:
   f=Fixture();obs=f.sample_harness(d,pointer='arm');obs.sample();row=obs.last;self.assertFalse(row['valid']);self.assertFalse(row['coherent']);self.assertIsNone(obs.buffer);self.assertEqual(row['transport_attempts'],4);self.assertEqual(len(row['discarded_read_failures']),4);self.assertEqual(obs.phases,['before snapshot']+['after snapshot attempt '+str(i) for i in range(1,5)]+['before publish']);self.assertFalse(core.policy.valid_sample(row));door=core.Door();door.held={'fwd'};actions=door.step(row,0,1);self.assertEqual(actions,[{'up':'fwd','reason':'missing/stale/coherence'}]);self.assertFalse(core.Cinematic().step(row,0,1,manual_log=True));self.assertFalse(any('down' in x or 'capture' in x for x in actions));self.assertFalse(core.policy.discharge(fixture['expected_snapshot'],row)['accepted']);self.assertEqual(json.loads((pathlib.Path(d)/'latest-state.json').read_text())['read_failure']['field_context']['member'],'id')
 def test_recovered_second_snapshot_requires_fresh_coherence_and_keeps_failure_context(self):
  with tempfile.TemporaryDirectory() as d:
   obs=Fixture().sample_harness(d,pointer='body',recover=True);obs.sample();self.assertTrue(obs.last['valid']);self.assertTrue(obs.last['transport_coherent']);self.assertEqual(obs.last['transport_attempts'],2);self.assertEqual(len(obs.last['discarded_read_failures']),1);self.assertEqual(obs.last['global']['frame'],671);self.assertNotIn('read_failure',obs.last);self.assertIn('after snapshot attempt 2',obs.phases)
 def test_unrelated_ValueError_remains_fatal_not_invalid_sample(self):
  with tempfile.TemporaryDirectory() as d:
   obs=Fixture().sample_harness(d,unrelated=True)
   with self.assertRaisesRegex(ValueError,'unrelated transport'):obs.sample()
   self.assertFalse((pathlib.Path(d)/'latest-state.json').exists())
 def test_retained_PID_exit_after_failed_read_still_prevents_publish(self):
  with tempfile.TemporaryDirectory() as d:
   obs=Fixture().sample_harness(d,pointer='system',post_failure=True)
   with self.assertRaises(EOFError):obs.sample()
   self.assertIsNone(obs.last);self.assertIsNone(obs.buffer);self.assertFalse((pathlib.Path(d)/'latest-state.json').exists())
 def test_null_optional_pointers_not_zero_accepted_and_no_input_guard_changes(self):
  f=Fixture()
  for n in ['arm','body','system']:f.pointer(n,0)
  row=f.reader.snapshot();self.assertIsNone(row['body']);self.assertIsNone(row['system']);self.assertIsNone(row['weapon']['id']);self.assertFalse(row['weapon']['valid_inventory_slot']);self.assertFalse(core.policy.ordinary_weapon_ready(row))
  for n in ['outer-driver.py','inner-adapter.py','windows-backend.py','guest-supervisor-core.py','input-deadlines.py','controller-core.py','policies.py','layout-contract.py','capture-budget.py','guest-profile-v2.json','exact-log-symbols.json']:self.assertEqual((P/n).read_bytes(),(OLD/n).read_bytes(),n)
if __name__=='__main__':unittest.main(verbosity=2)
