"""Pure source/profile/export/pin checks; never SDK/Make."""
from pathlib import Path
import json,copy,subprocess
from prepare_qa_pair import base,verify
P=Path(__file__).resolve().parent

def validate(plan,files=True):
 assert plan['status']=='PREPARED_NOT_RUN' and plan['arm_order']==['baseline','off','on']
 assert plan['sources']=={'baseline':'fb254e82ee6f9a3d9e34d53d1d442348a46b9cf2','off':base.SOURCE,'on':base.SOURCE}
 assert plan['no_execution']==dict(SDK=0,Make_queries=0,compiles=0,links=0,staging=0,guest=0)
 assert plan['budget']['owned_bytes_cap']==2*1024**3 and plan['budget']['jobs']==plan['budget']['shared_slots']==1
 assert plan['budget']['C_admission_bytes']==26*1024**3 and plan['budget']['C_floor_bytes']==24*1024**3
 assert plan['budget']['RAM_admission_bytes']==3*1024**3 and plan['budget']['RAM_floor_bytes']==512*1024**2
 assert len(plan['expected_overlays'])==14 and plan['expected_current_raw_object_counts']==dict(baseline=449,off=449,on=455)
 root=Path(plan['root'])
 for arm in plan['arm_order']:
  argv=plan['commands'][arm];assert argv[:2]==['bash',str(root/arm/'source/port/dreamcast/tools/d367/build-r21.sh')]
  flags=dict(x.split('=',1) for x in argv[2:]);assert flags==plan['resolved_expected'][arm]
  for k,v in [x.split('=',1) for x in plan['diagnostic_overrides']]:assert flags[k]==v
  assert flags['GC_ASSET_GATE']==flags['GC_ASSET_MOTION_UNKNOWN']==str(int(arm=='on'))
  assert flags['GC_ASSET_CATALOG_SHA256']=='0' and flags['QA_MENU']==flags['WORLD_METER']=='0'
  assert plan['environment'][arm]['JOBS']=='1' and plan['environment'][arm]['ASSETS']=='/root/probe/lanes/play-actor-bundle'
  if files:
   assert not (root/arm/'out').exists() and not (root/arm/'source/port/dreamcast/game/obj').exists()
   verify({str(root/arm/'source'/n):r for n,r in plan['source_manifests'][arm].items()})
   sub=base.git(base.TREE,'ls-tree',plan['sources'][arm],'port/dreamcast/game/third_party/sh4zam');assert base.SUBCOMMIT in sub
 if files:
  verify(plan['input_pins']);verify(plan['original_normal_pair_manifest'])
  assert base.used(root)<plan['budget']['owned_bytes_cap']
 assert plan['OFF_identity']['baseline_source']==plan['sources']['baseline']
 assert '49a4' in plan['OFF_identity']['compare'] and 'No production' in plan['OFF_identity']['compare']
 return True

if __name__=='__main__':
 plan=json.loads((P/'PREPARATION-THREE.json').read_text());validate(plan)
 negatives=[]
 for label,change in [('QA-profile-enabled',lambda p:p['resolved_expected']['off'].update(QA_MENU='1')),('catalog-enabled',lambda p:p['resolved_expected']['on'].update(GC_ASSET_CATALOG_SHA256='1'*64)),('off-motion-enabled',lambda p:p['resolved_expected']['off'].update(GC_ASSET_MOTION_UNKNOWN='1')),('drop-baseline',lambda p:p['arm_order'].pop(0)),('wrong-baseline-source',lambda p:p['sources'].update(baseline=base.SOURCE)),('extra-jobs',lambda p:p['budget'].update(jobs=4)),('missing-overlay',lambda p:p['expected_overlays'].pop())]:
  p=copy.deepcopy(plan);change(p)
  try:validate(p,False)
  except AssertionError:negatives.append(label)
  else:raise AssertionError(label+' escaped')
 print(json.dumps(dict(status='PURE_PREPARATION_READBACK_PASS',sources=plan['sources'],arms=3,input_pins=len(plan['input_pins']),normal_files=len(plan['original_normal_pair_manifest']),source_files=plan['source_files_per_arm'],negative_controls=negatives,SDK_commands=0),indent=2))
