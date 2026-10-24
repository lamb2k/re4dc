"""Source/metadata/byte readback only: no subprocess, SDK invocation or mutation."""
from pathlib import Path
import hashlib,json,re,shutil
RUN=Path('/dev/shm/gc-motion24-target-run-0mftarg0')
OWN=Path(__file__).resolve().parent
PREP=OWN.parent/'target-prep'
E=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/gc-motion24-20261024/target-independent-readback-v1')
FAILED_SHA='ac55f77721f954d1fbfdf9d36fafcf231d5f3a6e4630e8da1c0e43d4c9891124'

def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()

def undefined(path):return {x.strip()[2:] for x in path.read_text().splitlines() if x.strip().startswith('U ')}
def global_defined(path):
 result=set()
 for line in path.read_text().splitlines():
  a=line.split(None,2)
  if len(a)==3 and a[1] in ['T','W','V','D','B','R','S','A']:result.add(a[2])
 return result

def stack(path):
 rows=[]
 for line in path.read_text().splitlines():
  a=line.rsplit('\t',2)
  if len(a)!=3:continue
  match=re.match(r'^(.*?):(\d+):(\d+):(.*)$',a[0]);assert match,line
  rows.append({'source':match[1],'line':int(match[2]),'column':int(match[3]),'function':match[4],'bytes':int(a[1]),'qualifier':a[2],'raw':line})
 return rows

