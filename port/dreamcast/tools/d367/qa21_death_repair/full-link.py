#!/usr/bin/env python3
"""Plan or run one allocated trace-enabled link; never stages an image or restores states."""
import argparse,hashlib,json,os,shlex,shutil,signal,subprocess,time
from pathlib import Path
from overlay_identity import elf_text,overlay_bytes
from guarded_process import run_guarded
BASE=Path('/root/probe/codex-qa21-combined-regression');TRACE=Path('/root/probe/codex-qa21-death-repair');R=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/qa21-death-trace-runtime-20261021')
START=18*1024**3+640*1024**2;FLOOR=18*1024**3+64*1024**2;CAP=320*1024**2;LOG_CAP=8_000_000
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execute-link',action='store_true');p.add_argument('--execute-enabled-link',action='store_true');p.add_argument('--arm',choices=['off','on'],default='on');p.add_argument('--job',type=Path);a=p.parse_args();a.job=a.job or Path('/root/probe/qa21-death-repair-full-'+a.arm+'-20261021');assert a.job.parent==Path('/root/probe') and a.job.name.startswith('qa21-death-repair-full-');JOB=a.job;VIEW=JOB/'source-view';OUT=JOB/'enabled'
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
    try:st=(Path(folder)/name).lstat()
    except FileNotFoundError:continue # make atomically removes transient *.tmp2 files
    total+=max(st.st_size,st.st_blocks*512)
 return total
def retained_size():
 total=0
 for root in [TRACE,*Path('/root/probe').glob('qa21-death-repair-full-*')]:
  for folder,dirs,files in os.walk(root,followlinks=False):
   for name in files+dirs:
    try:st=(Path(folder)/name).lstat()
    except FileNotFoundError:continue
    total+=max(st.st_size,st.st_blocks*512)
 return total
def stop_build_reason(free, used, log_bytes, elapsed):
 if free<FLOOR:return 'C18GiB+64MiB runtime floor'
 if used>=CAP:return '320MiB incremental tree+output cap'
 if log_bytes>=LOG_CAP:return '8MB owned log cap'
 if elapsed>=600:return '600s owned build cap'
 return None
unit=json.loads((TRACE/'port/dreamcast/tools/d367/qa21_death_repair/repair-source-manifest.json').read_text());assert all(sha(TRACE/name)==digest for name,digest in unit['trace_files'].items())
assert git(BASE,'rev-parse','HEAD')=='e2ae49d16818b133b5eb1c94cdfed7f7e608c448';assert not git(BASE,'status','--porcelain');assert not git(TRACE,'status','--porcelain')
control=R/'builds/trace';recipe=control/'candidate.txt';knobs=shlex.split(recipe.read_text());assert 'QA_MENU=1' in knobs and 'PAUSE_NATIVE_PRESENTATION=0' in knobs and 'GAME_SH4ZAM=1' in knobs;assert 'DEATH_TRACE=1' in knobs and not any(k.startswith('GANADO_ROUTINE_BYTES=') or k=='SS_WINDOW_HOLD_RESTORE=1' for k in knobs);knobs+=['GANADO_ROUTINE_BYTES='+str(int(a.arm=='on'))]
# The previous exact recipe retained these measured bytes, before a transient overlay ELF/source metadata.
estimate={'prior_compiled_objects':187069626,'prior_link_scratch':49748731,'prior_complete_output':34057070,'temporary_overlay_ELF_allowance':29427116,'source_view_log_trace_allowance':16*1024**2};estimated_peak=sum(estimate.values());assert estimated_peak<CAP
plan={'scope':'Matched repair OFF/ON with DEATH_TRACE1 held constant; no stage or cross-program saved-state restore','repair_source':'f071b4e9069ebd3a7dec48a98f2fea95f6d11215','arm':a.arm,'trace_runtime_source':'f99dc69ad8bfeebcdb10913443543514dc40f9cc','trace_tools_HEAD':git(TRACE,'rev-parse','HEAD'),'frozen_source_HEAD':git(BASE,'rev-parse','HEAD'),'frozen_runtime_source':'6f9d31b0e00497a75fdd7e25bb04f92305103087','trace_files':unit['trace_files'],'recipe_sha256':sha(recipe),'compiler_sha256':sha('/opt/toolchains/dc/sh-elf/bin/sh-elf-g++'),'KOSlib_sha256':sha('/root/work/kos-re4dc-d367/lib/dreamcast/libkallisti.a'),'submodule':git(BASE,'submodule','status'),'knobs':knobs,'job':str(JOB),'source_view':'Read-only frozen dependencies; reviewed3 trace sources, exact repairedem10 and combined narrowMakeguards; private link scratch and SDK gen','resource':{'fresh_C_bytes':shutil.disk_usage('/mnt/c').free,'start_floor':START,'runtime_floor':FLOOR,'incremental_tree_output_cap':CAP,'footprint_accounting':'Per-entry max(logical bytes, allocated blocks), including directory blocks; source symlinks are not followed','log_cap':LOG_CAP,'estimate_components':estimate,'estimated_peak':estimated_peak},'repair_OFF_gate':{'status':'Allocated matched OFF control before ON','recipe':'Same trace-control recipe DEATH_TRACE1 with GANADO_ROUTINE_BYTES0; exact program/14 overlays/load segments required','expected_raw':'ca30bfc0c28490c91d18dbd37182e89d1f905cbf9bf735280bc7cd90cdb93b94','expected_all14_overlays':'Exact retained trace-control14','ELF_note':'Full ELF debug/path identity is recorded separately; raw program plus all14 overlays are the control gate; existing g0 unit identity is not a full-program gate'},'stage_status':'UNALLOCATED. Separate standalone image copy/patch and all-file verification plan; no image hardlinks or extracted asset tree.'}
if not (a.execute_link or a.execute_enabled_link):
 plan['admission']='PASS' if plan['resource']['fresh_C_bytes']>=START else 'REFUSED before job output';print(json.dumps(plan,indent=2));raise SystemExit(0)
