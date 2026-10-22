"""CONTROLLED exact019state alreadyatnative204Door4: acknowledgedowned-windowA to209, remainingcurrententryGoto thenphysicalDoor1/originalleadercut. No actor/room/outcome writes."""
from pathlib import Path
import math
import ctypes as C,ctypes.wintypes as W,json,time,re,struct,sys,hashlib,importlib.util,shutil,traceback
L=Path(__file__).parent;D=Path(r'C:\Flycast-Evidence\re4-dreamcast\castle18-20261018\Test21\recovered-j-content-20261021');cap=Path(sys.argv[1]).resolve();assert cap==D/'route-walk-controlled-ch32-door020'
k=C.WinDLL('kernel32',use_last_error=True);u=C.WinDLL('user32',use_last_error=True)
k.OpenProcess.argtypes=[W.DWORD,W.BOOL,W.DWORD];k.OpenProcess.restype=W.HANDLE;k.GetProcessTimes.argtypes=[W.HANDLE]+[C.POINTER(W.FILETIME)]*4;k.QueryFullProcessImageNameW.argtypes=[W.HANDLE,W.DWORD,W.LPWSTR,C.POINTER(W.DWORD)];k.ReadProcessMemory.argtypes=[W.HANDLE,C.c_void_p,C.c_void_p,C.c_size_t,C.POINTER(C.c_size_t)];k.WaitForSingleObject.argtypes=[W.HANDLE,W.DWORD];k.CloseHandle.argtypes=[W.HANDLE]
u.GetWindowThreadProcessId.argtypes=[W.HWND,C.POINTER(W.DWORD)];u.GetClassNameW.argtypes=[W.HWND,W.LPWSTR,C.c_int];u.PostMessageW.argtypes=[W.HWND,W.UINT,W.WPARAM,W.LPARAM];CALL=C.WINFUNCTYPE(W.BOOL,W.HWND,W.LPARAM);u.EnumWindows.argtypes=[CALL,W.LPARAM]
k.WriteProcessMemory.argtypes=[W.HANDLE,C.c_void_p,C.c_void_p,C.c_size_t,C.POINTER(C.c_size_t)];k.WriteProcessMemory.restype=W.BOOL
class GuiThreadInfo(C.Structure):
 _fields_=[('cbSize',W.DWORD),('flags',W.DWORD),('hwndActive',W.HWND),('hwndFocus',W.HWND),('hwndCapture',W.HWND),('hwndMenuOwner',W.HWND),('hwndMoveSize',W.HWND),('hwndCaret',W.HWND),('rcCaret',W.RECT)]
assert C.sizeof(GuiThreadInfo)==72
u.GetForegroundWindow.argtypes=[];u.GetForegroundWindow.restype=W.HWND
u.GetGUIThreadInfo.argtypes=[W.DWORD,C.POINTER(GuiThreadInfo)];u.GetGUIThreadInfo.restype=W.BOOL
u.SetForegroundWindow.argtypes=[W.HWND];u.SetForegroundWindow.restype=W.BOOL
u.IsWindowVisible.argtypes=[W.HWND];u.IsWindowVisible.restype=W.BOOL
u.IsIconic.argtypes=[W.HWND];u.IsIconic.restype=W.BOOL
u.IsChild.argtypes=[W.HWND,W.HWND];u.IsChild.restype=W.BOOL
u.GetWindowThreadProcessId.restype=W.DWORD
h=None;events=[];last=None;closed_sent=False
read_diagnostics=[];read_failure_count=0;region_failure_count=0;memory_ready=False
(D/(cap.name+'-observer-ready.json')).write_text(json.dumps(dict(scope=__doc__,sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))+'\n')
def check():
 assert k.WaitForSingleObject(h,0)==258,'Owned process exited'
 p=C.create_unicode_buffer(32768);n=W.DWORD(32768);assert k.QueryFullProcessImageNameW(h,0,p,C.byref(n));assert Path(p.value).resolve()==cap/'flycast.exe'
 a,b,c,d=(W.FILETIME()for _ in range(4));assert k.GetProcessTimes(h,C.byref(a),C.byref(b),C.byref(c),C.byref(d));assert a.dwLowDateTime+(a.dwHighDateTime<<32)==owner['start_filetime']
class MemoryUnavailable(Exception):
 def __init__(self,detail):self.detail=detail;super().__init__(json.dumps(detail,sort_keys=True))
class MemoryBasicInformation(C.Structure):
 _fields_=[('BaseAddress',C.c_void_p),('AllocationBase',C.c_void_p),('AllocationProtect',W.DWORD),('PartitionId',W.WORD),('RegionSize',C.c_size_t),('State',W.DWORD),('Protect',W.DWORD),('Type',W.DWORD)]
assert C.sizeof(C.c_void_p)==8 and C.sizeof(MemoryBasicInformation)==48
k.VirtualQueryEx.argtypes=[W.HANDLE,C.c_void_p,C.POINTER(MemoryBasicInformation),C.c_size_t];k.VirtualQueryEx.restype=C.c_size_t

