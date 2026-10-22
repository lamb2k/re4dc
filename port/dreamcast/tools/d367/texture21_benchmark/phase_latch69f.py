#!/usr/bin/env python3
"""Source-qualified completed-state reader contract. No process attach or guest launcher."""
import hashlib,struct
from observer import Invalid,u32

class PhaseLatch:
 def __init__(self,typed,audit):
  if audit['exact_ELF_sha256']!='69f2e7db588f515f4e6a67455d627a74fc17132d5ca20a591db4e0f15deedcae':raise Invalid('phase binding is for another ELF')
  self.t=typed;self.read=typed.read;self.vars=audit['variables'];self.members=audit['completed_frame_type']['members'];self.G=typed.t['scene']['types']['GlobalWork']['members']
  for name in ('Rno0','Frame_cnt','System_flg','Stop_flg'):
   if name not in self.G:raise Invalid('phase GlobalWork member missing '+name)
 def address(self,cu,name):return self.vars[cu+':'+name]['symbol']['address']
 def value(self,cu,name):
  r=self.vars[cu+':'+name];n=r['bytes'];b=self.read(r['symbol']['address'],n)
  if n not in (1,4):raise Invalid('phase scalar width differs')
  return b[0] if n==1 else u32(b)
 def text(self,a):return self.read(a,64).split(b'\0')[0].decode('ascii','strict')
 def state(self):
  pg=self.t.scalar('_pG');pl=self.t.scalar('_pPL');frame=u32(self.read(pg+self.G['Frame_cnt'],4));idx=self.value('debug.cpp','proc_tick_idx')
  if not 1<=idx<=27:raise Invalid('phase cursor not at published post-trans marker')
  names=self.address('debug.cpp','proc_name');last=self.text(u32(self.read(names+4*(idx+4),4)));cpu_name=self.text(u32(self.read(names+8,4)))
  base=self.address('native_ui.cpp','completed_frame');raw=self.read(base,192);seq=u32(raw,self.members['sequence'])
  if not seq or seq&1 or seq!=u32(self.read(base,4)):raise Invalid('incomplete completed-frame snapshot')
  state={'pg':pg,'pl':pl,'source_frame':frame,'Rno0':self.read(pg+self.G['Rno0'],1)[0],'system_flags':u32(self.read(pg+self.G['System_flg'],4)),'stop_flags':u32(self.read(pg+self.G['Stop_flg'],4)),'zero_tick':self.value('debug.cpp','zero_tick'),'proc_idx':idx,'last_proc':last,'cpu_proc':cpu_name,'cpu_ticks':u32(self.read(self.address('debug.cpp','proc_tick')+8,4)),'completed_sequence':seq,'completed_frame':u32(raw,self.members['frame']),'completed_present':u32(raw,self.members['present_requested']),'completed_aborted':u32(raw,self.members['aborted']),'completed_sha256':hashlib.sha256(raw).hexdigest()}
  for name in ('frame','source_draws_finished','frame_ready','ui_order','stream_aborted','pace_skip_frame','pace_skipped_frames','direct_open'):state[name]=self.value('native_ui.cpp',name)
  state['re4dc_pace_skipping']=self.value('pace.cpp','re4dc_pace_skipping')
  self.require(state);return state
 @staticmethod
 def require(s):
  if not s['completed_sequence'] or s['completed_sequence']&1:raise Invalid('completed sequence not stable even')
  if s['Rno0']!=3 or s['system_flags']&(0x100000|0x400) or s['stop_flags']&0x40000000:raise Invalid('not ordinary active freeplay')
  if s['last_proc']!='SndWatcher' or s['cpu_proc']!='PROCESS CPU' or not s['cpu_ticks']:raise Invalid('current CPU/post-trans marker absent')
  if s['source_draws_finished']!=1 or s['frame_ready']!=1 or any(s[n] for n in ('ui_order','stream_aborted','pace_skip_frame','re4dc_pace_skipping','direct_open')):raise Invalid('draw/skip/UI phase unsuitable')
  if s['completed_present']!=1 or s['completed_aborted'] or s['completed_frame']!=s['frame']:raise Invalid('completed native frame stale/held/aborted')
  if s['source_frame']!=((s['frame']+s['pace_skipped_frames'])&0xffffffff):raise Invalid('cold source/UI/skip clock relation failed')
 def capture(self):
  before=self.state();scene=self.t.scene();after=self.state()
  if before!=after or scene['source_tick']!=before['source_frame']:raise Invalid('phase/epoch/frame changed during scene read')
  return {'phase':before,'scene':scene,'cpu_us':before['cpu_ticks']*10//405,'scope':'Completed current source state in observed post-update interval. No presentation, all-key raster or high-water proof; runtime coverage unqualified.'}
