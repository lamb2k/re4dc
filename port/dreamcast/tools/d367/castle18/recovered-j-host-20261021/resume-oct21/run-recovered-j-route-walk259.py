from pathlib import Path
import subprocess,sys,shutil,json,hashlib,os,time
R=Path(r'C:\Flycast-Evidence\re4-dreamcast\castle18-20261018\Test21');L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18');D=R/'recovered-j-content-20261021';cap=D/'route-walk259';seed=D/'route-walk258';assert not cap.exists();assert shutil.disk_usage(R).free>=16*1024**3+128*1024**2
newsha='b67ac21eff8d819ef9ca5f0997b4c16401cb98a3d304feb65aa4b90f7affbeb6';assert json.loads((seed/'run-start.json').read_text())['disc_sha256']==newsha;state_sha=hashlib.sha256((seed/'data/disc.state').read_bytes()).hexdigest();assert state_sha=='839d1e9f787228e39b0746783bdbb0f350d1ec4804ef28fe04a894ea2cac3330'
segment=D/'segments'/cap.name;assert not segment.exists();segment.mkdir(parents=True)
for n in ['track03.iso','track02.raw']:os.link(D/'master'/n,segment/n)
targets='32500,-42000;30350,-42000;27000,-42000;21300,-42000;19000,-45000';controller_path=L/'owned-window-recovered-j-r201-source-ack-quickturn18-full-walk-still.py';ready=D/(cap.name+'-controller-ready.json');assert not ready.exists()
(D/(cap.name+'-inputs.json')).write_text(json.dumps(dict(scope='Exact258 originalWait/cell/lever completed1200/90 HG10+25,source28115 state839d1e9f787228e39b0746783bdbb0f350d1ec4804ef28fe04a894ea2cac3330. Execute FULL known5waypoint cell-to-West firingline escape inoneboundedguest; ordinarysourceBackack+B quickturn chosen>1.8rad, all existing injury/source/PID/resourceguards. Ashley remainsoriginalWait46 at29299,-42767. Preserveallactualinjuries, no rollback/state/gamewrites/build. Independentreviewedaimsetup next.',seed=str(seed),seed_sha256=state_sha,new_iso_sha256=newsha,elf_sha256='4d823b496b9a402baadabe7f679c089fa0fd55c7ffd175ec634915745a11487f',target_xz=targets,controller_sha256=hashlib.sha256(controller_path.read_bytes()).hexdigest()),indent=2)+'\n')
controller=subprocess.Popen([sys.executable,str(controller_path),str(cap),targets,'180','201'],creationflags=subprocess.CREATE_NO_WINDOW);sampler=observer=None
try:
 deadline=time.monotonic()+20
 while not ready.exists():
  assert controller.poll()is None and time.monotonic()<deadline,'Controller readiness failed'
  time.sleep(.1)
 sampler=subprocess.Popen([sys.executable,str(L/'test21-sample-j-motion-cache-v3.py'),str(cap)],creationflags=subprocess.CREATE_NO_WINDOW)
 observer=subprocess.Popen([sys.executable,str(L/'observe-recovered-j-cold-source-context.py'),str(cap)],creationflags=subprocess.CREATE_NO_WINDOW)
 subprocess.run([sys.executable,str(R/'tools/fp_run_ram.py'),'--base',str(D/'master'),'--cap',str(cap),'--syms',(R/'programs/candidate-routec21jmW/syms.txt').read_text().strip(),'--seconds','50','--warp',str(R/'fixtures/coldload-observer.txt'),'--pad',str(R/'fixtures/load-pad.txt'),'--state-seed',str(seed/'data'),'--period','10','--name','castle21-recoveredJ-route-walk259'],check=True)
finally:
 for proc in [controller,sampler,observer]:
  if proc:
   try:proc.wait(timeout=3)
   except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=3)