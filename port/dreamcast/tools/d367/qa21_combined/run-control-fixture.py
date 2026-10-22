from pathlib import Path
import argparse,ctypes,hashlib,json,os,shutil,subprocess,sys,time
def stop_reason(elapsed, free):
    if elapsed >= 47.5:
        return 'absolute owned guest wall-time cap'
    if free < 18*1024**3+64*1024**2:
        return 'C18GiB+64MiB runtime floor'
    return None
p=argparse.ArgumentParser();p.add_argument('name');p.add_argument('--keys',type=Path,required=True);p.add_argument('--seed');a=p.parse_args()
assert a.name.replace('-','').replace('_','').isalnum()
R=Path('C:/Flycast-Evidence/re4-dreamcast/qa21-combined-regression-20261021');D=R/'dependencies';assert shutil.disk_usage('C:/').free>18*1024**3+128*1024**2
binding=R/'control-binding.json';r=json.loads(binding.read_text());syms=' '.join(hex(int(r['symbols'][x],0)-0x8c000000) for x in ('logbuf','head','stage'))
runner=D/'checkpoint_runner18.py'
cmd=[sys.executable,str(D/'run_observed_v3.py'),'--runner',str(runner),'--runner-sha256',hashlib.sha256(runner.read_bytes()).hexdigest(),'--disc',r['disc_path'],'--cap',str(R/a.name),'--keys',str(a.keys),'--syms',syms,'--name','qa21-combined-'+a.name,'--binding',str(binding),'--layout',str(R/'builds/qa-control/dwarf-layout.json'),'--event-shots','--seconds','41','--no-limit','--save-checkpoint','--elf',str(R/'builds/qa-control/re4dc-game.elf')]
if a.seed:cmd+=['--checkpoint-seed',str(R/a.seed)]
assert not (R/a.name).exists();I=R/'invocations'/a.name;I.mkdir(parents=True,exist_ok=False)
shutil.copy2(__file__,I/'run-fixture.py');shutil.copy2(a.keys,I/'keys.txt')
(I/'invocation.json').write_text(json.dumps({'argv':cmd,'free_c':shutil.disk_usage('C:/').free,'source':r['source_candidate'],'program':r['disc_program_sha256'],'elf':r['elf_sha256'],'tools':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in D.glob('*.py')}},indent=2)+'\n')
k=ctypes.WinDLL('kernel32',use_last_error=True)
k.OpenProcess.argtypes=[ctypes.c_ulong,ctypes.c_int,ctypes.c_ulong];k.OpenProcess.restype=ctypes.c_void_p
k.QueryFullProcessImageNameW.argtypes=[ctypes.c_void_p,ctypes.c_ulong,ctypes.c_wchar_p,ctypes.POINTER(ctypes.c_ulong)]
k.GetProcessTimes.argtypes=[ctypes.c_void_p]+[ctypes.POINTER(ctypes.c_ulonglong)]*4
k.GetExitCodeProcess.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_ulong)]
k.TerminateProcess.argtypes=[ctypes.c_void_p,ctypes.c_uint]
k.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_ulong];k.WaitForSingleObject.restype=ctypes.c_ulong
k.CloseHandle.argtypes=[ctypes.c_void_p]
child=subprocess.Popen(cmd);handle=None;receipt={'absolute_guest_limit_s':47.5,'inner_requested_s':41,'scope':'Independent PID, executable and process-start verified outer guest supervisor'}
while True:
 if handle is None:
  try: value=(R/a.name/'flycast.pid').read_text().strip()
  except FileNotFoundError: value=''
  if value.isdigit():
   pid=int(value);candidate=k.OpenProcess(0x101001,False,pid)
   if candidate:
    path=ctypes.create_unicode_buffer(32768);size=ctypes.c_ulong(len(path))
    assert k.QueryFullProcessImageNameW(candidate,0,path,ctypes.byref(size))
    assert os.path.normcase(os.path.abspath(path.value))==os.path.normcase(str((R/a.name/'flycast.exe').resolve()))
    times=[ctypes.c_ulonglong() for _ in range(4)];assert k.GetProcessTimes(candidate,*[ctypes.byref(x) for x in times])
    start=times[0].value;handle=candidate;receipt.update(pid=pid,executable=path.value,start_filetime=start)
 if handle:
  code=ctypes.c_ulong();assert k.GetExitCodeProcess(handle,ctypes.byref(code))
  times=[ctypes.c_ulonglong() for _ in range(4)];assert k.GetProcessTimes(handle,*[ctypes.byref(x) for x in times])
  if code.value!=259:
   # ExitCode can be published before the kernel has finalized exit timestamps.
   if k.WaitForSingleObject(handle,0)!=0:
    time.sleep(0.05);continue
   assert k.GetProcessTimes(handle,*[ctypes.byref(x) for x in times])
   assert times[0].value==start and times[1].value>=start and times[1].value!=0
   receipt.update(exit_code=code.value,exit_filetime=times[1].value,actual_guest_seconds=(times[1].value-start)/1e7)
   k.CloseHandle(handle);handle=None;break
  elapsed=time.time()-(start/1e7-11644473600)
  reason=stop_reason(elapsed,shutil.disk_usage('C:/').free)
  if reason and not receipt.get('forced_stop'):
   assert times[0].value==start;assert k.TerminateProcess(handle,125)
   receipt.update(forced_stop=reason,stop_at_s=elapsed,checkpoint_usable=False)
 if child.poll() is not None and handle is None:break
 time.sleep(0.1)
rc=child.wait();receipt['launcher_exit']=rc
(I/'process-supervisor.json').write_text(json.dumps(receipt,indent=2)+'\n')
(I/'exit.json').write_text(json.dumps({'exit':rc})+'\n');raise SystemExit(rc)