"""Read-only provenance capture for current C57 QA; never invokes target tools."""
from pathlib import Path
import gzip,hashlib,json,shlex,struct,subprocess,os,math
TREE=Path('/root/probe/codex-issue52-objects')
ROOT=Path('/root/probe/codex-cache21-integration-next')
NS=TREE/'port/dreamcast/tools/d367/issue52_cache_currentqa_plan'
C=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/issue52-cache-currentqa-plan-20261022')
LANE=Path('/mnt/c/Game Dev/Emulators/codex-lanes/issue52-cache-currentqa-plan')
OLD=Path('/root/probe/texture-rect21-program-pair-20261021-01')
QA=Path('/root/probe/cache21-ganado-reader-build-20261021')
ON=QA/'on-01';OFF=QA/'off-01'
OBJ=OLD/'obj';QOBJ=ON/'obj';HELP=ROOT/'port/dreamcast/game/obj/ovlh'
EIGHT=Path('/root/probe/issue52-cache-repairs-sh4-objects-20261022-01')
PRIOR=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/issue52-cache-programme-prep02-20261022')
C57='c57ff60f0f462fdd2c419883b0258963504d756a';RUNTIME='babfaa7d8ee868c9b81305aef7024ffd543eb6f6'
sha=lambda b:hashlib.sha256(b).hexdigest()
def pin(p):
 p=Path(p);return {'p':str(p),'b':p.stat().st_size,'sha':sha(p.read_bytes())}
def gitblob(commit,rel):return subprocess.check_output(['git','show',commit+':'+rel],cwd=TREE)
def gitid(p):return subprocess.check_output(['git','rev-parse','HEAD'],cwd=p,text=True).strip()
def norm(s):return s.replace(str(QOBJ),'OBJ').replace(str(OFF/'obj'),'OBJ').replace(str(OBJ),'OBJ').replace(str(ROOT),'TREE').replace('/root/probe/codex-texture-rect21','TREE')
def canon(a):return [norm(s) for s in a]
def js(d):return json.dumps(d,sort_keys=True,separators=(',',':')).encode()+b'\n'
def deps(p):
 s=p.read_text().replace('\\\n',' ');return shlex.split(s.split(':',1)[1].split('\n',1)[0])
def elf_projection(p):
 b=p.read_bytes();assert b[:6]==b'\x7fELF\x01\x01';h=struct.unpack_from('<HHIIIIIHHHHHH',b,16);entry,phoff,shoff,flags=h[3:7];phsz,phn,shsz,shn,stridx=h[8:13]
 ss=[struct.unpack_from('<IIIIIIIIII',b,shoff+i*shsz)for i in range(shn)];st=ss[stridx];names=b[st[4]:st[4]+st[5]]
 def name(i):return names[i:names.index(0,i)].decode()
 allocated=[]
 for s in ss:
  if s[2]&2:allocated.append({'n':name(s[0]),'t':s[1],'f':s[2],'a':s[3],'b':s[5],'align':s[8],'entry':s[9],'sha':None if s[1]==8 else sha(b[s[4]:s[4]+s[5]])})
 loads=[]
 for i in range(phn):
  p0=struct.unpack_from('<IIIIIIII',b,phoff+i*phsz)
  if p0[0]==1:loads.append(dict(zip(['type','offset','vaddr','paddr','filesz','memsz','flags','align'],p0),sha=sha(b[p0[1]:p0[1]+p0[4]])))
 d={'machine':h[1],'entry':entry,'flags':flags,'allocated':allocated,'PT_LOAD':loads,'NOBITS':'Size/address/flags/alignment preserved; no file bytes. PT_LOAD memsz-filesz/BSS semantics mandatory.'};d['projection_sha']=sha(js(d));return d
