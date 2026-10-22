#!/usr/bin/env python3
"""Runtime04 completed-phase coverage observer; read/query only, no guest launcher."""
import argparse,collections,ctypes,hashlib,json,os,re,struct,time
from pathlib import Path
from observer import Process,Invalid
from typed_canonical1004 import TypedCanonical as Typed
from phase_latch69f05 import PhaseLatch05

ELF='69f2e7db588f515f4e6a67455d627a74fc17132d5ca20a591db4e0f15deedcae'
RAW='733afabf6567a9f086eacb48b70559aef764cf52a5b534f44602da3a8bc68a9e'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def load_contract(plan_dir,runtime='observer-runtime-69f',source_dir=None):
 """Fail before OpenProcess on any binding/schema/source dependency mismatch."""
 d=Path(plan_dir)/runtime;source_dir=Path(source_dir or Path(__file__).parent)
 binding=json.loads((d/'binding.json').read_text())
 if binding['namespace']!='observer-runtime-69f' or binding['elf_sha256']!=ELF or binding['program_sha256']!=RAW:raise Invalid('runtime04 identity mismatch')
 if set(binding['source_sha256'])!={'observer.py','typed_canonical1004.py','phase_latch69f.py','phase_latch69f05.py','observer69f.py'}:raise Invalid('runtime04 dependency manifest incomplete')
 for name,h in binding['source_sha256'].items():
  if Path(name).name!=name or sha(source_dir/name)!=h:raise Invalid('observer source dependency changed '+name)
 for name,h in binding['metadata_sha256'].items():
  if Path(name).name!=name or sha(d/name)!=h:raise Invalid('observer metadata changed '+name)
 if sha(Path(plan_dir)/'observation-cold-window.json')!=binding['plan_sha256'] or sha(Path(plan_dir)/'inputs-final/plan-inputs.json')!=binding['inputs_sha256']:raise Invalid('frozen plan inputs changed')
 plan=json.loads((Path(plan_dir)/'observation-cold-window.json').read_text());inputs=json.loads((Path(plan_dir)/'inputs-final/plan-inputs.json').read_text());plan.update({k:inputs[k]for k in ('selected','supplemental_originals','world_original_map')})
 plan['read_only_observer']['typed_layouts']['scene']=json.loads((d/binding['scene_layout']).read_text())
 audit=json.loads((d/binding['phase_audit']).read_text());paths=json.loads((d/binding['path_audit']).read_text())
 if audit['exact_ELF_sha256']!=ELF or paths['exact_ELF_sha256']!=ELF or paths['result']!='PASS' or paths['target_pointer_bytes']!=4:raise Invalid('actual linked ELF path audit failed')
 t=Typed(None,plan);PhaseLatch05(t,audit)
 return binding,plan,audit

class Process04(Process):
 def __init__(self,pid,exe):
  self.h=None;self.sync_h=None;self.guest_exit_verified=False;self.guest_exit_code=None
  try:
   super().__init__(pid,exe)
   self.k.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_ulong];self.k.WaitForSingleObject.restype=ctypes.c_ulong
   self.sync_h=self.k.OpenProcess(0x101000,False,pid)
   if not self.sync_h:raise Invalid('owned synchronize/query handle unavailable')
   ts=[ctypes.c_ulonglong()for _ in range(4)]
   if not self.k.GetProcessTimes(self.sync_h,*[ctypes.byref(x)for x in ts])or ts[0].value!=self.start:raise Invalid('synchronize handle creation time mismatch')
  except BaseException:
   if self.h:self.k.CloseHandle(self.h);self.h=None
   if self.sync_h:self.k.CloseHandle(self.sync_h);self.sync_h=None
   raise
 def live(self):
  def exited():
   status=self.k.WaitForSingleObject(self.sync_h,0)
   if status==258:return False
   if status!=0:raise Invalid('owned synchronize wait failed')
   c=ctypes.c_ulong()
   if not self.k.GetExitCodeProcess(self.sync_h,ctypes.byref(c)):raise Invalid('owned exit code unavailable')
   self.guest_exit_verified=True;self.guest_exit_code=c.value;return True
  if exited():return False
  try:
   if self.times()[0]!=self.start:raise Invalid('owned process creation time changed')
  except Exception:
   # Exit may occur after the first wait but before the identity query.
   # Suppress only a retained-handle-confirmed exit, preserving query errors.
   if exited():return False
   raise
  if exited():return False
  # ExitCodeProcess can change before the retained handle becomes signaled.
  # A nonsignaled, creation-time-verified handle remains pending for next poll.
  return True
 def close(self):
  if self.h:super().close();self.h=None
  if self.sync_h:self.k.CloseHandle(self.sync_h);self.sync_h=None