def region_query(host,n):
 q=MemoryBasicInformation();C.set_last_error(0);ret=int(k.VirtualQueryEx(h,host,C.byref(q),C.sizeof(q)));error=C.get_last_error()
 return dict(returned_bytes=ret,error=error,requested_host=hex(host),requested_bytes=n,base=hex(q.BaseAddress or 0),allocation_base=hex(q.AllocationBase or 0),region_bytes=q.RegionSize,state=hex(q.State),protect=hex(q.Protect),type=hex(q.Type),covers=ret==C.sizeof(q)and(q.BaseAddress or 0)<=host and host+n<=(q.BaseAddress or 0)+q.RegionSize,committed=ret==C.sizeof(q)and q.State==0x1000,accessible=ret==C.sizeof(q)and not(q.Protect&0x101))

def read(a,n):
 global memory_ready,read_failure_count
 assert 0x8c000000<=a and a+n<=0x8d000000
 host=ram+a-0x8c000000;buf=C.create_string_buffer(n);got=C.c_size_t();C.set_last_error(0);ok=bool(k.ReadProcessMemory(h,host,buf,n,C.byref(got)));error=C.get_last_error()
 if not ok or got.value!=n:
  memory_ready=False;read_failure_count+=1
  detail=dict(operation='ReadProcessMemory',guest_address=hex(a),host_address=hex(host),RAM_base=hex(ram),requested_bytes=n,api_ok=ok,bytes_read=got.value,win32_error=error,partial_data_hex=buf.raw[:min(got.value,n,32)].hex(),process_age=age(),pid=owner['pid'],process_start_filetime=owner['start_filetime'],region=region_query(host,n))
  if len(read_diagnostics)<100:read_diagnostics.append(detail)
  raise MemoryUnavailable(detail)
 return buf.raw

def startup_log_mapping(log,expected_state):
 maps=list(re.finditer(r'(?m)^.*RAM\(16 MB\)\s+([0-9a-fA-F]+).*$',log));loaded=re.search(r'(?m)^.*Loaded state ver [0-9]+ from '+re.escape(str(expected_state))+r' size [0-9]+.*$',log)
 if not maps or not loaded:return None
 return dict(RAM=int(maps[-1].group(1),16),mapping_line=maps[-1].group(0),state_load_line=loaded.group(0),mapping_precedes_load=maps[-1].end()<=loaded.start())

def wait_startup_mapping():
 global ram,region_failure_count
 missing_recorded=False
 while age()<38:
  check()
  try:log=(cap/'flycast.log').read_text(errors='replace')
  except FileNotFoundError:
   if not missing_recorded:events.append(dict(startup_log_not_created_pending=True,process_age=age(),no_inputs=True));missing_recorded=True
   time.sleep(.03);continue
  mapping=startup_log_mapping(log,cap/'data/disc.state')
  if mapping and mapping['mapping_precedes_load']:
   ram=mapping['RAM'];q=region_query(ram+0x2e91dc,4)
   if q['committed']and q['accessible']and q['covers']:
    events.append(dict(startup_exact_state_load_and_mapping=mapping,process_age=age(),process_identity=owner,initial_pG_region=q));return mapping
   region_failure_count+=1
   if len(read_diagnostics)<100:read_diagnostics.append(dict(operation='startupVirtualQueryEx',RAM_base=hex(ram),process_age=age(),pid=owner['pid'],process_start_filetime=owner['start_filetime'],region=q))
  time.sleep(.03)
 return None

def readable_sequence(row,previous,current_ram):
 return bool(row and previous and row.get('live_native_code_anchors_verified')is True and row.get('phase')==[3,0]and row.get('room')in['0x204','0x209']and row.get('pg')==previous.get('pg')and current_ram==previous.get('RAM_base')and row.get('frame',0)>previous.get('frame',0)and row.get('frame',0)>=3684)

u32=lambda a:struct.unpack('<I',read(a,4))[0]
def close():
 global closed_sent
 if closed_sent:return
 check();wins=[]
 @CALL
 def cb(w,_):
  p=W.DWORD();u.GetWindowThreadProcessId(w,C.byref(p));c=C.create_unicode_buffer(256);u.GetClassNameW(w,c,256)
  if p.value==owner['pid']and c.value=='SDL_app':wins.append(int(w))
  return True
 assert u.EnumWindows(cb,0)and len(wins)==1;assert u.PostMessageW(wins[0],0x10,0,0);closed_sent=True;events.append(dict(exact_owned_WM_CLOSE=True,process_age=age()))
