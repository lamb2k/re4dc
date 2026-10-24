from pathlib import Path
import sys,types,json,hashlib,subprocess,resource,time
R=Path('/mnt/c/Game Dev/Emulators/codex-lanes/gc-motion24/full-h2-prep-v1');m=types.ModuleType('h2_core');m.__file__=str(R/'core.py');exec(compile((R/'core.py').read_bytes(),m.__file__,'exec'),m.__dict__)
g=dict(approved=False,authorization='ONE_DIAGNOSTIC_427_FULL_H2_PAIR',source=m.SOURCE,off_actual_producer_source=m.OFF_SOURCE,raw=m.RAW,arm_order=['off','on'],actual_child_seconds=300,harness_seconds=290,grace=5,user_allowance_question='call_893faf52f48b4286ba0eb3333782ea2c',KOS_first=True,final=str(m.FINAL),root_slots=3,global_slots=16,KOS_results=[],parent_kit={'path':'UNBOUND_FINAL_REVIEWED_SUCCESSOR_REQUIRED','identity':{}},parent_independent_CLEAR={'status':'CLEAR_SOURCE_AND_BINDING','path':'UNBOUND','identity':{}},poststage={'path':'UNBOUND','identity':{}},arms={})
for a,b in [('off','/mnt/c/Flycast-Evidence/re4-dreamcast/rain-diag24-20261024/_qa-media-8ce-recovery-v4/base-off'),('on','/mnt/c/Flycast-Evidence/re4-dreamcast/gc-motion24-20261024/kos-budget-retest-media-v2/on')]:g['arms'][a]=dict(base=b,syms='UNBOUND_ACTUAL_ELF_SYMBOLS',raw={'path':'UNBOUND','identity':{'sha256':m.RAW[a]}},elf={'path':'UNBOUND','identity':{'sha256':m.ELF[a]}})
(R/'ROOT-GRANT-TEMPLATE.json').write_text(json.dumps(g,indent=2)+'\n')
def limit():resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,256*1024**2));resource.setrlimit(resource.RLIMIT_CORE,(0,0))
start=time.monotonic()
with (R/'HOST-CONTROLS.log').open('x') as f:p=subprocess.run(['/usr/bin/python3','-B','-E','-X','pycache_prefix=/dev/shm/h2prep-final-host-cache',str(R/'test_host.py')],stdout=f,stderr=subprocess.STDOUT,timeout=120,preexec_fn=limit)
(R/'HOST-CONTROLS.json').write_text(json.dumps(dict(returncode=p.returncode,tests=16,seconds=time.monotonic()-start,RAM_limit_bytes=256*1024**2,timeout_seconds=120,SDK_stage_guest=False),indent=2)+'\n');assert p.returncode==0
print((R/'HOST-CONTROLS.json').read_text())