from pathlib import Path
import re,hashlib
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18');base=L/'owned-window-recovered-j-r201-sustained-activefront9000-deathfirst-still.py';head=L/'owned-window-test21-j-original-r201-source-head5-wave213-still.py';wave=L/'owned-window-recovered-j-r201-postboss-wave-live-guard-walk-still.py';out=L/'owned-window-recovered-j-r201-source5C-head5-Wait-combat-still.py';assert not out.exists();s=base.read_text();h=head.read_text();w=wave.read_text()
a=s.index('_sc=json.loads(');b=s.index('\ntry:',a);s=s[:a]+"_sc=json.loads((_seed/'owned-window-current-stair-walk.json').read_text());_wa=[x for r in _sc['samples']if 'wave_status'in r for x in r['wave_status']['active_character_actors']if x['source_list_no']=='0x5c'and x['hp']>0];assert _wa;sealed_actor=_wa[-1];sealed_boss_hp=sealed_actor['hp'];sealed_target_ptr=int(sealed_actor['ptr'],16);assert 0<sealed_boss_hp<=1000\n"+s[b:]
s=s.replace("mapkeys={'forward':","mapkeys={'partner':(ord('S'),0x1f),'forward':",1)
a=s.index(' def weakpoint(gp):');b=s.index(' started=time.monotonic()',a);aa=h.index(' def source_head(gp):');bb=h.index(' sy=json.loads(',aa);ww=w.index(' sy=json.loads(');we=w.index(' arrived_frame=None',ww);s=s[:a]+h[aa:bb]+w[ww:we]+s[b:]
s=s.replace('started=time.monotonic();last_fire=', 'started=time.monotonic();wait_commands=0;wait_last=-999;wait_confirmed=None;wait_pos=None;last_fire=',1)
a=s.index('  if input_frame is None:');s=s[:a]+'''  pl=u32(0x8c39d700);sub=u32(0x8c39d6fc);assert read(pl+0x100,1)[0]==0 and read(sub+0x100,1)[0]==3
  flags=struct.unpack('<H',read(sub+0x400,2))[0];sr=list(read(sub+0xfc,4));pr=list(read(pl+0xfc,4));ap=struct.unpack('<3f',read(sub+0x94,12))
  if not(flags&2):
   transition(set());can_sub=bool(flags&0x80)or bool(flags&0x40 and not(flags&9)and sr[0]==0 and sr[1]in[0,1,2,4,5,6,7,8,9,10,11,12,13,14,17,18,19]);can_pl=pr[0]==0 and pr[1]<=6 and not(pr[1]==6 and pr[2]in[2,4,6])
   if can_sub and can_pl and ff-wait_last>=60:
    assert wait_commands<2,'Two ordinary source-ready Wait commands failed';transition({'partner'});until=time.monotonic()+1
    while u32(pg+0x51e4)<ff+8 and time.monotonic()<until:
     check();life,_,ash,_=struct.unpack('<4H',read(pg+0x4fa4,8));assert life>=_sp['health'][0] and ash>=_sp['health'][2],'Original injury during Wait command';time.sleep(.005)
    transition(set());wait_last=ff;wait_commands+=1;events.append({'normal_source_ready_S_Wait':dict(frame=ff,flags=hex(flags),partner_pos=ap)})
   time.sleep(.03);continue
  if wait_confirmed is None:wait_confirmed=ff;wait_pos=ap;events.append({'original_Ashley_Wait_confirmed':dict(frame=ff,flags=hex(flags),partner_pos=ap)})
  assert math.dist(ap,wait_pos)<1200,'Preserve ordinary West/North Ashley Wait location'
  if ff-wait_confirmed<15:transition(set());time.sleep(.03);continue
''' +s[a:]
s=s.replace("gp=0x8caf2460;assert read(gp+0x100,2)==b'\\x1b\\x0a'", "gp=sealed_target_ptr;assert read(gp+0x100,2)==b'\\x1b\\x07'and read(gp+0x398,1)[0]==0x5c")
a=s.index('  if ghp<=0:');b=s.index('  if shot_pending and ff-last_fire>=60:',a);s=s[:a]+'''  row['wave_status']=wave_status();live=[x for x in row['wave_status']['active_character_actors']if x['hp']>0];near=min((math.dist(pos,x['pos'])for x in live),default=1e9);ashnear=min((math.dist(ap,x['pos'])for x in live),default=1e9);row.update(nearest_live_enemy=near,nearest_to_Ashley=ashnear)
  if near<3500 or ashnear<3500:
   transition(set());events.append({'original_live_wave_within3500_combat_disengage':dict(row)});capture_before_close();assert u.PostMessageW(hwnd,0x10,0,0);break
  if ghp<=0:
   transition(set());row.update(selected_wave_actor_hp=ghp,selected_wave_actor_routines=list(read(gp+0xfc,4)))
   if death_since is None:death_since=ff;events.append({'actual_original_source5C_HP0':dict(row)})
   if ff-death_since>=30:events.append({'original_source5C_HP0_and30_worldticks':dict(row)});capture_before_close();assert u.PostMessageW(hwnd,0x10,0,0);break
   time.sleep(.03);continue
''' +s[b:]
s=s.replace('wp,scaled_radius=weakpoint(gp)','wp,scaled_radius=source_head(gp)');s=s.replace("assert math.hypot(ap[0]-29268,ap[2]+42749)<1200,'ActualAshley stays in original cell-exterior Wait46';", "assert math.dist(ap,wait_pos)<1200,'Preserve original ordinary Wait location';")
s=s.replace('if vel>40:','if vel>80:');s=s.replace("if row['actual_damage_record']['partNo']!=37:","if row['actual_damage_record']['partNo']!=5:")
a=s.index("  if row['player_back_dot']>=-600:");b=s.index('  rear_lost_since=None',a);s=s[:a]+s[b:];s=s.replace("aim_v=[v[0],v[1]-70,v[2]];row['normal_aim_point_offset_within_original_sphere']=[0,-70,0]","aim_v=[v[0],v[1],v[2]];row['normal_aim_point_offset_within_original_sphere']=[0,0,0]")
s=s.replace(" and row['player_back_dot']<-.7*math.hypot(pos[0]-gpos[0],pos[2]-gpos[2])",'');s=s.replace('weakpoint37','head5');s=s.replace('weakpoint_stop_ammo','head5_stop_ammo');s=s.replace('Garrador','selected_source5C');s=s.replace("'Ashley Wait outside required'","'Ashley ordinary Wait required'")
a=s.index("'scope':",s.index('finally:'));b=s.index(",'memory_rights':",a);s=s[:a]+"'scope':'One current original source5C head5 combat unit. Existing exact-state/ELF/image/PID/FILETIME and preloaded screenshot machinery, normal source-ready S Wait in safe North/West location, then ordinary RT/yaw/pitch/A against original head5 capsule midpoint and actual weapon ray/laser. Require original part5/HP decrease; max6shots/hits, normal empty reload,30worldticks afterHP0, any injury and3500 proximity to Leon OR Ashley stop. Target dynamically sealed from latest original linked list, no forced AI/position/HP/item/flag/game/state writes or rollback. Source prepared only until actual runtime evidence.'"+s[b:]
assert 'gp=0x8caf2460'not in s and 'no==37'not in s and 'v[1]-70'not in s and 'sealed_target_ptr'in s;compile(s,str(out),'exec');out.write_text(s);print(out,hashlib.sha256(out.read_bytes()).hexdigest())