assert retained_size()<640*1024**2,'640MiB pair retained cap';assert plan['resource']['fresh_C_bytes']>=START,'Refused before output: unchanged18GiB+640MiB admission';assert not JOB.exists(),'Preserve existing job'
frozen_scratch=tree_files(BASE/'port/dreamcast/game/obj');frozen_sdk=tree_files(BASE/'port/dreamcast/game/platform/sdk/gen')
# Recheck after read-only identities, before making any job output.
assert shutil.disk_usage('/mnt/c').free>=START,'Refused before output after source hashing'
JOB.mkdir();OUT.mkdir();(OUT/'obj').mkdir();(OUT/'link-scratch').mkdir()
overrides={'.git':TRACE/'.git','src/game/em_sub.cpp':TRACE/'src/game/em_sub.cpp','src/game/pl_dmg.cpp':TRACE/'src/game/pl_dmg.cpp','src/game/game.cpp':TRACE/'src/game/game.cpp','src/em10/em10.cpp':TRACE/'src/em10/em10.cpp','port/dreamcast/game/Makefile':TRACE/'port/dreamcast/game/Makefile','port/dreamcast/game/obj':OUT/'link-scratch','port/dreamcast/game/platform/sdk/gen':None,'port/dreamcast/tools/d367/qa21_death_trace':TRACE/'port/dreamcast/tools/d367/qa21_death_trace'}
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
def sample():
 global peak,min_free
 used=owned_size();free=shutil.disk_usage('/mnt/c').free;peak=max(peak,used);min_free=min(min_free,free)
 if retained_size()>=640*1024**2:return '640MiB retained pair including failures cap'
 return stop_build_reason(free,used,log.stat().st_size,time.monotonic()-started)
try:
 with log.open('xb') as stream:rc,guard,owned=run_guarded(cmd,VIEW,env,stream,sample,JOB/'owned-build.json')
except BaseException as error:
 (JOB/'supervisor-exception.json').write_text(json.dumps({'status':'FAILED_QUALIFICATION_SUPERVISOR_EXCEPTION','error':repr(error),'owned_cleanup_attempted':True,'stage_performed':False},indent=2)+'\n')
 raise
