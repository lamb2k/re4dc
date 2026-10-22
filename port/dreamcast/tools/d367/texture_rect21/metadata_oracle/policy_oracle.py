"""Pure offline policy oracle. No process/memory access and no target acceptance.
Input values must come from caller-owned exact-program, coherent read-only capture.
Synthetic tests validate this oracle's predicates, not the game implementation.
"""
import copy,json

def evaluate(expect,observation,*,allow_held_static=False):
 room=observation.get('room'); scenario=observation.get('scenario')
 if room not in expect['rooms'] or scenario not in expect['scenarios']:
  return dict(status='REJECT',reason='unknown room/scenario')
 for k in ('ELF_sha256','programme_sha256','source'):
  if observation.get(k)!=expect[k]:return dict(status='REJECT',reason='identity:'+k)
 if not observation.get('phase_qualified') or not observation.get('roots_stable'):
  return dict(status='WAIT',reason='unqualified phase or changed roots')
 r=expect['rooms'][room];world=r[expect['scenarios'][scenario][room]]
 lifecycle=observation.get('lifecycle')
 if lifecycle not in ('post_open','after_movie'):
  return dict(status='WAIT',reason='loading/movie phase unavailable')
 if lifecycle=='after_movie' and room!='r100':
  return dict(status='REJECT',reason='movie oracle only applies r100')
 failures=[]
 def check(key,want):
  if observation.get(key)!=want:failures.append(key)
 check('physical_world_sha256',world['sha256']);check('physical_world_body_crc',world['body_crc'])
 check('physical_world_full_crc',world['crc32']);check('physical_world_fnv',world['fnv_bytes'])
 check('sourceWorldSidecarCrc',world['body_crc']);check('enemyVisSidecarCrc',r['source_crc'])
 check('package_mesh_crc',r['mesh']['body_crc']);check('package_mesh_bytes',r['mesh']['bytes'])
 check('package_parts',r['mesh']['parts']);check('package_meshes',r['mesh']['meshes'])
 check('placements',r['placements']);check('placement_pointer_relation',True)
 check('id_header_source_crc',r['source_crc']);check('id_body_sha256',r['ids']['body']['sha256'])
 check('id_count',r['placements']);check('id_unique',r['ids']['unique_slots']);check('id_slot_of',r['ids']['slot_of'])
 check('id_pointer_relations',True)
 check('occl_ok',1);check('occl_room',r['room']);check('occl_crc',r['source_crc']);check('occl_nocc',r['OCCL']['occluders'])
 check('world_intact_source_predicate',True)
 # This predicate mirrors static source eligibility, not occluder placement liveness.
 if lifecycle=='post_open':
  check('trans_policy',3);check('trans_room',r['room']);check('trans_parts',r['classes']['parts'])
  check('trans_header_source_crc',r['source_crc']);check('trans_class_body_sha256',r['classes']['class_body']['sha256'])
  check('trans_pointer_relations',True);check('pass_mask_sha256',r['pass_mask']['sha256'])
 else:
  check('trans_idle',True) # cls=null/nparts0/room~0, actual baseline reload path
  check('pass_mask_raw_sha256',r['pass_mask_after_movie']['sha256'])
 if room=='r100':
  check('pc_ok',True)
  if observation.get('pc_lent') or not observation.get('pc_loaded'):
   return dict(status='WAIT',reason='PCL lending/reload not settled',failures=failures)
  check('pc_file_sha256',r['PCL']['sha256'])
  # File ownership capture remains actual, including the original M0 scenario.
  check('movie_mesh_crc',r['mesh']['crc32']);check('movie_mesh_fnv',r['mesh']['fnv_bytes'])
  check('movie_side_crc',world['crc32']);check('movie_side_fnv',world['fnv_bytes'])
  check('movie_mesh_bytes',r['mesh']['bytes']);check('movie_side_bytes',world['bytes'])
 else:check('pc_ok',False)
 if room=='r101':
  check('sg_groups',4);check('sg_pointer_relation',True);check('sg_file_sha256',r['R4SG']['sha256'])
  check('sg_source_crc',r['source_crc']);check('sg_record_crc',r['R4SG']['record_crc'])
 else:check('sg_groups',0)
 if failures:return dict(status='MISMATCH',failures=failures)
 if 'HOLD' in expect['status'] and not allow_held_static:
  return dict(status='HOLD',reason='matching static policy metadata cannot qualify held CRC programme/assets')
 return dict(status='STATIC_PREDICATES_MATCH',limits='No live capture, placement liveness, raster, timing, allocator or hardware proof')

