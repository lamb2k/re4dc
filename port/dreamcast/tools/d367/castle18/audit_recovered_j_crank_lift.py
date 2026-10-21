from pathlib import Path
import sys,json,struct,math
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18');prefix=(L/'audit-recovered-j-checkpoint.py').read_text().split('proof=dict(')[0];prefix=prefix.replace(';assert not out.exists()','');exec(prefix);assert phase==[3,0]and not(ss or stop or held);ram=raw[rb:rb+0x1000000];assert len(ram)==0x1000000;matches=[];needle=struct.pack('<3f',19974.,11555.,-21476.);pos=0
while True:
 at=ram.find(needle,pos)
 if at<0:break
 pos=at+1;ptr=0x8c000000+at-0x94
 if ptr%4 or not(0x8c000000<=ptr<0x8cfffc00):continue
 start=0;ref=struct.pack('<I',ptr)
 while True:
  q=ram.find(ref,start)
  if q<0:break
  start=q+1;work=0x8c000000+q-0x13c
  if q%4 or not(0x8c000000<=work<0x8cfffc00):continue
  ids=[u32(work+x)for x in [0x134,0x138,0x140]]
  if not all(0x8c000000<=x<0x8cfffc00 for x in ids):continue
  target=struct.unpack('<3f',read(work+0x148,12));actual=[struct.unpack('<f',read(x+0x98,4))[0]for x in ids];gap=[a-b for a,b in zip(target,actual)]
  if not all(math.isfinite(v)and 0<=v<=7539 for v in gap)or max(gap)-min(gap)>1:continue
  if not all(math.isfinite(v)and abs(v)<100000 for v in target):continue
  matches.append(dict(work=hex(work),crank=hex(ptr),wall_objects=[hex(x)for x in ids],raised_y=list(target),actual_y=actual,remaining_lift=gap[1],completed_lift=7539-gap[1]))
unique={x['work']:x for x in matches};assert len(unique)==1,unique;result=dict(scope='Read-only recovered-J NEW snapshot, four exact ELF anchors. Original source crank position, owner+0x13c, three agreeing wall lift deltas. No game/state writes.',capture=cap.name,source_frame=u32(pg+0x51e4),state_sha256=__import__('hashlib').sha256(state.read_bytes()).hexdigest(),**next(iter(unique.values())));dest=D/f'route-walk{n:02d}-physical-crank-lift.json';assert not dest.exists();dest.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))