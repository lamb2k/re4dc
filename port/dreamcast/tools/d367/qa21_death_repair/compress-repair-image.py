from pathlib import Path
import ctypes,hashlib,json,subprocess,time,shutil
R=Path('C:/Flycast-Evidence/re4-dreamcast/qa21-death-repair-runtime-20261021');p=R/'trace-input/gdemu/track03.iso';out=R/'OWNED-REPAIR-STAGE-LZX-COMPRESSION-20261021.json';assert not out.exists();k=ctypes.WinDLL('kernel32',use_last_error=True);k.GetCompressedFileSizeW.argtypes=[ctypes.c_wchar_p,ctypes.POINTER(ctypes.c_ulong)];k.GetCompressedFileSizeW.restype=ctypes.c_ulong;k.CreateFileW.argtypes=[ctypes.c_wchar_p,ctypes.c_ulong,ctypes.c_ulong,ctypes.c_void_p,ctypes.c_ulong,ctypes.c_ulong,ctypes.c_void_p];k.CreateFileW.restype=ctypes.c_void_p;k.CloseHandle.argtypes=[ctypes.c_void_p]
h=k.CreateFileW(str(p),0x80000000,0,None,3,0,None);assert h not in (None,ctypes.c_void_p(-1).value),'Skip: target still has reader/owner handle';k.CloseHandle(h)
def allocated():
 high=ctypes.c_ulong();ctypes.set_last_error(0);low=k.GetCompressedFileSizeW(str(p),ctypes.byref(high));assert low!=0xffffffff or ctypes.get_last_error()==0;return high.value<<32|low
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def info():
 s=p.stat();return {'logical_bytes':s.st_size,'allocated_bytes':allocated(),'sha256':sha(p),'file_id':[s.st_dev,s.st_ino],'links':s.st_nlink,'attributes':s.st_file_attributes,'C_free_bytes':shutil.disk_usage('C:/').free}
before=info();assert before['sha256']=='3c216e5ae8e8c9716906eace0ac98bc1b0712c8540f053359438d32ba77a9238';assert before['allocated_bytes']>=before['logical_bytes'],'Skip: already compressed';assert before['C_free_bytes']>=18*1024**3+640*1024**2
keep={str(q.relative_to(R)):sha(q) for q in R.rglob('*KEEP*') if q.is_file()};started=time.monotonic();log=R/'compact-owned-repair.log';guard=None
with log.open('xb') as stream:
 proc=subprocess.Popen(['compact.exe','/C','/F','/EXE:LZX','/I','/Q',str(p)],stdout=stream,stderr=subprocess.STDOUT)
 try:
  while proc.poll() is None:
   if shutil.disk_usage('C:/').free<18*1024**3+64*1024**2:guard='Runtime C floor'
   elif time.monotonic()-started>120:guard='120s own compact bound'
   elif log.stat().st_size>64000:guard='64KB own compact log bound'
   if guard:proc.terminate();break
   time.sleep(.1)
  rc=proc.wait(timeout=8)
 finally:
  if proc.poll() is None:proc.kill();proc.wait()
after=info();assert after['sha256']==before['sha256'] and after['logical_bytes']==before['logical_bytes'] and after['file_id']==before['file_id'] and after['links']==before['links'];assert keep=={str(q.relative_to(R)):sha(q) for q in R.rglob('*KEEP*') if q.is_file()}
receipt={'scope':'Idle owned repair image transparent NTFS LZX compression only; exclusive-handle admission; no guest or logical/source fixture change','path':str(p),'before':before,'after':after,'allocated_recovered_bytes':before['allocated_bytes']-after['allocated_bytes'],'actual_C_free_delta':after['C_free_bytes']-before['C_free_bytes'],'compact_exit':rc,'guard':guard,'seconds':time.monotonic()-started,'keep_hashes':keep,'host_throughput_comparison':'No throughput comparison across this compression boundary'};out.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
