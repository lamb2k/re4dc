"""Windows post-slot admission, then unchanged exact-child55 wrapper+harness."""
from pathlib import Path
import csv,hashlib,json,os,runpy,shutil,subprocess,sys,time
args=sys.argv[1:];cap=Path(args[args.index('--cap')+1]);assert not cap.exists()
assert os.environ.get('RE4DC_EMU')=='console'
assert os.environ.get('RE4DC_MAX_FLYCASTS')=='16' and os.environ.get('FP_NOLIMIT')=='1'
for k in ['RE4DC_GD_PROFILE','RE4DC_GD_JITTER','RE4DC_GD_SEED']:assert not os.environ.get(k),k
w=shutil.disk_usage('C:\\').free
l=int(subprocess.check_output(['wsl.exe','-d','Ubuntu-24.04','-u','root','--','python3','-c',"import shutil;print(shutil.disk_usage('/mnt/c').free)"],text=True).strip())
t=subprocess.check_output(['tasklist','/FI','IMAGENAME eq flycast.exe','/FO','CSV','/NH'],text=True,creationflags=subprocess.CREATE_NO_WINDOW)
n=sum(1 for r in csv.reader(t.splitlines()) if r and r[0].lower()=='flycast.exe');assert n<16
admit=dict(utc=time.time(),windows_free=w,wsl_free=l,lower_free=min(w,l),required=24*1024**3,flycast_count=n,environment={k:os.environ.get(k) for k in ['RE4DC_EMU','RE4DC_MAX_FLYCASTS','FP_NOLIMIT']},after_slots=True)
p=cap.parent.parent/'launches'/(cap.name+'-ADMISSION.json');p.parent.mkdir(parents=True,exist_ok=True)
with p.open('x') as f:json.dump(admit,f,indent=2)
assert min(w,l)>=24*1024**3,admit
bound=Path(r'C:\Game Dev\Emulators\codex-lanes\stat-bytes23\census-bound-run.py')
assert hashlib.sha256(bound.read_bytes()).hexdigest()=='e3f31e4a797b934543ac9e598a0e6350965533bdfe12299771200d11f183629c'
sys.argv=[str(bound),*args];runpy.run_path(str(bound),run_name='__main__')
