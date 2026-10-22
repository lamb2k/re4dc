"""Prepare source-only two-task metadata; no target tool or source view is executed."""
from pathlib import Path
import ast,gzip,hashlib,json,math,os,shlex,shutil,subprocess
T=Path('/root/probe/codex-issue52-objects');R=Path('/root/probe/codex-cache21-integration-next');Q=Path('/root/probe/codex-qa21-death-repair')
M=T/'port/dreamcast/tools/d367/issue52_cache_em10_objectprep';C=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/issue52-cache-em10-objectprep-20261022');L=Path('/mnt/c/Game Dev/Emulators/codex-lanes/issue52-cache-em10-objectprep')
P=T/'port/dreamcast/tools/d367/issue52_cache_currentqa_plan';OLD=T/'port/dreamcast/tools/d367/issue52_cache_repairs_objectprep';S=T/'port/dreamcast/tools/d367/issue52_objectprep650'
RUNNER=Path('/mnt/c/Game Dev/Emulators/codex-lanes/issue52-cache-repairs-objectprep/allocated-object-gate.py')
F=Path('/root/probe/issue52-cache-em10-sh4-objects-20261022-01');V=F/'sourceview';C57='c57ff60f0f462fdd2c419883b0258963504d756a';RT='babfaa7d8ee868c9b81305aef7024ffd543eb6f6'
sha=lambda b:hashlib.sha256(b).hexdigest()
def row(p):p=Path(p);return {'path':str(p),'resolved_path':str(p.resolve()),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())}
def load(p):p=Path(p);return json.loads(gzip.decompress(p.read_bytes())if p.suffix=='.gz'else p.read_bytes())
def git(*a,cwd=T):return subprocess.check_output(['git',*a],cwd=cwd,text=True).strip()
def verify(x):p=Path(x['path']);assert p.is_file()and p.stat().st_size==x['bytes']and sha(p.read_bytes())==x['sha256']and str(p.resolve())==x['resolved_path'],p
assert not M.exists()and not C.exists()and not F.exists()
assert git('rev-parse','HEAD')=='89ea415b5e698c4ab4aec28c7d2568fbb7f81ba5'and not git('status','--porcelain')
assert not git('status','--porcelain',cwd=R);assert shutil.disk_usage('/mnt/c').free>=19394461696+1048576
roothead=git('rev-parse','HEAD',cwd=R);qhead=git('rev-parse','HEAD',cwd=Q);qstatus=git('status','--porcelain',cwd=Q)
module=load(P/'module-reconstruction.json.gz');closure=[];qa=[]
header=subprocess.check_output(['git','show',C57+':include/cManager.h'],cwd=T)
for rel,h,b,equal in module['constituents'][0]['deps']:
 p=R/rel;current=row(p);historical=rel=='include/cManager.h'
 assert sha(header)==h if historical else current['sha256']==h,(rel,h)
 closure.append({'relative':rel,'candidate':current,'view_path':str(V/rel),'view_sha256':h,'view_bytes':b,'origin':'historical-cManager.h.gz'if historical else'frozen-current-root-exact-C57'})
 qp=Q/rel;qa.append({'relative':rel,'exists':qp.is_file(),'sha256':sha(qp.read_bytes())if qp.is_file()else None,'exact_C57':qp.is_file()and sha(qp.read_bytes())==h})
