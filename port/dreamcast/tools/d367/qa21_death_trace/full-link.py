#!/usr/bin/env python3
"""Plan or run one allocated trace-enabled link; never stages an image or restores states."""
import argparse,hashlib,json,os,shlex,shutil,signal,subprocess,time
from pathlib import Path
from overlay_identity import elf_text,overlay_bytes
BASE=Path('/root/probe/codex-qa21-combined-regression');TRACE=Path('/root/probe/codex-qa21-death-trace');R=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/qa21-combined-regression-20261021')
START=18*1024**3+640*1024**2;FLOOR=18*1024**3+64*1024**2;CAP=320*1024**2;LOG_CAP=8_000_000
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execute-link',action='store_true');p.add_argument('--execute-enabled-link',action='store_true');p.add_argument('--arm',choices=['off','on'],default='on');p.add_argument('--job',type=Path);a=p.parse_args();a.job=a.job or Path('/root/probe/qa21-death-trace-full-'+a.arm+'-20261021');assert a.job.parent==Path('/root/probe') and a.job.name.startswith('qa21-death-trace-full-');JOB=a.job;VIEW=JOB/'source-view';OUT=JOB/'enabled'
def sha(path):
 with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def git(root,*args):return subprocess.check_output(['git',*args],cwd=root,text=True).strip()
def tree_files(root):
 rows={}
 if root.exists():
  for folder,dirs,files in os.walk(root,followlinks=False):
   for name in files:
    q=Path(folder)/name
    if q.is_file():rows[str(q.relative_to(root))]={'bytes':q.stat().st_size,'sha256':sha(q)}
 return rows
def owned_size():
 total=0
 for root in (JOB,TRACE):
  if not root.exists():continue
  for folder,dirs,files in os.walk(root,followlinks=False):
   for name in files+dirs:
    st=(Path(folder)/name).lstat();total+=max(st.st_size,st.st_blocks*512)
 return total
def stop_build_reason(free, used, log_bytes, elapsed):
 if free<FLOOR:return 'C18GiB+64MiB runtime floor'
 if used>=CAP:return '320MiB incremental tree+output cap'
 if log_bytes>=LOG_CAP:return '8MB owned log cap'
 if elapsed>=600:return '600s owned build cap'
 return None
unit=json.loads((TRACE/'port/dreamcast/tools/d367/qa21_death_trace/source-unit-receipt-20261021.json').read_text());assert all(sha(TRACE/name)==digest for name,digest in unit['trace_files'].items())
assert git(BASE,'rev-parse','HEAD')=='e2ae49d16818b133b5eb1c94cdfed7f7e608c448';assert not git(BASE,'status','--porcelain');assert not git(TRACE,'status','--porcelain')
control=R/'builds/qa-control';recipe=control/'candidate.txt';knobs=shlex.split(recipe.read_text());assert 'QA_MENU=1' in knobs and 'PAUSE_NATIVE_PRESENTATION=0' in knobs and 'GAME_SH4ZAM=1' in knobs;assert not any(k.startswith('DEATH_TRACE=') or k=='SS_WINDOW_HOLD_RESTORE=1' for k in knobs);knobs+=['DEATH_TRACE='+str(int(a.arm=='on'))]
# The previous exact recipe retained these measured bytes, before a transient overlay ELF/source metadata.
estimate={'prior_compiled_objects':187069626,'prior_link_scratch':49748731,'prior_complete_output':34057070,'temporary_overlay_ELF_allowance':29427116,'source_view_log_trace_allowance':16*1024**2};estimated_peak=sum(estimate.values());assert estimated_peak<CAP
plan={'scope':'Allocated serial full OFF identity / ON link; no stage, cleanup or saved-state restore','arm':a.arm,'trace_runtime_source':'f99dc69ad8bfeebcdb10913443543514dc40f9cc','trace_tools_HEAD':git(TRACE,'rev-parse','HEAD'),'frozen_source_HEAD':git(BASE,'rev-parse','HEAD'),'frozen_runtime_source':'6f9d31b0e00497a75fdd7e25bb04f92305103087','trace_files':unit['trace_files'],'recipe_sha256':sha(recipe),'compiler_sha256':sha('/opt/toolchains/dc/sh-elf/bin/sh-elf-g++'),'KOSlib_sha256':sha('/root/work/kos-re4dc-d367/lib/dreamcast/libkallisti.a'),'submodule':git(BASE,'submodule','status'),'knobs':knobs,'job':str(JOB),'source_view':'Read-only frozen dependencies linked into a small owned view; only three trace sources and trace Makefile overlay; game/obj and platform/sdk/gen are private writable destinations','resource':{'fresh_C_bytes':shutil.disk_usage('/mnt/c').free,'start_floor':START,'runtime_floor':FLOOR,'incremental_tree_output_cap':CAP,'footprint_accounting':'Per-entry max(logical bytes, allocated blocks), including directory blocks; source symlinks are not followed','log_cap':LOG_CAP,'estimate_components':estimate,'estimated_peak':estimated_peak},'full_trace_OFF_gate':{'status':'NOT RUN; requires its own later allocation','recipe':'Same pinned QA control recipe with DEATH_TRACE=0 in an independent output tree; no object/output mutation or state sharing','expected_raw':'5c5a6c434751b03a0aaa05d8e2478820ca82a3790d7c3b06799f7845d6c5f68b','expected_all14_overlays':'Exact retained qa-control receipt','ELF_note':'Full ELF debug/path identity is recorded separately; raw program plus all14 overlays are the control gate; existing g0 unit identity is not a full-program gate'},'stage_status':'UNALLOCATED. Separate standalone image copy/patch and all-file verification plan; no image hardlinks or extracted asset tree.'}
if not (a.execute_link or a.execute_enabled_link):
 plan['admission']='PASS' if plan['resource']['fresh_C_bytes']>=START else 'REFUSED before job output';print(json.dumps(plan,indent=2));raise SystemExit(0)
