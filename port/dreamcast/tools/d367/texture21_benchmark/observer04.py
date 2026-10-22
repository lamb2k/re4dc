#!/usr/bin/env python3
"""Runtime04 completed-phase coverage observer; read/query only, no guest launcher."""
import argparse,collections,hashlib,json,os,re,struct,time
from pathlib import Path
from observer import Typed,Process,Invalid
from phase_latch04 import PhaseLatch04

ELF='e08c9abc8f6bb44bb2a94642fc9a2e664d22039659cea7fcce311cb9989d7433'
RAW='a58579b87da0c45267cb93efe29feea2438da9ddab62d0fe31c47a1c6ff32c71'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def load_contract(plan_dir,runtime='observer-runtime-04',source_dir=None):
 """Fail before OpenProcess on any binding/schema/source dependency mismatch."""
 d=Path(plan_dir)/runtime;source_dir=Path(source_dir or Path(__file__).parent)
 binding=json.loads((d/'binding.json').read_text())
 if binding['namespace']!='observer-runtime-04' or binding['elf_sha256']!=ELF or binding['program_sha256']!=RAW:raise Invalid('runtime04 identity mismatch')
 if set(binding['source_sha256'])!={'observer.py','phase_latch.py','phase_latch04.py','observer04.py'}:raise Invalid('runtime04 dependency manifest incomplete')
 for name,h in binding['source_sha256'].items():
  if Path(name).name!=name or sha(source_dir/name)!=h:raise Invalid('observer source dependency changed '+name)
 for name,h in binding['metadata_sha256'].items():
  if Path(name).name!=name or sha(d/name)!=h:raise Invalid('observer metadata changed '+name)
 if sha(Path(plan_dir)/'observation-cold-window.json')!=binding['plan_sha256'] or sha(Path(plan_dir)/'inputs-final/plan-inputs.json')!=binding['inputs_sha256']:raise Invalid('frozen plan inputs changed')
 plan=json.loads((Path(plan_dir)/'observation-cold-window.json').read_text());plan['selected']=json.loads((Path(plan_dir)/'inputs-final/plan-inputs.json').read_text())['selected']
 plan['read_only_observer']['typed_layouts']['scene']=json.loads((d/binding['scene_layout']).read_text())
 audit=json.loads((d/binding['phase_audit']).read_text());paths=json.loads((d/binding['path_audit']).read_text())
 if audit['exact_ELF_sha256']!=ELF or paths['exact_ELF_sha256']!=ELF or paths['result']!='PASS' or paths['target_pointer_bytes']!=4:raise Invalid('actual linked ELF path audit failed')
 t=Typed(None,plan);PhaseLatch04(t,audit)
 return binding,plan,audit

class Process04(Process):
 def __init__(self,pid,exe):
  self.h=None
  try:super().__init__(pid,exe)
  except BaseException:
   if self.h:self.k.CloseHandle(self.h);self.h=None
   raise
 def close(self):
  if self.h:super().close();self.h=None

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
 start=clock();end=start+seconds;ready=False;table_due=0;max_read=0.;iterations=0;anchors=False
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
    emit({'event':'completed_phase_table','host_elapsed':clock()-start,**row})
   except (Invalid,OSError,struct.error,UnicodeError) as exc:
    coverage.reject(str(exc),True)
    if str(exc)=='observer output budget reached':break
   max_read=max(max_read,precise()-begun_table)
  sleep(max(.001,.01-(precise()-begun)))
 return {'seconds':clock()-start,'iterations':iterations,'anchors_verified':anchors,'max_collection_seconds':max_read,'coverage':coverage.summary()}

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--cap',type=Path,required=True);ap.add_argument('--plan',type=Path,required=True);ap.add_argument('--seconds',type=float,default=41);ap.add_argument('--runtime-binding',default='observer-runtime-04');a=ap.parse_args()
 if not 0<a.seconds<=41:raise SystemExit('budget must be in (0,41] seconds')
 binding,plan,audit=load_contract(a.plan,a.runtime_binding)
 out=a.cap/'phase-observer04.jsonl';summary=a.cap/'phase-observer04-summary.json'
 if out.exists() or summary.exists():raise Invalid('preserve existing runtime04 output')
 pid=int((a.cap/'flycast.pid').read_text());exe=a.cap/'flycast.exe'
 if sha(exe)!=binding['emulator_sha256']:raise Invalid('emulator changed')
 proc=Process04(pid,exe);coverage=Coverage();result={'completed':False}
 try:
  if proc.start/1e7-11644473600<(a.cap/'flycast.pid').stat().st_mtime-10:raise Invalid('owned process predates fresh PID receipt')
  typed=Typed(proc.read,plan);latch=PhaseLatch04(typed,audit)
  with out.open('xb') as stream:
   writer=Jsonl(stream);writer.emit({'event':'identity','pid':pid,'start_filetime':proc.start,'exe':proc.path,'binding':binding,'scope':'READ_ONLY_COMPLETED_PHASE_COVERAGE; no death classification, timing gain or console acceptance'})
   result=observe(proc,typed,latch,binding,a.cap,a.seconds,writer.emit,coverage)
   result.update(completed=True,jsonl_bytes=writer.bytes,jsonl_rows=writer.rows)
 finally:
  proc.close();result.update(pid=pid,start_filetime=proc.start,coverage=coverage.summary(),scope='No SQ witness in completed-state channel: direct_open must be zero. No presentation/all-key raster/full allocator peak proof. Frozen runtime03 evidence remains separate.')
  with summary.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
 print(json.dumps(result))
if __name__=='__main__':main()
