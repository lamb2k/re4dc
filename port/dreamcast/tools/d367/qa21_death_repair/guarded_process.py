"""Owned process supervision with exception-safe cleanup; no unrelated process actions."""
import json,os,signal,subprocess,time
from pathlib import Path

def identity(pid):
 text=Path('/proc/'+str(pid)+'/stat').read_text(); tail=text[text.rfind(')')+2:].split()
 return {'pid':pid,'pgid':int(tail[2]),'proc_start':tail[19]}

def stop_owned(child, owned):
 if child.poll() is not None:return
 now=identity(child.pid)
 assert now=={k:owned[k] for k in ('pid','pgid','proc_start')}, 'Owned child identity changed'
 assert now['pgid']==child.pid
 os.killpg(child.pid,signal.SIGTERM)
 try:child.wait(timeout=8)
 except subprocess.TimeoutExpired:
  # Recheck the exact leader before escalation; never signal a reused group.
  assert identity(child.pid)==now
  os.killpg(child.pid,signal.SIGKILL);child.wait()

def run_guarded(cmd,cwd,env,stream,sample,owned_path,tick=.25):
 child=subprocess.Popen(cmd,cwd=cwd,env=env,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
 owned=None;reason=None
 try:
  owned=identity(child.pid);assert owned['pgid']==child.pid
  owned.update(argv=cmd,scope='Only this exact PID/PGID/proc_start may be stopped')
  Path(owned_path).write_text(json.dumps(owned,indent=2)+'\n')
  while child.poll() is None:
   reason=sample()
   if reason:break
   time.sleep(tick)
  if reason:stop_owned(child,owned)
  return child.wait(),reason,owned
 finally:
  if child.poll() is None:
   # This also covers identity/receipt/sampler exceptions immediately after spawn.
   if owned is None:owned=identity(child.pid)
   stop_owned(child,owned)
