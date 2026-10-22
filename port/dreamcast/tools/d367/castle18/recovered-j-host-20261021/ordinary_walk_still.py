from pathlib import Path
import ctypes as C,ctypes.wintypes as W,json,time,sys,re,struct,math
cap=Path(sys.argv[1]).resolve();root=Path(r'C:\Flycast-Evidence\re4-dreamcast\castle18-20261018').resolve();assert cap.is_relative_to(root)and cap.parent.name=='recovered-j-content-20261021' and re.fullmatch(r'route-walk[0-9]+',cap.name);expected=int(sys.argv[4],16)if len(sys.argv)>4 else 0x200;assert expected in [0x200,0x202,0x207,0x203,0x201,0x208,0x204];targets=[tuple(float(v)for v in t.split(','))for t in sys.argv[2].split(';')];assert 1<=len(targets)<=12 and all(len(t)==2 and all(abs(v)<100000 for v in t)for t in targets);target_i=0;target=targets[0];tolerance=float(sys.argv[3])if len(sys.argv)>3 else 300;assert 30<=tolerance<=300;out=cap/'owned-window-current-stair-walk.json';assert not out.exists()
k=C.WinDLL('kernel32',use_last_error=True);u=C.WinDLL('user32',use_last_error=True);k.OpenProcess.argtypes=[W.DWORD,W.BOOL,W.DWORD];k.OpenProcess.restype=W.HANDLE;k.QueryFullProcessImageNameW.argtypes=[W.HANDLE,W.DWORD,W.LPWSTR,C.POINTER(W.DWORD)];k.GetProcessTimes.argtypes=[W.HANDLE,C.POINTER(W.FILETIME),C.POINTER(W.FILETIME),C.POINTER(W.FILETIME),C.POINTER(W.FILETIME)];k.ReadProcessMemory.argtypes=[W.HANDLE,C.c_void_p,C.c_void_p,C.c_size_t,C.POINTER(C.c_size_t)];k.ReadProcessMemory.restype=W.BOOL;k.CloseHandle.argtypes=[W.HANDLE];u.GetWindowThreadProcessId.argtypes=[W.HWND,C.POINTER(W.DWORD)];u.GetClassNameW.argtypes=[W.HWND,W.LPWSTR,C.c_int];u.IsWindow.argtypes=[W.HWND];u.IsWindow.restype=W.BOOL;u.PostMessageW.argtypes=[W.HWND,W.UINT,W.WPARAM,W.LPARAM];u.PostMessageW.restype=W.BOOL;u.MapVirtualKeyW.argtypes=[W.UINT,W.UINT];u.MapVirtualKeyW.restype=W.UINT;CALL=C.WINFUNCTYPE(W.BOOL,W.HWND,W.LPARAM);u.EnumWindows.argtypes=[CALL,W.LPARAM]
owner=None;h=None;hwnd=None;active=set();events=[];samples=[];deadline=time.monotonic()+180;mapkeys={'forward':(ord('I'),0x17),'left':(ord('J'),0x24),'right':(ord('L'),0x26),'dash':(ord('C'),0x2e),'back':(ord('K'),0x25)}
import importlib.util,hashlib
_fast_path=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18\capture-original-J-fast-RGB565.py')
_fast_spec=importlib.util.spec_from_file_location('private_same_method_fast_capture',_fast_path);fast_capture=importlib.util.module_from_spec(_fast_spec);_fast_spec.loader.exec_module(fast_capture)
_fast_sha=hashlib.sha256(_fast_path.read_bytes()).hexdigest();assert _fast_sha=='5237ac180e5473a301f037206970e2a8f4526307194c27844fc52ab56812def1'
_ready=cap.parent/(cap.name+'-controller-ready.json');assert not _ready.exists();_ready.write_text(json.dumps(dict(controller=str(Path(__file__)),controller_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),decoder=str(_fast_path),decoder_sha256=_fast_sha,preloaded_before_guest_launch_handshake=True))+'\n');events.append({'private_same_method_fast_framebuffer_decoder_preloaded':dict(path=str(_fast_path),sha256=_fast_sha)})

