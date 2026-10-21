from pathlib import Path
import subprocess,sys,shutil,json,hashlib,os
R=Path(r'C:\Flycast-Evidence\re4-dreamcast\castle18-20261018\Test21');L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18');D=R/'recovered-j-content-20261021';number=int(sys.argv[1]);assert 2<=number<=8;cap=D/f'coldload{number:02d}';seed=D/f'coldload{number-1:02d}';assert not cap.exists();assert shutil.disk_usage(R).free>=16*1024**3+128*1024**2
newsha='b67ac21eff8d819ef9ca5f0997b4c16401cb98a3d304feb65aa4b90f7affbeb6';assert json.loads((seed/'run-start.json').read_text())['disc_sha256']==newsha;assert json.loads((seed/'run-result.json').read_text())['emulator_exited'];state_sha=hashlib.sha256((seed/'data/disc.state').read_bytes()).hexdigest()
source=Path(r'C:\Flycast-Evidence\re4-dreamcast\discsets20-20261020\fixtures\handoff-ch23end-A1.bin');original_sha=hashlib.sha256(source.read_bytes()).hexdigest();vm=D/'original-handoff-VMU-cold-copy.bin';assert hashlib.sha256(vm.read_bytes()).hexdigest()==original_sha
segment=D/'segments'/cap.name;assert not segment.exists();segment.mkdir(parents=True)
for n in ['track03.iso','track02.raw']:os.link(D/'master'/n,segment/n)
(D/(cap.name+'-inputs.json')).write_text(json.dumps(dict(scope='Only own recovered-J NEW cold lineage continuation; no old originalJ snapshot. Normal Title/CardLoad only. Unchanged program/assets.',seed=str(seed),state_sha256=state_sha,new_iso_sha256=newsha,elf_sha256='4d823b496b9a402baadabe7f679c089fa0fd55c7ffd175ec634915745a11487f',original_handoff_vmu_sha256=original_sha),indent=2)+'\n')
observer=subprocess.Popen([sys.executable,str(L/'observe-recovered-j-cold-source-context.py'),str(cap)],creationflags=subprocess.CREATE_NO_WINDOW)
try:subprocess.run([sys.executable,str(R/'tools/fp_run_ram.py'),'--base',str(D/'master'),'--cap',str(cap),'--syms',(R/'programs/candidate-routec21jmW/syms.txt').read_text().strip(),'--seconds','50','--vmu',str(vm),'--warp',str(R/'fixtures/coldload-observer.txt'),'--pad',str(R/'fixtures/load-pad.txt'),'--state-seed',str(seed/'data'),'--period','10','--name','castle21-recoveredJ-NEW-cold-CardLoad'],check=True)
finally:
 try:observer.wait(timeout=3)
 except subprocess.TimeoutExpired:observer.terminate();observer.wait(timeout=3)
 assert hashlib.sha256(source.read_bytes()).hexdigest()==original_sha and hashlib.sha256(vm.read_bytes()).hexdigest()==original_sha