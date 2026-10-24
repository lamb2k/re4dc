from pathlib import Path
import subprocess,json,hashlib,time,resource
R=Path('/mnt/c/Game Dev/Emulators/codex-lanes/gc-motion24/full-h2-prep-v2')
def limit():resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,256*1024**2));resource.setrlimit(resource.RLIMIT_CORE,(0,0))
for f in ['test_host.py','test_repairs.py']:
 t=time.monotonic()
 with (R/(f+'.final.log')).open('x') as out:p=subprocess.run(['/usr/bin/python3','-B','-E','-X','pycache_prefix=/dev/shm/h2-v2-final-'+f,str(R/f)],stdout=out,stderr=subprocess.STDOUT,timeout=120,preexec_fn=limit)
 assert p.returncode==0;print(f,p.returncode,time.monotonic()-t)
# Recheck all parent pins after final controls and regenerate only preparation-owned delta metadata.
subprocess.run(['/usr/bin/python3','-B','-E',str(R/'preserve.py')],check=True)