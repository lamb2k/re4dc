from pathlib import Path
import hashlib,json,re,sys,resource,datetime,shutil
OWN=Path('/mnt/c/Game Dev/Emulators/codex-lanes/gc-motion24');PREP=OWN/'target-prep'
sys.path.insert(0,str(PREP));from readback_prep import validate
resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,256*1024**2));resource.setrlimit(resource.RLIMIT_CORE,(0,0))
RUN=Path('/dev/shm/gc-motion24-target-run-0mftarg0');plan=json.loads((PREP/'PREPARATION.json').read_text());validate(plan)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
r=json.loads((RUN/'report.json').read_text());assert not r['complete'] and len(r['objects'])==33
wrap=json.loads((OWN/'ROOT-WRAP-PROVIDER-RESULT.json').read_text());assert wrap['failed_run_report_sha256']==sha(RUN/'report.json')
assert wrap['status']=='EXACT_EXISTING_LINK_WRAP_AND_REAL_PROVIDER_REWRITE_VERIFIED'
assert set(r['provider_closure']['missing'])=={x['reference'] for x in wrap['rewrites']}
for x in r['objects']:
 assert sha(RUN/(x['tag']+'.o'))==x['object_sha256'] and sha(RUN/(x['tag']+'-stripped.o'))==x['stripped_sha256']
 dep=json.loads((RUN/(x['tag']+'-dependencies.json')).read_text())
 for p,pin in dep.items():assert Path(p).stat().st_size==pin['bytes'] and sha(p)==pin['sha256'],p
 if x['stack_usage_sha256']:assert sha(RUN/(x['tag']+'.su'))==x['stack_usage_sha256']
def frames(tag):
 d={}
 for line in (RUN/(tag+'.su')).read_text().splitlines():
  cols=line.split('\t');assert len(cols)==3,line
  m=re.match(r'^.*?:\d+:\d+:(.*)$',cols[0]);assert m,cols[0]
  d[m.group(1)]={'frame':int(cols[1]),'kind':cols[2]}
 return d
stack=[]
for unit in ['native_ui','native_model','native_actor_fast','model_bridge']:
 a=frames('parent-'+unit+'-gate1-motionabsent');b=frames('current-'+unit+'-gate1-motionon')
 for fn in sorted(set(a)|set(b)):
  if a.get(fn)!=b.get(fn):stack.append({'unit':unit,'function':fn,'parent':a.get(fn),'on':b.get(fn)})
helper_frames=frames('current-gc_asset_motion_unknown-gate1-motionon')
E=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/gc-motion24-20261024/target-fce-current');assert not E.exists();E.mkdir()
# Preserve compact target receipts and compiler diagnostics. Actual objects and
# source exports stay at their owned RAM paths; no programme/asset is copied.
for f in sorted(RUN.iterdir()):
 if f.is_file() and f.suffix not in ['.o']:shutil.copyfile(f,E/f.name)
for f in ['ROOT-TARGET-GRANT.json','ROOT-WRAP-PROVIDER-RESULT.json','ROOT-WRAP-PROVIDER-FAILURE-1.json','ROOT-WRAP-PROVIDER-FAILURE-2.json']:
 shutil.copyfile(OWN/f,E/f)
for f in ['PREPARATION.json','EXPORT-MANIFEST.json','READBACK.json']:shutil.copyfile(PREP/f,E/('prep-'+f))
result={'status':'SELECTED_SH4_33_ARMS_AND_DISABLED_IDENTITY_PASS','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source':r['source'],'runtime':r['runtime'],'parent':r['parent'],'compiled_arms':33,'disabled_identity_groups':r['disabled_identity'],'empty_helper_arms':4,'selected_ON_delta':r['selected_ON_delta'],'raw_motion_state_bytes':24,'per_function_self_frame_changes':stack,'helper_self_frames':helper_frames,'provider_closure':{'baseline_wraps_verified':wrap['rewrites'],'remaining_unresolved':[],'needed_count':r['provider_closure']['needed'],'real_provider_scope':r['provider_closure']['limit']},'input_pins_final_verified':len(plan['input_pins']),'source_export_pins_final_verified':len(plan['source_pins']),'full_dependency_sets_final_verified':33,'original_incomplete_report_sha256':sha(RUN/'report.json'),'wrap_result_sha256':sha(OWN/'ROOT-WRAP-PROVIDER-RESULT.json'),'AS_and_owned_output_cap':268435456,'observed_RSS_peak':'not separately sampled','owned_output_bytes':r['owned_output_bytes'],'slot_released':True,'SDK_compile_rerun_after_checker_failure':False,'limits':['Selected object delta, not full linked section/end or measured heap','Per-function self frames, not complete nested stack/highwater','Real provider candidates plus exact existing linker wrap controls, not a new full link/map','No configured catalog, Motion provenance, complete coverage, terminal, runtime/guest or physical acceptance','Original six-wrapper checker failure and two synthetic-control harness failures preserved']}
(E/'SUMMARY.json').write_text(json.dumps(result,indent=2)+'\n')
manifest={f.name:{'bytes':f.stat().st_size,'sha256':sha(f)} for f in E.iterdir() if f.is_file()};(E/'SHA256-MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
(OWN/'ROOT-TARGET-FINAL-RECEIPT.json').write_text(json.dumps({'status':result['status'],'evidence':str(E),'summary_sha256':sha(E/'SUMMARY.json'),'manifest_sha256':sha(E/'SHA256-MANIFEST.json'),'metadata_files':len(manifest),'metadata_bytes':sum(x['bytes'] for x in manifest.values())},indent=2)+'\n')
print(json.dumps({'status':result['status'],'selected_ON_delta':result['selected_ON_delta'],'stack_changes':len(stack),'metadata_files':len(manifest),'manifest_sha256':sha(E/'SHA256-MANIFEST.json')}))