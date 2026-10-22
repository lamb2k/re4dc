from pathlib import Path
import ast,hashlib,json,sys,types,time
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18');p=L/'run-controlled-ch32-drain014.py';tree=ast.parse(p.read_text(encoding='utf-8'));start=next(i for i,n in enumerate(tree.body)if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='watch'for t in n.targets));nodes=[]
for n in tree.body[start:]:
 if isinstance(n,ast.Expr)and isinstance(n.value,ast.Call)and isinstance(n.value.func,ast.Name)and n.value.func.id=='print':break
 nodes.append(n)
class Helper:
 def __init__(self):self.returncode=None;self.terminate_calls=0;self.wait_calls=0
 def poll(self):return self.returncode
 def terminate(self):self.terminate_calls+=1;self.returncode=-15
 def wait(self,timeout):self.wait_calls+=1;return self.returncode
watch=Helper();calls=[]
def popen(*a,**kw):
 calls.append(a)
 if len(calls)==1:return watch
 raise OSError('focused fake observer spawn failure; no child or guest created')
cap=L/'SOURCE-ONLY-NEVER-CREATED-014-CLEANUP-CASE';assert not cap.exists()
ns=dict(subprocess=types.SimpleNamespace(Popen=popen,CREATE_NO_WINDOW=0,TimeoutExpired=TimeoutError),sys=sys,guard='fakeguard.py',observer='fakeobserver.py',cap=cap,D=L,time=time,protected={},sha=lambda p:None)
try:exec(compile(ast.Module(body=nodes,type_ignores=[]),'actual014_wrapper_cleanup','exec'),ns)
except OSError as e:observed=str(e)
else:raise AssertionError('Expected mocked spawn failure')
assert len(calls)==2 and watch.terminate_calls==1 and watch.wait_calls==1 and ns['harness_started']is False and ns['obs']is None
r=dict(scope='ONE focused actual-wrapper AST control case with fake helpers only. Zero spawned OS processes/Flycast/guest/ownership/files. Does not qualify live kernel stalls or guest cleanup.',wrapper_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),expected_exception=observed,helper_Popen_calls=2,started_fake_watcher_terminate_calls=watch.terminate_calls,started_fake_watcher_wait_calls=watch.wait_calls,harness_started=False,PASS=True)
(L/'controlled-ch32-drain014-startup-cleanup-source-case.json').write_text(json.dumps(r,indent=2)+'\n');print('PASS single fake-helper spawn-failure case; no process or guest')
