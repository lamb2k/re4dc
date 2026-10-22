from pathlib import Path
import subprocess,sys,shutil,json,hashlib,os,time
R=Path(r'C:\Flycast-Evidence\re4-dreamcast\castle18-20261018\Test21');L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18');D=R/'recovered-j-content-20261021';cap=D/'route-walk278';seed=D/'route-walk277';assert not cap.exists();assert shutil.disk_usage(R).free>=16*1024**3+128*1024**2
newsha='b67ac21eff8d819ef9ca5f0997b4c16401cb98a3d304feb65aa4b90f7affbeb6';assert json.loads((seed/'run-start.json').read_text())['disc_sha256']==newsha;state_sha=hashlib.sha256((seed/'data/disc.state').read_bytes()).hexdigest();assert state_sha=='1ad1f000e4e128e1f09c86668ed678a5aa90f86be3a80ddd11a595ea3d61f73d'
segment=D/'segments'/cap.name;assert not segment.exists();segment.mkdir(parents=True)
for n in ['track03.iso','track02.raw']:os.link(D/'master'/n,segment/n)
targets='16219,-38909';controller_path=L/'owned-window-recovered-j-r201-Garrador-actualcenter-tracking3500-v7-still.py';ready=D/(cap.name+'-controller-ready.json');assert not ready.exists()
(D/(cap.name+'-inputs.json')).write_text(json.dumps(dict(scope='Root-reviewed consolidated ordinary combat from authentic277 currentstairs position. Hostfront3500tracking policy; corrected sourceackfine/coastneutral controls, actual sourcecenter aim. Preserve all original frozen identities and conservative real firingguards including strongrear/miss75/laser/sphere/stability/rawneutral3/part37HP proof, max6shots/42s, anyhealthloss/process/resources. No traversal/doorprobe.',seed=str(seed),seed_sha256=state_sha,new_iso_sha256=newsha,elf_sha256='4d823b496b9a402baadabe7f679c089fa0fd55c7ffd175ec634915745a11487f',target_xz=targets,controller_sha256=hashlib.sha256(controller_path.read_bytes()).hexdigest()),indent=2)+'\n')
controller=subprocess.Popen([sys.executable,str(controller_path),str(cap),targets,'250','201'],creationflags=subprocess.CREATE_NO_WINDOW);sampler=observer=None
try:
 deadline=time.monotonic()+20
 while not ready.exists():
  assert controller.poll()is None and time.monotonic()<deadline,'Controller readiness failed'
  time.sleep(.1)
 sampler=subprocess.Popen([sys.executable,str(L/'test21-sample-j-motion-cache-v3.py'),str(cap)],creationflags=subprocess.CREATE_NO_WINDOW)
 observer=subprocess.Popen([sys.executable,str(L/'observe-recovered-j-cold-source-context.py'),str(cap)],creationflags=subprocess.CREATE_NO_WINDOW)
 subprocess.run([sys.executable,str(R/'tools/fp_run_ram.py'),'--base',str(D/'master'),'--cap',str(cap),'--syms',(R/'programs/candidate-routec21jmW/syms.txt').read_text().strip(),'--seconds','50','--warp',str(R/'fixtures/coldload-observer.txt'),'--pad',str(R/'fixtures/load-pad.txt'),'--state-seed',str(seed/'data'),'--period','10','--name','castle21-recoveredJ-route-walk278'],check=True)
finally:
 for proc in [controller,sampler,observer]:
  if proc:
   try:proc.wait(timeout=3)
   except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=3)