#!/usr/bin/env python3
"""Bind a read-only WORLD36 snapshot oracle to fresh actual69f DWARF."""
from pathlib import Path
import hashlib,json,re,subprocess,sys,zlib
PEER=Path('/root/probe/codex-texture21-benchmark/port/dreamcast/tools/d367/texture21_benchmark');sys.path.insert(0,str(PEER))
from dwarf_layout import parse
from audit_observer_elf import dies
ELF_SHA='69f2e7db588f515f4e6a67455d627a74fc17132d5ca20a591db4e0f15deedcae'
ELF=Path('/root/probe/texture-rect21-canonical36-link-20261021-01/out/re4dc-game.elf')
D=Path('/root/re4data/private/texture-world36-canonical-crc-20261021')
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 out=Path(sys.argv[1]);assert not out.exists();assert sha(ELF.read_bytes())==ELF_SHA
 proc=subprocess.Popen(['/opt/toolchains/dc/sh-elf/bin/sh-elf-readelf','--debug-dump=info',str(ELF)],stdout=subprocess.PIPE,text=True);block=[];chosen=[]
 def take(block):
  name=next((s.split(': ')[-1].strip() for s in block[:30] if 'DW_AT_name ' in s),'')
  if name.endswith('platform/native_ui.cpp'):chosen.append((name,block[:]))
 for line in proc.stdout:
  if 'Compilation Unit @ offset' in line:
   if block:take(block)
   block=[]
  block.append(line)
 take(block);assert proc.wait()==0 and len(chosen)==1;cu,lines=chosen[0];types=parse(lines,['Entry','Key','Package','Header','Texture','Ps2HdrSlot']);rows=dies(lines);by={d['offset']:d for d in rows}
 def resolve(d,seen=()):
  assert d['offset'] not in seen;a={}
  for name in ['specification','abstract_origin']:
   m=re.search(r'<0x([0-9a-f]+)>',d['attrs'].get(name,''))
   if m:a.update(resolve(by[m[1]],seen+(d['offset'],)))
  a.update(d['attrs']);return a
 def width(ref):
  d=by[re.search(r'<0x([0-9a-f]+)>',ref)[1]];a=d['attrs']
  if 'byte_size' in a:return int(a['byte_size'],0)
  if d['tag']=='DW_TAG_pointer_type':return 4
  if d['tag']=='DW_TAG_array_type':
   n=1;i=rows.index(d)
   for child in rows[i+1:]:
    if child['depth']<=d['depth']:break
    if child['depth']==d['depth']+1 and child['tag']=='DW_TAG_subrange_type':n*=int(child['attrs']['upper_bound'],0)+1
   return n*width(a['type'])
  return width(a['type'])
 member_widths={}
 for typename in ['Entry','Key','Package','Header','Texture','Ps2HdrSlot']:
  root=by[types[typename]['DIE_offset']];members={}
  for d in rows[rows.index(root)+1:]:
   if d['depth']<=root['depth']:break
   if d['tag']=='DW_TAG_member' and d['depth']==root['depth']+1 and 'data_member_location' in d['attrs']:
    a=d['attrs'];members[a['name'].split(': ')[-1]]=dict(bytes=width(a['type']),DIE=d['offset'],type_ref=a['type'])
  member_widths[typename]=members
 assert member_widths['Entry']['valid']['bytes']==1 and member_widths['Package']['upload_complete_']['bytes']==1
 variables={}
 wanted=['entries','frame','direct_open','model_handle','model_used','model_pending','model_packets','stream_scene','stream_aborted','frame_ready','source_draws_finished','direct_parts','direct_slots']
 for name in wanted:
  hits=[]
  for d in rows:
   if d['tag']!='DW_TAG_variable':continue
   a=resolve(d);loc=re.search(r'\(DW_OP_addr: ([0-9a-f]+)\)$',a.get('location',''))
   if a.get('name','').split(': ')[-1]==name and loc:hits.append(dict(CU=cu,DIE=d['offset'],address=int(loc[1],16),bytes=width(a['type']),type_ref=a['type']))
  assert len(hits)==1,(name,len(hits));variables[name]=hits[0]
 assert variables['entries']['bytes']==448*types['Entry']['size'] and types['Entry']['size']==224
 expected=[];receipt=json.loads((D/'receipt.json').read_text())
 for row in receipt['selected']:
  b=(D/'textures'/(row['scoped_key']+'.re4tex')).read_bytes();assert sha(b)==row['candidate_sha256'];assert zlib.crc32(b[48:])==int.from_bytes(b[36:40],'little');bindings=[dict(room=w['path'],**part) for w in receipt['worlds'] for part in w['changed_parts'] if part['scoped_key']==row['scoped_key']]
  expected.append(dict(key=row['scoped_key'],original_key=row['original_key'],package_sha256=sha(b),descriptor_sha256=sha(b[48:144]),payload_sha256=sha(b[144:]),body_crc32=row['candidate_crc32'],logical=row['logical'],physical=row['physical'],header_hex=b[:48].hex(),texture_hex=b[48:144].hex(),payload_bytes=row['payload_bytes'],bindings=bindings))
 source=Path('/root/probe/codex-texture-rect21/port/dreamcast/game/platform/native_ui.cpp');kos=Path('/root/work/kos-re4dc-d367/kernel/arch/dreamcast/hardware/pvr/pvr_prim.c');kh=Path('/root/work/kos-re4dc-d367/kernel/arch/dreamcast/include/dc/pvr.h')
 result={'schema':1,'ELF_sha256':ELF_SHA,'programme_sha256':'733afabf6567a9f086eacb48b70559aef764cf52a5b534f44602da3a8bc68a9e','source':'0425534d848973c1dae3ab960d0006ac9afcf363','pack_sha256':'89ef27a767fcee529c3ac6ca07fef5a8f9a3e2515f38eda63b61c8929fb0be62','CU':cu,'pointer_bytes':4,'types':types,'member_widths':member_widths,'variables':variables,'selected':expected,'sources':{str(x):sha(x.read_bytes()) for x in [source,kos,kh,PEER/'dwarf_layout.py',PEER/'audit_observer_elf.py']},'scope':'Fresh actual69f DWARF/CU/type/variable binding, source-only; not runtime capture or new general observer.','limits':['No actual submitted vertices/TA accepted primitive/selectedLOD record exists in this oracle.','Direct packet staging header observation must never become draw proof.']}
 out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'types':{k:v['size'] for k,v in types.items()},'variables':len(variables),'keys':len(expected),'bytes':out.stat().st_size}))
if __name__=='__main__':main()
