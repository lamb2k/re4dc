from pathlib import Path
import struct,json,hashlib,sys
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18');R=Path(r'C:\Flycast-Evidence\re4-dreamcast\castle18-20261018\Test21');D=R/'recovered-j-content-20261021';n=int(sys.argv[1]);cap=D/f'route-walk{n}';p=D/f'route-walk{n}-exact-combat.json';assert not p.exists()
proof=json.loads((D/f'route-walk{n}-checkpoint-proof.json').read_text());state=cap/'data/disc.state';assert hashlib.sha256(state.read_bytes()).hexdigest()==proof['state_sha256']
h={};exec((L/'audit-authoritative-life-extended-history-20261019.py').read_text().split('targets=[')[0],h);raw=h['decode'](state);va,code=h['load_segments'](R/'builds/c21jmW/re4dc-game.elf');rb=raw.find(code[0x4000:0x4100])-(va+0x4000-0x8c000000)
for off in [0x100000,0x120000,0x140000]:assert raw[rb+va+off-0x8c000000:rb+va+off+256-0x8c000000]==code[off:off+256]
def read(a,n):assert 0x8c000000<=a and a+n<=0x8d000000;return raw[rb+a-0x8c000000:rb+a+n-0x8c000000]
u32=lambda a:struct.unpack('<I',read(a,4))[0]
pg=u32(0x8c2e91dc);gp=0x8caf2460;assert read(gp+0x100,2)==b'\x1b\x0a';pl=u32(0x8c39d700);sub=u32(0x8c39d6fc)
ip=u32(0x8c3a91f4+0x14);count=u32(0x8c3a91f4+0x1c);assert 1<=count<=512;items=[]
for i in range(count):
 b=read(ip+i*14,14)
 if b[4]&1:items.append(dict(id=struct.unpack_from('<H',b)[0],num=struct.unpack_from('<H',b,2)[0],bullet=struct.unpack_from('<H',b,8)[0]&0x1fff))
record=dict(scope='Read-only exact closed checkpoint combat state, not last asynchronous controller sample. No guest or state writes.',run=cap.name,state_sha256=proof['state_sha256'],source=u32(pg+0x51e4),health=list(struct.unpack('<4H',read(pg+0x4fa4,8))),hero_pos=list(struct.unpack('<3f',read(pl+0x94,12))),hero_yaw=struct.unpack('<f',read(pl+0xa4,4))[0],hero_routines=list(read(pl+0xfc,4)),partner_pos=list(struct.unpack('<3f',read(sub+0x94,12))),partner_flags=hex(struct.unpack('<H',read(sub+0x400,2))[0]),boss=dict(hp=struct.unpack('<h',read(gp+0x320,2))[0],pos=list(struct.unpack('<3f',read(gp+0x94,12))),yaw=struct.unpack('<f',read(gp+0xa4,4))[0],routines=list(read(gp+0xfc,4))),items=items,elf_sha256=proof['start']['elf_sha256'],image_sha256=proof['start']['disc_sha256'])
p.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
