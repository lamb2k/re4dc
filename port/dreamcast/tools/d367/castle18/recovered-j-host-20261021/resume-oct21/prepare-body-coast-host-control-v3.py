from pathlib import Path
import hashlib
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18')
for old,new,kind in [('owned-window-recovered-j-r201-Garrador-reviewed-bodyalign-axis-v2-still.py','owned-window-recovered-j-r201-Garrador-bodycoast-exactHP-axis-v3-still.py','boss'),('owned-window-recovered-j-r201-source5C-reviewed-bodyalign-axis-v6-still.py','owned-window-recovered-j-r201-source5C-bodycoast-axis-v7-still.py','head')]:
 p=L/new;assert not p.exists();s=(L/old).read_text();s=s.replace('body_align_since=None;body_quick_done=False;','body_align_since=None;body_coast_until_idle=False;body_previous=None;body_quick_done=False;',1)
 if kind=='boss':
  a=s.index("_sc=json.loads((_seed/'owned-window-current-stair-walk.json').read_text())");b=s.index('\n',a)
  s=s[:a]+"_bc=json.loads((cap.parent/(_seed.name+'-exact-combat.json')).read_text());assert _bc['state_sha256']==_arm['seed_sha256'];sealed_boss_hp=_bc['boss']['hp'];assert 0<sealed_boss_hp<=4000"+s[b:]
 a=s.index('   if abs(qd)>.08:');b=s.index("   events.append({'ordinary_standing_body_prealigned",a)
 replacement="""   jxy=struct.unpack('<2b',read(0x8c3a9544,2));kon=struct.unpack('<Q',read(0x8c3a948c+0x10,8))[0];rate=0
   if body_previous is not None and ff>body_previous[0]:rate=abs((qy-body_previous[1]+math.pi)%(2*math.pi)-math.pi)/(ff-body_previous[0])
   body_previous=(ff,qy);row['body_observed_yaw_rate']=rate
   if body_coast_until_idle:
    transition(set())
    if abs(jxy[0])>=30 or abs(jxy[1])>=30 or kon&15 or pr[1]!=0:body_align_since=None;time.sleep(.015);continue
    if body_align_since is None:body_align_since=ff
    if ff-body_align_since<3:time.sleep(.015);continue
    body_coast_until_idle=False;events.append({'ordinary_turn_release_observed_actual_neutral_idle_three_ticks':dict(frame=ff,Joy_xy=jxy,routine=pr,error=qd)})
   # Run260 source observations show ~three ticks of stick decay after key release.
   # Coarse setup accepts <=.30rad only after actual neutral/idle; final firing ray is unchanged.
   release_bound=max(.12,min(.35,rate*3+.05))
   if active & {'left','right'} and abs(qd)<=release_bound:
    transition(set());body_coast_until_idle=True;body_align_since=None;events.append({'ordinary_turn_early_release_for_observed_stick_decay':dict(frame=ff,error=qd,observed_yaw_rate=rate,release_bound=release_bound)});time.sleep(.015);continue
   if abs(qd)>.30:
    wanted={'left'if qd>0 else'right'};body_align_since=None
    if active==wanted and not(kon&12)and ff-body_input_frame>=10:
     assert body_refresh<3,'Standing turn source acknowledgment absent';transition(set());body_coast_until_idle=True;body_refresh+=1;time.sleep(.015);continue
    if active!=wanted:body_input_frame=ff
    transition(wanted);time.sleep(.015);continue
   if active:
    transition(set());body_coast_until_idle=True;body_align_since=None;time.sleep(.015);continue
   if abs(jxy[0])>=30 or abs(jxy[1])>=30 or kon&15 or pr[1]!=0:body_align_since=None;time.sleep(.015);continue
   if body_align_since is None:body_align_since=ff
   if ff-body_align_since<3:time.sleep(.015);continue
"""
 s=s[:a]+replacement+s[b:];s=s.replace('body prealign below0.08rad/release+3ticks/idle BEFORE RT','coarse body prealign below0.30rad with observed-yaw earlyrelease and latched actual neutral/idle+3ticks BEFORE RT');compile(s,str(p),'exec');p.write_text(s);print(p.name,hashlib.sha256(p.read_bytes()).hexdigest())
