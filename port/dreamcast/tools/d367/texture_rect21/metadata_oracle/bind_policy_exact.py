from pathlib import Path
import argparse,hashlib,json,re,subprocess,sys
MODULE=Path('/root/probe/codex-texture21-benchmark/port/dreamcast/tools/d367/texture21_benchmark')
sys.path.insert(0,str(MODULE));from audit_observer_elf import dies
cli=argparse.ArgumentParser(description='Read-only exact-ELF policy supplement; no process access')
cli.add_argument('--identity',required=True);cli.add_argument('--output',required=True);args=cli.parse_args()
identity=json.loads(Path(args.identity).read_text())
assert identity['role'] in ('STATIC_HOLD','FRESH_REBIND_UNACCEPTED')
assert re.fullmatch('[0-9a-f]{40}',identity['source'])
for key in ('ELF_sha256','programme_sha256','compile_freeze_receipt_sha256'):
 assert re.fullmatch('[0-9a-f]{64}',identity[key]),key
ELF=Path(identity['ELF_path']);EXPECTED=identity['ELF_sha256']
assert hashlib.sha256(ELF.read_bytes()).hexdigest()==EXPECTED
assert hashlib.sha256(Path(identity['programme_path']).read_bytes()).hexdigest()==identity['programme_sha256']
if identity['role']=='FRESH_REBIND_UNACCEPTED':
 assert EXPECTED!='f42dbb7261ff93c23dbc8f0dfb810a77cd64ad460472239e58a7cb6fa1404e00','f42 is held, not a fresh repaired ABI'
 assert re.fullmatch('[0-9a-f]{64}',identity['canonical_certificate_manifest_sha256'])
 assert hashlib.sha256(Path(identity['canonical_certificate_manifest_path']).read_bytes()).hexdigest()==identity['canonical_certificate_manifest_sha256']
 assert set(identity['candidate_worlds'])=={'r100','r101','r103'}
 for value in identity['candidate_worlds'].values():
  assert re.fullmatch('[0-9a-f]{64}',value['sha256']) and 32<value['bytes']<32768
  world=Path(value['path']).read_bytes();assert len(world)==value['bytes'] and hashlib.sha256(world).hexdigest()==value['sha256']
wanted={'platform/native_static.cpp':{
 'ps2w':['room','storage','bytes','parts','placements','nplacements','sg_block','sg','sg_groups','masked','pass_mask','package.h_.crc','package.h_.bytes','package.h_.part_count','package.h_.mesh_count','package.h_.meshlet_count'],
 'enemyVisSidecarCrc':[],'re4dc_trans_policy':[],'sourceWorldSidecarCrc':[],'ps2_movie_files':['mesh','side','mesh_crc','mesh_fnv','side_crc','side_fnv'],
 'ps2_movie':['base','capacity','generation','phase'],
 'dyn::block':[],'dyn::ids':[],'dyn::nids':[],'dyn::slots':[],'dyn::nslots':[],'dyn::slot_of':[],
 'trans::block':[],'trans::cls':[],'trans::room':[],'trans::nparts':[],
 'pc::st':['ok','active','cell','frame'],'pc::data':['block','lent','loads','fails','lends'],
 },
 'platform/room_occl.c':{'o':['ok','room','nocc','crc','occ','cells','lists','pool'],'intact':[],'intact_frame':[],'c_notintact':[],'c_tests':[]}}
units={};block=[]
def take(lines):
 name=next((l.split(': ')[-1].strip()for l in lines[:30]if'DW_AT_name 'in l),'')
 for suffix in wanted:
  if name.endswith(suffix):
   assert suffix not in units;assert any(re.search(r'Pointer Size:\s+4$',x)for x in lines[:10])
   units[suffix]=dict(name=name,rows=dies(lines),header=lines[0].strip())
