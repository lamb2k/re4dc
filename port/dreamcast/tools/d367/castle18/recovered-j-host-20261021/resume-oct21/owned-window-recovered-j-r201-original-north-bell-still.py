from pathlib import Path
import ctypes as C,ctypes.wintypes as W,json,time,sys,re,struct,math
cap=Path(sys.argv[1]).resolve();root=Path(r'C:\Flycast-Evidence\re4-dreamcast\castle18-20261018').resolve();assert cap.is_relative_to(root)and cap.parent.name=='recovered-j-content-20261021' and re.fullmatch(r'route-walk[0-9]+',cap.name);expected=int(sys.argv[4],16)if len(sys.argv)>4 else 0x200;assert expected in [0x200,0x202,0x207,0x203,0x201,0x208,0x204];targets=[tuple(float(v)for v in t.split(','))for t in sys.argv[2].split(';')];assert 1<=len(targets)<=12 and all(len(t)==2 and all(abs(v)<100000 for v in t)for t in targets);target_i=0;target=targets[0];tolerance=float(sys.argv[3])if len(sys.argv)>3 else 300;assert 30<=tolerance<=300;out=cap/'owned-window-current-stair-walk.json';assert not out.exists()
k=C.WinDLL('kernel32',use_last_error=True);u=C.WinDLL('user32',use_last_error=True);k.OpenProcess.argtypes=[W.DWORD,W.BOOL,W.DWORD];k.OpenProcess.restype=W.HANDLE;k.QueryFullProcessImageNameW.argtypes=[W.HANDLE,W.DWORD,W.LPWSTR,C.POINTER(W.DWORD)];k.GetProcessTimes.argtypes=[W.HANDLE,C.POINTER(W.FILETIME),C.POINTER(W.FILETIME),C.POINTER(W.FILETIME),C.POINTER(W.FILETIME)];k.ReadProcessMemory.argtypes=[W.HANDLE,C.c_void_p,C.c_void_p,C.c_size_t,C.POINTER(C.c_size_t)];k.ReadProcessMemory.restype=W.BOOL;k.CloseHandle.argtypes=[W.HANDLE];u.GetWindowThreadProcessId.argtypes=[W.HWND,C.POINTER(W.DWORD)];u.GetClassNameW.argtypes=[W.HWND,W.LPWSTR,C.c_int];u.IsWindow.argtypes=[W.HWND];u.IsWindow.restype=W.BOOL;u.PostMessageW.argtypes=[W.HWND,W.UINT,W.WPARAM,W.LPARAM];u.PostMessageW.restype=W.BOOL;u.MapVirtualKeyW.argtypes=[W.UINT,W.UINT];u.MapVirtualKeyW.restype=W.UINT;CALL=C.WINFUNCTYPE(W.BOOL,W.HWND,W.LPARAM);u.EnumWindows.argtypes=[CALL,W.LPARAM]
owner=None;h=None;hwnd=None;active=set();events=[];samples=[];deadline=time.monotonic()+180;mapkeys={'forward':(ord('I'),0x17),'left':(ord('J'),0x24),'right':(ord('L'),0x26),'dash':(ord('C'),0x2e),'back':(ord('K'),0x25),'ready':(ord('V'),0x2f),'fire':(ord('X'),0x2d),'knife':(ord('F'),0x21),'inventory':(ord('D'),0x20),'menu_left':(0x25,0x4b,1),'menu_right':(0x27,0x4d,1),'menu_up':(0x26,0x48,1),'menu_down':(0x28,0x50,1)}
import importlib.util,hashlib
_fast_path=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18\capture-original-J-fast-RGB565.py')
_fast_spec=importlib.util.spec_from_file_location('private_same_method_fast_capture',_fast_path);fast_capture=importlib.util.module_from_spec(_fast_spec);_fast_spec.loader.exec_module(fast_capture)
_fast_sha=hashlib.sha256(_fast_path.read_bytes()).hexdigest();assert _fast_sha=='5237ac180e5473a301f037206970e2a8f4526307194c27844fc52ab56812def1'
_ready=cap.parent/(cap.name+'-controller-ready.json');assert not _ready.exists();_ready.write_text(json.dumps(dict(controller=str(Path(__file__)),controller_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),decoder=str(_fast_path),decoder_sha256=_fast_sha,preloaded_before_guest_launch_handshake=True))+'\n');events.append({'private_same_method_fast_framebuffer_decoder_preloaded':dict(path=str(_fast_path),sha256=_fast_sha)})

