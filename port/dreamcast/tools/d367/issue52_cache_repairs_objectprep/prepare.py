"""Prepare frozen cache-repair full-TU object tasks; never invokes a compiler."""
from pathlib import Path
import gzip,hashlib,json,os,shlex,subprocess
T=Path('/root/probe/codex-cache21-integration-next'); OWN=Path('/root/probe/codex-issue52-objects')
M=OWN/'port/dreamcast/tools/d367/issue52_cache_repairs_objectprep'
P=OWN/'port/dreamcast/tools/d367/issue52_objectprep650'
B=Path('/root/probe/cache21-ganado-reader-build-20261021/off-01'); O=Path('/root/probe/texture-rect21-program-pair-20261021-01'); R=Path('/root/probe/codex-texture-rect21')
F=Path('/root/probe/issue52-cache-repairs-sh4-objects-20261022-01')
HEAD='babfaa7d8ee868c9b81305aef7024ffd543eb6f6'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def pin(p):p=Path(p);return dict(path=str(p),resolved_path=str(p.resolve()),bytes=p.stat().st_size,sha256=sha(p))
def git(*a):return subprocess.check_output(['git',*a],cwd=T)
def put(n,x):
 p=M/n;b=(json.dumps(x,indent=2)+'\n').encode() if not isinstance(x,bytes) else x
 p.write_bytes(gzip.compress(b,mtime=0) if n.endswith('.gz') else b)
def req(c,s):
 if not c:raise RuntimeError(s)