def synthetic_observation(expect,room,scenario='994',lifecycle='post_open'):
 """Test data only; never emit as observed evidence."""
 r=expect['rooms'][room];w=r[expect['scenarios'][scenario][room]]
 o={k:expect[k]for k in('ELF_sha256','programme_sha256','source')}
 o.update(room=room,scenario=scenario,lifecycle=lifecycle,phase_qualified=True,roots_stable=True,
 physical_world_sha256=w['sha256'],physical_world_body_crc=w['body_crc'],physical_world_full_crc=w['crc32'],physical_world_fnv=w['fnv_bytes'],
 sourceWorldSidecarCrc=w['body_crc'],enemyVisSidecarCrc=r['source_crc'],package_mesh_crc=r['mesh']['body_crc'],package_mesh_bytes=r['mesh']['bytes'],package_parts=r['mesh']['parts'],package_meshes=r['mesh']['meshes'],
 placements=r['placements'],placement_pointer_relation=True,id_header_source_crc=r['source_crc'],id_body_sha256=r['ids']['body']['sha256'],id_count=r['placements'],id_unique=r['ids']['unique_slots'],id_slot_of=r['ids']['slot_of'],id_pointer_relations=True,
 occl_ok=1,occl_room=r['room'],occl_crc=r['source_crc'],occl_nocc=r['OCCL']['occluders'],world_intact_source_predicate=True,
 trans_policy=3,trans_room=r['room'],trans_parts=r['classes']['parts'],trans_header_source_crc=r['source_crc'],trans_class_body_sha256=r['classes']['class_body']['sha256'],trans_pointer_relations=True,pass_mask_sha256=r['pass_mask']['sha256'],
 trans_idle=True,pass_mask_raw_sha256=r['pass_mask_after_movie']['sha256'],pc_ok=room=='r100',pc_lent=False,pc_loaded=True,sg_groups=4 if room=='r101'else 0)
 if room=='r100':o.update(pc_file_sha256=r['PCL']['sha256'],movie_mesh_crc=r['mesh']['crc32'],movie_mesh_fnv=r['mesh']['fnv_bytes'],movie_side_crc=w['crc32'],movie_side_fnv=w['fnv_bytes'],movie_mesh_bytes=r['mesh']['bytes'],movie_side_bytes=w['bytes'])
 if room=='r101':o.update(sg_pointer_relation=True,sg_file_sha256=r['R4SG']['sha256'],sg_source_crc=r['source_crc'],sg_record_crc=r['R4SG']['record_crc'])
 return o

def selftest(expect):
 results=[]
 def run(name,o,status):
  result=evaluate(expect,o);assert result['status']==status,(name,result);results.append(dict(name=name,result=result['status']))
 for room in ('r100','r101','r103'):
  for scenario in ('M0','965','994'):run(room+' '+scenario+' static-held',synthetic_observation(expect,room,scenario),'HOLD')
 base=synthetic_observation(expect,'r100')
 for key,value in [('ELF_sha256','0'*64),('programme_sha256','0'*64),('source','0'*40)]:
  o=copy.deepcopy(base);o[key]=value;run('wrong '+key,o,'REJECT')
 for key,value in [('sourceWorldSidecarCrc',expect['rooms']['r100']['source_crc']),('enemyVisSidecarCrc',base['physical_world_body_crc']),('id_header_source_crc',base['physical_world_body_crc']),('trans_header_source_crc',base['physical_world_body_crc']),('physical_world_fnv',0),('trans_class_body_sha256','0'*64),('pc_file_sha256','0'*64),('occl_crc',base['physical_world_body_crc']),('movie_side_crc',expect['rooms']['r100']['source_crc'])]:
  o=copy.deepcopy(base);o[key]=value;run('reject mutated '+key,o,'MISMATCH')
 o=synthetic_observation(expect,'r101');o['sg_source_crc']=o['physical_world_body_crc'];run('SG physical instead source CRC',o,'MISMATCH')
 for key,value in [('roots_stable',False),('phase_qualified',False),('lifecycle','borrowed'),('pc_lent',True),('pc_loaded',False)]:
  o=copy.deepcopy(base);o[key]=value;run('WAIT '+key,o,'WAIT')
 o=synthetic_observation(expect,'r100',lifecycle='after_movie');o['trans_parts']=0;o['trans_class_body_sha256']=None;run('baseline movie idle not false class failure',o,'HOLD')
 # Unknown room/scenario do not silently select an expected certificate.
 o=copy.deepcopy(base);o['room']='r102';run('unknown room',o,'REJECT')
 o=copy.deepcopy(base);o['scenario']='future';run('unknown scenario',o,'REJECT')
 return dict(status='PASS_OFFLINE_ORACLE_TESTS_ONLY',tests=results,count=len(results),limits='Synthetic predicates. Existing47 actual extracted-source tests remain separate; no guest or target acceptance.')

if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--expected',required=True);p.add_argument('--test-output',required=True);args=p.parse_args()
 e=json.load(open(args.expected));out=selftest(e)
 with open(args.test_output,'x')as f:json.dump(out,f,indent=2);f.write('\n')
 print(json.dumps(dict(status=out['status'],count=out['count'])))