assert len(closure)==85 and sum(r['origin'].startswith('historical')for r in closure)==1
# Pin and verify inherited broad system/tool manifests; no redundant giant tables.
refs=[]
for p in[P/'SHA256SUMS',P/'module-reconstruction.json.gz',P/'qa52190.json',P/'VALIDATION.json',OLD/'SHA256SUMS',OLD/'environment.json',OLD/'tool-extra-pins.json',S/'system-header-pins.json.gz',S/'toolchain-pins.json',RUNNER]:refs.append(row(p))
system=load(S/'system-header-pins.json.gz');tools=load(S/'toolchain-pins.json');fixed=load(OLD/'tool-extra-pins.json')
for x in system+tools+fixed:verify(x)
# Same include-root traversal as the accepted650 metadata producer, resolved membership exact.
roots=['/opt/toolchains/dc/sh-elf/sh-elf/include','/opt/toolchains/dc/sh-elf/lib/gcc/sh-elf/15.2.0/include','/root/work/kos-re4dc-d367/include','/root/work/kos-re4dc-d367/kernel/arch/dreamcast/include','/root/work/kos-re4dc-d367/addons/include']
actual=set()
for root in roots:
 seen=set()
 for base,dirs,files in os.walk(root,followlinks=True):
  real=os.path.realpath(base)
  if real in seen:dirs[:]=[];continue
  seen.add(real)
  for n in files:
   p=Path(base)/n
   if p.is_file():actual.add(str(p.resolve()))
assert actual=={x['resolved_path']for x in system},'system membership differs from accepted manifest'
assert {str(p)for p in Path('/opt/toolchains/dc/sh-elf/lib/gcc/sh-elf/15.2.0/include-fixed').rglob('*')if p.is_file()}=={x['path']for x in fixed}
extra=[row(R/'port/dreamcast/kos-env.sh'),row(Path('/opt/toolchains/dc/sh-elf/bin/sh-elf-objdump'))]
# Only these pure functions are reusable. Allocation/worker/controller/materialize functions remain scope-specific.
src=RUNNER.read_text();tree=ast.parse(src);names={'req','sha','load','record','elf_info','stack_info','macros_from','content_sections'}
funcs={n.name:{'line':n.lineno,'end_line':n.end_lineno,'sha256':sha(ast.get_source_segment(src,n).encode())}for n in tree.body if isinstance(n,ast.FunctionDef)and n.name in names};assert set(funcs)==names
# Read-only ELF metadata via exact existing functions, not a second ELF parser/framework.
ns={'Path':Path,'hashlib':hashlib,'struct':__import__('struct'),'MI':1048576}
code=ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name in {'req','elf_info','content_sections'}],type_ignores=[])
exec(compile(ast.fix_missing_locations(code),str(RUNNER),'exec'),ns)
reference=Path(module['oldprefix'])/'mod/em10g/shared/src/em10/em10.o';verify({'path':str(reference),'resolved_path':str(reference.resolve()),'bytes':module['constituents'][0]['old']['b'],'sha256':module['constituents'][0]['old']['sha']})
info=ns['elf_info'](reference);selected=[s[6:]for s in info['sections']if s.startswith('.text.')and 'C_SawHit'in s];assert selected
base=module['commands'][0]['argv'][:];base[0]='/root/work/kos-re4dc-d367/utils/build_wrappers/kos-c++';k=base.index('-MMD');prefix=base[:k];source='../../../src/em10/em10.cpp';tasks={}
for name,val in [('em10-off',0),('em10-on',1)]:
 out=F/'objects'/name;a=[('-DRE4DC_GANADO_ROUTINE_BYTES='+str(val))if s=='-DRE4DC_GANADO_ROUTINE_BYTES=1'else s for s in prefix]
 command=a+['-fstack-usage','-MMD','-MP','-MF',str(out)+'.d','-c',source,'-o',str(out)+'.o']
 tasks[name]={'cwd':str(V/'port/dreamcast/game'),'unit':'em10','guard':'RE4DC_GANADO_ROUTINE_BYTES','expected_guard':val,'command':command,'macro_command':a+['-dM','-E',source],'preprocess_command':a+['-E','-P',source],'full_system_dependency_command':a+['-M','-MF',str(out)+'.full.d','-MT',str(out)+'.o',source],'strip_command':['/opt/toolchains/dc/sh-elf/bin/sh-elf-objcopy','--strip-debug',str(out)+'.o',str(out)+'.stripped.o'],'diagnostic_only_added_flag':'-fstack-usage','output_prefix':str(out),'disassembly_commands':[['/opt/toolchains/dc/sh-elf/bin/sh-elf-objdump','-dr','--disassemble='+sym,str(out)+'.o']for sym in selected]}
