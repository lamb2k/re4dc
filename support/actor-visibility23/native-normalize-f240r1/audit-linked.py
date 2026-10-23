"""Main's exact linked actor-image inventory; manual/runtime gates stay separate."""
from pathlib import Path
import argparse, hashlib, json, re, struct, subprocess
p=argparse.ArgumentParser();p.add_argument('--arm',choices=('on',),required=True);p.add_argument('--receipt-sha256',required=True);a=p.parse_args()
root=Path('/root/probe/lanes/actor-visibility23-eligibility-witness-integration/on2')
out=Path('/mnt/c/Game Dev/Emulators/codex-lanes/actor-visibility23')/'main-audit-f240-on2'
prefix='/opt/toolchains/dc/sh-elf/bin/sh-elf-'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def sections(p):
    b=Path(p).read_bytes();assert b[:7]==b'\x7fELF\x01\x01\x01'
    h=struct.unpack_from('<16sHHIIIIIHHHHHH',b);assert h[1:3]==(2,42)
    rows=[struct.unpack_from('<IIIIIIIIII',b,h[6]+i*h[11]) for i in range(h[12])]
    s=rows[h[13]];names=b[s[4]:s[4]+s[5]]
    return [(names[r[0]:].split(b'\0',1)[0].decode(),r,b[r[4]:r[4]+r[5]]) for r in rows]
assert not out.exists();assert sha(root/'LINK-RECEIPT.json')==a.receipt_sha256
r=json.loads((root/'LINK-RECEIPT.json').read_text());assert r['source_head']=='f2405bb06ebaff6e2a7681479d5308ec5d3b988a'
for k in ('main','raw','scrambled','resolved','objects_manifest','source_manifest','modules_roster','private_inputs_receipt'):
    assert sha(r[k]['path'])==r[k]['sha256'],k
for v in r['kos']+r['overlays']:assert sha(v['path'])==v['sha256'],v['path']
roster=json.loads(Path(r['modules_roster']['path']).read_text());assert len(roster)==14
assert {v['overlay'] for v in roster}=={Path(v['path']).name for v in r['overlays']}
for v in roster:
    elf=root/'modules'/v['elf'];raw=root/v['overlay']
    assert sha(elf)==v['elf_sha256'] and sha(raw)==v['overlay_sha256']
    chosen=[(s,d) for n,s,d in sections(elf) if n==v['section']];assert len(chosen)==1
    s,d=chosen[0];assert s[3]==v['vma'] and len(d)==v['bytes'] and hashlib.sha256(d).hexdigest()==v['image_sha256']
    assert raw.read_bytes()[64:64+len(d)]==d;v['verified_image_offset']=64
main=Path(r['main']['path']);ss=sections(main)
image_sections=[(n,s,d) for n,s,d in ss if s[2]&2 and s[1]!=8 and s[5] and n!='.stack']
lo=min(s[3] for n,s,d in image_sections);hi=max(s[3]+s[5] for n,s,d in image_sections)
assert lo==0x8c010000 and hi-lo<16*1024**2
image=bytearray(hi-lo)
for n,s,d in image_sections:image[s[3]-lo:s[3]-lo+len(d)]=d
assert image==Path(r['raw']['path']).read_bytes()
out.mkdir()
symbols=subprocess.check_output([prefix+'nm','-n','-S','-C',str(main)],text=True)
dis=subprocess.check_output([prefix+'objdump','-d','-C',str(main)],text=True)
terms=('actor_visibility','actorvis','shz_bounds','re4dc_warp_late','room_occl','skin_mesh_workspace','witness','section_wall23','cache_write_ccr')
selected=[f for f in re.split(r'(?=^[0-9a-f]+ <)',dis,flags=re.M) if any(t in f.split('\n',1)[0].lower() for t in terms)]
(out/'selected-functions.txt').write_text('\n'.join(selected))
(out/'selected-symbols.txt').write_text('\n'.join(s for s in symbols.splitlines() if any(t in s.lower() for t in terms))+'\n')
for name in ('re4dc_actor_visibility23_bind','re4dc_actor_visibility23_wall','shz_bounds_inverse','re4dc_actor_visibility23_frame'):
    assert name in symbols
assert 'world_scratch23' not in symbols
record=dict(status='LINKED_BYTES_AND_MODULES_VERIFIED_MANUAL_RUNTIME_GATES_OPEN',source=r['source_head'],receipt_sha256=a.receipt_sha256,
    elf=r['main'],raw=r['raw'],raw_reconstructed_from_initialized_sections=True,modules=roster,
    disassembly_sha256=hashlib.sha256(dis.encode()).hexdigest(),selected_functions_sha256=sha(out/'selected-functions.txt'),
    selected_symbols_sha256=sha(out/'selected-symbols.txt'),kos=r['kos'],private_inputs=r['private_inputs_receipt'],
    sections=[dict(name=n,address=hex(s[3]),bytes=s[5],type=s[1],flags=s[2]) for n,s,d in ss if s[2]&2])
(out/'LINKED-BYTES.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(dict(output=str(out),receipt_sha256=sha(out/'LINKED-BYTES.json'),status=record['status']),indent=2))
