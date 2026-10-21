from pathlib import Path
import ctypes,json,math,sys,time,re,struct
from ctypes import wintypes as W
import fp_run_qa_sixfix as pad
from qa_owned_checkpoint import capture_checkpoint
cap=Path(sys.argv[1]);deadline=time.monotonic()+58
k=ctypes.WinDLL('kernel32',use_last_error=True)
k.OpenProcess.argtypes=[W.DWORD,W.BOOL,W.DWORD];k.OpenProcess.restype=W.HANDLE
k.QueryFullProcessImageNameW.argtypes=[W.HANDLE,W.DWORD,W.LPWSTR,ctypes.POINTER(W.DWORD)]
k.GetProcessTimes.argtypes=[W.HANDLE]+[ctypes.POINTER(W.FILETIME)]*4
while time.monotonic()<deadline:
    if (cap/'owned-process.json').exists() and (cap/'readonly-combat-io.jsonl').exists() and (cap/'run-start.json').exists():break
    time.sleep(.1)
else:raise SystemExit('No own observer')
resume=Path(sys.argv[2]);meta=json.loads((cap/'run-start.json').read_text());prior=json.loads((resume/'run-start.json').read_text())
assert Path(meta['seed']).resolve()==(resume/'data').resolve(), 'Only exact supplied predecessor state'
assert meta['elf_sha256']==prior['elf_sha256']=='52a5d671203e22e9f20728a8fbc3b61e080f7ba44e06891df635248a374dd053'
assert meta['disc_sha256']==prior['disc_sha256']==json.loads((cap.parent/'sixfix-master/master-receipt.json').read_text())['track03_sha256']
owner=json.loads((cap/'owned-process.json').read_text());h=k.OpenProcess(0x1010,False,owner['pid']);assert h
path=ctypes.create_unicode_buffer(32768);size=W.DWORD(len(path));assert k.QueryFullProcessImageNameW(h,0,path,ctypes.byref(size))
assert Path(path.value).resolve()==Path(owner['path']).resolve()
c,e,kt,ut=(W.FILETIME() for _ in range(4));assert k.GetProcessTimes(h,ctypes.byref(c),ctypes.byref(e),ctypes.byref(kt),ctypes.byref(ut))
assert (c.dwHighDateTime<<32|c.dwLowDateTime)==owner['start_filetime']

k.ReadProcessMemory.argtypes=[W.HANDLE,W.LPCVOID,W.LPVOID,ctypes.c_size_t,ctypes.POINTER(ctypes.c_size_t)]
ram=int(re.findall(r'RAM\(16 MB\)\s+([0-9a-fA-F]+)',(cap/'flycast.log').read_text(errors='replace'))[-1],16)
def read(a,n):
 assert 0x8c000000<=a and a+n<=0x8d000000
 b=ctypes.create_string_buffer(n);got=ctypes.c_size_t();assert k.ReadProcessMemory(h,ram+a-0x8c000000,b,n,ctypes.byref(got))and got.value==n;return b.raw
u32=lambda a:struct.unpack('<I',read(a,4))[0]
pg=0x8c361c18;ss=0x8c395c84;im=0x8c360ef0
assert [z['address']for z in json.loads((cap.parent/'sixfix-elf-scoped-symbols.json').read_text())['symbols']if z['name']=='_SubScreenWk']==[ss]
assert [z['address']for z in json.loads((cap.parent/'sixfix-elf-scoped-symbols.json').read_text())['symbols']if z['name']=='_ItemMgr']==[im]
deadline=time.monotonic()+44
out=(cap/'normal-inventory-controls.jsonl').open('x')
def write(z):out.write(json.dumps(z)+'\n');out.flush()
def stop(reason):
 tmp=cap/'owned-stop-request.tmp';tmp.write_text(json.dumps(dict(pid=owner['pid'],start_filetime=owner['start_filetime'],reason=reason))+'\n');tmp.replace(cap/'owned-stop-request.json')
def latest():return json.loads((cap/'readonly-combat-io.jsonl').read_text().splitlines()[-1])
def pulse(key):
 f=u32(pg+0x51e4);windows=pad.press(owner['pid'],[key],.14);time.sleep(.12);write(dict(key=key,frame_before=f,frame_after=u32(pg+0x51e4),windows=windows))
def wait_world():
 quiet=time.monotonic();last=None
 while time.monotonic()<deadline:
  try:z=latest()
  except (IndexError,json.JSONDecodeError):time.sleep(.05);continue
  if z['disc']['reads']!=last:last=z['disc']['reads'];quiet=time.monotonic()
  if read(ss+0x28,1)[0]==0 and 'player_pos'in z and z['stop']=='0x0'and z['hand']['job_state']==0 and all(v<0 for v in z['hand']['want'])and time.monotonic()-quiet>.3:return z
  time.sleep(.04)
 raise TimeoutError('Original world return/hand settle')