# Same exact flags: the guard and private output filenames are the only OFF->ON changes.
a=tasks['em10-off']['command'];b=tasks['em10-on']['command'];assert [s.replace('=0','=1').replace('em10-off','em10-on')if s.startswith('-DRE4DC_GANADO_ROUTINE_BYTES=')or'em10-off'in s else s for s in a]==b
macro={'RE4DC_ACTOR_TRANSACTION':'1','RE4DC_ACTOR_LEON_NATIVE_LOOK':'1','RE4DC_VMU_DIALOG':'1','RE4DC_GAME':'1','RE4DC_BODY_ROUTE':'1','RE4DC_BODY_ROUTE_FAR':'12000','_prolog':'em12_prolog','_epilog':'em12_epilog','_unresolved':'em12_unresolved','_ctors':'re4dc_module_ctors','_dtors':'re4dc_module_dtors'}
zero=['EM_ADMISSION_DISP_FIX','EFFECT_ADMISSION_GUARD','EVD_ADMISSION_TXN','EVD_START_CLEANUP','EVD_START_ROLLBACK','EVD_DEBUG_READ_CLEANUP','EVD_EXEC_FAILURE_CLEANUP','EVD_ARAM_ALLOC_RETRY','EVD_READ_RELEASE_REFS','EVD_READ_ADMISSION_PREFLIGHT','EVD_MODULE_VALIDATE_FIRST','MOTION_RETIRE_PREFLIGHT','EVD_FORWARD_RECEIPT','EFFECT_CONTROLLER_VALIDATE_FIRST','TEX_PAYLOAD_RETRY','EVENT_MANAGER_STORAGE_FLAGS','CABIN_SOURCE','SS_RESTORE_VALIDATE_FIRST','RESET_RETIRE_BEFORE_HEAPS','SS_WINDOW_HOLD_RESTORE']
# Common validated programme framework is only a future reference, never an em10 compile certificate.
Q4=Path('/root/re4data/private/texture-consumers21-next792-runner04-20261022');q4=load(Q4/'SOURCE04-qualification.json');common={'source_commit':q4['source_commit'],'qualification':row(Q4/'SOURCE04-qualification.json'),'seal':row(Q4/'SHA256SUMS.txt'),'files':[],'root_report':'Actual mipmap04 ALL41 gates PASS/frozen B04/E04, per direct root allocation message; no fresh programme run/validation here.','role':'Future programme/controller closure reuse only. Compile source/tool/header/environment pre/post still required.'}
assert common['seal']['sha256']=='fcd9bcb10d41fb6c38876d34ccf32a22a19ba139142fc2bf2c882adc88fe9b1a'
for x in q4['source_files']:
 p=row(x['path']);assert p['sha256']==x['sha256']and p['bytes']==x['bytes'];common['files'].append(p)