class Coverage:
 """Keep differing variants; never select a matching row or apply tolerance."""
 def __init__(self,first=240,last=360):
  self.first=first;self.last=last;self.variants={};self.accepted=0;self.attempts=0;self.rejected=collections.Counter();self.diagnostic=collections.Counter();self.table_accepted=0;self.table_rejected=collections.Counter();self.raw_output_complete=True
 def attempt(self,unlatched=None):
  self.attempts+=1
  if unlatched is not None:self.diagnostic[str(unlatched)]+=1
 def reject(self,reason,table=False):
  (self.table_rejected if table else self.rejected)[reason]+=1
  if reason=='observer output budget reached':self.raw_output_complete=False
 def accept(self,row,table=False):
  if table:self.table_accepted+=1;return True
  self.accepted+=1;frame=row['scene']['source_tick']
  stable={'phase':row['phase'],'scene':row['scene'],'cpu_us':row['cpu_us']}
  h=hashlib.sha256(json.dumps(stable,sort_keys=True,allow_nan=False).encode()).hexdigest();vs=self.variants.setdefault(frame,set());new=h not in vs;vs.add(h);return new
 def summary(self):
  need=set(range(self.first,self.last+1));seen=set(self.variants);conflict=sorted(k for k,v in self.variants.items() if len(v)>1)
  return {'attempts':self.attempts,'accepted_attempts':self.accepted,'unique_completed_source_frames':len(seen),'observed_frame_range':[min(seen),max(seen)] if seen else None,'target':[self.first,self.last],'target_missing_frames':sorted(need-seen),'conflicting_frames':conflict,'variant_counts':{str(k):len(v) for k,v in sorted(self.variants.items())},'rejection_counts':dict(self.rejected),'unlatched_attempt_frames':dict(self.diagnostic),'table_accepted':self.table_accepted,'table_rejection_counts':dict(self.table_rejected),'raw_output_complete':self.raw_output_complete,'coverage_pass':need<=seen and not conflict and self.raw_output_complete,'performance_pair_gate':'PENDING: coverage-only; exact paired scene/controls/behavior/identity counters still required'}

class Jsonl:
 def __init__(self,stream,limit=3500000):self.stream=stream;self.limit=limit;self.bytes=0;self.rows=0
 def emit(self,row):
  b=(json.dumps(row,separators=(',',':'),allow_nan=False)+'\n').encode()
  if self.bytes+len(b)>self.limit:raise Invalid('observer output budget reached')
  self.stream.write(b);self.stream.flush();self.bytes+=len(b);self.rows+=1

def collect_one(typed,latch,coverage,table=False):
 """Independent bounded scalar/table channels, each with its own full latch."""
 if table:
  row=latch.capture(lambda:{'scene':typed.scene(),'table':typed.table(),'vram_counters':{n:typed.local(n) for n in ('vram_budget','vram_rejects','vram_retries')},'pvr_state_sha256':hashlib.sha256(typed.read(typed.sym('_pvr_state'),520)).hexdigest()})
 else:row=latch.capture()
 if coverage.accept(row,table):return row
 return None