assert not NS.exists() and not C.exists()
assert gitid(TREE)=='20133f9ea4593e456e61648166eb15e0056fc121'
assert not subprocess.check_output(['git','status','--porcelain'],cwd=TREE,text=True)
# Buildlog text is source provenance only; no command below invokes GCC, make, ld, objcopy or lease.
oldlog=(OLD/'out-off/build.log').read_text().splitlines();onlog=(ON/'build.log').read_text().splitlines();offlog=(OFF/'build.log').read_text().splitlines()
inv=json.load(open(OLD/'out-off/object-file-identities.json'));invmap={r['path']:r for r in inv}
olddeps={r['path']:r for r in json.load(open(OLD/'out-off/actual-dependency-closure.json'))}
oldmatrix=json.loads(gzip.decompress((PRIOR/'object-matrix.json.gz').read_bytes()))
oldlink=json.loads(gzip.decompress((PRIOR/'link-plan.json.gz').read_bytes()))
partial=next((i+1,shlex.split(s))for i,s in enumerate(onlog)if s.startswith('sh-elf-ld ')and'/em10g.o.tmp'in s)
strip=next((i+1,shlex.split(s))for i,s in enumerate(onlog)if s.startswith('sh-elf-objcopy ')and'/em10g.o.tmp'in s)
constituents=[Path(s)for s in partial[1]if s.endswith('.o')];assert len(constituents)==14
module=[];allcommands=[]
for j,p in enumerate(constituents):
 rel=p.relative_to(QOBJ);op=OBJ/rel
 row=invmap[str(op)];assert sha(op.read_bytes())==row['sha256']
 ci,ca=next((i+1,shlex.split(s))for i,s in enumerate(onlog)if' -c 'in s and shlex.split(s)[-1]==str(p))
 oi,oa=next((i+1,shlex.split(s))for i,s in enumerate(oldlog)if' -c 'in s and shlex.split(s)[-1]==str(op))
 same=canon(ca)==canon(oa);target=j==0
 assert same or(target and canon([s for s in ca if s!='-DRE4DC_GANADO_ROUTINE_BYTES=1'])==canon(oa))
 dp=p.with_suffix('.d');delta=[];closure=[]
 if dp.exists():
  for d in sorted(set(deps(dp))):
   if d.startswith('../../../'):
    relative=os.path.normpath(d[9:]);bb=gitblob(C57,relative);oldp='/root/probe/codex-texture-rect21/'+relative
   elif d.startswith('platform/')or d=='gx_fast.h':
    relative='port/dreamcast/game/'+d;bb=gitblob(C57,relative);oldp='/root/probe/codex-texture-rect21/'+relative
   else:
    pp=Path(d) if d.startswith('/')else ROOT/'port/dreamcast/game'/d;bb=pp.read_bytes();relative=str(pp);oldp=norm(str(pp))
   h0=olddeps.get(oldp);eq=h0 is not None and sha(bb)==h0['sha256'];closure.append([relative,sha(bb),len(bb),eq])
   if not eq:delta.append(relative)
  # Exactly one source changed in the em10 TU; all thirteen reusable constituents have exact input contracts.
  assert delta==(['src/em10/em10.cpp']if target else []),(str(rel),delta)
 else:
  sp=Path(ca[ca.index('-c')+1]);assert sp.read_bytes()==(OBJ/sp.relative_to(QOBJ)).read_bytes();closure=[[str(sp),sha(sp.read_bytes()),sp.stat().st_size,True]]
 module.append({'i':j,'r':str(rel),'old':{'b':row['bytes'],'sha':row['sha256']},'on_line':ci,'old_line':oi,'normalized_flags_equal':same,'rebuild':target,'source_delta':delta,'d':pin(dp)if dp.exists()else None,'deps':closure})
 allcommands.append({'i':j,'argv':ca,'old_argv':oa})
assert sha((QOBJ/'mod/em10g/state.ld').read_bytes())==sha((OBJ/'mod/em10g/state.ld').read_bytes())
# Exact OFF/default compiler argv and generated inputs versus the already completed eight-TU unit.
cache=[]
for name,source in [('sscrn','sscrn_bridge.cpp'),('reset','../../../src/game/main.cpp')]:
 li,ca=next((i+1,shlex.split(s))for i,s in enumerate(onlog)if' -c '+source+' -o 'in s)
 prev=json.load(open(EIGHT/(name+'-default-object-command.json')));a=prev['argv'];k=a.index('-fstack-usage');a=a[:k]+['-MMD','-MP','-c',source,'-o','OUT'];a[0]=ca[0];cb=ca[:];cb[-1]='OUT';assert canon(a)==canon(cb)
 cache.append({'tu':name,'qa_compile_line':li,'qa_argv':ca,'eight_argv_pin':pin(EIGHT/(name+'-default-object-command.json')),'flags_exact_after_only_stack_dependency_output_instrumentation_removed':True,'old_header':{'sha':'19ce63044d273bce47c208773df8921f08f90fc58bdfc162e7bb9507f5940e3c','from':C57},'current_header':pin(ROOT/'include/cManager.h'),'OFF_programme_identity_still_required':True,'objects':{v:pin(EIGHT/'objects'/(name+'-'+v+'.o'))for v in ['default','off','on']}})
