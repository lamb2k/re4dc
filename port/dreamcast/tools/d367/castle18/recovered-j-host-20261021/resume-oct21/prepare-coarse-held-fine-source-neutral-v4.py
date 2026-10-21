from pathlib import Path
import hashlib
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18')
for old,new in [('owned-window-recovered-j-r201-Garrador-bodycoast-exactHP-axis-v3-still.py','owned-window-recovered-j-r201-Garrador-coarseheld-finepulse-coast-v4-still.py'),('owned-window-recovered-j-r201-source5C-bodycoast-axis-v7-still.py','owned-window-recovered-j-r201-source5C-coarseheld-finepulse-coast-v8-still.py')]:
 p=L/new;assert not p.exists();s=(L/old).read_text();s=s.replace("   before=u32(pg+0x51e4);before_m3r=","   fine=max(abs(yerr),abs(perr))<.08\n   if fine:ticks=1\n   before=u32(pg+0x51e4);before_m3r=",1)
 oldline="     if cf>before and any(abs(errs[i])<=aim_tolerance*.8 or errs[i]*initial[i]<=0 for i in axes):crossed=True;break"
 newline="""     projected=False
     if len(feedback)>=3:
      prev=feedback[max(0,len(feedback)-4)];dt=cf-prev['frame']
      if dt>0:
       rates=[(errs[i]-prev['errors'][i])/dt for i in [0,1]]
       projected=any(errs[i]*rates[i]<0 and abs(errs[i])<=abs(rates[i])*3+aim_tolerance for i in axes)
     if cf>before and (projected or any(abs(errs[i])<=aim_tolerance*.8 or errs[i]*initial[i]<=0 for i in axes)):crossed=True;break"""
 assert oldline in s;s=s.replace(oldline,newline,1);s=s.replace('settled=crossed or near','settled=crossed or near or fine',1)
 a=s.index("    transition({'ready'});settle=");b=s.index("   events.append({'reviewed_dominant_axis_held_correction'",a)
 s=s[:a]+"""    transition({'ready'});neutral_since=None;until=time.monotonic()+2;neutral_start=u32(pg+0x51e4)
    while True:
     held_aim_guard(pl,gp);assert time.monotonic()<until and u32(pg+0x51e4)-neutral_start<=30,'Ordinary aim release source neutral timeout';nf=u32(pg+0x51e4);jxy=struct.unpack('<2b',read(0x8c3a9544,2));kon=struct.unpack('<Q',read(0x8c3a948c+0x10,8))[0]
     if abs(jxy[0])<1 and abs(jxy[1])<1 and not(kon&15):
      if neutral_since is None:neutral_since=nf
      if nf-neutral_since>=3:break
     else:neutral_since=None
     time.sleep(.005)
"""+s[b:]
 s=s.replace("max_source_ticks=ticks,initial_errors=initial", "max_source_ticks=ticks,fine_one_tick_then_actual_neutral=fine,initial_errors=initial",1)
 s=s.replace('Source-prepared until actual Flycast proof.','Source-prepared until actual Flycast proof. Run266 confirmed held coarse yaw reaches target but fixed3tick neutral retains decayingstick and overshoots; this variant predicts release using three-tick observed error trend, waits actualJoyXY0 and Keydirection0 plus3ticks, and uses original one-tick fine corrections only below0.08rad. Final physical firing guards unchanged. ',1);compile(s,str(p),'exec');p.write_text(s);print(p.name,hashlib.sha256(p.read_bytes()).hexdigest())
