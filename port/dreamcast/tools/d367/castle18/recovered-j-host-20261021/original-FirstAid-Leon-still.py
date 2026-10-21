from pathlib import Path
import ctypes as C,ctypes.wintypes as W,json,time,sys,re,struct,math
cap=Path(sys.argv[1]).resolve();root=Path(r'C:\Flycast-Evidence\re4-dreamcast\castle18-20261018').resolve();assert cap.is_relative_to(root)and cap.parent.name=='recovered-j-content-20261021'and re.fullmatch(r'route-walk[0-9]+',cap.name);expected=int(sys.argv[4],16)if len(sys.argv)>4 else 0x200;assert expected in [0x200,0x202,0x207,0x203,0x201,0x208,0x204];targets=[tuple(float(v)for v in t.split(','))for t in sys.argv[2].split(';')];assert 1<=len(targets)<=12 and all(len(t)==2 and all(abs(v)<100000 for v in t)for t in targets);target_i=0;target=targets[0];tolerance=float(sys.argv[3])if len(sys.argv)>3 else 300;assert 30<=tolerance<=300;out=cap/'owned-window-current-stair-walk.json';assert not out.exists()
k=C.WinDLL('kernel32',use_last_error=True);u=C.WinDLL('user32',use_last_error=True);k.OpenProcess.argtypes=[W.DWORD,W.BOOL,W.DWORD];k.OpenProcess.restype=W.HANDLE;k.QueryFullProcessImageNameW.argtypes=[W.HANDLE,W.DWORD,W.LPWSTR,C.POINTER(W.DWORD)];k.GetProcessTimes.argtypes=[W.HANDLE,C.POINTER(W.FILETIME),C.POINTER(W.FILETIME),C.POINTER(W.FILETIME),C.POINTER(W.FILETIME)];k.ReadProcessMemory.argtypes=[W.HANDLE,C.c_void_p,C.c_void_p,C.c_size_t,C.POINTER(C.c_size_t)];k.ReadProcessMemory.restype=W.BOOL;k.CloseHandle.argtypes=[W.HANDLE];u.GetWindowThreadProcessId.argtypes=[W.HWND,C.POINTER(W.DWORD)];u.GetClassNameW.argtypes=[W.HWND,W.LPWSTR,C.c_int];u.IsWindow.argtypes=[W.HWND];u.IsWindow.restype=W.BOOL;u.PostMessageW.argtypes=[W.HWND,W.UINT,W.WPARAM,W.LPARAM];u.PostMessageW.restype=W.BOOL;u.MapVirtualKeyW.argtypes=[W.UINT,W.UINT];u.MapVirtualKeyW.restype=W.UINT;CALL=C.WINFUNCTYPE(W.BOOL,W.HWND,W.LPARAM);u.EnumWindows.argtypes=[CALL,W.LPARAM]
owner=None;h=None;hwnd=None;active=set();events=[];samples=[];deadline=time.monotonic()+180;mapkeys={'forward':(ord('I'),0x17),'left':(ord('J'),0x24),'right':(ord('L'),0x26),'dash':(ord('C'),0x2e),'ready':(ord('V'),0x2f),'fire':(ord('X'),0x2d),'knife':(ord('F'),0x21),'inventory':(ord('D'),0x20),'menu_left':(0x25,0x4b,1),'menu_right':(0x27,0x4d,1),'menu_up':(0x26,0x48,1),'menu_down':(0x28,0x50,1)}
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
 assert u.EnumWindows(enum,0)and len(found)==1,('owned window lookup failed',found);hwnd=found[0];base=None
 while base is None:
  text=(cap/'flycast.log').read_text(errors='replace');m=re.findall(r'RAM\(16 MB\)\s+([0-9a-fA-F]+)',text)
  if m:base=int(m[-1],16)
  else:assert time.monotonic()<deadline;time.sleep(.2)
 # Wait for exact owned snapshot load completion before reads/input.
 while True:
  log=(cap/'flycast.log').read_text(errors='replace');loaded=re.findall(r'Loaded state ver \d+ from (.*?) size \d+',log)
  if loaded and Path(loaded[-1]).resolve()==(cap/'data/disc.state').resolve():events.append({'exact_owned_snapshot_loaded_before_input':loaded[-1]});break
  assert time.monotonic()<deadline;check();time.sleep(.02)
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
  check();assert u.IsWindow(hwnd);pid=W.DWORD();u.GetWindowThreadProcessId(hwnd,C.byref(pid));assert pid.value==owner['pid']
  for name in sorted(active-wanted):
   vk,scan=mapkeys[name][:2];ext=mapkeys[name][2]if len(mapkeys[name])>2 else 0;assert u.PostMessageW(hwnd,0x101,vk,1|(scan<<16)|(ext<<24)|0xc0000000);active.remove(name);events.append({'key':name,'up':True,'host_monotonic':time.monotonic()})
  for name in sorted(wanted-active):
   vk,scan=mapkeys[name][:2];ext=mapkeys[name][2]if len(mapkeys[name])>2 else 0;assert u.MapVirtualKeyW(vk,0)==scan;assert u.PostMessageW(hwnd,0x100,vk,1|(scan<<16)|(ext<<24));active.add(name);events.append({'key':name,'down':True,'host_monotonic':time.monotonic()})

 def inventory():
  ip=u32(0x8c3a91f4+0x14);n=u32(0x8c3a91f4+0x1c);assert 1<=n<=512 and 0x8c000000<=ip and ip+n*14<0x8d000000
  items=[]
  for j in range(n):
   b=read(ip+j*14,14)
   if b[4]&1:items.append({'id':struct.unpack_from('<H',b,0)[0],'num':struct.unpack_from('<H',b,2)[0],'bullet':struct.unpack_from('<H',b,8)[0]&0x1fff,'raw':b.hex()})
  return items


 def pulse(name,ticks=2):
  before=u32(pg+0x51e4);transition({name});until=time.monotonic()+(1.5 if name=="inventory" else .25)
  while u32(pg+0x51e4)<before+ticks and time.monotonic()<until:time.sleep(.01)
  transition(set());time.sleep(.18)
 started=time.monotonic();opened=False;selected=False;initial=None;healed=False
 while time.monotonic()-started<47:
  pg=u32(0x8c2e91dc);assert 0x8c000000<=pg<=0x8cffa000;ff=u32(pg+0x51e4);room=struct.unpack('<H',read(pg+0x4f9e,2))[0];chapter=read(pg+0x4f8a,1)[0];life,maxlife,ash,maxash=struct.unpack('<4H',read(pg+0x4fa4,8));stop=u32(pg+0x170);phase=list(read(pg+0x20,2));assert room==0x207 and chapter==6 and life>0 and ash==330,('sourcehealth/roomunsafe',life,ash,hex(room));items=inventory();sprays=[i for i in items if i['id']==5];loop=read(0x8c3de064+0x28,1)[0];menu=read(0x8c3de064+0x264,1)[0];mode=read(0x8c3de064+0x267,1)[0];cmd=struct.unpack('<b',read(0x8c3de064+0x26c,1))[0];pp=u32(0x8c3de064+0x2b0);row={'frame':ff,'life':life,'maxlife':maxlife,'Ashley':ash,'phase':phase,'Stop':hex(stop),'Loop':loop,'menu_no':menu,'cursor_mode':mode,'cmd_cursor':cmd,'items':items};samples.append(row)
  assert life>=725,'Stop on further original Leon damage'
  if initial is None:initial={'life':life,'spray_count':sum(i['num']for i in sprays)};assert initial['spray_count']==1 and 0<life<maxlife
  if life==maxlife and not sprays:healed=True
  if healed:
   transition(set())
   if loop==0 and stop==0 and phase==[3,0] and not(u32(pg+0x5010)&0x10000000):events.append({'original_firstaid_used_and_normal_inventory_return':{'frame':ff,'life':life,'Ashley':ash,'initial':initial}});capture_before_close();assert u.PostMessageW(hwnd,0x10,0,0);break
   pulse('dash');continue
  assert sprays,'source spray disappeared without full heal'
  if loop==0:
   if stop or phase!=[3,0]or(u32(pg+0x5010)&0x10000000):transition(set());time.sleep(.05);continue
   pl=u32(0x8c39d700);assert 0x8c000000<=pl<0x8cfff000
   routine=list(read(pl+0xfc,4));allowed=routine[0]==0 and ((routine[1]==6 and routine[2] not in [2,4,5]) or (routine[1]==15 and routine[2] in [2,10]) or (routine[1]!=6 and routine[1]!=15 and (routine[1]<=4 or routine[1]==17)))
   if not allowed:row['waiting_original_subScrCheck']=routine;time.sleep(.02);continue
   pulse('inventory');events.append({'normal_inventory_Y_pulse':ff});continue
  if menu not in [1,4] or not(0x8c000000<=pp<0x8cfff000):transition(set());time.sleep(.1);continue
  cur=u32(pp+0x30);board=u32(pp)
  if cur==0 and board==0:transition(set());row['original_puzzle_loading']=True;time.sleep(.1);continue
  assert cur==board and 0x8c000000<=board<0x8cfff000,('unexpected source board',hex(cur),hex(board));inhand=u32(pp+0x10);assert not inhand,'refuse item move/discard state';pieces=u32(pp+8);n=read(pp+0xc,1)[0];assert 0<n<=128 and 0x8c000000<=pieces and pieces+n*0x2c<0x8d000000;matches=[]
  for j in range(n):
   b=read(pieces+j*0x2c,0x2c)
   if not(b[0]&1):continue
   ip=struct.unpack_from('<I',b,0x24)[0]
   if ip and struct.unpack('<H',read(ip,2))[0]==5:matches.append({'piece':hex(pieces+j*0x2c),'item':hex(ip),'pos':struct.unpack_from('<2f',b,0x14)})
  assert len(matches)==1,('source firstaid piece ambiguity',matches);piece=matches[0];tx,ty=[math.floor(v)for v in piece['pos']];cx,cy=struct.unpack('<bb',read(cur+0x3c,2));w,hgt=struct.unpack('<bb',read(cur+4,2));assert 0<=tx<w and 0<=ty<hgt;row.update(cursor=[cx,cy],target=[tx,ty],spray_piece=piece)
  if selected:
   assert cx==tx and cy==ty and cmd==0,'refuse changed selection or non-Use command';pulse('fire');events.append({'normal_firstaid_Use_or_default_Leon_A':ff});continue
  if cx!=tx:pulse('menu_right'if tx>cx else'menu_left',1);continue
  if cy!=ty:pulse('menu_down'if ty>cy else'menu_up',1);continue
  selected=True;pulse('fire');events.append({'normal_firstaid_context_A':ff})
 transition(set())
except Exception as e:
 import traceback
 if h and hwnd:
  try:
   check();transition(set());capture_before_close();assert u.PostMessageW(hwnd,0x10,0,0);events.append({'owned_close_on_guard':True})
  except Exception as close_error:events.append({'guard_close_refused':repr(close_error)})
 events.append({'abort':repr(e),'traceback':traceback.format_exc()})
finally:
 if h and hwnd and active:
  try:transition(set())
  except Exception as e:events.append({'cleanup_refused':repr(e)})
 if h:k.CloseHandle(h)
 out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps({'scope':'Original existing First Aid Spray item05 via normal inventory, cursor, Use and default Leon confirmation buttons. Read-only original puzzle/item/health feedback. No item/HP/state writes or global input.','memory_rights':'PROCESS_VM_READ|PROCESS_QUERY_LIMITED_INFORMATION','owner':owner,'window':hwnd,'events':events,'samples':samples},indent=2)+'\n');print(out,flush=True)
