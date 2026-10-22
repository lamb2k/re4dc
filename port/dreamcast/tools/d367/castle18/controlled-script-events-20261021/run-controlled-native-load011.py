"""Prepare/check by default; execution requires root's separate allocated-run invocation."""
from pathlib import Path
import sys,json,hashlib,shutil,subprocess,os,time,argparse
L=Path(__file__).parent;R=Path(r'C:\Flycast-Evidence\re4-dreamcast\castle18-20261018\Test21');D=R/'recovered-j-content-20261021';cap=D/'route-walk-controlled-native-load011'
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execute-allocated011',action='store_true');a=ap.parse_args()
fixture=R/'fixtures/coldload-observer.txt';pad=L/'native-load011-pad.txt';observer=L/'observe-controlled-native-load011.py';guard=L/'guard-resume-41inner-47absolute-resources-v5.py';vmu=D/'route-walk-controlled-event009/data/T0000_vmu_save_A1.bin'
pins=json.loads((L/'controlled-native-load011-pins.json').read_text(encoding='utf-8'))
for path,digest in pins.items():assert sha(Path(path))==digest,('Input identity mismatch',path)
assert os.environ.get('RE4DC_EMU','')!='console','Native ordinary harness only; console backend is another fixture'
assert sha(guard)=='7aa4113d44b5bab5b1010649a432ed1d50e34aaf4de7fb4899aaf692055b0ba0'
assert sha(vmu)=='425595f75b099a23789e09bbbd8fa4a3661072539644eae6051aa884943400b0'
protected={'route-walk127':'ec9ed07928efec777400317762bb1730a0644def73d610a1631c20381ca40e16','route-walk294':'cb7a314b8fd0383af0b7baf17c2e87a712705beb122a1d39c7705553dd795258'}
for name,digest in protected.items():assert sha(D/name/'data/disc.state')==digest
compile(observer.read_text(encoding='utf-8'),str(observer),'exec')
if not a.execute_allocated011:
 print(json.dumps(dict(prepared_only=True,no_guest=True,private009VMU=sha(vmu),observer_sha256=sha(observer),supervisor_sha256=sha(guard),pins_sha256=sha(L/'controlled-native-load011-pins.json'))));sys.exit(0)
assert not cap.exists()and not(D/(cap.name+'-observer-ready.json')).exists()
# Conservative latest root peer envelope: programme128 + pack448 + source64MiB,
# in addition to the standing200MiB peers and128MiB guest start allowance.
admission=18*1024**3+(128+200+640)*1024**2;assert shutil.disk_usage(D).free>=admission,('Fresh disk admission',admission)
p=subprocess.run(['powershell.exe','-NoProfile','-Command',"@(Get-CimInstance Win32_Process -Filter \"Name LIKE 'Flycast%'\").Count"],capture_output=True,text=True,check=True);assert int(p.stdout.strip())<16,'Global Flycast16 capacity'
segment=D/'segments'/cap.name;assert not segment.exists();segment.mkdir(parents=True)
for n in ['track03.iso','track02.raw']:os.link(D/'master'/n,segment/n)
proof=dict(scope='CONTROLLED native cold LOAD from actual009 persisted privateVMU; ordinary source-gated Title/CardLoad pad input only. No state-seed, no snapshot restore, no room/jp/RSF/HP/AI intervention, no authentic rollback. Not release or physical Dreamcast acceptance.',vmu_source=str(vmu),vmu_source_sha256=sha(vmu),state_seed=None,inputs=pins,environment={n:os.environ.get(n)for n in ['RE4DC_EMU','FP_NOLIMIT','TRACE_SLOTS','TRACE_LOCK_OWNER']},harness_seconds=41,observer_close_seconds=39,absolute_seconds=47.5,capture_cap_bytes=60*1024**2,admission_bytes=admission,runtime_floor_bytes=18*1024**3+64*1024**2,protected=protected,programme_binding_receipt_sha256=sha(D/'frozen-master-programme-binding-20261021.json'),acceptance='Observe actual original CardLoad success and post-load chapter7/room204 gameplay plus screenshot/closedstate; merely reaching menus or setting fields is partial. Private source VMU remains unchanged; runtime VMU is a fresh harness copy. Template data may contain an unused state file; AutoLoadState=no is explicitly verified and no state-seed argument supplied.')
(D/(cap.name+'-preparation.json')).write_text(json.dumps(proof,indent=2)+'\n')
watch=subprocess.Popen([sys.executable,str(guard),str(cap)],creationflags=subprocess.CREATE_NO_WINDOW);obs=subprocess.Popen([sys.executable,str(observer),str(cap)],creationflags=subprocess.CREATE_NO_WINDOW)
try:
 until=time.monotonic()+15
 while not(D/(cap.name+'-observer-ready.json')).exists():assert obs.poll()is None and time.monotonic()<until;time.sleep(.05)
 subprocess.run([sys.executable,str(R/'tools/fp_run_ram.py'),'--base',str(D/'master'),'--cap',str(cap),'--syms',(R/'builds/c21jmW/syms.txt').read_text().strip(),'--seconds','41','--vmu',str(vmu),'--warp',str(fixture),'--pad',str(pad),'--period','0','--name','castle21-CONTROLLED-native-cold-LOAD009-privateVMU011'],check=True)
finally:
 watch.wait(timeout=85)
 if obs.poll()is None:
  try:obs.wait(timeout=5)
  except subprocess.TimeoutExpired:obs.terminate();obs.wait(timeout=3)
 assert sha(vmu)==pins[str(vmu)],'Original009 privateVMU changed'
 for name,digest in protected.items():assert sha(D/name/'data/disc.state')==digest
 if cap.exists()and(cap/'owned-resource-guard.json').exists():assert json.loads((cap/'owned-resource-guard.json').read_text())['process_exited'],'Exact process exit unverified'
 assert watch.returncode==0,('V5 supervisor failure preserved',watch.returncode)
print('Controlled010 closed; audit native Load and actual runtime savedata independently')
