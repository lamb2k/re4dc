"""Stream actual ELF DWARF into bounded selected type/member records."""
import pathlib,subprocess,re,json,sys,hashlib
elf=pathlib.Path(sys.argv[1]);dest=pathlib.Path(sys.argv[2]);wanted={'cUnit','cCoord','cModel','cPlayer','cEm','cEmMgr','cObjMgr','cManager<cEm>','cManager<cObj>','Snapshot','Source','Re4dcNativeFrameStats','pvr_state_t','Package','Entry','GlobalWork','Camera'}
roots={};kept={};known={};stack={};cur=None
allowed={'DW_TAG_member','DW_TAG_inheritance','DW_TAG_structure_type','DW_TAG_class_type','DW_TAG_union_type','DW_TAG_array_type','DW_TAG_subrange_type','DW_TAG_enumerator'}
def name(d):
 a=d['attrs'];n=a.get('DW_AT_name','').split('): ',1)[-1]
 if n in wanted:return n
 m=re.search(r'<0x([0-9a-f]+)>',a.get('DW_AT_specification',''));return known.get(int(m[1],16),'') if m else ''
def finish():
 if cur is None:return
 n=name(cur);o=cur['offset']
 if n:
  known[o]=n
  if cur['tag'] in ['DW_TAG_class_type','DW_TAG_structure_type','DW_TAG_typedef']:
   cur['resolved_name']=n;roots[o]=cur;kept[o]=cur
 if cur['parent'] in kept and cur['tag'] in allowed:kept[o]=cur
p=subprocess.Popen(['/opt/toolchains/dc/sh-elf/bin/sh-elf-readelf','--debug-dump=info',str(elf)],stdout=subprocess.PIPE,text=True)
for line in p.stdout:
 m=re.match(r'\s*<(\d+)><([0-9a-f]+)>: Abbrev Number: (\d+)(?: \((DW_TAG_\w+)\))?',line)
 if m:
  finish();level=int(m[1]);off=int(m[2],16)
  cur={'offset':off,'tag':m[4],'parent':stack.get(level-1),'attrs':{}} if m[4] else None
  stack[level]=off
 else:
  m=re.match(r'\s*<[0-9a-f]+>\s+(DW_AT_\w+)\s*:\s*(.*)',line)
  if cur is not None and m:cur['attrs'][m[1]]=m[2]
finish();assert p.wait()==0
children={}
for d in kept.values():children.setdefault(d['parent'],[]).append(d)
unique={}
for o,d in roots.items():
 if 'DW_AT_byte_size' not in d['attrs']:continue
 n=d.get('resolved_name','');ch=children.get(o,[])
 sig=(n,d['attrs']['DW_AT_byte_size'],json.dumps([(x['tag'],x['attrs'].get('DW_AT_name'),x['attrs'].get('DW_AT_data_member_location')) for x in ch]))
 if sig not in unique:unique[sig]=o
select=set(unique.values());changed=True
while changed:
 changed=False
 for o,d in kept.items():
  if d['parent'] in select and o not in select:select.add(o);changed=True
result={'elf':str(elf),'elf_sha256':hashlib.sha256(elf.read_bytes()).hexdigest(),'roots':[hex(o) for o in unique.values()],'dies':{hex(o):kept[o] for o in sorted(select)}}
dest.write_text(json.dumps(result,indent=2)+'\n');print('compact roots',len(unique),'records',len(select),'bytes',dest.stat().st_size)
for o in unique.values():
 d=roots[o];n=d.get('resolved_name','')
 if n in {'cEmMgr','cObjMgr','cManager<cEm>','cManager<cObj>','cCoord','cModel','cPlayer','cEm'}:print(n,d['attrs'].get('DW_AT_byte_size'),[(x['attrs'].get('DW_AT_name','').split('): ',1)[-1],x['attrs'].get('DW_AT_data_member_location')) for x in children.get(o,[]) if x['tag'] in {'DW_TAG_member','DW_TAG_inheritance'}])