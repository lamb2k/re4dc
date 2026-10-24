from pathlib import Path
import os,sys,json,subprocess,time,signal,hashlib
HERE=Path(__file__).resolve().parent
KIT=HERE.parent/'kos-budget-qa-on-continuation-v1'
assert hashlib.sha256((HERE/'ROOT-GRANT.json').read_bytes()).hexdigest()=='d8bbe8511554d2ddf9ee1af0667e7227fd21fbc8f4f057e78abef88d22ed6f36'
g=json.loads((HERE/'ROOT-GRANT.json').read_text());env={'PATH':'/usr/bin:/bin','HOME':'/root','USER':'root','LOGNAME':'root','LANG':'C.UTF-8','GC_BUDGET_QA_SOURCE':g['source'],'GC_BUDGET_QA_PLAN':g['plan_sha256'],'GC_BUDGET_QA_TOOLS':g['toolchain_sha256']}
for n in ['CONTRACT.json','TOOLCHAIN-SEAL.json']:
 assert hashlib.sha256((KIT/n).read_bytes()).hexdigest()==g['plan_sha256' if n.startswith('CONTRACT') else 'toolchain_sha256']
assert 600-(time.time()%600)>200,'Quiet scheduling window too short; no SDK launched'
cmd=['/usr/bin/bash','-p',str(KIT/'run.sh')];child=None;seen={};start=time.monotonic();report={'scope':g['scope'],'argv':cmd,'environment':env,'grant_sha256':hashlib.sha256((HERE/'ROOT-GRANT.json').read_bytes()).hexdigest()}
def stop(sig,frame):raise InterruptedError('Root SDK observer stopped '+str(sig))
for sig in [signal.SIGTERM,signal.SIGHUP,signal.SIGINT]:signal.signal(sig,stop)
def release_samples():
 for p in Path('/proc').iterdir():
  if not p.name.isdigit():continue
  try:
   a=[x.decode(errors='replace') for x in (p/'cmdline').read_bytes().split(b'\0') if x]
   if not a or Path(a[0]).name not in {'bash','python','python3','python3.12'}:continue
   script=None
   for x in a[1:5]:
    if x in {'-c','-m'}:break
    if x.startswith('-'):continue
    script=x;break
   if not script or Path(script).name not in {'rr-cycle.sh','rr-cycle.py','rr-qa.sh','rr-qa.py','rr-jobs.sh','rr-jobs.py'}:continue
   key=p.name+':'+(p/'stat').read_text().split(') ',1)[1].split()[19]
   if key not in seen:
    row={'pid':int(p.name),'script':script,'executable':a[0],'elapsed_s':time.monotonic()-start,'args':a[1:12]};seen[key]=row
    with (HERE/'RELEASE-OBSERVATIONS.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
  except (FileNotFoundError,ProcessLookupError,PermissionError):continue
try:
 with (HERE/'SDK-CONTROLLER.log').open('xb') as log:
  child=subprocess.Popen(cmd,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  while child.poll() is None:
   release_samples();assert time.monotonic()-start<800,'Root total SDK deadline';time.sleep(.25)
  report['returncode']=child.returncode
finally:
 if child and child.poll() is None:
  try:os.killpg(child.pid,signal.SIGTERM)
  except ProcessLookupError:pass
  try:child.wait(timeout=10)
  except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
 report.update(seconds=time.monotonic()-start,release_observations=list(seen.values()))
 with (HERE/'SDK-PROCESS.json').open('x') as f:json.dump(report,f,indent=2);f.write('\n')
print(json.dumps(report),flush=True)
if report.get('returncode')!=0:raise SystemExit(1)