assert frozen_scratch==tree_files(BASE/'port/dreamcast/game/obj'),'Frozen link scratch changed';assert frozen_sdk==tree_files(BASE/'port/dreamcast/game/platform/sdk/gen'),'Frozen SDK generated sources changed';assert not git(BASE,'status','--porcelain')
assert all(sha(TRACE/name)==digest for name,digest in unit['trace_files'].items())
assert sha('/root/work/kos-re4dc-d367/lib/dreamcast/libkallisti.a')==plan['KOSlib_sha256']
result={'source':plan,'process':owned,'returncode':rc,'guard':guard,'seconds':round(time.monotonic()-started,4),'peak_incremental_bytes':max(peak,owned_size()),'minimum_free_C_bytes':min_free,'frozen_scratch_and_sdk_preserved':True,'retained_pair_bytes':retained_size()}
if rc or guard:
 (JOB/'failed.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'status':'FAILED','code':rc,'guard':guard,'job':str(JOB)}));raise SystemExit(rc or 2)
elf=OUT/'re4dc-game.elf';raw=OUT/'program.bin';subprocess.run(['/opt/toolchains/dc/sh-elf/bin/sh-elf-objcopy','-R','.stack','-O','binary',str(elf),str(raw)],check=True);assert owned_size()<CAP
files={f.name:{'bytes':f.stat().st_size,'sha256':sha(f)} for f in [elf,raw,*sorted(OUT.glob('*.ovl'))]};assert len(files)==16
control_files=json.loads((R/'build-receipt.json').read_text())['files'];text=elf_text(elf);overlay_rows={}
for f in sorted(OUT.glob('*.ovl')):
 row=overlay_bytes(f.read_bytes(),text);row['control_sha256']=control_files[f.name]['sha256'];row['same_as_control']=row['sha256']==row['control_sha256'];old=(control/f.name).read_bytes();new=f.read_bytes();row['difference_scope']='identical' if old==new else ('main-text-binding-only' if old[:56]==new[:56] and old[64:]==new[64:] else 'binding-and/or-payload; linked resident references require review');overlay_rows[f.name]=row
resolved=dict(line.split('=',1) for line in (OUT/'resolved-knobs.txt').read_text().splitlines() if '=' in line)
for name,value in {'DEATH_TRACE':'1','GANADO_ROUTINE_BYTES':str(int(a.arm=='on')),'QA_MENU':'1','PAUSE_NATIVE_PRESENTATION':'0','GAME_SH4ZAM':'1','SKIN_SH4ZAM':'0'}.items():assert resolved[name]==value
assert resolved.get('SS_WINDOW_HOLD_RESTORE','0')=='0'
commands=[line for line in log.read_text().splitlines() if line.startswith('kos-c++ ') and ' -c ' in line and '-DRE4DC_DEATH_TRACE=1' in line];assert len(commands)==3
assert {Path(shlex.split(line)[shlex.split(line).index('-c')+1]).name for line in commands}=={'em_sub.cpp','pl_dmg.cpp','game.cpp'}
repair_commands=[line for line in log.read_text().splitlines() if line.startswith('kos-c++ ') and ' -c ' in line and '-DRE4DC_GANADO_ROUTINE_BYTES=1' in line]
assert len(repair_commands)==(1 if a.arm=='on' else 0)
if a.arm=='on':assert Path(shlex.split(repair_commands[0])[shlex.split(repair_commands[0]).index('-c')+1]).name=='em10.cpp'
else:assert all(files[name]['sha256']==row['sha256'] for name,row in control_files.items() if name!='re4dc-game.elf'),'Repair OFF raw/14 overlay identity failed'
def elf_load_segments(path):
 data=path.read_bytes();assert data[:6]==b'\x7fELF\x01\x01'
 import struct
 phoff=struct.unpack_from('<I',data,28)[0];size,count=struct.unpack_from('<HH',data,42);rows=[]
 for i in range(count):
  kind,off,va,pa,fs,ms,flags,align=struct.unpack_from('<8I',data,phoff+i*size)
  if kind==1:rows.append({'vaddr':va,'paddr':pa,'filesz':fs,'memsz':ms,'flags':flags,'align':align,'sha256':hashlib.sha256(data[off:off+fs]).hexdigest()})
 return rows
loads=elf_load_segments(elf);control_loads=elf_load_segments(control/'re4dc-game.elf')
if a.arm=='off':assert loads==control_loads,'Repair OFF exact trace-control load segments failed'
result.update(arm=a.arm,repair_compile_commands=repair_commands,load_segments=loads,control_load_segments=control_loads,repair_OFF_trace_control_identity=(a.arm=='off'),full_OFF_control_identity=(a.arm=='off'),status='LINK_COMPLETE_ONLY',files=files,resolved_sha256=sha(OUT/'resolved-knobs.txt'),recipe_sha256=sha(OUT/'candidate.txt'),log_sha256=sha(log),trace_compile_commands=commands,all14_bound_to_new_ELF=True,overlays=overlay_rows,footprint_after_raw=owned_size(),stage_performed=False,cross_program_state_restore=False)
(OUT/'KEEP.txt').write_text('Preserve trace ELF/raw/14 overlays/recipe/source/process/log identities; link only, no stage/runtime proof.\n');(JOB/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'status':'LINK_COMPLETE_ONLY','source':plan['trace_tools_HEAD'],'program':files['program.bin'],'ELF':files['re4dc-game.elf'],'all14_bound_to_new_ELF':True,'peak':result['peak_incremental_bytes']}))