assert plan['resource']['fresh_C_bytes']>=START,'Refused before output: unchanged18GiB+640MiB admission';assert not JOB.exists(),'Preserve existing job'
frozen_scratch=tree_files(BASE/'port/dreamcast/game/obj');frozen_sdk=tree_files(BASE/'port/dreamcast/game/platform/sdk/gen')
# Recheck after read-only identities, before making any job output.
assert shutil.disk_usage('/mnt/c').free>=START,'Refused before output after source hashing'
JOB.mkdir();OUT.mkdir();(OUT/'obj').mkdir();(OUT/'link-scratch').mkdir()
overrides={'.git':TRACE/'.git','src/game/em_sub.cpp':TRACE/'src/game/em_sub.cpp','src/game/pl_dmg.cpp':TRACE/'src/game/pl_dmg.cpp','src/game/game.cpp':TRACE/'src/game/game.cpp','port/dreamcast/game/Makefile':TRACE/'port/dreamcast/game/Makefile','port/dreamcast/game/obj':OUT/'link-scratch','port/dreamcast/game/platform/sdk/gen':None,'port/dreamcast/tools/d367/qa21_death_trace':TRACE/'port/dreamcast/tools/d367/qa21_death_trace'}
def mirror(rel=''):
 dst=VIEW/rel;dst.mkdir()
 for child in (BASE/rel).iterdir():
  name=(Path(rel)/child.name).as_posix();target=dst/child.name
  if name in overrides:
   if overrides[name] is None:target.mkdir()
   else:target.symlink_to(overrides[name],target_is_directory=overrides[name].is_dir())
  elif any(k.startswith(name+'/') for k in overrides):mirror(name)
  else:target.symlink_to(child,target_is_directory=child.is_dir())
 # sdk/gen may not exist in a pristine frozen dependency tree.
 for name,value in overrides.items():
  if str(Path(name).parent).replace('\\','/')==rel and not (VIEW/name).exists() and not (VIEW/name).is_symlink():
   if value is None:(VIEW/name).mkdir()
   else:(VIEW/name).symlink_to(value,target_is_directory=value.is_dir())
mirror();assert (VIEW/'port/dreamcast/game/obj').resolve()==(OUT/'link-scratch').resolve();assert (VIEW/'port/dreamcast/game/platform/sdk/gen').resolve()!= (BASE/'port/dreamcast/game/platform/sdk/gen').resolve()
for name,digest in unit['trace_files'].items():assert sha(VIEW/name)==digest
(OUT/'candidate.txt').write_text(' '.join(knobs)+'\n');(JOB/'preflight.json').write_text(json.dumps(plan,indent=2)+'\n')
env=os.environ.copy();env.update(TREE=str(VIEW),ROUTE_OUT_ROOT=str(JOB),ROUTE_PROGRAMS_DIR=str(JOB/'programs'),ROUTE_PROGRAMS_JSON='',SOURCE_DATE_EPOCH='1760000000',ASSETS='/root/probe/lanes/play-actor-bundle',OBJDIR=str(OUT/'obj'),OUT=str(OUT),JOBS='4',PYTHONDONTWRITEBYTECODE='1')
cmd=['bash','/root/probe/d367-buildslot.sh','bash',str(VIEW/'port/dreamcast/tools/d367/build-r21.sh'),*knobs];log=OUT/'build.log';started=time.monotonic();guard=None;peak=owned_size();min_free=shutil.disk_usage('/mnt/c').free
with log.open('xb') as stream:
 child=subprocess.Popen(cmd,cwd=VIEW,env=env,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True);start=Path('/proc/'+str(child.pid)+'/stat').read_text().split()[21];owned={'pid':child.pid,'pgid':os.getpgid(child.pid),'proc_start':start,'argv':cmd,'scope':'Only this owned process group may be stopped'};(JOB/'owned-build.json').write_text(json.dumps(owned,indent=2)+'\n')
 while child.poll() is None:
  used=owned_size();free=shutil.disk_usage('/mnt/c').free;peak=max(peak,used);min_free=min(min_free,free)
  guard=stop_build_reason(free,used,log.stat().st_size,time.monotonic()-started)

  if guard:
   assert Path('/proc/'+str(child.pid)+'/stat').read_text().split()[21]==start and os.getpgid(child.pid)==child.pid;os.killpg(child.pid,signal.SIGTERM)
   try:child.wait(timeout=8)
   except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
   break
  time.sleep(.25)
 rc=child.wait()