generated=[]
for n in ['pace.h','vmu-context-options.h','act-cap.h']:
 assert (QOBJ/n).read_bytes()==(OBJ/n).read_bytes();generated.append({'qa':pin(QOBJ/n),'old':pin(OBJ/n),'exact':True})
# Current selected QA payloads are read-only historical observations, not fresh programme acceptance.
receiptpath=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/cache21-extended-20261021/ganado-reader-enabled-v1.json');receipt=json.load(open(receiptpath))
assert sha((ON/'program.bin').read_bytes())==receipt['program_sha256'];assert sha((ON/'re4dc-game.elf').read_bytes())==receipt['elf_sha256']
for r in receipt['overlays']:assert sha((ON/r['name']).read_bytes())==r['sha256']
qa={'source':C57,'recipe':pin(ON/'candidate.txt'),'resolved':pin(ON/'resolved-knobs.txt'),'build_log':pin(ON/'build.log'),'owned_build':pin(ON/'owned-build.json'),'receipt':pin(receiptpath),'programme':pin(ON/'program.bin'),'elf':pin(ON/'re4dc-game.elf'),'image_reference_only':'da10104f6d4e28c6e4509a9fb75182fc4612f89a411ed4c1efa85d8a6c8bde7f','image_not_rehashed_or_staged_here':True,'overlays':[pin(ON/r['name'])for r in receipt['overlays']],'projection':elf_projection(ON/'re4dc-game.elf')}
# All helper objects survived with the current QA paths in the frozen moves manifest.
moves=(HELP/'moves.tsv').read_text().splitlines();assert len(moves)==188 and all('/em10g.o\t'not in s for s in moves)
assert all(str(QOBJ)in s for s in moves)
helpers=[pin(p)for p in sorted(HELP.glob('*.o'))];assert len(helpers)==43
context={p.name:pin(p)for p in HELP.iterdir()if p.is_file()and not p.name.endswith('.o')}
# Derive an explicit immutable-input argv template from the historical structural link plan.
# Swapping to current-QA helper objects is explicit, not a claim that the older canonical programme is QA52190.
argv=oldlink['base_argv'][:];objects=[];future='FRESH_C57_GANADO1_EM10G.o'
for i,s in enumerate(argv):
 if not s.endswith('.o'):continue
 if '/obj/ovlh/'in s:s=str(HELP/Path(s).name);argv[i]=s
 if s.endswith('/obj/mod/em10g.o'):argv[i]=future;objects.append({'argv_i':i,'future':future,'derived_from':'module-reconstruction.json.gz'});continue
 p=Path(s);objects.append({'argv_i':i,**pin(p),'provenance':'C57_ON_helper'if p.parent==HELP else'inherited_original_QA_explicit_historical_basis'})
