from pathlib import Path
import ctypes as C,ctypes.wintypes as W,json,time,re,struct,sys,hashlib,importlib.util,shutil,traceback
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18');D=Path(r'C:\Flycast-Evidence\re4-dreamcast\castle18-20261018\Test21\recovered-j-content-20261021');cap=Path(sys.argv[1]).resolve();assert cap==D/'route-walk-controlled-event008';events=[];rows=[];h=None;owner=None;baseline_y=None;baseline_clear=False;observed_held=False;last=None;first_frame=None;closed_sent=False;wave_seen=set();secondary_seen=set();seen16=False;entered208=None;crank_full=None;entered204=None;baseline_crank=None
spec=importlib.util.spec_from_file_location('controlled_fast_capture',L/'capture-original-J-fast-RGB565.py');fc=importlib.util.module_from_spec(spec);spec.loader.exec_module(fc)
k=C.WinDLL('kernel32',use_last_error=True);u=C.WinDLL('user32',use_last_error=True);k.OpenProcess.argtypes=[W.DWORD,W.BOOL,W.DWORD];k.OpenProcess.restype=W.HANDLE;k.GetProcessTimes.argtypes=[W.HANDLE]+[C.POINTER(W.FILETIME)]*4;k.QueryFullProcessImageNameW.argtypes=[W.HANDLE,W.DWORD,W.LPWSTR,C.POINTER(W.DWORD)];k.ReadProcessMemory.argtypes=[W.HANDLE,C.c_void_p,C.c_void_p,C.c_size_t,C.POINTER(C.c_size_t)];k.WaitForSingleObject.argtypes=[W.HANDLE,W.DWORD];k.CloseHandle.argtypes=[W.HANDLE];u.GetWindowThreadProcessId.argtypes=[W.HWND,C.POINTER(W.DWORD)];u.GetClassNameW.argtypes=[W.HWND,W.LPWSTR,C.c_int];u.PostMessageW.argtypes=[W.HWND,W.UINT,W.WPARAM,W.LPARAM];CALL=C.WINFUNCTYPE(W.BOOL,W.HWND,W.LPARAM);u.EnumWindows.argtypes=[CALL,W.LPARAM]
(D/(cap.name+'-observer-ready.json')).write_text(json.dumps(dict(scope='CONTROLLED EVENT COVERAGE, read-only observer/no input',observer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))+'\n')
def check():
 assert k.WaitForSingleObject(h,0)==258,'Owned process exited';b=C.create_unicode_buffer(32768);n=W.DWORD(32768);assert k.QueryFullProcessImageNameW(h,0,b,C.byref(n));assert Path(b.value).resolve()==cap/'flycast.exe';a,b,c,d=(W.FILETIME()for _ in range(4));assert k.GetProcessTimes(h,C.byref(a),C.byref(b),C.byref(c),C.byref(d));assert a.dwLowDateTime+(a.dwHighDateTime<<32)==owner['start_filetime']
def read(a,n):
 assert 0x8c000000<=a and a+n<=0x8d000000;buf=C.create_string_buffer(n);got=C.c_size_t();assert k.ReadProcessMemory(h,ram+a-0x8c000000,buf,n,C.byref(got))and got.value==n;return buf.raw
u32=lambda a:struct.unpack('<I',read(a,4))[0]
def pulse_action():
 check();assert age()<35,'Action admission margin';wins=[]
 @CALL
 def cb(w,_):
  p=W.DWORD();u.GetWindowThreadProcessId(w,C.byref(p));b=C.create_unicode_buffer(256);u.GetClassNameW(w,b,256)
  if p.value==owner['pid']and b.value=='SDL_app':wins.append(int(w))
  return True
 assert u.EnumWindows(cb,0)and len(wins)==1;hwnd=wins[0];held=False;ack=[]
 try:
  check();assert u.PostMessageW(hwnd,0x100,ord('X'),1|(0x2d<<16));held=True;until=time.monotonic()+.2
  while time.monotonic()<until:
   check();assert age()<40.5;ack.append(dict(frame=u32(u32(0x8c2e91dc)+0x51e4),Key_trg=hex(u32(0x8c3a948c+24))));time.sleep(.02)
 finally:
  if held:
   check();p=W.DWORD();u.GetWindowThreadProcessId(hwnd,C.byref(p));assert p.value==owner['pid'];assert u.PostMessageW(hwnd,0x101,ord('X'),1|(0x2d<<16)|0xc0000000)
 events.append(dict(ordinary_A_X_pulse_seconds=.2,source_Key_trg_samples=ack,release_before_age=age()))

