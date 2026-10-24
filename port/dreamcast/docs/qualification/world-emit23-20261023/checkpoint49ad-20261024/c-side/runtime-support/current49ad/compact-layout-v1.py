import json,pathlib,re,subprocess
src=pathlib.Path('/dev/shm/world-emit49ad-layout/dwarf-selected.json');j=json.loads(src.read_text());dies={int(k,16):v for k,v in j['dies'].items()};children={}
for off,d in dies.items():children.setdefault(d['parent'],[]).append(d)
def name(d):return d['attrs'].get('DW_AT_name','').split('): ',1)[-1]
def num(s):
 m=re.search(r'<0x([0-9a-f]+)>',s);return int(m[1],16) if m else int(s,0)
def info(d):
 a=d['attrs'];members=[]
 for x in children.get(d['offset'],[]):
  if x['tag']=='DW_TAG_member':members.append({'name':name(x),'offset':x['attrs'].get('DW_AT_data_member_location'),'type_ref':x['attrs'].get('DW_AT_type'),'byte_size':x['attrs'].get('DW_AT_byte_size')})
 return {'die':hex(d['offset']),'name':name(d),'size':a.get('DW_AT_byte_size'),'attrs':a,'members':members}
out={'elf':j['elf'],'elf_sha256':j['elf_sha256'],'types':[]}
checks=[('Snapshot','428'),('Source','112'),('Re4dcNativeFrameStats','192'),('GlobalWork','34432'),('Camera','248'),('Entry','224'),('Package','64')]
for nm,size in checks:
 selected=[d for d in dies.values() if name(d)==nm and d['attrs'].get('DW_AT_byte_size')==size and d['tag'] in ['DW_TAG_structure_type','DW_TAG_class_type']]
 assert selected,(nm,size)
 d=selected[-1] if nm in ['Source','GlobalWork','Camera'] else selected[0];o=info(d);out['types'].append(o)
 print(nm,size,[(x['name'],x['offset']) for x in o['members']])
for d in dies.values():
 if name(d)=='pvr_state_t':
  ref=num(d['attrs']['DW_AT_type']);o=info(dies[ref]);out['types'].append(o);print('pvr_state_t',o['size'],[(x['name'],x['offset']) for x in o['members']]);break
p=pathlib.Path('/mnt/c/Game Dev/Emulators/codex-lanes/world-emit23/runtime-support/current49ad/layout-research.json');p.write_text(json.dumps(out,indent=2)+'\n')
nm=subprocess.check_output(['/opt/toolchains/dc/sh-elf/bin/sh-elf-nm','-C','-S','--defined-only',j['elf']],text=True)
rows=[l for l in nm.splitlines() if re.search(r' [bBdD] ',l) and any(t in l for t in ['pvr_','(anonymous namespace)::entries','(anonymous namespace)::loads','(anonymous namespace)::frame','(anonymous namespace)::present','re4dc_gxf','re4dc_gx_projection'])]
p.with_name('nm-present-upload.txt').write_text('\n'.join(rows)+'\n');print('\n'.join(rows))