proc=subprocess.Popen(['/opt/toolchains/dc/sh-elf/bin/sh-elf-readelf','--debug-dump=info',str(ELF)],stdout=subprocess.PIPE,text=True)
for line in proc.stdout:
 if'Compilation Unit @ offset'in line:
  if block:take(block)
  block=[]
 block.append(line)
take(block);assert proc.wait()==0 and set(units)==set(wanted)
nm=subprocess.check_output(['/opt/toolchains/dc/sh-elf/bin/sh-elf-nm','-n','-S',str(ELF)],text=True)
symbols=[]
for line in nm.splitlines():
 p=line.split()
 if len(p)==4:symbols.append(dict(address=int(p[0],16),bytes=int(p[1],16),kind=p[2],name=p[3]))
report=dict(ELF_sha256=EXPECTED,programme_sha256=identity['programme_sha256'],source=identity['source'],identity=identity,pointer_bytes=4,endianness='little',address_space='SH4 P1 virtual; external RAM mapping belongs to caller',status='OFFLINE_TYPED_POLICY_BINDING_NO_PROCESS_ATTACH',variables={},fields=[],CU={})
for suffix,u in units.items():
 rows=u['rows'];by={d['offset']:i for i,d in enumerate(rows)};parents={};stack=[]
 for i,d in enumerate(rows):
  while stack and rows[stack[-1]]['depth']>=d['depth']:stack.pop()
  parents[i]=stack[-1]if stack else None;stack.append(i)
 def ref(text):
  m=re.search(r'<0x([0-9a-f]+)>',text or'');assert m and m[1]in by,text;return by[m[1]]
 def attrs(i,seen=()):
  assert i not in seen
  out={};origin=i
  for key in('specification','abstract_origin'):
   if key in rows[i]['attrs']:
    out,origin=attrs(ref(rows[i]['attrs'][key]),seen+(i,))
  out=out|rows[i]['attrs'];return out,origin
 def children(i):
  depth=rows[i]['depth']
  for j in range(i+1,len(rows)):
   if rows[j]['depth']<=depth:break
   if rows[j]['depth']==depth+1:yield j
 def size(i,seen=()):
  assert i not in seen
  d=rows[i];a=d['attrs']
  if'byte_size'in a:return int(a['byte_size'],0)
  if d['tag']=='DW_TAG_pointer_type':return 4
  if d['tag']=='DW_TAG_array_type':
   n=1
   for j in children(i):
    if rows[j]['tag']=='DW_TAG_subrange_type':
     a2=rows[j]['attrs'];n*=int(a2['count'],0)if'count'in a2 else int(a2['upper_bound'],0)+1
   return n*size(ref(a['type']),seen+(i,))
  return size(ref(a['type']),seen+(i,))
 def unwrap(i):
  chain=[]
  while rows[i]['tag']in('DW_TAG_typedef','DW_TAG_const_type','DW_TAG_volatile_type'):
   chain.append(rows[i]['offset']);i=ref(rows[i]['attrs']['type'])
  return i,chain
 def qualified(i,a,origin):
  name=a.get('name','').split(': ')[-1];parts=[];p=parents[origin]
  while p is not None:
   if rows[p]['tag']=='DW_TAG_namespace':
    n=rows[p]['attrs'].get('name','').split(': ')[-1]
    if n:parts.insert(0,n)
   p=parents[p]
  return '::'.join(parts+[name])
 def member(i,name):
  i,_=unwrap(i);tag=rows[i]['tag'];assert tag in('DW_TAG_class_type','DW_TAG_structure_type','DW_TAG_union_type')
  hits=[]
  for j in children(i):
   d=rows[j];a=d['attrs']
   if d['tag']=='DW_TAG_member'and a.get('name','').split(': ')[-1]==name:
    assert'data_member_location'in a or tag=='DW_TAG_union_type'
    hits.append((j,int(a.get('data_member_location','0'),0)))
  assert len(hits)==1,(name,len(hits),rows[i]);return hits[0]
 def path(i,names):
  off=0;diepath=[rows[i]['offset']];pointer_paths=[]
  for name in names:
   i,_=unwrap(i);assert rows[i]['tag']!='DW_TAG_pointer_type','deref path must be explicit'
   j,at=member(i,name);off+=at;diepath.append(rows[j]['offset']);i=ref(rows[j]['attrs']['type'])
  leaf,chain=unwrap(i);width=size(i)
  if rows[leaf]['tag']=='DW_TAG_pointer_type':
   assert width==4;pointer_paths.append(rows[leaf]['offset'])
  return dict(offset=off,bytes=width,DIE_path=diepath,type_DIE=rows[i]['offset'],leaf_tag=rows[leaf]['tag'],pointer_DIEs=pointer_paths)
 for name,fields in wanted[suffix].items():
  hits=[]
  for i,d in enumerate(rows):
   if d['tag']!='DW_TAG_variable':continue
   a,origin=attrs(i);loc=re.search(r'\(DW_OP_addr: ([0-9a-f]+)\)$',a.get('location',''))
   if loc and qualified(i,a,origin)==name:hits.append((i,a,origin,int(loc[1],16)))
  assert len(hits)==1,(suffix,name,len(hits))
  i,a,origin,address=hits[0];assert 'declaration' not in rows[i]['attrs'] and 'location' in rows[i]['attrs']
  typ=ref(a['type']);width=size(typ)
  matches=[s for s in symbols if s['address']==address and s['bytes']==width]
  assert matches,(name,address,width)
  record=dict(CU=u['name'],CU_header=u['header'],definition_DIE=rows[i]['offset'],declaration_DIE=rows[origin]['offset'],actual_definition_attrs=rows[i]['attrs'],address=address,bytes=width,qualified_name=name,type_DIE=rows[typ]['offset'],matching_nm=matches,
              same_name_other_locations=[s for s in symbols if s['name']in {x['name']for x in matches}and s['address']!=address])
  key=suffix+':'+name;report['variables'][key]=record
  for field in fields:
   p=path(typ,field.split('.'));p.update(variable=key,path=name+'.'+field,address=address+p['offset'],CU=u['name']);report['fields'].append(p)
 u.pop('rows');report['CU'][suffix]=u
