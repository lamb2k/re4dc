from pathlib import Path
import struct,re,json,hashlib
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18');D=Path(r'C:\Flycast-Evidence\re4-dreamcast\castle18-20261018\Test21\recovered-j-content-20261021');p=Path(r'\\wsl.localhost\Ubuntu-24.04\root\probe\castle21-recovered-j-content-20261021\tree\st2\r204.arc');b=p.read_bytes();manifest=json.loads((D/'master/base-manifest.json').read_text());assert hashlib.sha256(b).hexdigest()==manifest['st2/r204.arc']['sha256'];rows=[]
for m in re.finditer(b'AEV\0',b):
 pos=m.start();v,n=struct.unpack_from('<HH',b,pos+4)
 if v!=0x104 or not 0<n<256 or pos+16+n*0x9c>len(b):continue
 for i in range(n):
  q=b[pos+16+i*0x9c:pos+16+(i+1)*0x9c];pts=[struct.unpack_from('<2f',q,0x14+j*8)for j in range(4)];r=dict(no=hex(q[0x36]),type=q[0x35],enabled=bool(q[0x34]&1),checkFlag=q[0x37],trigger=q[0x38],center=[sum(x[0]for x in pts)/4,struct.unpack_from('<f',q,8)[0]+1,sum(x[1]for x in pts)/4],points=pts,angle=struct.unpack_from('<b',q,0x48)[0]*2*3.141592653589793/180)
  if q[0x35]==1:r.update(destination=hex(q[0x6c]*256+q[0x6d]),lock_type=q[0x6e],lock_flag=q[0x6f],destination_position=list(struct.unpack_from('<3f',q,0x5c)))
  rows.append(r)
out=D/'r204-frozen-selected-source-AEV-controlled-20261021.json';assert not out.exists();out.write_text(json.dumps(dict(source=str(p),sha256=hashlib.sha256(b).hexdigest(),areas=rows),indent=2)+'\n');print(json.dumps([r for r in rows if r['type']==1 or r['no']in['0x2','0x3','0x6','0x7','0x8','0x9']],indent=2))
