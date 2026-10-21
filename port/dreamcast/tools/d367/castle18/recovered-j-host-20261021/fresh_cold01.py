from pathlib import Path
import subprocess,sys,shutil,json,hashlib,os
R=Path(r'C:\Flycast-Evidence\re4-dreamcast\castle18-20261018\Test21');L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18');D=R/'recovered-j-content-20261021';cap=D/'coldload01';assert not cap.exists();assert shutil.disk_usage(R).free>=16*1024**3+128*1024**2
source=Path(r'C:\Flycast-Evidence\re4-dreamcast\discsets20-20261020\fixtures\handoff-ch23end-A1.bin');vm=D/'original-handoff-VMU-cold-copy.bin';assert not vm.exists();original_sha=hashlib.sha256(source.read_bytes()).hexdigest();shutil.copyfile(source,vm);assert hashlib.sha256(vm.read_bytes()).hexdigest()==original_sha
proof=json.loads((D/'master-proof.json').read_text());assert proof['iso_sha256']=='b67ac21eff8d819ef9ca5f0997b4c16401cb98a3d304feb65aa4b90f7affbeb6'
segment=D/'segments'/cap.name;assert not segment.exists();segment.mkdir(parents=True)
for n in ['track03.iso','track02.raw']:os.link(D/'master'/n,segment/n)
(D/'coldload01-inputs.json').write_text(json.dumps(dict(scope='NEW cold-boot recovered-J-content lineage only; no originalJ snapshot. Original handoff VMU fresh private copy; normal gated Title/CardLoad pad input only. Same original program/6765file hashes. No game RAM writes, source/asset replacement, build, SD or release claim.',vmu_source=str(source),vmu_original_sha256=original_sha,vmu_copy=str(vm),elf_sha256=proof['program_elf_sha256'],new_iso_sha256=proof['iso_sha256'],old_j221_preserved=True,original_image_not_reconstructed=True),indent=2)+'\n')
observer=subprocess.Popen([sys.executable,str(L/'observe-recovered-j-cold-source-context.py'),str(cap)],creationflags=subprocess.CREATE_NO_WINDOW)
try:subprocess.run([sys.executable,str(R/'tools/fp_run_ram.py'),'--base',str(D/'master'),'--cap',str(cap),'--syms',(R/'programs/candidate-routec21jmW/syms.txt').read_text().strip(),'--seconds','50','--vmu',str(vm),'--warp',str(R/'fixtures/coldload-observer.txt'),'--pad',str(R/'fixtures/load-pad.txt'),'--period','10','--name','castle21-recoveredJ-NEW-cold-CardLoad'],check=True)
finally:
 try:observer.wait(timeout=3)
 except subprocess.TimeoutExpired:observer.terminate();observer.wait(timeout=3)
 assert hashlib.sha256(source.read_bytes()).hexdigest()==original_sha and hashlib.sha256(vm.read_bytes()).hexdigest()==original_sha,'Original VMU and immutable copy must remain unchanged'