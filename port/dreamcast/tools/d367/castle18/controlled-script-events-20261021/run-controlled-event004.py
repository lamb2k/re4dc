from pathlib import Path
import sys,json,hashlib,shutil,subprocess,os,time,datetime
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18');R=Path(r'C:\Flycast-Evidence\re4-dreamcast\castle18-20261018\Test21');D=R/'recovered-j-content-20261021';cap=D/'route-walk-controlled-event004';assert not cap.exists();assert shutil.disk_usage(D).free>=18*1024**3+328*1024**2,'Admission18GiB+128MiB+200MiB peers'
fixture=L/'controlled-event004-warp.txt';observer=L/'observe-controlled-r208-event004.py';guard=L/'guard-resume-41inner-47absolute-resources-v4.py';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();assert sha(fixture)=='12ad4b88c83efc6ae00ea138ef713ce9162e83e02cc531ce02211bd646370db0';assert sha(guard)=='c166c7a00d8b34082dd9c5cb4957bd66a4d10e54abbc3104aa316e11c70571e7';compile(observer.read_text(),str(observer),'exec');assert not(D/(cap.name+'-observer-ready.json')).exists()
segment=D/'segments'/cap.name;assert not segment.exists();segment.mkdir(parents=True)
for n in ['track03.iso','track02.raw']:os.link(D/'master'/n,segment/n)
proof=dict(scope='CONTROLLED SCRIPTED EVENT COVERAGE NEW COLD TEST LINEAGE. No authentic snapshot input, no new game program/assets/fullimage copy. Native fixture initialchapter/partner/position/DebugTrg0 pressure bypass are declared SETUP, NEVERauthenticcombat orhardwareacceptance.',fixture_raw_sha256=sha(fixture),fixture_normalized_lf_sha256=hashlib.sha256(fixture.read_bytes().replace(b'\r',b'')).hexdigest(),observer_sha256=sha(observer),supervisor_sha256=sha(guard),runtime='12a841d7c',elf_sha256='4d823b496b9a402baadabe7f679c089fa0fd55c7ffd175ec634915745a11487f',image_sha256='b67ac21eff8d819ef9ca5f0997b4c16401cb98a3d304feb65aa4b90f7affbeb6',protected_states_unchanged=['route-walk127','route-walk294'],harness_seconds=41,absolute_seconds=47.5,source_event='Cold208 DebugTrg0 at60 bypasses plates; require original crank rise4984/4000 and event return; goto240 original204 door and A280; require actual204 load. Plates/bridge/footings not exercised.',assets={n:json.loads((D/'master/base-manifest.json').read_text())[n]for n in ['st2/r208.arc','st2/r204.arc']})
(D/(cap.name+'-preparation.json')).write_text(json.dumps(proof,indent=2)+'\n')
watch=subprocess.Popen([sys.executable,str(guard),str(cap)],creationflags=subprocess.CREATE_NO_WINDOW);obs=subprocess.Popen([sys.executable,str(observer),str(cap)],creationflags=subprocess.CREATE_NO_WINDOW)
try:
 until=time.monotonic()+15
 while not(D/(cap.name+'-observer-ready.json')).exists():assert obs.poll()is None and time.monotonic()<until;time.sleep(.05)
 subprocess.run([sys.executable,str(R/'tools/fp_run_ram.py'),'--base',str(D/'master'),'--cap',str(cap),'--syms',(R/'programs/candidate-routec21jmW/syms.txt').read_text().strip(),'--seconds','41','--warp',str(fixture),'--period','0','--name','castle21-CONTROLLED-r208-crank-exit004'],check=True)
finally:
 watch.wait(timeout=85)
 if obs.poll()is None:
  try:obs.wait(timeout=5)
  except subprocess.TimeoutExpired:obs.terminate();obs.wait(timeout=3)
 if cap.exists()and(cap/'owned-resource-guard.json').exists():
  receipt=json.loads((cap/'owned-resource-guard.json').read_text());assert receipt['process_exited'],'Exact process exit unverified'
 assert watch.returncode==0,('Supervisor failed; preserve controlled evidence',watch.returncode)
print('Controlledevent004 closed; audit originalpostconditions separately')
