from pathlib import Path
import hashlib,py_compile
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18');src=L/'owned-window-recovered-j-r201-source-ack-quickturn-walk-still.py';assert hashlib.sha256(src.read_bytes()).hexdigest()=='1b8ed650c9eb3c908bac6fa1ef1066713c1482c73cea2922e40013bc194fd510';s=src.read_text()
s=s.replace("mapkeys={'forward':","mapkeys={'ready':(ord('V'),0x2f),'fire':(ord('X'),0x2d),'forward':",1)
b=(L/'owned-window-recovered-j-r201-original-bell-current-health-still.py').read_text();inv=b[b.index(' def inventory():'):b.index(' def pulse(')]
s=s.replace(' captured_checkpoint=False',inv+' captured_checkpoint=False',1)
s=s.replace('input_refreshes=0\n while','input_refreshes=0;bait_started=None;bait_frame=None;bait_magazine=None;bait_done=False\n while',1)
marker='  ff=u32(pg+0x51e4);key_on='
at=s.index(marker)
block='''  if not bait_done:
   ff=u32(pg+0x51e4);routine=list(read(pl+0xfc,4));gun=next(i for i in inventory()if i['id']==0x23)
   if bait_started is None:bait_started=ff;bait_magazine=gun['bullet'];assert bait_magazine>=1,'One ordinary bait round required'
   if gun['bullet']==bait_magazine-1:
    transition(set());bait_done=True;events.append({'one_ordinary_bait_shot_ammo_decrement_not_damage_claim':dict(frame=ff,magazine_before=bait_magazine,magazine_after=gun['bullet'],boss=samples[-1]['Garrador'])});continue
   assert gun['bullet']==bait_magazine and ff-bait_started<90,'Ordinary bait shot failed or unexpected multiple consumption'
   if bait_frame is not None:transition(set());time.sleep(.01);continue
   transition({'ready'})
   if routine[0]==0 and routine[1]==6 and routine[2]==1 and ff-bait_started>=3:
    bait_frame=ff;transition({'ready','fire'});until=time.monotonic()+1
    while u32(pg+0x51e4)<ff+3 and time.monotonic()<until:
     check();life,_,ash,_=struct.unpack('<4H',read(pg+0x4fa4,8));assert life>=baseline_health[0]and ash>=baseline_health[1],'Original injury during bait shot';time.sleep(.005)
    transition(set());events.append({'normal_RT_A_single_bait_pulse_before_full_dodge':dict(frame=ff,position=pos,yaw=yaw)})
   time.sleep(.02);continue
'''
s=s[:at]+block+s[at:]
s=s.replace("'scope':'Actual J123 original injury528/90 state;","'scope':'Consolidated original combat attempt: one normal RT+A bait shot, exact one-round consumption required, then full source-ack Back/B northwestern dodge and eastern firing approach. Bait shot claims noise/ammunition only, no weakpoint damage unless source proves it. Current sealed health and all injury/PID/phase/collision/resource guards retained; no game/state/health/AI writes. Historical base:",1)
dst=L/'owned-window-recovered-j-r201-single-bait-full-dodge-still.py';assert not dst.exists();dst.write_text(s,encoding='utf-8');py_compile.compile(str(dst),doraise=True);print(dst.name,hashlib.sha256(dst.read_bytes()).hexdigest())
