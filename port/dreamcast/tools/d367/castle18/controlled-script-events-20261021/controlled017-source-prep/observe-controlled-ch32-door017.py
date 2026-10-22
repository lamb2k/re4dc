"""CONTROLLED exact016state continuation: existing DBG_WARP Goto command setup, ordinary native Door0 to204Part1; no actor/room/outcome memory writes."""
from pathlib import Path
import math
import ctypes as C,ctypes.wintypes as W,json,time,re,struct,sys,hashlib,importlib.util,shutil,traceback
L=Path(__file__).parent;D=Path(r'C:\Flycast-Evidence\re4-dreamcast\castle18-20261018\Test21\recovered-j-content-20261021');cap=Path(sys.argv[1]).resolve();assert cap==D/'route-walk-controlled-ch32-door017'
k=C.WinDLL('kernel32',use_last_error=True);u=C.WinDLL('user32',use_last_error=True)
k.OpenProcess.argtypes=[W.DWORD,W.BOOL,W.DWORD];k.OpenProcess.restype=W.HANDLE;k.GetProcessTimes.argtypes=[W.HANDLE]+[C.POINTER(W.FILETIME)]*4;k.QueryFullProcessImageNameW.argtypes=[W.HANDLE,W.DWORD,W.LPWSTR,C.POINTER(W.DWORD)];k.ReadProcessMemory.argtypes=[W.HANDLE,C.c_void_p,C.c_void_p,C.c_size_t,C.POINTER(C.c_size_t)];k.WaitForSingleObject.argtypes=[W.HANDLE,W.DWORD];k.CloseHandle.argtypes=[W.HANDLE]
u.GetWindowThreadProcessId.argtypes=[W.HWND,C.POINTER(W.DWORD)];u.GetClassNameW.argtypes=[W.HWND,W.LPWSTR,C.c_int];u.PostMessageW.argtypes=[W.HWND,W.UINT,W.WPARAM,W.LPARAM];CALL=C.WINFUNCTYPE(W.BOOL,W.HWND,W.LPARAM);u.EnumWindows.argtypes=[CALL,W.LPARAM]
k.WriteProcessMemory.argtypes=[W.HANDLE,C.c_void_p,C.c_void_p,C.c_size_t,C.POINTER(C.c_size_t)];k.WriteProcessMemory.restype=W.BOOL
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