env=load(OLD/'environment.json');env['required_execution']['TMPDIR']=str(F/'temp');env['startup']='Use accepted env-i/one-slot worker recipe, source frozen root kos-env.sh; snapshot complete environment/resolution before and after every command. Do not inherit other jobs lease/environment. No runner is created or executed in this source unit.'
for p in env['absent']:assert not Path(p).exists()
view={'destination':str(V),'cwd':str(V/'port/dreamcast/game'),'source':str(V/'src/em10/em10.cpp'),'source_bytes':869044,'source_sha256':'065613c2d2297a5f843d71c897daffd14a715d7aac7e17c3fe563c6be990aaad','recipe':['After separate allocation and exact source/tool/header pins pass, create fresh owned sourceview; never expand or edit QA sparse tree.','Copy the85 sealed input files to their exact relative paths as regular read-only files. Copy84 byte-exact-C57 files from frozen root and decompress the one sealed historical cManager.h payload. Create all source/include/cwd ancestors as real owned directories. No symlink directories or source/header escape.','Copy only sealed inputs; resolve original ../../../src/em10/em10.cpp and -I../../../include from real private cwd. Assert resolved source and every expected dependency are inside this view and match C57 identity.','Make real files0444/directories0555 after creation, pin complete view membership/identities and verify source/root inputs pre/post. Retain read-only view on failure until exact owned processes/lease close; never mutate source tree.'],'raw_copied_payload_bytes':sum(r['view_bytes']for r in closure),'minimal_view_not_full_historical_tree':True,'actual_materialized':False,'C57_header_sha256':sha(header),'current_root_header_sha256':sha((R/'include/cManager.h').read_bytes()),'header_scope':'Historical header only in historical C57 module reconstruction view. Current qualified SS/main keep current header; no source swap or current-root full adoption claim.'}
plan={'state':'TWO_TASK_SOURCE_PREPARATION_ONLY_NO_ALLOCATION','root_runtime':RT,'root_docs_observed':roothead,'basis_source':C57,'basis_programme':'52190ed293d8e62238bcad40fd351d35a965b253ad5b59cda570d0de34187e45','basis_ELF':'248dd4aac7c4e22a7a18a0183fc6409401fddf610d98881c90dd9664e342640b','prior_plan':'89ea415b5 preserved immutable','future_output':str(F),'task_order':['em10-off','em10-on'],'existing_object_runner':row(RUNNER),'pure_helpers':funcs,'do_not_reuse_unmodified':['scope-bound eight-task controller/worker/base_pins/view_pins/materialize/paths/allocation hashes','hardcoded SS/reset selected-symbol and six-controls-beforeON logic'],'main_owns_actual_controller':True,'metadata_hard_bytes':1048576,'global_source_peer_bytes':67108864,'preparation_floor_bytes':19394461696,'future_proposal_only':{'hard_bytes':33554432,'soft_abort_bytes':25165824,'active_ephemeral_reservation_per_command':4194304,'runtime_floor_bytes':19394461696,'source_peer_reservation_bytes':67108864,'one_shared_buildslot_lease':True,'sequential':True,'no_retry':True,'sourceview_estimate_bytes':1572864,'max_probe_stream_bytes':4194304,'max_macro_stream_bytes':262144,'new_metadata_need_root_allocation_before_execution':True},'runs':{'compiler':0,'preprocessor':0,'lease':0,'linker':0,'programme':0,'image':0,'guest':0},'future_controls':['OFF first: exact macro map critical fields; full actual-system dependency closure must belong to sealed85view+1233system+fixed set before object compile. Missing pin aborts, never retrospective seal.','OFF explicitGANADO0 object: strip both immutable original QA reference and fresh OFF with same pinned objcopy in owned output, exact stripped plus allocated/relocation identities required. Source path remains original relative spelling; debug ELF paths need not hash equal.','ON only after OFF control passes: macro map equal except GANADO and volatile builtin timestamps; same full dependency set, actual resolved argv, source/tool/header/envprepost. Record PP hashes, raw/stripped hashes, sections/relocs/stack and exact native SawHit disassembly. No runtime attribution from objects.','Keep original13 constituent objects/order and state.ld bound to89ea module recipe; no partial link here.','Later programme is a separate allocation: fresh OFF52190/all14 and allocated/loadable ELF+BSS before SS/resetON. Event1 staysHOLD. Future programme/ELF/DWARF/stateABI/coldfixture must match newprogramme, no8942/crossprogramme52190 state reuse.'],'preserve':'Default0 experiments/negative window restoration0; no runtime/recipe/release/SD/third-party action. External Claude jobs untouched; no service capacity or hardware claims.'}
files={
 'plan.json':plan,'planned-tasks.json.gz':tasks,'source-inputs.json.gz':closure,'source-view.json':view,'environment.json':env,
 'qa-tree-disposition.json':{'tree':str(Q),'head':qhead,'dirty':qstatus,'source_or_header_writes':0,'git_mutations':0,'usable_direct_C57_tree':False,'expected_dependencies':85,'byte_exact_present_count':sum(r['exact_C57']for r in qa),'missing_count':sum(not r['exists']for r in qa),'em10_present_but_not_C57':next(r for r in qa if r['relative']=='src/em10/em10.cpp'),'sparse_patterns':git('sparse-checkout','list',cwd=Q).splitlines(),'header_skip_worktree':git('ls-files','-v','include/cManager.h',cwd=Q),'Makefile_byte_exact_C57':(Q/'port/dreamcast/game/Makefile').read_bytes()==subprocess.check_output(['git','show',C57+':port/dreamcast/game/Makefile'],cwd=T),'reason':'Required headers omitted by intentional sparse checkout; source lacks final12-line C57 reader repair; Makefile differs. No QA tree edits/sparse expansion performed.'},
 'reference-control.json':{'original_QA_object':row(reference),'original_info_allocated_bytes':info['allocated_section_bytes'],'allocated_and_reloc_sections_sha256':sha(json.dumps(ns['content_sections'](info),sort_keys=True).encode()),'reference_strip_command':['/opt/toolchains/dc/sh-elf/bin/sh-elf-objcopy','--strip-debug',str(reference),str(F/'objects/reference-QA.stripped.o')],'reference_strip_not_executed':True,'same_strip_required_for_fresh_OFF':True,'stripped_expected_hash':'Computed from pre-pinned immutable reference with same pinned objcopy under separate allocation; not a guessed historicalg0 hash.','do_not_relabel_old_g0_reader_unit':'Older reader unit adds-g0/macro-prefix-map; prior source proof only, not this exact actual-QA debug/tool/wrapper contract.','selected_native_symbols':selected,'constituents_source':row(P/'module-reconstruction.json.gz'),'ordered_unchanged_13':[{'relative':r['r'],'object':{'path':str(Path(module['oldprefix'])/r['r']),'bytes':r['old']['b'],'sha256':r['old']['sha']}}for r in module['constituents'][1:]],'no_module_link_allocated':True},
 'provenance-reuse.json':{'references':refs,'extra_tool_pins':extra,'verified_system_count':len(system),'verified_tool_count':len(tools),'include_roots':roots,'system_resolved_membership_sha256':sha('\n'.join(sorted(actual)).encode()),'include_fixed_membership':[r['path']for r in fixed],'source_tools_headers_checked_preparation_only':True,'fresh_per_command_prepost_required':True,'no_compiler_version_probe_executed':True},
 'critical-macros.json':{'fixed':macro,'guard':'RE4DC_GANADO_ROUTINE_BYTES','guards_must_be_undefined_or_zero':['RE4DC_'+x for x in zero],'all_other_nonvolatile_macros_must_match_OFF_ON':True,'volatile_exclusions':['__DATE__','__TIME__','__TIMESTAMP__'],'Event1_HOLD':True},'common-runner04-reference.json':common}
encoded={n:(gzip.compress((json.dumps(d,sort_keys=True,separators=(',',':'))+'\n').encode(),mtime=0)if n.endswith('.gz')else(json.dumps(d,sort_keys=True,separators=(',',':'))+'\n').encode())for n,d in files.items()};encoded['historical-cManager.h.gz']=gzip.compress(header,mtime=0)
forecast=3*sum(math.ceil(len(b)/4096)*4096 for b in encoded.values())+196608;assert forecast<1048576,forecast
M.mkdir();C.mkdir()
for n,b in encoded.items():(M/n).write_bytes(b);(C/n).write_bytes(b)
assert git('rev-parse','HEAD',cwd=Q)==qhead and git('status','--porcelain',cwd=Q)==qstatus
print(json.dumps({'files':{n:len(b)for n,b in encoded.items()},'forecast_bytes':forecast,'source_view_payload_bytes':view['raw_copied_payload_bytes'],'system_headers':len(system),'source_headers':len(closure),'QA_direct_usable':False,'root_docs_observed':roothead}))
