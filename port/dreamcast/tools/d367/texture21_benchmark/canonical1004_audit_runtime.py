#!/usr/bin/env python3
"""Fresh exact linked ELF path/width audits for runtime04, without target builds."""
import argparse,hashlib,json,re,subprocess,sys
from pathlib import Path
from canonical1004_audit_scene import dies
ELF='69f2e7db588f515f4e6a67455d627a74fc17132d5ca20a591db4e0f15deedcae'

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--elf',type=Path,required=True);ap.add_argument('--plan',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--readelf',default='/opt/toolchains/dc/sh-elf/bin/sh-elf-readelf');a=ap.parse_args();assert hashlib.sha256(a.elf.read_bytes()).hexdigest()==ELF
 a.out.mkdir(exist_ok=False);here=Path(__file__).parent
 subprocess.run([sys.executable,str(here/'canonical1004_audit_scene.py'),'--elf',str(a.elf),'--plan',str(a.plan),'--out',str(a.out/'scene-package-paths.json')],check=True)
 subprocess.run([sys.executable,str(here/'canonical1004_audit_phase.py'),'--elf',str(a.elf),'--out',str(a.out/'phase-contract.json')],check=True)
 base=json.loads((a.out/'scene-package-paths.json').read_text());phase=json.loads((a.out/'phase-contract.json').read_text());scene=json.loads((a.plan/'observer-runtime-03/scene-existing-dwarf02.json').read_text())
 for name,actual in base['compilation_units']['scene']['types'].items():
  assert actual['size']==scene['types'][name]['size'] and actual['members']==scene['types'][name]['members']
 paths={(r['type'],r['member']):r for r in base['member_paths']}
 required={'GlobalWork':{'Rno0':1,'Frame_cnt':4,'System_flg':4,'Stop_flg':4,'Cam':248,'room_id':2,'pl_life':2,'pl_life_max':2,'ashley_life':2,'ashley_life_max':2},'CameraControl':{'camera':248},'cCoord':{'pos':12,'ang':12}}
 for typ,fields in required.items():
  for name,width in fields.items():assert paths[typ,name]['type_size_bytes']==width,(typ,name)
 # Extract exact CU again to type every completed-frame member, not just offset.
 block=[];native=None;units={}
 def take(lines):
  nonlocal native
  name=next((l.split(': ')[-1].strip() for l in lines[:30] if 'DW_AT_name ' in l),'')
  if name.endswith('platform/native_ui.cpp'):assert native is None;native=lines
  for basename in ('native_ui.cpp','debug.cpp','pace.cpp','tick_log.cpp'):
   if name.endswith('/'+basename) or name==basename:assert basename not in units;units[basename]=lines
 proc=subprocess.Popen([a.readelf,'--debug-dump=info',str(a.elf)],stdout=subprocess.PIPE,text=True)
 for line in proc.stdout:
  if 'Compilation Unit @ offset' in line:
   if block:take(block)
   block=[]
  block.append(line)
 take(block);assert proc.wait()==0 and native
 rows=dies(native);by={r['offset']:i for i,r in enumerate(rows)};root=by[phase['completed_frame_type']['DIE_offset']]
 def ref(d):return by[re.search(r'<0x([0-9a-f]+)>',d['attrs']['type'])[1]]
 def size(i):
  r=rows[i];at=r['attrs']
  if 'byte_size' in at:return int(at['byte_size'],0)
  if r['tag']=='DW_TAG_pointer_type':return 4
  if r['tag']=='DW_TAG_array_type':
   n=1
   for x in rows[i+1:]:
    if x['depth']<=r['depth']:break
    if x['depth']==r['depth']+1 and x['tag']=='DW_TAG_subrange_type':n*=int(x['attrs'].get('upper_bound','-1'),0)+1
   return n*size(ref(r))
  return size(ref(r))
 stats=[]
 for r in rows[root+1:]:
  if r['depth']<=rows[root]['depth']:break
  if r['tag']=='DW_TAG_member' and r['depth']==rows[root]['depth']+1:
   at=r['attrs'];name=at['name'].split(': ')[-1];off=int(at['data_member_location'],0);width=size(ref(r));assert phase['completed_frame_type']['members'][name]==off;assert width==(120 if name=='work' else 4)
   stats.append({'member':name,'offset':off,'bytes':width,'DIE':r['offset'],'type_ref':at['type']})
 assert len(stats)==len(phase['completed_frame_type']['members'])==19
 chains={}
 for key,v in phase['variables'].items():
  rr=dies(units[key.split(':')[0]]);bb={r['offset']:r for r in rr};at=v['resolved_attrs']['type'];chain=[]
  while at:
   x=bb[re.search(r'<0x([0-9a-f]+)>',at)[1]];chain.append({'DIE':x['offset'],'tag':x['tag'],'byte_size':x['attrs'].get('byte_size'),'name':x['attrs'].get('name')});at=x['attrs'].get('type')
  chains[key]=chain
 namechain=chains['debug.cpp:proc_name'];assert namechain[0]['tag']=='DW_TAG_array_type' and namechain[1]['tag']=='DW_TAG_pointer_type' and int(namechain[1]['byte_size'],0)==4
 tickchain=chains['debug.cpp:proc_tick'];assert tickchain[0]['tag']=='DW_TAG_array_type' and int(tickchain[-1]['byte_size'],0)==4
 report={'result':'PASS','exact_ELF_sha256':ELF,'target_pointer_bytes':4,'scene_package_member_paths':len(base['member_paths']),'pointer_paths':len(base['pointer_paths']),'runtime_symbols':len(base['symbols']),'phase_variables':len(phase['variables']),'phase_variable_type_chains':chains,'completed_frame_member_paths':stats,'extra_runtime04_member_accesses':{typ:{n:paths[typ,n] for n in fields} for typ,fields in required.items()},'duplicate_entries_binding':base['duplicate_entries_binding'],'duplicate_phase_symbols':{k:v for k,v in phase['variables'].items() if v['same_mangled_symbol_elsewhere']},'scene_package_report_sha256':hashlib.sha256((a.out/'scene-package-paths.json').read_bytes()).hexdigest(),'phase_report_sha256':hashlib.sha256((a.out/'phase-contract.json').read_bytes()).hexdigest(),'scope':'Actual linked69f ELF, CU/DIE/type widths and duplicate locations. No guest/runtime coverage.'}
 (a.out/'runtime69f-path-width-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k] for k in ('result','scene_package_member_paths','pointer_paths','phase_variables')}))
if __name__=='__main__':main()