def inram(a,n=1):return 0x8c000000<=a and a+n<=0x8d000000
native_anchors_verified=False
native_anchors=[]
def live_native_anchors():
 global native_anchors_verified,native_anchors
 if native_anchors_verified:return True
 e=(D.parent/'builds/c21jmW/re4dc-game.elf').read_bytes();phoff=struct.unpack_from('<I',e,28)[0];phsize,phnum=struct.unpack_from('<HH',e,42)
 assert e[:6]==b'\x7fELF\x01\x01'and phsize==32
 sites=[0x8c04bd30,0x8c087974,0x8c110f0c,0x8c14f0fc,0x8c2ce564,0x8c26cf88,0x8c14a95c,0x8c0bc300,0x8c0bc384]
 evidence=[]
 for addr in sites:
  expected=None
  for i in range(phnum):
   typ,off,va,pa,sz,mem,flags,align=struct.unpack_from('<8I',e,phoff+i*phsize)
   if typ==1 and va<=addr and addr+32<=va+sz:expected=e[off+addr-va:off+addr-va+32];break
  assert expected is not None
  actual=read(addr,32)
  if actual!=expected:return False
  evidence.append(dict(address=hex(addr),bytes=32,sha256=hashlib.sha256(actual).hexdigest()))
 native_anchors=evidence;native_anchors_verified=True;events.append(dict(live_frozen_maincode_anchors=evidence,process_age=age()));return True
def sample():
 pg=u32(0x8c2e91dc)
 if not inram(pg,0x8600):return None
 stamp=(u32(pg+0x51e4),read(pg+0x20,2));room_stamp=read(pg+0x4f9c,6);room=struct.unpack('<H',read(pg+0x4f9e,2))[0]
 row=dict(process_age=age(),pg=pg,frame=stamp[0],phase=list(stamp[1]),room=hex(room),chapter=read(pg+0x4f8a,1)[0],Stop=hex(u32(pg+0x170)),status0=hex(u32(pg+0x500c)),status1=hex(u32(pg+0x5010)),status3=hex(u32(pg+0x5018)),health=list(struct.unpack('<4H',read(pg+0x4fa4,8))),Key_on=hex(u32(0x8c3a948c+16)),Key_trg=hex(u32(0x8c3a948c+24)))
 row.update(Part=read(pg+0x4f9d,1)[0],previous_room=hex(struct.unpack('<H',read(pg+0x4fa0,2))[0]),next_room=hex(struct.unpack('<H',read(pg+0x28,2))[0]),next_point=read(pg+0x2a,1)[0],scenario0=hex(u32(pg+0x51c0)),partner_ptr=u32(0x8c39d6fc))
 if room not in [0x204,0x209] or row['phase']!=[3,0]:return row if stamp==(u32(pg+0x51e4),read(pg+0x20,2))else None
 row['live_native_code_anchors_verified']=live_native_anchors()
 if not row['live_native_code_anchors_verified']:return row
 pl=u32(0x8c39d700)
 if not inram(pl,0x3a0):return None
 mat=list(struct.unpack('<12f',read(pl+12,48)));pos=list(struct.unpack('<3f',read(pl+0x94,12)))
 if not all(math.isfinite(v)for v in mat+pos):return None
 row.update(player_ptr=pl,player_pos=pos,player_matrix=mat,transformed_front_unclipped=[mat[i*4+1]*250+mat[i*4+2]*550+mat[i*4+3]for i in range(3)])
 sys=u32(0x8c3b94f0)
 if sys!=0x8c3b93cc:return None
 header=u32(sys);work=u32(sys+4)
 if not inram(header,16)or work!=header+16:return None
 head=read(header,16);n=struct.unpack_from('<H',head,6)[0]
 if head[:4]!=b'AEV\0'or struct.unpack_from('<H',head,4)[0]!=0x104 or not 0<n<256:return None
 table=read(work,n*0x9c);areas={}
 for i in range(n):
  q=table[i*0x9c:(i+1)*0x9c];no=q[0x36]
  if no in [0,4,0xa]:areas[hex(no)]=dict(ptr=work+i*0x9c,floor=struct.unpack_from('<f',q,8)[0],height=struct.unpack_from('<f',q,12)[0],enabled=bool(q[0x34]&1),type=q[0x35],checkFlag=q[0x37],trigger=q[0x38],checkType=q[0x39],func=struct.unpack_from('<I',q,0x40)[0],door=dict(destination=hex((q[0x6c]<<8)|q[0x6d]),Part=q[0x74],lockType=q[0x6e],lockFlag=q[0x6f],callback=hex(struct.unpack_from('<I',q,0x70)[0]),position=list(struct.unpack_from('<3f',q,0x5c)),angle=struct.unpack_from('<f',q,0x68)[0]),quad=[list(struct.unpack_from('<2f',q,0x14+j*8))for j in range(4)])
 row['areas']=areas;row['native_AEV04_clipped_hit']=bool(u32(sys+16)&0x08000000);row['native_AEV0A_clipped_hit']=bool(u32(sys+16)&0x00200000);row['native_AEV0A_executed']=bool(u32(sys+48)&0x00200000);row['camera_no']=struct.unpack('<b',read(0x8c3949a4+0x692,1))[0]
 act=read(0x8c392e20,260);ar=[]
 for i in range(8):
  q=act[68+i*24:68+(i+1)*24];ar.append(dict(func=struct.unpack_from('<I',q,4)[0],arg=struct.unpack_from('<I',q,8)[0],kind=q[12],slot=q[13],type=q[14],button=q[15],d=struct.unpack_from('<I',q,16)[0],flags=struct.unpack_from('<I',q,20)[0]))
 row['action']=dict(active=act[66],stop_old=act[65],num=act[64],work=ar)
 rd=0x8c3b9314;nr=struct.unpack('<H',read(rd+2,2))[0];sv=u32(rd+24);row['saved_RSF205']=None
 if 0<nr<256 and inram(sv,nr*0xd8):
  tb=read(sv,nr*0xd8);rsf=next((struct.unpack_from('<I',tb,i*0xd8+4)[0]for i in range(nr)if tb[i*0xd8:i*0xd8+2]==b'\x02\x05'),None);row['saved_RSF205']=rsf;row['saved_RSF204']=next((struct.unpack_from('<I',tb,i*0xd8+4)[0]for i in range(nr)if tb[i*0xd8:i*0xd8+2]==b'\x02\x04'),None)
  if tb!=read(sv,nr*0xd8)or nr!=struct.unpack('<H',read(rd+2,2))[0]or sv!=u32(rd+24):return None
 w=read(0x8c47fb58,1836);row['warp']=dict(flags=list(w[:5]),name=w[5:37].split(b'\0')[0].decode(errors='replace'),room=hex(struct.unpack_from('<H',w,38)[0]),rooms=struct.unpack_from('<I',w,1640)[0],room_frames=struct.unpack_from('<I',w,1632)[0],max_entry=w[1630],n_go=struct.unpack_from('<I',w,1176)[0],go0=w[984:1008].hex(),go1=w[1008:1032].hex(),go2=w[1032:1056].hex(),n_act=struct.unpack_from('<I',w,836)[0],n_rsf=struct.unpack_from('<I',w,204)[0],has_trg=w[840],has_kill=w[854])
 p=u32(0x8c39d3b8+20);seen=set();actors=[]
 while p and p not in seen and len(seen)<128:
  if not inram(p,0x3c8):return None
  seen.add(p);b=read(p,0x3c8);actor=dict(ptr=hex(p),id=b[0x100],type=b[0x101],source_list=b[0x398],hp=struct.unpack_from('<h',b,0x320)[0],native_status=hex(struct.unpack_from('<I',b,0x3c4)[0]),be_flag=hex(struct.unpack_from('<I',b,4)[0]),routines=list(b[0xfc:0x100]))
  if actor['id']==0x41:
   b=read(p,0x820);actor.update(flag=hex(struct.unpack_from('<I',b,0x3c8)[0]),position=list(struct.unpack_from('<3f',b,0x94)),Etc_no=b[0x81f],door_work_flags=hex(struct.unpack_from('<I',b,0x3e0)[0]),base_dir=struct.unpack_from('<f',b,0x778)[0],base_matrix=list(struct.unpack_from('<12f',b,0x77c)),base_inverse=list(struct.unpack_from('<12f',b,0x7ac)),key_flag=struct.unpack_from('<I',b,0x7dc)[0],open_flag=b[0x81d])
  actors.append(actor);p=struct.unpack_from('<I',b,8)[0]
 row['actors']=actors;row['physical_doors1']=[v for v in actors if v['id']==0x41 and v.get('Etc_no')==1]
 if stamp!=(u32(pg+0x51e4),read(pg+0x20,2))or room_stamp!=read(pg+0x4f9c,6)or pg!=u32(0x8c2e91dc)or pl!=u32(0x8c39d700):return None
 return row

