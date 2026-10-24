"""Source-only corrected baseline preflight. No SDK/Make invocation."""
from pathlib import Path
import copy,hashlib,importlib.util,json,shlex,shutil,subprocess,tempfile,os
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'qa-pair-v1'
spec=importlib.util.spec_from_file_location('q',OLD/'prepare_qa_pair.py');q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q)
b=q.base
GC={'GC_ASSET_GATE','GC_ASSET_CATALOG_SHA256','GC_ASSET_MOTION_UNKNOWN'}

def feature_absent(signature):
 assert signature['gc_runtime_paths']==[] and signature['gc_runtime_token_paths']==[]
 assert not (GC&set(signature['make_known_names']))
 return True

def feature_signature(source):
 game=source/'port/dreamcast/game';paths=[];tokens=[]
 for f in game.rglob('*'):
  if not f.is_file():continue
  if 'gc_asset' in f.name:paths.append(str(f.relative_to(source)))
  if f.suffix in ('.cpp','.c','.h','.inc','.mk','') and any(x in f.read_bytes() for x in [b'RE4DC_GC_ASSET_GATE',b'RE4DC_GC_ASSET_MOTION_UNKNOWN',b'GC_ASSET_CATALOG_SHA256']):tokens.append(str(f.relative_to(source)))
 # Reuse actual known-name grep, not a permissive independent spelling check.
 script=(source/'port/dreamcast/tools/d367/build-r21.sh').read_text();start=script.index('KNOWN=$(cat ');end=script.index('DEAD=',start)
 known=subprocess.check_output(['bash','-c',script[start:end]+'\nprintf "%s\n" "$KNOWN"'],cwd=source,text=True).splitlines()
 return dict(gc_runtime_paths=paths,gc_runtime_token_paths=tokens,make_known_names=known)

def actual_preflight(source,argv):
 text=(source/'port/dreamcast/tools/d367/build-r21.sh').read_text();start=text.index('R21=(');end=text.index('\n)',start)+2
 checks=text[text.index('KNOWN=$(cat '):text.index('make -C port/dreamcast/game -j')]
 snippet='set -euo pipefail\n'+text[start:end]+'\n'+checks
 assert 'make -C' not in snippet and 're4dc-knobs' not in snippet
 env=os.environ.copy();env.update(ASSETS=str(b.ASSETS),ROOT=str(source),OBJDIR=str(source.parent/'out/obj'),OUT=str(source.parent/'out'))
 r=subprocess.run(['bash','-c',snippet,'source-preflight',*argv[2:]],cwd=source,env=env,text=True,capture_output=True)
 return dict(returncode=r.returncode,stdout=r.stdout,stderr=r.stderr,script_sha256=b.sha(source/'port/dreamcast/tools/d367/build-r21.sh'),snippet_sha256=hashlib.sha256(snippet.encode()).hexdigest(),scope='Actual R21 array and exact KNOWN/DEAD block; stops before make/SDK')

def semantic(plan):
 assert plan['arm_order']==['baseline','off','on']
 assert plan['budget']['additional_preserved_preparation_roots']==[plan['preserved_failed_root']]
 assert plan['budget']['expected_approx_owned_peak_bytes']<plan['budget']['owned_bytes_cap']==2*1024**3
 feature_absent(plan['baseline_feature_absence'])
 for arm in plan['arm_order']:
  flags=dict(x.split('=',1) for x in plan['commands'][arm][2:]);assert flags==plan['resolved_expected'][arm]
  for key,value in [x.split('=',1) for x in plan['diagnostic_overrides']]:assert flags[key]==value
  if arm=='baseline':assert not GC&flags.keys()
  else:
   assert flags['GC_ASSET_GATE']==flags['GC_ASSET_MOTION_UNKNOWN']==str(int(arm=='on'))
   assert flags['GC_ASSET_CATALOG_SHA256']=='0'
 return True

