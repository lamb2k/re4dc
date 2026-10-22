"""Focused v4 source/hash/AST only: startupflag and allocation accounting."""
import ast,datetime,hashlib,json,pathlib
Q=pathlib.Path(r'\\wsl.localhost\Ubuntu-24.04\root\probe\codex-qa21-death-repair\port\dreamcast\tools\d367');P=Q/'qa21_native_job_inventory_v4';B=Q/'qa21_native_job_inventory_v3';OUT=pathlib.Path(__file__).parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();fn=lambda p,n:next(x for x in ast.walk(ast.parse(p.read_text())) if isinstance(x,ast.FunctionDef) and x.name==n);dump=lambda n:ast.dump(n,include_attributes=False)
assert sha(P/'manifest.json')=='031077676c334cb7989039c53bbcdbb0153e9b6ff93590d93a4eec71f73ac115';assert sha(P/'SOURCE_MANIFEST.json')=='be81ef2badd38aa735f5a34811ac792a472638fc35cddc87927ec1917a58a968';assert sha(P/'LAUNCH_REQUEST.json')=='e6df4294699d9762bfa23d62166b22b788e6d891136f4ba5f2924e31a78a9d0f'
pins={}
for label,file in [('integrity','SOURCE_MANIFEST.json'),('runtime','manifest.json')]:
 rows=[]
 for row in json.loads((P/file).read_text())['files']:
  p=pathlib.Path(row['path']) if row.get('absolute') else P/row['path'];assert sha(p)==row['sha256'],row['path']
  if 'bytes' in row:assert p.stat().st_size==row['bytes']
  rows.append(dict(path=row['path'],sha256=sha(p),bytes=p.stat().st_size))
 pins[label]=rows
exact=['coordinator.py','cleanup.py','inventory.py','frozen-windows-backend.py','frozen-native-reference-api.py']
for n in exact:assert (P/n).read_bytes()==(B/n).read_bytes(),n
assert (P/'startup.py').read_text()==(B/'startup.py').read_text().replace('subprocess.CREATE_NO_WINDOW','subprocess.DETACHED_PROCESS')
for n in ['hard_parent','sha']:assert dump(fn(P/'supervisor.py',n))==dump(fn(B/'supervisor.py',n)),n
old=(B/'supervisor.py').read_text();expected=old.replace("def load_cleanup():\n    spec=importlib.util.spec_from_file_location('fixture_cleanup',P/'cleanup.py');", "def load_module(name):\n    spec=importlib.util.spec_from_file_location(name,P/(name+'.py'));").replace("cleanup=load_cleanup();", "cleanup=load_module('cleanup');")
start=expected.index('    k.GetCompressedFileSizeW.argtypes=');end=expected.index('    proc=None;',start)
expected=expected[:start]+"    allocation=load_module('allocation');api=load_module('frozen-native-reference-api').WindowsApi()\n    def usage():return allocation.measure(api,root)\n"+expected[end:]
assert (P/'supervisor.py').read_text()==expected
charge=fn(P/'allocation.py','file_charge');text=ast.unparse(charge)
assert 'CreateFileW(str(path), 128, 7, None, 3, 2097152, None)' in text and "value['attributes'] & 1024" in text and "value['deleted']" in text and "value['directory']" in text and "value['size'] < 0" in text and "value['allocated'] < 0" in text and "max(value['size'], value['allocated'])" in text
assert any(isinstance(n,ast.Try) and n.finalbody and 'api.close(h)' in ast.unparse(n.finalbody[0]) for n in ast.walk(charge))
measure=ast.unparse(fn(P/'allocation.py','measure'));assert 'total = 4096' in measure and 'total += 4096' in measure
coverage=[]
for platform in ['linux','windows']:
 p=P/('receipt-'+platform+'.json');r=json.loads(p.read_text());assert r['test_count']==8 and r['status']=='PASS' and r['runtime_manifest_sha256']==sha(P/'manifest.json')
 for n,h in r['tests'].items():assert sha(P/n)==h
 coverage.append(dict(platform=platform,sha256=sha(p),retained_tests=8,current_test_manifest_pins=True,rerun=False))
request=json.loads((P/'LAUNCH_REQUEST.json').read_text());sites=json.loads((P/'CONSOLE_LAUNCH_SITES.json').read_text())
report=dict(scope='SOURCE/hash/AST/retainedreceipt only; no imports/tests/nativequery/launch/image/state/preflight/allocation',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),candidate='86f54d1c0adc49b31406d8c076c546fe57505557',disposition='CLEAR focused detached startup/allocation-source correction; no native04 allocation or fulljob qualification',pins=pins,exact_v3=exact,startup_exact_only_creationflag_change=True,supervisor_exact_only_loader_and_nativeallocation_measure_change=True,file_charge_source=ast.get_source_segment((P/'allocation.py').read_text(),charge),measure_directory_charge=4096,retained_coverage=coverage,retained_console_sites=sites,limitations=['StrictPIDmembership/retainedidentity/refusal/cleanup/HOLD unchanged; no conhost allowance','Directorycharging is declared4096perdirectory; no genericdirectorytreeoradversarialnamespacecertification bythisfocusedreview','FILE_STANDARD_INFO nativeinteroperability/new04 outcome stillrequiresrootallocation','Observed03conhost supportscandidate motivation but doesnotidentifyold55368cause','Laterin-jobtasklist/readerNO_WINDOW sites notexercised: unreleasedstartup04 cannotqualifyfullreleasedjob/IPC/game','Native-success5s/10s conditionalbound; persistentdenialHOLD/no unconditionalPASS','No actualfileallocation/nativeimage/state/exequery performed byreviewer'])
(OUT/'review-86f54.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(disposition=report['disposition'],integritypins=len(pins['integrity']),runtimepins=len(pins['runtime']),exactv3=len(exact),retained_tests_each=8)))