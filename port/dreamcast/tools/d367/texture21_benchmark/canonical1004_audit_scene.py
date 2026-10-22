#!/usr/bin/env python3
"""Validate every observer field against selected compilation units in the exact linked ELF."""
import argparse,hashlib,json,re,struct,subprocess
from pathlib import Path
from dwarf_layout import parse
from prepare_candidate import select_symbol
ELF='69f2e7db588f515f4e6a67455d627a74fc17132d5ca20a591db4e0f15deedcae'

def dies(lines):
 rows=[];current=None
 for line in lines:
  m=re.match(r'\s*<(\d+)><([0-9a-f]+)>:.*\((DW_TAG_\w+)\)',line)
  if m:
   if current:rows.append(current)
   current={'depth':int(m[1]),'offset':m[2],'tag':m[3],'attrs':{}}
  elif re.match(r'\s*<\d+><[0-9a-f]+>: Abbrev Number: 0',line):
   if current:rows.append(current)
   current=None
  elif current:
   m=re.search(r'DW_AT_(\w+)\s*:\s*(.*)',line)
   if m:current['attrs'][m[1]]=m[2].strip()
 if current:rows.append(current)
 return rows

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--elf',type=Path,required=True);ap.add_argument('--plan',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--readelf',default='/opt/toolchains/dc/sh-elf/bin/sh-elf-readelf');ap.add_argument('--nm',default='/opt/toolchains/dc/sh-elf/bin/sh-elf-nm');a=ap.parse_args()
 blob=a.elf.read_bytes();assert hashlib.sha256(blob).hexdigest()==ELF
 assert blob[:6]==b'\x7fELF\x01\x01' and struct.unpack_from('<H',blob,18)[0]==42
 plan=json.loads((a.plan/'observation-cold-window.json').read_text());expected=plan['read_only_observer']['typed_layouts'];expected['scene']=json.loads((a.plan/'observer-runtime-02/scene-existing-dwarf02.json').read_text())
 spec={'scene':('src/game/cam_ctrl.cpp',['GlobalWork','CameraControl','Camera']),'player':('src/game/model.cpp',['cCoord']),'native_ui':('platform/native_ui.cpp',['Entry','Key','Package','Header','Texture'])}
 units={};block=[]
 def take(lines):
  name=None
  for line in lines[:30]:
   if 'DW_AT_name ' in line:name=line.split(': ')[-1].strip();break
  if name:
   for group,(suffix,wanted) in spec.items():
    if name.endswith(suffix):
     assert group not in units,'duplicate compilation unit'
     assert any(re.search(r'Pointer Size:\s+4$',l) for l in lines[:10])
     units[group]={'source':name,'lines':lines,'types':parse(lines,wanted),'dies':dies(lines)}
 proc=subprocess.Popen([a.readelf,'--debug-dump=info',str(a.elf)],stdout=subprocess.PIPE,text=True)
 for line in proc.stdout:
  if 'Compilation Unit @ offset' in line:
   if block:take(block)
   block=[]
  block.append(line)
 take(block);assert proc.wait()==0;assert set(units)==set(spec)
 report={'result':'PASS','exact_ELF_sha256':ELF,'elf_class':32,'endian':'little','machine':'SuperH','all_selected_CU_pointer_size_bytes':4,'scope':'Actual linked ELF DWARF/symbol paths, plus separate synthetic value read exercise; no guest','compilation_units':{},'member_paths':[],'pointer_paths':[]}
 for group,u in units.items():
  for name,record in u['types'].items():
   exp=expected[group]['types'][name]
   assert record['size']==exp['size'] and record['members']==exp['members'],(group,name,'object/ELF layout mismatch')
  rows=u['dies'];by={d['offset']:i for i,d in enumerate(rows)}
  def children(i):
   depth=rows[i]['depth']
   for j in range(i+1,len(rows)):
    if rows[j]['depth']<=depth:break
    if rows[j]['depth']==depth+1:yield j
  def ref(d):
   m=re.search(r'<0x([0-9a-f]+)>',d['attrs'].get('type',''));return by[m[1]] if m and m[1] in by else None
  def fields(i,base=0,path=(),seen=()):
   assert i not in seen
   union=rows[i]['tag']=='DW_TAG_union_type'
   for j in children(i):
    d=rows[j];v=d['attrs']
    if d['tag']!='DW_TAG_member':continue
    if 'data_member_location' not in v and not union:continue
    off=base+int(v.get('data_member_location','0'),0)
    if 'name' in v:yield v['name'].split(': ')[-1],off,path+[d['offset']],d
    elif ref(d) is not None:yield from fields(ref(d),off,path+[d['offset']],seen+(i,))
  def sizeof(index,seen=()):
   assert index not in seen,'cyclic type size'
   d=rows[index];attrs=d['attrs']
   if 'byte_size' in attrs:return int(attrs['byte_size'],0)
   if d['tag']=='DW_TAG_pointer_type':return 4
   if d['tag'] in ('DW_TAG_typedef','DW_TAG_const_type','DW_TAG_volatile_type'):return sizeof(ref(d),seen+(index,))
   if d['tag']=='DW_TAG_array_type':
    size=sizeof(ref(d),seen+(index,))
    for j in children(index):
     ar=rows[j]['attrs']
     if rows[j]['tag']=='DW_TAG_subrange_type':size*=int(ar['count'],0) if 'count' in ar else int(ar['upper_bound'],0)-int(ar.get('lower_bound','0'),0)+1
    return size
   raise ValueError('unsupported member type size '+d['tag'])
  widths={'Entry':{'package':64,'key':8,'frame':4,'valid':1,'model_header':32,'model_header_key':4},'Key':{'crc':4,'fnv':4},'Package':{n:(1 if n in ('streamed_','payload_released_','upload_complete_') else 4) for n in u['types'].get('Package',{}).get('members',{})},'Header':{n:(8 if n=='magic' else 4) for n in u['types'].get('Header',{}).get('members',{})},'Texture':{n:(64 if n=='material' else 4) for n in u['types'].get('Texture',{}).get('members',{})},'GlobalWork':{'Cam':248,'Frame_cnt':4,'room_id':2,'pl_life':2,'pl_life_max':2,'ashley_life':2,'ashley_life_max':2},'Camera':{'param':32,'mat':48,'v_mat':48,'ProjMat':64},'cCoord':{'pos':12,'ang':12}}
  for typename,record in u['types'].items():
   root=by[record['DIE_offset']]
   for name,off,path,d in fields(root,path=[record['DIE_offset']]):
    assert record['members'][name]==off
    width=sizeof(ref(d))
    if name in widths.get(typename,{}):assert width==widths[typename][name],(typename,name,width,widths[typename][name])
    report['member_paths'].append({'type_size_bytes':width,'observer_access_checked':name in widths.get(typename,{}),'CU':u['source'],'type':typename,'member':name,'byte_offset':off,'DIE_path':path,'decl_line':d['attrs'].get('decl_line'),'member_type_ref':d['attrs'].get('type')})
    k=ref(d);chain=[]
    while k is not None and rows[k]['tag'] in ('DW_TAG_typedef','DW_TAG_const_type','DW_TAG_volatile_type'):
     chain.append(rows[k]['offset']);k=ref(rows[k])
    if k is not None and rows[k]['tag']=='DW_TAG_pointer_type':
     width=int(rows[k]['attrs'].get('byte_size','4'),0);assert width==4
     report['pointer_paths'].append({'CU':u['source'],'type':typename,'member':name,'DIE':rows[k]['offset'],'bytes':width,'typedef_chain':chain})
  report['compilation_units'][group]={'name':u['source'],'CU_header':u['lines'][0].strip(),'types':u['types'],'pointer_bytes':4}
 nm=subprocess.check_output([a.nm,'-S','-n',str(a.elf)],text=True);symbols=[]
 for line in nm.splitlines():
  p=line.split()
  if len(p)==4:symbols.append({'address':int(p[0],16),'size':int(p[1],16),'kind':p[2],'name':p[3]})
 report['symbols']={}
 for name,expected_symbol in plan['read_only_observer']['symbols'].items():
  actual=select_symbol(symbols,expected_symbol['name'],expected_symbol['size']);assert actual==expected_symbol
  report['symbols'][name]=actual
 rows=units['native_ui']['dies'];by={d['offset']:i for i,d in enumerate(rows)}
 vars=[d for d in rows if d['tag']=='DW_TAG_variable' and 'specification' in d['attrs'] and re.search(r'\(DW_OP_addr: '+format(plan['read_only_observer']['symbols']['native_ui_entries']['address'],'x')+r'\)$',d['attrs'].get('location',''))]
 assert len(vars)==1,vars
 variable=vars[0];m=re.search(r'<0x([0-9a-f]+)>',variable['attrs']['specification']);declaration=rows[by[m[1]]];assert declaration['attrs']['name'].split(': ')[-1]=='entries'
 m=re.search(r'<0x([0-9a-f]+)>',declaration['attrs']['type']);array=rows[by[m[1]]];assert array['tag']=='DW_TAG_array_type'
 am=re.search(r'<0x([0-9a-f]+)>',array['attrs']['type']);entry=rows[by[am[1]]];assert entry['attrs']['name'].split(': ')[-1]=='Entry' and int(entry['attrs']['byte_size'],0)==224
 sub=[d for d in rows[by[array['offset']]+1:] if d['depth']==array['depth']+1 and d['tag']=='DW_TAG_subrange_type']
 assert int(sub[0]['attrs']['upper_bound'],0)==447
 report['duplicate_entries_binding']={'selected':plan['read_only_observer']['symbols']['native_ui_entries'],'actual_variable_DIE':variable,'declaration_DIE':declaration,'array_DIE':array,'entry_type_DIE':entry,'upper_bound':447,'slots':448,'other_same_name_symbols':[r for r in symbols if r['name']=='__ZN12_GLOBAL__N_1L7entriesE' and r['address']!=plan['read_only_observer']['symbols']['native_ui_entries']['address']],'rule':'Exact native_ui CU Entry[448], 224-byte type and location; no name-only map'}
 G=units['scene']['types']['GlobalWork']['members'];assert [G[n] for n in ['room_id','pl_life','pl_life_max','ashley_life','ashley_life_max']]==[20382,20388,20390,20392,20394]
 report['contiguous_life_read']={'field_offsets':[G[n] for n in ['pl_life','pl_life_max','ashley_life','ashley_life_max']],'read_bytes':8,'format':'4 little-endian int16; raw values, no death classification'}
 with a.out.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
 print(json.dumps({'result':'PASS','member_paths':len(report['member_paths']),'pointer_paths':len(report['pointer_paths']),'symbols':len(report['symbols']),'out':str(a.out)}))
if __name__=='__main__':main()
