"""Focused actual local startup binding tests; never invoke runner/watch/main."""
import ast,hashlib,json,pathlib,unittest
P=pathlib.Path(__file__).parent;O=P.parent/'qa21_nontrace_return_door_v1';V=P.parent/'qa21_nontrace_guest_telemetry_v1'
RUNTIME=['outer-driver.py','inner-adapter.py','windows-backend.py','guest-supervisor-core.py','input-deadlines.py','controller-core.py','policies.py','observe.py','observer-v2.py','layout-contract.py','capture-budget.py']
def startup(p):
 tree=ast.parse((P/'inner-adapter.py').read_text());nodes=[n for n in ast.walk(tree) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in {'logs','syms'} for t in n.targets)]
 assert len(nodes)==2
 env={'P':p,'json':json};exec(compile(ast.fix_missing_locations(ast.Module(body=sorted(nodes,key=lambda n:n.lineno),type_ignores=[])),'<actual-inner-symbol-startup>','exec'),env);return env

def local_dependencies():
 rows=[]
 for name in RUNTIME:
  for n in ast.walk(ast.parse((P/name).read_text())):
   if isinstance(n,ast.BinOp) and isinstance(n.op,ast.Div) and isinstance(n.left,ast.Name) and n.left.id=='P' and isinstance(n.right,ast.Constant) and isinstance(n.right.value,str):rows.append((name,n.lineno,n.right.value))
   if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='with_name' and len(n.args)==1 and isinstance(n.args[0],ast.Constant):rows.append((name,n.lineno,n.args[0].value))
 return rows
class Binding(unittest.TestCase):
 def test_blocked_old_target_reproduces_missing_read_and_preserved_seal(self):
  self.assertFalse((O/'exact-log-symbols.json').exists())
  with self.assertRaises(FileNotFoundError):startup(O)
  self.assertEqual(hashlib.sha256((O/'source-manifest.json').read_bytes()).hexdigest(),'8d06f482b0a4587aef90a610e2b2db132fa0fb9a09c015496f7f93e836d5f500')
 def test_actual_startup_assignments_succeed_without_watch_or_runner(self):
  e=startup(P);self.assertEqual(e['syms'],' '.join(hex(e['logs'][n][0]['address']-0x8c000000) for n in ['_re4dc_logbuf','_re4dc_log_head','_re4dc_stage']));self.assertNotIn('runner',e);self.assertNotIn('thread',e)
 def test_local_metadata_exact_v1_elf_and_required_unambiguous_object_symbols(self):
  f=P/'exact-log-symbols.json';self.assertEqual(f.read_bytes(),(V/f.name).read_bytes());r=json.loads(f.read_text());self.assertEqual(r['elf_sha256'],'248dd4aac7c4e22a7a18a0183fc6409401fddf610d98881c90dd9664e342640b');self.assertEqual(set(r['symbols']),{'_re4dc_logbuf','_re4dc_log_head','_re4dc_stage'})
  for n,size in [('_re4dc_logbuf',65536),('_re4dc_log_head',4),('_re4dc_stage',4)]:
   self.assertEqual(len(r['symbols'][n]),1);row=r['symbols'][n][0];self.assertEqual((row['bytes'],row['type']),(size,'STT_OBJECT'));self.assertGreaterEqual(row['address'],0x8c000000)
 def test_all_actual_literal_local_dependencies_exist_and_are_byteexact_v1(self):
  rows=local_dependencies();self.assertTrue(any(n=='exact-log-symbols.json' for _,_,n in rows));self.assertTrue(any(n=='layout-contract.py' for _,_,n in rows))
  for source,line,name in rows:
   if name=='source-manifest.json':continue # generated last; exact manifest closure checked separately
   self.assertTrue((P/name).is_file(),(source,line,name));expected=(V/name).read_bytes()
   if name=='controller-core.py':expected=expected.replace(b"key='a';hold=.2;self.attempts+=1",b"key='a';hold=.15;self.attempts+=1")
   self.assertEqual((P/name).read_bytes(),expected,(source,line,name))
 def test_all_runtime_profile_bytes_and_only_contact_delta_unchanged(self):
  for n in RUNTIME:self.assertEqual((P/n).read_bytes(),(O/n).read_bytes(),n)
  self.assertEqual((P/'guest-profile-v2.json').read_bytes(),(V/'guest-profile-v2.json').read_bytes());self.assertEqual(hashlib.sha256((P/'guest-profile-v2.json').read_bytes()).hexdigest(),'4c386fa2fd826d2b04f7bf5b8696dca3e339dd92485c11b8ec91b863d21ce99b')
if __name__=='__main__':unittest.main(verbosity=2)
