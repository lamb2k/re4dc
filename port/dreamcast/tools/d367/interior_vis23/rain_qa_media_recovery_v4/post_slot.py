"""Post-slot Windows observer. No guest without exact separately reviewed grant."""
from pathlib import Path
import ctypes,hashlib,json,os,re,shutil,subprocess,sys,threading,time
import common as c
import rain_record as rr

def observe(cap,output,offset,stop):
 k=ctypes.WinDLL('kernel32',use_last_error=True)
 k.OpenProcess.argtypes=[ctypes.c_ulong,ctypes.c_int,ctypes.c_ulong];k.OpenProcess.restype=ctypes.c_void_p
 k.ReadProcessMemory.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_size_t,ctypes.POINTER(ctypes.c_size_t)];k.ReadProcessMemory.restype=ctypes.c_int
 k.CloseHandle.argtypes=[ctypes.c_void_p];k.CloseHandle.restype=ctypes.c_int
 handle=None;pid=None;ram=None;start=time.monotonic();written=0
 with output.open('x') as log:
  def emit(x):
   nonlocal written
   line=json.dumps(x)+'\n';written+=len(line.encode());c.need(written<=4*1024**2,'observer4MiB cap');log.write(line);log.flush()
  try:
   while not stop.wait(.1):
    if time.monotonic()-start>=60:emit({'status':'OBSERVER_DEADLINE_NO_QUALIFICATION'});break
    if handle is None:
     try:
      pid=int((cap/'flycast.pid').read_text());m=re.findall(r'RAM\(16 MB\) ([0-9A-Fa-f]+)',(cap/'flycast.log').read_text(errors='replace'))
      if not m:continue
      ram=int(m[-1],16);handle=k.OpenProcess(0x0010|0x0400,False,pid)
      if not handle:raise OSError(ctypes.get_last_error(),'OpenProcess')
      emit({'status':'HOST_RAM_BASE','pid':pid,'RAM':hex(ram),'offset':hex(offset),'host_alias_only':True})
     except FileNotFoundError:continue
    def read():
     b=ctypes.create_string_buffer(128);n=ctypes.c_size_t()
     if not k.ReadProcessMemory(handle,ctypes.c_void_p(ram+offset),b,128,ctypes.byref(n)) or n.value!=128:raise OSError(ctypes.get_last_error(),'ReadProcessMemory')
     return b.raw
    a=read();b=read();emit({'host_elapsed_s':time.monotonic()-start,'pid':pid,'record':rr.stable(a,b)})
  except BaseException as e:emit({'status':'OBSERVER_FAILED','error':repr(e)})
  finally:
   if handle:k.CloseHandle(handle)

def main(arm):
 plan=c.verify_kit('guest');grant=c.read(c.HERE/'ROOT-GUEST-GRANT.json')
 c.need(grant.get('toolchain_sha256')==c.sha(c.HERE/'TOOLCHAIN-SEAL.json') and grant.get('arms')==['off','on'] and grant.get('scope')=='held0-r10c-console45-child55' and grant.get('child_seconds')==55 and grant.get('held')==0,'Root separate held0 grant')
 c.need(os.environ.get('RE4DC_EMU')=='console' and os.environ.get('FP_NOLIMIT')=='1' and os.environ.get('RE4DC_MAX_FLYCASTS')=='16','Explicit console/FPS/global16')
 c.need(not any(os.environ.get(k) for k in ['RE4DC_GD_PROFILE','RE4DC_GD_JITTER','RE4DC_GD_SEED','RE4DC_LOG_STOP','RE4DC_LOG_STOP_TICK']),'No hidden emulator/log stop changes')
 c.verify_inputs(plan)
 template=c.native(plan['template_data']['root']);c.need({q.relative_to(template).as_posix() for q in template.rglob('*') if q.is_file()}==set(plan['template_data']['files']),'Template VMU membership changed')
 cap=c.native(plan['captures'][arm]);cache=c.native(plan['cache_prefixes'][arm]);c.need(not cap.exists() and sys.pycache_prefix==str(cache) and not cache.exists(),'Fresh cap/cache')
 free=shutil.disk_usage('C:\\').free
 wsl=int(subprocess.check_output(['wsl.exe','-d','Ubuntu-24.04','-u','root','--','/usr/bin/python3.12','-I','-S','-B','-c',"import shutil;print(shutil.disk_usage('/mnt/c').free)"],text=True).strip())
 c.need(min(free,wsl)>=24*1024**3,'Lower Windows/WSL C floor')
 base=c.native(plan['base_paths'][arm]);done=c.read(base/'COMPLETE.json')
 c.need(done['status']=='STAGED_READBACK_PASS_GUEST_PENDING' and done['arm']==arm and done['programme']==plan['programmes'][arm]['program.bin']['sha256'],'Exact staged programme')
 c.need(done['plan_sha256']==c.sha(c.HERE/'PLAN.json'),'Exact stage plan')
 for n,pin in done['tracks'].items():c.verify(base/n,pin)
 c.need(c.read(base/'FINAL-READBACK-MANIFEST.json')==c.read(c.HERE/(arm.upper()+'-EXPECTED-MANIFEST.json')),'All1697assets/main14 finalreadback')
 # Parent root controller must independently preserve real inherited stat3/trace16 kernel locks and lower WSL/Windows floor, no guest request before slot admission.
 event=threading.Event();worker=None;capture_process_returned=False
 if arm=='on':
  worker=threading.Thread(target=observe,args=(cap,cap.parent/(cap.name+'-rain-records.jsonl'),plan['observation']['rain_record_ON_offset'],event),daemon=True)
  cap.parent.mkdir(parents=True,exist_ok=True);worker.start()
 else:
  cap.parent.mkdir(parents=True,exist_ok=True);c.fresh(cap.parent/(cap.name+'-rain-records.json'),{'status':'NOT_COMPILED_IN_OFF','no_fabricated_record':True})
 try:
  pillow=c.native(plan['pillow_launcher']);pin=plan['input_pins'][plan['pillow_launcher']];m=c.load_source('pinned_pillow_launcher',pillow,pin)
  argv=['--',str(c.native(plan['tools']['bound']['path'])),str(c.native(plan['tools']['harness']['path'])),'--base',str(base),'--cap',str(cap),'--syms',plan['syms'][arm],'--warp',str(c.native(plan['fixtures']['warp']['path'])),'--pad',str(c.native(plan['fixtures']['pad']['path'])),'--seconds','45','--period','25','--name','rain8ce-held0-'+arm]
  sys.argv=[str(pillow),*argv];m.main();capture_process_returned=True
 finally:
  event.set()
  if worker:
   worker.join(timeout=3);c.need(not worker.is_alive(),'observer did not join')
   pidfile=cap/'flycast.pid';pid=int(pidfile.read_text()) if pidfile.exists() else None
   judged=rr.judge_file(cap.parent/(cap.name+'-rain-records.jsonl'),pid)
   c.fresh(cap.parent/(cap.name+'-diagnostic-result.json'),{'capture_process_returned':capture_process_returned,'diagnostic':judged})