def readable_sequence(row,previous,current_ram):
 return bool(row and previous and row.get('live_native_code_anchors_verified')is True and row.get('phase')==[3,0]and row.get('room')in['0x205','0x204']and row.get('pg')==previous.get('pg')and current_ram==previous.get('RAM_base')and row.get('frame',0)>previous.get('frame',0)and row.get('frame',0)>=1769)

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
 sites=[0x8c04bd30,0x8c087974,0x8c110f0c,0x8c14f0fc,0x8c2ce564,0x8c26cf88,0x8c14a95c]
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
 if room not in [0x205,0x204] or row['phase']!=[3,0]:return row if stamp==(u32(pg+0x51e4),read(pg+0x20,2))else None
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
  if no in [0,3,4,7,8,0x11,0x15,0x1b]:areas[hex(no)]=dict(ptr=work+i*0x9c,enabled=bool(q[0x34]&1),type=q[0x35],checkFlag=q[0x37],trigger=q[0x38],checkType=q[0x39],func=struct.unpack_from('<I',q,0x40)[0],door=dict(destination=hex((q[0x6c]<<8)|q[0x6d]),Part=q[0x74],lockType=q[0x6e],lockFlag=q[0x6f],callback=hex(struct.unpack_from('<I',q,0x70)[0]),position=list(struct.unpack_from('<3f',q,0x5c)),angle=struct.unpack_from('<f',q,0x68)[0]),quad=[list(struct.unpack_from('<2f',q,0x14+j*8))for j in range(4)])
 row['areas']=areas;row['native_AEV00_collision_clipped_front_hit']=bool(u32(sys+16)&0x80000000);row['native_AEV08_executed']=bool(u32(sys+48)&0x00800000)
 act=read(0x8c392e20,260);ar=[]
 for i in range(8):
  q=act[68+i*24:68+(i+1)*24];ar.append(dict(func=struct.unpack_from('<I',q,4)[0],arg=struct.unpack_from('<I',q,8)[0],kind=q[12],slot=q[13],type=q[14],button=q[15],d=struct.unpack_from('<I',q,16)[0],flags=struct.unpack_from('<I',q,20)[0]))
 row['action']=dict(active=act[66],stop_old=act[65],num=act[64],work=ar)
 rd=0x8c3b9314;nr=struct.unpack('<H',read(rd+2,2))[0];sv=u32(rd+24);row['saved_RSF205']=None
 if 0<nr<256 and inram(sv,nr*0xd8):
  tb=read(sv,nr*0xd8);rsf=next((struct.unpack_from('<I',tb,i*0xd8+4)[0]for i in range(nr)if tb[i*0xd8:i*0xd8+2]==b'\x02\x05'),None);row['saved_RSF205']=rsf;row['saved_RSF204']=next((struct.unpack_from('<I',tb,i*0xd8+4)[0]for i in range(nr)if tb[i*0xd8:i*0xd8+2]==b'\x02\x04'),None)
  if tb!=read(sv,nr*0xd8)or nr!=struct.unpack('<H',read(rd+2,2))[0]or sv!=u32(rd+24):return None
 w=read(0x8c47fb58,1836);row['warp']=dict(flags=list(w[:5]),name=w[5:37].split(b'\0')[0].decode(errors='replace'),room=hex(struct.unpack_from('<H',w,38)[0]),rooms=struct.unpack_from('<I',w,1640)[0],room_frames=struct.unpack_from('<I',w,1632)[0],max_entry=w[1630],n_go=struct.unpack_from('<I',w,1176)[0],go0=w[984:1008].hex(),n_act=struct.unpack_from('<I',w,836)[0],n_rsf=struct.unpack_from('<I',w,204)[0],has_trg=w[840],has_kill=w[854])
 p=u32(0x8c39d3b8+20);seen=set();actors=[]
 while p and p not in seen and len(seen)<128:
  if not inram(p,0x3c8):return None
  seen.add(p);b=read(p,0x3c8);actors.append(dict(ptr=hex(p),id=b[0x100],type=b[0x101],source_list=b[0x398],hp=struct.unpack_from('<h',b,0x320)[0],native_status=hex(struct.unpack_from('<I',b,0x3c4)[0]),be_flag=hex(struct.unpack_from('<I',b,4)[0]),routines=list(b[0xfc:0x100])));p=struct.unpack_from('<I',b,8)[0]
 row['actors']=actors;row['source68_active_observed']=any(v['source_list']==0x68 and int(v['be_flag'],16)&0x201==1 and int(v['native_status'],16)&0x20 for v in actors)
 if stamp!=(u32(pg+0x51e4),read(pg+0x20,2))or room_stamp!=read(pg+0x4f9c,6)or pg!=u32(0x8c2e91dc)or pl!=u32(0x8c39d700):return None
 return row

WP=0x8c47fb58;GO=WP+984;COUNT=WP+1176
TARGET=(7314.582275390625,9996.8271484375,42846.009765625)
DESCRIPTOR=struct.pack('<I4f4B',0,*TARGET,0.,1,0,0,1)
assert len(DESCRIPTOR)==24

def setup_ready(row,empty=True):
 if not row or row['room']!='0x205'or row['phase']!=[3,0]or row['health'][0]<=0:return False
 w=row.get('warp',{});a=row.get('areas',{});rsf=row.get('saved_RSF205')
 return row.get('live_native_code_anchors_verified')is True and row['Stop']=='0x0'and not(int(row['status1'],16)&0x10000000)and not(int(row['Key_on'],16)&0x80080000)and rsf is not None and rsf&0xc0000000==0xc0000000 and all(not a.get(x,{}).get('enabled',True)for x in ['0x7','0x8','0x15'])and a.get('0x11',{}).get('enabled')and a.get('0x1b',{}).get('func',0)!=0 and w.get('flags')==[1,1,0,1,1]and w.get('name')=='castle21-CONTROLLED-ch32-drain0'and w.get('room')=='0x205'and w.get('rooms')==1 and w.get('max_entry')==1 and w.get('n_go')==0 and w.get('go0')==('00'*24 if empty else DESCRIPTOR.hex())and w.get('n_act')==0 and w.get('n_rsf')==0 and not w.get('has_trg')and not w.get('has_kill')

def exact_command_write(address,data):
 assert (address==GO and data==DESCRIPTOR)or(address==COUNT and data==struct.pack('<I',1)),'Only declared existing goto command writes'
 check();assert memory_ready and age()<20 and shutil.disk_usage(D).free>=18*1024**3+64*1024**2
 before=read(address,len(data));buf=C.create_string_buffer(data);got=C.c_size_t()
 receipt=dict(controlled_existing_rig_command_write=True,address=hex(address),before=before.hex(),after_requested=data.hex(),process_age=age());events.append(receipt)
 ok=bool(k.WriteProcessMemory(h,ram+address-0x8c000000,buf,len(data),C.byref(got)));receipt.update(api_ok=ok,bytes_written=got.value)
 assert ok and got.value==len(data),'Exact config write failed; no retry/rollback'
 receipt['observed_after']=read(address,len(data)).hex()

