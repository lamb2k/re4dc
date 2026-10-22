"""Independent read/hash review only. No compiler, preprocessor, linker or imports of plan code."""
from pathlib import Path
import collections, gzip, hashlib, json, shlex, shutil, subprocess
P=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/issue52-cache-currentqa-plan-20261022')
ROOT=Path('/root/probe/codex-cache21-integration-next')
C57='c57ff60f0f462fdd2c419883b0258963504d756a'
FLOOR=19394461696
assert shutil.disk_usage('/mnt/c').free>=FLOOR
sha=lambda b:hashlib.sha256(b).hexdigest()
checks=[]; verified={}; blobs={}
def check(name,condition):
 assert condition,name
 checks.append(name)
def load(n):
 b=(P/n).read_bytes()
 return json.loads(gzip.decompress(b) if n.endswith('.gz') else b)
def pin(r):
 path=Path(r.get('p',r.get('path','')))
 size=r.get('b',r.get('bytes')); h=r.get('sha',r.get('sha256'))
 if str(path) not in verified:
  b=path.read_bytes();verified[str(path)]=(len(b),sha(b))
 assert verified[str(path)]==(size,h),str(path)
 return verified[str(path)]
def blob(relative):
 if relative not in blobs:
  b=subprocess.check_output(['git','-C',str(ROOT),'show',C57+':'+relative]);blobs[relative]=(len(b),sha(b))
 return blobs[relative]
seals={}
for seal,expected in [('SHA256SUMS','8816b98a26d29218386abadf6001d1fbeb6e1501f1699fc18bcae75930289ed6'),('EVIDENCE-SHA256SUMS','cc7ded5b8b238b8bbc1669af89ae80e8d4615fa8c8ba1c81f56a3438fda483e7')]:
 b=(P/seal).read_bytes();assert sha(b)==expected
 for line in b.decode().splitlines():
  h,n=line.split('  ',1);assert '/' not in n and sha((P/n).read_bytes())==h,n
 seals[seal]={'sha256':expected,'members':len(b.decode().splitlines())}
check('both source/full packet seals and every listed member agree',True)
PREP='89ea415b5e698c4ab4aec28c7d2568fbb7f81ba5'
prep_tree='/root/probe/codex-issue52-objects';prep_rel='port/dreamcast/tools/d367/issue52_cache_currentqa_plan/'
for line in (P/'SHA256SUMS').read_text().splitlines():
 h,n=line.split('  ',1)
 b=subprocess.check_output(['git','-C',prep_tree,'show',PREP+':'+prep_rel+n])
 assert sha(b)==h and b==(P/n).read_bytes(),n
