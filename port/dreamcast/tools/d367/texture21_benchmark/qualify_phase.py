#!/usr/bin/env python3
"""Exercise all actual ELF-bound phase paths in synthetic RAM; never attaches to a process."""
import argparse,json,struct,hashlib
from pathlib import Path
from observer import Typed,ram_range,Invalid
from phase_latch import PhaseLatch

def main():
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('--plan',type=Path,required=True);a.add_argument('--audit',type=Path,required=True);a.add_argument('--out',type=Path,required=True);a=a.parse_args();audit=json.loads(a.audit.read_text());plan=json.loads((a.plan/'observation-cold-window.json').read_text());plan['selected']=json.loads((a.plan/'inputs-final/plan-inputs.json').read_text())['selected'];plan['read_only_observer']['typed_layouts']['scene']=json.loads((a.plan/'observer-runtime-03/scene-existing-dwarf02.json').read_text());raw=bytearray(16777216)
 def read(addr,n):off=ram_range(addr,n);return bytes(raw[off:off+n])
 def put(addr,b):off=ram_range(addr,len(b));raw[off:off+len(b)]=b
 def w(addr,n):put(addr,struct.pack('<I',n))
 t=Typed(read,plan);pg=0x8c700000;pl=0x8c710000;w(t.sym('_pG'),pg);w(t.sym('_pPL'),pl);G=t.t['scene']['types']['GlobalWork']['members'];w(pg+G['Frame_cnt'],10);put(pg+G['Rno0'],b'\3');put(pg+G['room_id'],struct.pack('<H',0x103));l=PhaseLatch(t,audit)
 def var(cu,name,n):rec=audit['variables'][cu+':'+name];put(rec['symbol']['address'],bytes([n]) if rec['bytes']==1 else struct.pack('<I',n))
 for name,n in [('frame',10),('source_draws_finished',1),('frame_ready',1),('ui_order',0),('stream_aborted',0),('pace_skip_frame',0),('pace_skipped_frames',0),('direct_open',0)]:var('native_ui.cpp',name,n)
 var('pace.cpp','re4dc_pace_skipping',0);var('debug.cpp','proc_tick_idx',20);var('debug.cpp','zero_tick',123)
 put(0x8c720000,b'SndWatcher\0');put(0x8c720080,b'PROCESS CPU\0');w(l.address('debug.cpp','proc_name')+24*4,0x8c720000);w(l.address('debug.cpp','proc_name')+8,0x8c720080);w(l.address('debug.cpp','proc_tick')+8,40500)
 stats=l.address('native_ui.cpp','completed_frame');w(stats,2);w(stats+4,10);w(stats+184,1);w(stats+188,0);result=l.capture();assert result['cpu_us']==1000 and result['scene']['source_tick']==10
 rejects=[]
 for label,addr,value,restore in [('stale completed snapshot',stats+4,9,10),('odd sequence',stats,3,2),('next iteration reset',l.address('debug.cpp','proc_tick_idx'),0,20)]:
  w(addr,value)
  try:l.capture();raise AssertionError('invalid marker admitted '+label)
  except Invalid:rejects.append(label)
  w(addr,restore)
 with a.out.open('x') as f:json.dump({'result':'PASS','audit_sha256':hashlib.sha256(a.audit.read_bytes()).hexdigest(),'scope':'All scalar/array/string/192B stats/scene paths use actual e08c CU/type/address bindings in synthetic RAM; no live process or guest','positive':result,'negative_cases':rejects,'runtime_coverage':'UNQUALIFIED; no default observer integration'},f,indent=2);f.write('\n')
 print('Exact ELF phase/scene path dry-run PASS')
if __name__=='__main__':main()
