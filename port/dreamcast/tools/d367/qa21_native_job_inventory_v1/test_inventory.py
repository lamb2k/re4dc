"""Focused fake-API controls only. No native imports/child launches."""
import ast,copy,importlib.util,pathlib,unittest
P=pathlib.Path(__file__).parent
spec=importlib.util.spec_from_file_location('inventory',P/'inventory.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class API:
 def __init__(self,pids):self.pids=pids
 def job_pids(self,job):return self.pids
class Tests(unittest.TestCase):
 def run_capture(self,pids,inspect):
  records=[]
  def publish(row):records.append(copy.deepcopy(row))
  try:return m.capture(API(pids),123,{'pid':7,'start_filetime':42,'path':'C:/python.exe'},inspect,publish),records,None
  except Exception as exc:return None,records,exc
 def test_raw_persisted_before_member_inspection(self):
  seen=[]
  def inspect(pid):self.assertEqual(len(seen),1);return {'pid':pid}
  result=m.capture(API([7]),1,{'pid':7,'start_filetime':2,'path':'C:/p.exe'},inspect,lambda row:seen.append(copy.deepcopy(row)))
  self.assertTrue(result['strict_membership'])
 def test_extra_member_preserved_before_refusal(self):
  _,rows,error=self.run_capture([7,9],lambda pid:{'pid':pid})
  self.assertIsNotNone(error);self.assertEqual(rows[0]['added'],[9]);self.assertEqual(len(rows[-1]['members']),2)
 def test_missing_expected_preserved(self):
  _,rows,error=self.run_capture([9],lambda pid:{'pid':pid})
  self.assertIsNotNone(error);self.assertEqual(rows[0]['missing'],[7]);self.assertEqual(rows[-1]['member_pids'],[9])
 def test_open_failure_records_error_and_continues_members(self):
  def inspect(pid):raise OSError('captured query failure')
  _,rows,error=self.run_capture([7,9],inspect)
  self.assertIsNotNone(error);self.assertEqual(len(rows[-1]['members']),2);self.assertEqual(rows[-1]['members'][0]['query_error']['type'],'OSError')
 def test_path_birth_survive_later_native_membership_failure(self):
  identity={'pid':7,'start_filetime':42,'path':'C:/python.exe'}
  _,rows,error=self.run_capture([7],lambda pid:{'identity':identity,'query_error':{'text':'not member'}})
  self.assertIsNotNone(error);self.assertEqual(rows[-1]['members'][0]['proof']['identity'],identity)
 def test_exact_backend_and_inner_never_released(self):
  source=(P/'coordinator.py').read_text();tree=ast.parse(source)
  called=[n.func.attr for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)]
  self.assertIn('spawn_waiting',called);self.assertNotIn('release',called);self.assertNotIn('global_count',called)
  self.assertNotIn('write',called);self.assertIn('stop_private_job',called);self.assertIn('wait_private_job_empty',called)
 def test_parent_hard_guard_has_no_io_or_native_query(self):
  tree=ast.parse((P/'supervisor.py').read_text());guard=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='hard_parent')
  calls=[ast.unparse(n.func) for n in ast.walk(guard) if isinstance(n,ast.Call)]
  self.assertEqual(sorted(calls),['done.wait','os._exit'])
 def test_inventory_write_failure_prevents_any_member_query(self):
  calls=[]
  def publish(row):raise OSError('disk unavailable')
  with self.assertRaises(OSError):m.capture(API([7]),1,{'pid':7},lambda pid:calls.append(pid),publish)
  self.assertEqual(calls,[])
if __name__=='__main__':unittest.main()
