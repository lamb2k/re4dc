"""Source-only exact020state native204Door4 to209 physicalDoor1/original leader-cut continuation; default checks only, exact root allocation required."""
from pathlib import Path
import sys,json,hashlib,shutil,subprocess,os,time,argparse
L=Path(__file__).parent;R=Path(r'C:\Flycast-Evidence\re4-dreamcast\castle18-20261018\Test21');D=R/'recovered-j-content-20261021';cap=D/'route-walk-controlled-ch32-door021'
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execute-allocated021',action='store_true');a=ap.parse_args()
fixture=L/'controlled-ch32-drain014-warp.txt';observer=L/'observe-controlled-ch32-door021.py';guard=L/'guard-resume-41inner-47absolute-resources-v5.py';vmu=D/'route-walk-controlled-event009/data/T0000_vmu_save_A1.bin';seed=D/'route-walk-controlled-ch32-door020/data'
pinpath=L/'controlled-ch32-door021-pins.json';pins=json.loads(pinpath.read_text(encoding='utf-8'))
actual=[fixture,observer,guard,vmu,seed/'disc.state',seed/'T0000_vmu_save_A1.bin',L/'controlled-ch32-drain014-ABI.json',L/'controlled-ch32-drain014-room-message0.json',L/'controlled018-ABI-WRITE-ALLOWLIST.json',L/'controlled018-READINESS-CONTRACT.json',L/'controlled021-OWNED-INPUT-CONTRACT.json',L/'controlled019-input-DWARF.json',R/'tools/fp_run_ram.py']
for p in actual:assert str(p)in pins,('Actual argv/dependency is not pinned',str(p))
for name,digest in pins.items():assert sha(Path(name))==digest,('Input identity mismatch',name)
assert os.environ.get('RE4DC_EMU','')!='console','This allocation is native Windows Flycast only'
assert sha(guard)=='7aa4113d44b5bab5b1010649a432ed1d50e34aaf4de7fb4899aaf692055b0ba0'
protected={'route-walk127/data/disc.state':'ec9ed07928efec777400317762bb1730a0644def73d610a1631c20381ca40e16','route-walk294/data/disc.state':'cb7a314b8fd0383af0b7baf17c2e87a712705beb122a1d39c7705553dd795258','route-walk-controlled-native-radio013/data/disc.state':'97b63602b83d6234a1603dc24a90fa42f2d0702db626ead2e4d4e5e20efafe13','route-walk-controlled-event009/data/T0000_vmu_save_A1.bin':'425595f75b099a23789e09bbbd8fa4a3661072539644eae6051aa884943400b0'}
protected['route-walk-controlled-ch32-drain014/data/disc.state']='3713cb2a4442ec5ddbf3dc4aec8dff107aa66721913e75813858c326a820adc5'
protected['route-walk-controlled-ch32-drain014/data/T0000_vmu_save_A1.bin']='425595f75b099a23789e09bbbd8fa4a3661072539644eae6051aa884943400b0'
protected['route-walk-controlled-ch32-drain015/data/disc.state']='2236156faabd0def3e9f38d708dbe983d2632441cd3fba521ef8fab634eb5237'
protected['route-walk-controlled-ch32-drain015/data/T0000_vmu_save_A1.bin']='425595f75b099a23789e09bbbd8fa4a3661072539644eae6051aa884943400b0'
protected['route-walk-controlled-ch32-door016/data/disc.state']='a33b2ac44cce042d035f7a981e96cf57b19bec1484f04c86084ece22803f73e8'
protected['route-walk-controlled-ch32-door016/data/T0000_vmu_save_A1.bin']='425595f75b099a23789e09bbbd8fa4a3661072539644eae6051aa884943400b0'
protected['route-walk-controlled-ch32-door017/data/disc.state']='1b1485784a8c796fbaad18573002ae353f75d9b67c0b4b156e1724bf296ac04b'
protected['route-walk-controlled-ch32-door017/data/T0000_vmu_save_A1.bin']='425595f75b099a23789e09bbbd8fa4a3661072539644eae6051aa884943400b0'
protected['route-walk-controlled-ch32-door018/data/disc.state']='4d7178b9d7420156b39328396cae08661f92c297f4ed28794b145a3cfe03ecdc'
protected['route-walk-controlled-ch32-door018/data/T0000_vmu_save_A1.bin']='425595f75b099a23789e09bbbd8fa4a3661072539644eae6051aa884943400b0'
protected['route-walk-controlled-ch32-door019/data/disc.state']='669b920f06e89403a15d3796021878c39ee9807fe020487e6a8666220f635631'
protected['route-walk-controlled-ch32-door019/data/T0000_vmu_save_A1.bin']='425595f75b099a23789e09bbbd8fa4a3661072539644eae6051aa884943400b0'
protected['route-walk-controlled-ch32-door020/data/disc.state']='eba7a32afa7c59381ec7ce36918ea706feea187757e8fbb40a2fe5f2695ac008'
protected['route-walk-controlled-ch32-door020/data/T0000_vmu_save_A1.bin']='425595f75b099a23789e09bbbd8fa4a3661072539644eae6051aa884943400b0'
for name,digest in protected.items():assert sha(D/name)==digest
compile(observer.read_text(encoding='utf-8'),str(observer),'exec')
assert fixture.read_text().splitlines()==['squeeze 49152 0','name castle21-CONTROLLED-ch32-drain014','room 0x205','jp 0','chapter 7','pos 46118.5419921875 996.8269653320312 48787.291015625','ang 0','alivelog 30','dump']
admission=20342374400;runtime=19394461696
argv=[sys.executable,str(R/'tools/fp_run_ram.py'),'--base',str(D/'master'),'--cap',str(cap),'--syms',(R/'builds/c21jmW/syms.txt').read_text().strip(),'--seconds','41','--vmu',str(vmu),'--state-seed',str(seed),'--warp',str(fixture),'--period','0','--name','castle21-CONTROLLED-original209-door021']
if not a.execute_allocated021:
 print(json.dumps(dict(prepared_only=True,no_guest=True,observer_sha256=sha(observer),wrapper_sha256=sha(Path(__file__)),pins_sha256=sha(pinpath),argv=argv,admission_bytes=admission,runtime_floor=runtime,capture_cap=60*1024**2,global_limit=16,lane_limit=2,exclusive_gui_input_required=True,source_only=True)));sys.exit(0)