try:
 while not(cap/'owned-process.json').exists():assert time.monotonic()<deadline;time.sleep(.2)
 (cap/'owned-controller-source.py').write_bytes(Path(__file__).read_bytes())
 owner=json.loads((cap/'owned-process.json').read_text());assert Path(owner['path']).resolve()==cap/'flycast.exe';h=k.OpenProcess(0x10|0x1000,False,owner['pid']);assert h
 def check():
  path=C.create_unicode_buffer(32768);n=W.DWORD(32768);assert k.QueryFullProcessImageNameW(h,0,path,C.byref(n));assert Path(path.value).resolve()==cap/'flycast.exe';a,b,c,d=W.FILETIME(),W.FILETIME(),W.FILETIME(),W.FILETIME();assert k.GetProcessTimes(h,C.byref(a),C.byref(b),C.byref(c),C.byref(d));assert a.dwLowDateTime+(a.dwHighDateTime<<32)==owner['start_filetime']
 check();assert json.loads((cap/'run-start.json').read_text())['elf_sha256']=='4d823b496b9a402baadabe7f679c089fa0fd55c7ffd175ec634915745a11487f';assert json.loads((cap/'run-start.json').read_text())['disc_sha256']=='b67ac21eff8d819ef9ca5f0997b4c16401cb98a3d304feb65aa4b90f7affbeb6';found=[]
 @CALL
 def enum(w,_):
  p=W.DWORD();u.GetWindowThreadProcessId(w,C.byref(p));c=C.create_unicode_buffer(256);u.GetClassNameW(w,c,256)
  if p.value==owner['pid']and c.value=='SDL_app':found.append(int(w))
  return True
 while not found:
  assert time.monotonic()<deadline;assert u.EnumWindows(enum,0);time.sleep(.05)
 assert len(found)==1,('owned window lookup failed',found);hwnd=found[0];base=None
 while base is None:
  text=(cap/'flycast.log').read_text(errors='replace');m=re.findall(r'RAM\(16 MB\)\s+([0-9a-fA-F]+)',text)
  if m:base=int(m[-1],16)
  else:assert time.monotonic()<deadline;time.sleep(.2)
 # Wait for the exact owned snapshot load receipt before any guest read/input.
 while True:
  log=(cap/'flycast.log').read_text(errors='replace');loaded=re.findall(r'Loaded state ver \d+ from (.*?) size \d+',log)
  if loaded and Path(loaded[-1]).resolve()==(cap/'data/disc.state').resolve():events.append({'exact_owned_snapshot_loaded_before_input':loaded[-1]});break
  assert time.monotonic()<deadline,'Owned snapshot did not finish loading';check();time.sleep(.02)
 def read(a,n):
  assert 0x8c000000<=a and a+n<=0x8d000000;buf=C.create_string_buffer(n);got=C.c_size_t();assert k.ReadProcessMemory(h,base+a-0x8c000000,buf,n,C.byref(got))and got.value==n;return buf.raw
 u32=lambda a:struct.unpack('<I',read(a,4))[0]
 captured_checkpoint=False
 def capture_before_close():
  global captured_checkpoint
  if captured_checkpoint:return
  captured_checkpoint=True
  try:
   import importlib.util,shutil
   check();assert shutil.disk_usage(cap).free>=16*1024**3+64*1024**2,'Preserve retained runtime disk floor for screenshot'
   pg=u32(0x8c2e91dc);before=u32(pg+0x51e4);health=list(struct.unpack('<4H',read(pg+0x4fa4,8)));room=struct.unpack('<H',read(pg+0x4f9e,2))[0]
   fb=re.findall(r'fb=[0-9a-f]+,[0-9a-f]+',(cap/'run-output.txt').read_text(errors='replace'));until=time.monotonic()+4
   while not fb and time.monotonic()<until:
    check();time.sleep(.1);fb=re.findall(r'fb=[0-9a-f]+,[0-9a-f]+',(cap/'run-output.txt').read_text(errors='replace'))
   assert fb,'No matching framebuffer pointers in current owned run log'
   shot=cap/'shots'/('checkpoint-source-%d'%before);shot.mkdir(parents=True,exist_ok=False)
   for nm in ['emu.cfg','flycast.log','flycast.pid']:shutil.copyfile(cap/nm,shot/nm)
   (shot/'boot.log').write_text(fb[-1]+'\n',encoding='utf-16')
   fast_capture.capture(shot,shot/'frames');after=u32(pg+0x51e4)
   context={'run':cap.name,'lineage':'Recovered J NEW cold boot progression','iso_sha256':'b67ac21eff8d819ef9ca5f0997b4c16401cb98a3d304feb65aa4b90f7affbeb6','runtime':'12a841d7c','elf_sha256':'4d823b496b9a402baadabe7f679c089fa0fd55c7ffd175ec634915745a11487f','room':hex(room),'source_frame_interval':[before,after],'health_before':health,'health_after':list(struct.unpack('<4H',read(pg+0x4fa4,8))),'action_result':events[-1]if events else 'bounded normal knife arm checkpoint','last_sample':samples[-1]if samples else None,'capture_method':'Existing read-only VRAM/RGB565 method with offline-compatible private vector decoding, preloaded before guest; asynchronous source-frame interval, no simulation freeze','png_paths':[str(p)for p in (shot/'frames').glob('*.png')]}
   (shot/'checkpoint-context.json').write_text(json.dumps(context,indent=2)+'\n',encoding='utf-8');events.append({'checkpoint_screenshot':str(shot/'frames/fb0.png'),'context':str(shot/'checkpoint-context.json')})
  except Exception as e:events.append({'checkpoint_screenshot_unavailable':repr(e)})

 def transition(wanted):
  global last_input_refresh,input_refreshes
  if active and active==wanted:
   tp=u32(0x8c2e91dc);tf=u32(tp+0x51e4);kon=struct.unpack('<Q',read(0x8c3a948c+0x10,8))[0]
   if kon==0 and tf-last_input_refresh>=5:
    assert input_refreshes<8,'Normalinput source acknowledgment failed after8refreshes'
    for nm in sorted(active):
     vk,scan=mapkeys[nm];assert u.PostMessageW(hwnd,0x101,vk,1|(scan<<16)|0xc0000000)
    active.clear();until=time.monotonic()+1
    while u32(tp+0x51e4)<tf+2 and time.monotonic()<until:check();time.sleep(.005)
    last_input_refresh=u32(tp+0x51e4);input_refreshes+=1;events.append({'normal_owned_key_release_repress_after_source_Key_zero':{'source_frame':tf,'wanted':sorted(wanted),'count':input_refreshes}})
  check();assert u.IsWindow(hwnd);pid=W.DWORD();u.GetWindowThreadProcessId(hwnd,C.byref(pid));assert pid.value==owner['pid']
  for name in sorted(active-wanted):
   vk,scan=mapkeys[name];assert u.PostMessageW(hwnd,0x101,vk,1|(scan<<16)|0xc0000000);active.remove(name);events.append({'key':name,'up':True,'host_monotonic':time.monotonic()})
  for name in sorted(wanted-active):
   vk,scan=mapkeys[name];assert u.MapVirtualKeyW(vk,0)==scan;assert u.PostMessageW(hwnd,0x100,vk,1|(scan<<16));active.add(name);events.append({'key':name,'down':True,'host_monotonic':time.monotonic()})
 # Clear restored frontend held keys through ordinary owned-window button releases.
 for name,(vk,scan)in mapkeys.items():assert u.PostMessageW(hwnd,0x101,vk,1|(scan<<16)|0xc0000000)
 events.append({'normal_owned_button_releases_after_loaded_new_lineage_state':list(mapkeys)})
 last_input_refresh=-999;input_refreshes=0
 started=time.monotonic();stagnation=[];escape_life=None;last_quick=-999
 while time.monotonic()-started<49:
  pg=u32(0x8c2e91dc);assert 0x8c000000<=pg<=0x8cffa000;phase=tuple(read(pg+0x20,2));chapter=read(pg+0x4f8a,1)[0];assert chapter==6,('requires original chapter3-1 native load',chapter);pl=u32(0x8c39d700);
  assert not(u32(pg+0x500c)&0x100000),('original source death flag active',hex(u32(pg+0x500c)))
  if phase!=(3,0)or read(0x8c3de064+0x28,1)[0]!=0 or u32(pg+0x170)!=0 or u32(pg+0x5010)&0x10000000 or not(0x8c000000<=pl<=0x8cffff00):transition(set());samples.append({'waiting_source_phase':phase,'chapter':chapter,'Stop':hex(u32(pg+0x170)),'frame':u32(pg+0x51e4)});time.sleep(.15);continue
  assert not(u32(pg+0x500c)&0x100000),('original source death flag active',hex(u32(pg+0x500c)))
  room=struct.unpack('<H',read(pg+0x4f9e,2))[0];assert room==expected,('stop outside expected source room',room);hp,hp_max=struct.unpack('<hh',read(pg+0x4fa4,4));assert 0<hp<=hp_max<=10000,('sourceplayerinactive/dead',hp,hp_max)
  if escape_life is None:escape_life=hp
  if hp<1200 or struct.unpack('<H',read(pg+0x4fa8,2))[0]<600:
   transition(set());events.append({'normal_first_damage_checkpoint':True,'frame':u32(pg+0x51e4),'health':[hp,struct.unpack('<H',read(pg+0x4fa8,2))[0]]});capture_before_close();assert u.PostMessageW(hwnd,0x10,0,0);break
  assert hp>0,('Original escape source death',escape_life,hp);sub=u32(0x8c39d6fc);assert sub==0 or 0x8c000000<=sub<=0x8cffff00,('invalidsourcepartner',hex(sub));subhp=struct.unpack('<H',read(pg+0x4fa8,2))[0]if sub else None;assert subhp is None or 120<subhp<=10000,('sourcepartnerinactive/dead',subhp);assert read(pl+0x100,1)[0]==0 and (not sub or read(sub+0x100,1)[0]==3),('current actor identity guard',hex(pl),hex(sub));pos=struct.unpack('<3f',read(pl+0x94,12));yaw=struct.unpack('<3f',read(pl+0xa0,12))[1];assert all(math.isfinite(v)and abs(v)<1e6 for v in (*pos,yaw));dx,dz=target[0]-pos[0],target[1]-pos[2];distance=math.hypot(dx,dz);delta=(math.atan2(dx,dz)-yaw+math.pi)%(2*math.pi)-math.pi;samples.append({'host_monotonic':time.monotonic(),'room':hex(room),'frame':u32(pg+0x51e4),'player_hp':hp,'partner_hp':subhp,'pos':pos,'yaw':yaw,'target_distance':distance,'angle_error':delta})
  samples[-1]['source_Key_on']=hex(struct.unpack('<Q',read(0x8c3a948c+0x10,8))[0])
  now=time.monotonic();stagnation.append((now,u32(pg+0x51e4),pos[0],pos[2]));stagnation=[r for r in stagnation if now-r[0]<=8]
  if len(stagnation)>1 and now-stagnation[0][0]>=6 and stagnation[-1][1]-stagnation[0][1]>=10 and abs(delta)<.12 and distance>tolerance and math.hypot(target[0]-stagnation[0][2],target[1]-stagnation[0][3])-min(math.hypot(target[0]-r[2],target[1]-r[3])for r in stagnation)<100:
   transition(set());events.append({'normal_input_has_no_displacement':True,'frame':u32(pg+0x51e4),'pos':pos,'target':target,'source_tick_window':stagnation[-1][1]-stagnation[0][1]});check();assert u.IsWindow(hwnd);capture_before_close();assert u.PostMessageW(hwnd,0x10,0,0);events.append({'owned_close_after_collision_stop':True});break
  if distance<tolerance:
   transition(set());events.append({'waypoint_reached':target_i,'target':target,'pos':pos});target_i+=1
   if target_i>=len(targets):
    check();assert u.IsWindow(hwnd);capture_before_close();assert u.PostMessageW(hwnd,0x10,0,0);events.append({'owned_close_after_goals':True});break
   target=targets[target_i];stagnation=[];time.sleep(.15);continue
  if abs(delta)>2.5 and u32(pg+0x51e4)-last_quick>=60:
   before=u32(pg+0x51e4);transition({'back','dash'});until=time.monotonic()+.25
   while (u32(pg+0x51e4)<before+2 or time.monotonic()<until)and time.monotonic()<until+1:time.sleep(.01)
   transition(set());last_quick=before;events.append({'normal_back_and_B_quickturn':True,'frame':before,'starting_yaw':yaw,'desired_angle_error':delta});time.sleep(.1);continue
  wanted={'left'if delta>0 else'right'}if abs(delta)>.08 else{'forward','dash'}
  if abs(delta)>.08:
   before=u32(pg+0x51e4);moving=abs(delta)<.6;transition(wanted|({'forward','dash'}if moving else set()));until=time.monotonic()+.15
   while u32(pg+0x51e4)==before and time.monotonic()<until:time.sleep(.005)
   transition({'forward','dash'}if moving else set());time.sleep(.02)
  else:transition(wanted);time.sleep(.05)
 transition(set());check()
 if u.IsWindow(hwnd):capture_before_close();assert u.PostMessageW(hwnd,0x10,0,0);events.append({'owned_close_at_input_deadline':True})
except Exception as e:
 events.append({'abort':repr(e)})
 if h and hwnd:
  try:
   check()
   if u.IsWindow(hwnd):capture_before_close();assert u.PostMessageW(hwnd,0x10,0,0);events.append({'owned_close_on_guard':True})
  except Exception as e:events.append({'guard_close_refused':repr(e)})
finally:
 if h and hwnd and active:
  try:transition(set())
  except Exception as e:events.append({'cleanup_refused':repr(e)})
 if h:k.CloseHandle(h)
 out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps({'scope':'Normal controller forward+B-run and optional original quickturn key messages to exact ownedSDL HWND only; read-only guest scalar pose feedback; no writes to game/process/state, no global input/focus/mouse','memory_rights':'PROCESS_VM_READ|PROCESS_QUERY_LIMITED_INFORMATION','owner':owner,'window':hwnd,'target_xz':target,'events':events,'samples':samples},indent=2)+'\n');print(out,flush=True)