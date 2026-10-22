"""Read sealed Git blobs and receipts only; no owner worktree mutation/test execution."""
from pathlib import Path
import subprocess,json,hashlib,re
T=Path('/root/probe/codex-issue52-rootpose23-review')
OUT=T/'codex-review/issue52-rootpose23/DAMCAUSE-543-review.json'
BASE='64a28a7bdc44312924b14414501b7d4ff1d2d032';TIP='543c55f17dbd437e3453434224dea337725ebb73'
g=lambda *a:subprocess.check_output(['git','-C',str(T),*a])
blob=lambda rev,p:g('show',rev+':'+p)
H=lambda b:hashlib.sha256(b).hexdigest()
P='port/dreamcast/tools/d367/damcause23/'
h=json.loads(blob(TIP,P+'diagnostic-host-receipt.json'));w=json.loads(blob(TIP,P+'actual-wiring02.json'))
assert h['base']==BASE
pins=[]
for row in h['source_pins']:
 assert H(blob(BASE,row['path']))==row['before_sha256']
 assert H(blob(TIP,row['path']))==row['after_sha256']
 pins.append(row)
for row in h['source_task_pins']:
 assert blob(BASE,row['path'])==blob(TIP,row['path'])
 assert H(blob(TIP,row['path']))==row['sha256']
assert H(blob(TIP,P+'qualify-diagnostics.py'))==h['runner_sha256']
assert w['prior_host_receipt_sha256']==H(blob(TIP,P+'diagnostic-host-receipt.json'))
assert w['prior_host_source_pins_all_match']
assert len(h['disabled_preprocessor_controls'])==14
assert all(row['exact']for row in h['disabled_preprocessor_controls'])
assert w['disabled_parity_controls']==h['disabled_preprocessor_controls']
assert len(w['results'])==7
assert {r['variant']for r in w['results']}=={'default','zero','one','invalid','no_crash','no_stage','no_route'}
for row in w['results']:
 assert(row['exit']==0)==(row['variant']in['default','zero','one'])
assert H(blob(TIP,'port/dreamcast/game/game30.mk'))==w['game30_sha256']
assert H(blob(TIP,'port/dreamcast/game/Makefile'))==w['makefile_sha256']
assert blob(TIP,'port/dreamcast/game/Makefile')==blob(BASE,'port/dreamcast/game/Makefile')
for p in ['include/cManager.h','src/st1/r10c.cpp','port/dreamcast/game/platform/modules.cpp']:
 assert blob(BASE,p)==blob(TIP,p)
def fn(s,start):
 a=s.index(start);b=s.index('{',a);depth=1;i=b+1
 while depth:
  depth+=(s[i]=='{')-(s[i]=='}');i+=1
 return s[a:i]
old=blob(BASE,'src/game/em_set.cpp').decode();new=blob(TIP,'src/game/em_set.cpp').decode()
assert fn(old,'static cEm* emMustCreate(')==fn(new,'static cEm* emMustCreate(')
code=blob(TIP,P+'qualify-diagnostics.py').decode()
assert 'source_task=0x1111;'in code and 'using u32 = unsigned long;'in code
assert len(h['host'])==3
for r in h['host']:
 assert r['stdout'][0]['scenarios']==13
assert h['host'][0]['stdout'][0]==h['host'][1]['stdout'][0]==h['host'][2]['stdout'][0]
on=next(r for r in h['host']if r['variant']=='enabled')
assert on['stdout'][1]['collector_controls']==15
out={'scope':'INDEPENDENT_SOURCE_AND_RETAINED_RECEIPT_REVIEW_ONLY','base':BASE,'reviewed_tip':TIP,'source_pins_verified':pins,'host_receipt_sha256':H(blob(TIP,P+'diagnostic-host-receipt.json')),'actual_wiring_receipt_sha256':H(blob(TIP,P+'actual-wiring02.json')),'host_counts_read_not_rerun':{'scenarios_each':13,'variants':3,'collector_controls':15,'disabled_source_comparisons':14,'actual_Make_controls':7},'behavior_fingerprint':on['stdout'][0]['behavior_fingerprint'],'no_concrete_source_blocker_found':True,'unchanged_contracts':['emMustCreate','cManager.h','r10c.cpp','modules.cpp','Makefile','scheduler.cpp','sce_sys.cpp','scheduler.h'],'not_proved':['fullTU/SH4/target linker','real scheduler/task-slot lifetime','actual native module bind or I/O','Flycast guest','physical Test21 cause'],'no_test_rerun_or_native_query_or_guest':True}
assert not OUT.exists();OUT.write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({'receipt':str(OUT),'sha256':H(OUT.read_bytes()),'counts':out['host_counts_read_not_rerun'],'fingerprint':out['behavior_fingerprint']}))