allocation=json.loads((L/'DOOR021-ROOT-ALLOCATION.json').read_text(encoding='utf-8'));assert allocation['allocated021']is True and allocation['wrapper_sha256']==sha(Path(__file__))and allocation['pins_sha256']==sha(pinpath),'Exact one-run root allocation required'
assert allocation['observer_sha256']==sha(observer)and allocation['allow_debug_goto_command_writes']is True and allocation['allow_owned_window_focus']is True and allocation['allow_scan_code_SendInput']is True and allocation['exclusive_gui_input']is True and allocation['maximum_successful_command_bytes']==29 and allocation['write_allowlist']==[{'address':'0x8c47ff60','bytes':24},{'address':'0x8c4801b6','bytes':1},{'address':'0x8c47fff0','bytes':4}],'Exact debug command write allocation required'
assert not cap.exists()and not(D/(cap.name+'-observer-ready.json')).exists()
assert shutil.disk_usage(D).free>=admission,('Fresh disk admission',admission)
cmd="$p=@(Get-CimInstance Win32_Process -Filter \"Name LIKE 'Flycast%'\"); ConvertTo-Json -InputObject @($p | Select-Object ProcessId,ExecutablePath) -Compress"
p=subprocess.run(['powershell.exe','-NoProfile','-Command',cmd],capture_output=True,text=True,check=True);processes=json.loads(p.stdout or'[]');assert isinstance(processes,list)and len(processes)<16,'Global Flycast16 admission';assert sum(str(v.get('ExecutablePath','')).lower().startswith(str(D).lower())for v in processes)<2,'Castle2 admission'
assert not processes,'021 owned-focus unit requires no peer Flycast/GUI-input process; root must close QA and hold exclusive GUI-input lease'
segment=D/'segments'/cap.name;assert not segment.exists();segment.mkdir(parents=True)
for n in ['track03.iso','track02.raw']:os.link(D/'master'/n,segment/n)
proof=dict(scope='CONTROLLED actual020 fullstate continuation afteroriginalfirstcutreturn. Inheritedactual020alreadyatDoor4; experimental scan-code SendInputA with nativeack, no firstgoto. ONLYafteractual209freeplay publishslot2/currententry3 combinedphysicalDoor1/AEV0A,29Bcountlast. PhysicaldoorA uses sameackmethod; maxonekeydownperstage. No actor/room/HP/RSF/AI/outcome writes/build/fullcopy. Inherited017 and authentic127/294/013/009VMUs preserved.',inputs=pins,argv=argv,fixture_sha256=sha(fixture),observer_sha256=sha(observer),supervisor_sha256=sha(guard),programme_binding_receipt_sha256=sha(D/'frozen-master-programme-binding-20261021.json'),environment={n:os.environ.get(n)for n in ['RE4DC_EMU','TRACE_SLOTS','TRACE_LOCK_OWNER']},admission_bytes=admission,runtime_floor_bytes=runtime,capture_cap_bytes=60*1024**2,raw_seconds=41,normal_close_seconds=39,absolute_seconds=47.5,global16=True,lane2=True,protected=protected,initial_process_inventory=processes,acceptance='Actual native204Door4 request then209 entry; actual game-thread combinedpose/nativephysicaldoor1 action; actualDoor1 opening; originalAEV0A camera3 then2/eventreturn/Stop0/advancingframes, screenshots. Commandsetup/doorflags/roomentryalone are not cut completion. Partialoriginalevent preserved at bound, no retry/rollback or forcedoutcomes. No combat/release/hardware/performance acceptance.')
(D/(cap.name+'-preparation.json')).write_text(json.dumps(proof,indent=2)+'\n')
watch=None;obs=None;harness_started=False
try:
 watch=subprocess.Popen([sys.executable,str(guard),str(cap)],creationflags=subprocess.CREATE_NO_WINDOW)
 obs=subprocess.Popen([sys.executable,str(observer),str(cap)],creationflags=subprocess.CREATE_NO_WINDOW)
 until=time.monotonic()+15
 while not(D/(cap.name+'-observer-ready.json')).exists():assert obs.poll()is None and time.monotonic()<until;time.sleep(.05)
 harness_started=True
 subprocess.run(argv,check=True)
