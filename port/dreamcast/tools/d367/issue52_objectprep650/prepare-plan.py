from pathlib import Path
import gzip,hashlib,json,os,shlex,subprocess
T=Path('/root/probe/codex-mipmap21-next650');OWN=Path('/root/probe/codex-issue52-objects')
M=OWN/'port/dreamcast/tools/d367/issue52_objectprep650'
C=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/issue52-650-objectprep-20261022')
B=Path('/root/probe/texture-rect21-canonical36-link-20261021-01')
E=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/texture-rect21-20261021/canonical-programme-01')
P=E.parent/'canonical-programme-plan-01/plan02.json';FUTURE=Path('/root/probe/issue52-650-sh4-objects-20261022-01')
SOURCE='33504b9df434b82cd92e7bab3bb4630663a72ddd';BASE='0425534d848973c1dae3ab960d0006ac9afcf363'
def require(x,msg):
 if not x:raise RuntimeError(msg)
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024**2),b''):h.update(b)
 return h.hexdigest()
def git(*args,cwd=T):return subprocess.check_output(['git',*args],cwd=cwd,text=True).strip()
def row(p):return dict(path=str(p),resolved_path=str(p.resolve()),bytes=p.stat().st_size,sha256=sha(p))
def emit(name,data,gz=False):
 b=(json.dumps(data,indent=2)+'\n').encode()
 if gz:b=gzip.compress(b,mtime=0)
 for root in (M,C):(root/name).write_bytes(b)
def walk(root):
 seen=set()
 for base,dirs,fs in os.walk(root,followlinks=True):
  real=os.path.realpath(base)
  if real in seen:dirs[:]=[];continue
  seen.add(real)
  for f in fs:
   p=Path(base)/f
   if p.is_file():yield p
require(git('rev-parse','HEAD')==SOURCE and not git('status','--porcelain'),'candidate not clean frozen33504')
require((not M.exists() or not any(M.iterdir())) and (not C.exists() or not any(C.iterdir())) and not FUTURE.exists(),'preserve existing namespace/output')
M.mkdir(exist_ok=True);C.mkdir(exist_ok=True)
sealed=json.loads((E/'qualification-final.json').read_text());plan=json.loads(P.read_text())
require(sealed['source']==BASE and sealed['programme_sha256']=='733afabf6567a9f086eacb48b70559aef764cf52a5b534f44602da3a8bc68a9e' and sealed['ELF_sha256']=='69f2e7db588f515f4e6a67455d627a74fc17132d5ca20a591db4e0f15deedcae','canonical binding mismatch')
for f,key in [('program.bin','programme_sha256'),('re4dc-game.elf','ELF_sha256')]:require(sha(E/f)==sealed[key],'sealed final identity drift '+f)
require(sha(P)=='ace4795913750dca3ca8647b3551d61d9685a6dce51dc1d9d4107760c5a7f881','sealed plan drift')
closure=json.loads((E/'actual-complete-dependency-closure.json').read_text());canon={r['path']:r for r in closure}
# Recorded canonical headers/source are reused only after independent hash verification.
for r in closure:require(Path(r['path']).is_file() and sha(Path(r['path']))==r['sha256'],'canonical dependency drift '+r['path'])
changes=['port/dreamcast/game/platform/native_static.cpp','port/dreamcast/tools/d367/texture_rect21/scoped_representations.inc','port/dreamcast/tools/d367/texture_rect21/provenance_certificates.inc','port/dreamcast/tools/d367/texture_rect21/world_rect_bind.h','port/dreamcast/tools/d367/texture_rect21/world_rect_provenance.h']
source_delta=[]
for p in changes:
 old=subprocess.check_output(['git','show',BASE+':'+p],cwd=T);now=(T/p).read_bytes()
 source_delta.append(dict(path=p,base_git_blob=git('rev-parse',BASE+':'+p),candidate_git_blob=git('rev-parse',SOURCE+':'+p),base_sha256=hashlib.sha256(old).hexdigest(),candidate_sha256=hashlib.sha256(now).hexdigest(),candidate_bytes=len(now)))
