"""Compact successor metadata preparation. No compiler/preprocessor/linker execution."""
from pathlib import Path
import collections,gzip,hashlib,json,math,os,shlex,subprocess
T=Path('/root/probe/codex-cache21-integration-next');OWN=Path('/root/probe/codex-issue52-objects');R=Path('/root/probe/codex-texture-rect21');O=Path('/root/probe/texture-rect21-program-pair-20261021-01');D=O/'out-off';Q=Path('/root/probe/issue52-cache-repairs-sh4-objects-20261022-01');C=Path('/root/probe/codex-mipmap21-alpha-reader')
L=Path('/mnt/c/Game Dev/Emulators/codex-lanes/issue52-cache-programme-prep02');M=OWN/'port/dreamcast/tools/d367/issue52_cache_programme_prep02';E=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/issue52-cache-programme-prep02-20261022');B=Path('/root/probe/cache21-two-repairs-programme-20261022-01')
PL=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/texture-rect21-20261021/canonical-programme-plan-01/plan02.json');FAIL=Path('/mnt/c/Game Dev/Emulators/codex-lanes/issue52-cache-programme-prep')
HEAD='2fd3c17aa083845ada3c1c31bb0e3f311402cd6e';RUN='babfaa7d8ee868c9b81305aef7024ffd543eb6f6';CAP=524288
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def req(c,s):
 if not c:raise RuntimeError(s)
def git(*a,cwd=T):return subprocess.check_output(['git',*a],cwd=cwd)
def pin(p):p=Path(p);return dict(path=str(p),bytes=p.stat().st_size,sha256=sha(p),resolved=str(p.resolve()))
def allocated():
 return sum(max(p.stat().st_blocks*512,math.ceil(p.stat().st_size/4096)*4096) for root in (L,M,E) if root.exists() for p in root.rglob('*') if p.is_file() and not p.is_symlink())
def put(n,x):
 raw=x if isinstance(x,bytes) else (json.dumps(x,separators=(',',':'))+'\n').encode();b=gzip.compress(raw,mtime=0) if n.endswith('.gz') else raw
 # Charge current source/lane plus an entire future mirror and Git/closeout
 # reserve before writing, including alignment. Never serialize broad raw rows.
 current=allocated();existing=sum(math.ceil(p.stat().st_size/4096)*4096 for p in M.iterdir() if p.is_file())
 forecast=current+existing+2*math.ceil(len(b)/4096)*4096+131072
 req(forecast<CAP,'compact source+futuremirror+Git reserve would exceed512KiB '+n)
 (M/n).write_bytes(b)
req(git('rev-parse','HEAD').decode().strip()==HEAD and not git('status','--porcelain').strip(),'source not clean docs2fd')
req(not git('diff',RUN,HEAD,'--','include','src','port/dreamcast/game','port/dreamcast/room').strip(),'runtime differs frombabfaa')
req(not B.exists() and not E.exists(),'fresh future/mirror namespace required')
req(not M.exists() or {p.name for p in M.iterdir()}=={'prepare.py'},'preserve populated packet')
M.mkdir(exist_ok=True)
put('prepare.py',Path(__file__).read_bytes())
plan=json.loads(PL.read_text());inventory=json.loads((D/'object-file-identities.json').read_text());invmap={r['path']:(i,r) for i,r in enumerate(inventory)};closure=json.loads((D/'actual-dependency-closure.json').read_text());oldpins={r['path']:r for r in closure}
lines=(D/'build.log').read_text().splitlines();linkline=[(i+1,l) for i,l in enumerate(lines) if 'bash tools/link.sh' in l];req(len(linkline)==1,'ambiguous actualQA link')
original=shlex.split(linkline[0][1]);objs=[Path(v) for v in original if v.endswith('.o')];req(len(objs)==446,'object count')
commands={};module_steps=collections.defaultdict(list)
for no,line in enumerate(lines,1):
 if line.startswith(('kos-c++ ','kos-cc ')):
  a=shlex.split(line)
  if '-c' in a and '-o' in a:commands[a[a.index('-o')+1]]=no
 if line.startswith(('sh-elf-ld ','sh-elf-objcopy ','bash tools/build-')):
  for p in objs:
   if '/mod/' in str(p) and (str(p) in line):module_steps[str(p)].append(no)
qasnap={str(O/'obj/native-reuse/texture_package.o'):O/'off-texture_package.o',str(O/'obj/platform/native_ui.o'):O/'off-native_ui.o'}
changed=[];changedmap={};candidatepins=[]
for r in closure:
 p=Path(r['path'])
 try:rel=p.relative_to(R);q=T/rel
 except ValueError:continue
 req(q.is_file(),'candidate source input missing '+str(q))
 if sha(q)!=r['sha256']:
  i=len(changed);changedmap[str(p)]=i;changed.append(dict(i=i,relative=str(rel),old=r['sha256'],current=sha(q),bytes=q.stat().st_size));candidatepins.append(pin(q))