req(git('rev-parse','HEAD').decode().strip()==HEAD,'HEAD');req(not git('status','--porcelain').strip(),'dirty');req(not F.exists(),'future output exists')
M.mkdir(parents=True,exist_ok=False)
# Preserve the generator itself in this exclusive metadata namespace.
(M/'prepare.py').write_bytes(Path(__file__).read_bytes())
refs=[B/'build.log',B/'owned-build.json',B/'candidate.txt',O/'out-off/build.log',O/'pair-result.json',P/'system-header-pins.json.gz',P/'toolchain-pins.json',P/'compiler-environment.json',Path('/root/probe/d367-buildslot.sh')]
inputs={};comparisons=[];tasks={};contracts=[];baselines={};codecs={}
units=[('sscrn','port/dreamcast/game/sscrn_bridge.cpp','sscrn_bridge.cpp','sscrn_bridge','54ba44079c33117b8241a9277c3aecdce8b4f9ce','RE4DC_SS_RESTORE_VALIDATE_FIRST'),('reset','src/game/main.cpp','../../../src/game/main.cpp','src/game/main','575953b0bc039dbc716d3411e275be1d04313e2e','RE4DC_RESET_RETIRE_BEFORE_HEAPS')]
for name,rel,src,obj,prev,guard in units:
 p=T/rel;inputs[str(p)]=pin(p)
 old=git('show',prev+':'+rel);oldsha=hashlib.sha256(old).hexdigest();put(name+'-previous.cpp.gz',old)
 req(git('show','c57ff60f0:'+rel)==old,'previous source not same full TU as C57')
 recorded=[shlex.split(s) for s in (B/'build.log').read_text().splitlines() if s.startswith('kos-c++ ') and '-c '+src+' ' in s];req(len(recorded)==1,'ambiguous C57 command')
 canonical=[shlex.split(s) for s in (O/'out-off/build.log').read_text().splitlines() if s.startswith('kos-c++ ') and '-c '+src+' ' in s];req(len(canonical)==1,'ambiguous canonical command')
 # The C57 and canonical command contracts must differ only in source/output root spelling.
 norm=lambda a:[v.replace(str(B),'<OBJ>').replace(str(O),'<OBJ>').replace(str(T),'<SOURCE>').replace(str(R),'<SOURCE>') for v in a]
 req(norm(recorded[0])==norm(canonical[0]),'C57/canonical compile flags differ')
 oldobj=O/'obj'/(obj+'.o');dep=O/'obj'/(obj+'.d');refs.extend([oldobj,dep])
 line=dep.read_text().replace('\\\n',' ').splitlines()[0]
 deps=[]
 for s in shlex.split(line.split(':',1)[1]):
  q=Path(s);q=q if q.is_absolute() else R/'port/dreamcast/game'/q;q=q.resolve()
  try:r=q.relative_to(R);current=T/r
  except ValueError:r=None;current=q
  req(q.is_file() and current.is_file(),'missing dependency '+str(q));inputs[str(current)]=pin(current)
  if r is not None:
   prior=git('show',prev+':'+str(r));req(hashlib.sha256(prior).hexdigest()==sha(current) or str(r)==rel,'previous dependency differs '+str(r))
  deps.append(dict(recorded_path=str(q),candidate_path=str(current),sha256=sha(current),baseline_same=(str(r)!=rel if r is not None else True)))
 # Every forced include remains exact recorded bytes; no generated header rerun.
 a=canonical[0];prefix=a[:a.index('-MMD')];prefix[0]='/root/work/kos-re4dc-d367/utils/build_wrappers/kos-c++'
 prefix=[v.replace(str(R),str(T)) for v in prefix]
 for i,v in enumerate(prefix):
  if v=='-include':
   h=Path(prefix[i+1]);h=h if h.is_absolute() else T/'port/dreamcast/game'/h;req(h.is_file(),'forced header missing');inputs[str(h.resolve())]=pin(h.resolve())
 contracts.append(dict(unit=name,source=rel,guard=guard,previous_commit=prev,previous_source_sha256=oldsha,candidate_source_sha256=sha(p),recorded_C57_argv=recorded[0],recorded_canonical_argv=canonical[0],mapped_unchanged_prefix=prefix,optimization_order=[v for v in prefix if v.startswith('-O')],previous_MMD_dependencies=deps,previous_header_contract_exact_except_selected_TU=True,canonical_object=pin(oldobj),canonical_object_identity_claim=False))
 baselines[name]=dict(commit=prev,relative_source=rel,sha256=oldsha,compressed_source=name+'-previous.cpp.gz',projection=str(F/'projections'/name),policy='Create a read-only symlink view of candidate tree; ancestor directories of both selected TU and compile cwd are real (union); replace only selected TU with decompressed exact previous bytes. Preserve command source argument, relative include lookup, __FILE__ and __BASE_FILE__. Do not edit parent tree. All current dependency bytes except selected TU verified equal previous commit. Pin view and resolved paths at admission; full actual system dependencies must match candidate-normalized closure.')
 for mode in ['previous','default','off','on']:
  cwd=(F/'projections'/name if mode=='previous' else T)/'port/dreamcast/game'
  flags=prefix.copy();expected=None if mode in ['previous','default'] else (0 if mode=='off' else 1)
  if expected is not None:flags.append('-D'+guard+'='+str(expected))
  out=F/'objects'/(name+'-'+mode)
  tasks[name+'-'+mode]=dict(cwd=str(cwd),unit=name,guard=guard,expected_guard=expected,command=flags+['-fstack-usage','-MMD','-MP','-MF',str(out)+'.d','-c',src,'-o',str(out)+'.o'],macro_command=flags+['-dM','-E',src],preprocess_command=flags+['-E','-P',src],full_system_dependency_command=flags+['-M','-MT',name+'-'+mode,'-MF',str(out)+'.full.d',src],strip_command=['/opt/toolchains/dc/sh-elf/bin/sh-elf-objcopy','--strip-debug',str(out)+'.o',str(out)+'.stripped.o'],diagnostic_only_added_flag='-fstack-usage on every object; same effective code flags within TU',output_prefix=str(out))
for rel in ['port/dreamcast/game/Makefile','port/dreamcast/game/game30.mk','port/dreamcast/game/subscreen.mk','port/dreamcast/game/crowd.mk','port/dreamcast/game/pace.mk','port/dreamcast/game/vmu_context.mk','port/dreamcast/game/dbgwarp.mk','port/dreamcast/kos-env.sh']:
 inputs[str(T/rel)]=pin(T/rel)
# Hash reusable broad system/tool manifests freshly; do not run any tool executable.
count=0
for f in ['system-header-pins.json.gz','toolchain-pins.json']:
 raw=(P/f).read_bytes();rows=json.loads(gzip.decompress(raw) if f.endswith('.gz') else raw)
 for row in rows:
  p=Path(row['path']);req(p.is_file() and sha(p)==row['sha256'] and str(p.resolve())==row['resolved_path'],'reusable manifest drift '+str(p));count+=1