check('all fourteen sealed source members exactly match requested preparation commit89ea',True)
plan=load('plan.json');qa=load('qa52190.json');mod=load('module-reconstruction.json.gz');link=load('link-input-template.json.gz');cc=load('cache-object-contract.json');sp=load('source-blob-pins.json')
check('source-only unallocated packet; all seven execution counters zero',plan['state']=='SOURCE_ONLY_CURRENT_QA_PLAN_NOT_ALLOCATED' and not any(plan['runs'].values()))
check('runtime/docs pins match the requested packet',plan['source_runtime']=='babfaa7d8ee868c9b81305aef7024ffd543eb6f6' and plan['source_docs_observed']=='62a76a77309d70cecfbe7fa8dca9225902231c0a')
check('two compiler tasks are proposals, not existing results',plan['fresh_compiler_proposal']['count']==2)
for key in ['programme','elf','recipe','resolved','build_log','owned_build','receipt']:pin(qa[key])
for r in qa['overlays']:pin(r)
check('selected C57 programme52190/ELF248 and fourteen distinct overlay identities',qa['source']==C57 and qa['programme']['sha']=='52190ed293d8e62238bcad40fd351d35a965b253ad5b59cda570d0de34187e45' and qa['elf']['sha']=='248dd4aac7c4e22a7a18a0183fc6409401fddf610d98881c90dd9664e342640b' and len({r['p'] for r in qa['overlays']})==14)
producer=Path('/mnt/c/Game Dev/Emulators/codex-lanes/cache21/build-ganado-reader-on.py')
text=producer.read_text();base=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/feedback21-runtime-20261021/pause-build-off/original-candidate.txt')
receipt=json.loads(Path(qa['receipt']['p']).read_text());owned=json.loads(Path(qa['owned_build']['p']).read_text())
guards=receipt['selected_guards'];knobs=base.read_text().split()+guards+['CABIN_SOURCE=0']
check('receipt recipe SHA is the base recipe, expanded candidate/owned command exact',sha(base.read_bytes())==receipt['recipe_sha256'] and Path(qa['recipe']['p']).read_text()==' '.join(knobs)+'\n' and owned['command'][4:]==knobs and owned['source']==C57 and "'recipe_sha256':sha(recipe)" in text)
resolved=dict(l.split('=',1) for l in Path(qa['resolved']['p']).read_text().splitlines() if '=' in l and not l.startswith(('#',' ')))
check('actual resolved actor/native-look/VMU1 and CABIN0 preserved',all(resolved[k]==str(v) for k,v in {'ACTOR_TRANSACTION':1,'ACTOR_LEON_NATIVE_LOOK':1,'VMU_DIALOG':1,'CABIN_SOURCE':0,'GANADO_ROUTINE_BYTES':1}.items()))
check('all fifteen retained cache switches are zero including every EVD switch',len(guards)==16 and guards[-1]=='GANADO_ROUTINE_BYTES=1' and all(x.endswith('=0') and resolved[x.split('=')[0]]=='0' for x in guards[:-1]))
for k in ['GAME_CPPFLAGS','PLATFORM_CPPFLAGS']:
 flags=shlex.split(resolved[k]);assert all('-DRE4DC_'+x+'=1' in flags for x in ['ACTOR_TRANSACTION','ACTOR_LEON_NATIVE_LOOK','VMU_DIALOG'])
 assert not any(x.startswith(('-DRE4DC_EVD_','-DRE4DC_EVENT_MANAGER_STORAGE_FLAGS','-DRE4DC_CABIN_SOURCE')) for x in flags)
check('global GAME/PLATFORM actor/VMU macro contract; EVD/Event/CABIN absent',True)
for r in sp['runtime'].values():pin(r)
check('actual C57 em10/header blobs and current runtime source pins',blob('src/em10/em10.cpp')==(sp['C57_em10']['bytes'],sp['C57_em10']['sha']) and blob('include/cManager.h')==(sp['C57_cManager']['bytes'],sp['C57_cManager']['sha']))
check('historical/current cManager explicitly different; no substituted current header',sp['C57_cManager']['sha']!=sp['runtime']['include/cManager.h']['sha'])
oldprefix=mod['oldprefix'];qprefix=mod['prefix'];offprefix=qprefix.replace('/on-01/obj','/off-01/obj')
def normalize(argv):
 return [a.replace(qprefix,'OBJ').replace(offprefix,'OBJ').replace(oldprefix,'OBJ').replace(str(ROOT),'TREE').replace('/root/probe/codex-texture-rect21','TREE') for a in argv]
