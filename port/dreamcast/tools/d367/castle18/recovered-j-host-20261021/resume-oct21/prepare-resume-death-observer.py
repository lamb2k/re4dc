from pathlib import Path
import hashlib,py_compile
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18')
combat=L/'owned-window-recovered-j-r201-sustained-front9000-still.py'
s=combat.read_text(encoding='utf-8-sig')
assert hashlib.sha256(combat.read_bytes()).hexdigest()=='6f330b4d5190b161c3e6141ed411dd74dd8515e0203b36058c374e3f5512c2d4'
line=next(l for l in s.splitlines(True)if l.startswith('  if shot_pending and ff-last_fire>=60:'))
assert s.count(line)==1;s=s.replace(line,'',1)
at=s.index('  wp,scaled_radius=weakpoint(gp);')
s=s[:at]+line+s[at:]
fixed=L/'owned-window-recovered-j-r201-sustained-front9000-death-first-still.py';assert not fixed.exists();fixed.write_text(s.rstrip()+'\n',encoding='utf-8');py_compile.compile(str(fixed),doraise=True)
base=L/'owned-window-recovered-j-r201-source-ack-quickturn-walk-still.py';s=base.read_text()
assert hashlib.sha256(base.read_bytes()).hexdigest()=='1b8ed650c9eb3c908bac6fa1ef1066713c1482c73cea2922e40013bc194fd510'
s=s.replace('input_refreshes=0\n while','input_refreshes=0;death_stable_since=None;initial_dying_checked=False\n while',1)
start=s.index('  gp=0x8caf2460;');end=s.index(' transition(set());check()\n if u.IsWindow(hwnd):capture_before_close()',start)
neutral='''  transition(set());ff=u32(pg+0x51e4)
  if not initial_dying_checked:
   assert struct.unpack('<h',read(0x8caf2460+0x320,2))[0]==0 and read(0x8caf2460+0xfc,1)[0]==3,'Requires exact original HP0 dying checkpoint';initial_dying_checked=True
  count=struct.unpack('<H',read(0x8c3b9314+2,2))[0];sv=u32(0x8c3b9314+0x18);assert 0<count<512
  rsf=next(u32(sv+j*0xd8+4)for j in range(count)if read(sv+j*0xd8,2)==bytes([2,1]));samples[-1].update(original_r201_saved_RSF=hex(rsf),original_room_flags=hex(u32(pg+0x51cc)),Garrador_hp=struct.unpack('<h',read(0x8caf2460+0x320,2))[0],Garrador_routines=list(read(0x8caf2460+0xfc,4)))
  if rsf&0xc4000000==0xc4000000:
   if death_stable_since is None:death_stable_since=ff;events.append({'original_death_door_lever_callbacks_observed':dict(samples[-1])})
   if ff-death_stable_since>=30:
    events.append({'original_death_door_callback_stable_freeplay_30ticks':dict(samples[-1])});capture_before_close();assert u.PostMessageW(hwnd,0x10,0,0);break
  else:death_stable_since=None
  time.sleep(.03)
'''
s=s[:start]+neutral+s[end:]
s=s.replace("'scope':'Actual J123 original injury528/90 state;", "'scope':'Recovered J actual HP0 dying continuation: neutral input only, require original deathRSF0, open doorRSF1 and leverRSF5 plus30 stable source freeplay ticks. Latest sealed health, exact image/program and PID guards retained. No state/game writes. Historical base:",1)
dst=L/'owned-window-recovered-j-r201-death-door-neutral-still.py';assert not dst.exists();dst.write_text(s.rstrip()+'\n',encoding='utf-8');py_compile.compile(str(dst),doraise=True)
for p in [fixed,dst]:print(p.name,hashlib.sha256(p.read_bytes()).hexdigest())
