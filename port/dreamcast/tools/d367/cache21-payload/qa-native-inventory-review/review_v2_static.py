"""Focused v2 static review only. No candidate imports/tests/native calls/launches."""
import ast,datetime,hashlib,json,pathlib
Q=pathlib.Path(r'\\wsl.localhost\Ubuntu-24.04\root\probe\codex-qa21-death-repair\port\dreamcast\tools\d367');P=Q/'qa21_native_job_inventory_v2';B=Q/'qa21_native_job_inventory_v1';OUT=pathlib.Path(__file__).parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();fn=lambda p,n:next(x for x in ast.walk(ast.parse(p.read_text())) if isinstance(x,ast.FunctionDef) and x.name==n)
assert sha(P/'manifest.json')=='dd43ac827378e107bf774f03f2be4ad68e51543a16683697f45cb5fd91a23734';assert sha(P/'SOURCE_MANIFEST.json')=='169593e26a5f0b01d82e800cad3ed4a6b678b792bc4210cb7050963ec3f4f3a8';assert sha(P/'LAUNCH_REQUEST.json')=='1de2fa1ae8a4ca01b8b76fb15fe20e8366eadf302dac400d24cec267b060622b'
pins={}
for label,file in [('integrity','SOURCE_MANIFEST.json'),('runtime','manifest.json')]:
 rows=[]
 for row in json.loads((P/file).read_text())['files']:
  p=pathlib.Path(row['path']) if row.get('absolute') else P/row['path'];assert sha(p)==row['sha256'],row['path']
  if 'bytes' in row:assert p.stat().st_size==row['bytes']
  rows.append(dict(path=row['path'],sha256=sha(p),bytes=p.stat().st_size))
 pins[label]=rows
old=json.loads((B/'SOURCE_MANIFEST.json').read_text())
for row in old['files']:assert sha(B/row['path'])==row['sha256']
for n in ['frozen-windows-backend.py','frozen-native-reference-api.py']:assert (P/n).read_bytes()==(B/n).read_bytes()
assert "identity == expected" in ast.unparse(fn(P/'inventory.py','capture'))
assert "backend.inner_identity if pid == backend.inner_identity['pid']" in ast.unparse(fn(P/'coordinator.py','inspect'))
job=ast.unparse(fn(P/'cleanup.py','job_cleanup'));assert "state['private_job_empty'] and state['inner_finalized']" in job and "'job_stop'" in job and 'for name, action' in job
retained=ast.unparse(fn(P/'cleanup.py','retained_cleanup'));assert "state['signaled_finalized']" in retained and 'status == 0' in retained
supermain=ast.unparse(fn(P/'supervisor.py','main'));assert supermain.index("absolute_guard.join(timeout=0.2)")<supermain.index('proc._handle.Close()')
assert "while not finalized['signaled_finalized']" in supermain
spawn=fn(P/'frozen-windows-backend.py','spawn_waiting');spawntext=ast.unparse(spawn);assert 'AssignProcessToJobObject' in spawntext and 'proc.terminate()' in spawntext and 'proc.wait(timeout=2)' in spawntext and 'proc._handle.Close()' in spawntext and 'self.inner = None' in spawntext
# The inherited except/finally drops the only retained Popen HANDLE even if kill/wait throws.
exceptnode=next(n for n in ast.walk(spawn) if isinstance(n,ast.ExceptHandler));killtry=next(n for n in exceptnode.body if isinstance(n,ast.Try));assert any('proc._handle.Close()' in ast.unparse(n) for n in killtry.finalbody)
coverage=[]
for platform in ['linux','windows']:
 p=P/('receipt-'+platform+'.json');r=json.loads(p.read_text());assert r['test_count']==13 and r['status']=='PASS' and r['tests_sha256']==sha(P/'test_inventory.py') and r['runtime_manifest_sha256']==sha(P/'manifest.json');coverage.append(dict(platform=platform,sha256=sha(p),retained_tests=13,current_test_manifest_pins=True,rerun=False))
report=dict(scope='SOURCE/hash/AST/retainedreceipt only; no imports/tests/nativequery/launch/image/state/preflight/allocation',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),candidate='467e3cecb82ae18ea518a029128bf0eb424f38a9',disposition='Three direct repairs verified; remaining inherited unassigned-startup handle-loss gap BLOCKS complete failure-safety disposition',pins=pins,v1_pins_preserved=len(old['files']),retained_coverage=coverage,verified_repairs=['OriginalexpectedPID/birth/path compared afterrawpersistence; nativeexpectedPID proof usesoriginalpin','Pipe/stop/wait/finalization/empty independent; disarm requiresbothjobemptyandinnerfinalized','Supervisor kill errorscaptured; wait/times/status independent; bothguardsjoinbeforeHANDLEclose; pendingretainsHOLD'],explicit_contract_limit='Persistentnativekill/waitdenial is unresolvedHOLD, not unconditional<=5child/<=10parent acceptance; rootactualallocationheld',remaining_finding=dict(id='inherited-unassigned-startup-handle-loss',file='frozen-windows-backend.py',line=spawn.lineno,proof='AssignProcessToJobObject can fail before containment. Exception cleanup terminate/wait may fail; unconditional finally closes proc handle and sets backend.inner=None. No returned coordinatorinner exists; jobempty cantrue and helperinnerNone then safe_to_disarmtrue, without retaining unassigned process.',source=ast.get_source_segment((P/'frozen-windows-backend.py').read_text(),spawn),scope='Same startup termination-failure contract; no observed unassigned child/orphan/native failure or explanation of55368 asserted',required='Root disposition or minimalfixture capture/retain actualPopen HANDLE independently before frozenexception cleanup, with exactbirth/path and no disarmuntilindependentfinalization; do not silently addbroadercontainment'),limitations=['Retained13fakecontrols do not execute nativekernelAPI','Old55368 cause remainsunknown; blocked10c preserved','No unconditionaltimeboundunderpersistentnative refusal hasbeenestablished','No nativefixture/allocation permitted bythissource disposition'])
(OUT/'review-467e3.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(disposition=report['disposition'],integritypins=len(pins['integrity']),runtimepins=len(pins['runtime']),retained_tests_each=13)))