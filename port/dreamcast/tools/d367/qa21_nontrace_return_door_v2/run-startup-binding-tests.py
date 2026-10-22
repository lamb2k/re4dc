"""Focused binding source tests only; no nativechild/guest invocation."""
import datetime,hashlib,json,pathlib,platform,subprocess,sys
P=pathlib.Path(__file__).parent
names=['test-startup-binding.py','run-startup-binding-tests.py','inner-adapter.py','exact-log-symbols.json','runtime-source-proof.json','guest-profile-v2.json']
pins={n:hashlib.sha256((P/n).read_bytes()).hexdigest() for n in names}
r=subprocess.run([sys.executable,str(P/'test-startup-binding.py')],capture_output=True,text=True)
assert pins=={n:hashlib.sha256((P/n).read_bytes()).hexdigest() for n in names}
row={'scope':'5NEW focused actual-local startup data binding tests only; no guest/nativechild/RAM/input','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'platform':platform.platform(),'sources':pins,'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'guest_qualified':False}
f=P/('binding-tests-'+platform.system().lower()+'-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json');assert not f.exists();f.write_bytes((json.dumps(row,indent=2)+'\n').encode());print(json.dumps({'receipt':str(f),'returncode':r.returncode}));raise SystemExit(r.returncode)
