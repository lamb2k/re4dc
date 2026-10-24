"""Pure preparation readback. No process, SDK, Make or linker execution."""
from pathlib import Path
import copy,hashlib,json
HERE=Path(__file__).resolve().parent
SOURCE='aab201ceac0e18107f64a3212398afe916793327'

def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()

def validate(plan,files=True):
 assert plan['status']=='PREPARED_NOT_RUN' and plan['source']==SOURCE
 assert plan['no_execution']==dict(SDK=0,Make_queries=0,links=0,staging=0,guest=0)
 assert plan['budget']['jobs']==plan['budget']['shared_slots']==1
 assert plan['budget']['C_floor_bytes']==24*1024**3 and plan['budget']['owned_bytes_cap']==2*1024**3
 assert len(plan['expected_overlays'])==14 and len(set(plan['expected_overlays']))==14
 assert plan['expected_current_raw_object_counts']==dict(off=448,on=454)
 assert len(plan['changed_translation_units'])==7
 root=Path(plan['root'])
 assert root.is_relative_to(Path('/dev/shm'))
 for arm,gate,motion in [('off','0','0'),('on','1','1')]:
  command=plan['commands'][arm];env=plan['environment'][arm]
  assert command[:2]==['bash',str(root/arm/'source/port/dreamcast/tools/d367/build-r21.sh')]
  assert command[-3:]==['GC_ASSET_GATE='+gate,'GC_ASSET_CATALOG_SHA256=0','GC_ASSET_MOTION_UNKNOWN='+motion]
  assert env['OUT']==str(root/arm/'out') and env['OBJDIR']==str(root/arm/'out/obj')
  assert env['JOBS']=='1' and env['SOURCE_DATE_EPOCH']=='1760000000'
  assert env['ASSETS']=='/root/probe/lanes/play-actor-bundle'
  if files:
   assert not (root/arm/'out').exists() and not (root/arm/'source/port/dreamcast/game/obj').exists()
   for name,row in plan['source_manifest'].items():
    q=root/arm/'source'/name;assert q.stat().st_size==row['bytes'] and sha(q)==row['sha256']
   assert (root/arm/'source/port/dreamcast/game/third_party/sh4zam/include/sh4zam/shz_xmtrx.h').is_file()
 for arm,count in [('off',448),('on',453)]:
  graph=plan['old_graph'][arm];assert graph['object_count']==len(graph['raw_object_order'])==count and graph['overlay_order']==plan['expected_overlays']
 if files:
  for path,row in {**plan['input_pins'],**plan['original_old_full_manifest']}.items():assert Path(path).stat().st_size==row['bytes'] and sha(path)==row['sha256']
 return True

if __name__=='__main__':
 plan=json.loads((HERE/'PREPARATION.json').read_text());validate(plan)
 mutants=[]
 for name in ['MotionOFF-in-ON','catalog-configured','old-source-output','missing-overlay','jobs4','source-wrong','old-graph-reused-as-new']:
  bad=copy.deepcopy(plan)
  if name=='MotionOFF-in-ON':bad['commands']['on'][-1]='GC_ASSET_MOTION_UNKNOWN=0'
  elif name=='catalog-configured':bad['commands']['on'][-2]='GC_ASSET_CATALOG_SHA256='+'1'*64
  elif name=='old-source-output':bad['environment']['on']['OUT']='/root/work/lanes/gc-port23-full-target2-scratch/on/out'
  elif name=='missing-overlay':bad['expected_overlays'].pop()
  elif name=='jobs4':bad['environment']['on']['JOBS']='4'
  elif name=='source-wrong':bad['source']=plan['old_full_source']
  else:bad['expected_current_raw_object_counts']['on']=453
  try:validate(bad,False)
  except AssertionError:mutants.append(name)
  else:raise AssertionError('bad preparation escaped '+name)
 result={'status':'FRESH_NORMAL_PAIR_PREPARATION_READBACK_PASS','source':SOURCE,'source_files_per_arm':plan['source_files_per_arm'],'source_export_bytes_per_arm':plan['source_export_bytes_per_arm'],'input_pins_verified':len(plan['input_pins']),'old_full_files_preserved_and_rehashed':len(plan['original_old_full_manifest']),'fresh_arms':2,'old_object_reuse':False,'rejected_metadata_mutants':mutants,'SDK_commands':0,'Make_queries':0,'links':0,'output_dirs_created':False,'limits':'Preparation only. Actual full Make expansion, all fresh compiles/links/14 overlays, raw identity and linked_end remain unmeasured until root allocation.'}
 (HERE/'READBACK.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