def main():
 assert sha(RUN/'report.json')==FAILED_SHA
 report=json.loads((RUN/'report.json').read_text());plan=json.loads((PREP/'PREPARATION.json').read_text())
 assert not report['complete'] and len(report['objects'])==len(plan['arms'])==33
 assert report['preparation_sha256']==sha(PREP/'PREPARATION.json')
 assert report['runner_sha256']==sha(OWN.parent/'run-target-motion24.py')
 assert report['source']==plan['head'] and report['parent']==plan['parent'] and report['runtime']==plan['runtime']
 pins_verified={}
 def verify(path,row):
  path=Path(path);assert path.stat().st_size==row['bytes']
  if str(path) not in pins_verified:pins_verified[str(path)]=sha(path)
  assert pins_verified[str(path)]==row['sha256'],str(path)
 for name,row in plan['input_pins'].items():verify(name,row)
 export=Path(plan['export'])
 for name,row in plan['source_pins'].items():
  label,name=name.split(':',1);verify(export/label/name,row)
 objects={};binary_manifest={};metadata_manifest={};dep_refs=0;external_bundle=set();stack_comparisons={};selected_rows=[]
 for row in report['objects']:
  tag=row['tag'];assert tag not in objects;objects[tag]=row
  arm=next(a for a in plan['arms'] if a['tag']==tag)
  assert row['unit']==arm['unit'] and row['label']==arm['label'] and row['gate']==arm['gate'] and row['motion']==arm['motion']
  cmd=json.loads((RUN/(tag+'-command.json')).read_text());expected=list(arm['argv']);expected[expected.index('-o')+1]=str(RUN/(tag+'.o'));assert cmd==expected
  assert sha(RUN/(tag+'.o'))==row['object_sha256']
  assert sha(RUN/(tag+'-stripped.o'))==row['stripped_sha256']
  assert sha(RUN/(tag+'.su'))==row['stack_usage_sha256']
  deps_path=RUN/(tag+'-dependencies.json');assert sha(deps_path)==row['dependencies_sha256'];deps=json.loads(deps_path.read_text());assert len(deps)==row['dependency_count'];dep_refs+=len(deps)
  for name,pin in deps.items():
   verify(name,pin)
   if name.startswith('/root/probe/lanes/play-actor-bundle/'):external_bundle.add(name)
  values=[int(n) for n in (RUN/(tag+'-size.txt')).read_text().splitlines()[-1].split()[:3]];assert dict(zip(['text','data','bss'],values))==row['sections']
  if row['empty_required']:
   assert not any(values) and not (RUN/(tag+'-defined.txt')).read_text().strip() and not (RUN/(tag+'-undefined.txt')).read_text().strip()
  for suffix in ['.o','-stripped.o']:
   q=RUN/(tag+suffix);binary_manifest[q.name]={'bytes':q.stat().st_size,'sha256':sha(q),'copied':False}
 identities=[]
 for unit in ['native_ui','native_model','native_actor_fast','model_bridge']:
  for gate in [0,1]:
   tags=[f'parent-{unit}-gate{gate}-motionabsent',f'current-{unit}-gate{gate}-motionabsent',f'current-{unit}-gate{gate}-motionzero']
   hashes={sha(RUN/(tag+'-stripped.o')) for tag in tags};assert len(hashes)==1
   identities.append({'unit':unit,'gate':gate,'arms':tags,'stripped_sha256':hashes.pop(),'pass':True})
  parent=f'parent-{unit}-gate1-motionabsent';current=f'current-{unit}-gate1-motionon'
  delta={k:objects[current]['sections'][k]-objects[parent]['sections'][k] for k in ['text','data','bss']};selected_rows.append({'unit':unit,'parent':objects[parent]['sections'],'current':objects[current]['sections'],'delta':delta})
  a,b=stack(RUN/(parent+'.su')),stack(RUN/(current+'.su'))
  def byname(rows):
   d={}
   for r in rows:d.setdefault(r['function'],[]).append(r)
   return d
  x,y=byname(a),byname(b);changes=[]
  for name in x.keys()&y.keys():
   old=max(v['bytes'] for v in x[name]);new=max(v['bytes'] for v in y[name])
   if old!=new:changes.append({'function':name,'parent_max_self':old,'current_max_self':new,'arithmetic_delta':new-old,'parent_rows':x[name],'current_rows':y[name]})
  stack_comparisons[unit]={'changed_common_signatures':sorted(changes,key=lambda r:r['function']),'removed_signatures':sorted(x.keys()-y.keys()),'added_signatures':sorted(y.keys()-x.keys()),'parent':a,'current':b}
 helper='current-gc_asset_motion_unknown-gate1-motionon';selected_rows.append({'unit':'gc_asset_motion_unknown','parent':dict(text=0,data=0,bss=0),'current':objects[helper]['sections'],'delta':objects[helper]['sections']})
 delta={k:sum(r['delta'][k] for r in selected_rows) for k in ['text','data','bss']};assert delta==report['selected_ON_delta']==dict(text=1286,data=0,bss=24)
 assert objects[helper]['sections']['bss']==24 and sum(r['empty_required'] for r in report['objects'])==4
 base_u=set();current_u=set();own_defs=set()
 for unit in ['native_ui','native_model','native_actor_fast','model_bridge']:
  base_u|=undefined(RUN/(f'parent-{unit}-gate1-motionabsent-undefined.txt'))
 for unit in ['native_ui','native_model','native_actor_fast','model_bridge','gc_asset_motion_unknown']:
  tag=f'current-{unit}-gate1-motionon';current_u|=undefined(RUN/(tag+'-undefined.txt'));own_defs|=global_defined(RUN/(tag+'-defined.txt'))
 new_u=current_u-base_u;new_external=new_u-own_defs
 missing=report['provider_closure']['missing'];normalized={name[1:] for name in missing}
 assert len(missing)==6 and normalized<=base_u and normalized<=current_u
 full=Path('/root/work/lanes/gc-port23-full-target2-scratch/on/build.log');lines=full.read_text().splitlines();link=lines[1031];assert '--wrap=' in link
 wrap_flags=set(re.findall(r'--wrap[=,]([A-Za-z0-9_]+)',link));proof=[]
 for raw in missing:
  demangled=raw[1:];assert demangled.startswith('__real_');target=demangled[len('__real_'):];assert target in wrap_flags
  proof.append({'raw_SH4_symbol':raw,'demangled_log_symbol':demangled,'present_parent_Gate1':demangled in base_u,'present_current_ON':demangled in current_u,'actual_old_link_wrap_option':'--wrap='+target,'historical_link_line':1032,'status':'preexisting wrapper import; GNU link-rewrite/provider validation retained for root, not declared closed here'})
 assert not new_external,new_external
 assert sha(RUN/'report.json')==FAILED_SHA
 # Copy only diagnostics/manifests. Binaries, programmes, assets and source exports stay put.
 for q in RUN.iterdir():
  if not q.is_file() or q.suffix in ['.o','.elf','.bin','.a']:continue
  if q.name=='report.json':continue
  metadata_manifest[q.name]={'bytes':q.stat().st_size,'sha256':sha(q)};shutil.copyfile(q,E/q.name)
 for name in ['PREPARATION.json','EXPORT-MANIFEST.json','READBACK.json']:
  shutil.copyfile(PREP/name,E/('source-export-'+name))
 (E/'OBJECTS-NOT-COPIED.json').write_text(json.dumps(binary_manifest,indent=2)+'\n')
 (E/'METADATA-COPIED.json').write_text(json.dumps(metadata_manifest,indent=2)+'\n')
 (E/'historical-link-line1032.txt').write_text(link+'\n')
 result={'status':'COMPILE_IDENTITY_AND_SIZE_READBACK_PASS_PROVIDER_WRAP_PENDING','original_failed_report_sha256':FAILED_SHA,'source':report['source'],'runtime':report['runtime'],'parent':report['parent'],'objects_verified':33,'identity_groups_verified':identities,'helper_OFF_empty':4,'raw_helper_state_bytes':24,'selected_ON':selected_rows,'selected_delta':delta,'selected_total_delta_bytes':sum(delta.values()),'dependency_references_verified':dep_refs,'unique_dependency_and_input_files_verified':len(pins_verified),'external_bundle_dependencies_used':sorted(external_bundle),'new_demangled_imports':sorted(new_u),'new_imports_resolved_in_selected_objects':sorted(new_u&own_defs),'new_external_imports_not_in_baseline_or_selected_definitions':sorted(new_external),'preexisting_wrapper_analysis':proof,'stack':stack_comparisons,'helper_self_frames':stack(RUN/(helper+'.su')),'SDK_commands_by_readback':0,'limits':['No recompile or SDK query','No entire provider-closure PASS: six raw preexisting wrappers remain root link-rewrite validation','Compiler .su self frames only; source-origin maximum is not a full callchain/heap/highwater','Existing actor wrapper8 and same-origin clone1716 replaced by named1740: raw named delta1732 is not established dynamic stack growth','OneWindow new local unsigned flag and RAIIword are4 each by target-compiled static_assert/source; chunk frame1136->1148, dispatch1392->1400, owned1456->1468 are compiler self-frame changes','No fresh full programme/map/runtime/guest/coverage/provenance/I001 acceptance'],'metadata_files_copied':len(metadata_manifest),'binary_manifest_count':len(binary_manifest)}
 (E/'READBACK.json').write_text(json.dumps(result,indent=2)+'\n');(OWN/'READBACK.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({k:result[k] for k in ['status','objects_verified','helper_OFF_empty','raw_helper_state_bytes','selected_delta','dependency_references_verified','unique_dependency_and_input_files_verified','new_demangled_imports','new_external_imports_not_in_baseline_or_selected_definitions','metadata_files_copied','binary_manifest_count']},indent=2))

if __name__=='__main__':main()