# Named packed metadata/slot layouts from the SAME exact native_static CU.
 if suffix=='platform/native_static.cpp':
  report['packed_types']={}
  for typename in('Ps2Head','Ps2Part','dyn::Head','dyn::Slot','trans::Head','Ps2Placement','pc::Frustum'):
   found=[]
   for i,d in enumerate(rows):
    if d['tag'] in('DW_TAG_structure_type','DW_TAG_class_type')and 'byte_size'in d['attrs'] and qualified(i,d['attrs'],i)==typename:found.append(i)
   assert len(found)==1,(typename,found)
   i=found[0];fields={}
   for j in children(i):
    d=rows[j]
    if d['tag']=='DW_TAG_member' and 'name'in d['attrs']:
     name=d['attrs']['name'].split(': ')[-1];fields[name]=path(i,[name])
   report['packed_types'][typename]=dict(bytes=size(i),DIE=rows[i]['offset'],members=fields)
# The two caller-owned byte arrays use actual declared packed native structs.
# Bind their offsets/sizes from the native_static CU too, without new CU scans.
report['parser_sources']={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in(MODULE/'audit_observer_elf.py',MODULE/'dwarf_layout.py')}
assert len(report['variables'])==23 and len(report['fields'])==43
assert {k:v['bytes'] for k,v in report['packed_types'].items()}=={'Ps2Head':32,'Ps2Part':16,'dyn::Head':16,'dyn::Slot':72,'trans::Head':24,'Ps2Placement':52,'pc::Frustum':108}
with Path(args.output).open('x') as f:f.write(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(variables=len(report['variables']),fields=len(report['fields']),bytes=Path(args.output).stat().st_size)))