assert len(objects)==447
# Existing source plan's old native UI/texture snapshots are intentional original-QA OFF bytes, not later mutated .o paths.
fullplan={'argv':argv,'objects':objects,'old_framework_reference':pin(PRIOR/'link-plan.json.gz'),'context':'Private fresh copied script context. Rewrite only owned OUT/script-context paths and declared object replacements; do not run retained tools/link.sh or mutate old ovlh.','KOS_LDFLAGS':oldlink['base_environment']['KOS_LDFLAGS'],'other_environment':oldlink['base_environment'],'replacements':oldlink['replacements'],'C57_context':context,'C57_helpers':helpers,'C57_moves':pin(HELP/'moves.tsv'),'moves_count':len(moves),'em10g_moved':False,'QA_full_payload_gate':'52190ed293d8e62238bcad40fd351d35a965b253ad5b59cda570d0de34187e45 plus all14 selected QA overlays plus ELF allocated/loadable projection BEFORE enabled link','notes':'argv template still references originalQA SS/main; futureOFF selects existing qualified default objects at explicit indices, futureON selects qualified ON. Fresh Ganado module shared by both. Exact resolved absolute argv/env must be sealed by main controller before execution.'}
# Source references are hashes, never source copies/temporary baseline views in this allocation.
refs=[pin(p)for p in [OLD/'out-off/object-file-identities.json',OLD/'out-off/actual-dependency-closure.json',OLD/'out-off/build.log',OFF/'build.log',OFF/'candidate.txt',OFF/'program.bin',OFF/'re4dc-game.elf',EIGHT/'object-gates.json',EIGHT/'final-audit.json',EIGHT/'execution-environment.json',EIGHT/'extra-pins.json',PRIOR/'SHA256SUMS',PRIOR/'object-matrix.json.gz']if p.exists()]
sourcepins={r:pin(ROOT/r)for r in ['include/cManager.h','src/em10/em10.cpp','src/game/main.cpp','port/dreamcast/game/sscrn_bridge.cpp','port/dreamcast/game/Makefile','port/dreamcast/game/game30.mk']}
plan={'state':'SOURCE_ONLY_CURRENT_QA_PLAN_NOT_ALLOCATED','source_runtime':RUNTIME,'source_docs_observed':gitid(ROOT),'old_20133':'Historical8942 reference only; not selected and never relabeled currentQA.','matrix':{'current_QA_OFF':{'GANADO_ROUTINE_BYTES':1,'EVENT_MANAGER_STORAGE_FLAGS':0,'SS_RESTORE_VALIDATE_FIRST':0,'RESET_RETIRE_BEFORE_HEAPS':0},'two_new_repairs':{'GANADO_ROUTINE_BYTES':1,'EVENT_MANAGER_STORAGE_FLAGS':0,'SS_RESTORE_VALIDATE_FIRST':1,'RESET_RETIRE_BEFORE_HEAPS':1},'full_Event1':'HOLD; incompatible old Event proof not reusable as QA contract. Fresh actual QA projection/object closure separately required.'},'fixed':{'ACTOR_TRANSACTION':1,'ACTOR_LEON_NATIVE_LOOK':1,'VMU_DIALOG':1,'all15_cache_guards':0,'CABIN_SOURCE':0,'SS_WINDOW_HOLD_RESTORE':0},'fresh_compiler_proposal':{'count':2,'order':['original C57 em10 fullTU GANADO omitted/0 baseline control matching retained original-QA allocated/relocation/stripped object','original C57 em10 fullTU GANADO1 under exact C57 ON argv/dependency contract'],'why':'Only one target-specific macro changes; thirteen other module constituents have matching normalized argv and exact input identities. Existing eight-TU SS/main controls have exact QA flag/generated-header contract; no automatic fresh compile needed if sealed tools/headers/env/objects still match. Any drift is STOP/root review, not silent refresh.','source_view':'Future bounded real baseline directory ancestors plus exact C57 em10 source and C57 header/input blobs where historical contract requires; symlink escaping prohibited. This is explicit historical C57 module reconstruction, not current-root-source qualification. Never swap historical cManager into current SS/main or claim current-source adoption for inherited objects.','fresh_compile_projection':'Pin all full system headers/env/wrapper/real cc1plus/as/tools/plugins pre/post; resolved macros/full dependencies/-E-P/object/stripped/allocated sections/relocs/stack; exact symbols and owner flags. Prior current-header wholeTU OFF equality is not fullQA identity.'},'future_execution':['Main seals final exact input/source/header/tool/argv/env/lease/resource/trace controller, after common runner real trace gaps fixed.','Two fresh em10 compiler tasks, sequential. Fail closed on any missing dependency/source/tool pin, drift or OFF object mismatch.','Reconstruct single GANADO1 em10g module: fresh first constituent plus13 retained exact matching constituents; exact state.ld/order/partialld+objcopy symbols. Preserve temporary and final receipts.','Fresh currentQA OFF full programme with qualified SS/main default objects. Require raw52190, all14 exact and allocated/loadable ELF signature including BSS before allowing enabled link. Full new debug ELF SHA recorded separately. Any mismatch retained; no waiver or header substitution.','Only after OFF succeeds, SS/main ON two-new-repair link/all14 binding. This is linkage only, not Flycast/source-state acceptance.','New programme/ELF/DWARF/ABI bound cold fixture and later allocated guest. Do not reuse8942 or prior52190 states across new programme identities.'],'budgets':{'metadata_hard_bytes':1048576,'global_source_peer_bytes':67108864,'future_proposal_only':{'compiler_objects_views_traces_reserve_bytes':33554432,'programme_pair_soft_bytes':234881024,'programme_pair_hard_bytes':268435456,'one_shared_lease':True,'no_stage_image_guest':True,'fresh_floor_and_peer_admission_by_root':True}},'runs':{'compiler':0,'preprocessor':0,'linker':0,'lease':0,'programme':0,'stage':0,'guest':0},'main_owns':'Runtime, review, actual matrix/controller/allocation; production owner Claude unchanged.'}
files={
 'plan.json':js(plan),'qa52190.json':js(qa),'cache-object-contract.json':js({'rows':cache,'generated':generated,'sourcepins':sourcepins,'eight_source':'babfaa7d8','Event0':True,'current_vs_historical_header_gap_must_pass_full52190_gate':True}),
 'module-reconstruction.json.gz':gzip.compress(js({'prefix':str(QOBJ),'oldprefix':str(OBJ),'constituents':module,'commands':allcommands,'partial_link':{'line':partial[0],'argv':partial[1]},'objcopy':{'line':strip[0],'argv':strip[1]},'state_ld':pin(QOBJ/'mod/em10g/state.ld'),'GANADO0_original_command':next(shlex.split(s)for s in offlog if' -c 'in s and s.endswith('/mod/em10g/shared/src/em10/em10.o'))}),mtime=0),
 'link-input-template.json.gz':gzip.compress(js(fullplan),mtime=0),'references.json':js(refs),
 'source-blob-pins.json':js({'C57_em10':{'sha':sha(gitblob(C57,'src/em10/em10.cpp')),'bytes':len(gitblob(C57,'src/em10/em10.cpp'))},'C57_cManager':{'sha':sha(gitblob(C57,'include/cManager.h')),'bytes':len(gitblob(C57,'include/cManager.h'))},'runtime':sourcepins,'no_source_view_materialized':True}),
 'tool-closure-reuse.json':js({'framework_only':'Common consumer trace/tool closure, no duplication or source qualification claims for target programme','preferred_source':'8a210d5c1ec9b1c2428f0cd0ad3b9ed5aea2c1c2','source_seal':'5713b205e311effcfc0d8280962928e6d15b174792537b77b207d6e6fb6aa92d','namespace':'texture-consumers21-next792-runner02-20261022','driver_profile':'Exact one exclusive G++ cc*.res create/unlink, same creator PID, no reads/writes, postabsence. NOT a generic transient allowlist. Actual linker lifecycle separately strict.','mandatory':'Main verifies real-trace gaps fixed before reuse and seals actual cache-specific controller. Fresh per-unit source/header/tool/plugin/loader/env/exec/open pre/post; separate actual GCC-selected ld and toolbin ld pins. No missing-prepin waiver; ac552/older650/failedprogramme evidence immutable.','controller_implemented_here':False})}
assert sum(len(b)for b in files.values())<180000
NS.mkdir();C.mkdir()
# At most3 allocated copies + estimated Git objects + closeout/controller-prep footprint; admission before writes.
forecast=3*sum(math.ceil(len(b)/4096)*4096 for b in files.values())+196608
assert forecast<1048576,forecast
for n,b in files.items():(NS/n).write_bytes(b);(C/n).write_bytes(b)
print(json.dumps({'files':{k:len(v)for k,v in files.items()},'forecast':forecast,'module_reused':13,'module_fresh':1,'objects':len(objects),'new_source':str(NS),'new_evidence':str(C),'qa':qa['programme']['sha']}))
