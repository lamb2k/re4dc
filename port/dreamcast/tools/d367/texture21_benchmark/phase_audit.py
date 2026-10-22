#!/usr/bin/env python3
"""Offline exact-ELF inventory for an existing post-update read-only phase latch."""
import argparse,hashlib,json,re,struct,subprocess
from pathlib import Path
from audit_observer_elf import dies
from dwarf_layout import parse
ELF='e08c9abc8f6bb44bb2a94642fc9a2e664d22039659cea7fcce311cb9989d7433'

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--elf',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--readelf',default='/opt/toolchains/dc/sh-elf/bin/sh-elf-readelf');ap.add_argument('--nm',default='/opt/toolchains/dc/sh-elf/bin/sh-elf-nm');ap.add_argument('--objdump',default='/opt/toolchains/dc/sh-elf/bin/sh-elf-objdump');a=ap.parse_args();assert hashlib.sha256(a.elf.read_bytes()).hexdigest()==ELF
 names={'native_ui.cpp':['completed_frame','source_draws_finished','frame','ui_order','frame_ready','stream_aborted','pace_skip_frame','pace_skipped_frames','direct_open'],'debug.cpp':['proc_tick_idx','proc_tick_idx_bak','proc_name','proc_tick','zero_tick'],'pace.cpp':['re4dc_pace_skipping'],'tick_log.cpp':['g_frames','g_first','g_snapSeq','g_snapCount','g_snapName','g_snapAvg','g_snapMax']};units={};block=[]
 def take(lines):
  cu=next((l.split(': ')[-1].strip() for l in lines[:30] if 'DW_AT_name ' in l),'')
  for name in names:
   if cu.endswith('/'+name) or cu==name:
    assert name not in units;assert any(re.search(r'Pointer Size:\s+4$',l) for l in lines[:10]);units[name]={'name':cu,'lines':lines,'dies':dies(lines)}
 proc=subprocess.Popen([a.readelf,'--debug-dump=info',str(a.elf)],stdout=subprocess.PIPE,text=True)
 for l in proc.stdout:
  if 'Compilation Unit @ offset' in l:
   if block:take(block)
   block=[]
  block.append(l)
 take(block);assert proc.wait()==0 and set(units)==set(names)
 nm=subprocess.check_output([a.nm,'-S','-n',str(a.elf)],text=True);symbols=[]
 for line in nm.splitlines():
  p=line.split()
  if len(p)==4:symbols.append({'address':int(p[0],16),'size':int(p[1],16),'kind':p[2],'name':p[3]})
 report={'exact_ELF_sha256':ELF,'status':'OFFLINE_SOURCE_TYPED_BINDING_ONLY_NO_RUNTIME_COVERAGE','target_pointer_bytes':4,'variables':{}}
 for cu,needed in names.items():
  rows=units[cu]['dies'];by={r['offset']:r for r in rows}
  def resolve(d,seen=()):
   if d['offset'] in seen:raise ValueError('cyclic variable specification')
   attrs={}
   for attr in ('specification','abstract_origin'):
    m=re.search(r'<0x([0-9a-f]+)>',d['attrs'].get(attr,''))
    if m:attrs.update(resolve(by[m[1]],seen+(d['offset'],)))
   attrs.update(d['attrs']);return attrs
  def size(ref,seen=()):
   m=re.search(r'<0x([0-9a-f]+)>',ref);d=by[m[1]];assert d['offset'] not in seen
   at=d['attrs']
   if 'byte_size' in at:return int(at['byte_size'],0)
   if d['tag']=='DW_TAG_pointer_type':return 4
   if d['tag']=='DW_TAG_array_type':
    n=1;index=rows.index(d)
    for child in rows[index+1:]:
     if child['depth']<=d['depth']:break
     if child['tag']=='DW_TAG_subrange_type' and child['depth']==d['depth']+1:n*=int(child['attrs'].get('upper_bound','-1'),0)+1
    return n*size(at['type'],seen+(d['offset'],))
   return size(at['type'],seen+(d['offset'],))
  for name in needed:
   hits=[]
   for d in rows:
    if d['tag']!='DW_TAG_variable':continue
    attrs=resolve(d);location=re.search(r'\(DW_OP_addr: ([0-9a-f]+)\)$',attrs.get('location',''))
    if attrs.get('name','').split(': ')[-1]==name and location:hits.append((d,attrs,int(location[1],16)))
   assert len(hits)==1,(cu,name,len(hits));d,attrs,addr=hits[0];width=size(attrs['type']);matches=[s for s in symbols if s['address']==addr and s['size']==width];assert len(matches)==1,(name,matches,width)
   report['variables'][cu+':'+name]={'CU':units[cu]['name'],'DIE':d['offset'],'resolved_attrs':attrs,'symbol':matches[0],'bytes':width,'same_mangled_symbol_elsewhere':[s for s in symbols if s['name']==matches[0]['name'] and s['address']!=addr]}
 report['completed_frame_type']=parse(units['native_ui.cpp']['lines'],['Re4dcNativeFrameStats'])['Re4dcNativeFrameStats'];assert report['completed_frame_type']['size']==192
 report['phase_order']=['ProcessTickInit resets zero_tick and proc_tick_idx BEFORE next UI begin','re4dc_ui_begin resets source_draws_finished=false and advances UI frame (skip path does not advance UI frame)','Render temporarily replaces active camera by itemCamera then restores it; GXSetDrawSync(ADEB) ends source draws BEFORE Frame_cnt increments','main increments GlobalWork.Frame_cnt BEFORE TaskScheduler','gameMainLoop Player moves before CameraMove; CameraMove updates controller, active copy, perspective and view in several stores','Trans later registers current updated source state for subsequent rendering','Main stamps SndWatcher after Trans and workers; PROCESS CPU before Render_done','Render_done executes after_render callbacks and display copy','Render_swap invokes re4dc_ui_end_frame, writes completed_frame with odd/even sequence AFTER render/present','Main finishes vsync/TOTAL/tick_log, then next ProcessTickInit']
 report['marker_contract']={'primary':'Stable nonzero even completed_frame.sequence; completed.frame==nativeUI.frame; source_frame==nativeUI.frame+pace_skipped_frames for verified fresh cold clock origin; pre/post identical sequence/frame/zero_tick/phase cursor and flags','phase':'Rno0==3; last published proc_name[proc_tick_idx+4] is SndWatcher; idx1..27; source_draws_finished1,frame_ready1,ui_order0,pace_skip_frame0,re4dc_pace_skipping0,stream_aborted0,direct_open0; completed.present_requested1,aborted0','reject':'Next-iteration reset, skipped/held/menu/movie/abort/loading, stale completed frame, changed tuples/pointers/phase/frame, unqualified clock origin','read_scope':'Only existing guest RAM through read/query rights; no state/register/recipe writes or thread suspension','limitations':['source_draws_finished becomes true BEFORE the current Player/CameraMove updates; alone it is NOT a completed-state latch','Completed-frame sequence protects its stats, not camera by itself; combine all phase/frame guards','End-frame acceptance interval may be narrow; runtime coverage of every requested tick is unproven','No old B/C row may be reclassified by neighboring pose equality','This establishes post-update observation, not displayed picture or complete PVR raster proof']}
 report['tick_log_cursors']={'g_frames/g_first':'Cumulative current60tick window; resets after log flush and is not a seqlock for live game pose','g_snapSeq':'Changes only every60ticks and is not an odd/even per-frame latch','duplicate':'g_frames has another same-name same-size symbol; bind actual tick_log CU DIE/address, never name-only or size-only map'}
 report['disassembly']={}
 for name in ('_ProcessTickGet','_ProcessTickInit','_re4dc_ui_end_frame','_re4dc_ui_begin','_Render_swap'):
  hits=[s for s in symbols if s['name']==name];assert len(hits)==1;s=hits[0];text=subprocess.check_output([a.objdump,'-d','--start-address='+hex(s['address']),'--stop-address='+hex(s['address']+s['size']),str(a.elf)],text=True);report['disassembly'][name]={'symbol':s,'sha256':hashlib.sha256(text.encode()).hexdigest(),'text':text}
 with a.out.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
 print(json.dumps({'variables':len(report['variables']),'completed_type_bytes':report['completed_frame_type']['size'],'out':str(a.out)}))
if __name__=='__main__':main()
