from pathlib import Path
import json,hashlib
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18');source=(L/'run-resume-41inner-47absolute-resource-guard-v3.py').read_text();tail=source[source.index('finally:\n')+len('finally:\n'):];tail='\n'.join(x[1:]if x.startswith(' ')else x for x in tail.splitlines());results=[]
for code in [0,9]:
 statuses=[]
 class Watch:
  returncode=code
  def wait(self,timeout):assert timeout==85;results.append(dict(case='driver_failure_with_live_child',watcher_waited=True,timeout=timeout,returncode=code))
  def terminate(self):raise AssertionError('Must never kill watcher')
 class FakeFile:
  def read_text(self):return json.dumps(dict(process_exited=True))
 class FakeCap:
  def __truediv__(self,n):assert n=='owned-resource-guard.json';return FakeFile()
 env=dict(watch=Watch(),cap=FakeCap(),json=json,n=0,status=statuses.append)
 error=None
 try:exec(compile(tail,'<isolated runner finally fault test>','exec'),env)
 except AssertionError as e:error=repr(e)
 assert bool(error)==bool(code);assert len(statuses)==1
 results[-1].update(status=statuses,error=error)
out=L/'runner-v3-isolated-finally-tests.json';assert not out.exists();out.write_text(json.dumps(dict(scope='Isolated real runner finally block, synthetic watcher and receipt; no launch/no real process. Driver-return/failure path must wait watcher, require process_exited and propagate nonzero guard status.',runner_sha256=hashlib.sha256(source.encode()).hexdigest(),results=results),indent=2)+'\n');print(out)
