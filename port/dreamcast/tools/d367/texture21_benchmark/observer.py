#!/usr/bin/env python3
"""Bounded read-only Windows observer for the frozen rectangle C functional guest."""
import argparse,ctypes,hashlib,json,math,os,re,struct,time
from pathlib import Path
RAM0=0x8c000000; RAM_END=0x8d000000
class Invalid(ValueError):pass

def u32(b,o=0):return struct.unpack_from('<I',b,o)[0]
def key(b,o=0):return '%08x-%08x'%struct.unpack_from('<II',b,o)
def ram_range(a,n):
 if not RAM0<=a<=a+n<=RAM_END or n<0 or n>100352:raise Invalid('outside bounded main RAM')
 return a-RAM0

def vram_pointer(a):return (a&0xff000000) in (0xa4000000,0xa5000000) and (a&0xffffff)<8388608

class Typed:
 def __init__(self,read,plan):
  self.read=read;self.plan=plan;self.sy=plan['read_only_observer']['symbols'];self.t=plan['read_only_observer']['typed_layouts'];self.entries=self.sy['native_ui_entries']['address'];self.stride=224;self.selected={}
  required={'scene':{'GlobalWork':['Frame_cnt','room_id','pl_life','Cam'],'Camera':['param','mat','v_mat','ProjMat'],'CameraControl':['camera']},'player':{'cCoord':['pos','ang']},'native_ui':{'Entry':['package','key','frame','valid','model_header','model_header_key'],'Package':['header_','data_','pvr_textures_','owns_texture_','upload_complete_'],'Header':['magic','texture_count','texture_stride','texture_offset','payload_crc32'],'Texture':['material','width','height','format','flags','payload','data_size']}}
  for group,types in required.items():
   for typename,names in types.items():
    if any(n not in self.t[group]['types'][typename]['members'] for n in names):raise Invalid('incomplete typed layout: '+group+'.'+typename)
  entry=self.t['native_ui']['types']['Entry']
  if entry['size']!=224 or entry['members']!={**entry['members'],'package':0,'key':64,'frame':72,'valid':76,'model_header':96,'model_header_key':128} or self.sy['native_ui_entries']['size']!=448*224:raise Invalid('unexpected native Entry layout')
  for i,r in enumerate(plan['selected']):
   self.selected[r['original_key']]=(i,'original');self.selected[r['scoped_key']]=(i,'candidate')
 def sym(self,n):return self.sy[n]['address']
 def scalar(self,n):return u32(self.read(self.sym(n),4))
 def local(self,n):
  name='__ZN12_GLOBAL__N_1L'+str(len(n))+n+'E'
  return self.read(self.sym(name),1)[0] if n=='direct_open' else self.scalar(name)
 def count64(self,n):
  a=self.sym('__ZN12_GLOBAL__N_1L'+str(len(n))+n+'E');h=self.read(a+4,4);lo=self.read(a,4)
  if h!=self.read(a+4,4):raise Invalid('torn 64-bit counter')
  return u32(lo)+(u32(h)<<32)
 def scene(self):
  g=self.scalar('_pG');p=self.scalar('_pPL');G=self.t['scene']['types']['GlobalWork']['members'];C=self.t['scene']['types']['Camera']['members'];cc=self.t['scene']['types']['CameraControl']['members'];co=self.t['player']['types']['cCoord']['members'];controller_cam=self.sym('_CamCtrl')+cc['camera'];cam=g+G['Cam'];tick=u32(self.read(g+G['Frame_cnt'],4))
  room=struct.unpack('<H',self.read(g+G['room_id'],2))[0]
  if not tick or room==0 or room>0x500:raise Invalid('source scene not initialized')
  def fs(a,n):
   v=struct.unpack('<'+'f'*n,self.read(a,n*4))
   if not all(math.isfinite(x) for x in v):raise Invalid('nonfinite pose')
   return list(v)
  pose={'player_position':fs(p+co['pos'],3),'player_angles':fs(p+co['ang'],3),'camera_param':fs(cam+C['param'],8),'camera_mat':fs(cam+C['mat'],12),'camera_view':fs(cam+C['v_mat'],12),'camera_projection':fs(cam+C['ProjMat'],16),'controller_camera_param':fs(controller_cam+C['param'],8),'controller_camera_mat':fs(controller_cam+C['mat'],12),'controller_camera_view':fs(controller_cam+C['v_mat'],12),'controller_camera_projection':fs(controller_cam+C['ProjMat'],16)}
  life=struct.unpack('<4h',self.read(g+G['pl_life'],8));drive={'reads':self.local('m_tot_reads'),'bytes':self.count64('m_tot_bytes'),'block_us':self.count64('m_tot_block')}
  if tick!=u32(self.read(g+G['Frame_cnt'],4)) or g!=self.scalar('_pG') or p!=self.scalar('_pPL'):raise Invalid('torn source frame')
  return {'camera_scope':'active pG->Cam after source CameraMove; controller camera recorded separately','source_tick':tick,'room_id':room,'life_raw':list(life),'pose':pose,'drive_nonmusic':drive,'source_ptr':g}
 def table(self):
  raw=self.read(self.entries,448*self.stride);rows=[];valid=0;alloc=set()
  for i in range(448):
   at=i*self.stride;b=raw[at:at+self.stride]
   if b[76]!=1:continue
   valid+=1;k=key(b,64)
   if k not in self.selected:continue
   row={'slot':i,'address':self.entries+at,'key':k,'cohort':self.selected[k][0],'arm':self.selected[k][1],'entry_frame':u32(b,72),'cached_model_header':b[96:128].hex(),'model_header_key':u32(b,128)}
   P=self.t['native_ui']['types']['Package']['members'];pkg={n:(b[o] if n in ('streamed_','payload_released_','upload_complete_') else u32(b,o)) for n,o in P.items()};row['package']=pkg
   try:
    h=self.read(pkg['header_'],48);H=self.t['native_ui']['types']['Header']['members'];hdr={n:(h[:8].hex() if n=='magic' else u32(h,o)) for n,o in H.items()};row['header']=hdr
    if hdr['texture_count']!=1 or hdr['texture_stride']!=96:raise Invalid('selected package descriptor count/stride')
    t=self.read(pkg['data_']+hdr['texture_offset'],96);row['texture']={n:u32(t,o) for n,o in self.t['native_ui']['types']['Texture']['members'].items() if n!='material'};row['texture']['material']=t[:64].split(b'\0')[0].decode('ascii','replace')
    if row['arm']=='candidate':
     expected=self.plan['selected'][row['cohort']];tex=row['texture'];row['candidate_descriptor_match']=hdr['payload_crc32']==expected['candidate_crc32'] and [tex['width'],tex['height']]==expected['physical'] and tex['format']==0 and tex['flags']==4 and tex['payload']==2 and tex['data_size']==3414
    ptrs=self.read(pkg['pvr_textures_'],8);sampled,base=struct.unpack('<II',ptrs);row.update(pvr_sampled=sampled,pvr_allocation_base=base,owns_texture=self.read(pkg['owns_texture_'],1)[0])
    row['vram_pointers_valid']=vram_pointer(sampled) and vram_pointer(base)
    if row['vram_pointers_valid']:alloc.add(base&0xffffff)
    row['admission']='sampled_valid_uploaded' if pkg['upload_complete_']==1 and row['vram_pointers_valid'] else 'sampled_not_fully_uploaded'
    if b!=self.read(self.entries+at,self.stride) or h!=self.read(pkg['header_'],48):raise Invalid('torn selected entry/package')
   except (Invalid,struct.error) as exc:row['admission']='UNKNOWN';row['reason']=str(exc)
   rows.append(row)
  cohorts={}
  for r in rows:cohorts.setdefault(r['cohort'],set()).add(r['arm'])
  return {'original_only_cohorts':sum(x=={'original'} for x in cohorts.values()),'candidate_only_cohorts':sum(x=={'candidate'} for x in cohorts.values()),'both_cohorts':sum(len(x)==2 for x in cohorts.values()),'valid_slots':valid,'slot_capacity':448,'selected':rows,'unique_selected_vram_allocation_bases':sorted(alloc),'allocation_bytes':'UNAVAILABLE: pointer census is not allocator extent census','draw_proof':False}
 def witness(self):
  def tup():return [self.local(n) for n in ('frame','direct_open','model_handle','model_used','model_pending','model_packets')]
  a=tup();frame,opened,handle,used,pending,packets=a
  if not opened:return None
  if not self.entries<=handle<self.entries+448*self.stride or (handle-self.entries)%self.stride or not 0<=used<=pending<=384:raise Invalid('direct latch outside typed cache/packet bounds')
  e=self.read(handle,self.stride);k=key(e,64)
  if k not in self.selected:return None
  if u32(e,72)!=frame:raise Invalid('direct entry frame mismatch')
  header=self.read(packets+used*32,32)
  if a!=tup() or e!=self.read(handle,self.stride) or header!=self.read(packets+used*32,32):raise Invalid('torn direct header witness')
  tsp=u32(header,8);tcw=u32(header,12)
  return {'key':k,'ui_frame':frame,'header':header.hex(),'tsp':tsp,'tcw':tcw,'physical_64_square':(tsp&63)==27,'vq':bool(tcw&(1<<30)),'mipmap':bool(tcw&(1<<31)),'scope':'sampled minimum SQ header submission only; no total/vertex/raster/nonuse proof'}