req(len(changed)==15,'changed input inventory drift')
def readdeps(p):
 raw=p.read_text()
 if p==O/'obj/platform/native_ui.d':
  raw=(O/'static-costs/off/native_ui.d').read_text().replace(str(O/'static-costs/off/native_ui.o'),str(O/'obj/platform/native_ui.o'),1)
  req(hashlib.sha256(raw.encode()).hexdigest()=='e6ab0fd495b11113b9ab9be21f13d5af3878a186f04a4c7831fbed3840b4493a','original OFF nativeUI dep recovery mismatch')
 line=raw.replace('\\\n',' ').splitlines()[0];out=[]
 for x in shlex.split(line.split(':',1)[1]):
  q=Path(x);q=q if q.is_absolute() else R/'port/dreamcast/game'/q;out.append(str(q.resolve()))
 return out
rows=[];affected=collections.defaultdict(list);module_rows=[];module_hits={};counts=collections.Counter()
for i,p in enumerate(objs):
 selected=qasnap.get(str(p),p)
 req(str(p) in invmap and sha(selected)==invmap[str(p)][1]['sha256'],'original QA selected object pin drift '+str(selected))
 d=p.with_suffix('.d');deps=readdeps(d) if d.is_file() else [];hits=sorted({changedmap[q] for q in deps if q in changedmap})
 row=dict(i=i,r=str(p.relative_to(O/'obj')),sha=sha(selected),b=selected.stat().st_size,override=str(selected.relative_to(O)) if selected!=p else None,cl=commands.get(str(p)),dsha=('e6ab0fd495b11113b9ab9be21f13d5af3878a186f04a4c7831fbed3840b4493a' if p==O/'obj/platform/native_ui.o' else sha(d)) if d.is_file() else None,dc=len(deps),delta=hits)
 counts['all']+=1;counts['direct_d']+=d.is_file();counts['compile_line']+=str(p) in commands;counts['direct_affected']+=bool(hits)
 for h in hits:affected[h].append(i)
 if p.parent.name=='mod':
  prefix=str(p.with_suffix(''))+'/'
  members=[j for j,r in enumerate(inventory) if r['path'].startswith(prefix)]
  req(members,'sealed module constituent inventory missing '+str(p));mh=set();ds=0;source_commands=[]
  for j in members:
   r=inventory[j];q=Path(r['path']);req(q.is_file() and sha(q)==r['sha256'],'sealed module constituent drift '+str(q))
   if q.suffix=='.d':ds+=1;mh.update(changedmap[s] for s in readdeps(q) if s in changedmap)
   if str(q) in commands:source_commands.append(commands[str(q)])
  steps=module_steps[str(p)];req(steps,'sealed module producer step missing '+str(p));row['module']=len(module_rows);module_rows.append(dict(object_id=i,inventory_indices=members,dependency_files=ds,changed=sorted(mh),build_log_steps=steps,compile_log_steps=sorted(set(source_commands)),current_source_qualified=False));module_hits[i]=sorted(mh)
 counts['d_exact_without_delta']+=bool(d.is_file() and not hits)
 row['current_contract']='prior_bytes_only_projection_required' if hits else ('recorded_inputs_exact' if d.is_file() else 'sealed_composite_or_producer_only')
 rows.append(row)
req(counts['direct_affected']==258 and len(affected[changedmap[str(R/'include/cManager.h')]])==252,'direct census drift')
# Source/event receipts are semantic references, not falsely reused QA objects.
eventdir=T/'port/dreamcast/tools/d367/cache21';event=json.loads((eventdir/'event-storage-event-sh4.json').read_text());eventcmd=event['variants']['default']['command'];qaevent=next(r for r in rows if r['r']=='src/game/event.o');qaargv=shlex.split(lines[qaevent['cl']-1]);event_def=lambda a:{v[2:].split('=',1)[0]:v[2:].split('=',1)[1] if '=' in v else '1' for v in a if v.startswith('-D')}
a=event_def(eventcmd);b=event_def(qaargv);different={k:[a.get(k),b.get(k)] for k in sorted(a.keys()|b.keys()) if a.get(k)!=b.get(k)}
# Derive one exact base direct argv from the preserved canonical link census,
# reverting canonical UI/static replacements to original QA bytes. No new792.
base=plan['future_direct_link_argv'].copy();base[0]='/root/work/kos-re4dc-d367/utils/build_wrappers/kos-c++'
for i,v in enumerate(base):
 if v.endswith('/objects/native_ui-on.o'):base[i]=str(O/'off-native_ui.o')
 elif v==str(O/'obj/native-reuse/texture_package.o'):base[i]=str(O/'off-texture_package.o')
 elif v.endswith('/objects/native_static-linked.o'):base[i]=str(R/'port/dreamcast/game/obj/ovlh/o1_native_static.o')
 elif v.endswith('re4dc-game.elf') and i>0 and base[i-1]=='-o':base[i]=str(B/'ARM/re4dc-game.elf')
