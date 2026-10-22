from pathlib import Path
import struct,json,hashlib
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18');D=Path(r'C:\Flycast-Evidence\re4-dreamcast\castle18-20261018\Test21\recovered-j-content-20261021');R=D.parent
h={};exec((L/'audit-authoritative-life-extended-history-20261019.py').read_text().split('targets=[')[0],h);raw=h['decode'](D/'route-walk-controlled-ch32-door017/data/disc.state');va,code=h['load_segments'](R/'builds/c21jmW/re4dc-game.elf');rb=raw.find(code[0x4000:0x4100])-(va+0x4000-0x8c000000)
def read(a,n):return raw[rb+a-0x8c000000:rb+a+n-0x8c000000]
u32=lambda a:struct.unpack('<I',read(a,4))[0];sys=u32(0x8c3b94f0);table=u32(sys+4);header=u32(sys);n=struct.unpack('<H',read(header+6,2))[0];door=None
for i in range(n):
 q=read(table+i*0x9c,0x9c)
 if q[0x36]==4:door=dict(ptr=hex(table+i*0x9c),floor=struct.unpack_from('<f',q,8)[0],height=struct.unpack_from('<f',q,12)[0],bytes=q.hex());break
w=read(0x8c47fb58,1836);r=dict(state_sha256=hashlib.sha256((D/'route-walk-controlled-ch32-door017/data/disc.state').read_bytes()).hexdigest(),nativeDoor4=door,go0=w[984:1008].hex(),go1=w[1008:1032].hex(),go2=w[1032:1056].hex());(L/'controlled018-closed017-start.json').write_text(json.dumps(r,indent=2)+'\n');print(r)
p=L/'extract-controlled018-camera-DWARF.py';s=(L/'extract-controlled018-physical-door-DWARF.py').read_text().replace("['cEm','EmDoorWork']","['CameraControl']");a=s.index("wanted={");b=s.index(';result={}',a);s=s[:a]+"wanted={'CameraControl':['cameraNo','areaNo']}"+s[b:];s=s.replace('controlled018-physical-door-DWARF.json','controlled018-camera-DWARF.json');p.write_text(s)