"""Copy verified controller source and prepare four fixed pending recovery cases."""
from pathlib import Path
import hashlib,json,sys
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'kos-budget-retest-guest-prep-v1'
PLAN=HERE.parent/'kos-budget-retest-guest-prep-v2'
def row(raw):return dict(size=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def read(p):return json.loads(Path(p).read_bytes())
def write(n,raw):
 with (HERE/n).open('xb') as f:f.write(raw)
def fresh(n,j):write(n,(json.dumps(j,indent=1)+'\n').encode())
if __name__=='__main__':
 if not (__debug__ and sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode):raise SystemExit('Use isolated nonoptimized source')
 assert row((OLD/'TOOLCHAIN-SEAL.json').read_bytes())==dict(size=3857,sha256='7b5120956b13f1d25f50280120686a8efe45ed70f09ca14042722cb4eaa9997e')
 for n,v in read(OLD/'TOOLCHAIN-SEAL.json')['members'].items():assert row((OLD/n).read_bytes())==v
 assert row((PLAN/'PLAN-SEAL.json').read_bytes())==dict(size=1753,sha256='b6e24101a8e1889f278f48a1603384f87efa6a8445fe750f79b51860210e053b')
 for n in ['controller.py','post_slot.py','launch.py','windows_entry.py','owned_process.py','judge.py','INPUT-PINS.json']:
  write(n,(OLD/n).read_bytes())
 j=read(OLD/'PLAN.json');j['status']='EXECUTABLE_SOURCE_PENDING_ACTUAL_OFF_AND_CURRENT_BASELINE_NO_GRANT';j['media_binding']='RECOVERY-BINDING.json required, absent until root handback';j['metadata_roots']=[str(HERE.parent/n) for n in ['kos-budget-retest-stage-root-v1','review-kos-budget-retest-media-poststage-v2','kos-budget-retest-guest-root-review-v2']]
 final='/mnt/c/Flycast-Evidence/re4-dreamcast/gc-motion24-20261024/kos-budget-retest-guest-v2'
 def win(s):return 'C:\\'+s[7:].replace('/','\\')
 for c in j['cases']:
  c['name']='recovery427-'+c['arm']+'-49152-'+str(c['fragment']);c['cap_WSL']=final+'/captures/'+c['name'];c['cache_WSL']=final+'/cache/'+c['name']
  base='/mnt/c/Flycast-Evidence/re4-dreamcast/rain-diag24-20261024/_qa-media-8ce-recovery-v4/base-off' if c['arm']=='off' else '/mnt/c/Flycast-Evidence/re4-dreamcast/gc-motion24-20261024/kos-budget-retest-media-v2/on'
  argv=c['argv'];argv[5:10]=['-I','-S','-B','-X','pycache_prefix='+win(c['cache_WSL'])]
  for flag,value in [('--base',win(base)),('--cap',win(c['cap_WSL'])),('--name',c['name'])]:argv[argv.index(flag)+1]=value
  c['base_WSL']=base;c['actual_media_identity']='UNKNOWN_UNTIL_ROOT_HANDOFF_AND_FULL_READBACK'
 fresh('PLAN.json',j)
 fresh('ROOT-GUEST-GRANT-TEMPLATE.json',dict(approved=False,authorization='FOUR_KOS48_CORRECTED427_CONSOLE_ONLY',scope='CAPTURES_AND_BOUNDED_KOS_JUDGEMENT_ONLY',source='427784b1f48aa30742850bb5025925ab619b740e',kit_sha256='ROOT_PIN_FINAL_BOUND_TOOLCHAIN_SEAL',media_kit_sha256='2301e39cfb166ee25bab261f0323d1df27331155148b67453bc527ce7330bee1',recovery_context='EXPLICIT_NEW_CURRENT_BASELINE_NO_OLD_HASH_RESTORATION',case_order=[0,1,2,3],seconds=45,exact_child_seconds=55,parent_seconds=95,admission_seconds=180,overall_seconds=1300,new_delta_cap=5*1024**3//4,aggregate_cap=13*1024**3//2,root_slots=3,global_slots=16,H2=False,poststage=dict(path=str(HERE.parent/'review-kos-budget-retest-media-poststage-v2/FINAL-READBACK.json'),identity=None),metadata_allowlists={p:[] for p in j['metadata_roots']}))
 fresh('SOURCE-LINEAGE.json',dict(predecessor_guest_seal=row((OLD/'TOOLCHAIN-SEAL.json').read_bytes()),pending_plan_seal=row((PLAN/'PLAN-SEAL.json').read_bytes()),unchanged={n:row((OLD/n).read_bytes()) for n in ['controller.py','post_slot.py','launch.py','windows_entry.py','owned_process.py','judge.py','INPUT-PINS.json']},OFF_producer='8ce5ee2d00027268c3e69c9c300b819c1b14c63f',OFF_actual_identity=None,baseline=None,source_and_host_only=True))
