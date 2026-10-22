"""Run source/fixture tests plus tiny Windows child tests; NEVER invokes an emulator."""
import datetime,hashlib,json,os,pathlib,subprocess,sys,time
P=pathlib.Path(__file__).parent;names=['test-observer-v2.py','test-supervisor.py','test-controllers.py','test-capture-budget.py','test-inner-contract.py']
if os.name=='nt':names+=['test-windows-private-job.py']
rows=[]
for name in names:
 start=time.monotonic();r=subprocess.run([sys.executable,str(P/name)],capture_output=True,text=True,timeout=20);rows.append({'test':name,'exit_code':r.returncode,'seconds':time.monotonic()-start,'stdout':r.stdout,'stderr':r.stderr})
receipt={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'source/actual-layout/mock and five tiny Python private-job children only; NO Flycast guest, input, RAM or image writer','tests_expected':50 if os.name=='nt' else 45,'passed':all(r['exit_code']==0 for r in rows),'runs':rows,'source_sha256':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(P.iterdir()) if f.suffix in ('.py','.md','.txt','.json') and f.name not in ['unit-test-receipt.json','source-manifest.json']}}
(P/'unit-test-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',newline='\n');print(json.dumps({'passed':receipt['passed'],'expected_tests':receipt['tests_expected'],'source_files':len(receipt['source_sha256'])}));raise SystemExit(0 if receipt['passed'] else 1)
