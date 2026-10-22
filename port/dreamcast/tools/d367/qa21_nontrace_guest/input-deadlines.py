"""Independent per-key queue deadlines; never takes observer/controller/capture lock.
Only the provided owned native post callback can send input. No process/RAM API here.
"""
import threading,time
class Inputs:
 def __init__(self,post,elapsed,fail,clock=time.monotonic,timer=threading.Timer):
  self.post=post;self.elapsed=elapsed;self.fail=fail;self.clock=clock;self.timer=timer;self.lock=threading.RLock();self.held={};self.events=[];self.timers=[];self.closed=False
 def down(self,key,bound):
  with self.lock:
   if self.closed:raise RuntimeError('input lease closed')
   if key in self.held or not 0<bound<=1.5:raise RuntimeError('invalid/duplicate bounded down')
   token={'start':self.clock(),'bound':bound};self.held[key]=token
   delay=max(0,bound-min(.02,bound/4));task=self.timer(delay,lambda:self.expire(key,token));task.daemon=True;token['timer']=task;self.timers.append(task);task.start()
   try:self.post(key,False)
   except BaseException:
    try:self._up(key,'failed-down cleanup')
    finally:raise
   return self.elapsed()
 def _up(self,key,reason):
  token=self.held.get(key)
  if token is None:return
  self.post(key,True);end=self.clock();released=self.elapsed();token['timer'].cancel();del self.held[key]
  event={'key':key,'reason':reason,'elapsed':released,'queue_hold_upper_seconds':end-token['start'],'bound':token['bound']};self.events.append(event)
  if event['queue_hold_upper_seconds']>token['bound']:
   error=RuntimeError('native keyup queued after declared pulse bound: '+key);self.fail(error);raise error
 def up(self,key):
  with self.lock:self._up(key,'engine-up')
 def expire(self,key,token):
  try:
   with self.lock:
    if self.held.get(key) is token:self._up(key,'deadline')
  except BaseException as error:self.fail(error)
 def release_all(self,reason):
  errors=[]
  with self.lock:
   for key in list(self.held):
    try:self._up(key,reason)
    except BaseException as error:errors.append(error)
   if self.held:errors.append(RuntimeError('held inputs remain; capture prohibited'))
  if errors:raise RuntimeError('; '.join(str(e) for e in errors))
 def drain(self):
  with self.lock:events=self.events;self.events=[];return events
 def keys(self):
  with self.lock:return set(self.held)
 def close(self):
  error=None
  with self.lock:self.closed=True
  try:self.release_all('inner-close')
  except BaseException as e:error=e
  for task in self.timers:task.cancel()
  for task in self.timers:
   if task is not threading.current_thread():
    task.join(timeout=2)
    if task.is_alive():error=RuntimeError('input deadline thread did not join')
  if error:raise error

def release_before_capture(inputs,synchronize,capture):
 inputs.release_all('before-capture');synchronize(True)
 if inputs.keys():raise RuntimeError('capture cannot start with held input')
 return capture()
