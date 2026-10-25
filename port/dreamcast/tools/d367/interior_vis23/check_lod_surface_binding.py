"""Current source/profile pin negatives, read-only with RAM-mutated views."""
import argparse,importlib.util,json,tempfile
from pathlib import Path
from unittest.mock import patch
p=argparse.ArgumentParser();p.add_argument('--source-tree',required=True,type=Path);p.add_argument('--profile',required=True,type=Path);p.add_argument('--out',required=True,type=Path);v=p.parse_args()
s=importlib.util.spec_from_file_location('audit',Path(__file__).with_name('lod_surface_audit.py'));a=importlib.util.module_from_spec(s);s.loader.exec_module(a)
baseline=a.bind_source(v.source_tree,v.profile);results={}
with tempfile.TemporaryDirectory(prefix='interior-surface-bind-',dir='/dev/shm') as d:
 for key,new in [('QUALITY_LOD_PX','4'),('SCENERY_FAR_LOD','3'),('SCENERY_DEDUP','3')]:
  path=Path(d)/(key+'.txt');text=v.profile.read_text();before=key+'='+baseline['knobs'][key];assert text.count(before+'\n')==1;path.write_text(text.replace(before+'\n',key+'='+new+'\n'))
  try:a.bind_source(v.source_tree,path)
  except ValueError as e:results['profile_'+key]=str(e)
  else:raise AssertionError('Wrong current profile accepted')
 original=Path.read_bytes
 for name,rel,before,after in [('source_lod_divisor','port/dreamcast/game/platform/native_static.cpp',b'const float lod_div=lod_px*float(RE4DC_SCENERY_FAR_LOD);',b'const float lod_div=lod_px;'),('source_box_frustum','port/dreamcast/room/pvr_geometry.cpp',None,None)]:
  target=v.source_tree/rel
  def read_mutant(q):
   data=original(q)
   if q!=target:return data
   if before is None:return data+b'\n// private read-intercept pin negative\n'
   assert data.count(before)==1;return data.replace(before,after)
  with patch.object(Path,'read_bytes',read_mutant):
   try:a.bind_source(v.source_tree,v.profile)
   except ValueError as e:results[name]=str(e)
   else:raise AssertionError('Changed renderer policy accepted')
assert len(results)==5
with v.out.open('x') as f:json.dump(dict(baseline=baseline,negatives_rejected=results,source_mutation_method='Private RAM read-intercept only; tracked/shared source files untouched',actual_profile_file_unchanged=a.identity(v.profile)),f,indent=2)
print(json.dumps(dict(baseline=True,negative_controls=len(results),all_refused=True)))