assert frozen_scratch==tree_files(BASE/'port/dreamcast/game/obj'),'Frozen link scratch changed';assert frozen_sdk==tree_files(BASE/'port/dreamcast/game/platform/sdk/gen'),'Frozen SDK generated sources changed';assert not git(BASE,'status','--porcelain')
assert all(sha(TRACE/name)==digest for name,digest in unit['trace_files'].items())
assert sha('/root/work/kos-re4dc-d367/lib/dreamcast/libkallisti.a')==plan['KOSlib_sha256']
result={'source':plan,'process':owned,'returncode':rc,'guard':guard,'seconds':round(time.monotonic()-started,4),'peak_incremental_bytes':max(peak,owned_size()),'minimum_free_C_bytes':min_free,'frozen_scratch_and_sdk_preserved':True}
if rc or guard:
 (JOB/'failed.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'status':'FAILED','code':rc,'guard':guard,'job':str(JOB)}));raise SystemExit(rc or 2)
elf=OUT/'re4dc-game.elf';raw=OUT/'program.bin';subprocess.run(['/opt/toolchains/dc/sh-elf/bin/sh-elf-objcopy','-R','.stack','-O','binary',str(elf),str(raw)],check=True);assert owned_size()<CAP
files={f.name:{'bytes':f.stat().st_size,'sha256':sha(f)} for f in [elf,raw,*sorted(OUT.glob('*.ovl'))]};assert len(files)==16
control_files=json.loads((control/'receipt.json').read_text())['files'];text=elf_text(elf);overlay_rows={}
for f in sorted(OUT.glob('*.ovl')):
 row=overlay_bytes(f.read_bytes(),text);row['control_sha256']=control_files[f.name]['sha256'];row['same_as_control']=row['sha256']==row['control_sha256'];old=(control/f.name).read_bytes();new=f.read_bytes();row['difference_scope']='identical' if old==new else ('main-text-binding-only' if old[:56]==new[:56] and old[64:]==new[64:] else 'binding-and/or-payload; linked resident references require review');overlay_rows[f.name]=row
resolved=dict(line.split('=',1) for line in (OUT/'resolved-knobs.txt').read_text().splitlines() if '=' in line)
for name,value in {'DEATH_TRACE':str(int(a.arm=='on')),'QA_MENU':'1','PAUSE_NATIVE_PRESENTATION':'0','GAME_SH4ZAM':'1','SKIN_SH4ZAM':'0'}.items():assert resolved[name]==value
assert resolved.get('SS_WINDOW_HOLD_RESTORE','0')=='0'
commands=[line for line in log.read_text().splitlines() if line.startswith('kos-c++ ') and ' -c ' in line and '-DRE4DC_DEATH_TRACE=1' in line];assert len(commands)==(3 if a.arm=='on' else 0)
if a.arm=='on':assert {Path(shlex.split(line)[shlex.split(line).index('-c')+1]).name for line in commands}=={'em_sub.cpp','pl_dmg.cpp','game.cpp'}
else:assert all(files[name]['sha256']==row['sha256'] for name,row in control_files.items()),'Full OFF raw/14 overlay identity failed'
result.update(arm=a.arm,full_OFF_control_identity=(a.arm=='off'),status='LINK_COMPLETE_ONLY',files=files,resolved_sha256=sha(OUT/'resolved-knobs.txt'),recipe_sha256=sha(OUT/'candidate.txt'),log_sha256=sha(log),trace_compile_commands=commands,all14_bound_to_new_ELF=True,overlays=overlay_rows,footprint_after_raw=owned_size(),stage_performed=False,cross_program_state_restore=False)
(OUT/'KEEP.txt').write_text('Preserve trace ELF/raw/14 overlays/recipe/source/process/log identities; link only, no stage/runtime proof.\n');(JOB/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'status':'LINK_COMPLETE_ONLY','source':plan['trace_tools_HEAD'],'program':files['program.bin'],'ELF':files['re4dc-game.elf'],'all14_bound_to_new_ELF':True,'peak':result['peak_incremental_bytes']}))