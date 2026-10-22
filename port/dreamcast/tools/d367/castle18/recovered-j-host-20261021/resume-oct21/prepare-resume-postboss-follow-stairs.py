from pathlib import Path
import hashlib,py_compile
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18')
src=L/'owned-window-recovered-j-r201-source-ack-quickturn-walk-still.py'
assert hashlib.sha256(src.read_bytes()).hexdigest()=='1b8ed650c9eb3c908bac6fa1ef1066713c1482c73cea2922e40013bc194fd510'
s=src.read_text(encoding='utf-8-sig')
s=s.replace("mapkeys={'forward':", "mapkeys={'partner':(ord('S'),0x1f),'forward':",1)
s=s.replace('input_refreshes=0\n while', 'input_refreshes=0;follow_frame=None;initial_distance=None;last_command=-999;commands=0\n while',1)
old="assert struct.unpack('<H',read(sub+0x400,2))[0]&2,'Require original Ashley Wait outside cell';"
assert s.count(old)==1;s=s.replace(old,'')
start=s.index('  gp=0x8caf2460;')
end=s.index('\n  ff=u32(pg+0x51e4);',start)
follow='''  ff=u32(pg+0x51e4);count=struct.unpack('<H',read(0x8c3b9314+2,2))[0];sv=u32(0x8c3b9314+0x18);assert 0<count<512
  rsf=next(u32(sv+j*0xd8+4)for j in range(count)if read(sv+j*0xd8,2)==bytes([2,1]));assert rsf&0xc4000000==0xc4000000,'Original boss death/door/lever callback prerequisite';samples[-1]['original_r201_saved_RSF']=hex(rsf)
  flags=struct.unpack('<H',read(sub+0x400,2))[0];sr=list(read(sub+0xfc,4));pr=list(read(pl+0xfc,4));ap=struct.unpack('<3f',read(sub+0x94,12));partner_distance=math.dist(pos,ap);samples[-1].update(partner_flags=hex(flags),partner_pos=ap,partner_distance=partner_distance)
  if initial_distance is None:initial_distance=partner_distance
  if flags&2:
   transition(set());can_sub=bool(flags&0x80)or bool(flags&0x40 and not(flags&9)and sr[0]==0 and sr[1]in[0,1,2,4,5,6,7,8,9,10,11,12,13,14,17,18,19]);can_pl=pr[0]==0 and pr[1]<=6 and not(pr[1]==6 and pr[2]in[2,4,6])
   if can_sub and can_pl and ff-last_command>=60:
    assert commands<2,'Two normal source-ready Follow commands failed';transition({'partner'});until=time.monotonic()+1
    while u32(pg+0x51e4)<ff+8 and time.monotonic()<until:
     check();life,_,ash,_=struct.unpack('<4H',read(pg+0x4fa4,8));assert life>=baseline_health[0]and ash>=baseline_health[1],'Original damage during Follow';time.sleep(.005)
    transition(set());last_command=ff;commands+=1;events.append({'normal_source_ready_S_Follow':dict(frame=ff,flags=hex(flags),distance=partner_distance)})
   time.sleep(.03);continue
  if follow_frame is None:follow_frame=ff;events.append({'actual_original_Ashley_Follow_cleared_Wait':dict(frame=ff,flags=hex(flags))})
  if ff-follow_frame<15 or partner_distance>initial_distance-100:transition(set());time.sleep(.03);continue
'''
s=s[:start]+follow.rstrip()+s[end:]
s=s.replace("'scope':'Actual J123 original injury528/90 state;", "'scope':'Recovered J actual boss-death callback required; source-ready normal Ashley Follow plus actual movement, then consolidated original stairs route. Latest sealed health and any further damage guard. No reload needed while magazine remains nonempty. Historical base:",1)
dst=L/'owned-window-recovered-j-r201-postboss-follow-stairs-still.py';assert not dst.exists();dst.write_text(s.rstrip()+'\n',encoding='utf-8');py_compile.compile(str(dst),doraise=True)
print(dst,hashlib.sha256(dst.read_bytes()).hexdigest())
