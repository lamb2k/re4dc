from pathlib import Path
import hashlib
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18')
for old,new in [('owned-window-recovered-j-r201-Garrador-coarseheld-finepulse-coast-v4-still.py','owned-window-recovered-j-r201-Garrador-sourceack-fine-neutral-fire-v5-still.py'),('owned-window-recovered-j-r201-source5C-coarseheld-finepulse-coast-v8-still.py','owned-window-recovered-j-r201-source5C-sourceack-fine-neutral-fire-v9-still.py')]:
 p=L/new;assert not p.exists();s=(L/old).read_text();a=s.index(' def held_ray_feedback');s=s[:a]+""" def actual_aim_neutral_latch(pl,gp):
  transition({'ready'});start=u32(pg+0x51e4);deadline=time.monotonic()+2;ns=None;last=None
  while True:
   held_aim_guard(pl,gp);nf=u32(pg+0x51e4);assert nf-start<=30 and time.monotonic()<deadline,'Ordinary all-axis neutral latch timeout';jxy=struct.unpack('<2b',read(0x8c3a9544,2));kon=struct.unpack('<Q',read(0x8c3a948c+0x10,8))[0];pr=list(read(pl+0xfc,4));assert pr[0]==0 and pr[1]==6,'Ordinary RT routine changed during aim neutral latch'
   if jxy==(0,0) and not(kon&15):
    if ns is None:ns=nf
    if nf-ns>=3:return dict(start=start,neutral_since=ns,through=nf,Joy_xy=jxy,Key_on=hex(kon))
   else:ns=None
   time.sleep(.005)
"""+s[a:]
 s=s.replace("   if fine:ticks=1", """   if fine:
    ticks=1
    if struct.unpack('<2b',read(0x8c3a9544,2))!=(0,0) or active & {'left','right','forward','back'}:
     events.append({'fine_entry_drain_inherited_coarse_input':actual_aim_neutral_latch(pl,gp)});aim_settled_since=None;continue""",1)
 needle="   while u32(pg+0x51e4)<before+ticks:"
 repl="""   if fine:
    ack_start=before;ack_deadline=time.monotonic()+2
    while True:
     held_aim_guard(pl,gp);cf=u32(pg+0x51e4);jxy=struct.unpack('<2b',read(0x8c3a9544,2));pr=list(read(pl+0xfc,4));assert pr[0]==0 and pr[1]==6,'Ordinary RT routine changed before raw axis acknowledgment'
     want_x=-1 if 'left'in wanted else(1 if 'right'in wanted else 0);want_y=1 if 'forward'in wanted else(-1 if 'back'in wanted else 0)
     if (not want_x or jxy[0]*want_x>0) and (not want_y or jxy[1]*want_y>0):break
     assert cf-ack_start<=20 and time.monotonic()<ack_deadline,'Bounded fine raw-axis source acknowledgment timeout';time.sleep(.005)
    before=cf;until=time.monotonic()+2;events.append({'fine_raw_axis_ack_then_one_source_tick_interval':dict(host_press_frame=ack_start,ack_frame=cf,Joy_xy=jxy,Key_on=hex(struct.unpack('<Q',read(0x8c3a948c+0x10,8))[0]),keys=sorted(wanted),scope='Read-only asynchronous source interval; not proof of exactly one game execution')})
   while u32(pg+0x51e4)<before+ticks:"""
 assert needle in s;s=s.replace(needle,repl,1)
 a=s.index("    transition({'ready'});neutral_since=None;");b=s.index("   events.append({'reviewed_dominant_axis_held_correction'",a);s=s[:a]+"    neutral_receipt=actual_aim_neutral_latch(pl,gp);events.append({'actual_aim_neutral_after_correction':neutral_receipt})\n"+s[b:]
 needle="  if key_on&15:aim_settled_since=None;transition({'ready'});time.sleep(.03);continue"
 assert needle in s;s=s.replace(needle,"""  if key_on&15 or struct.unpack('<2b',read(0x8c3a9544,2))!=(0,0) or active & {'left','right','forward','back'}:
   events.append({'universal_actual_rawJoy_neutral_before_final_ray_fire':actual_aim_neutral_latch(pl,gp)});aim_settled_since=None;continue""",1)
 s=s.replace('Source-prepared until actual Flycast proof.','Source-prepared until actual Flycast proof. Independent followup source review: fine entry drains inheritedcoarse; selectedrawaxis correctsign acknowledged before one-source-tick interval with20tick/2sec bound; finalfire universallyrequiresactualJoyXY0/Keydirection0+3ticks. Read-only asynchronous interval does not prove exactlyoneexecution. ',1)
 compile(s,str(p),'exec');p.write_text(s);print(p.name,hashlib.sha256(p.read_bytes()).hexdigest())
