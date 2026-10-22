"""Synthetic RAM with actual frozen linked-ELF bindings; never a game process."""
import json,struct
from pathlib import Path
from observer import ram_range
from typed_canonical1004 import TypedCanonical as Typed
from phase_latch69f05 import PhaseLatch05

class Fixture:
 def __init__(self,plan_dir):
  p=Path(plan_dir);self.plan=json.loads((p/'observation-cold-window.json').read_text());inputs=json.loads((p/'inputs-final/plan-inputs.json').read_text());self.plan.update({k:inputs[k]for k in ('selected','supplemental_originals','world_original_map')});self.plan['read_only_observer']['typed_layouts']['scene']=json.loads((p/'observer-runtime-69f/scene-existing-dwarf69f.json').read_text());self.audit=json.loads((p/'observer-runtime-69f/phase-contract.json').read_text());self.raw=bytearray(16777216);self.read_hook=None
  self.t=Typed(self.read,self.plan);self.l=PhaseLatch05(self.t,self.audit);self.pg=0x8c700000;self.pl=0x8c710000;G=self.t.t['scene']['types']['GlobalWork']['members'];self.G=G
  self.w(self.t.sym('_pG'),self.pg);self.w(self.t.sym('_pPL'),self.pl);self.w(self.pg+G['Frame_cnt'],10);self.put(self.pg+G['Rno0'],b'\3');self.put(self.pg+G['room_id'],struct.pack('<H',0x103));self.put(self.pg+G['pl_life'],struct.pack('<4h',1000,1000,600,600))
  for name,n in [('frame',10),('source_draws_finished',1),('frame_ready',1),('ui_order',0),('stream_aborted',0),('pace_skip_frame',0),('pace_skipped_frames',0),('direct_open',0)]:self.var('native_ui.cpp',name,n)
  self.var('pace.cpp','re4dc_pace_skipping',0);self.var('debug.cpp','proc_tick_idx',20);self.var('debug.cpp','zero_tick',123)
  self.put(0x8c720000,b'SndWatcher\0');self.put(0x8c720080,b'PROCESS CPU\0');self.w(self.l.address('debug.cpp','proc_name')+24*4,0x8c720000);self.w(self.l.address('debug.cpp','proc_name')+8,0x8c720080);self.w(self.l.address('debug.cpp','proc_tick')+8,40500)
  self.stats=self.l.address('native_ui.cpp','completed_frame');self.w(self.stats,2);self.w(self.stats+4,10);self.w(self.stats+184,1);self.w(self.stats+188,0)
  self.install_selected()
 def read(self,a,n):
  o=ram_range(a,n)
  if self.read_hook:self.read_hook(a,n)
  return bytes(self.raw[o:o+n])
 def put(self,a,b):o=ram_range(a,len(b));self.raw[o:o+len(b)]=b
 def w(self,a,n):self.put(a,struct.pack('<I',n))
 def var(self,cu,name,n):
  r=self.audit['variables'][cu+':'+name];self.put(r['symbol']['address'],bytes([n]) if r['bytes']==1 else struct.pack('<I',n))
 def install_selected(self):
  t=self.t;e=t.entries;s=self.plan['selected'][0];self.put(e+64,struct.pack('<II',*[int(x,16) for x in s['key'].split('-')]));self.put(e+76,b'\1');self.w(e+72,10)
  P=t.t['native_ui']['types']['Package']['members'];data=0x8c740000;ptrs=0x8c750000;owns=0x8c750020
  for name,v in [('header_',data),('data_',data),('pvr_textures_',ptrs),('owns_texture_',owns)]:self.w(e+P[name],v)
  self.put(e+P['upload_complete_'],b'\1');self.put(ptrs,struct.pack('<II',0xa4001000,0xa4001000));self.put(owns,b'\1');H=t.t['native_ui']['types']['Header']['members']
  self.put(data,b'RE4DCTX\0')
  for name,v in [('texture_count',1),('texture_stride',96),('texture_offset',48),('payload_crc32',s['canonical_body_crc32'])]:self.w(data+H[name],v)
  T=t.t['native_ui']['types']['Texture']['members']
  self.put(data+48,bytes.fromhex(s['native_descriptor_hex']))