extra=[pin(p) for p in Path('/opt/toolchains/dc/sh-elf/lib/gcc/sh-elf/15.2.0/include-fixed').rglob('*') if p.is_file()]

for h in ['crash-screen.h','subscreen.h','pipeline30.h','pace.h','vmu-context-options.h']:
 req(sha(B/'obj'/h)==sha(O/'obj'/h),'recorded generated header mismatch '+h);refs.append(B/'obj'/h)
put('references.json',[pin(p) for p in refs]);put('input-pins.json.gz',list(inputs.values()));put('tool-extra-pins.json',extra)
put('compile-contracts.json.gz',contracts);put('planned-tasks.json.gz',tasks);put('baseline-projections.json',baselines)
put('environment.json',dict(influencing_environment={k:os.environ.get(k) for k in ['CPATH','C_INCLUDE_PATH','CPLUS_INCLUDE_PATH','OBJC_INCLUDE_PATH','GCC_EXEC_PREFIX','COMPILER_PATH','LIBRARY_PATH','DEPENDENCIES_OUTPUT','SUNPRO_DEPENDENCIES','SOURCE_DATE_EPOCH']},required_execution=dict(RE4DC_KOS_BASE='/root/work/kos-re4dc-d367',KOS_BASE='/root/work/kos-re4dc-d367',PATH='/root/work/kos-re4dc-d367/utils/build_wrappers:/opt/toolchains/dc/sh-elf/bin:/usr/bin:/bin',TMPDIR=str(F/'temp'),SOURCE_DATE_EPOCH='1760000000'),absent=['/root/work/kos-ports/include','/opt/toolchains/dc/sh-elf/lib/gcc/sh-elf/15.2.0/specs'],startup='Pin/source candidate port/dreamcast/kos-env.sh, then verify complete influencing environment and exact tool resolution before and after each task. Real compiler driver/cc1plus/assembler/wrappers pinned via reused manifest. Consumer owns any future programme subprocess/plugin closure.'))
put('plan.json',dict(state='SOURCE_ONLY_PREPARATION_NO_ALLOCATION',source=HEAD,tree=str(T),own_namespace=str(M),future_output=str(F),task_order=['sscrn-previous','sscrn-default','sscrn-off','reset-previous','reset-default','reset-off','sscrn-on','reset-on'],fresh_controls_before_ON=6,actual_compiler_runs=0,actual_lease=False,guard_defaults=0,metadata_limit_bytes=524288,verified_reused_system_tool_pins=count,new_source_input_pins=len(inputs),fresh_baselines=2,previous_source=dict(sscrn='54ba44079c33117b8241a9277c3aecdce8b4f9ce',reset='575953b0bc039dbc716d3411e275be1d04313e2e'),future_proposal=dict(one_shared_lease=True,sequential=True,hard_bytes=33554432,soft_abort_bytes=25165824,estimated_peak_bytes=16777216,root_allocation_required=True,no_make_link_programme_stage_image_guest=True,no_retry=True),default_OFF_gate='For each TU require previous/default/explicit0 full -E -P identity and --strip-debug exact object equality under same flags; macros differ only named guard absent/0 (other source macros unchanged). Compare normalized complete dependencies and all allocated sections/relocations. Stop before ON if any failure.',old_reference_policy='C57 objects were pruned; canonical004 objects retained and pinned, with exact normalized C57 argv/generated headers. cManager.h changed after C57/004 but matches both selected previous commits and candidate. Old objects are provenance only, not fresh controls. Fresh previous full-TU controls use exact previous source and its verified dependency contract. Any optional old-object normalized identity comparison must report a disagreement, not waive it.',source_runtime_ownership='Main retains all runtime editing and integration; no shared runtime claims taken.',programme_tool_closure_certified=False))
print(json.dumps(dict(status='SOURCE-ONLY PACKET CREATED; no compiler/preprocessor/lease',metadata_dir=str(M),source=HEAD,pins=len(inputs),manifest_records=count,tasks=len(tasks))))