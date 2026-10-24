"""Bounded source/layout and pure read-only observer controls; no guest or SDK."""
import copy,ctypes,hashlib,importlib.util,json,pathlib,struct,tempfile
here=pathlib.Path(__file__).parent;sp=importlib.util.spec_from_file_location('observer',here/'freeze330-observer.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
layout=json.loads((here/'observer-layout-R-g.json').read_text());tree=pathlib.Path('/root/work/lanes/world-emit23-current-R')
for path,sha in layout['source_pins'].items():assert hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()==sha
main=(tree/'src/game/main.cpp').read_text();main=main[main.index('TaskExec(0, Title_task, 0);'):]
order=['Render_before();','Render();','pG->Frame_cnt++;','TaskScheduler();','Render_done();','Render_swap();'];positions=[main.index(x) for x in order];assert positions==sorted(positions)
game=(tree/'src/game/game.cpp').read_text();game=game[game.index('void gameMainLoop()'):];assert game.index('re4dc_room_cycle_poll()')<game.index('EmMgr.move')
warp=(tree/'port/dreamcast/game/dbgwarp_bridge.cpp').read_text();assert 'if (wp.has_freeze && pG && (u32) pG->Frame_cnt >= wp.freeze_tick)' in warp and 'for (;;) thd_sleep(1000);' in warp
fast=(tree/'port/dreamcast/game/platform/native_actor_fast.cpp').read_text();assert '#if RE4DC_ACTOR_STATS_LEAN && !RE4DC_ACTOR_LOG' in fast and 'NopStat parts, handled, declined' in fast and '#define RE4DC_STATS_OBJECT stats_live' in fast
knobs=dict(x.split('=',1) for x in pathlib.Path('/root/probe/lanes/route/out-fpwe23R49adgW/resolved-knobs.txt').read_text().splitlines() if '=' in x)
assert knobs['NATIVE_ACTOR_FAST']=='1' and knobs['ACTOR_STATS_LEAN']=='1' and knobs['NATIVE_ACTOR_LOG']=='0'
assert not any('actor' in k.lower() or 'viewport' in k.lower() for k in layout['types']['Re4dcNativeFrameStats']['members'])
assert layout['types']['cUnit']['members']['pNext']==8 and layout['types']['cManager<cEm>']['members']['pAlive']==20
print('PASS actual source call order, lean actor-counter refusal, nm/DWARF field layouts/source hashes')
def put(b,o,*values):struct.pack_into('<'+'I'*len(values),b,o,*values)
src=bytearray(112);put(src,0,328);put(src,12,0x101)
profile=bytearray(428);put(profile,0,20,300);profile[316:]=src
frame=bytearray(192);put(frame,0,22,300);put(frame,184,1)
pvr=bytearray(520);put(pvr,0,1);put(pvr,44,0);put(pvr,312,0,614400,614400,614400);put(pvr,332,640,480)
p=m.profile_decode(profile);f=m.frame_decode(frame);v=m.pvr_decode(pvr)
begin=bytearray(src);put(begin,0,329)
a={'profile':p,'completed':f,'source_begin':m.source_decode(begin),'global_tick':330,'live_camera':[0.0]*8,'global_state_sha256':'stable','pvr':v,'viewport':[0,0,640,480,0,1],'projection':[0.0]*7,'pipeline':{'pending':-1,'flip':0,'manual':1,'steady_q':0,'steady_watch':0,'submitted':10,'resolved':9,'failures':0,'ui_frame':301,'frame_ready':1,'stream_scene':0,'loads':50},'EmMgr':{'actors':[{'id':0}],'scope':'LIVE'},'ObjMgr':{'actors':[],'scope':'LIVE'},'packages':{'entries':[{'upload_complete':1}],'sha256':'stable'}}
b=copy.deepcopy(a);b['pvr']['vblank_count_observation_only']+=3;b['pvr']['sha256']='vblank-changed'
r=m.assess(a,b,layout,0x101,330);assert r['readonly_snapshot_consistent'] and not r['strict_pixel_qualified'] and len(r['strict_pixel_refusals'])==3
print('PASS coherent diagnostic positive; benign vblank advance ignored; strict pixels remain refused')
mutations={
'pending-flip':lambda x:x['pipeline'].__setitem__('flip',1),
'queued-presentation':lambda x:x['pipeline'].__setitem__('steady_q',1),
'pending-watch':lambda x:x['pipeline'].__setitem__('steady_watch',1),
'pending-KOS':lambda x:x['pipeline'].__setitem__('pending',1),
'render-busy':lambda x:x['pvr'].__setitem__('render_busy',1),
'wrong-completed-room':lambda x:x['profile']['source'].__setitem__('room',0x100),
'wrong-completed-tick':lambda x:x['profile']['source'].__setitem__('tick',329),
'wrong-source-begin':lambda x:x['source_begin'].__setitem__('tick',330),
'wrong-global-tick':lambda x:x.__setitem__('global_tick',331),
'frame-mismatch':lambda x:x['completed'].__setitem__('frame',299),
'queue-drop':lambda x:x['completed'].__setitem__('queue_drops',1),
'aborted':lambda x:x['completed'].__setitem__('aborted',1),
'not-requested':lambda x:x['completed'].__setitem__('present_requested',0),
'upload-incomplete':lambda x:x['packages']['entries'][0].__setitem__('upload_complete',0),
'wrong-fb-extent':lambda x:x['pvr'].__setitem__('width',1280),
'changed-viewport':lambda x:x['viewport'].__setitem__(1,0.5),
'changed-live-actor':lambda x:x['EmMgr']['actors'][0].__setitem__('id',1),
}
for name,change in mutations.items():
 bad=copy.deepcopy(b);change(bad);r=m.assess(a,bad,layout,0x101,330);assert not r['readonly_snapshot_consistent'] and not r['strict_pixel_qualified'],name
print('PASS',len(mutations),'state/phase/upload/presentation refusal controls')
# Meaningful old freeze-only admission mutant: would falsely accept the incomplete completed binding.
def old_freeze_only():return a['global_tick']==330
assert old_freeze_only() and not m.assess(a,b,layout,0x101,330)['strict_pixel_qualified']
print('PASS freeze-only admission mutant detected')
reads=[]
def good_read(addr,count):reads.append((addr,count));return (profile if count==428 else profile[:4])
assert m.coherent_read(good_read,1,428)==profile and len(reads)==3
odd=bytes([1,0,0,0]);calls=[]
def odd_read(addr,count):calls.append((addr,count));return odd+bytes(count-4)
try:m.coherent_read(odd_read,1,428)
except m.Refused:assert len(calls)==9
else:raise AssertionError('odd read accepted')
print('PASS sequence read consistency and bounded nine-read odd rejection')
class Kernel:
 def __init__(self,partial=False):self.calls=[];self.partial=partial
 def ReadProcessMemory(self,handle,address,buffer,count,out):
  self.calls.append((handle,address,count));ctypes.cast(out,ctypes.POINTER(ctypes.c_size_t))[0]=count-1 if self.partial else count;return 1
class Owned:
 handle=1234
 def __init__(self,partial=False):self.kernel=Kernel(partial)
o=Owned();v=m.read_vram_same_handle(o,0x123000000);assert len(v)==8388608 and o.kernel.calls==[(1234,0x123000000,8388608)]
try:m.read_vram_same_handle(Owned(True),0x123000000)
except m.Refused:pass
else:raise AssertionError('short VRAM read accepted')
print('PASS exact existing handle8MiB read, no reopen, short-read rejection')
manager=bytearray(56);base=0x8c800000;put(manager,4,base,1,800);put(manager,20,base)
model=bytearray(800);put(model,4,1);put(model,248,7);model[256]=0
r=m.actor_roster(lambda p,n:bytes(model),manager);assert len(r['actors'])==1
put(model,8,base)
try:m.actor_roster(lambda p,n:bytes(model),manager)
except m.Refused:pass
else:raise AssertionError('cycle accepted')
print('PASS actual cUnit/manager offsets, bounded roster/cycle rejection')
print('ALL SOURCE/HOST CONTROLS PASS; no guest, SDK, pixel qualification or runtime edits')