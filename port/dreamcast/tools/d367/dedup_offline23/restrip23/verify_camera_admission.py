"""Verify complete v2 camera pins/bit expansion; no guest or state inference."""
import argparse,ast,hashlib,json,re,struct,configparser
from pathlib import Path
EXPECTED_SOURCE='c2f0d82e95050a708d0b977f94fad34890cbc279'
def sha(b):return hashlib.sha256(b).hexdigest()
def source_parser(source,expected_sha):
 if sha(source)!=expected_sha:raise ValueError('source parser pin')
 ns={'re':re}
 for n in ast.parse(source).body:
  if isinstance(n,ast.FunctionDef) and n.name in ('parse','legacy_line'):
   exec(compile(ast.Module(body=[n],type_ignores=[]),'<pinned camera source>','exec'),ns)
 if not all(x in ns for x in ('parse','legacy_line')):raise ValueError('parser methods missing')
 return ns['parse'],ns['legacy_line']
def exact_expansion(raw,derived,parse,legacy):
 raw=raw.replace('\r\n','\n');derived=derived.replace('\r\n','\n');rows={}
 for line in raw.splitlines(keepends=True):
  row=parse(line);f=row['frame']
  if f in rows:raise ValueError('duplicate frame')
  values=struct.unpack('<26f',struct.pack('<26I',row['far_bits'],*row['view_bits'],*row['projection_bits'],*row['viewport_bits']))
  import math
  if not all(math.isfinite(v) for v in values):raise ValueError('nonfinite camera')
  rows[f]=row
 wanted=list(range(500,795,7))
 if any(f not in rows for f in wanted):raise ValueError('missing requested full camera')
 if derived!=''.join(legacy(rows[f]) for f in wanted):raise ValueError('derived full fields differ')
 return dict(complete_rows=len(rows),frame_range=[min(rows),max(rows)],selected_frames=wanted,all26_camera_far_float_bits_preserved=True,all6_viewport_words_preserved=True)
def verify(admission_path,parser_source,programme_dir):
 b=admission_path.read_bytes();a=json.loads(b);root=admission_path.parent
 if a['status']!='PASS_COMPLETE_CAMERA_FOR_OFFLINE_MODEL' or a['source']!=EXPECTED_SOURCE:raise ValueError('wrong admission/source')
 for name,row in a['pins'].items():
  path=root/Path(name.replace('\\','/'));data=path.read_bytes()
  if len(data)!=row['bytes'] or sha(data)!=row['sha256']:raise ValueError('admission pin '+name)
 parse,legacy=source_parser(parser_source.read_bytes(),a['source_parser_sha256'])
 raw=(root/'FOREST-CAMERA-V2-RAW-RECORDS.txt').read_text();derived=(root/'FOREST-CAMERA-DERIVED-LEGACY.txt').read_text()
 result=exact_expansion(raw,derived,parse,legacy)
 lines=raw.splitlines(keepends=True);last=lines[-1];parts=last.split(' ');parts[-1]=parts[-1][:-2]+'\n'
 controls={}
 bads={'missing_final_newline':raw[:-1], 'short_final_word':''.join(lines[:-1])+ ' '.join(parts), 'duplicate_frame':raw+lines[0]}
 first=derived.splitlines(keepends=True)[0];token=first.split('vp=')[1].split()[5];badword=f'{int(token,16)^1:08x}'
 badderived=derived.replace('vp='+first.split('vp=')[1].strip(),'vp='+first.split('vp=')[1].strip().rsplit(' ',1)[0]+' '+badword,1)
 for name,bad in bads.items():
  try:exact_expansion(bad,derived,parse,legacy)
  except ValueError:controls[name]='REFUSED'
  else:raise AssertionError('negative accepted '+name)
 try:exact_expansion(raw,badderived,parse,legacy)
 except ValueError:controls['derived_viewport_bit_mutation']='REFUSED'
 else:raise AssertionError('derived bit mutation accepted')
 if result['selected_frames']!=a['selected_frames'] or result['complete_rows']!=a['complete_rows']:raise ValueError('admission record census')
 programme=json.loads((root/'PROGRAMME-PINS.json').read_text())
 if programme['source']!=EXPECTED_SOURCE:raise ValueError('programme source')
 for name,row in programme['files'].items():
  path=programme_dir/name;data=path.read_bytes()
  if len(data)!=row['size'] or sha(data)!=row['sha256']:raise ValueError('programme pin '+name)
 knobs=dict(re.findall(r'^([A-Z0-9_]+)=(.*)$',(programme_dir/'resolved-knobs.txt').read_text(),re.M))
 for k,v in dict(PS2_PVS='1',PS2_PVS_DEFAULT='2',SCENERY_SUBMIT_BATCH='0',SCENERY_FAR_LOD='4',QUALITY='1',QA_MENU='0',WORLD_METER='0').items():
  if knobs.get(k)!=v:raise ValueError('camera profile '+k)
 log=(root/'capture-r2/run-output.txt').read_text();rr=json.loads((root/'capture-r2/run-result.json').read_text());bound=json.loads((root/'capture-r2/bounded-launch.json').read_text())
 if 'quality: init mode=standard source=default features=00000001 lod_px=5' not in log:raise ValueError('quality evidence')
 if rr['emu']!='console' or rr['stop']!='warp: frozen at tick 800' or bound['pid']!=a['actual_guest_pid'] or bound['deadline_seconds']!=55 or bound['deadline_fired'] or bound['guest_observed_elapsed_s']>55:raise ValueError('capture profile/bounds')
 cfg=(root/'capture-r2/emu.cfg').read_text()
 cp=configparser.ConfigParser();cp.read_string(cfg)
 if cp.get('config','aica.LimitFPS',fallback='')!='yes':raise ValueError('explicit FPS setting')
 return dict(status='PASS_PINNED_COMPLETE_FOREST_CAMERA_FOR_OFFLINE_MODEL',admission=dict(path=str(admission_path),bytes=len(b),sha256=sha(b)),parser_sha256=a['source_parser_sha256'],camera_source=EXPECTED_SOURCE,runtime_recipe_base='fb254e82ee6f9a3d9e34d53d1d442348a46b9cf2',programme_pins_checked=len(programme['files']),root_pins_checked=len(a['pins']),effective_lod_divisor=20,actual_data_negative_controls=controls,**result,scope='All full camera float fields preserved from pinned source v2 rows; no full sampled runtime state, performance, target requalification or look equality claim.')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--admission',type=Path,required=True);ap.add_argument('--parser-source',type=Path,required=True);ap.add_argument('--programme-dir',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
 if a.output.exists():raise FileExistsError(a.output)
 out=verify(a.admission,a.parser_source,a.programme_dir);a.output.write_bytes((json.dumps(out,indent=2)+'\n').encode());print(json.dumps(out,indent=2))
if __name__=='__main__':main()