def publish_existing_goto():
 check();row=sample()
 if not setup_ready(row):return False
 events.append(dict(immediate_command_recheck=row,write_allowlist={'descriptor':hex(GO),'publication':hex(COUNT)},no_actor_room_or_outcome_writes=True))
 exact_command_write(GO,DESCRIPTOR)
 assert read(GO,24)==DESCRIPTOR and u32(COUNT)==0,'Unpublished descriptor verification failed'
 row=sample();assert setup_ready(row,False),'State changed before publication; retain unconsumed command, no retry/rollback'
 exact_command_write(COUNT,struct.pack('<I',1))
 assert u32(COUNT)==1,'Command publication not observed'
 events.append(dict(existing_goto_published=True,process_age=age(),entry=1,sub=False,engine_owns_done=True))
 return True

def door_ready(row):
 if not row or row['room']!='0x205'or row['phase']!=[3,0]or row['health'][0]<=0:return False
 w=row.get('warp',{});a=row.get('areas',{}).get('0x0',{});d=a.get('door',{});act=row.get('action',{})
 try:g=bytes.fromhex(w.get('go0',''))
 except ValueError:return False
 return row.get('live_native_code_anchors_verified')is True and row['Stop']=='0x0'and not(int(row['status1'],16)&0x10000000)and w.get('n_go')==1 and len(g)==24 and g[:21]==DESCRIPTOR[:21]and g[21]==1 and g[22:]==DESCRIPTOR[22:]and row.get('native_AEV00_collision_clipped_front_hit')is True and a.get('enabled')and a.get('type')==1 and a.get('func')==0 and a.get('checkFlag')==1 and a.get('trigger')==8 and a.get('checkType')==1 and d.get('destination')=='0x204'and d.get('Part')==1 and d.get('lockType')==0 and d.get('lockFlag')==0 and d.get('callback')=='0x8c910320'and act.get('active')==1 and any(v.get('arg')==a.get('ptr')and v.get('kind')==0x10 and v.get('button')==1 and v.get('func')==0x8c14a95c and v.get('type')==2 and v.get('d')==row.get('player_ptr')for v in act.get('work',[]))and not(int(row['Key_on'],16)&0x80080000)

def pulse_door():
 check();row=sample()
 if not memory_ready or age()>=28 or not door_ready(row):return False
 wins=[]
 @CALL
 def cb(w,_):
  p=W.DWORD();u.GetWindowThreadProcessId(w,C.byref(p));c=C.create_unicode_buffer(256);u.GetClassNameW(w,c,256)
  if p.value==owner['pid']and c.value=='SDL_app':wins.append(int(w))
  return True
 assert u.EnumWindows(cb,0)and len(wins)==1;hwnd=wins[0];pressed=False;ack=[];vk=ord('X');scan=0x2d
 try:
  check();assert memory_ready and age()<28;row=sample()
  if not door_ready(row):return False
  events.append(dict(immediate_native_door_A_recheck=row));assert u.PostMessageW(hwnd,0x100,vk,1|(scan<<16));pressed=True;until=time.monotonic()+.2
  while time.monotonic()<until:
   check();assert age()<40.5;ack.append(dict(frame=u32(row['pg']+0x51e4),Key_trg=hex(u32(0x8c3a948c+24))));time.sleep(.015)
 finally:
  if pressed and k.WaitForSingleObject(h,0)==258:
   check();p=W.DWORD();u.GetWindowThreadProcessId(hwnd,C.byref(p));assert p.value==owner['pid'];assert u.PostMessageW(hwnd,0x101,vk,1|(scan<<16)|0xc0000000)
 events.append(dict(ordinary_owned_UI_pulse='native-upper-Door0-A',seconds=.2,ack_observations=ack,process_age=age()));return True
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
 (shot/'controlled-context.json').write_text(json.dumps(dict(scope='CONTROLLED exact015state existingrig goto placement then nativeDoor0/204Part1. Debugcommand setup is separate from originalexit/event outcomes.',observation=row,before=before,after=after,pngs=[dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest())for p in(shot/'frames').glob('*.png')]),indent=2)+'\n')

