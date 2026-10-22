#!/usr/bin/env python3
"""Separate69f scalar-first successor. Read/query only; no game/process launch."""
import argparse,json,os,re
from pathlib import Path
from observer import Invalid
from observer69f import ELF,RAW,Coverage,sha,load_contract
from typed_canonical1004 import TypedCanonical
from scalar_priority69f import ScalarProcess,ScalarLatch,BufferedRows,observe_scalar

NAMESPACE='observer-runtime-69f-scalar-first-01'
def load_successor(plan_dir,runtime=NAMESPACE,source_dir=None):
 root=Path(plan_dir);source_dir=Path(source_dir or Path(__file__).parent)
 b=json.loads((root/runtime/'binding.json').read_text())
 if b['namespace']!=NAMESPACE or b['elf_sha256']!=ELF or b['program_sha256']!=RAW:raise Invalid('successor identity mismatch')
 base_path=b['base_plan_dir']
 if os.name!='nt'and re.match(r'^[A-Za-z]:[\\/]',base_path):base_path='/mnt/'+base_path[0].lower()+base_path[2:].replace('\\','/')
 base_root=Path(base_path)
 if base_root.resolve()!=root.resolve():raise Invalid('successor base metadata must remain in own plan namespace')
 if b['base_runtime']!='observer-runtime-69f'or sha(base_root/b['base_runtime']/'binding.json')!=b['base_binding_sha256']:raise Invalid('frozen base binding changed')
 if set(b['source_sha256'])!={'scalar_priority69f.py','observer69f_scalar_first.py','observer.py','observer69f.py','typed_canonical1004.py','phase_latch69f.py','phase_latch69f05.py'}:raise Invalid('successor dependencies incomplete')
 for n,h in b['source_sha256'].items():
  if Path(n).name!=n or sha(source_dir/n)!=h:raise Invalid('successor source changed '+n)
 base,plan,audit=load_contract(base_root,b['base_runtime'],source_dir)
 if set(b['metadata_sha256'])!=set(base['metadata_sha256']):raise Invalid('successor metadata manifest incomplete')
 for n,h in b['metadata_sha256'].items():
  if Path(n).name!=n or sha(root/runtime/n)!=h or h!=base['metadata_sha256'].get(n):raise Invalid('successor metadata changed '+n)
 if b['plan_sha256']!=base['plan_sha256']or b['inputs_sha256']!=base['inputs_sha256']:raise Invalid('successor plan inputs differ from frozen base')
 for name,member in audit['completed_frame_type']['members'].items():
  matches=[r for r in json.loads((base_root/b['base_runtime']/'runtime69f-path-width-report.json').read_text())['completed_frame_member_paths']if r['member']==name]
  if len(matches)!=1 or matches[0]['offset']!=member or matches[0]['bytes']!=(120 if name=='work'else 4):raise Invalid('completed typed member proof missing')
 for name in('proc_tick','proc_name'):
  if audit['variables']['debug.cpp:'+name]['bytes']!=128:raise Invalid('process array actual target width differs')
 return b,base,plan,audit

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--cap',type=Path,required=True);ap.add_argument('--plan',type=Path,required=True);ap.add_argument('--runtime-binding',default=NAMESPACE);ap.add_argument('--seconds',type=float,default=41);a=ap.parse_args()
 if not 0<a.seconds<=41:raise Invalid('budget must be in (0,41]')
 successor,binding,plan,audit=load_successor(a.plan,a.runtime_binding)
 out=a.cap/'scalar-first69f.jsonl';summary=a.cap/'scalar-first69f-summary.json'
 if out.exists()or summary.exists():raise Invalid('preserve existing successor output')
 pid=int((a.cap/'flycast.pid').read_text());exe=a.cap/'flycast.exe'
 if sha(exe)!=binding['emulator_sha256']:raise Invalid('emulator changed')
 proc=ScalarProcess(pid,exe);coverage=Coverage();buffer=BufferedRows();result={'completed':False}
 try:
  if proc.start/1e7-11644473600<(a.cap/'flycast.pid').stat().st_mtime-10:raise Invalid('owned process predates fresh PID receipt')
  typed=TypedCanonical(proc.read,plan);latch=ScalarLatch(typed,audit)
  buffer.emit({'event':'identity','pid':pid,'start_filetime':proc.start,'exe':proc.path,'successor_binding':successor,'base_binding':binding,'scope':'READ_ONLY_SOURCE_QUALIFIED_SUCCESSOR; no runtime coverage accepted'})
  result=observe_scalar(proc,latch,binding,a.cap,a.seconds,buffer.emit,coverage);result['completed']=True
 finally:
  proc.close();buffer.write(out);result.update(pid=pid,start_filetime=proc.start,jsonl_bytes=buffer.bytes,jsonl_rows=len(buffer.rows),coverage=coverage.summary(),scope='Scalar-first only; no freshkey/table/CPUdirect evidence; no actualTA/chosenLOD/presentation/hardware or timer-derivedFPS proof.')
  with summary.open('x')as f:json.dump(result,f,indent=2);f.write('\n')
 print(json.dumps(result))
if __name__=='__main__':main()
