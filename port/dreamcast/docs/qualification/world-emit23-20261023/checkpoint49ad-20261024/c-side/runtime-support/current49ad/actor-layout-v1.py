import json,pathlib,re,subprocess
j=json.loads(pathlib.Path('/dev/shm/world-emit49ad-layout/dwarf-selected.json').read_text());d={int(k,16):v for k,v in j['dies'].items()};child={}
for o,x in d.items():child.setdefault(x['parent'],[]).append(x)
def name(x,depth=0):
 if depth>4:return ''
 a=x['attrs'];v=a.get('DW_AT_name','').split('): ',1)[-1]
 if v:return v
 ref=a.get('DW_AT_specification','');m=re.search(r'<0x([0-9a-f]+)>',ref)
 return name(d[int(m[1],16)],depth+1) if m and int(m[1],16) in d else ''
rows=[]
for o,x in d.items():
 n=name(x)
 if n in ['cModel','cPlayer','cUnit','cEmMgr','cObjMgr','cEm','cManager<cEm>','cManager<cObj>'] and x['attrs'].get('DW_AT_byte_size'):
  members=[{'tag':y['tag'],'name':name(y),'attrs':y['attrs']} for y in child.get(o,[]) if y['tag'] in ['DW_TAG_member','DW_TAG_inheritance']]
  row={'name':n,'die':hex(o),'attrs':x['attrs'],'members':members};rows.append(row)
  print(n,hex(o),x['attrs']['DW_AT_byte_size'],[(m['name'],m['attrs'].get('DW_AT_data_member_location')) for m in members][:20])
p=pathlib.Path('/mnt/c/Game Dev/Emulators/codex-lanes/world-emit23/runtime-support/current49ad/actor-layout-research.json');p.write_text(json.dumps(rows,indent=2)+'\n')
nm=subprocess.check_output(['/opt/toolchains/dc/sh-elf/bin/sh-elf-nm','-C','-S','--defined-only',j['elf']],text=True)
rows=[x for x in nm.splitlines() if re.search(r' [bBdD] ',x) and any(t in x for t in ['EmMgr','ObjMgr','q_n','watch','flip_n','pace_present','gxf_viewport','gxf_projection'])]
p.with_name('nm-actors-phase.txt').write_text('\n'.join(rows)+'\n');print('\n'.join(rows))