# The native_ui caller is unchanged; changed transitive headers/table are the UI unit under test.
u='port/dreamcast/game/platform/native_ui.cpp';require(subprocess.check_output(['git','show',BASE+':'+u],cwd=T)==(T/u).read_bytes(),'native_ui source differs from042 unexpectedly')
refs=[P,E/'qualification-final.json',E/'independent-program-qualification.json',E/'actual-complete-dependency-closure.json',E/'derived-rename.json',E/'inherited-resolved-knobs.txt',B/'run.sh',B/'worker.py',Path('/root/probe/d367-buildslot.sh')]
tasks={};deps={};input_paths=set();summaries=[]
for unit in ('native_ui','native_static'):
 for mode in ('default','off','on'):
  name=unit+'-'+mode;p=B/(name+'-task.json');r=json.loads(p.read_text());refs.extend([p,E/(name+'-receipt.json')])
  require(r['expected_guard']==('1' if mode=='on' else '0'),'sealed guard mismatch')
  out=FUTURE/'objects'/name;new={k:r[k][:] for k in ('command','macro_command','preprocess_command')}
  for key,args in new.items():
   require(args[0]=='kos-c++','unexpected compiler driver')
   args[0]='/root/work/kos-re4dc-d367/utils/build_wrappers/kos-c++'
   if key=='command':
    args[args.index('-o')+1]=str(out)+'.o';args[args.index('-MF')+1]=str(out)+'.d'
   # no source optimization, macro, forced header or language flag changes
  command=new['command'];baseargs=[];i=0
  while i<len(command):
   v=command[i]
   if v in ('-o','-MF'):i+=2;continue
   if v in ('-MMD','-MP','-c','-fstack-usage'):i+=1;continue
   if v=='platform/'+unit+'.cpp':i+=1;continue
   baseargs.append(v);i+=1
  new['full_dependency_command']=baseargs+['-M','-MT',name,'-MF',str(out)+'-full.d','platform/'+unit+'.cpp']
  new.update(cwd=str(T/'port/dreamcast/game'),expected_guard=r['expected_guard'],output_prefix=str(out),canonical_task_sha256=sha(p),canonical_task=str(p))
  tasks[name]=new
  d=B/'objects'/(name+'.d');refs.append(d)
  line=d.read_text().replace('\\\n',' ').splitlines()[0];paths=[]
  for text in shlex.split(line.split(':',1)[1]):
   q=Path(text);q=q if q.is_absolute() else Path(r['cwd'])/q;q=q.resolve()
   require(str(q) in canon,'actual .d source not in sealed closure '+str(q))
   require(sha(q)==canon[str(q)]['sha256'],'sealed .d source drift')
   rel=None
   try:rel=q.relative_to(Path('/root/probe/codex-texture-rect21'))
   except ValueError:pass
   mapped=T/rel if rel is not None else q
   require(mapped.is_file(),'candidate dependency missing '+str(mapped));input_paths.add(mapped)
   changed=rel is not None and str(rel) in changes
   require(changed or sha(mapped)==sha(q),'unexpected candidate dependency difference '+str(mapped))
   paths.append(dict(canonical_path=str(q),candidate_path=str(mapped),canonical_sha256=sha(q),candidate_sha256=sha(mapped),approved_changed_input=changed))
  deps[name]=paths
  oldreceipt=json.loads((E/(name+'-receipt.json')).read_text());summaries.append(dict(name=name,guard=r['expected_guard'],canonical_object=oldreceipt,argv_count=len(command),optimization_order=[x for x in command if x.startswith('-O')],actual_dependency_count=len(paths)))