refs=load('references.json')
for r in refs:pin(r)
depref=next(r for r in refs if 'actual-dependency-closure' in r['p'])
olddeps={r['path']:r for r in json.loads(Path(depref['p']).read_text())}
invref=next(r for r in refs if r['p'].endswith('object-file-identities.json'))
oldinventory={r['path']:r for r in json.loads(Path(invref['p']).read_text())}
oldlog=Path(next(r for r in refs if r['p'].endswith('out-off/build.log'))['p']).read_text().splitlines()
onlog=Path(qa['build_log']['p']).read_text().splitlines()
offlog=Path(next(r for r in refs if r['p'].endswith('off-01/build.log'))['p']).read_text().splitlines()
check('fourteen module input rows and target-only rebuild',len(mod['constituents'])==len(mod['commands'])==14 and [r['i'] for r in mod['constituents'] if r['rebuild']]==[0])
depcount=0
for r,c in zip(mod['constituents'],mod['commands']):
 assert r['i']==c['i']
 oldpath=str(Path(oldprefix)/r['r'])
 pin({'p':oldpath,**r['old']})
 original=oldinventory[oldpath]
 assert (original['bytes'],original['sha256'])==(r['old']['b'],r['old']['sha'])
 assert shlex.split(onlog[r['on_line']-1])==c['argv'] and shlex.split(oldlog[r['old_line']-1])==c['old_argv']
 if r['i']==0:
  assert normalize([s for s in c['argv'] if s!='-DRE4DC_GANADO_ROUTINE_BYTES=1'])==normalize(c['old_argv'])
  assert r['source_delta']==['src/em10/em10.cpp']
 else:assert normalize(c['argv'])==normalize(c['old_argv']) and not r['source_delta']
 if r['d']:pin(r['d'])
 for rel,h,b,eq in r['deps']:
  depcount+=1
  if not rel.startswith('/'):
   assert blob(rel)==(b,h),rel
   prior=olddeps['/root/probe/codex-texture-rect21/'+rel]
   assert (prior['sha256']==h)==eq
  else:
   pin({'p':rel,'b':b,'sha':h})
   if '/obj/' in rel:
    assert Path(rel).read_bytes()==Path(rel.replace(qprefix,oldprefix)).read_bytes()
  assert eq or r['i']==0 and rel=='src/em10/em10.cpp'
check('all fourteen exact logged argv; thirteen normalized matches; target flag is sole argv delta',True)
check('all fourteen retained module object hashes agree with original QA inventory',True)
check('every recorded local dependency independently bound to C57 or exact generated inputs',True)
check('original GANADO0 command exists and is the GANADO1 command minus only flag/path',any(shlex.split(s)==mod['GANADO0_original_command'] for s in offlog if ' -c ' in s) and normalize(mod['GANADO0_original_command'])==normalize([s for s in mod['commands'][0]['argv'] if s!='-DRE4DC_GANADO_ROUTINE_BYTES=1']))
for stage in ['partial_link','objcopy']:assert shlex.split(onlog[mod[stage]['line']-1])==mod[stage]['argv']
check('exact state script and ordered partial-link/objcopy recipes', [s for s in mod['partial_link']['argv'] if s.endswith('.o')]==[qprefix+'/'+r['r'] for r in mod['constituents']])
pin(mod['state_ld'])
check('state script identical to original QA script',Path(mod['state_ld']['p']).read_bytes()==Path(mod['state_ld']['p'].replace(qprefix,oldprefix)).read_bytes())
counts=collections.Counter(r.get('provenance','future') for r in link['objects'])
for r in link['objects']:
 if 'future' not in r:pin(r);assert link['argv'][r['argv_i']]==r['p']
 else:assert link['argv'][r['argv_i']]==r['future']
check('447 ordered link objects split403 inherited/43 helpers/one pending module',counts=={'inherited_original_QA_explicit_historical_basis':403,'C57_ON_helper':43,'future':1})
for r in link['C57_helpers']:pin(r)
pin(link['C57_moves'])
moves=Path(link['C57_moves']['p']).read_text().splitlines();sources=list(dict.fromkeys(l.split('\t')[1] for l in moves))
check('188 C57-path moves yield43 helpers and exclude em10g',len(moves)==188 and len(sources)==43 and all(s.startswith(qprefix+'/') and not s.endswith('/em10g.o') for s in sources) and {f'o{i}_{Path(s).name}' for i,s in enumerate(sources)}=={Path(r['p']).name for r in link['C57_helpers']})
check('helper input hash set exactly equals independently hashed retained helper set',{(r['p'],r['b'],r['sha']) for r in link['objects'] if r.get('provenance')=='C57_ON_helper'}=={(r['p'],r['b'],r['sha']) for r in link['C57_helpers']})
for r in link['C57_context'].values():pin(r)
for row in cc['rows']:
 pin(row['eight_argv_pin']);prev=json.loads(Path(row['eight_argv_pin']['p']).read_text())['argv'];qaargv=row['qa_argv'];source=qaargv[qaargv.index('-c')+1]
 k=prev.index('-fstack-usage');proj=prev[:k]+['-MMD','-MP','-c',source,'-o','OUT'];proj[0]=qaargv[0]
 target=qaargv[:];target[-1]='OUT'
 assert normalize(proj)==normalize(target) and shlex.split(onlog[row['qa_compile_line']-1])==qaargv
 assert not any(s.startswith(('-DRE4DC_EVD_','-DRE4DC_EVENT_MANAGER_STORAGE_FLAGS')) for s in prev)
 for r in row['objects'].values():pin(r)
 pin(row['current_header'])
