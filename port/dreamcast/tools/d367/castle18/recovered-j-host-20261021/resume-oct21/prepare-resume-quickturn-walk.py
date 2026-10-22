from pathlib import Path
import ast,json,hashlib
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18');src=L/'owned-window-recovered-j-r201-sealed-injury-recovery-still.py';dst=L/'owned-window-recovered-j-r201-source-ack-quickturn-walk-still.py';assert not dst.exists();s=src.read_text()
old="""   before=u32(pg+0x51e4);transition({'back','dash'});until=time.monotonic()+.25
   while (u32(pg+0x51e4)<before+2 or time.monotonic()<until)and time.monotonic()<until+1:time.sleep(.01)
   transition(set());last_quick=before;events.append({'normal_back_and_B_quickturn':True,'frame':before,'starting_yaw':yaw,'desired_angle_error':delta});time.sleep(.1);continue"""
new="""   before=u32(pg+0x51e4);transition(set());transition({'back'});until=time.monotonic()+1
   def quick_guard():
    check();life,_,ash,_=struct.unpack('<4H',read(pg+0x4fa4,8));assert life>=baseline_health[0] and ash>=baseline_health[1],'Original injury during normal quickturn'
   while True:
    quick_guard();qf=u32(pg+0x51e4);joy_y=struct.unpack('<b',read(0x8c3a9544+1,1))[0];kon=struct.unpack('<Q',read(0x8c3a948c+0x10,8))[0]
    if joy_y<=-30 and kon&2:break
    assert time.monotonic()<until and qf-before<30,'Normal Back source acknowledgment timed out';time.sleep(.005)
   events.append({'actual_normal_back_source_ack_before_B_edge':dict(frame=qf,JoyY=joy_y,source_Key_on=hex(kon))});transition({'back','dash'});until=time.monotonic()+1
   while u32(pg+0x51e4)<qf+3:quick_guard();assert time.monotonic()<until;time.sleep(.005)
   transition(set());last_quick=before;events.append({'normal_source_ack_Back_then_B_quickturn':True,'frame':before,'starting_yaw':yaw,'desired_angle_error':delta});time.sleep(.03);continue"""
assert s.count(old)==1;s=s.replace(old,new);ast.parse(s);dst.write_text(s,newline='\n')
(L/'resume-quickturn-walk-review.json').write_text(json.dumps(dict(source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),candidate_sha256=hashlib.sha256(dst.read_bytes()).hexdigest(),reason='Existing125/126 control qualification proved normal analog Back must be source-acknowledged before fresh B edge. Old generic navigation still posted both together. Extend the proven126 sequence to whole waypoint navigation; never write actor yaw or source keys.',validation='AST compile and one exact control block replacement; retains nested HP/PID/time guards; actual full route pending.'),indent=2)+'\n');print(dst)
