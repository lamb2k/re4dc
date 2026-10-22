#!/usr/bin/env python3
"""Cross-check packet descriptors/aliases/certificates against sealed actual inputs."""
from pathlib import Path
import hashlib,json,re,struct,sys,zlib
T=Path(__file__).resolve().parent;sys.path.insert(0,str(T));import world_bindings as world
O=Path(sys.argv[1]);p=json.loads((O/'ADDITIONS142.json').read_text());w=json.loads((O/'WORLD792-LINEAGE.json').read_text());byroom={x['path'].split('/')[2]:world.inspect_sidecar(Path(x['absolute_path']).read_bytes())for x in w['worlds']};counts=aliases=0
for x in p['selected']:
 b=Path(x['absolute_path']).read_bytes();assert hashlib.sha256(b).hexdigest()==x['sha256']==x['candidate_sha256'];assert b[48:144].hex()==x['descriptor_hex']and len(b)==x['bytes']==x['package_bytes'];assert zlib.crc32(b[48:])&0xffffffff==x['body_crc32']==x['candidate_crc32'];d=struct.unpack('<64s8I',bytes.fromhex(x['descriptor_hex']));assert d[1:3]==tuple(x['physical'])and d[3]==x['format']and d[5]==x['payload_bytes']and d[6]==x['flags']and d[7]==x['payload_type'];counts+=1
 for a in x['aliases']:
  row=byroom[a['room']][a['part']];assert row['key']==x['scoped_key']and[row['width'],row['height']]==x['logical'];assert row['render_pass']==a['render_pass']and row['cull']==a['cull']and row['flags']==a['flags']and row['texture']==a['texture'];aliases+=1
cert=Path(w['certificates']['path']);entries=[]
for line in cert.read_text().splitlines():
 if line.startswith('{'):entries.append(tuple(int(n,16)if n.startswith('0x')else int(n)for n in re.findall(r'(0x[0-9a-f]+|\d+)U',line)))
assert len(entries)==len(w['worlds'])==29
for row,entry in zip(w['worlds'],entries):
 expected=(int(row['path'].split('/')[2][1:],16),row['bytes'],row['placements'],row['parts'],row['meshes'],row['physical_body_crc'],row['physical_file_fnv'],row['mesh_crc'],row['mesh_bytes'],row['canonical_source_crc']);assert entry==expected
layout=p['index_layout'];assert counts==142 and aliases==508 and layout['final_members']==7151+142==7293 and layout['required_index_sectors']==57 and layout['index_capacity']==7296 and layout['spare_entries']==3 and layout['new_data_start']==118784 and layout['new_data_start']-layout['parent_data_start']==2048 and layout['final_virtual_pack_sha256']is None
report=dict(status='PASS_PACKET142_DESCRIPTOR_HASH_BODYCRC_508_ALIAS_BINDINGS_AND29_CERTIFICATES',records=counts,actual_world_alias_bindings=aliases,actual_certificate_tuples=29,virtual_parent_only=True,requires57indexsectors=True,no_actual_pack_or_assets_written=True)
(O/'READBACK-QUALIFICATION.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))