# All448? entries are byte-bound by retained source/object/library/support records.
linkobjects=[Path(v) for v in base if v.endswith('.o')];req(len(linkobjects)==447,'direct final census')
for p in linkobjects:req(p.is_file(),'missing final linked object '+str(p))
for row in plan['frozen_overlay_derived_objects']:req(sha(Path(row['derived']['path']))==row['derived']['sha256'],'frozen derived helper drift')
replacement_indices={k:base.index(str(O/'obj'/v)) for k,v in dict(sscrn='sscrn_bridge.o',reset='src/game/main.o').items()}
replacements={}
for arm,mode in [('off','default'),('two-repairs','on')]:
 replacements[arm]={str(idx):pin(Q/'objects'/(unit+'-'+mode+'.o')) for unit,idx in replacement_indices.items()}
 for r in replacements[arm].values():req(sha(Path(r['path']))==r['sha256'],'fresh cache object drift')
refs=[O/'static-costs/off/native_ui.d',Path('/mnt/c/Flycast-Evidence/re4-dreamcast/feedback21-runtime-20261021/qa-aafc10f3-input/input-receipt.json'),O/'off-native_ui.o',O/'off-texture_package.o',PL,D/'build.log',D/'candidate.txt',D/'resolved-knobs.txt',D/'owned-build.json',D/'receipt.json',D/'actual-dependency-closure.json',D/'object-file-identities.json',Q/'object-gates.json',Q/'final-audit.json',Q/'SHA256SUMS',FAIL/'census-work.json.gz',FAIL/'FAILED-CLOSEOUT.json',eventdir/'event-storage-event-sh4.json',eventdir/'event-storage-game-sh4.json']
helperrefs=[]
for f,commit in [('tool_closure.py','946a76c6069d036ca3a1ee6d5e2231348df8b708'),('trace_closure.py','d2109af80')]:
 p=C/'port/dreamcast/tools/d367/link_closure21'/f;blob=git('show',commit+':port/dreamcast/tools/d367/link_closure21/'+f,cwd=C);same=p.read_bytes()==blob
 if f=='tool_closure.py':req(same,'immutable helper drift');refs.append(p)
 helperrefs.append(dict(file=f,commit=commit,Git_blob_sha256=hashlib.sha256(blob).hexdigest(),live_matches=same,live_is_adopted=same,immutable_Git_source_only=True))
for x in ['texture-consumers21-link-tool-closure-plan-20261022','texture-consumers21-trace792-plan-20261022']:
 p=Path('/mnt/c/Flycast-Evidence/re4-dreamcast')/x/'SHA256SUMS.txt';req(p.is_file(),'consumer source seal missing');refs.append(p)