WP=0x8c47fb58;COUNT=WP+1176;MAX_ENTRY=WP+1630
GO0_DONE=bytes.fromhex('00000000a894e4454f331c46025e27470000000001010001')
TARGET1=(-11179.9853515625,6000.99853515625,-28483.38525390625)
TARGET2=(-16150.030113227178,2001.,13499.981467821544)
STAGES={1:dict(room='0x204',entry=2,address=WP+1008,descriptor=struct.pack('<I4f4B',0,*TARGET1,0.,1,0,0,2)),2:dict(room='0x209',entry=3,address=WP+1032,descriptor=struct.pack('<I4f4B',0,*TARGET2,1.5707499980926514,1,0,0,3))}
WRITE_ALLOWLIST=[{'address':hex(STAGES[2]['address']),'bytes':24},{'address':hex(MAX_ENTRY),'bytes':1},{'address':hex(COUNT),'bytes':4}]

def freeplay_ready(row,room):
 return bool(row and row['room']==room and row['phase']==[3,0]and row['health'][0]>0 and row.get('live_native_code_anchors_verified')is True and row['Stop']=='0x0'and not(int(row['status1'],16)&0x10000000)and not(int(row['Key_on'],16)&0x80080000))

def consumed(w,stage):
 try:g=bytes.fromhex(w.get('go'+str(stage),''));d=STAGES[stage]['descriptor']
 except (ValueError,KeyError):return False
 return len(g)==24 and g[:21]==d[:21]and g[21]==1 and g[22:]==d[22:]

