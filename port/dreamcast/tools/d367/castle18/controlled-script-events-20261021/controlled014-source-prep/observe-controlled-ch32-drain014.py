"""CONTROLLED cold205 original lever/drain observer; read-only memory, ordinary owned UI keys and WM_CLOSE."""
from pathlib import Path
import math
import ctypes as C,ctypes.wintypes as W,json,time,re,struct,sys,hashlib,importlib.util,shutil,traceback
L=Path(__file__).parent;D=Path(r'C:\Flycast-Evidence\re4-dreamcast\castle18-20261018\Test21\recovered-j-content-20261021');cap=Path(sys.argv[1]).resolve();assert cap==D/'route-walk-controlled-ch32-drain014'
k=C.WinDLL('kernel32',use_last_error=True);u=C.WinDLL('user32',use_last_error=True)
k.OpenProcess.argtypes=[W.DWORD,W.BOOL,W.DWORD];k.OpenProcess.restype=W.HANDLE;k.GetProcessTimes.argtypes=[W.HANDLE]+[C.POINTER(W.FILETIME)]*4;k.QueryFullProcessImageNameW.argtypes=[W.HANDLE,W.DWORD,W.LPWSTR,C.POINTER(W.DWORD)];k.ReadProcessMemory.argtypes=[W.HANDLE,C.c_void_p,C.c_void_p,C.c_size_t,C.POINTER(C.c_size_t)];k.WaitForSingleObject.argtypes=[W.HANDLE,W.DWORD];k.CloseHandle.argtypes=[W.HANDLE]
u.GetWindowThreadProcessId.argtypes=[W.HWND,C.POINTER(W.DWORD)];u.GetClassNameW.argtypes=[W.HWND,W.LPWSTR,C.c_int];u.PostMessageW.argtypes=[W.HWND,W.UINT,W.WPARAM,W.LPARAM];CALL=C.WINFUNCTYPE(W.BOOL,W.HWND,W.LPARAM);u.EnumWindows.argtypes=[CALL,W.LPARAM]
h=None;events=[];last=None;closed_sent=False
(D/(cap.name+'-observer-ready.json')).write_text(json.dumps(dict(scope=__doc__,sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))+'\n')
def check():
 assert k.WaitForSingleObject(h,0)==258,'Owned process exited'
 p=C.create_unicode_buffer(32768);n=W.DWORD(32768);assert k.QueryFullProcessImageNameW(h,0,p,C.byref(n));assert Path(p.value).resolve()==cap/'flycast.exe'
 a,b,c,d=(W.FILETIME()for _ in range(4));assert k.GetProcessTimes(h,C.byref(a),C.byref(b),C.byref(c),C.byref(d));assert a.dwLowDateTime+(a.dwHighDateTime<<32)==owner['start_filetime']
def read(a,n):
 assert 0x8c000000<=a and a+n<=0x8d000000;buf=C.create_string_buffer(n);got=C.c_size_t();assert k.ReadProcessMemory(h,ram+a-0x8c000000,buf,n,C.byref(got))and got.value==n;return buf.raw
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
META=json.loads((L/'controlled-ch32-drain014-room-message0.json').read_text())
def inram(a,n=1):return 0x8c000000<=a and a+n<=0x8d000000
def native_message():
 b=read(0x8c3b684c+8,236)
 return dict(vptr=struct.unpack_from('<I',b)[0],be_flag=struct.unpack_from('<I',b,8)[0],flags2=struct.unpack_from('<I',b,16)[0],routines=list(b[12:16]),wait=struct.unpack_from('<H',b,114)[0],button=b[116],attribute=struct.unpack_from('<I',b,132)[0],text=struct.unpack_from('<I',b,156)[0],table_size=struct.unpack_from('<b',b,228)[0],selection=struct.unpack_from('<b',b,229)[0],current=struct.unpack_from('<b',b,230)[0])
