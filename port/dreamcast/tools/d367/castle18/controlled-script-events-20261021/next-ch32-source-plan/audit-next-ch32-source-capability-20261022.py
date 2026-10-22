from pathlib import Path
import json,struct,re,hashlib,datetime,subprocess
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18')
D=Path(r'C:\Flycast-Evidence\re4-dreamcast\castle18-20261018\Test21\recovered-j-content-20261021')
T=Path(r'\\wsl.localhost\Ubuntu-24.04\root\probe\codex-castle18')
TREE=Path(r'\\wsl.localhost\Ubuntu-24.04\root\probe\castle21-recovered-j-content-20261021\tree')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((D/'master/base-manifest.json').read_text())
rooms=['204','205','209','20a','20b','20c','20f','206'];out={}
for room in rooms:
 key=f'st2/r{room}.arc';p=TREE/key;b=p.read_bytes();assert sha(p)==m[key]['sha256'];rows=[]
 for match in re.finditer(b'AEV\0',b):
  pos=match.start();v,n=struct.unpack_from('<HH',b,pos+4)
  if v!=0x104 or not 0<n<256 or pos+16+n*0x9c>len(b):continue
  for i in range(n):
   q=b[pos+16+i*0x9c:pos+16+(i+1)*0x9c];pts=[struct.unpack_from('<2f',q,0x14+j*8)for j in range(4)]
   r=dict(no=hex(q[0x36]),type=q[0x35],flag=hex(q[0x34]),checkFlag=q[0x37],trigger=q[0x38],center=[sum(x[0]for x in pts)/4,struct.unpack_from('<f',q,8)[0]+1,sum(x[1]for x in pts)/4],points=pts,angle=struct.unpack_from('<b',q,0x48)[0]*2*3.141592653589793/180)
   if q[0x35]==1:r.update(destination=f'r{q[0x6c]*256+q[0x6d]:03x}',lock_type=q[0x6e],lock_flag=q[0x6f],destination_position=list(struct.unpack_from('<3f',q,0x5c)),destination_part=q[0x74])
   rows.append(r)
 src=T/f'src/st2/r{room}.cpp';s=src.read_text();out['r'+room]=dict(ARC=m[key],source_sha256=sha(src),doors=[r for r in rows if r['type']==1],selected_areas=[r for r in rows if room=='205' and r['no']in['0x8','0x3','0x11','0x1b']])
flags={}
for line in (D.parent/'builds/c21jmW/resolved-knobs.txt').read_text().splitlines():
 if '='in line:
  k,v=line.split('=',1)
  if k in ['ROUTE_CH31','ROUTE_CH32','ROUTE_CH41','ROUTE_MOVIES','ROUTE_MOVIES_CH3','DBG_WARP','WARP_JUMP','WARP_KILL_PHASE','ALIVE_CAP_NOVIS','R101_ALIVE_CAP','VMU_SAVE','RADIO_SUB_RT','RADIO_SUB_LOG']:flags[k]=v
assetkeys=[k for k in m if any(k.startswith(f'dc/native/r{r}/')for r in rooms)or(k.startswith('dc/movie/')and any(f'r{r}'in k for r in rooms))or k in ['dc/st2_0.ovl','dc/st2_1.ovl','etc/emleon07.esl','etc/emleon08.esl']]
receipt=dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),scope='READ-ONLY source/master capability and route plan; no guest/build/image or gameplay writes, not live event/release/hardware acceptance.',source_commit='12a841d7cfe2c747266b0c330555557e651a4af0',programme_raw_sha256=m['1ST_READ.BIN']['sha256'],master_binding_sha256=sha(D/'frozen-master-programme-binding-20261021.json'),resolved_flags=flags,rooms=out,selected_manifest_assets={k:m[k]for k in assetkeys},protected013_state_sha256='97b63602b83d6234a1603dc24a90fa42f2d0702db626ead2e4d4e5e20efafe13')
dest=L/'NEXT-CH32-SOURCE-CAPABILITY-20261022.json';assert not dest.exists();dest.write_text(json.dumps(receipt,indent=2)+'\n')
print('receipt',sha(dest),dest.stat().st_size,'assets',len(assetkeys),'flags',flags)
for room,x in out.items():
 print(room,'doors',[(r['no'],r['destination'],r['destination_part'],r['lock_type'],[round(v,2)for v in r['center']])for r in x['doors']])
 if room=='r205':print('selected',x['selected_areas'])