def setup_ready(row,stage,prepared=0):
 c=STAGES[stage];w=row.get('warp',{})if row else {};oldentry=c['entry']-1
 if not freeplay_ready(row,c['room']):return False
 if stage==1 and not(row.get('Part')==1 and row.get('previous_room')=='0x205'):return False
 if stage==2 and not(row.get('Part')==0 and row.get('previous_room')=='0x204'and consumed(w,1)):return False
 return w.get('flags')==[1,1,0,1,1]and w.get('name')=='castle21-CONTROLLED-ch32-drain0'and w.get('room')=='0x205'and w.get('rooms')==c['entry']and w.get('max_entry')==(c['entry']if prepared==2 else oldentry)and w.get('n_go')==stage and w.get('go0')==GO0_DONE.hex()and w.get('go'+str(stage))==('00'*24 if not prepared else c['descriptor'].hex())and(stage!=1 or w.get('go2')=='00'*24)and w.get('n_act')==0 and w.get('n_rsf')==0 and not w.get('has_trg')and not w.get('has_kill')

def exact_command_write(address,data,stage):
 assert stage==2,'Inheritedfirstplacementmustnotbereplayed'
 c=STAGES[stage]
 assert (address==c['address']and data==c['descriptor'])or(address==MAX_ENTRY and data==bytes([c['entry']]))or(address==COUNT and data==struct.pack('<I',stage+1)),'Only exact current-stage config writes'
 check();assert memory_ready and age()<29 and shutil.disk_usage(D).free>=18*1024**3+64*1024**2
 before=read(address,len(data));buf=C.create_string_buffer(data);got=C.c_size_t()
 receipt=dict(controlled_existing_rig_command_write=True,stage=stage,address=hex(address),before=before.hex(),after_requested=data.hex(),process_age=age());events.append(receipt)
 ok=bool(k.WriteProcessMemory(h,ram+address-0x8c000000,buf,len(data),C.byref(got)));receipt.update(api_ok=ok,bytes_written=got.value)
 assert ok and got.value==len(data),'Exact config write failed; no retry/rollback'
 receipt['observed_after']=read(address,len(data)).hex()

def publish_existing_goto(stage):
 assert stage==2
 check();row=sample();c=STAGES[stage]
 if not setup_ready(row,stage):return False
 events.append(dict(immediate_command_recheck=row,stage=stage,write_allowlist=WRITE_ALLOWLIST,no_actor_room_or_outcome_writes=True))
 exact_command_write(c['address'],c['descriptor'],stage)
 assert read(c['address'],24)==c['descriptor']and u32(COUNT)==stage,'Unpublished descriptor verification failed'
 row=sample();assert setup_ready(row,stage,1),'State changed before entry admission; no retry/rollback'
 exact_command_write(MAX_ENTRY,bytes([c['entry']]),stage)
 row=sample();assert setup_ready(row,stage,2),'State changed before count publication; no retry/rollback'
 exact_command_write(COUNT,struct.pack('<I',stage+1),stage)
 assert u32(COUNT)==stage+1,'Command publication not observed'
 events.append(dict(existing_goto_published=True,stage=stage,process_age=age(),entry=c['entry'],sub=False,count_published_last=True,engine_owns_done=True))
 return True

def pose_matches(row,stage):
 target=struct.unpack_from('<3f',STAGES[stage]['descriptor'],4);actual=row.get('player_pos',[])
 return len(actual)==3 and all(math.isfinite(v)for v in actual)and sum((actual[i]-target[i])**2 for i in range(3))<150**2

def door_ready(row,stage):
 if not freeplay_ready(row,STAGES[stage]['room'])or not consumed(row.get('warp',{}),stage)or not pose_matches(row,stage):return False
 act=row.get('action',{});w=row['warp']
 if w.get('n_go')!=stage+1 or w.get('max_entry')!=STAGES[stage]['entry']or w.get('rooms')!=STAGES[stage]['entry']or act.get('active')!=1:return False
 if stage==1:
  a=row.get('areas',{}).get('0x4',{});d=a.get('door',{})
  return row.get('native_AEV04_clipped_hit')is True and a.get('enabled')and a.get('type')==1 and a.get('func')==0 and a.get('checkFlag')==1 and a.get('trigger')==8 and a.get('checkType')==1 and d.get('destination')=='0x209'and d.get('Part')==0 and d.get('lockType')==0 and d.get('lockFlag')==0 and d.get('callback')=='0x0'and any(v.get('arg')==a.get('ptr')and v.get('kind')==0x10 and v.get('button')==1 and v.get('func')==0x8c14a95c and v.get('type')==2 and v.get('d')==row.get('player_ptr')for v in act.get('work',[]))
 doors=row.get('physical_doors1',[]);a=row.get('areas',{}).get('0xa',{})
 if len(doors)!=1 or a.get('type')!=2 or a.get('func',0)==0:return False
 d=doors[0]
 return d.get('type')==1 and d.get('hp',0)>0 and not(int(d['flag'],16)&0x30000000)and int(d['door_work_flags'],16)&1==0 and d.get('key_flag')==0x36 and all(math.isfinite(v)for v in d.get('position',[]))and len(d.get('position',[]))==3 and sum((d['position'][i]-[-15750.,2000.,12850.][i])**2 for i in range(3))<10**2 and any(v.get('arg')==int(d['ptr'],16)and v.get('kind')==0x10 and v.get('slot')==5 and v.get('button')==1 and v.get('func')in[0x8c0bc300,0x8c0bc384]and v.get('type')==0 and v.get('d')==0 and v.get('flags')==0 for v in act.get('work',[]))