def message_identity(pg,m):
 lang=u32(0x8c3b64c4);table=u32(0x8c3b64c4+8)
 if str(lang)not in META['languages']or table!=u32(pg+0x4f20)or not inram(table,META['MDT_size']):return None
 spec=META['languages'][str(lang)];block=table+u32(table+4+lang*4)
 if block!=table+spec['table_offset']or u32(block+4)!=spec['count']:return None
 start=block+u32(block+8);end=block+u32(block+12)
 if start!=table+spec['message0_offset']or end!=table+spec['message0_end']:return None
 digest=hashlib.sha256(read(start,end-start)).hexdigest()
 if digest!=spec['sha256']or not start<=m['text']<end:return None
 return dict(language=lang,room_table=hex(table),message_no=0,start=hex(start),end=hex(end),sha256=digest)
native_anchors_verified=False
native_anchors=[]
def live_native_anchors():
 global native_anchors_verified,native_anchors
 if native_anchors_verified:return True
 e=(D.parent/'builds/c21jmW/re4dc-game.elf').read_bytes();phoff=struct.unpack_from('<I',e,28)[0];phsize,phnum=struct.unpack_from('<HH',e,42)
 assert e[:6]==b'\x7fELF\x01\x01'and phsize==32
 sites=[0x8c04bd30,0x8c087974,0x8c110f0c,0x8c14f0fc,0x8c2ce564]
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
 stamp=(u32(pg+0x51e4),read(pg+0x20,2));room=struct.unpack('<H',read(pg+0x4f9e,2))[0]
 row=dict(process_age=age(),pg=pg,frame=stamp[0],phase=list(stamp[1]),room=hex(room),chapter=read(pg+0x4f8a,1)[0],Stop=hex(u32(pg+0x170)),status0=hex(u32(pg+0x500c)),status1=hex(u32(pg+0x5010)),status3=hex(u32(pg+0x5018)),health=list(struct.unpack('<4H',read(pg+0x4fa4,8))),Key_on=hex(u32(0x8c3a948c+16)),Key_trg=hex(u32(0x8c3a948c+24)))
 if room!=0x205 or row['phase']!=[3,0]:return row if stamp==(u32(pg+0x51e4),read(pg+0x20,2))else None
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
  if no in [3,7,8,0x11,0x15,0x1b]:areas[hex(no)]=dict(ptr=work+i*0x9c,enabled=bool(q[0x34]&1),type=q[0x35],checkFlag=q[0x37],trigger=q[0x38],checkType=q[0x39],func=struct.unpack_from('<I',q,0x40)[0],quad=[list(struct.unpack_from('<2f',q,0x14+j*8))for j in range(4)])
 row['areas']=areas;row['native_AEV08_collision_clipped_front_hit']=bool(u32(sys+16)&0x00800000);row['native_AEV08_executed']=bool(u32(sys+48)&0x00800000)
 act=read(0x8c392e20,260);ar=[]
 for i in range(8):
  q=act[68+i*24:68+(i+1)*24];ar.append(dict(func=struct.unpack_from('<I',q,4)[0],arg=struct.unpack_from('<I',q,8)[0],kind=q[12],slot=q[13],type=q[14],button=q[15],d=struct.unpack_from('<I',q,16)[0],flags=struct.unpack_from('<I',q,20)[0]))
 row['action']=dict(active=act[66],stop_old=act[65],num=act[64],work=ar)
 rd=0x8c3b9314;nr=struct.unpack('<H',read(rd+2,2))[0];sv=u32(rd+24);row['saved_RSF205']=None
 if 0<nr<256 and inram(sv,nr*0xd8):
  tb=read(sv,nr*0xd8);rsf=next((struct.unpack_from('<I',tb,i*0xd8+4)[0]for i in range(nr)if tb[i*0xd8:i*0xd8+2]==b'\x02\x05'),None);row['saved_RSF205']=rsf
  if tb!=read(sv,nr*0xd8)or nr!=struct.unpack('<H',read(rd+2,2))[0]or sv!=u32(rd+24):return None
 row['message0']=native_message();row['message0_source_identity']=message_identity(pg,row['message0'])
 p=u32(0x8c39d3b8+20);seen=set();actors=[]
 while p and p not in seen and len(seen)<128:
  if not inram(p,0x3a0):return None
  seen.add(p);b=read(p,0x3a0);actors.append(dict(ptr=hex(p),id=b[0x100],type=b[0x101],source_list=b[0x398],hp=struct.unpack_from('<h',b,0x320)[0],be_flag=hex(struct.unpack_from('<I',b,4)[0]),routines=list(b[0xfc:0x100])));p=struct.unpack_from('<I',b,8)[0]
 row['actors']=actors;row['source68_active_observed']=any(v['source_list']==0x68 and int(v['be_flag'],16)&1 and v['hp']>0 for v in actors)
 if stamp!=(u32(pg+0x51e4),read(pg+0x20,2))or pg!=u32(0x8c2e91dc)or pl!=u32(0x8c39d700):return None
 return row