for r in cc['generated']:
 pin(r['old']);pin(r['qa']);assert Path(r['old']['p']).read_bytes()==Path(r['qa']['p']).read_bytes()
check('eight-unit SS/main actual-QA flags/generated headers and immutable object inputs; current Event0',True)
for arm in ['off','two-repairs']:
 for i,r in link['replacements'][arm].items():pin(r);assert ('main.o' if int(i)==207 else 'sscrn_bridge.o') in link['argv'][int(i)]
check('two arms replace only SS/main at exact selected-QA argv indices',set(link['replacements'])=={'off','two-repairs'} and all(set(x)=={'207','448'} for x in link['replacements'].values()))
check('Event1 HOLD and full raw/all14/allocated-loadable ELF including BSS must precede ON',plan['matrix']['current_QA_OFF']=={'EVENT_MANAGER_STORAGE_FLAGS':0,'GANADO_ROUTINE_BYTES':1,'RESET_RETIRE_BEFORE_HEAPS':0,'SS_RESTORE_VALIDATE_FIRST':0} and 'HOLD' in plan['matrix']['full_Event1'] and all(x in ' '.join(plan['future_execution']) for x in ['raw52190','all14','allocated/loadable','BSS','Only after OFF succeeds']))
check('retained ELF projection covers11allocated sections and3 load segments including nonzero BSS',len(qa['projection']['allocated'])==11 and len(qa['projection']['PT_LOAD'])==3 and any(r['t']==8 and r['b']>0 for r in qa['projection']['allocated']))
check('future fresh paths/environment and tool closure are explicitly unsealed',all(k in ' '.join(link['fresh_owned_path_rewrites_required']) for k in ['TMPDIR','EM10G','SS/main']) and 'before execution' in link['notes'])
print(json.dumps({'state':'INDEPENDENT_SOURCE_PROVENANCE_PASS_EXECUTION_PENDING','checks':checks,'counts':{'checks':len(checks),'unique_external_inputs_hashed':len(verified),'C57_blobs_hashed':len(blobs),'local_module_dependency_occurrences':depcount,'link_objects':len(link['objects']),'helper_moves':len(moves),'helper_objects':len(sources)},'seals':seals,'source_preparation':PREP,'source_runtime':plan['source_runtime'],'source_docs':plan['source_docs_observed'],'selected_programme':qa['programme']['sha'],'selected_ELF':qa['elf']['sha'],'selected_ELF_projection':qa['projection']['projection_sha'],'base_recipe_sha256':receipt['recipe_sha256'],'expanded_candidate_sha256':qa['recipe']['sha'],'recipe_producer_sha256':sha(producer.read_bytes()),'runtime_edits':0,'compiler_preprocessor_linker_lease_guest_runs':0,'limitations':['Historical C57 module reconstruction, not whole-current-source qualification.','43 helpers are currently retained exact bytes tied to C57-path moves; original unpruned helper hashes cannot be recovered by this review. Full OFF gate remains mandatory.','MMD local dependencies are not full system-header/tool/env closure; root must seal that fresh.','No fresh GANADO control objects or programme identity results exist in this packet.','Eight earlier source/host/SH4 claims referenced, not rerun.','Source-only metadata review is not Flycast/release/physical Dreamcast acceptance.']},indent=2))