def window_evidence(hwnd):
 check();p=W.DWORD();thread=int(u.GetWindowThreadProcessId(hwnd,C.byref(p)));assert p.value==owner['pid']and thread
 fg=int(u.GetForegroundWindow()or 0);fp=W.DWORD()
 if fg:u.GetWindowThreadProcessId(fg,C.byref(fp))
 q=GuiThreadInfo();q.cbSize=C.sizeof(q);C.set_last_error(0);ok=bool(u.GetGUIThreadInfo(thread,C.byref(q)));error=C.get_last_error();focus=int(q.hwndFocus or 0);kp=W.DWORD()
 if focus:u.GetWindowThreadProcessId(focus,C.byref(kp))
 return dict(hwnd=int(hwnd),owner_pid=p.value,thread_id=thread,foreground_hwnd=fg,foreground_pid=fp.value,gui_query_ok=ok,gui_query_error=error,active_hwnd=int(q.hwndActive or 0),focus_hwnd=focus,focus_pid=kp.value,focus_is_owned_child=bool(focus and u.IsChild(hwnd,focus)),gui_flags=q.flags,visible=bool(u.IsWindowVisible(hwnd)),iconic=bool(u.IsIconic(hwnd)),process_age=age())

def verified_owned_focus(e):
 return bool(e.get('gui_query_ok')and e.get('owner_pid')==owner['pid']and e.get('foreground_hwnd')==e.get('hwnd')and e.get('active_hwnd')==e.get('hwnd')and e.get('focus_pid')==owner['pid']and(e.get('focus_hwnd')==e.get('hwnd')or e.get('focus_is_owned_child')))

def ensure_owned_focus(hwnd):
 before=window_evidence(hwnd);events.append(dict(owned_window_before_focus=before))
 if verified_owned_focus(before):return True
 # One reversible focus request targets only this exact guest-owned SDL window.
 # No foreign window receives an input/focus request; guest closure returns control to Windows.
 check();accepted=bool(u.SetForegroundWindow(hwnd));until=time.monotonic()+.35;after=before
 while time.monotonic()<until and age()<32:
  check();after=window_evidence(hwnd)
  if verified_owned_focus(after):events.append(dict(owned_window_focus_verified=after,SetForegroundWindow_returned=accepted));return True
  time.sleep(.01)
 events.append(dict(owned_window_focus_unverified=after,SetForegroundWindow_returned=accepted,no_input=True));return False

def native_input_ack(row,stage):
 check();pg=u32(0x8c2e91dc);assert pg==row['pg'];f=u32(pg+0x51e4);old,on,trg=struct.unpack('<3Q',read(0x8c3a948c+8,24));phase=list(read(pg+0x20,2));nextroom=struct.unpack('<H',read(pg+0x28,2))[0];stable=f==u32(pg+0x51e4)
 keys=stable and bool((on|trg)&0x80080000==0x80080000);effect=stable and stage==1 and phase[0]==4 and nextroom==0x209
 return dict(frame=f,coherent=stable,Key_old=hex(old),Key_on=hex(on),Key_trg=hex(trg),phase=phase,next_room=hex(nextroom),native_key_ack=keys,original_door_request_ack=effect,acknowledged=keys or effect)

def pulse_door(stage):
 check();row=sample();result=dict(pressed=False,acknowledged=False,stage=stage)
 if not memory_ready or age()>=31.5 or not door_ready(row,stage):return result
 wins=[]
 @CALL
 def cb(w,_):
  p=W.DWORD();u.GetWindowThreadProcessId(w,C.byref(p));c=C.create_unicode_buffer(256);u.GetClassNameW(w,c,256)
  if p.value==owner['pid']and c.value=='SDL_app':wins.append(int(w))
  return True
 assert u.EnumWindows(cb,0)and len(wins)==1;hwnd=wins[0];pressed=False;ack=[];vk=ord('X');scan=0x2d
 if not ensure_owned_focus(hwnd):return result
 try:
  check();assert memory_ready and age()<32;row=sample();focus=window_evidence(hwnd)
  if not door_ready(row,stage)or not verified_owned_focus(focus):return result
  events.append(dict(immediate_native_door_A_recheck=row,stage=stage,owned_window_evidence=focus));assert u.PostMessageW(hwnd,0x100,vk,1|(scan<<16));pressed=True;result['pressed']=True;until=time.monotonic()+.75
  while time.monotonic()<until:
   check();assert age()<40.5;proof=native_input_ack(row,stage);ack.append(proof)
   if proof['acknowledged']:result['acknowledged']=True;break
   time.sleep(.003)
 finally:
  if pressed and k.WaitForSingleObject(h,0)==258:
   check();p=W.DWORD();u.GetWindowThreadProcessId(hwnd,C.byref(p));assert p.value==owner['pid'];assert u.PostMessageW(hwnd,0x101,vk,1|(scan<<16)|0xc0000000)
 if pressed:events.append(dict(ordinary_owned_UI_pulse=('native204-Door4-A'if stage==1 else'native209-physicalDoor1-A'),stage=stage,maximum_hold_seconds=.75,one_keydown_only=True,result=result,ack_observations=ack,owned_window_after_release=window_evidence(hwnd),process_age=age()))
 return result
