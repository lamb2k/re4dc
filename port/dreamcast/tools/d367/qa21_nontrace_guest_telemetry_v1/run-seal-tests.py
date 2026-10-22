"""Focused immutable-seal unit; portable fakes plus three tiny Windows Python children."""
import datetime,hashlib,json,os,pathlib,platform,subprocess,sys
P=pathlib.Path(__file__).parent
names=['outer-driver.py','inner-adapter.py','windows-backend.py','guest-supervisor-core.py','input-deadlines.py','guest-profile-v2.json','observer-binding-v2.json','test-failure-telemetry.py','test-seal.py','test-native-seal.py',pathlib.Path(__file__).name]
pins={n:hashlib.sha256((P/n).read_bytes()).hexdigest() for n in names};results=[]
modules=['test-native-seal.py'] if '--native-only' in sys.argv[1:] and os.name=='nt' else ['test-failure-telemetry.py','test-seal.py']+(['test-native-seal.py'] if os.name=='nt' else [])
for name in modules:
 run=subprocess.run([sys.executable,str(P/name)],capture_output=True,text=True);results.append({'module':name,'returncode':run.returncode,'stdout':run.stdout,'stderr':run.stderr})
 if run.returncode:break
assert pins=={n:hashlib.sha256((P/n).read_bytes()).hexdigest() for n in names},'source changed during tests'
r={'scope':'newseal source/fake tests30; onWindows additional3tinyPython child tests; noFlycast/RAM/input/build/image','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'platform':platform.platform(),'python':sys.version,'sources':pins,'selected_modules':modules,'results':results,'pass':all(x['returncode']==0 for x in results),'guest_qualified':False,'old_shoot01_remains_failed':True}
f=P/('seal-receipt-'+platform.system().lower()+'-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json');f.write_bytes((json.dumps(r,indent=2)+'\n').encode());print(json.dumps({'receipt':str(f),'pass':r['pass'],'results':[{k:v for k,v in x.items() if k not in ['stdout','stderr']} for x in results]}));raise SystemExit(0 if r['pass'] else 1)