finally:
 try:
  if not harness_started:
   # These exact helper objects cannot own a guest: the harness has never been invoked.
   # Any unexpected ownership artifact retains the watcher rather than guessing closure.
   assert not(cap/'owned-process.json').exists(),'Unexpected guest ownership before harness invocation'
   cleanup_errors=[]
   for label,helper in [('observer',obs),('watcher',watch)]:
    if helper is None:continue
    try:
     if helper.poll()is None:helper.terminate()
     helper.wait(timeout=5)
    except BaseException as e:cleanup_errors.append((label,repr(e)))
   assert not cleanup_errors,('Startup helper cleanup failed',cleanup_errors)
  else:
   try:
    assert watch is not None
    watch.wait(timeout=85)  # Never terminate the guest's independent V5 watcher here.
   finally:
    # A watcher wait failure must not bypass reaping this exact owned observer helper.
    if obs is not None and obs.poll()is None:
     try:obs.wait(timeout=5)
     except subprocess.TimeoutExpired:obs.terminate();obs.wait(timeout=3)
 finally:
  for name,digest in protected.items():assert sha(D/name)==digest,('Protected input changed',name)
 if harness_started:
  assert (cap/'owned-resource-guard.json').exists(),'No retained supervisor receipt'
  receipt=json.loads((cap/'owned-resource-guard.json').read_text());assert receipt['process_exited']and receipt['closed_identity']['retained_handle_signaled'],'Exact owned exit unverified'
  assert watch.returncode==0,('V5 failure preserved',watch.returncode)
  assert obs.returncode==0,('Observer failure preserved',obs.returncode)
print('Controlled021 closed; audit native209 physicalDoor1/originalleadercut independently')
