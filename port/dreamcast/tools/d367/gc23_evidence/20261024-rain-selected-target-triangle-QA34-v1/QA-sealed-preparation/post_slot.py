"""FUTURE Windows post-slot admission; no guest without a separate root grant."""
from pathlib import Path
import csv,hashlib,json,os,runpy,shutil,subprocess,sys,time
HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
gate=sys.argv[1];args=sys.argv[2:];assert gate in ('kos','h2')
seal=HERE/'TOOLCHAIN-SEAL.json';assert os.environ.get('GC_QA_GUEST_ALLOCATED')==sha(seal),'Separate root guest allocation required'
meta=json.loads(seal.read_text());grant=json.loads((HERE/'ROOT-GUEST-GRANT.json').read_text());assert grant.get('toolchain_sha256')==sha(seal) and gate in grant.get('gates',[])
if gate=='h2':assert grant.get('fresh_H2_exception') is True and grant.get('max_child_seconds')==300,'No historical long exception reuse'
cap=Path(args[args.index('--cap')+1]);assert not cap.exists()
assert os.environ.get('RE4DC_EMU')=='console' and os.environ.get('RE4DC_MAX_FLYCASTS')=='16' and os.environ.get('FP_NOLIMIT')=='1'
for k in ('RE4DC_GD_PROFILE','RE4DC_GD_JITTER','RE4DC_GD_SEED'):assert not os.environ.get(k),k
w=shutil.disk_usage('C:\\').free
l=int(subprocess.check_output(['wsl.exe','-d','Ubuntu-24.04','-u','root','--','/usr/bin/python3','-c',"import shutil;print(shutil.disk_usage('/mnt/c').free)"],text=True).strip())
t=subprocess.check_output(['tasklist','/FI','IMAGENAME eq flycast.exe','/FO','CSV','/NH'],text=True,creationflags=subprocess.CREATE_NO_WINDOW);n=sum(1 for r in csv.reader(t.splitlines()) if r and r[0].lower()=='flycast.exe');assert n<16
admit=dict(utc=time.time(),windows_free=w,wsl_free=l,lower_free=min(w,l),required=24*1024**3,flycast_count=n,console_env_verified=True,after_slots=True,gate=gate)
p=cap.parent/(cap.name+'-ADMISSION.json');p.parent.mkdir(parents=True,exist_ok=True)
with p.open('x') as f:json.dump(admit,f,indent=2)
assert min(w,l)>=24*1024**3,admit
bound=HERE/'h2-bound-run.py' if gate=='h2' else Path(r'C:\Game Dev\Emulators\codex-lanes\stat-bytes23\census-bound-run.py')
expected=meta['members']['h2-bound-run.py']['sha256'] if gate=='h2' else meta['external_tools']['exact_child55']['identity']['sha256'];assert sha(bound)==expected
sys.argv=[str(bound),*args];runpy.run_path(str(bound),run_name='__main__')