def lever_ready(row):
 if not row or row['room']!='0x205'or row['phase']!=[3,0]or row.get('saved_RSF205')is None:return False
 a=row.get('areas',{}).get('0x8',{});act=row.get('action',{})
 return row.get('live_native_code_anchors_verified')is True and row['chapter']==7 and row['health'][0]>0 and row['Stop']=='0x0'and not(int(row['status1'],16)&0x10000000)and not(row['saved_RSF205']&0xc0000000)and a.get('enabled')and a.get('checkFlag')==1 and a.get('checkType')==1 and a.get('trigger')==8 and a.get('func',0)!=0 and row.get('native_AEV08_collision_clipped_front_hit')and act.get('active')==1 and act.get('stop_old')==0 and any(v['arg']==a['ptr']and v['d']==row['player_ptr']and v['type']==2 and v['button']==1 and v['func']!=0 for v in act.get('work',[]))
def prompt_ready(row):
 if not row or row['room']!='0x205'or row['phase']!=[3,0]or row['health'][0]<=0:return False
 m=row.get('message0',{})
 return row.get('live_native_code_anchors_verified')is True and invoked and (exec_seen or held_seen)and row.get('saved_RSF205')is not None and not(row['saved_RSF205']&0x80000000)and row.get('message0_source_identity')and m.get('vptr')==0x8c2ce56c and m.get('be_flag',0)&1 and m.get('flags2',0)&1 and m.get('attribute')==0x1012 and m.get('button')==1 and m.get('wait')==0 and m.get('table_size')==2 and m.get('selection')==0 and m.get('current')in[0,1]
def pulse(kind):
 check()
 if age()>=30:return False
 row=sample()
 if not row:return False
 if kind=='lever-A':
  if not lever_ready(row):return False
  vk,scan,ext=ord('X'),0x2d,0
 elif kind=='choose-Yes':
  if not(prompt_ready(row)and row['message0']['current']==1):return False
  vk,scan,ext=(0x26,0x48,1)if row['message0']['attribute']&0x00800000 else(0x25,0x4b,1)
 else:
  assert kind=='confirm-Yes'
  if not(prompt_ready(row)and row['message0']['current']==0):return False
  vk,scan,ext=ord('X'),0x2d,0
 if int(row['Key_on'],16)&0x80080000:return False
 wins=[]
 @CALL
 def cb(w,_):
  p=W.DWORD();u.GetWindowThreadProcessId(w,C.byref(p));c=C.create_unicode_buffer(256);u.GetClassNameW(w,c,256)
  if p.value==owner['pid']and c.value=='SDL_app':wins.append(int(w))
  return True
 assert u.EnumWindows(cb,0)and len(wins)==1;hwnd=wins[0];pressed=False;ack=[]
 try:
  check()
  if age()>=30:return False
  row=sample()
  if not row or not(lever_ready(row)if kind=='lever-A'else(prompt_ready(row)and row['message0']['current']==(1 if kind=='choose-Yes'else 0)))or int(row['Key_on'],16)&0x80080000:return False
  events.append(dict(immediate_input_recheck=kind,row=row));assert u.PostMessageW(hwnd,0x100,vk,1|(scan<<16)|(ext<<24));pressed=True;end=time.monotonic()+.2
  while time.monotonic()<end:
   check();assert age()<40.5;ack.append(dict(frame=u32(row['pg']+0x51e4),Key_trg=hex(u32(0x8c3a948c+24))));time.sleep(.015)
 finally:
  if pressed and k.WaitForSingleObject(h,0)==258:
   check();p=W.DWORD();u.GetWindowThreadProcessId(hwnd,C.byref(p));assert p.value==owner['pid'];assert u.PostMessageW(hwnd,0x101,vk,1|(scan<<16)|(ext<<24)|0xc0000000)
 events.append(dict(ordinary_owned_UI_pulse=kind,seconds=.2,ack_observations=ack,process_age=age()));return True

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
 (shot/'controlled-context.json').write_text(json.dumps(dict(scope='CONTROLLED cold205 original lever/drain; source-native clipped-hit flag and transformed-unclipped front distinguished. Prompt/source identity and original end required; no outcome memory writes.',observation=row,before=before,after=after,pngs=[dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest())for p in(shot/'frames').glob('*.png')]),indent=2)+'\n')
