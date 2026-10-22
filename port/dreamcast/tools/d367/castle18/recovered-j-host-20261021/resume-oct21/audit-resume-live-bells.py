from pathlib import Path
import json,sys,struct
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18');h={};prefix=(L/'audit-resume-exact-combat.py').read_text().split('record=dict')[0];exec(prefix.replace('assert not p.exists()','pass'),h);r,u32,pg=h['read'],h['u32'],h['pg'];out=h['D']/(h['cap'].name+'-bells.json');assert not out.exists();rows=[]
for ptr in [0x8caddab8,0x8cadd6e0]:
 b=r(ptr,0x338);rows.append(dict(ptr=hex(ptr),id=b[0x100],be_flag=hex(struct.unpack_from('<I',b,4)[0]),routines=list(b[0xfc:0x100]),position=struct.unpack_from('<3f',b,0x94),ringTimer=struct.unpack_from('<h',b,0x332)[0],hit_ptr=hex(struct.unpack_from('<I',b,0x334)[0])))
count=struct.unpack('<H',r(0x8c3b9314+2,2))[0];table=u32(0x8c3b9314+0x18);assert count<512;rsf=None
for i in range(count):
 b=r(table+i*0xd8,0xd8)
 if b[:2]==b'\x02\x01':rsf=hex(struct.unpack_from('<I',b,4)[0]);break
rec=dict(scope='Read-only exact closed checkpoint original bell objects and saved r201 flags.',run=h['cap'].name,state_sha256=h['proof']['state_sha256'],bells=rows,r201_RSF=rsf);out.write_text(json.dumps(rec,indent=2)+'\n');print(json.dumps(rec))
