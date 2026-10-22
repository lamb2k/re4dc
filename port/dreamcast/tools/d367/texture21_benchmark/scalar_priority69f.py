"""Scalar-first polling and completed-stat capture. Read-only; no guest launcher."""
import collections,hashlib,json,struct,time
from observer import Invalid,u32
from observer69f import Coverage,Process04
from phase_latch69f05 import PhaseLatch05

class ScalarProcess(Process04):
 """Retained identity/exit unchanged; add QPC bounds around frozen80ms reads."""
 def set_window(self,deadline):
  self.precise_deadline=deadline
  # Keep the frozen base80ms ceiling. Its GetTickCount64 has15.625ms
  # granularity here, so a translated4ms deadline would reject short valid reads
  # at timer rollovers. The additional QPC before/after bound is strictly4ms.
  self.read_deadline=time.monotonic()+.08
 def read(self,address,size):
  if time.perf_counter()>self.precise_deadline:raise Invalid('precise bounded read window exceeded')
  result=super().read(address,size)
  if time.perf_counter()>self.precise_deadline:raise Invalid('precise bounded read window exceeded')
  return result

class ScalarLatch(PhaseLatch05):
 def peek_ready(self):
  """Three cheap reads are hints only. Full existing latch always decides."""
  raw=self.read(self.address('native_ui.cpp','completed_frame'),8)
  seq,frame=struct.unpack('<II',raw)
  current=self.value('native_ui.cpp','frame');idx=self.value('debug.cpp','proc_tick_idx')
  return bool(seq and not seq&1 and frame==current and 1<=idx<=27)
 def capture_scalar(self):
  def body():
   scene=self.t.scene();raw=self.t.read(self.address('native_ui.cpp','completed_frame'),192)
   ticks=self.t.read(self.address('debug.cpp','proc_tick'),self.vars['debug.cpp:proc_tick']['bytes'])
   names=self.t.read(self.address('debug.cpp','proc_name'),self.vars['debug.cpp:proc_name']['bytes'])
   return {'scene':scene,'completed_native_raw192':raw.hex(),'process_ticks_raw':ticks.hex(),'process_names_raw':names.hex()}
  row=self.capture(body)
  raw=bytes.fromhex(row['body']['completed_native_raw192'])
  if hashlib.sha256(raw).hexdigest()!=row['phase']['completed_sha256']:raise Invalid('completed stats differ from exact phase snapshot')
  fields={n:(raw[o:o+120].hex()if n=='work'else u32(raw,o))for n,o in self.members.items()}
  # source_heap_free remains an unsigned raw word; no signed/type inference.
  row['body']['completed_native_fields']=fields
  row['body']['stats_scope']='Actual69f audited offsets/widths; work is opaque120B, source_heap_free raw32word. Timer fields are target timer observations, not console acceptance or host wall FPS.'
  row['body']['process_marker_scope']='PROCESS CPU and indexed markers are current via existing phase/epoch guard; PROCESS TOTAL slot0 is NOT qualified current here (written after Render_swap). Never sum overlapping rows or derive FPS from these timers.'
  return row

class BufferedRows:
 """No filesystem flush on the sampling path; whole JSON rows remain bounded."""
 def __init__(self,limit=3500000):self.limit=limit;self.rows=[];self.bytes=0
 def emit(self,row):
  b=(json.dumps(row,separators=(',',':'),allow_nan=False)+'\n').encode()
  if self.bytes+len(b)>self.limit:raise Invalid('observer output budget reached')
  self.rows.append(b);self.bytes+=len(b)
 def write(self,path):
  with path.open('xb')as stream:
   for b in self.rows:stream.write(b)

def observe_scalar(proc,latch,binding,cap,seconds,emit,coverage,*,clock=time.perf_counter,precise=time.perf_counter,sleep=time.sleep,cadence=.0005):
 """No table/direct work or disk I/O; all full-latch failures stay failures."""
 import re
 from pathlib import Path
 if not 0<seconds<=41 or not .00025<=cadence<=.001:raise Invalid('scalar observer bounded budget/cadence required')
 start=clock();cpu_start=time.process_time();end=start+seconds;ready=False;polls=0;last_poll=None;max_gap=0.;max_collection=0.;not_ready=0;gap_hist=collections.Counter();epochs=set()
 while clock()<end and proc.live():
  began=precise();now=clock();polls+=1
  if last_poll is not None:
   gap=now-last_poll;max_gap=max(max_gap,gap);gap_hist['<=1ms'if gap<=.001 else'<=2ms'if gap<=.002 else'<=5ms'if gap<=.005 else'>5ms']+=1
  last_poll=now
  if hasattr(proc,'set_window'):proc.set_window(min(end,now+.004))
  else:proc.read_deadline=min(end,now+.004) # deterministic fakeprocess clock domain only
  try:
   if proc.ram is None:
    matches=re.findall(r'RAM\(16 MB\) ([0-9A-Fa-f]+)',(Path(cap)/'flycast.log').read_text(errors='replace'))
    if not matches:raise Invalid('waiting RAM log')
    proc.ram=int(matches[-1],16)
   if not ready:
    for anchor in binding['anchors']:
     if proc.read(anchor['address'],256).hex()!=anchor['hex']:raise Invalid('waiting exact program anchors')
    ready=True;emit({'event':'program_anchors_verified','ram_host_base':proc.ram})
   if not latch.peek_ready():not_ready+=1
   else:
    coverage.attempt();row=latch.capture_scalar();epochs.add(row['phase']['zero_tick'])
    if coverage.accept(row):emit({'event':'completed_scalar_priority_sample','host_elapsed':clock()-start,**row})
  except(Invalid,OSError,struct.error,UnicodeError)as exc:
   coverage.reject(str(exc))
   if str(exc)=='observer output budget reached':break
  max_collection=max(max_collection,precise()-began)
  sleep(max(0.,cadence-(precise()-began)))
 return {'seconds':clock()-start,'observer_process_CPU_seconds':time.process_time()-cpu_start,'polls':polls,'anchors_verified':ready,'hint_not_ready_polls':not_ready,'max_poll_gap_seconds':max_gap,'poll_gap_histogram':dict(gap_hist),'max_collection_seconds':max_collection,'distinct_observed_epoch_count':len(epochs),'coverage':coverage.summary(),'collection_ended':'verified_owned_guest_exit'if getattr(proc,'guest_exit_verified',False)else'observer_budget','owned_guest_exit_code':getattr(proc,'guest_exit_code',None),'cadence_seconds':cadence,'clock_domain':'perf_counter/QPC4ms before+afterread; originalbase80ms monotonic ceiling additionally retained','scope':'Source-qualified successor; no runtime coverage guarantee. No table/direct reads and no synchronous disk output in sampling loop. All pre/post/fulldependency guards unchanged. No FPS or speedup from poll cadence.'}

def cadence_model(period_ns,window_ns,count,poll_ns,read_ns=200000,start_ns=0):
 """Deterministic host scheduling fixture, never emulator/console evidence."""
 now=start_ns;end=count*period_ns;seen=set();polls=0
 while now<end:
  frame=now//period_ns;within=now%period_ns;polls+=1
  if period_ns-window_ns<=within and within+read_ns<period_ns:seen.add(frame)
  now+=max(poll_ns,read_ns)
 return {'seen':sorted(seen),'missing':sorted(set(range(count))-seen),'polls':polls,'scope':'SYNTHETIC_SCHEDULING_MODEL_NOT_GUEST'}
