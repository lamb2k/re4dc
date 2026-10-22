from pathlib import Path
import ctypes,hashlib,json,subprocess,time,shutil
R=Path('C:/Flycast-Evidence/re4-dreamcast/qa21-death-repair-runtime-20261021');cases=('repair-cold-r10301','repair-return-door01','repair-BB-only01','repair-continue01','repair-gameplay01','repair-continue-play02');k=ctypes.WinDLL('kernel32',use_last_error=True);k.GetCompressedFileSizeW.argtypes=[ctypes.c_wchar_p,ctypes.POINTER(ctypes.c_ulong)];k.GetCompressedFileSizeW.restype=ctypes.c_ulong;k.CreateFileW.argtypes=[ctypes.c_wchar_p,ctypes.c_ulong,ctypes.c_ulong,ctypes.c_void_p,ctypes.c_ulong,ctypes.c_ulong,ctypes.c_void_p];k.CreateFileW.restype=ctypes.c_void_p;k.CloseHandle.argtypes=[ctypes.c_void_p]
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def info(p):
 st=p.stat();hi=ctypes.c_ulong();ctypes.set_last_error(0);lo=k.GetCompressedFileSizeW(str(p),ctypes.byref(hi));assert lo!=0xffffffff or ctypes.get_last_error()==0;return {'sha256':sha(p),'logical_bytes':st.st_size,'allocated_bytes':(hi.value<<32)|lo,'file_id':[st.st_dev,st.st_ino],'links':st.st_nlink}
keep={str(p.relative_to(R)):sha(p) for p in R.rglob('*KEEP*') if p.is_file()};states={str(R/c/'data/disc.state'):sha(R/c/'data/disc.state') for c in cases};free_before=shutil.disk_usage('C:/').free;rows=[]
for case in cases:
 p=R/case/'flycast.exe';before=info(p);expected=json.loads((R/case/'checkpoint.json').read_text())['emulator_sha256'];assert before['sha256']==expected
 if before['allocated_bytes']<before['logical_bytes']:rows.append({'path':str(p),'status':'SKIPPED_ALREADY_COMPRESSED','before':before});continue
 h=k.CreateFileW(str(p),0x80000000,0,None,3,0,None)
 if h in (None,ctypes.c_void_p(-1).value):rows.append({'path':str(p),'status':'SKIPPED_OPEN_HANDLE','before':before});continue
 k.CloseHandle(h);assert shutil.disk_usage('C:/').free>=18*1024**3+640*1024**2;started=time.monotonic();log=R/(case+'-exe-compact.log');guard=None
 with log.open('xb') as stream:
  proc=subprocess.Popen(['compact.exe','/C','/F','/EXE:LZX','/I','/Q',str(p)],stdout=stream,stderr=subprocess.STDOUT)
  try:
   while proc.poll() is None:
    if shutil.disk_usage('C:/').free<18*1024**3+64*1024**2:guard='Runtime floor'
    elif time.monotonic()-started>30:guard='30s compact cap'
    elif log.stat().st_size>64000:guard='64KB log cap'
    if guard:proc.terminate();break
    time.sleep(.05)
   rc=proc.wait(timeout=5)
  finally:
   if proc.poll() is None:proc.kill();proc.wait()
 after=info(p);assert all(before[n]==after[n] for n in ('sha256','logical_bytes','file_id','links'));rows.append({'path':str(p),'status':'COMPRESSED' if rc==0 and not guard else 'STOPPED','before':before,'after':after,'guard':guard,'returncode':rc,'seconds':time.monotonic()-started})
assert states=={p:sha(Path(p)) for p in states};assert keep=={str(p.relative_to(R)):sha(p) for p in R.rglob('*KEEP*') if p.is_file()};free_after=shutil.disk_usage('C:/').free;row={'scope':'Exact closed owned runtime executable copies only; no source,image,state or gameplay changes','cases':rows,'allocated_recovered_bytes':sum(x['before']['allocated_bytes']-x.get('after',x['before'])['allocated_bytes'] for x in rows),'actual_C_before':free_before,'actual_C_after':free_after,'actual_C_delta':free_after-free_before,'KEEP_unchanged':True,'all6_state_hashes_unchanged':states,'no_further_guest_run_for_cleanup':True};out=R/'OWNED-IDLE-EXE-LZX-COMPRESSION-20261021.json';assert not out.exists();out.write_text(json.dumps(row,indent=2)+'\n');print(json.dumps({'compressed':sum(x['status']=='COMPRESSED' for x in rows),'allocated_recovered':row['allocated_recovered_bytes'],'C_before':free_before,'C_after':free_after,'actual_C_delta':free_after-free_before}))
