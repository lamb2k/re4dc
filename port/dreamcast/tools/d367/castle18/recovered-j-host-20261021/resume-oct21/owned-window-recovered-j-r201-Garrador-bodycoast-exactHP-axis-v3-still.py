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
_bc=json.loads((cap.parent/(_seed.name+'-exact-combat.json')).read_text());assert _bc['state_sha256']==_arm['seed_sha256'];sealed_boss_hp=_bc['boss']['hp'];assert 0<sealed_boss_hp<=4000

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
 sy=json.loads((root/'Test21/J-elf-scoped-symbols.json').read_text())['symbols'];pitch_m3r=next(x['address']for x in sy if x['name']=='m3r');pitch_system=next(x['address']for x in sy if x['name']=='_pSys')
 def held_aim_guard(pl,gp):
  check();hh=list(struct.unpack('<4H',read(pg+0x4fa4,8)));assert hh[0]>=_sp['health'][0] and hh[2]>=_sp['health'][2],'Original injury during bounded ordinary input'
  assert tuple(read(pg+0x20,2))==(3,0) and u32(pg+0x170)==0 and read(0x8c3de064+0x28,1)[0]==0,'Original phase changed during input'
  pp=struct.unpack('<3f',read(pl+0x94,12));ap=struct.unpack('<3f',read(u32(0x8c39d6fc)+0x94,12))
  assert read(gp+0x100,2)==b'\x1b\x0a';gg=struct.unpack('<3f',read(gp+0x94,12));gy=struct.unpack('<f',read(gp+0xa4,4))[0];dot=(pp[0]-gg[0])*math.sin(gy)+(pp[2]-gg[2])*math.cos(gy);assert not(dot>=-600 and math.hypot(pp[0]-gg[0],pp[2]-gg[2])<=9000 and read(gp+0xfc,1)[0]!=2),'Original active front9000 disengagement during input'
 def held_ray_feedback(pl,gp):
  wp,rr=weakpoint(gp);wep=u32(pl+0x788);obj=u32(wep+0x34);assert 0x8c000000<=obj<0x8cff0000;mu,mm=point(obj,0,(228,-24,29));dr=[-mm[0],-mm[4],-mm[8]];nn=math.sqrt(sum(v*v for v in dr))
  if not .8<nn<1.2:return None
  dr=[x/nn for x in dr];vv=[wp[i]-mu[i]for i in range(3)];av=[vv[0],vv[1]-70,vv[2]];ye=(math.atan2(av[0],av[2])-math.atan2(dr[0],dr[2])+math.pi)%(2*math.pi)-math.pi;pe=math.atan2(av[1],math.hypot(av[0],av[2]))-math.atan2(dr[1],math.hypot(dr[0],dr[2]));return ye,pe
 started=time.monotonic();body_align_since=None;body_coast_until_idle=False;body_previous=None;body_quick_done=False;body_input_frame=-999;body_refresh=0;last_fire=-999;shots=0;shot_pending=False;initial_boss_hp_checked=False;pitch_up_key='forward';baseline=sealed_boss_hp;hits=0;matrix_bad_since=None;rear_lost_since=None;death_since=None;reload_started=None;pitch_check=None;input_frame=None;last_refresh=-999;refresh_count=0;aligned_since=None;aim_settled_since=None;target_last=None;target_stable_since=None
 while time.monotonic()-started<42:
  check();pg=u32(0x8c2e91dc);ff=u32(pg+0x51e4);health=list(struct.unpack('<4H',read(pg+0x4fa4,8)));room=struct.unpack('<H',read(pg+0x4f9e,2))[0];phase=tuple(read(pg+0x20,2));stop=u32(pg+0x170);ss=read(0x8c3de064+0x28,1)[0];row={'frame':ff,'room':hex(room),'phase':phase,'Stop':hex(stop),'SSLoop':ss,'health':health};samples.append(row);assert room==0x201 and read(pg+0x4f8a,1)[0]==6
  if health[0]<_sp['health'][0] or health[2]<_sp['health'][2]:transition(set());events.append({'stop_on_any_further_original_health_loss':row});capture_before_close();assert u.PostMessageW(hwnd,0x10,0,0);break
  assert not(u32(pg+0x500c)&0x100000),'Original source death'
  if phase!=(3,0)or stop or ss or u32(pg+0x5010)&0x10000000:transition(set());time.sleep(.04);continue
  pl=u32(0x8c39d700);sub=u32(0x8c39d6fc);assert read(pl+0x100,1)[0]==0 and read(sub+0x100,1)[0]==3;assert struct.unpack('<H',read(sub+0x400,2))[0]&2,'Original Ashley Wait required'
  if input_frame is None:
   gp=0x8caf2460;held_aim_guard(pl,gp);qp=struct.unpack('<3f',read(pl+0x94,12));qy=struct.unpack('<f',read(pl+0xa4,4))[0];qh,_=weakpoint(gp);qd=(math.atan2(qh[0]-qp[0],qh[2]-qp[2])-qy+math.pi)%(2*math.pi)-math.pi;pr=list(read(pl+0xfc,4));row.update(body_prealign_error=qd,body_prealign_yaw=qy,body_prealign_routine=pr,source_raw_Joy_xy=list(struct.unpack('<2b',read(0x8c3a9544,2))),source_raw_Joy_on=hex(u32(0x8c3a9544+0x10)),source_Key_on=hex(struct.unpack('<Q',read(0x8c3a948c+0x10,8))[0]))
   if pr[0]!=0 or pr[1]in[5,6]:transition(set());body_align_since=None;time.sleep(.025);continue
   if not body_quick_done and abs(qd)>1.8:
    transition(set());before=ff;transition({'back'});until=time.monotonic()+1
    while True:
     held_aim_guard(pl,gp);qf=u32(pg+0x51e4);joy=struct.unpack('<b',read(0x8c3a9544+1,1))[0];kon=struct.unpack('<Q',read(0x8c3a948c+0x10,8))[0]
     if joy<=-30 and kon&2:break
     assert time.monotonic()<until and qf-before<30,'Ordinary Back source acknowledgment timed out';time.sleep(.005)
    transition({'back','dash'});until=time.monotonic()+1
    while u32(pg+0x51e4)<qf+3:held_aim_guard(pl,gp);assert time.monotonic()<until;time.sleep(.005)
    transition(set());body_quick_done=True;body_align_since=None;events.append({'ordinary_Back_ack_B_before_RT_then_wait_authored_routine':dict(frame=before,ack=qf,JoyY=joy,yaw=qy,delta=qd)});time.sleep(.025);continue
   jxy=struct.unpack('<2b',read(0x8c3a9544,2));kon=struct.unpack('<Q',read(0x8c3a948c+0x10,8))[0];rate=0
   if body_previous is not None and ff>body_previous[0]:rate=abs((qy-body_previous[1]+math.pi)%(2*math.pi)-math.pi)/(ff-body_previous[0])
   body_previous=(ff,qy);row['body_observed_yaw_rate']=rate
   if body_coast_until_idle:
    transition(set())
    if abs(jxy[0])>=30 or abs(jxy[1])>=30 or kon&15 or pr[1]!=0:body_align_since=None;time.sleep(.015);continue
    if body_align_since is None:body_align_since=ff
    if ff-body_align_since<3:time.sleep(.015);continue
    body_coast_until_idle=False;events.append({'ordinary_turn_release_observed_actual_neutral_idle_three_ticks':dict(frame=ff,Joy_xy=jxy,routine=pr,error=qd)})
   # Run260 source observations show ~three ticks of stick decay after key release.
   # Coarse setup accepts <=.30rad only after actual neutral/idle; final firing ray is unchanged.
   release_bound=max(.12,min(.35,rate*3+.05))
   if active & {'left','right'} and abs(qd)<=release_bound:
    transition(set());body_coast_until_idle=True;body_align_since=None;events.append({'ordinary_turn_early_release_for_observed_stick_decay':dict(frame=ff,error=qd,observed_yaw_rate=rate,release_bound=release_bound)});time.sleep(.015);continue
   if abs(qd)>.30:
    wanted={'left'if qd>0 else'right'};body_align_since=None
    if active==wanted and not(kon&12)and ff-body_input_frame>=10:
     assert body_refresh<3,'Standing turn source acknowledgment absent';transition(set());body_coast_until_idle=True;body_refresh+=1;time.sleep(.015);continue
    if active!=wanted:body_input_frame=ff
    transition(wanted);time.sleep(.015);continue
   if active:
    transition(set());body_coast_until_idle=True;body_align_since=None;time.sleep(.015);continue
   if abs(jxy[0])>=30 or abs(jxy[1])>=30 or kon&15 or pr[1]!=0:body_align_since=None;time.sleep(.015);continue
   if body_align_since is None:body_align_since=ff
   if ff-body_align_since<3:time.sleep(.015);continue
   events.append({'ordinary_standing_body_prealigned_and_settled_BEFORE_RT':dict(frame=ff,yaw=qy,bearing_error=qd,routine=pr)});input_frame=ff;last_refresh=ff+6
  if ff<input_frame+6:transition({'ready'});time.sleep(.03);continue
  key_on=struct.unpack('<Q',read(0x8c3a948c+0x10,8))[0];row['source_Key_on']=hex(key_on)
  if active and key_on==0 and ff-last_refresh>=10:
   assert refresh_count<3,'Normal ownedinput still absent after3source-readiness refreshes'
   wanted=set(active);transition(set());before=ff;until=time.monotonic()+1
   while u32(pg+0x51e4)<before+3 and time.monotonic()<until:time.sleep(.01)
   transition(wanted);last_refresh=ff;refresh_count+=1;events.append({'normal_release_then_repress_after_no_source_input':dict(frame=ff,wanted=sorted(wanted))});time.sleep(.03);continue
  pl=u32(0x8c39d700);sub=u32(0x8c39d6fc);assert read(pl+0x100,1)[0]==0 and read(sub+0x100,1)[0]==3;assert struct.unpack('<H',read(sub+0x400,2))[0]&2,'Ashley Wait outside required';pos=struct.unpack('<3f',read(pl+0x94,12));yaw=struct.unpack('<f',read(pl+0xa4,4))[0];routine=list(read(pl+0xfc,4));gp=0x8caf2460;assert read(gp+0x100,2)==b'\x1b\x0a';ghp=struct.unpack('<h',read(gp+0x320,2))[0];gpos=struct.unpack('<3f',read(gp+0x94,12));gyaw=struct.unpack('<f',read(gp+0xa4,4))[0]
  if not initial_boss_hp_checked:assert ghp==baseline,'Exact continuation initial boss HP differs';initial_boss_hp_checked=True
  if ghp<=0:
   transition(set());row.update(Garrador_hp=ghp,Garrador_routines=list(read(gp+0xfc,4)))
   saves=u32(0x8c3b9314+0x18);count=struct.unpack('<H',read(0x8c3b9314+2,2))[0];assert count<512
   rsf=None
   for j in range(count):
    sp=saves+j*0xd8
    if read(sp,2)==b'\x02\x01':rsf=u32(sp+4);break
   row['original_r201_saved_RSF']=hex(rsf)if rsf is not None else None
   if rsf is not None and rsf&0x80000000:
    if death_since is None:death_since=ff
    if ff-death_since>=30:events.append({'actual_original_death_callback_RSF0_and_stable_world':row});capture_before_close();assert u.PostMessageW(hwnd,0x10,0,0);break
   else:death_since=None
   time.sleep(.03);continue
  if shot_pending and ff-last_fire>=60:transition(set());events.append({'bounded_shot_reaction_observation_without_further_HP_drop':row});capture_before_close();assert u.PostMessageW(hwnd,0x10,0,0);break
  wp,scaled_radius=weakpoint(gp);row.update(original_weakpoint_scaled_radius=scaled_radius,player_pos=pos,yaw=yaw,player_routines=routine,Garrador_hp=ghp,Garrador_pos=gpos,Garrador_yaw=gyaw,Garrador_routines=list(read(gp+0xfc,4)),weakpoint37_world=wp,player_back_dot=(pos[0]-gpos[0])*math.sin(gyaw)+(pos[2]-gpos[2])*math.cos(gyaw))
  ap=struct.unpack('<3f',read(sub+0x94,12));assert math.hypot(ap[0]-29268,ap[2]+42749)<1200,'ActualAshley stays in original cell-exterior Wait46';row['partner_safe_corner_pos']=ap
  if target_last is None:target_last=(ff,wp)
  elif ff>target_last[0]:
   vel=math.dist(wp,target_last[1])/(ff-target_last[0]);row['weakpoint_velocity_per_source_tick']=vel
   if vel>40:target_stable_since=None
   elif target_stable_since is None:target_stable_since=ff
   target_last=(ff,wp)
  row.update(status1=hex(u32(pg+0x5010)),audible_footstep=bool(u32(pg+0x5010)&0x80000000))
  dp=u32(gp+0x338);row['actual_damage_record']={'weapon':read(gp+0x326,1)[0],'part_ptr':hex(dp),'partNo':struct.unpack('<h',read(dp+0x26,2))[0]if 0x8c000000<=dp<0x8cffff00 else None,'flags':read(gp+0x324,1)[0]}
  if ghp<baseline:
   transition({'ready'});events.append({'actual_original_handgun_Garrador_HP_drop':dict(row),'baseline_HP':baseline,'ordinary_shot_count':shots});baseline=ghp;hits+=1;last_fire=ff;shot_pending=False;target_stable_since=None;target_last=None;aim_settled_since=None;aligned_since=None
   if row['actual_damage_record']['partNo']!=37:events.append({'actual_body_part_hit_not_weakpoint_stop_ammo':dict(row)});capture_before_close();assert u.PostMessageW(hwnd,0x10,0,0);break
   if hits>=6 or shots>=6:events.append({'bounded_six_shot_or_hit_segment_complete':dict(row)});capture_before_close();assert u.PostMessageW(hwnd,0x10,0,0);break
   if hits in[1,3]:captured_checkpoint=False;capture_before_close();captured_checkpoint=False
   continue
  if routine[0]!=0:transition(set());time.sleep(.03);continue
  if row['player_back_dot']>=-600:
   row['far_original_AI_tracking_no_frontal_shot']=True
   if math.hypot(pos[0]-gpos[0],pos[2]-gpos[2])<=9000 and row['Garrador_routines'][0]!=2:
    transition(set());events.append({'active_front_facing_boss_within9000_early_disengagement_no_shot':dict(row)});capture_before_close();assert u.PostMessageW(hwnd,0x10,0,0);break
  rear_lost_since=None

  delta=(math.atan2(wp[0]-pos[0],wp[2]-pos[2])-yaw+math.pi)%(2*math.pi)-math.pi;row['standing_target_yaw_error']=delta
  if routine[1]!=6:
   transition({'ready'});row['normal_ready_before_any_standing_turn']=True;time.sleep(.025);continue
  if not(active & {'left','right','forward','back'}):transition({'ready'})
  gun=next(i for i in inventory()if i['id']==0x23)
  if gun['bullet']==0 and routine[2]==1:
   assert any(i['id']==4 and i['num']>0 for i in inventory()),'No reserve ammunition'
   events.append({'normal_RT_B_reload_empty_handgun':dict(frame=ff,inventory=inventory())});before=ff;transition({'ready','dash'});until=time.monotonic()+1
   while u32(pg+0x51e4)<before+3 and time.monotonic()<until:time.sleep(.005)
   transition({'ready'});last_fire=ff;time.sleep(.03);continue
  if routine[2]!=1:time.sleep(.03);continue
  wep=u32(pl+0x788);obj=u32(wep+0x34);assert 0x8c000000<=obj<0x8cff0000;assert read(pg+0x4fb3,1)[0]==2,'Exact handgun source offset table only'
  muzzle,m=point(obj,0,(228,-24,29));dr=[-m[0],-m[4],-m[8]];norm=math.sqrt(sum(v*v for v in dr))
  if not .8<norm<1.2:
   transition({'ready'});events.append({'transient_nonunit_weapon_matrix_read_no_fire':dict(frame=ff,norm=norm)})
   if matrix_bad_since is None:matrix_bad_since=ff
   assert ff-matrix_bad_since<5,'Persistent invalid original weapon matrix; refuse aim/fire'
   time.sleep(.01);continue
  matrix_bad_since=None;dr=[v/norm for v in dr];v=[wp[i]-muzzle[i]for i in range(3)];dot=sum(v[i]*dr[i]for i in range(3));miss=math.sqrt(max(0,sum(a*a for a in v)-dot*dot));rayyaw=math.atan2(dr[0],dr[2]);raypitch=math.atan2(dr[1],math.hypot(dr[0],dr[2]));aim_v=[v[0],v[1]-70,v[2]];row['normal_aim_point_offset_within_original_sphere']=[0,-70,0];yerr=(math.atan2(aim_v[0],aim_v[2])-rayyaw+math.pi)%(2*math.pi)-math.pi;perr=math.atan2(aim_v[1],math.hypot(aim_v[0],aim_v[2]))-raypitch;row.update(weapon_object=hex(obj),muzzle=muzzle,ray_direction=dr,ray_pitch=raypitch,ray_yaw_error=yerr,ray_pitch_error=perr,ray_sphere_miss=miss,ray_forward_distance=dot)
  aim_tolerance=max(.003,min(.02,60/max(dot,1)))
  row['range_dependent_aim_tolerance']=aim_tolerance
  pitch_up_key='back'if u32(u32(pitch_system))&0x80000000 else'forward';pitch_check=None;row['source_m3r']=list(struct.unpack('<3f',read(pitch_m3r,12)))
  if abs(yerr)>aim_tolerance or abs(perr)>aim_tolerance:
   aim_settled_since=None;wanted={'ready'};axes=[]
   if abs(yerr)>max(aim_tolerance,2*abs(perr)):
    wanted.add('left'if yerr>0 else'right');ticks=max(3,min(20,int(abs(yerr)/.02)));axes=[0]
   elif abs(perr)>max(aim_tolerance,2*abs(yerr)):
    wanted.add(pitch_up_key if perr>0 else('back'if pitch_up_key=='forward'else'forward'));ticks=max(3,min(12,int(abs(perr)/.01)));axes=[1]
   else:
    if abs(yerr)>aim_tolerance:wanted.add('left'if yerr>0 else'right');axes.append(0)
    if abs(perr)>aim_tolerance:wanted.add(pitch_up_key if perr>0 else('back'if pitch_up_key=='forward'else'forward'));axes.append(1)
    ticks=max(3,min(8,int(max(abs(yerr),abs(perr))/.02)))
   before=u32(pg+0x51e4);before_m3r=list(struct.unpack('<3f',read(pitch_m3r,12)));initial=(yerr,perr);feedback=[];last_ff=-1;crossed=False;transition(wanted);until=time.monotonic()+2
   while u32(pg+0x51e4)<before+ticks:
    held_aim_guard(pl,gp);assert time.monotonic()<until,'Bounded source input correction walltime';cf=u32(pg+0x51e4);errs=held_ray_feedback(pl,gp)
    if errs is None:crossed=True;break
    if cf!=last_ff:
     feedback.append(dict(frame=cf,errors=errs,m3r=list(struct.unpack('<3f',read(pitch_m3r,12))),Joy_xy=list(struct.unpack('<2b',read(0x8c3a9544,2))),Joy_on=hex(u32(0x8c3a9544+0x10)),Key_on=hex(struct.unpack('<Q',read(0x8c3a948c+0x10,8))[0])));last_ff=cf
     if cf>before and any(abs(errs[i])<=aim_tolerance*.8 or errs[i]*initial[i]<=0 for i in axes):crossed=True;break
    time.sleep(.005)
   after=u32(pg+0x51e4);errs=held_ray_feedback(pl,gp);near=errs is None or all(abs(errs[i])<=aim_tolerance for i in axes);settled=crossed or near
   if settled:
    transition({'ready'});settle=u32(pg+0x51e4)+3;until=time.monotonic()+2
    while u32(pg+0x51e4)<settle:held_aim_guard(pl,gp);assert time.monotonic()<until;time.sleep(.005)
   events.append({'reviewed_dominant_axis_held_correction':dict(frame_interval=[before,after],keys=sorted(wanted),max_source_ticks=ticks,initial_errors=initial,ended_errors=errs,crossed_or_near=settled,preserved_nonzero_axis=not settled,source_m3r_before=before_m3r,source_m3r_after=list(struct.unpack('<3f',read(pitch_m3r,12))),source_feedback=feedback)});continue
  if key_on&15:aim_settled_since=None;transition({'ready'});time.sleep(.03);continue
  if aim_settled_since is None:aim_settled_since=ff
  row['normal_neutral_aim_source_ticks']=ff-aim_settled_since
  if ff-aim_settled_since<3 or target_stable_since is None or ff-target_stable_since<3:transition({'ready'});time.sleep(.03);continue
  marker=struct.unpack('<3f',read(obj+0x358,12));laser_target=u32(obj+0x364);row.update(laser_marker=marker,laser_target=hex(laser_target),laser_marker_to_weakpoint=math.dist(marker,wp))
  if dot>0 and miss<75:
   if aligned_since is None:aligned_since=ff
   if ff-aligned_since>=15 and(laser_target!=gp or abs(math.dist(marker,wp)-scaled_radius)>30):transition(set());events.append({'normal_aim_aligned_but_original_laser_occluded_or_no_weakpoint_target_no_shot':row});capture_before_close();assert u.PostMessageW(hwnd,0x10,0,0);break
  else:aligned_since=None
  if dot>0 and miss<75 and row['player_back_dot']<-.7*math.hypot(pos[0]-gpos[0],pos[2]-gpos[2]) and ff-last_fire>=30 and laser_target==gp and abs(math.dist(marker,wp)-scaled_radius)<30:
   gun=next(i for i in inventory()if i['id']==0x23);assert gun['bullet']>0,'Stop for ordinary reload';assert shots<6,'Six-shot segment bound'
   events.append({'ordinary_RT_A_when_actual_weapon_ray_intersects_weakpoint37_sphere':dict(frame=ff,hp=ghp,magazine=gun['bullet'],ray_miss=miss,back_dot=row['player_back_dot'])});before=ff;transition({'ready','fire'});until=time.monotonic()+1
   while u32(pg+0x51e4)<before+3 and time.monotonic()<until:time.sleep(.005)
   transition({'ready'});last_fire=ff;shots+=1;shot_pending=True
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
 out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps({'scope':'Independent source-reviewed ordinary control setup: complete normal source-ack quickturn, standing coarse body prealign below0.30rad with observed-yaw earlyrelease and latched actual neutral/idle+3ticks BEFORE RT, recompute physical ray after RT camera-pitch initialization. Actual sourceSys inversion/m3r, dominant-axis3..20yaw/3..12pitch held corrections with intrahold geometry/health/proximity/sourceack polling, earlycross/near stop, persistent nonzeroaxis at coarsecap; final3tick neutral only when settled. Original collision/ray/laser/HP/shot/injury/PID/resource guards unchanged. Source-prepared until actual Flycast proof. Resumed sustained combat:9000 front guard checks active enemy rather than original damage-routine2 pose rotation; actual shot still requires strongrear, exact ray/laser/part37. Original death branch precedes shot-pending timeout. Anyinjury/phase/PID/resource guards unchanged. Historical base: unchanged6shot/hit unit, stronger9000 frontal disengagement and shorter42s controller bound. Actual recovered83 original4000HP/1200+90; existing qualified normal weakpoint37 controller, exact current actor/Wait location, no position changes; normal lower-edge aim70units below original spherecentre to clear original door lintel; actual original centre/radius/ray/laser/damage guards unchanged, boss761, strong rear angle; tighter physical aim target, actualpart37 proof required+safeWesternWait currentcheckpoint; require rear, stableweakpoint+neutralsettledaim3source ticks; normal RT entered BEFORE any directional aim; original in-place weapon aim/A only, actual source weapon-matrix ray and original weakpoint37 read-only guidance. Track actual HP drops; stop at six shots/hits, front-facing boss within3500 or any injury; farther original AI may be tracked with stationary aim but actual strong rear firing predicate is unchanged; original RSF0 callback required for completed kill; no aim/hit/projectile/HP/AI/flag/game writes or rollback.','memory_rights':'PROCESS_VM_READ|PROCESS_QUERY_LIMITED_INFORMATION','owner':owner,'window':hwnd,'events':events,'samples':samples},indent=2)+'\n');print(out,flush=True)