def capture(row,label):
 check();assert age()<38.5 and shutil.disk_usage(D).free>=18*1024**3+64*1024**2
 matches=re.findall(r'fb=[0-9a-f]+,[0-9a-f]+',(cap/'run-output.txt').read_text(errors='replace'))
 if not matches:
  pair=(u32(0x8c483e00+312),u32(0x8c483e00+320));assert pair==(u32(0x8c483e00+312),u32(0x8c483e00+320))and pair==(0x230980,0x630980),'Stable inherited frozenPVRpair required'
  matches=['fb=%x,%x'%tuple(((0xd2800000+(v&0x7fffff))*2)&0xffffffff for v in pair)]
 spec=importlib.util.spec_from_file_location('controlled_load_capture',L/'capture-original-J-fast-RGB565.py');fc=importlib.util.module_from_spec(spec);spec.loader.exec_module(fc)
 shot=cap/'shots'/('controlled-'+label);shot.mkdir(parents=True,exist_ok=False)
 for n in ['emu.cfg','flycast.log','flycast.pid']:shutil.copyfile(cap/n,shot/n)
 (shot/'boot.log').write_text(matches[-1]+'\n',encoding='utf-16');before=sample();fc.capture(shot,shot/'frames');after=sample()
 (shot/'controlled-context.json').write_text(json.dumps(dict(scope='CONTROLLED actual019state; existing config command setup separate from original204Door4/209physicalDoor1/leader-event outputs.',observation=row,before=before,after=after,pngs=[dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest())for p in(shot/'frames').glob('*.png')]),indent=2)+'\n')

