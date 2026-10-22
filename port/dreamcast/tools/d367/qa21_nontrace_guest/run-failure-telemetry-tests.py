"""Only the new telemetry exception tests. No emulator, build, stage or RAM access."""
import datetime,hashlib,json,pathlib,platform,subprocess,sys
P=pathlib.Path(__file__).parent
names=['input-deadlines.py','inner-adapter.py','windows-backend.py','guest-supervisor-core.py','test-failure-telemetry.py',pathlib.Path(__file__).name]
pins={n:hashlib.sha256((P/n).read_bytes()).hexdigest() for n in names}
run=subprocess.run([sys.executable,str(P/'test-failure-telemetry.py')],capture_output=True,text=True)
assert pins=={n:hashlib.sha256((P/n).read_bytes()).hexdigest() for n in names},'source changed during tests'
receipt={'scope':'13 NEW telemetry exception tests only; no Flycast/build/stage/input/RAM','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'platform':platform.platform(),'python':sys.version,'argv':[sys.executable,str(P/'test-failure-telemetry.py')],'returncode':run.returncode,'sources':pins,'stdout':run.stdout,'stderr':run.stderr,'guest_qualified':False,'old_failed_run_remains_failed':True,'timing_guards_unchanged':True}
name='failure-telemetry-receipt-'+platform.system().lower()+'-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json'
(P/name).write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'receipt':str(P/name),'returncode':run.returncode,'sources':pins}));raise SystemExit(run.returncode)