try:
 until=time.monotonic()+70
 while not(cap/'owned-process.json').exists():assert time.monotonic()<until;time.sleep(.05)
 owner=json.loads((cap/'owned-process.json').read_text());h=k.OpenProcess(0x1000|0x10|0x100000,False,owner['pid']);assert h;check();age0=time.time()-(owner['start_filetime']/1e7-11644473600);mono0=time.monotonic();age=lambda:age0+time.monotonic()-mono0
 start=json.loads((cap/'run-start.json').read_text());assert start['elf_sha256']=='4d823b496b9a402baadabe7f679c089fa0fd55c7ffd175ec634915745a11487f'and start['disc_sha256']=='b67ac21eff8d819ef9ca5f0997b4c16401cb98a3d304feb65aa4b90f7affbeb6'
 assert re.search(r'(?m)^Dreamcast\.AutoLoadState = no\s*$',(cap/'emu.cfg').read_text()),'New controlled cold fixture requires AutoLoadState=no'
 while True:
  check();m=re.findall(r'RAM\(16 MB\)\s+([0-9a-fA-F]+)',(cap/'flycast.log').read_text(errors='replace'))
  if m:ram=int(m[-1],16);break
  assert age()<38,'Cold RAM deadline';time.sleep(.05)
 invoked=False;confirmed=False;directed=False;baseline=False;exec_seen=False;held_seen=False;shots=set();done_frame=None;released_at=None
 with(cap/'controlled-drain014-observations.jsonl').open('x')as out:
  while k.WaitForSingleObject(h,0)==258 and age()<39:
   check();row=sample()
   if row:
    last=row;out.write(json.dumps(row)+'\n');out.flush()
    if row.get('saved_RSF205')is not None and not(row['saved_RSF205']&0xc0000000):baseline=True
    exec_seen|=row.get('native_AEV08_executed',False);held_seen|=bool(int(row['status1'],16)&0x10000000)
    if baseline and not invoked and lever_ready(row)and age()<26:
     if pulse('lever-A'):invoked=True;released_at=age()
    elif invoked and not confirmed and prompt_ready(row)and age()<30 and age()>released_at+.15:
     if 'prompt'not in shots:
      shots.add('prompt')
      try:capture(row,'original-drain-prompt')
      except Exception as e:events.append(dict(optional_capture_unavailable=repr(e),label='prompt'))
     now=sample()
     if now and prompt_ready(now):
      if now['message0']['current']==1 and not directed:
       if pulse('choose-Yes'):directed=True;released_at=age()
      elif now['message0']['current']==0:
       if pulse('confirm-Yes'):confirmed=True;released_at=age()
    areas=row.get('areas',{});rsf=row.get('saved_RSF205')
    complete=baseline and invoked and confirmed and held_seen and rsf is not None and rsf&0xc0000000==0xc0000000 and all(not areas.get(k,{}).get('enabled',True)for k in ['0x7','0x8','0x15'])and areas.get('0x11',{}).get('enabled')and areas.get('0x1b',{}).get('func',0)!=0 and row['Stop']=='0x0'and not(int(row['status1'],16)&0x10000000)
    if complete and done_frame is None:done_frame=row['frame'];events.append(dict(original_drain_end_observed=row,actor68_active=row.get('source68_active_observed'),absent_actor_does_not_prove_held=True))
    labels=[]
    if done_frame is not None and row['frame']>=done_frame+5 and age()<37:labels.append('original-drain-end')
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
 if cap.exists():(cap/'controlled-drain014-observer-summary.json').write_text(json.dumps(dict(scope=__doc__,last=last,events=events,owned_close_sent=closed_sent,source_fields_not_acceptance_alone=True),indent=2)+'\n')