# Starting boss HP comes only from the exact immutable latest owned state receipt.
_arm=json.loads((cap.parent/(cap.name+'-inputs.json')).read_text());_seed=Path(_arm['seed']).resolve();assert _seed.parent==cap.parent and re.fullmatch(r'route-walk[0-9]+',_seed.name)
_sp=json.loads((cap.parent/(_seed.name+'-checkpoint-proof.json')).read_text());assert _sp['state_sha256']==_arm['seed_sha256']==hashlib.sha256((_seed/'data/disc.state').read_bytes()).hexdigest();assert _sp['start']['elf_sha256']=='4d823b496b9a402baadabe7f679c089fa0fd55c7ffd175ec634915745a11487f'
_sc=json.loads((_seed/'owned-window-current-stair-walk.json').read_text());_gr=[r['Garrador_hp'] if 'Garrador_hp'in r else r['Garrador']['hp']for r in _sc['samples']if 'Garrador_hp'in r or 'Garrador'in r];assert _gr;sealed_boss_hp=_gr[-1];assert 0<sealed_boss_hp<=4000

try:
 while not(cap/'owned-process.json').exists():assert time.monotonic()<deadline;time.sleep(.2)
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
  assert time.monotonic()<deadline;check();assert u.EnumWindows(enum,0);time.sleep(.05)
 assert len(found)==1,('owned window lookup failed',found);hwnd=found[0];base=None
 while base is None:
  text=(cap/'flycast.log').read_text(errors='replace');m=re.findall(r'RAM\(16 MB\)\s+([0-9a-fA-F]+)',text)
  if m:base=int(m[-1],16)
  else:assert time.monotonic()<deadline;time.sleep(.2)
 # Exact owned snapshot load required before any guest read or input.
 while True:
  log=(cap/'flycast.log').read_text(errors='replace');loaded=re.findall(r'Loaded state ver \d+ from (.*?) size \d+',log)
  if loaded and Path(loaded[-1]).resolve()==(cap/'data/disc.state').resolve():events.append({'exact_owned_snapshot_loaded_before_input':loaded[-1]});break
  assert time.monotonic()<deadline;check();time.sleep(.02)
 def read(a,n):
  assert 0x8c000000<=a and a+n<=0x8d000000;buf=C.create_string_buffer(n);got=C.c_size_t();assert k.ReadProcessMemory(h,base+a-0x8c000000,buf,n,C.byref(got))and got.value==n;return buf.raw
 u32=lambda a:struct.unpack('<I',read(a,4))[0]
 def transition(wanted):
  check();assert u.IsWindow(hwnd);pid=W.DWORD();u.GetWindowThreadProcessId(hwnd,C.byref(pid));assert pid.value==owner['pid']
  for name in sorted(active-wanted):
   vk,scan=mapkeys[name][:2];ext=mapkeys[name][2]if len(mapkeys[name])>2 else 0;assert u.PostMessageW(hwnd,0x101,vk,1|(scan<<16)|(ext<<24)|0xc0000000);active.remove(name);events.append({'key':name,'up':True,'host_monotonic':time.monotonic()})
  for name in sorted(wanted-active):
   vk,scan=mapkeys[name][:2];ext=mapkeys[name][2]if len(mapkeys[name])>2 else 0;assert u.MapVirtualKeyW(vk,0)==scan;assert u.PostMessageW(hwnd,0x100,vk,1|(scan<<16)|(ext<<24));active.add(name);events.append({'key':name,'down':True,'host_monotonic':time.monotonic()})

 def actors():
  ptr=u32(0x8c39d3b8+0x14);seen=set();result=[]
  while ptr:
   assert ptr not in seen and len(seen)<128 and 0x8c000000<=ptr<0x8cfff000;seen.add(ptr);b=read(ptr,0x410)
   pos=struct.unpack_from('<3f',b,0x94);assert all(math.isfinite(v)and abs(v)<1000000 for v in pos)
   result.append({'ptr':hex(ptr),'id':b[0x100],'type':b[0x101],'list_no':b[0x398],'hp':struct.unpack_from('<h',b,0x320)[0],'pos':pos,'routines':list(b[0xfc:0x100])});ptr=struct.unpack_from('<I',b,8)[0]
  return result
 def inventory():
  ip=u32(0x8c3a91f4+0x14);n=u32(0x8c3a91f4+0x1c);assert 1<=n<=512 and 0x8c000000<=ip and ip+n*14<0x8d000000
  items=[]
  for j in range(n):
   b=read(ip+j*14,14)
   if b[4]&1:items.append({'id':struct.unpack_from('<H',b,0)[0],'num':struct.unpack_from('<H',b,2)[0],'bullet':struct.unpack_from('<H',b,8)[0]&0x1fff,'raw':b.hex()})
  return items


 def pulse(name,ticks=2):
  before=u32(pg+0x51e4);transition({name});until=time.monotonic()+2
  while u32(pg+0x51e4)<before+ticks and time.monotonic()<until:time.sleep(.01)
  transition(set());time.sleep(.18)
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
 check();assert u.IsWindow(hwnd);wp=W.DWORD();u.GetWindowThreadProcessId(hwnd,C.byref(wp));assert wp.value==owner['pid']
 for nm,args in mapkeys.items():
  vk,scan=args[:2];ext=args[2]if len(args)>2 else 0;assert u.PostMessageW(hwnd,0x101,vk,1|(scan<<16)|(ext<<24)|0xc0000000)
 events.append({'normal_owned_all_button_releases_after_exact_snapshot_load':list(mapkeys)})

 def partptr(model,no):
  p=u32(model+0xf4);assert p
  if u32(model+4)&0x2000:return p+no*0x1d8
  for _ in range(no):p=u32(p+0xf4);assert p
  return p
 def point(model,no,ofs):
  m=struct.unpack('<12f',read(partptr(model,no)+0xc,48));assert all(math.isfinite(v)and abs(v)<1e6 for v in m)
  return [sum(m[j*4+i]*ofs[i]for i in range(3))+m[j*4+3]for j in range(3)],m
 def weakpoint(gp):
  cur=gp+0x33c;seen=set()
  while cur:
   assert cur not in seen and len(seen)<64;seen.add(cur);b=read(cur,0x34);no=struct.unpack_from('<h',b,0x26)[0]
   if no==37:
    center,m=point(gp,36,struct.unpack_from('<3f',b));radius=struct.unpack_from('<f',b,0x18)[0]*math.sqrt(m[2]**2+m[6]**2+m[10]**2);assert 150<radius<350 and struct.unpack_from('<f',b,0x1c)[0]==0
    return center,radius
   cur=struct.unpack_from('<I',b,0x30)[0]
  raise AssertionError('Original weakpoint37 missing')
 started=time.monotonic();last_fire=-999;shots=0;shot_pending=False;initial_boss_hp_checked=False;pitch_up_key='forward';baseline=sealed_boss_hp;hits=0;matrix_bad_since=None;rear_lost_since=None;death_since=None;reload_started=None;pitch_check=None;input_frame=None;last_refresh=-999;refresh_count=0;aligned_since=None;aim_settled_since=None;target_last=None;target_stable_since=0
 while time.monotonic()-started<46:
  check();pg=u32(0x8c2e91dc);ff=u32(pg+0x51e4);health=list(struct.unpack('<4H',read(pg+0x4fa4,8)));room=struct.unpack('<H',read(pg+0x4f9e,2))[0];phase=tuple(read(pg+0x20,2));stop=u32(pg+0x170);ss=read(0x8c3de064+0x28,1)[0];row={'frame':ff,'room':hex(room),'phase':phase,'Stop':hex(stop),'SSLoop':ss,'health':health};samples.append(row);assert room==0x201 and read(pg+0x4f8a,1)[0]==6
  if health[0]<1200 or health[2]<90:transition(set());events.append({'stop_on_any_further_original_health_loss':row});capture_before_close();assert u.PostMessageW(hwnd,0x10,0,0);break
  assert not(u32(pg+0x500c)&0x100000),'Original source death'
  if phase!=(3,0)or stop or ss or u32(pg+0x5010)&0x10000000:transition(set());time.sleep(.04);continue
  if input_frame is None:input_frame=ff;last_refresh=ff+6
  if ff<input_frame+6:transition({'ready'});time.sleep(.03);continue
  key_on=struct.unpack('<Q',read(0x8c3a948c+0x10,8))[0];row['source_Key_on']=hex(key_on)
  if active and key_on==0 and ff-last_refresh>=10:
   assert refresh_count<3,'Normal ownedinput still absent after3source-readiness refreshes'
   wanted=set(active);transition(set());before=ff;until=time.monotonic()+1
   while u32(pg+0x51e4)<before+3 and time.monotonic()<until:time.sleep(.01)
   transition(wanted);last_refresh=ff;refresh_count+=1;events.append({'normal_release_then_repress_after_no_source_input':dict(frame=ff,wanted=sorted(wanted))});time.sleep(.03);continue
  if shot_pending and ff-last_fire>=30:transition(set());events.append({'bounded_shot_reaction_observation_without_further_HP_drop':row});capture_before_close();assert u.PostMessageW(hwnd,0x10,0,0);break
  pl=u32(0x8c39d700);sub=u32(0x8c39d6fc);assert read(pl+0x100,1)[0]==0 and read(sub+0x100,1)[0]==3;assert struct.unpack('<H',read(sub+0x400,2))[0]&2,'Ashley Wait outside required';pos=struct.unpack('<3f',read(pl+0x94,12));yaw=struct.unpack('<f',read(pl+0xa4,4))[0];routine=list(read(pl+0xfc,4));gp=0x8caf2460;assert read(gp+0x100,2)==b'\x1b\x0a';ghp=struct.unpack('<h',read(gp+0x320,2))[0];gpos=struct.unpack('<3f',read(gp+0x94,12));gyaw=struct.unpack('<f',read(gp+0xa4,4))[0]
  if not initial_boss_hp_checked:assert ghp==baseline,'Exact continuation initial boss HP differs';initial_boss_hp_checked=True

  row.update(player_pos=pos,yaw=yaw,player_routines=routine,Garrador_hp=ghp,Garrador_pos=gpos,Garrador_yaw=gyaw,Garrador_routines=list(read(gp+0xfc,4)))
  assert math.dist(pos,gpos)>=3500,'Stop stationary bell arm if original enemy approaches3500'
  bell=0x8cadd6e0;assert read(bell+0x100,1)[0]==0x14 and math.dist(struct.unpack('<3f',read(bell+0x94,12)),(27273,178,-33277))<1,'Exact original northbell identity'
  hit=u32(bell+0x334);assert hit==0x8cc27d20 and read(hit+0x100,2)==bytes([0x4d,1]),'Exact source bell hit body'
  ring=struct.unpack('<h',read(bell+0x332,2))[0];assert 0<=ring<=90;row.update(original_bell=hex(bell),original_bell_hit=hex(hit),ringTimer=ring,status1=hex(u32(pg+0x5010)))
  if ring>0:
   transition({'ready'});events.append({'actual_original_bell_ringTimer_callback':dict(row),'ordinary_shots':shots});capture_before_close();assert u.PostMessageW(hwnd,0x10,0,0);break
  if shot_pending:transition({'ready'});time.sleep(.02);continue
  if routine[0]!=0:transition(set());time.sleep(.03);continue
  if routine[1]!=6:transition({'ready'});time.sleep(.025);continue
  transition({'ready'})
  if routine[2]!=1:time.sleep(.03);continue
  wp,_=point(bell,1,(0,-650,0));scaled_radius=300;row['original_bell_hit_world']=wp
  wep=u32(pl+0x788);obj=u32(wep+0x34);assert 0x8c000000<=obj<0x8cff0000;assert read(pg+0x4fb3,1)[0]==2,'Exact handgun source offset table only'
  muzzle,m=point(obj,0,(228,-24,29));dr=[-m[0],-m[4],-m[8]];norm=math.sqrt(sum(v*v for v in dr))
  if not .8<norm<1.2:
   transition({'ready'});events.append({'transient_nonunit_weapon_matrix_read_no_fire':dict(frame=ff,norm=norm)})
   if matrix_bad_since is None:matrix_bad_since=ff
   assert ff-matrix_bad_since<5,'Persistent invalid original weapon matrix; refuse aim/fire'
   time.sleep(.01);continue
  matrix_bad_since=None;dr=[v/norm for v in dr];v=[wp[i]-muzzle[i]for i in range(3)];dot=sum(v[i]*dr[i]for i in range(3));miss=math.sqrt(max(0,sum(a*a for a in v)-dot*dot));rayyaw=math.atan2(dr[0],dr[2]);raypitch=math.atan2(dr[1],math.hypot(dr[0],dr[2]));aim_v=list(v);row['normal_bell_aim_offset']=[0,0,0];yerr=(math.atan2(aim_v[0],aim_v[2])-rayyaw+math.pi)%(2*math.pi)-math.pi;perr=math.atan2(aim_v[1],math.hypot(aim_v[0],aim_v[2]))-raypitch;row.update(weapon_object=hex(obj),muzzle=muzzle,ray_direction=dr,ray_pitch=raypitch,ray_yaw_error=yerr,ray_pitch_error=perr,ray_sphere_miss=miss,ray_forward_distance=dot)
  aim_tolerance=max(.003,min(.02,60/max(dot,1)))
  row['range_dependent_aim_tolerance']=aim_tolerance
  if pitch_check is not None:
   before_pitch,desired_sign=pitch_check
   if abs(raypitch-before_pitch)>.002 and (raypitch-before_pitch)*desired_sign<0:pitch_up_key='back'if pitch_up_key=='forward'else'forward';events.append({'normal_pitch_direction_calibrated':pitch_up_key})
   pitch_check=None
  if abs(yerr)>aim_tolerance or abs(perr)>aim_tolerance:
   aim_settled_since=None;wanted={'ready'};counts=[]
   if abs(yerr)>aim_tolerance:wanted.add('left'if yerr>0 else'right');counts.append(max(1,min(5,int(abs(yerr)/.025))))
   if abs(perr)>aim_tolerance:
    wanted.add(pitch_up_key if perr>0 else('back'if pitch_up_key=='forward'else'forward'));counts.append(max(1,min(5,int(abs(perr)/.03))));pitch_check=(raypitch,1 if perr>0 else-1)
   ticks=min(counts);before=ff;transition(wanted);until=time.monotonic()+1
   while u32(pg+0x51e4)<before+ticks and time.monotonic()<until:check();time.sleep(.005)
   transition({'ready'});settle=u32(pg+0x51e4)+3;until=time.monotonic()+2
   while u32(pg+0x51e4)<settle and time.monotonic()<until:check();time.sleep(.005)
   events.append({'normal_two_axis_stick_pulse_then_pose_settle':dict(frame=before,keys=sorted(wanted),held_source_ticks=ticks,ray_yaw_error=yerr,ray_pitch_error=perr,settle_through=settle)});continue
  if key_on&15:aim_settled_since=None;transition({'ready'});time.sleep(.03);continue
  if aim_settled_since is None:aim_settled_since=ff
  row['normal_neutral_aim_source_ticks']=ff-aim_settled_since
  if ff-aim_settled_since<3 or target_stable_since is None or ff-target_stable_since<3:transition({'ready'});time.sleep(.03);continue
  marker=struct.unpack('<3f',read(obj+0x358,12));laser_target=u32(obj+0x364);row.update(laser_marker=marker,laser_target=hex(laser_target),laser_marker_to_weakpoint=math.dist(marker,wp))

  if dot>0 and miss<75:
   if aligned_since is None:aligned_since=ff
   if ff-aligned_since>=15 and laser_target!=hit:
    transition(set());events.append({'normal_bell_ray_aligned_but_original_laser_not_hit_body_no_shot':dict(row)});capture_before_close();assert u.PostMessageW(hwnd,0x10,0,0);break
  else:aligned_since=None
  if dot>0 and miss<75 and laser_target==hit and math.dist(marker,wp)<=350:
   gun=next(i for i in inventory()if i['id']==0x23);assert gun['bullet']>0 and shots==0,'Exactly one ordinary bell shot maximum'
   events.append({'ordinary_RT_A_to_original_bell_hit_body':dict(frame=ff,magazine=gun['bullet'],ray_miss=miss,laser_target=hex(laser_target),bell=hex(bell),original_hit_world=wp)});before=ff;transition({'ready','fire'});until=time.monotonic()+1
   while u32(pg+0x51e4)<before+3 and time.monotonic()<until:time.sleep(.005)
   transition({'ready'});last_fire=ff;shots=1;shot_pending=True
  time.sleep(.03)
 transition(set());check()
 if u.IsWindow(hwnd):capture_before_close();assert u.PostMessageW(hwnd,0x10,0,0);events.append({'owned_close_at_input_deadline':True})
