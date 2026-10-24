"""Independent byte/argv consistency readback; no subprocess/SDK execution."""
from pathlib import Path
import copy,hashlib,json,shlex
HERE=Path(__file__).resolve().parent
PARENT='870789095c4c14fbdbf22043447b249063d2ec3a'
CURRENT='aab201ceac0e18107f64a3212398afe916793327'
UNITS=['platform/native_ui.cpp','platform/native_model.cpp','platform/native_actor_fast.cpp','model_bridge.cpp']
HELPER='platform/gc_asset_motion_unknown.cpp'
FULL=Path('/root/work/lanes/gc-port23-full-target2-scratch')
PREFIX='port/dreamcast/game/'

def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()

def validate(plan,files=True):
 assert plan['status']=='PREPARED_NOT_EXECUTED' and plan['head']==CURRENT and plan['parent']==PARENT
 assert plan['sdk_commands']==plan['wrapper_queries']==0 and not plan['slot_acquired']
 assert len(plan['arms'])==plan['arm_count']==33 and plan['ON_count']==5
 out=Path(plan['export']);seen=set();ON=0
 for row in plan['arms']:
  unit,label,gate,motion=row['unit'],row['label'],row['gate'],row['motion']
  assert unit in UNITS+[HELPER] and label in ['parent','current'] and gate in [0,1] and motion in ['absent','zero','on']
  key=(unit,label,gate,motion);assert key not in seen;seen.add(key)
  assert row['source']==(PARENT if label=='parent' else CURRENT)
  assert row['group']==('GAME' if unit=='model_bridge.cpp' else 'PLATFORM')
  assert row['new_helper_template']==(unit==HELPER)
  assert row['empty_required']==(unit==HELPER and motion!='on')
  if unit==HELPER:assert label=='current'
  if motion=='on':assert gate==1 and label=='current';ON+=1
  template=row['raw_command_template'];original=shlex.split(template['raw']);assert original==template['args']
  assert original[original.index('-c')+1]==('platform/gc_asset_gate.cpp' if unit==HELPER else unit)
  if files:assert (FULL/('on' if gate else 'off')/'build.log').read_text().splitlines()[template['line']-1]==template['raw']
  expected=[x for x in original if x not in ['-MMD','-MP','-MD']]
  for option in ['-MF','-MT','-MQ']:
   while option in expected:i=expected.index(option);del expected[i:i+2]
  arm='on' if gate else 'off'
  for i,x in enumerate(expected):
   if x.startswith(str(FULL/arm/'out/obj')+'/') and x!=original[original.index('-o')+1]:
    expected[i]=str(out/'generated'/arm/Path(x).relative_to(FULL/arm/'out/obj'))
  if motion!='absent':expected.append('-DRE4DC_GC_ASSET_MOTION_UNKNOWN='+('1' if motion=='on' else '0'))
  expected[expected.index('-c')+1]=unit;expected[expected.index('-o')+1]=str(out/'objects'/(row['tag']+'.o'));expected.append('-fstack-usage')
  assert row['argv']==expected
  assert row['cwd']==str(out/label/PREFIX)
  a=row['argv'];assert a[0]=='kos-c++'
  assert [x for x in a if x.startswith('-DRE4DC_GC_ASSET_GATE=')]==(['-DRE4DC_GC_ASSET_GATE=1'] if gate else [])
  assert [x for x in a if x.startswith('-DRE4DC_GC_ASSET_MOTION_UNKNOWN=')]==([] if motion=='absent' else ['-DRE4DC_GC_ASSET_MOTION_UNKNOWN='+('1' if motion=='on' else '0')])
  assert bool([x for x in a if x.startswith('-DRE4DC_GC_ASSET_CATALOG_SHA256=')])==(bool(gate) and unit!='model_bridge.cpp')
  if files:assert (out/label/PREFIX/unit).is_file()
 assert ON==5
 for unit in UNITS:
  assert {x[1:] for x in seen if x[0]==unit}=={('parent',0,'absent'),('parent',1,'absent'),('current',0,'absent'),('current',0,'zero'),('current',1,'absent'),('current',1,'zero'),('current',1,'on')}
 assert {x[1:] for x in seen if x[0]==HELPER}=={('current',0,'absent'),('current',0,'zero'),('current',1,'absent'),('current',1,'zero'),('current',1,'on')}
 if files:
  for key,pin in plan['source_pins'].items():
   label,name=key.split(':',1);path=out/label/name;assert path.stat().st_size==pin['bytes'] and sha(path)==pin['sha256']
  for path,pin in plan['input_pins'].items():assert Path(path).stat().st_size==pin['bytes'] and sha(path)==pin['sha256']
  manifest=json.loads((HERE/'EXPORT-MANIFEST.json').read_text());assert manifest['export']==str(out)
  for name,pin in manifest['files'].items():assert sha(out/name)==pin['sha256']
  assert not (out/'parent'/PREFIX/HELPER).exists()
  for row in plan['arms']:
   a=row['argv']
   for i,x in enumerate(a):
    if x=='-include':assert (Path(a[i+1]) if Path(a[i+1]).is_absolute() else Path(row['cwd'])/a[i+1]).is_file()
 return len(seen)

if __name__=='__main__':
 plan=json.loads((HERE/'PREPARATION.json').read_text());validate(plan)
 mutants=[]
 for kind in ['missing-arm','wrong-GAME-pin','missing-motion-flag','wrong-source','helper-parent','extra-optimization']:
  bad=copy.deepcopy(plan)
  if kind=='missing-arm':bad['arms'].pop()
  elif kind=='wrong-GAME-pin':next(x for x in bad['arms'] if x['unit']=='model_bridge.cpp' and x['motion']=='on')['argv'].append('-DRE4DC_GC_ASSET_CATALOG_SHA256="0"')
  elif kind=='missing-motion-flag':r=next(x for x in bad['arms'] if x['motion']=='on');r['argv']=[x for x in r['argv'] if 'MOTION_UNKNOWN' not in x]
  elif kind=='wrong-source':bad['arms'][0]['source']=CURRENT
  elif kind=='helper-parent':next(x for x in bad['arms'] if x['unit']==HELPER)['label']='parent'
  else:bad['arms'][0]['argv'].append('-O0')
  try:validate(bad,False)
  except AssertionError:mutants.append(kind)
  else:raise AssertionError('invalid matrix escaped '+kind)
 result={'status':'PREPARATION_READBACK_PASS','arm_count':33,'ON_count':5,'source_export_pins':len(plan['source_pins']),'input_pins':len(plan['input_pins']),'rejected_metadata_mutants':mutants,'sdk_commands':0,'scope':'Byte/argv/export preparation only. No compiler, wrapper, version, dependency-generation, object, target or runtime execution.'}
 (HERE/'READBACK.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
