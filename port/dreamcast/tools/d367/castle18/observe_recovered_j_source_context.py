from pathlib import Path
import ctypes,json,re,struct,sys,time,hashlib
from ctypes import wintypes as W
cap=Path(sys.argv[1]);deadline=time.monotonic()+65
k=ctypes.WinDLL('kernel32',use_last_error=True);k.OpenProcess.argtypes=[W.DWORD,W.BOOL,W.DWORD];k.OpenProcess.restype=W.HANDLE;k.ReadProcessMemory.argtypes=[W.HANDLE,W.LPCVOID,W.LPVOID,ctypes.c_size_t,ctypes.POINTER(ctypes.c_size_t)];k.QueryFullProcessImageNameW.argtypes=[W.HANDLE,W.DWORD,W.LPWSTR,ctypes.POINTER(W.DWORD)];k.GetProcessTimes.argtypes=[W.HANDLE]+[ctypes.POINTER(W.FILETIME)]*4;k.CloseHandle.argtypes=[W.HANDLE]
while time.monotonic()<deadline:
 if(cap/'owned-process.json').exists()and(cap/'flycast.log').exists():
  matches=re.findall(r'RAM\(16 MB\)\s+([0-9A-Fa-f]+)',(cap/'flycast.log').read_text(errors='replace'))
  if matches:break
 time.sleep(.05)
else:raise SystemExit('No owned process RAM')
owner=json.loads((cap/'owned-process.json').read_text());h=k.OpenProcess(0x10|0x1000,False,owner['pid']);assert h
assert json.loads((cap/'run-start.json').read_text())['elf_sha256']=='4d823b496b9a402baadabe7f679c089fa0fd55c7ffd175ec634915745a11487f'
def check():
 path=ctypes.create_unicode_buffer(32768);n=W.DWORD(len(path));assert k.QueryFullProcessImageNameW(h,0,path,ctypes.byref(n));assert Path(path.value).resolve()==Path(owner['path']).resolve()==cap/'flycast.exe'
 a,b,c,d=(W.FILETIME()for _ in range(4));assert k.GetProcessTimes(h,ctypes.byref(a),ctypes.byref(b),ctypes.byref(c),ctypes.byref(d));assert(a.dwHighDateTime<<32|a.dwLowDateTime)==owner['start_filetime']
check();ram=int(matches[-1],16)
def read(a,n):
 if not(0x8c000000<=a and a+n<=0x8d000000):raise EOFError()
 b=ctypes.create_string_buffer(n);got=ctypes.c_size_t()
 if not k.ReadProcessMemory(h,ram+a-0x8c000000,b,n,ctypes.byref(got))or got.value!=n:raise EOFError()
 return b.raw
u32=lambda a:struct.unpack('<I',read(a,4))[0]
def sample():
 pg=u32(0x8c2e91dc)
 if not 0x8c000000<=pg<=0x8cffa000:return None
 return dict(utc_ns=time.time_ns(),frame=u32(pg+0x51e4),room=hex(struct.unpack('<H',read(pg+0x4f9e,2))[0]),chapter=read(pg+0x4f8a,1)[0],phase=list(read(pg+0x20,2)),Stop=hex(u32(pg+0x170)),SSLoop=read(0x8c3de064+0x28,1)[0],health=list(struct.unpack('<4H',read(pg+0x4fa4,8))))
pending={};done=set();lastwrite=0;last=None
with(cap/'readonly-source-context.jsonl').open('x')as out:
 try:
  while time.monotonic()<deadline and not(cap/'run-result.json').exists():
   row=sample()
   if row:
    last=row
    if time.monotonic()-lastwrite>.1:out.write(json.dumps(row)+'\n');out.flush();lastwrite=time.monotonic()
   for shot in (cap/'shots').glob('*'):
    if not shot.is_dir()or str(shot)in done:continue
    if str(shot)not in pending:pending[str(shot)]=last
    pngs=list((shot/'frames').glob('*.png'))
    if pngs and row:
     check();before=pending[str(shot)]or row;context=dict(run=cap.name,lineage='recovered-J-content new cold boot',runtime='12a841d7c',elf_sha256='4d823b496b9a402baadabe7f679c089fa0fd55c7ffd175ec634915745a11487f',iso_sha256='b67ac21eff8d819ef9ca5f0997b4c16401cb98a3d304feb65aa4b90f7affbeb6',source_frame_interval=[before['frame'],row['frame']],before=before,after=row,action_result='Normal Title/CardLoad cold boot; screenshot context only, no progression claim from partial menu',method='Read-only globals sampled around existing owned-harness screenshot directory/PNG creation; asynchronous interval includes capture',pngs=[str(p)for p in pngs]);(shot/'checkpoint-context.json').write_text(json.dumps(context,indent=2)+'\n');done.add(str(shot))
   time.sleep(.01)
 except(EOFError,AssertionError,struct.error,OSError):pass
 finally:k.CloseHandle(h)