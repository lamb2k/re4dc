"""Rain-owned PREPARE/PREFLIGHT launcher. run requires a separate root grant; never builds or stages."""
from pathlib import Path
import argparse,fcntl,hashlib,json,os,subprocess
HERE=Path(__file__).resolve().parent
E=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/water-rain24/rain-bca44-console55-20261024');TREE=Path('/root/work/lanes/water-rain24');SOURCE='bca44d58a1fa0a51fd87ba94deba8cba925c8998'
HOST=Path('/mnt/c/Game Dev/Emulators/codex-lanes/stat-bytes23');D=TREE/'port/dreamcast/tools/d367';P='/mnt/c/Users/lambd/AppData/Local/Programs/Python/Python312/python.exe';FLOOR=24*1024**3

def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def verify_file(p,row):
 p=Path(p)
 if not p.is_file() or p.stat().st_size!=row['bytes'] or sha(p)!=row['sha256']:raise ValueError('pinned file drift: '+str(p))
def win(p):return subprocess.check_output(['wslpath','-w',str(p)],text=True,timeout=5).strip()
def require_grant(grant,preflight_sha,arm):
 expected={'source','preflight_sha256','root_approved','cases','maximum_guests','seconds'}
 if set(grant)!=expected or grant['source']!=SOURCE or grant['preflight_sha256']!=preflight_sha or grant['root_approved'] is not True or grant['cases']!=['off','on'] or grant['maximum_guests']!=2 or grant['seconds']!=45 or arm not in grant['cases']:raise ValueError('missing/wrong explicit root pair grant')
def validate():
 import shutil
 if shutil.disk_usage('/mnt/c').free<FLOOR:raise ValueError('C24GiB floor')
 if subprocess.check_output(['git','-C',str(TREE),'rev-parse','HEAD'],text=True).strip()!=SOURCE or subprocess.check_output(['git','-C',str(TREE),'status','--porcelain']):raise ValueError('canonical frozen source drift')
 if HERE!=E/'helpers':raise ValueError('use the frozen rain-owned E/helpers launcher')
 pre=E/'identities/launch-preflight.json';data=json.loads(pre.read_text())
 if data['source']!=SOURCE or not data['guests_blocked_pending_root_grant']:raise ValueError('wrong preflight scope')
 seen={}
 for path,row in data['pins'].items():
  p=Path(path);st=p.stat();key=(st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns)
  if key not in seen:verify_file(p,row);seen[key]=row
  elif seen[key]!=row:raise ValueError('hard-link identity conflict')
 for arm in ['off','on']:
  layout=json.loads((E/'identities'/(arm+'-g-source-layout.json')).read_text())
  if layout['source']!=SOURCE or layout['arm']!=arm:raise ValueError('wrong actual arm layout')
  actual=Path(data['arms'][arm]['out'])/'re4dc-game.elf'
  if sha(actual)!=layout['elf_sha256']:raise ValueError('layout/actual ELF mismatch')
 return data,pre

def command(arm,data):
 row=data['arms'][arm];cap=E/'captures'/(arm+'-r10c-view-v1');layout=E/'identities'/(arm+'-g-source-layout.json')
 cmd=['bash',str(HOST/'stat-guest-slot.sh'),'bash',str(D/'trace_lock.sh'),P,win(HOST/'census-bound-run.py'),win(HERE/'observe_canary.py'),win(D/'fullplay/fp_run.py'),win(layout),'10c','--base',win(row['base']),'--cap',win(cap),'--syms',row['syms'],'--warp',win(E/'fixtures/r10c-view.txt'),'--pad',win(E/'fixtures/neutral-pad.txt'),'--vmu',win(E/'capsules'/arm/'data/T0000_vmu_save_A1.bin'),'--seconds','45','--period','0','--stop','warp: frozen at tick 330','--grace','2','--name','rain-'+arm+'-view-v1']
 return cmd,cap

def main():
 ap=argparse.ArgumentParser();ap.add_argument('action',choices=['preflight','run']);ap.add_argument('arm',choices=['off','on']);a=ap.parse_args()
 data,pre=validate();cmd,cap=command(a.arm,data)
 if a.action=='preflight':print(json.dumps({'executed':False,'source':SOURCE,'preflight_sha256':sha(pre),'arm':a.arm,'command':cmd,'actual_guest_config':'not created; unchanged force_limited guard must publish exact prelaunch cfg before spawn','generic_disc_lint':'FAIL retained; exact virtual proxy mapping reviewed separately','actual_source_signature':'not observed yet; absent means UNEXERCISED','scope':'two limited view observations only; no lifecycle/owner/completed-scene/pixel PASS'},indent=2));return
 # No code in preparation creates this grant. A separate root decision is mandatory.
 grantpath=E/'ROOT-CANARY-GRANT.json'
 if not grantpath.is_file():raise ValueError('root preflight approval/grant missing; guest remains blocked')
 require_grant(json.loads(grantpath.read_text()),sha(pre),a.arm)
 with (E/'rain-owned-worker.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX)
  data,pre=validate();require_grant(json.loads(grantpath.read_text()),sha(pre),a.arm);cmd,cap=command(a.arm,data)
  ledgerpath=E/'attempts.json';ledger=json.loads(ledgerpath.read_text()) if ledgerpath.exists() else []
  if cap.exists() or any(x['arm']==a.arm for x in ledger) or len(ledger)>=2:raise ValueError('case already consumed/fresh capture required')
  env=dict(os.environ,RE4DC_EMU='console',FP_NOLIMIT='0',RE4DC_MAX_FLYCASTS='16',TRACE_SLOTS='16',TRACE_LOCK_OWNER='water-rain24-bca44-'+a.arm+'-view-v1',RE4DC_CONSOLE_EXE=r'C:\Flycast-Evidence\re4-dreamcast\flycast-console-bin\flycast-console.exe')
  for k in ['RE4DC_GD_PROFILE','RE4DC_GD_JITTER','RE4DC_GD_SEED','RE4DC_CONSOLE_DYNAREC']:env.pop(k,None)
  env['WSLENV']=':'.join(filter(None,[env.get('WSLENV',''),'RE4DC_EMU','FP_NOLIMIT','RE4DC_MAX_FLYCASTS','RE4DC_CONSOLE_EXE']))
  ledger.append({'arm':a.arm,'source':SOURCE,'preflight_sha256':sha(pre),'root_grant_sha256':sha(grantpath),'requested_seconds':45,'exact_child_cap_seconds':55,'command':cmd});ledgerpath.write_text(json.dumps(ledger,indent=2)+'\n')
  with (E/(a.arm+'-view-v1-launcher.log')).open('x') as out:result=subprocess.run(cmd,env=env,stdout=out,stderr=subprocess.STDOUT)
  print(json.dumps({'launcher_rc':result.returncode,'capture':str(cap),'automatic_visual_or_lifecycle_pass':False}));raise SystemExit(result.returncode)
if __name__=='__main__':main()