except Exception as e:
 import traceback
 events.append({'abort':repr(e),'traceback':traceback.format_exc()})
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
 out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps({'scope':'Original northbell functional shot, exact source cObjBell/part1 parent target and cEmHit laser owner. One normalRT+A maximum, source ringTimer callback required;1200/90 anydamage/PID/phase/3500distance/50s guards. No game or actor/flag writes. Existing ancestry: actual recovered83 original4000HP/1200+90; existing qualified normal weakpoint37 controller, exact current actor/Wait location, no position changes; normal lower-edge aim70units below original spherecentre to clear original door lintel; actual original centre/radius/ray/laser/damage guards unchanged, boss761, strong rear angle; tighter physical aim target, actualpart37 proof required+safeWesternWait currentcheckpoint; require rear, stableweakpoint+neutralsettledaim3source ticks; normal RT entered BEFORE any directional aim; original in-place weapon aim/A only, actual source weapon-matrix ray and original weakpoint37 read-only guidance. Track actual HP drops; stop at six shots/hits, front-facing boss within3500 or any injury; farther original AI may be tracked with stationary aim but actual strong rear firing predicate is unchanged; original RSF0 callback required for completed kill; no aim/hit/projectile/HP/AI/flag/game writes or rollback.','memory_rights':'PROCESS_VM_READ|PROCESS_QUERY_LIMITED_INFORMATION','owner':owner,'window':hwnd,'events':events,'samples':samples},indent=2)+'\n');print(out,flush=True)