# Broad system-header pins cover system inputs deliberately omitted by original -MMD.
sysroots=[Path('/opt/toolchains/dc/sh-elf/sh-elf/include'),Path('/opt/toolchains/dc/sh-elf/lib/gcc/sh-elf/15.2.0/include'),Path('/root/work/kos-re4dc-d367/include'),Path('/root/work/kos-re4dc-d367/kernel/arch/dreamcast/include'),Path('/root/work/kos-re4dc-d367/addons/include'),Path('/root/work/kos-ports/include')]
absent_sysroots=[str(root) for root in sysroots if not root.exists()]
require(absent_sysroots==['/root/work/kos-ports/include'],'unexpected missing include roots')
sysroots=[root for root in sysroots if root.is_dir()]
system={str(p.resolve()):p for root in sysroots for p in walk(root)}
wrappers=Path('/root/work/kos-re4dc-d367/utils/build_wrappers')
tools=[wrappers/'kos-c++',wrappers/'kos-cc',Path('/opt/toolchains/dc/sh-elf/libexec/gcc/sh-elf/15.2.0/cc1plus')]
tools += [Path('/opt/toolchains/dc/sh-elf/bin')/('sh-elf-'+name) for name in ('gcc','g++','as','objcopy','readelf','nm','size')]
tools += [Path('/root/work/kos-re4dc-d367')/name for name in ('environ_base.sh','environ_dreamcast.sh')]
tools += [T/'port/dreamcast/kos-env.sh',Path('/usr/bin/bash'),Path('/usr/bin/python3'),Path('/root/probe/d367-buildslot.sh')]
for p in tools:require(p.is_file(),'tool input missing '+str(p))
# Include all candidate guarded headers even when a default/off preprocessor omits them.
input_paths.update(T/p for p in changes);input_paths.add(T/u)
emit('canonical-references.json',[row(p) for p in sorted(set(refs))])
emit('candidate-source-delta.json',source_delta)
emit('planned-tasks.json',tasks)
emit('actual-dependency-mapping.json.gz',deps,True)
emit('candidate-input-pins.json.gz',[row(p) for p in sorted(input_paths)],True)
emit('system-header-pins.json.gz',[row(p) for p in system.values()],True)
emit('toolchain-pins.json',[row(p) for p in sorted(set(tools))])
emit('compiler-environment.json',dict(absent_include_roots=absent_sysroots,influencing_environment={k:os.environ.get(k) for k in ('CPATH','C_INCLUDE_PATH','CPLUS_INCLUDE_PATH','OBJC_INCLUDE_PATH','GCC_EXEC_PREFIX','COMPILER_PATH','LIBRARY_PATH','DEPENDENCIES_OUTPUT','SUNPRO_DEPENDENCIES','SOURCE_DATE_EPOCH')},startup_script=str(B/'run.sh'),candidate_kos_env_sha256=sha(T/'port/dreamcast/kos-env.sh'),retained_forced_header_root='/root/probe/texture-rect21-program-pair-20261021-01/obj'))
emit('canonical-controls.json',summaries)
emit('preparation.json',dict(source=SOURCE,base_source=BASE,base_programme=sealed['programme_sha256'],base_ELF=sealed['ELF_sha256'],canonical_dependency_closure_verified=len(closure),candidate_pinned_inputs=len(input_paths),system_header_pins=len(system),compiler_version=subprocess.check_output(['/opt/toolchains/dc/sh-elf/bin/sh-elf-g++','--version'],text=True).splitlines()[0],native_ui_source_exact_base=True,status='PREPARED ONLY: zero compilation/preprocessing/linking performed',future_output=str(FUTURE),runtime_source_owned_by_main=True,buildslot_disposition='One shared d367 slot held across six sequential object tasks; no make/full link/stage/guest. Explicit root allocation required.',requested_future_cap_bytes=32*1024**2,estimated_future_peak_bytes=24*1024**2,metadata_source_plus_mirror_limit_bytes=2*1024**2,root_global_budget_bytes=64*1024**2))
# Bound metadata writes in both locations; no compiler or preprocessor commands are executed.
bytes_=sum(p.stat().st_size for root in (M,C) for p in root.rglob('*') if p.is_file());require(bytes_<2*1024**2,'metadata source/mirror budget')
print(json.dumps(dict(source=SOURCE,verified_canonical_inputs=len(closure),candidate_inputs=len(input_paths),system_headers=len(system),metadata_source_and_mirror_bytes=bytes_,planned_tasks=len(tasks),no_builds=True)))

