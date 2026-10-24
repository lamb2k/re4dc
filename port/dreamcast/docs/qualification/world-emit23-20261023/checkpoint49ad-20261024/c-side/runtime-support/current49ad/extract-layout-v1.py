import json,pathlib,re,subprocess,sys,hashlib
elf=pathlib.Path(sys.argv[1]);dst=pathlib.Path(sys.argv[2]);dst.mkdir(parents=True,exist_ok=True)
nm=subprocess.check_output(['/opt/toolchains/dc/sh-elf/bin/sh-elf-nm','-C','-S','--defined-only',str(elf)],text=True)
terms=['completed_frame','completed_render_profile','render_source_begin','pG','pPL','pvr_state','viewport','projection','stream_','framebuffer','movie_upload_serial','movie_shown_serial','model_presented','upload','gxf','pending']
selected=[]
for line in nm.splitlines():
 parts=line.split(maxsplit=3)
 if len(parts)==4 and any(x in parts[3] for x in terms) and parts[2].lower() in ['b','d','r','s']:
  selected.append(line)
(dst/'nm-selected.txt').write_text('\n'.join(selected)+'\n')
print('\n'.join(selected[:100]))
# Stream readelf DWARF; store only structural entries and attributes, no binary execution.
p=subprocess.Popen(['/opt/toolchains/dc/sh-elf/bin/sh-elf-readelf','--debug-dump=info',str(elf)],stdout=subprocess.PIPE,text=True)
dies={};stack={};current=None
for line in p.stdout:
 m=re.match(r'\s*<(\d+)><([0-9a-f]+)>: Abbrev Number: (\d+)(?: \((DW_TAG_\w+)\))?',line)
 if m:
  level=int(m[1]);offset=int(m[2],16)
  if m[4]:
   current={'offset':offset,'tag':m[4],'parent':stack.get(level-1),'attrs':{}};dies[offset]=current;stack[level]=offset
  else:current=None
 elif current:
  m=re.match(r'\s*<[0-9a-f]+>\s+(DW_AT_\w+)\s*:\s*(.*)',line)
  if m:current['attrs'][m[1]]=m[2]
assert p.wait()==0
names=['Snapshot','Source','Re4dcNativeFrameStats','Re4dcModelWorkStats','pvr_state','pvr_state_t','cModel','cPlayer','GlobalWork','Camera','Vec3f','Entry','Package','SourceFrame','GXFState']
def name(d):
 v=d['attrs'].get('DW_AT_name','');return v.split('): ',1)[-1]
chosen={o:d for o,d in dies.items() if name(d) in names and d['tag'] in ['DW_TAG_structure_type','DW_TAG_class_type','DW_TAG_typedef']}
# Retain selected type subtrees and references, enough to decode actual members and arrays.
keep=set(chosen);changed=True
while changed:
 changed=False
 for o,d in dies.items():
  if o not in keep and d['parent'] in keep:keep.add(o);changed=True
 for o in list(keep):
  for val in dies[o]['attrs'].values():
   for ref in re.findall(r'<0x([0-9a-f]+)>',val):
    n=int(ref,16)
    if n in dies and n not in keep:keep.add(n);changed=True
result={'elf':str(elf),'elf_sha256':hashlib.sha256(elf.read_bytes()).hexdigest(),'type_roots':list(chosen),'dies':{hex(o):dies[o] for o in sorted(keep)}}
(dst/'dwarf-selected.json').write_text(json.dumps(result,indent=2)+'\n')
print('DWARF entries',len(dies),'retained',len(keep),'roots',[(hex(o),name(d),d['attrs'].get('DW_AT_byte_size')) for o,d in chosen.items()])