# Pin all retained final objects and old scripts/libs by compact dictionary rows.
put('object-matrix.json.gz',dict(prefix=str(O/'obj'),columns='i,r,sha,b,cl,dsha,dc,delta,current_contract,module?',rows=rows,module_rows=module_rows,changes=changed,affected={str(k):v for k,v in affected.items()},counts=dict(counts),module_affected_count=sum(bool(v) for v in module_hits.values()),module_cManager_count=sum(changedmap[str(R/'include/cManager.h')] in v for v in module_hits.values())))
put('link-plan.json.gz',dict(base_argv=base,base_environment=plan['environment'],old_actual_link_line=linkline[0][0],old_actual_link_argv_sha256=hashlib.sha256(json.dumps(original,separators=(',',':')).encode()).hexdigest(),cwd_context='Private copied linker-script context; never run mutating old link.sh in retained tree',replacements=replacements,overlays=plan['overlays'],frozen_helper_moves_ref='plan02 frozen_overlay_derived_objects;42unchanged+oldQAstatic h2; preserve placements',all_final_linked_object_pins=[pin(p) for p in linkobjects],libraries_ref='plan02 unchanged_library_pins',link_support_ref='plan02 link_support_pins',fresh_output=str(B),other_guards='Actual retained QA byte/recipe state, including Event0. Do not claim all current source or Make BOTH=1 globally compiled.',scope='Proposed mixed-provenance QA basis plus two new repairs; main must select coherent final arm before allocation'))
put('event-contract.json',dict(prior_receipt_pin=pin(eventdir/'event-storage-event-sh4.json'),current_header_pin=pin(T/'include/cManager.h'),QA_actual_event_compile_log_line=qaevent['cl'],different_definitions=different,old_Event_objects_reusable_in_QA=False,reason='Prior target gates use actor/VMU0 and EVD enabled; QA has actor/VMU1 and EVDoff. Same source semantics do not prove exact QA macro/header/object contract.',required_for_Event_enabled='Fresh actual-QA current-header Event/read and all instantiated Event-manager consumers, plus SS/main under Event1.252directcManager users+module-derived consumers require resolved preprocess/object projections or fresh objects. Existing8 cache objects have Event omitted/0 and cannot be relabelled Event1. Main must choose projection/rebuild closure; no minimum two-TU claim.'))
put('candidate-source-pins.json',candidatepins+[pin(T/'port/dreamcast/game/game30.mk'),pin(T/'port/dreamcast/tools/d367/cache21/INTEGRATION_PREPARATION_20261022.md')])
put('references.json',[pin(p) for p in refs]);put('tool-closure-reuse.json',dict(immutable_consumer_helpers=helperrefs,helper_role='source discovery/check only; not fresh programme pre/post',newunit_requirements='Use sealed consumer capture/check and strict execve/open parser around every actual binary-producing child. Fresh pre/post resolved tool+hostloader/plugin/env/input pins; selected GCC ld and toolbin ld pinned independently even ifsameSHA. Preserve held650 failure; no waiver or duplicate infrastructure.',concrete_controller='Consumer next792 controller still requires sealed release/main adaptation; no current dirty source used here.'))
expected=json.loads((D/'receipt.json').read_text());put('QA-control.json',dict(source=expected['source'],program=pin(D/'program.bin'),ELF=pin(D/'re4dc-game.elf'),files=expected['files'],required='OFF raw8942ad7e90d9adab56873d0738d76c274b98c28c35587e52fc93e2091f13300d ANDall14 exact; additionally allocated/loadableELF content/layout/addresses/flags/PT_LOADmemsz inclBSS exact. Fulldebug/path ELFhash recordedseparately, not requiredidentical.',on='Only after OFF passes. FreshenabledELF/program+all14 overlays regenerated/resealed and boundnewidentity, checkedpayload/relocFNV/targets/slots. No old14 copy into newprogramme.',mismatch='Preserve full mismatch/diffs and STOP. No canonical cManager swap, stale-object relabel, retrospective exception or enabled link.'))
put('plan.json',dict(state='SOURCE_METADATA_ONLY_NOT_ALLOCATED',source=HEAD,runtime=RUN,source_tree=str(T),metadata_namespace=str(M),future_output=str(B),cap_bytes=CAP,compiler_runs=0,preprocessor_runs=0,linker_runs=0,lease=False,guard_arms={'QA_OFF':{'EVENT_MANAGER_STORAGE_FLAGS':0,'SS_RESTORE_VALIDATE_FIRST':0,'RESET_RETIRE_BEFORE_HEAPS':0},'TWO_NEW_REPAIRS_ONLY':{'EVENT_MANAGER_STORAGE_FLAGS':0,'SS_RESTORE_VALIDATE_FIRST':1,'RESET_RETIRE_BEFORE_HEAPS':1},'EVENT_PLUS_TWO_HOLD':{'EVENT_MANAGER_STORAGE_FLAGS':1,'SS_RESTORE_VALIDATE_FIRST':1,'RESET_RETIRE_BEFORE_HEAPS':1}},root_candidate_adoption='No blanket current-source qualification;15changed inputs258direct affected/252cManager plus module evidence explicitly require projection/rebuild for all-root-source claim. TWO arm only inheritedQA+newSS/main with Event0, conditional main selection and hardOFFlinkgate.',smallest_future_controls='TWO arm: no automatic extra compiler if main accepts explicit mixedQA provenance;8existingqualifiedobjects provide2default/2enabled inputs. To adopt currentroot/Event source: freshactual-QA controls/projections for every affectedconsumer; sourcecensus supplies258+module closure. No compiler run here.',future_resource_proposal=dict(pair_hard_bytes=268435456,pair_soft_abort_bytes=234881024,components=dict(two_final_ELF_programme14_WSL_and_C=150994944,one_shifted_ELF=33554432,traces_logs_tools_context_and_reserve=50331648),estimate_bytes=234881024,optional_current_source_refresh='Separate root-sized object/projection allocation; not hidden inside linkpair estimate',one_shared_lease=True,sequential_OFF_before_ON=True,root_fresh_disk_peer_reservation_review_required=True,no_stage_image_guest=True),failed_precursor='FAILED preserved, not retrospectively within512KiB; own48,776B gzip referenced only. Successor has independent prewriteforecast and final allocated accounting.'))
print(json.dumps(dict(state='COMPACT SOURCE PLAN CREATED_NO_TOOLCHAIN',packet_logical=sum(p.stat().st_size for p in M.iterdir()),current_new_allocated=allocated(),direct_census=dict(counts),module_affected=sum(bool(v) for v in module_hits.values()),Event_prior_QA_definition_differences=different)))
