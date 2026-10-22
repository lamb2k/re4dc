from pathlib import Path
import hashlib,py_compile
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18')
src=L/'owned-window-recovered-j-r201-source-ack-quickturn-walk-still.py';s=src.read_text()
assert hashlib.sha256(src.read_bytes()).hexdigest()=='1b8ed650c9eb3c908bac6fa1ef1066713c1482c73cea2922e40013bc194fd510'
old="assert struct.unpack('<H',read(sub+0x400,2))[0]&2,'Require original Ashley Wait outside cell';"
assert s.count(old)==1;s=s.replace(old,"assert not(struct.unpack('<H',read(sub+0x400,2))[0]&2),'Require original Ashley Follow after normal command';")
historical=(L/'owned-window-test21-j-original-r201-reset-wave-entry205-still.py').read_text()
ws=historical[historical.index(' sy=json.loads('):historical.index(' started=time.monotonic();')]
s=s.replace(' started=time.monotonic();',ws+' started=time.monotonic();',1)
start=s.index('  gp=0x8caf2460;');end=s.index('\n  ff=u32(pg+0x51e4);',start)
replacement='''  count=struct.unpack('<H',read(0x8c3b9314+2,2))[0];sv=u32(0x8c3b9314+0x18);assert 0<count<512;rsf=next(u32(sv+j*0xd8+4)for j in range(count)if read(sv+j*0xd8,2)==bytes([2,1]));assert rsf&0xc4000000==0xc4000000,'Original death/door/lever prerequisite';samples[-1]['original_r201_saved_RSF']=hex(rsf);samples[-1]['partner_pos']=struct.unpack('<3f',read(sub+0x94,12));samples[-1]['partner_flags']=hex(struct.unpack('<H',read(sub+0x400,2))[0]);samples[-1]['wave_status']=wave_status()
  near=min((math.hypot(e['pos'][0]-pos[0],e['pos'][2]-pos[2])for e in samples[-1]['wave_status']['active_character_actors']if e['hp']>0 and e['id']!='0x1b'),default=1e9);samples[-1]['nearest_live_enemy_xz']=near
  if near<3500:transition(set());events.append({'original_live_wave_enemy_within3500_stop_before_approach':dict(samples[-1])});capture_before_close();assert u.PostMessageW(hwnd,0x10,0,0);break
'''
s=s[:start]+replacement.rstrip()+s[end:]
start=s.index('  if distance<tolerance and target_i==len(targets)-1:');end=s.index('  if distance<tolerance:\n',start)
replacement='''  if (distance<tolerance or arrived_frame is not None)and target_i==len(targets)-1:
   transition(set())
   if arrived_frame is None:arrived_frame=ff;events.append({'normal_reset_wave_area_reached_observe_original_source_120ticks':dict(samples[-1])})
   if ff-arrived_frame>=120:events.append({'normal_reset_wave_source_120tick_observation_complete':dict(samples[-1])});capture_before_close();assert u.PostMessageW(hwnd,0x10,0,0);break
   time.sleep(.03);continue
'''
s=s[:start]+replacement+s[end:]
s=s.replace("'scope':'Actual J123 original injury528/90 state;", "'scope':'Recovered J current sealed postboss Follow walk: original death/door/lever RSF required, exact scoped source waves read-only, source-ack normal controls, stop any injury or live enemy within3500; last waypoint observes120ticks neutral. Historical base:",1)
dst=L/'owned-window-recovered-j-r201-postboss-wave-walk-still.py';assert not dst.exists();dst.write_text(s.rstrip()+'\n',encoding='utf-8');py_compile.compile(str(dst),doraise=True);print(dst.name,hashlib.sha256(dst.read_bytes()).hexdigest())