def close():
 global closed_sent
 if closed_sent:return
 check();wins=[]
 @CALL
 def cb(w,_):
  p=W.DWORD();u.GetWindowThreadProcessId(w,C.byref(p));b=C.create_unicode_buffer(256);u.GetClassNameW(w,b,256)
  if p.value==owner['pid']and b.value=='SDL_app':wins.append(int(w))
  return True
 assert u.EnumWindows(cb,0)and len(wins)==1;assert u.PostMessageW(wins[0],0x10,0,0);closed_sent=True;events.append(dict(exact_owned_WM_CLOSE=True))
def capture(label,row):
 check();assert shutil.disk_usage(D).free>=18*1024**3+64*1024**2;fb=re.findall(r'fb=[0-9a-f]+,[0-9a-f]+',(cap/'run-output.txt').read_text(errors='replace'));fb_source='current native log'
 if not fb:
  # FrozenELF pvr_get_front/back disassembly: _pvr_state8c483e00, two framebuffer structs312/320.
  # StandardDC conversion proven against closed005 native log and closed006 state; exact inherited buffers required.
  pair=(u32(0x8c483e00+312),u32(0x8c483e00+320));assert pair==(u32(0x8c483e00+312),u32(0x8c483e00+320)), 'Unstable framebuffer pair'
  assert pair==(0x230980,0x630980),'Inherited framebuffer identity changed'
  ptrs=[((0xd2800000+(v&0x7fffff))*2)&0xffffffff for v in pair]
  for ptr in ptrs:fc.framebuffer_offset(ptr)
  fb=['fb=%x,%x'%tuple(ptrs)];fb_source='current live frozenELF pvr_state+312/320, checked inherited005/006 buffers';events.append(dict(framebuffer_readonly_fallback=dict(source=fb_source,native=[hex(v)for v in pair],rgb565=[hex(v)for v in ptrs])))
 p=cap/'shots'/('controlled-'+label);p.mkdir(parents=True,exist_ok=False)
 for name in ['emu.cfg','flycast.log','flycast.pid']:shutil.copyfile(cap/name,p/name)
 (p/'boot.log').write_text(fb[-1]+'\n',encoding='utf-16');before=u32(row['pg']+0x51e4);fc.capture(p,p/'frames');after=u32(row['pg']+0x51e4);(p/'controlled-context.json').write_text(json.dumps(dict(scope='CONTROLLED teleport/scripted-event coverage; not authentic combat or hardware acceptance',source_frame_interval=[before,after],framebuffer_source=fb_source,observation=row,pngs=[dict(path=str(x),sha256=hashlib.sha256(x.read_bytes()).hexdigest())for x in(p/'frames').glob('*.png')]),indent=2)+'\n');events.append(dict(screenshot=str(p),source_interval=[before,after]))