def main():
 old=json.loads((OLD/'PREPARATION-THREE.json').read_text());prior=Path(old['root']);failed=prior/'qa-receipt.json'
 failure=json.loads(failed.read_text());assert not failure['complete'] and failure['failure']=="RuntimeError('Fresh build failed baseline rc=1')"
 assert failure['runner_sha256']==b.sha(OLD/'run_qa_three_arm.py')
 assert (prior/'baseline/build.log').read_text().strip()=='build-r21.sh: knobs no makefile reads (dead or misspelled): GC_ASSET_GATE GC_ASSET_CATALOG_SHA256 GC_ASSET_MOTION_UNKNOWN'
 assert not list((prior/'baseline/out').rglob('*.o')) and not (prior/'baseline/source/port/dreamcast/game/obj').exists()
 for arm in old['arm_order']:
  q.verify({str(prior/arm/'source'/n):r for n,r in old['source_manifests'][arm].items()})
 q.verify(old['input_pins']);q.verify(old['original_normal_pair_manifest'])
 assert b.git(b.TREE,'rev-parse','HEAD').strip()==b.SOURCE and not b.git(b.TREE,'status','--porcelain').strip()
 priorpins={str(f):dict(bytes=f.stat().st_size,sha256=b.sha(f)) for f in sorted(prior.rglob('*')) if f.is_file() and not f.is_symlink()}
 root=Path('/dev/shm/gc-motion24-qa-memory-v2-dbqczoc8')
 assert root.is_dir()
 plan=copy.deepcopy(old);plan['root']=str(root)
 for arm in old['arm_order']:
  q.verify({str(root/arm/'source'/n):r for n,r in old['source_manifests'][arm].items()})
  assert not (root/arm/'out').exists() and not (root/arm/'build.log').exists() and not (root/arm/'source/port/dreamcast/game/obj').exists()
  plan['commands'][arm]=[x.replace(str(prior),str(root)) for x in old['commands'][arm]]
  plan['environment'][arm]={k:v.replace(str(prior),str(root)) for k,v in old['environment'][arm].items()}
 baseline=plan['commands']['baseline'];removed=[x for x in baseline[2:] if x.split('=',1)[0] in GC]
 assert removed==['GC_ASSET_GATE=0','GC_ASSET_CATALOG_SHA256=0','GC_ASSET_MOTION_UNKNOWN=0']
 plan['commands']['baseline']=[x for x in baseline if x.split('=',1)[0] not in GC]
 for k in GC:plan['resolved_expected']['baseline'].pop(k)
 plan['removed_baseline_options']=removed
 plan['preserved_failed_root']=str(prior);plan['preserved_failed_root_manifest']=priorpins
 plan['preserved_initial_failure']=dict(receipt=str(failed),sha256=b.sha(failed),runner_sha256=b.sha(OLD/'run_qa_three_arm.py'),preparation_sha256=b.sha(OLD/'PREPARATION-THREE.json'))
 plan['baseline_feature_absence']=feature_signature(root/'baseline/source');feature_absent(plan['baseline_feature_absence'])
 plan['actual_deadknob_preflight']={arm:actual_preflight(root/arm/'source',plan['commands'][arm]) for arm in plan['arm_order']}
 assert all(row['returncode']==0 for row in plan['actual_deadknob_preflight'].values())
 wrong=actual_preflight(root/'baseline/source',plan['commands']['baseline']+removed);assert wrong['returncode']==1 and all(k in wrong['stderr'] for k in GC)
 plan['preserved_old_baseline_preflight_reproduction']=wrong
 plan['input_pins']=dict(old['input_pins'])
 for f in [Path(__file__),OLD/'PREPARATION-THREE.json',OLD/'run_qa_three_arm.py',OLD/'RUNNER-PINS.json',OLD/'SHA256-MANIFEST.json',failed]:plan['input_pins'][str(f)]=dict(bytes=f.stat().st_size,sha256=b.sha(f))
 plan['budget']['additional_preserved_preparation_roots']=[str(prior)]
 plan['budget']['expected_approx_owned_peak_bytes']=1800*1024**2
 plan['budget']['estimate']='Three new source copies~299MB plus prior failed root313MB, fresh3outputs~450MB/scratch~150MB/transients/metadata; conservative1.8GiB below2GiB TOTAL, runtime guard sums active+prior roots.'
 plan['budget']['owned_now_with_preserved']=b.used(root)+b.used(prior)
 plan['OFF_identity']['baseline_source_feature_absence_proved']=True
 assert semantic(plan)
 negatives=[]
 def rejected(label,change):
  x=copy.deepcopy(plan);change(x)
  try:semantic(x)
  except (AssertionError,KeyError):negatives.append(label)
  else:raise AssertionError(label+' escaped')
 rejected('baseline-GC-dead-option',lambda x:x['commands']['baseline'].append('GC_ASSET_GATE=0'))
 rejected('baseline-source-feature-present',lambda x:x['baseline_feature_absence']['gc_runtime_paths'].append('port/dreamcast/game/platform/gc_asset_gate.cpp'))
 rejected('missing-common-QA-flag',lambda x:x['commands']['baseline'].__setitem__(next(i for i,a in enumerate(x['commands']['baseline']) if a=='KOS_WATCH=1'),'KOS_WATCH=0'))
 rejected('OFF-Motion-enabled',lambda x:x['resolved_expected']['off'].update(GC_ASSET_MOTION_UNKNOWN='1'))
 rejected('ON-Motion-disabled',lambda x:x['resolved_expected']['on'].update(GC_ASSET_MOTION_UNKNOWN='0'))
 rejected('configured-catalog',lambda x:x['resolved_expected']['on'].update(GC_ASSET_CATALOG_SHA256='1'*64))
 rejected('preserved-root-unbudgeted',lambda x:x['budget'].update(additional_preserved_preparation_roots=[]))
 plan['negative_controls']=negatives
 assert b.used(root)+b.used(prior)<plan['budget']['owned_bytes_cap']
 (HERE/'PREPARATION.json').write_text(json.dumps(plan,indent=2)+'\n');(root/'PREPARATION.json').write_text(json.dumps(plan,indent=2)+'\n')
 print(json.dumps(dict(status='PREPARED_NOT_RUN',root=str(root),removed_baseline_options=removed,actual_preflight={a:r['returncode'] for a,r in plan['actual_deadknob_preflight'].items()},old_failure_reproduced=wrong['returncode'],negative_controls=negatives,owned_total=b.used(root)+b.used(prior),preserved_old_files=len(priorpins),plan_sha256=b.sha(HERE/'PREPARATION.json'),SDK=0,Make_queries=0),indent=2))
if __name__=='__main__':main()
