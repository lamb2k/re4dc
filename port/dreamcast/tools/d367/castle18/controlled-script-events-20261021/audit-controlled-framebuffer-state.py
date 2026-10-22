from pathlib import Path
import struct,hashlib,json,re
L=Path(__file__).parent;D=Path(r'C:\Flycast-Evidence\re4-dreamcast\castle18-20261018\Test21\recovered-j-content-20261021');R=D.parent;h={};exec((L/'audit-authoritative-life-extended-history-20261019.py').read_text().split('targets=[')[0],h);va,code=h['load_segments'](R/'builds/c21jmW/re4dc-game.elf');records=[]
for n in [5,6]:
 cap=D/f'route-walk-controlled-event{n:03d}';p=cap/'data/disc.state';raw=h['decode'](p);rb=raw.find(code[0x4000:0x4100])-(va+0x4000-0x8c000000)
 for off in [0x100000,0x120000,0x140000]:assert raw[rb+va+off-0x8c000000:rb+va+off+256-0x8c000000]==code[off:off+256]
 u32=lambda a:struct.unpack_from('<I',raw,rb+a-0x8c000000)[0];st=0x8c483e00;native=[u32(st+312),u32(st+320)];ptrs=[((0xd2800000+(x&0x7fffff))*2)&0xffffffff for x in native];logged=re.findall(r'fb=[0-9a-f]+,[0-9a-f]+',(cap/'run-output.txt').read_text(errors='replace'));records.append(dict(run=n,state_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),pvr_state=hex(st),framebuffers_native=[hex(x)for x in native],rgb565_pointers=[hex(x)for x in ptrs],frame_select=u32(st+44),dma_render=u32(st+80),render_to_texture=u32(st+84),logged=logged[-1:]))
assert set(records[0]['rgb565_pointers'])==set(int(x,16).__format__('#x')for x in re.findall('[0-9a-f]+',records[0]['logged'][0])[1:])
out=D/'controlled005-006-frozen-PVR-framebuffer-readonly-audit.json';assert not out.exists();out.write_text(json.dumps(dict(scope='Read-only saved-state proof against frozenELF front/back disassembly. Native pvr_state two framebuffer structs at312/320, standardDC mask7fffff and KOS conversion. Current live pointer reads still need bounded/identity checks.',records=records),indent=2)+'\n');print(json.dumps(records,indent=2))