try:
 until=time.monotonic()+70
 while not(cap/'owned-process.json').exists():assert time.monotonic()<until;time.sleep(.05)
 owner=json.loads((cap/'owned-process.json').read_text());h=k.OpenProcess(0x1000|0x10|0x100000,False,owner['pid']);assert h;check();age0=time.time()-(owner['start_filetime']/1e7-11644473600);mono0=time.monotonic();age=lambda:age0+time.monotonic()-mono0
 start=json.loads((cap/'run-start.json').read_text());assert start['elf_sha256']=='4d823b496b9a402baadabe7f679c089fa0fd55c7ffd175ec634915745a11487f'and start['disc_sha256']=='b67ac21eff8d819ef9ca5f0997b4c16401cb98a3d304feb65aa4b90f7affbeb6'
 while True:
  check();m=re.findall(r'RAM\(16 MB\)\s+([0-9a-fA-F]+)',(cap/'flycast.log').read_text(errors='replace'))
  if m:ram=int(m[-1],16);break
  if age()>38:close();raise TimeoutError('ColdRAM deadline')
  time.sleep(.05)
 out=cap/'controlled-events-observations.jsonl';movie_shot=False;chapter_seen=False;action_age=None;card_shot=False
 with out.open('x')as f:
  while k.WaitForSingleObject(h,0)==258 and age()<39:
   check();pg=u32(0x8c2e91dc)
   if not 0x8c000000<=pg<0x8cffa000:time.sleep(.03);continue
   room=struct.unpack('<H',read(pg+0x4f9e,2))[0]
   if room!=0x204:time.sleep(.03);continue
   row=dict(pg=pg,process_age=age(),frame=u32(pg+0x51e4),room=hex(room),phase=list(read(pg+0x20,2)),Stop=hex(u32(pg+0x170)),health=list(struct.unpack('<4H',read(pg+0x4fa4,8))),status1=hex(u32(pg+0x5010)),status3=hex(u32(pg+0x5018)),chapter=read(pg+0x4f8a,1)[0],partner_ptr=hex(u32(0x8c39d6fc)))
   pl=u32(0x8c39d700)
   if 0x8c000000<=pl<0x8cfff000:row['player_pos']=list(struct.unpack('<3f',read(pl+0x94,12)))
   rd=0x8c3b9314;nr=struct.unpack('<H',read(rd+2,2))[0];sv=u32(rd+0x18);rsf=None
   if 0<nr<256 and 0x8c000000<=sv and sv+nr*0xd8<=0x8d000000:
    tb=read(sv,nr*0xd8);rsf=next((struct.unpack_from('<I',tb,i*0xd8+4)[0]for i in range(nr)if tb[i*0xd8:i*0xd8+2]==b'\x02\x04'),None)
   row['saved_RSF']=hex(rsf)if rsf is not None else None
   row['CardStatus']=hex(u32(pg+8));row['message0']=dict(table_size=read(0x8c3b6938,1)[0],selection=read(0x8c3b6939,1)[0],current=read(0x8c3b693a,1)[0],button=read(0x8c3b684c+0x7c,1)[0],attribute=hex(u32(0x8c3b684c+0x8c)))
   if rsf is not None and not(rsf&0x80000000):baseline_clear=True
   if u32(pg+0x5010)&0x10000000:observed_held=True
   row.update(baseline_RSF0_clear_seen=baseline_clear,event_hold_seen=observed_held);last=row;rows.append(row);f.write(json.dumps(row)+'\n');f.flush()
   if not movie_shot and rsf is not None and rsf&0x80000000 and 2<age()<35:
    events.append(dict(original_event_RSF0_early=row))
    try:capture('original-r204-event-start',row)
    except Exception as e:events.append(dict(optional_initial_capture_unavailable=repr(e)))
    movie_shot=True
   m=row['message0']
   if action_age is None and 2<age()<30 and row['chapter']==7 and row['partner_ptr']=='0x0' and rsf is not None and rsf&0x80000000 and (m['table_size'],m['selection'],m['current'],m['button'],m['attribute'])==(2,0,0,1,'0x1001'):
    events.append(dict(actual_native_Save_Yes_prompt_before_A=row));pulse_action();action_age=age()
   if action_age is not None and not card_shot and age()>action_age+6 and age()<35:
    try:capture('original-chapter-CardSave-after-A',row)
    except Exception as e:events.append(dict(optional_CardSave_capture_unavailable=repr(e)))
    card_shot=True
   if not chapter_seen and row['chapter']!=6:
    events.append(dict(chapter_task_early_transition=row));chapter_seen=True
   time.sleep(.025)
 if k.WaitForSingleObject(h,0)==258 and not closed_sent:
  if last:
   try:capture('inner-deadline',last)
   except Exception as e:events.append(dict(deadline_capture_unavailable=repr(e)))
  close()
except Exception as e:
 events.append(dict(observer_error=repr(e),traceback=traceback.format_exc()))
 if h and k.WaitForSingleObject(h,0)==258:
  try:close()
  except Exception as x:events.append(dict(close_error=repr(x)))
finally:
 if h:k.CloseHandle(h)
 if cap.exists():(cap/'controlled-events-observer.json').write_text(json.dumps(dict(scope='CONTROLLED direct continuation of closed006 movie state. No rearm/outcome state edits. Exactly one ordinaryA pulse at coherent native SaveYes prompt; no later blind buttons. Original005 chapter6/partner/AEV2 setup inherited. Early RSF0/chapter7/RSF7 do not prove movieEOF/resultsUI/savewrite/radio. Authentic127/294 untouched.',owner=owner,baseline_crank=baseline_crank,crank_full_frame=crank_full,baseline_RSF5_clear_seen=baseline_clear,events=events,last=last),indent=2)+'\n')