try:
 allocation=json.loads((L/'DOOR020-ROOT-ALLOCATION.json').read_text(encoding='utf-8'));assert allocation['allocated020']is True and allocation['allow_debug_goto_command_writes']is True and allocation['allow_owned_window_focus']is True and allocation['exclusive_gui_input']is True and allocation['maximum_successful_command_bytes']==29 and allocation['observer_sha256']==hashlib.sha256(Path(__file__).read_bytes()).hexdigest() and allocation['write_allowlist']==WRITE_ALLOWLIST, 'Exact root-owned debug command allocation required'
 until=time.monotonic()+70
 while not(cap/'owned-process.json').exists():assert time.monotonic()<until;time.sleep(.05)
 owner=json.loads((cap/'owned-process.json').read_text());h=k.OpenProcess(0x1000|0x10|0x20|0x8|0x100000,False,owner['pid']);assert h;check();age0=time.time()-(owner['start_filetime']/1e7-11644473600);mono0=time.monotonic();age=lambda:age0+time.monotonic()-mono0
 start=json.loads((cap/'run-start.json').read_text());assert start['elf_sha256']=='4d823b496b9a402baadabe7f679c089fa0fd55c7ffd175ec634915745a11487f'and start['disc_sha256']=='b67ac21eff8d819ef9ca5f0997b4c16401cb98a3d304feb65aa4b90f7affbeb6'
 assert re.search(r'(?m)^Dreamcast\.AutoLoadState = yes\s*$',(cap/'emu.cfg').read_text()),'Exact019 fullstate continuation requires AutoLoadState=yes'
 mapping=wait_startup_mapping();mapping_ready=mapping is not None
 if not mapping_ready:events.append(dict(startup_readiness_timeout=True,no_inputs=True))
 previous_readable=None;readiness_recorded=False;action_blocked=False
 published={1:True,2:False};sent={1:False,2:False};attempted={1:False,2:False};placed={1:True,2:False};entry=False;door_open=False;cut3=False;cut2=False;returned=False;shots=set();cut2frame=None
 events.append(dict(inherited017_firstcut_return=True,inherited019_placement_already_consumed=True,state_sha256='669b920f06e89403a15d3796021878c39ee9807fe020487e6a8666220f635631',no_replay_015_drain_or_017_firstcut=True,controlled_setup_maximum_successful_bytes=29))
 with(cap/'controlled-door020-observations.jsonl').open('x')as out:
  while k.WaitForSingleObject(h,0)==258 and age()<39:
   check()
   if not mapping_ready:time.sleep(.03);continue
   try:row=sample()
   except MemoryUnavailable:
    previous_readable=None;time.sleep(.03);continue
   if row:
    memory_ready=readable_sequence(row,previous_readable,ram)
    previous_readable=dict(pg=row['pg'],frame=row['frame'],RAM_base=ram)if row.get('live_native_code_anchors_verified')and row['phase']==[3,0]else None
    if memory_ready and not readiness_recorded:
     try:probe=read(0x8c2e91dc,4)
     except MemoryUnavailable:previous_readable=None;time.sleep(.03);continue
     if struct.unpack('<I',probe)[0]!=row['pg']:memory_ready=False;previous_readable=None;continue
     readiness_recorded=True;events.append(dict(initial_readable_native_sequence=row,RAM_base=hex(ram),no_inputs_before_readiness=True,exact_successful_pG_probe=dict(guest_address='0x8c2e91dc',host_address=hex(ram+0x2e91dc),requested_bytes=4,api_ok=True,bytes_read=4,data_hex=probe.hex(),process_identity=owner)))
    last=row;out.write(json.dumps(row)+'\n');out.flush()
    for stage in [1,2]:
     # Stage2 is not even offered before the actual original209 load has been observed.
     eligible=stage==1 or entry
     if eligible and memory_ready and not action_blocked and not published[stage]and age()<(18 if stage==1 else 28)and setup_ready(row,stage):
      try:published[stage]=publish_existing_goto(stage)
      except MemoryUnavailable as e:action_blocked=True;events.append(dict(command_read_unavailable_no_retry=e.detail,stage=stage))
     if published[stage]and not placed[stage]and row.get('room')==STAGES[stage]['room']and consumed(row.get('warp',{}),stage)and pose_matches(row,stage):
      placed[stage]=True;events.append(dict(native_existing_goto_consumed=row,stage=stage))
     if memory_ready and not action_blocked and placed[stage]and not attempted[stage]and age()<31.5 and door_ready(row,stage):
      attempted[stage]=True
      try:
       pulse_result=pulse_door(stage);sent[stage]=pulse_result['pressed'];events.append(dict(single_action_attempt=pulse_result,no_automatic_retry=True))
      except MemoryUnavailable as e:action_blocked=True;events.append(dict(input_read_unavailable_no_retry=e.detail,stage=stage))
    if sent[1]and row['phase'][0]==4 and row['next_room']=='0x209'and row['next_point']==0 and'request'not in shots:
     shots.add('request');events.append(dict(original_native_209_door_request=row))
    if sent[1]and row['room']=='0x209'and row['phase']==[3,0]and row['previous_room']=='0x204'and row['Part']==0:
     if not entry:entry=True;events.append(dict(actual_209_entry=row))
     if row.get('native_AEV0A_executed')and'aev0a'not in shots:shots.add('aev0a');events.append(dict(original_AEV0A_execution_observed=row))
     doors=row.get('physical_doors1',[])
     if sent[2]and len(doors)==1 and int(doors[0]['flag'],16)&0x10000000 and not door_open:door_open=True;events.append(dict(original_physicalDoor1_open_flag=row))
     event_active=bool(int(row['status1'],16)&0x10000000)
     if door_open and event_active and row.get('camera_no')==3 and not cut3:cut3=True;events.append(dict(original_leader_cut_camera3=row))
     if cut3 and event_active and row.get('camera_no')==2 and not cut2:cut2=True;cut2frame=row['frame'];events.append(dict(original_leader_cut_camera2=row))
     if cut2 and not returned and not event_active and row['Stop']=='0x0'and row['frame']>cut2frame:returned=True;events.append(dict(original_leader_cut_return=row))
    labels=[]
    if cut3 and not cut2 and age()<35:labels.append('original-leader-cut-camera3')
    if cut2 and not returned and age()<36:labels.append('original-leader-cut-camera2')
    if returned and age()<37:labels.append('original-leader-cut-return')
    if age()>=36 and age()<37:labels.append('deadline-context')
    for label in labels:
     if label not in shots:
      shots.add(label)
      try:capture(row,label)
      except Exception as e:events.append(dict(optional_capture_unavailable=repr(e),label=label))
   time.sleep(.03)
 if k.WaitForSingleObject(h,0)==258:close()
except BaseException as e:
 events.append(dict(observer_failure=repr(e),traceback=traceback.format_exc()))
 if h and k.WaitForSingleObject(h,0)==258:
  try:close()
  except Exception as x:events.append(dict(close_failed=repr(x)))
 raise
finally:
 if h:k.CloseHandle(h)
 if cap.exists():(cap/'controlled-door020-observer-summary.json').write_text(json.dumps(dict(scope=__doc__,last=last,events=events,owned_close_sent=closed_sent,source_fields_not_acceptance_alone=True,controlled_setup_not_event_completion=True,read_failure_count=read_failure_count,region_failure_count=region_failure_count,read_diagnostics=read_diagnostics),indent=2)+'\n')