def observe(proc,typed,latch,binding,cap,seconds,emit,coverage,clock=time.monotonic,precise=time.perf_counter,sleep=time.sleep):
 start=clock();end=start+seconds;ready=False;table_due=0;max_read=0.;iterations=0;anchors=False;last_table=None;direct_seen=set();direct_rejected=collections.Counter();direct_samples=0
 while clock()<end and proc.live():
  begun=precise();proc.read_deadline=min(end,clock()+.08);iterations+=1
  try:
   if proc.ram is None:
    matches=re.findall(r'RAM\(16 MB\) ([0-9A-Fa-f]+)',(Path(cap)/'flycast.log').read_text(errors='replace'))
    if not matches:raise Invalid('waiting RAM log')
    proc.ram=int(matches[-1],16)
   if not ready:
    for anchor in binding['anchors']:
     if proc.read(anchor['address'],256).hex()!=anchor['hex']:raise Invalid('waiting exact program anchors')
    ready=True;anchors=True;emit({'event':'program_anchors_verified','ram_host_base':proc.ram})
   context=None
   try:context=latch.diagnostic()['source_frame_unlatched']
   except Invalid:pass
   coverage.attempt(context)
   row=collect_one(typed,latch,coverage)
   if row:emit({'event':'completed_phase_sample','host_elapsed':clock()-start,**row})
  except (Invalid,OSError,struct.error,UnicodeError) as exc:
   coverage.reject(str(exc))
   if str(exc)=='observer output budget reached':break
  max_read=max(max_read,precise()-begun)
  # Tables have a separate pre/post guard and deadline. A table failure never
  # reclassifies a scalar as valid/invalid or supplies a replacement scalar.
  if ready and clock()>=table_due and clock()<end:
   begun_table=precise();proc.read_deadline=min(end,clock()+.08);table_due=clock()+.2
   try:
    row=collect_one(typed,latch,coverage,True)
    table=row['body']['table'];semantic={**table,'selected':[{k:v for k,v in r.items()if k!='entry_frame'}for r in table['selected']]};table_sha=hashlib.sha256(json.dumps(semantic,sort_keys=True).encode()).hexdigest()
    if table_sha==last_table:row['body']['table']={'unchanged_semantic_sha256':table_sha,'selected_count':len(table['selected']),'valid_slots':table['valid_slots'],'scope':'Fresh coherent table read/re-read; resource payload identical to preceding full table, entry_frame excluded from semantic equality'}
    else:last_table=table_sha;row['body']['table']['semantic_sha256']=table_sha
    emit({'event':'completed_phase_table','host_elapsed':clock()-start,**row})
   except (Invalid,OSError,struct.error,UnicodeError) as exc:
    coverage.reject(str(exc),True)
    if str(exc)=='observer output budget reached':break
   max_read=max(max_read,precise()-begun_table)
  if ready and clock()<end:
   proc.read_deadline=min(end,clock()+.08)
   try:
    direct=typed.witness()
    if direct:
     sig=(direct['key'],direct['ui_frame'],direct['source_frame'],direct['snapshot']['packet_header_before'])
     if sig not in direct_seen:emit({'event':'coherent_CPU_direct_packet','host_elapsed':clock()-start,**direct});direct_seen.add(sig);direct_samples+=1
   except (Invalid,OSError,struct.error,UnicodeError)as exc:
    direct_rejected[str(exc)]+=1
    if str(exc)=='observer output budget reached':coverage.reject(str(exc));break
  sleep(max(.001,.01-(precise()-begun)))
 return {'seconds':clock()-start,'iterations':iterations,'anchors_verified':anchors,'max_collection_seconds':max_read,'coverage':coverage.summary(),'direct_packet_samples':direct_samples,'direct_packet_rejection_counts':dict(direct_rejected),'collection_ended':'verified_owned_guest_exit'if getattr(proc,'guest_exit_verified',False)else'observer_budget','owned_guest_exit_code':getattr(proc,'guest_exit_code',None),'first_cold_partial_evidence_valid_scope':'Incomplete240..360 islatercomparisonOPEN, notfirstfunctionaljobfailure; no performancePASS inferred'}

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--cap',type=Path,required=True);ap.add_argument('--plan',type=Path,required=True);ap.add_argument('--seconds',type=float,default=41);ap.add_argument('--runtime-binding',default='observer-runtime-69f');a=ap.parse_args()
 if not 0<a.seconds<=41:raise SystemExit('budget must be in (0,41] seconds')
 binding,plan,audit=load_contract(a.plan,a.runtime_binding)
 out=a.cap/'phase-observer69f.jsonl';summary=a.cap/'phase-observer69f-summary.json'
 if out.exists() or summary.exists():raise Invalid('preserve existing runtime04 output')
 pid=int((a.cap/'flycast.pid').read_text());exe=a.cap/'flycast.exe'
 if sha(exe)!=binding['emulator_sha256']:raise Invalid('emulator changed')
 proc=Process04(pid,exe);coverage=Coverage();result={'completed':False}
 try:
  if proc.start/1e7-11644473600<(a.cap/'flycast.pid').stat().st_mtime-10:raise Invalid('owned process predates fresh PID receipt')
  typed=Typed(proc.read,plan);latch=PhaseLatch05(typed,audit)
  with out.open('xb') as stream:
   writer=Jsonl(stream);writer.emit({'event':'identity','pid':pid,'start_filetime':proc.start,'exe':proc.path,'binding':binding,'scope':'READ_ONLY_COMPLETED_PHASE_COVERAGE; no death classification, timing gain or console acceptance'})
   result=observe(proc,typed,latch,binding,a.cap,a.seconds,writer.emit,coverage)
   result.update(completed=True,jsonl_bytes=writer.bytes,jsonl_rows=writer.rows)
 finally:
  proc.close();result.update(pid=pid,start_filetime=proc.start,coverage=coverage.summary(),scope='Direct packets are separately coherent CPU staging only; no actualTA/vertices/raster/chosenLOD. Completed state channel requires direct_open0. No fullallocator/highwater/netVRAMsaving proof. Historicalruntime03/04 remain separate.')
  with summary.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
 print(json.dumps(result))
if __name__=='__main__':main()
