"""Portable independently supervised guest lifecycle, backend retained handles/job.
No filesystem or native API is hidden here; fake backend verifies every exit path.
"""
ABSOLUTE=47.5;INPUT_RELEASE=40.75;INNER=41;CAP=60000000;ADMISSION=18*1024**3+128*1024**2;RUNTIME=18*1024**3+64*1024**2

def monitor(backend,cmd,after_spawn=None):
 job=None;inner=None;guest=None;identity=None;result={'qualified':False};released=False
 try:
  if backend.free()<ADMISSION:raise RuntimeError('fresh disk admission')
  if backend.global_count()>=16:raise RuntimeError('global16 admission')
  job=backend.create_private_job();inner=backend.spawn_waiting(cmd,job)
  if after_spawn:after_spawn(inner)
  backend.arm_deadlines(inner);backend.release(inner)
  while True:
   backend.check_deadlines()
   if backend.free()<RUNTIME:raise RuntimeError('runtime disk floor')
   if backend.evidence_bytes()>=CAP:raise RuntimeError('60MB evidence cap')
   if backend.global_count()>16:raise RuntimeError('global16 overflow')
   found=backend.find_guest()
   if found is not None:
    now=backend.identity(found)
    if guest is None:guest=found;identity=now
    if now!=identity:raise RuntimeError('PID/start/path identity changed')
    elapsed=backend.actual_seconds(guest)
    if elapsed>=INPUT_RELEASE and not released:backend.release_inputs(guest);released=True
    if elapsed>=ABSOLUTE:raise RuntimeError('absolute47.5s cap')
   if not backend.inner_alive(inner):
    backend.wait(inner);result['qualified']=backend.exit_code(inner)==0;break
   backend.tick()
  backend.check_deadlines()
  if guest is None:raise RuntimeError('no owned guest observed')
  if backend.guest_alive(guest):raise RuntimeError('guest outlived runner')
  actual=backend.actual_seconds(guest)
  if actual>ABSOLUTE:raise RuntimeError('actual process exceeded47.5s')
  result.update(actual_guest_seconds=actual,input_release_before41=released,identity=identity)
 except BaseException as error:result.update(qualified=False,error=type(error).__name__+': '+str(error))
 finally:
  # Each cleanup attempt is independent; even failed pipe/wait/identity operations
  # cannot skip private-job termination, remaining waits or final handle closure.
  def cleanup(label,fn):
   try:fn()
   except BaseException as error:
    result['qualified']=False;result.setdefault('cleanup_errors',[]).append(label+': '+type(error).__name__+': '+str(error))
  # Keep the independent hard deadline armed until private-job termination.
  if job is not None:cleanup('private job stop',lambda:backend.stop_private_job(job))
  if inner is not None:cleanup('pipe close',lambda:backend.close_release_pipe(inner))
  if guest is not None:
   def release_owned():
    if backend.identity(guest)!=identity:raise RuntimeError('refuse foreign guest input cleanup')
    backend.release_inputs(guest)
   cleanup('input release',release_owned)
  if inner is not None:cleanup('inner wait',lambda:backend.wait(inner))
  if guest is not None:cleanup('guest wait',lambda:backend.wait_guest(guest))
  def retain_exit_telemetry():
   reporter=getattr(backend,'final_process_telemetry',None)
   if reporter is None:
    result['process_telemetry']={'available':False,'reason':'backend has no retained process telemetry provider'};return
   try:result['process_telemetry']=reporter()
   except BaseException as error:
    result['process_telemetry']={'available':False,'reason':type(error).__name__+': '+str(error)};raise
   if result['process_telemetry'].get('available'):
    result['identity']=result['process_telemetry']['identity'];result['actual_guest_seconds']=result['process_telemetry']['actual_guest_seconds']
    if result['actual_guest_seconds']>ABSOLUTE:raise RuntimeError('final retained process exceeded47.5s')
  # Diagnostic failures cannot skip cleanup or change a failed run into PASS.
  cleanup('retained exit telemetry',retain_exit_telemetry)
  job_empty=job is None
  if job is not None:
   def confirm_empty():
    nonlocal job_empty
    backend.wait_private_job_empty(job);job_empty=True
   cleanup('private job empty',confirm_empty)
  if job_empty:cleanup('deadline join',backend.stop_deadlines)
  else:result.update(qualified=False,hard_deadline_retained='private job emptiness not established; do not disarm live guard')
  cleanup('handle close',lambda:backend.close_owned_handles(job,inner,guest))
 return result