class Process:
 def __init__(self,pid,exe):
  self.k=ctypes.WinDLL('kernel32',use_last_error=True);k=self.k
  k.OpenProcess.argtypes=[ctypes.c_ulong,ctypes.c_int,ctypes.c_ulong];k.OpenProcess.restype=ctypes.c_void_p
  k.ReadProcessMemory.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_size_t,ctypes.POINTER(ctypes.c_size_t)];k.ReadProcessMemory.restype=ctypes.c_int
  k.QueryFullProcessImageNameW.argtypes=[ctypes.c_void_p,ctypes.c_ulong,ctypes.c_wchar_p,ctypes.POINTER(ctypes.c_ulong)]
  k.GetProcessTimes.argtypes=[ctypes.c_void_p]+[ctypes.POINTER(ctypes.c_ulonglong)]*4;k.GetExitCodeProcess.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_ulong)];k.CloseHandle.argtypes=[ctypes.c_void_p]
  self.h=k.OpenProcess(0x1010,False,pid)
  if not self.h:raise Invalid('cannot open owned PID read/query only')
  path=ctypes.create_unicode_buffer(32768);n=ctypes.c_ulong(len(path))
  if not k.QueryFullProcessImageNameW(self.h,0,path,ctypes.byref(n)) or os.path.normcase(os.path.abspath(path.value))!=os.path.normcase(str(exe.resolve())):raise Invalid('PID executable mismatch')
  self.start=self.times()[0];self.path=path.value;self.ram=None;self.read_deadline=float('inf')
 def times(self):
  ts=[ctypes.c_ulonglong() for _ in range(4)]
  if not self.k.GetProcessTimes(self.h,*[ctypes.byref(x) for x in ts]):raise Invalid('process times unavailable')
  return [x.value for x in ts]
 def live(self):
  c=ctypes.c_ulong()
  return bool(self.k.GetExitCodeProcess(self.h,ctypes.byref(c))) and c.value==259 and self.times()[0]==self.start
 def read(self,a,n):

  if time.monotonic()>self.read_deadline:raise Invalid('bounded read window exceeded')
  off=ram_range(a,n)
  if self.ram is None:raise Invalid('RAM base unavailable')
  b=ctypes.create_string_buffer(n);got=ctypes.c_size_t()
  if not self.k.ReadProcessMemory(self.h,self.ram+off,b,n,ctypes.byref(got)) or got.value!=n:raise Invalid('read unavailable')
  return b.raw
 def close(self):self.k.CloseHandle(self.h)

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--cap',type=Path,required=True);ap.add_argument('--plan',type=Path,required=True);ap.add_argument('--seconds',type=float,default=41);ap.add_argument('--runtime-binding',default='observer-runtime-03');a=ap.parse_args()
 if not 0<a.seconds<=41:raise SystemExit('budget must be in (0,41] seconds')
 start=time.monotonic();end=start+a.seconds;plan=json.loads((a.plan/'observation-cold-window.json').read_text());binding=json.loads((a.plan/a.runtime_binding/'binding.json').read_text());inputs=json.loads((a.plan/'inputs-final/plan-inputs.json').read_text());plan['selected']=inputs['selected']
 if 'scene_layout' in binding:
  layoutpath=a.plan/a.runtime_binding/binding['scene_layout']
  if hashlib.sha256(layoutpath.read_bytes()).hexdigest()!=binding['scene_layout_sha256']:raise SystemExit('scene layout changed')
  plan['read_only_observer']['typed_layouts']['scene']=json.loads(layoutpath.read_text())
 out=a.cap/'typed-observer.jsonl';summary=a.cap/'typed-observer-summary.json'
 if out.exists() or summary.exists():raise SystemExit('preserve existing observer output')
 if hashlib.sha256((a.plan/'observation-cold-window.json').read_bytes()).hexdigest()!=binding['plan_sha256']:raise SystemExit('plan changed')
 pid=int((a.cap/'flycast.pid').read_text());exe=a.cap/'flycast.exe';exe_sha=hashlib.sha256(exe.read_bytes()).hexdigest()
 if exe_sha!=binding['emulator_sha256']:raise SystemExit('emulator changed')
 typed=Typed(None,plan)
 proc=Process(pid,exe)
 if proc.start/1e7-11644473600<(a.cap/'flycast.pid').stat().st_mtime-10:raise Invalid('owned process predates fresh PID receipt')
 typed.read=proc.read;ready=False;rows=0;bytesout=0;waits={};table_due=0;lasttick=None;witnesses=set();max_sample=0.;initial_head=None
 def emit(row):
  nonlocal rows,bytesout
  b=(json.dumps(row,separators=(',',':'),allow_nan=False)+'\n').encode()
  if bytesout+len(b)>3900000:raise Invalid('observer output budget reached')
  stream.write(b);stream.flush();bytesout+=len(b);rows+=1
 try:
  with out.open('xb') as stream:
   emit({'event':'identity','pid':pid,'start_filetime':proc.start,'exe':proc.path,'exe_sha256':exe_sha,'binding':binding,'scope':'READ_ONLY_FUNCTIONAL; no timing comparison or death inference'})
   while time.monotonic()<end and proc.live():
    begun=time.monotonic();proc.read_deadline=begun+.08
    try:
     if proc.ram is None:
      log=(a.cap/'flycast.log').read_text(errors='replace');matches=re.findall(r'RAM\(16 MB\) ([0-9A-Fa-f]+)',log)
      if not matches:raise Invalid('waiting RAM log')
      proc.ram=int(matches[-1],16)
     if not ready:
      for anchor in binding['anchors']:
       if proc.read(anchor['address'],256).hex()!=anchor['hex']:raise Invalid('waiting exact program anchors')
      ready=True;initial_head=typed.scalar('_re4dc_log_head');emit({'event':'program_anchors_verified','ram_host_base':proc.ram,'initial_log_head':initial_head})
     scene=typed.scene()
     if time.monotonic()>=table_due:
      scene['table']=typed.table();scene['vram_counters']={n:typed.local(n) for n in ('vram_budget','vram_rejects','vram_retries')};scene['pvr_state_sha256']=hashlib.sha256(proc.read(typed.sym('_pvr_state'),520)).hexdigest();scene['table_end_source_tick']=u32(proc.read(scene['source_ptr']+typed.t['scene']['types']['GlobalWork']['members']['Frame_cnt'],4));table_due=time.monotonic()+.2
     witness=typed.witness()
     if witness:
      signature=(witness['key'],witness['ui_frame'],witness['header'])
      if signature not in witnesses:scene['minimum_header_witness']=witness;witnesses.add(signature)
     if scene['source_tick']!=lasttick or 'table' in scene or 'minimum_header_witness' in scene:
      scene.update(event='sample',host_elapsed=time.monotonic()-start,log_head=typed.scalar('_re4dc_log_head'));emit(scene);lasttick=scene['source_tick']
    except (Invalid,OSError,struct.error) as exc:
     reason=str(exc);waits[reason]=waits.get(reason,0)+1
     if reason=='observer output budget reached':break
    elapsed=time.monotonic()-begun;max_sample=max(max_sample,elapsed)
    time.sleep(max(.001,.01-elapsed))
 finally:
  result={'pid':pid,'start_filetime':proc.start,'seconds':time.monotonic()-start,'rows':rows,'jsonl_bytes':bytesout,'anchors_verified':ready,'last_source_tick':lasttick,'wait_or_reject_counts':waits,'minimum_witnesses':len(witnesses),'max_sample_seconds':max_sample,'memory_accounting':'Partial typed fields only; full RAM/VRAM extent census, runtime high water and PVR vertex/raster totals unavailable','scope':'No gameplay writes, death classification, state writes, timing gain, release or console acceptance'}
  proc.close()
  with summary.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
 print(json.dumps(result))
if __name__=='__main__':main()
