from pathlib import Path
import hashlib
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18')
def augment(src,out,kind):
 s=(L/src).read_text();p=L/out;assert not p.exists();f='weakpoint'if kind=='boss'else'source_head'
 if kind=='boss':
  at=s.index(' started=time.monotonic()');s=s[:at]+" sy=json.loads((root/'Test21/J-elf-scoped-symbols.json').read_text())['symbols'];pitch_m3r=next(x['address']for x in sy if x['name']=='m3r');pitch_system=next(x['address']for x in sy if x['name']=='_pSys')\n"+s[at:]
 at=s.index(' started=time.monotonic()');guard=r""" def held_aim_guard(pl,gp):
  check();hh=list(struct.unpack('<4H',read(pg+0x4fa4,8)));assert hh[0]>=_sp['health'][0] and hh[2]>=_sp['health'][2],'Original injury during bounded ordinary input'
  assert tuple(read(pg+0x20,2))==(3,0) and u32(pg+0x170)==0 and read(0x8c3de064+0x28,1)[0]==0,'Original phase changed during input'
  pp=struct.unpack('<3f',read(pl+0x94,12));ap=struct.unpack('<3f',read(u32(0x8c39d6fc)+0x94,12))
"""
 if kind=='boss':guard+=r"""  assert read(gp+0x100,2)==b'\x1b\x0a';gg=struct.unpack('<3f',read(gp+0x94,12));gy=struct.unpack('<f',read(gp+0xa4,4))[0];dot=(pp[0]-gg[0])*math.sin(gy)+(pp[2]-gg[2])*math.cos(gy);assert not(dot>=-600 and math.hypot(pp[0]-gg[0],pp[2]-gg[2])<=9000 and read(gp+0xfc,1)[0]!=2),'Original active front9000 disengagement during input'
"""
 else:guard+=r"""  assert read(gp+0x100,2)==b'\x1b\x07'and read(gp+0x398,1)[0]==0x5c;live=[x for x in wave_status()['active_character_actors']if x['hp']>0];assert all(math.dist(pp,x['pos'])>=3500 and math.dist(ap,x['pos'])>=3500 for x in live),'Original3500 Leon-or-Ashley disengagement during input'
"""
 guard+=r""" def held_ray_feedback(pl,gp):
  wp,rr=AIMFUNC(gp);wep=u32(pl+0x788);obj=u32(wep+0x34);assert 0x8c000000<=obj<0x8cff0000;mu,mm=point(obj,0,(228,-24,29));dr=[-mm[0],-mm[4],-mm[8]];nn=math.sqrt(sum(v*v for v in dr))
  if not .8<nn<1.2:return None
  dr=[x/nn for x in dr];vv=[wp[i]-mu[i]for i in range(3)];av=[vv[0],vv[1]OFFSET,vv[2]];ye=(math.atan2(av[0],av[2])-math.atan2(dr[0],dr[2])+math.pi)%(2*math.pi)-math.pi;pe=math.atan2(av[1],math.hypot(av[0],av[2]))-math.atan2(dr[1],math.hypot(dr[0],dr[2]));return ye,pe
""".replace('AIMFUNC',f).replace('OFFSET','-70'if kind=='boss'else'')
 s=s[:at]+guard+s[at:];s=s.replace('started=time.monotonic();','started=time.monotonic();body_align_since=None;body_quick_done=False;body_input_frame=-999;body_refresh=0;',1)
 a=s.index('  if input_frame is None:');b=s.index('  if ff<input_frame+6:',a)
 gp='0x8caf2460'if kind=='boss'else'sealed_target_ptr'
 pre="""  if input_frame is None:
   gp=TARGETPTR;held_aim_guard(pl,gp);qp=struct.unpack('<3f',read(pl+0x94,12));qy=struct.unpack('<f',read(pl+0xa4,4))[0];qh,_=AIMFUNC(gp);qd=(math.atan2(qh[0]-qp[0],qh[2]-qp[2])-qy+math.pi)%(2*math.pi)-math.pi;pr=list(read(pl+0xfc,4));row.update(body_prealign_error=qd,body_prealign_yaw=qy,body_prealign_routine=pr,source_raw_Joy_xy=list(struct.unpack('<2b',read(0x8c3a9544,2))),source_raw_Joy_on=hex(u32(0x8c3a9544+0x10)),source_Key_on=hex(struct.unpack('<Q',read(0x8c3a948c+0x10,8))[0]))
   if pr[0]!=0 or pr[1]in[5,6]:transition(set());body_align_since=None;time.sleep(.025);continue
   if not body_quick_done and abs(qd)>1.8:
    transition(set());before=ff;transition({'back'});until=time.monotonic()+1
    while True:
     held_aim_guard(pl,gp);qf=u32(pg+0x51e4);joy=struct.unpack('<b',read(0x8c3a9544+1,1))[0];kon=struct.unpack('<Q',read(0x8c3a948c+0x10,8))[0]
     if joy<=-30 and kon&2:break
     assert time.monotonic()<until and qf-before<30,'Ordinary Back source acknowledgment timed out';time.sleep(.005)
    transition({'back','dash'});until=time.monotonic()+1
    while u32(pg+0x51e4)<qf+3:held_aim_guard(pl,gp);assert time.monotonic()<until;time.sleep(.005)
    transition(set());body_quick_done=True;body_align_since=None;events.append({'ordinary_Back_ack_B_before_RT_then_wait_authored_routine':dict(frame=before,ack=qf,JoyY=joy,yaw=qy,delta=qd)});time.sleep(.025);continue
   if abs(qd)>.08:
    wanted={'left'if qd>0 else'right'};body_align_since=None
    if active==wanted and not(struct.unpack('<Q',read(0x8c3a948c+0x10,8))[0]&12)and ff-body_input_frame>=10:
     assert body_refresh<3,'Standing turn source acknowledgment absent';transition(set());until=time.monotonic()+1
     while u32(pg+0x51e4)<ff+2 and time.monotonic()<until:held_aim_guard(pl,gp);time.sleep(.005)
     body_refresh+=1
    if active!=wanted:body_input_frame=ff
    transition(wanted);time.sleep(.025);continue
   transition(set())
   if body_align_since is None:body_align_since=ff
   if ff-body_align_since<3 or pr[1]!=0:time.sleep(.025);continue
   events.append({'ordinary_standing_body_prealigned_and_settled_BEFORE_RT':dict(frame=ff,yaw=qy,bearing_error=qd,routine=pr)});input_frame=ff;last_refresh=ff+6
""".replace('TARGETPTR',gp).replace('AIMFUNC',f)
 if kind=='boss':pre="  pl=u32(0x8c39d700);sub=u32(0x8c39d6fc);assert read(pl+0x100,1)[0]==0 and read(sub+0x100,1)[0]==3;assert struct.unpack('<H',read(sub+0x400,2))[0]&2,'Original Ashley Wait required'\n"+pre
 s=s[:a]+pre+s[b:]
 if kind=='boss':
  a=s.index('  if pitch_check is not None:');b=s.index('  if abs(yerr)>aim_tolerance',a);s=s[:a]+"  pitch_up_key='back'if u32(u32(pitch_system))&0x80000000 else'forward';pitch_check=None;row['source_m3r']=list(struct.unpack('<3f',read(pitch_m3r,12)))\n"+s[b:]
 s=s.replace("  transition({'ready'})\n  gun=", "  if not(active & {'left','right','forward','back'}):transition({'ready'})\n  gun=",1)
 a=s.index('  if abs(yerr)>aim_tolerance or abs(perr)>aim_tolerance:');b=s.index('  if key_on&15:',a)
 pulse="""  if abs(yerr)>aim_tolerance or abs(perr)>aim_tolerance:
   aim_settled_since=None;wanted={'ready'};axes=[]
   if abs(yerr)>max(aim_tolerance,2*abs(perr)):
    wanted.add('left'if yerr>0 else'right');ticks=max(3,min(20,int(abs(yerr)/.02)));axes=[0]
   elif abs(perr)>max(aim_tolerance,2*abs(yerr)):
    wanted.add(pitch_up_key if perr>0 else('back'if pitch_up_key=='forward'else'forward'));ticks=max(3,min(12,int(abs(perr)/.01)));axes=[1]
   else:
    if abs(yerr)>aim_tolerance:wanted.add('left'if yerr>0 else'right');axes.append(0)
    if abs(perr)>aim_tolerance:wanted.add(pitch_up_key if perr>0 else('back'if pitch_up_key=='forward'else'forward'));axes.append(1)
    ticks=max(3,min(8,int(max(abs(yerr),abs(perr))/.02)))
   before=u32(pg+0x51e4);before_m3r=list(struct.unpack('<3f',read(pitch_m3r,12)));initial=(yerr,perr);feedback=[];last_ff=-1;crossed=False;transition(wanted);until=time.monotonic()+2
   while u32(pg+0x51e4)<before+ticks:
    held_aim_guard(pl,gp);assert time.monotonic()<until,'Bounded source input correction walltime';cf=u32(pg+0x51e4);errs=held_ray_feedback(pl,gp)
    if errs is None:crossed=True;break
    if cf!=last_ff:
     feedback.append(dict(frame=cf,errors=errs,m3r=list(struct.unpack('<3f',read(pitch_m3r,12))),Joy_xy=list(struct.unpack('<2b',read(0x8c3a9544,2))),Joy_on=hex(u32(0x8c3a9544+0x10)),Key_on=hex(struct.unpack('<Q',read(0x8c3a948c+0x10,8))[0])));last_ff=cf
     if cf>before and any(abs(errs[i])<=aim_tolerance*.8 or errs[i]*initial[i]<=0 for i in axes):crossed=True;break
    time.sleep(.005)
   after=u32(pg+0x51e4);errs=held_ray_feedback(pl,gp);near=errs is None or all(abs(errs[i])<=aim_tolerance for i in axes);settled=crossed or near
   if settled:
    transition({'ready'});settle=u32(pg+0x51e4)+3;until=time.monotonic()+2
    while u32(pg+0x51e4)<settle:held_aim_guard(pl,gp);assert time.monotonic()<until;time.sleep(.005)
   events.append({'reviewed_dominant_axis_held_correction':dict(frame_interval=[before,after],keys=sorted(wanted),max_source_ticks=ticks,initial_errors=initial,ended_errors=errs,crossed_or_near=settled,preserved_nonzero_axis=not settled,source_m3r_before=before_m3r,source_m3r_after=list(struct.unpack('<3f',read(pitch_m3r,12))),source_feedback=feedback)});continue
"""
 s=s[:a]+pulse+s[b:];s=s.replace("'scope':'","'scope':'Independent source-reviewed ordinary control setup: complete normal source-ack quickturn, standing body prealign below0.08rad/release+3ticks/idle BEFORE RT, recompute physical ray after RT camera-pitch initialization. Actual sourceSys inversion/m3r, dominant-axis3..20yaw/3..12pitch held corrections with intrahold geometry/health/proximity/sourceack polling, earlycross/near stop, persistent nonzeroaxis at coarsecap; final3tick neutral only when settled. Original collision/ray/laser/HP/shot/injury/PID/resource guards unchanged. Source-prepared until actual Flycast proof. ",1);compile(s,str(p),'exec');p.write_text(s);print(p.name,hashlib.sha256(p.read_bytes()).hexdigest())
augment('owned-window-recovered-j-r201-source5C-exactwave-sourcepitch-v4-still.py','owned-window-recovered-j-r201-source5C-reviewed-bodyalign-axis-v6-still.py','head')
augment('owned-window-recovered-j-r201-sustained-activefront9000-deathfirst-still.py','owned-window-recovered-j-r201-Garrador-reviewed-bodyalign-axis-v2-still.py','boss')