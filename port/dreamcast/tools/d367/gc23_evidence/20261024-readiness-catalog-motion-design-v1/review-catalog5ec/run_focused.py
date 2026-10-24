from pathlib import Path
import sys,subprocess,resource,json,hashlib,time
resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,256*1024*1024));resource.setrlimit(resource.RLIMIT_CORE,(0,0))
out=Path('/mnt/c/Game Dev/Emulators/codex-lanes/gc-port23/review-catalog5ec');tests=Path('/dev/shm/gc-catalog-review5ec/source/port/dreamcast/tools/d367/gc_port23')
t=time.monotonic();p=subprocess.run([sys.executable,'-m','unittest','-v','test_catalog_defensive'],cwd=tests,capture_output=True,text=True)
log=p.stdout+p.stderr;(out/'focused-independent.log').write_text(log)
rec={'source':'5ec379b023a800a4e980108218b5242f4e2472ef','source_mode':'immutable git archive; original tests unchanged; git show uses existing read-only object database','command':['python3','-m','unittest','-v','test_catalog_defensive'],'exit':p.returncode,'seconds':time.monotonic()-t,'RLIMIT_AS_bytes':256*1024*1024,'compiler_jobs':1,'log_sha256':hashlib.sha256(log.encode()).hexdigest(),'scope':'host actual source functions with mocked providers, no SDK/guest/target'}
(out/'focused-independent.json').write_text(json.dumps(rec,indent=2)+'\n');print(log);assert p.returncode==0