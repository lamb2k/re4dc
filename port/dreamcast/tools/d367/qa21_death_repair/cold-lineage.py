from pathlib import Path
from evidence_footprint import measure
import argparse,ctypes,hashlib,json,os,shutil,subprocess,sys,time
def stop_reason(elapsed, free):
    if elapsed >= 47.5:
        return 'absolute owned guest wall-time cap'
    if free < 18*1024**3+64*1024**2:
        return 'C18GiB+64MiB runtime floor'
    return None
p=argparse.ArgumentParser();p.add_argument('name');p.add_argument('--keys',type=Path,required=True);p.add_argument('--seed');p.add_argument('--controller',type=Path);p.add_argument('--runtime-manifest',type=Path,required=True);a=p.parse_args()
assert a.name.replace('-','').replace('_','').isalnum()
# A future separately allocated stage must provide this exact new-program manifest.
# This launcher never stages anything and never accepts the historical control/combined states.
m=json.loads(a.runtime_manifest.read_text());assert m['scope']=='trace-runtime-qualification'
assert hashlib.sha256(Path(__file__).read_bytes()).hexdigest()==m['launcher_sha256']
assert hashlib.sha256(Path(__file__).with_name('evidence_footprint.py').read_bytes()).hexdigest()==m['evidence_footprint_sha256']
R=Path(m['evidence_root']);assert R.resolve()==Path('C:/Flycast-Evidence/re4-dreamcast/qa21-death-repair-runtime-20261021').resolve()
D=Path(m['dependencies_root']);binding=Path(m['binding']);assert binding.parent.resolve()==R.resolve()
elf=Path(m['elf']);layout=Path(m['layout']);disc=Path(m['disc']);assert disc.resolve()==(R/'trace-input/gdemu').resolve()
r=json.loads(binding.read_text());build=json.loads(Path(m['build_receipt']).read_text());stage=json.loads(Path(m['stage_receipt']).read_text())
assert build['status']=='LINK_COMPLETE_ONLY' and not build['stage_performed']
assert build['source']['trace_runtime_source']=='f99dc69ad8bfeebcdb10913443543514dc40f9cc'
assert build['source']['repair_source']=='f071b4e9069ebd3a7dec48a98f2fea95f6d11215' and build['arm']=='on'
assert r['source_candidate']==build['source']['trace_tools_HEAD']
assert r['disc_program_sha256']==build['files']['program.bin']['sha256']==stage['program_sha256']
assert r['elf_sha256']==build['files']['re4dc-game.elf']['sha256']==hashlib.sha256(elf.read_bytes()).hexdigest()
assert r['disc_program_sha256'] not in ('ce080eb290aec073f406e93da27911f4fa70b457768288f52a893175a6846e8e','5c5a6c434751b03a0aaa05d8e2478820ca82a3790d7c3b06799f7845d6c5f68b','ca30bfc0c28490c91d18dbd37182e89d1f905cbf9bf735280bc7cd90cdb93b94')
assert stage['unrelated_exact_file_count']==1728 and stage['all14_staged_overlays_match_build'] and stage['input_track03_sha256']=='2e40da769c049ab502f3608ea4f633b2b8ff32f4e9fe290b0c15ae30ac31b0aa'
assert not stage['source_image_mutated'] and not stage['image_hardlinks_or_shared_writable_extents']
assert json.loads(layout.read_text())['elf_sha256']==r['elf_sha256']
expected={'repair-cold-r10301':(None,'cold',False),'repair-return-door01':('repair-cold-r10301','empty',True),'repair-BB-only01':('repair-return-door01','BB',False),'repair-continue01':('repair-BB-only01','continue',False),'repair-gameplay01':('repair-continue01','empty',True),'repair-continue-play02':('repair-gameplay01','empty',True)}
assert a.name in expected;seed,keyname,controller=expected[a.name];assert a.seed==seed and bool(a.controller)==controller
assert hashlib.sha256(a.keys.read_bytes()).hexdigest()==m['keys'][keyname]['sha256']
if a.controller:assert hashlib.sha256(a.controller.read_bytes()).hexdigest()==m['gameplay_controller_sha256' if a.name in ('repair-gameplay01','repair-continue-play02') else 'door_controller_sha256']
if a.seed:assert (R/a.seed/'checkpoint.json').is_file()
for name,digest in m['dependencies'].items():assert hashlib.sha256((D/name).read_bytes()).hexdigest()==digest
assert shutil.disk_usage('C:/').free>18*1024**3+128*1024**2
syms=' '.join(hex(int(r['symbols'][x],0)-0x8c000000) for x in ('logbuf','head','stage'))
runner=D/'checkpoint_runner18.py'
cmd=[sys.executable,str(D/'run_observed_v3.py'),'--runner',str(runner),'--runner-sha256',hashlib.sha256(runner.read_bytes()).hexdigest(),'--disc',str(disc),'--cap',str(R/a.name),'--keys',str(a.keys),'--syms',syms,'--name','qa21-deathtrace-'+a.name,'--binding',str(binding),'--layout',str(layout),'--event-shots','--seconds','41','--no-limit','--save-checkpoint','--elf',str(elf)]
if a.seed:cmd+=['--checkpoint-seed',str(R/a.seed)]
assert not (R/a.name).exists();I=R/'invocations'/a.name;I.mkdir(parents=True,exist_ok=False)
shutil.copy2(__file__,I/'run-fixture.py');shutil.copy2(Path(__file__).with_name('evidence_footprint.py'),I/'evidence_footprint.py');shutil.copy2(a.keys,I/'keys.txt')
(I/'invocation.json').write_text(json.dumps({'argv':cmd,'free_c':shutil.disk_usage('C:/').free,'source':r['source_candidate'],'program':r['disc_program_sha256'],'elf':r['elf_sha256'],'tools':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in D.glob('*.py')}},indent=2)+'\n')
k=ctypes.WinDLL('kernel32',use_last_error=True)
k.OpenProcess.argtypes=[ctypes.c_ulong,ctypes.c_int,ctypes.c_ulong];k.OpenProcess.restype=ctypes.c_void_p
k.QueryFullProcessImageNameW.argtypes=[ctypes.c_void_p,ctypes.c_ulong,ctypes.c_wchar_p,ctypes.POINTER(ctypes.c_ulong)]
k.GetProcessTimes.argtypes=[ctypes.c_void_p]+[ctypes.POINTER(ctypes.c_ulonglong)]*4
k.GetExitCodeProcess.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_ulong)]
k.TerminateProcess.argtypes=[ctypes.c_void_p,ctypes.c_uint]
k.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_ulong];k.WaitForSingleObject.restype=ctypes.c_ulong
k.CloseHandle.argtypes=[ctypes.c_void_p]
child=subprocess.Popen(cmd);controller=None
if a.controller:
 shutil.copy2(a.controller,I/'controller.py')
 controller=subprocess.Popen([sys.executable,str(a.controller),str(R/a.name),str(D),str(R/a.seed) if a.seed else ''])
handle=None;receipt={'absolute_guest_limit_s':47.5,'inner_requested_s':41,'scope':'Independent PID, executable and process-start verified outer guest supervisor'}
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
  usage=measure(R/a.name,disc);receipt['latest_evidence_footprint']=usage
  if usage['charged_bytes']>=60_000_000:reason='60MB new evidence cap'
  if reason and not receipt.get('forced_stop'):
   assert times[0].value==start;assert k.TerminateProcess(handle,125)
   receipt.update(forced_stop=reason,stop_at_s=elapsed,checkpoint_usable=False)
 if child.poll() is not None and handle is None:break
 time.sleep(0.1)
rc=child.wait();receipt['launcher_exit']=rc
if controller:
 try:receipt['controller_exit']=controller.wait(timeout=2)
 except subprocess.TimeoutExpired:controller.terminate();receipt['controller_exit']=controller.wait()
(I/'process-supervisor.json').write_text(json.dumps(receipt,indent=2)+'\n')
(I/'exit.json').write_text(json.dumps({'exit':rc})+'\n');raise SystemExit(rc)