try:
 initial=wait_world();assert initial['health'][0]>=1000
 write(dict(checkpoint=capture_checkpoint(cap,'inventory-entry','Direct HG/TMP inventory Equip control','Same six-fix source, original safe pre-s03 world'),before=initial))
 for step,(item,wep)in enumerate([(0x30,11),(0x23,2),(0x30,11),(0x23,2)]):
  before=wait_world();assert before['health'][0]>=1000
  pulse('y');open_frame=u32(pg+0x51e4);equipped=False;selected=False;opened=False
  while time.monotonic()<deadline:
   loop=read(ss+0x28,1)[0];menu=read(ss+0x264,1)[0];mode=read(ss+0x267,1)[0];cmd=struct.unpack('<b',read(ss+0x26c,1))[0];pp=u32(ss+0x2b0);armed=struct.unpack('<H',read(im+0x10,2))[0]
   row=dict(step=step,target_item=item,frame=u32(pg+0x51e4),loop=loop,menu=menu,mode=mode,cmd=cmd,armed=armed)
   if loop==0:
    if equipped:break
    time.sleep(.05);continue
   if menu not in [1,4] or u32(pg+0x51e4)<open_frame+30 or not(0x8c000000<=pp<0x8cfff000):time.sleep(.05);continue
   board=u32(pp);cur=u32(pp+0x30)
   if not board:time.sleep(.05);continue
   assert cur==board and not u32(pp+0x10),'Refuse alternate board or item movement'
   if armed==item:equipped=True;pulse('b');write(dict(row,normal_equipped_exit=True));continue
   pieces=u32(pp+8);n=read(pp+0xc,1)[0];assert 0<n<=128;matches=[]
   for j in range(n):
    b=read(pieces+j*0x2c,0x2c)
    if not(b[0]&1):continue
    ip=struct.unpack_from('<I',b,0x24)[0]
    if ip and struct.unpack('<H',read(ip,2))[0]==item:matches.append(b)
   assert len(matches)==1,('Actual source item piece ambiguity',item,matches)
   target=matches[0];assert target[0x20]==0,'Only source unrotated fixture pieces';shape=struct.unpack_from('<I',target,4)[0];sd=read(shape,0x4c);sw,sh=struct.unpack_from('<bb',sd);px,py=struct.unpack_from('<2f',target,0x14);ox,oy=struct.unpack_from('<2f',target,0xc);vx,vy=int(px-ox),int(py-oy);cells=[(vx+x,vy+y)for y in range(sh)for x in range(sw)if sd[0xc+x+y*sw]==ord('1')];cx,cy=struct.unpack('<bb',read(board+0x3c,2));w,hgt=struct.unpack('<bb',read(board+4,2));assert cells and all(0<=x<w and 0<=y<hgt for x,y in cells);tx,ty=min(cells,key=lambda xy:abs(xy[0]-cx)+abs(xy[1]-cy));write(dict(row,cursor=[cx,cy],target=[tx,ty],actual_target_cells=cells))
   if not opened and step==0:write(dict(checkpoint=capture_checkpoint(cap,'inventory-open','Original inventory open for TMP Equip','Read-only piece identity/cursor'),step=step));opened=True
   if selected:
    assert (cx,cy)in cells and cmd==0,'Refuse changed selection or non-Equip command';pulse('a');continue
   if cx!=tx:pulse('right'if tx>cx else'left');continue
   if cy!=ty:pulse('down'if ty>cy else'up');continue
   selected=True;pulse('a')
  else:raise TimeoutError('Normal inventory Equip did not finish')
  after=wait_world();assert after['weapon'][3]==wep,('Weapon mismatch',after['weapon'],wep)
  write(dict(step=step,item=item,before=before,after=after,disc_delta={key:after['disc'][key]-before['disc'][key]for key in ['reads','bytes','block_us']},hand_delta={key:after['hand'][key]-before['hand'][key]for key in ['reads','read_bytes','misses','async_reads','copies','yields']}))
  write(dict(step=step,checkpoint=capture_checkpoint(cap,'inventory-return-%02d'%step,'Original inventory Equip return','Actual source weapon verified, hand worker settled')))
 stop('NORMAL_INVENTORY_HG_TMP_COMPLETE')
except Exception as exc:
 import traceback
 write(dict(failure=repr(exc),traceback=traceback.format_exc()))
 try:write(dict(checkpoint=capture_checkpoint(cap,'inventory-failure','Inventory controller guard',repr(exc))))
 except Exception as shot:write(dict(screenshot_unavailable=repr(shot)))
 stop('NORMAL_INVENTORY_CONTROL_GUARD')
finally:out.close();k.CloseHandle(h)
