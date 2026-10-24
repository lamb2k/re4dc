"""Exact root-grant-only serial OFF then ON host observer. No SDK/guest."""
from pathlib import Path
import json,time,signal,shutil,os
import common as c
import future_master as fm
HERE=Path(__file__).resolve().parent

def resources(plan,admission=True):
 mem=[x.split() for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')]
 if len(mem)!=1 or len(mem[0])!=3 or mem[0][2]!='kB' or not mem[0][1].isdigit():raise ValueError('Invalid MemAvailable')
 physical=int(mem[0][1])*1024;tmpfs=shutil.disk_usage('/dev/shm').free
 return {'C':fm.floor(plan['capacity']['C_admission_bytes' if admission else 'C_floor_bytes']),'tmpfs_available_bytes':tmpfs,'MemAvailable_bytes':physical,'lower_RAM_bytes':min(tmpfs,physical),'ext4':fm.require_ext4(Path(plan['work_paths']['off']).parent),'release_active':c.release_active()}

def main(selection):
 if selection not in ['off','on','all'] or os.environ.get('RAIN_QA_STAGE_ARMS')!=selection:raise ValueError('Exact root arm scope required')
 selected=['off','on'] if selection=='all' else [selection]
 plan=c.verify_kit('stage');c.verify_inputs(plan)
 for group in ['base_paths','work_paths']:
  for arm in selected:
   path=plan[group][arm];fm.absolute_fresh(path,Path(path).parent)
 before=resources(plan)
 if before['release_active']:raise ValueError('Release priority')
 print(json.dumps({'ROOT_SERIAL_STAGE_ADMISSION':before,'selected_arms':selected,'jobs':1,'source':plan['source']},sort_keys=True),flush=True)
 parent=Path(plan['base_paths']['off']).parent;results={};started=time.monotonic()
 def deadline(sig,frame):raise RuntimeError('600s arm deadline; preserve owned attempt')
 old=signal.signal(signal.SIGALRM,deadline)
 try:
  for arm in selected:
   armstart=time.monotonic();signal.setitimer(signal.ITIMER_REAL,600)
   try:fm.main(arm)
   finally:signal.setitimer(signal.ITIMER_REAL,0)
   receipt=c.read(Path(plan['base_paths'][arm])/'COMPLETE.json')
   if receipt['status']!='STAGED_READBACK_PASS_GUEST_PENDING' or not receipt['all14_exact'] or not receipt['assets_exact']:raise ValueError('Arm incomplete '+arm)
   results[arm]={'elapsed_seconds':time.monotonic()-armstart,'receipt':str(Path(plan['base_paths'][arm])/'COMPLETE.json'),'receipt_pin':c.row(Path(plan['base_paths'][arm])/'COMPLETE.json'),'programme':receipt['programme'],'tracks':receipt['tracks']}
  fm.fresh(parent/('ROOT-STAGE-'+selection.upper()+'-RESULT.json'),{'status':'SELECTED_ARMS_STAGED_READBACK_PASS_NO_GUEST','selected_arms':selected,'source':plan['source'],'seal_sha256':c.sha(HERE/'TOOLCHAIN-SEAL.json'),'plan_sha256':c.sha(HERE/'PLAN.json'),'arms':results,'elapsed_seconds':time.monotonic()-started,'before':before,'after':resources(plan,False),'owned_bytes':fm.owned_bytes([parent,Path(plan['work_paths']['off']).parent]),'SDK_guest':False})
  # Pair sealing is conditional on both actual current-seal completions. No wait/retry.
  pair={}
  for a in ['off','on']:
   path=Path(plan['base_paths'][a])/'COMPLETE.json'
   if not path.exists():continue
   r=c.read(path)
   if r.get('tool_seal_sha256')!=c.sha(HERE/'TOOLCHAIN-SEAL.json') or r.get('plan_sha256')!=c.sha(HERE/'PLAN.json') or r.get('source')!=plan['source'] or r.get('programme')!=plan['programmes'][a]['program.bin']['sha256'] or not r.get('all14_exact') or not r.get('assets_exact') or r.get('status')!='STAGED_READBACK_PASS_GUEST_PENDING':raise ValueError('Foreign/incomplete prior arm '+a)
   if {n:c.row(path.parent/n) for n in fm.TRACKS}!=r['tracks']:raise ValueError('Changed completed track '+a)
   pair[a]={'receipt':str(path),'pin':c.row(path),'tracks':r['tracks']}
  if set(pair)=={'off','on'}:fm.fresh(parent/'ROOT-STAGED-PAIR-RESULT.json',{'status':'BOTH_ACTUAL_ARMS_STAGED_READBACK_PASS_NO_GUEST','arms':pair,'seal_sha256':c.sha(HERE/'TOOLCHAIN-SEAL.json'),'source':plan['source']})
 except BaseException as e:
  if parent.is_dir() and not parent.is_symlink():fm.fresh(parent/('ROOT-STAGE-'+selection.upper()+'-FAILED.json'),{'status':'FAILED_PRESERVED_NO_RETRY','error':repr(e),'completed_arms':results,'elapsed_seconds':time.monotonic()-started})
  raise
 finally:
  signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,old)
if __name__=='__main__':raise SystemExit('Use authenticated launch.py serial-stage off|on|all')