try:
 allocation=json.loads((L/'DOOR017-ROOT-ALLOCATION.json').read_text(encoding='utf-8'));assert allocation['allocated017']is True and allocation['allow_debug_goto_command_writes']is True and allocation['observer_sha256']==hashlib.sha256(Path(__file__).read_bytes()).hexdigest() and allocation['write_allowlist']==[{'address':'0x8c47ff30','bytes':24},{'address':'0x8c47fff0','bytes':4}], 'Exact root-owned debug command allocation required'
 until=time.monotonic()+70
 while not(cap/'owned-process.json').exists():assert time.monotonic()<until;time.sleep(.05)
 owner=json.loads((cap/'owned-process.json').read_text());h=k.OpenProcess(0x1000|0x10|0x20|0x8|0x100000,False,owner['pid']);assert h;check();age0=time.time()-(owner['start_filetime']/1e7-11644473600);mono0=time.monotonic();age=lambda:age0+time.monotonic()-mono0
 start=json.loads((cap/'run-start.json').read_text());assert start['elf_sha256']=='4d823b496b9a402baadabe7f679c089fa0fd55c7ffd175ec634915745a11487f'and start['disc_sha256']=='b67ac21eff8d819ef9ca5f0997b4c16401cb98a3d304feb65aa4b90f7affbeb6'
 assert re.search(r'(?m)^Dreamcast\.AutoLoadState = yes\s*$',(cap/'emu.cfg').read_text()),'Exact015 fullstate continuation requires AutoLoadState=yes'
 mapping=None;mapping_ready=False
 while age()<38:
  check();mapping=startup_log_mapping((cap/'flycast.log').read_text(errors='replace'),cap/'data/disc.state')
  if mapping and mapping['mapping_precedes_load']:
   ram=mapping['RAM'];q=region_query(ram+0x2e91dc,4)
   if q['committed']and q['accessible']and q['covers']:
    events.append(dict(startup_exact_state_load_and_mapping=mapping,process_age=age(),process_identity=owner,initial_pG_region=q));mapping_ready=True;break
   region_failure_count+=1
   if len(read_diagnostics)<100:read_diagnostics.append(dict(operation='startupVirtualQueryEx',RAM_base=hex(ram),process_age=age(),pid=owner['pid'],process_start_filetime=owner['start_filetime'],region=q))
  time.sleep(.03)
 if not mapping_ready:events.append(dict(startup_readiness_timeout=True,no_inputs=True))
 previous_readable=None;readiness_recorded=False;action_blocked=False
 published=False;door_sent=False;placed=False;entry=False;hold=False;returned=False;shots=set();hold_frame=None
 events.append(dict(inherited016_no_command_progress=True,inherited015_original_drain_completion=True,state_sha256='a33b2ac44cce042d035f7a981e96cf57b19bec1484f04c86084ece22803f73e8',actor68_active_not_observed=True,not_held_proof=True))
 with(cap/'controlled-door017-observations.jsonl').open('x')as out:
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
    if memory_ready and not action_blocked and not published and age()<18 and setup_ready(row):
     try:published=publish_existing_goto()
     except MemoryUnavailable as e:action_blocked=True;events.append(dict(command_read_unavailable_no_retry=e.detail))
    w=row.get('warp',{});g=bytes.fromhex(w.get('go0',''))
    if published and not placed and row['room']=='0x205'and len(g)==24 and g[21]==1:
     placed=True;events.append(dict(native_existing_goto_consumed=row))
    if memory_ready and not action_blocked and placed and not door_sent and age()<28 and door_ready(row):
     try:door_sent=pulse_door()
     except MemoryUnavailable as e:action_blocked=True;events.append(dict(input_read_unavailable_no_retry=e.detail))
    if door_sent and row['phase'][0]==4 and row['next_room']=='0x204'and row['next_point']==1 and 'request'not in shots:
     shots.add('request');events.append(dict(original_native_door_request=row))
    if door_sent and row['room']=='0x204'and row['phase']==[3,0]and row['previous_room']=='0x205'and row['Part']==1:
     if not entry:entry=True;events.append(dict(actual_204Part1_entry=row))
     if int(row['Stop'],16)&0x10000000 and not hold:hold=True;hold_frame=row['frame'];events.append(dict(original_first_cut_hold=row))
     if hold and not returned and row['Stop']=='0x0'and row['frame']>hold_frame:returned=True;events.append(dict(original_first_cut_return=row))
    labels=[]
    if entry and not returned and age()<35:labels.append('original-204Part1-entry')
    if returned and age()<37:labels.append('original-first-cut-return')
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
 if cap.exists():(cap/'controlled-door017-observer-summary.json').write_text(json.dumps(dict(scope=__doc__,last=last,events=events,owned_close_sent=closed_sent,source_fields_not_acceptance_alone=True,no_209_command=True,read_failure_count=read_failure_count,region_failure_count=region_failure_count,read_diagnostics=read_diagnostics),indent=2)+'\n')
