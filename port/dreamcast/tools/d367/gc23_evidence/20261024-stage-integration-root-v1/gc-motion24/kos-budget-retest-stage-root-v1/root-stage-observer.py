from pathlib import Path
import os,sys,json,subprocess,time,signal,hashlib
HERE=Path(__file__).resolve().parent
KIT=HERE.parent/'kos-budget-retest-media-prep-v2'
SHA='83c68a8de1462a4feb080a48849af396dff769f4a65b37854878c16aa395562e'
assert hashlib.sha256((KIT/'ROOT-STAGE-GRANT.json').read_bytes()).hexdigest()==SHA
g=json.loads((KIT/'ROOT-STAGE-GRANT.json').read_text())
assert g['approved'] and g['scope']=='STAGE_ONLY_NO_GUEST_NO_SDK'
assert hashlib.sha256((KIT/'TOOLCHAIN-SEAL.json').read_bytes()).hexdigest()==g['toolchain_sha256']
assert 600-(time.time()%600)>200,'Quiet window insufficient; no stage launch'
env={'PATH':'/usr/bin:/bin','HOME':'/root','USER':'root','LOGNAME':'root','LANG':'C.UTF-8','GC_BUDGET_RETEST_TOOLS':g['toolchain_sha256'],'GC_CENSUS_STAGE_GRANT_SHA256':SHA}
cmd=['/usr/bin/python3','-I','-S','-B',str(KIT/'launch.py')]
child=None;start=time.monotonic();out={'scope':g['scope'],'grant_sha256':SHA,'argv':cmd,'environment':env,'started_utc':__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()}
def stop(sig,frame):raise InterruptedError('Root stage interrupted '+str(sig))
for sig in [signal.SIGTERM,signal.SIGHUP,signal.SIGINT]:signal.signal(sig,stop)
try:
 with (HERE/'CONTROLLER.log').open('xb') as log:
  child=subprocess.Popen(cmd,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  while child.poll() is None:
   assert time.monotonic()-start<720,'Root host-stage deadline';time.sleep(.5)
  out['returncode']=child.returncode
finally:
 if child:
  try:os.killpg(child.pid,signal.SIGTERM)
  except ProcessLookupError:pass
  try:child.wait(timeout=5)
  except subprocess.TimeoutExpired:pass
  try:os.killpg(child.pid,signal.SIGKILL)
  except ProcessLookupError:pass
  child.wait()
 out['seconds']=time.monotonic()-start
 with (HERE/'PROCESS.json').open('x') as f:json.dump(out,f,indent=2);f.write('\n')
print(json.dumps(out),flush=True)
if out.get('returncode')!=0:raise SystemExit(1)
