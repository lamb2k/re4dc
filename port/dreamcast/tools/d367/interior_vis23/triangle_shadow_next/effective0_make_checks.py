#!/usr/bin/env python3
"""No-SDK exact Make option/default/target-local prerequisite controls."""
import argparse,hashlib,json,resource,subprocess,tempfile
from pathlib import Path

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--source-tree',required=True,type=Path);ap.add_argument('--out',required=True,type=Path);a=ap.parse_args()
 if a.out.exists():raise ValueError('Preserve prior controls')
 resource.setrlimit(resource.RLIMIT_AS,(268435456,268435456));mk=a.source_tree/'port/dreamcast/game/t2exact.mk';scenery=mk.with_name('scenery19.mk');old=subprocess.check_output(['git','-C',str(a.source_tree),'show','18caa03ca:port/dreamcast/game/t2exact.mk'],text=True);records=[]
 base={'OBJDIR':'out','PS2_WORLD_ROOMS':'1','MESH_LOD':'1','PS2_WORLD_NONEMPTY_LOD':'1','PS2_PVS':'1'}
 with tempfile.TemporaryDirectory(prefix='iv23-effective0-make-',dir='/dev/shm') as temp:
  temp=Path(temp);(temp/'old.mk').write_text(old)
  def invoke(label,overrides,target='out/platform/native_static.o',expect=True,legacy=False,batch=False):
   values=dict(base);values.update(overrides);harness=temp/(label+'.mk');source=temp/'old.mk' if legacy else mk
   text='include '+str(source)+'\n'
   if batch:text+='include '+str(scenery)+'\n'
   text+=target+":\n\t@printf '%s\\n' '$(PLATFORM_CPPFLAGS)|$(GAME_CPPFLAGS)'\n";harness.write_text(text)
   run=subprocess.run(['make','--no-print-directory','-f',str(harness),target]+[k+'='+v for k,v in values.items()],capture_output=True,text=True)
   if (run.returncode==0)!=expect:raise ValueError('Unexpected Make outcome '+label+run.stdout+run.stderr)
   records.append(dict(label=label,returncode=run.returncode,stdout=run.stdout,stderr=run.stderr))
   return run
  for pvs in ('0','1'):
   now=invoke('default-pvs'+pvs,{'PS2_PVS':pvs});prior=invoke('old-pvs'+pvs,{'PS2_PVS':pvs},legacy=True)
   if now.stdout!=prior.stdout:raise ValueError('Default flag identity failed')
   now=invoke('explicit-off-pvs'+pvs,{'PS2_PVS':pvs,'PS2_PVS_EFFECTIVE0_SOURCES':'0'})
   if now.stdout!=prior.stdout:raise ValueError('Explicit OFF flag identity failed')
  good=invoke('enabled',{'PS2_PVS_EFFECTIVE0_SOURCES':'1'})
  if '-DRE4DC_PS2_PVS_EFFECTIVE0_SOURCES=1' not in good.stdout:raise ValueError('Missing target feature define')
  for target in ('out/platform/native_ui.o','out/dbgwarp_bridge.o','out/unrelated.o'):
   run=invoke('local-'+target.split('/')[-1],{'PS2_PVS_EFFECTIVE0_SOURCES':'1'},target=target)
   if 'RE4DC_PS2_PVS_EFFECTIVE0_SOURCES' in run.stdout:raise ValueError('Feature leaked to another object')
  for value in ('2','-1','foo',''):
   invoke('bad-value-'+str(len(records)),{'PS2_PVS_EFFECTIVE0_SOURCES':value},expect=False)
  for key,value in (('PS2_PVS','0'),('MESH_LOD','0'),('PS2_WORLD_NONEMPTY_LOD','0'),('PS2_WORLD_ROOMS','0'),('PS2_WORLD_ROOMS','3')):
   invoke('missing-'+key+'-'+value,{'PS2_PVS_EFFECTIVE0_SOURCES':'1',key:value},expect=False)
  for rooms in ('1','2'):invoke('rooms'+rooms,{'PS2_PVS_EFFECTIVE0_SOURCES':'1','PS2_WORLD_ROOMS':rooms})
  batch=invoke('batch-pvs-still-refused',{'PS2_PVS_EFFECTIVE0_SOURCES':'1','SCENERY_SUBMIT_BATCH':'1','SCENERY_CHUNK':'1','PS2_STRIP_GROUPS':'1','TA_DIRECT':'1','MESH_DIRECT':'1','PS2_WORLD_MESH':'1','PS2_WORLD_HDR_CACHE':'1','WORLD_SCRATCH':'0','TA_GUARD':'0'},expect=False,batch=True)
  if 'SCENERY_SUBMIT_BATCH does not yet qualify PS2_PVS' not in batch.stderr:raise ValueError('Existing batching refusal changed')
 out=dict(kind='No-SDK source Make controls only; no programme/binary identity claim',tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),make_sha256=hashlib.sha256(mk.read_bytes()).hexdigest(),scenery_guard_sha256=hashlib.sha256(scenery.read_bytes()).hexdigest(),cases=records,default_and_off_flags_identical=True,target_local=True,existing_batching_rejection_preserved=True,runtime_admitted_cuts=0)
 with a.out.open('x') as dst:json.dump(out,dst,indent=1);dst.write('\n')
 print(json.dumps(out))
if __name__=='__main__':main()
