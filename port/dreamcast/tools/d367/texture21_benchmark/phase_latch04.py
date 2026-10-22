#!/usr/bin/env python3
"""Completed-state runtime04 collections with stable rereads of every body dependency."""
import hashlib,json
from observer import Invalid,ram_range
from phase_latch import PhaseLatch

class StableReads:
 def __init__(self,read):self.read=read;self.ranges={};self.first_bytes=0;self.verify_bytes=0
 def __call__(self,address,size):
  ram_range(address,size);value=self.read(address,size);key=(address,size)
  if key in self.ranges and self.ranges[key]!=value:raise Invalid('body dependency changed during first pass')
  if key not in self.ranges:self.first_bytes+=size;self.ranges[key]=value
  return value
 def verify(self):
  for (address,size),expected in self.ranges.items():
   actual=self.read(address,size);self.verify_bytes+=size
   if actual!=expected:raise Invalid('body dependency changed during verification')
 def receipt(self):
  rows=[{'address':a,'bytes':n,'sha256':hashlib.sha256(v).hexdigest()} for (a,n),v in sorted(self.ranges.items())]
  return {'unique_ranges':len(rows),'first_pass_bytes':self.first_bytes,'verification_bytes':self.verify_bytes,'manifest_sha256':hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest()}

class PhaseLatch04(PhaseLatch):
 def diagnostic(self):
  """Unlatched startup/coverage context only; never an accepted scene."""
  pg=self.t.scalar('_pG');pl=self.t.scalar('_pPL');frame=int.from_bytes(self.read(pg+self.G['Frame_cnt'],4),'little')
  return {'source_frame_unlatched':frame,'pg_unlatched':pg,'pl_unlatched':pl}
 def state(self):
  s=super().state();C=self.t.t['scene']['types']['Camera'];CC=self.t.t['scene']['types']['CameraControl'];P=self.t.t['player']['types']['cCoord']
  pointers={'active_camera':s['pg']+self.G['Cam'],'controller_camera':self.t.sym('_CamCtrl')+CC['members']['camera'],'player_position':s['pl']+P['members']['pos'],'player_angles':s['pl']+P['members']['ang'],'source_frame_address':s['pg']+self.G['Frame_cnt'],'entries_address':self.t.entries}
  for name,address in pointers.items():ram_range(address,C['size'] if name in ('active_camera','controller_camera') else (100352 if name=='entries_address' else 12 if name.startswith('player_') else 4))
  s['source_pointers']=pointers;return s
 def capture(self,collect=None):
  before=self.state();original=self.t.read;rec=StableReads(original)
  try:
   self.t.read=rec;body=collect() if collect is not None else {'scene':self.t.scene()};rec.verify()
  finally:self.t.read=original
  after=self.state();scene=body['scene']
  if before!=after or scene['source_tick']!=before['source_frame'] or scene['source_ptr']!=before['pg']:raise Invalid('phase/epoch/frame/pointer changed during collection')
  return {'phase':before,'scene':scene,'body':{k:v for k,v in body.items() if k!='scene'},'dependencies':rec.receipt(),'cpu_us':before['cpu_ticks']*10//405,'scope':'Qualified completed-state observation only; no presentation/all-key raster/full allocator peak proof'}
