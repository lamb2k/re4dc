from pathlib import Path
import ast,json,hashlib
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18');src=L/'owned-window-recovered-j-r201-source-ack-quickturn-walk-still.py';dst=L/'owned-window-recovered-j-r201-escape-original-cycle-still.py';assert not dst.exists();s=src.read_text()
old=" started=time.monotonic();stagnation=[];escape_life=None;last_quick=-999;sword_interaction=False;baseline_health=None;input_ready_frame=None;last_input_refresh=-999;input_refreshes=0"
assert s.count(old)==1;s=s.replace(old,old+';escape_destination_reached=False;saw_lower_floor=False')
old="  if distance<tolerance and target_i==len(targets)-1:\n   transition(set());events.append({'normal_Garrador_sourceSAT_west_escape_segment_complete':True,'frame':u32(pg+0x51e4),'pos':pos,'health':[hp,ash_life]});capture_before_close();assert u.PostMessageW(hwnd,0x10,0,0);break"
new="""  if escape_destination_reached or (distance<tolerance and target_i==len(targets)-1):
   transition(set())
   if not escape_destination_reached:
    escape_destination_reached=True;events.append({'full_normal_escape_destination_reached_hold_without_further_noise':dict(frame=ff,pos=pos,health=[hp,ash_life])})
   if gpos[1]<-1500:saw_lower_floor=True
   separation=math.dist(pos,gpos);rear=samples[-1]['Garrador']['player_back_dot']
   samples[-1]['neutral_original_AI_cycle_after_full_escape']=dict(saw_lower_floor=saw_lower_floor,separation=separation)
   if separation<6500 and rear>=-600:
    events.append({'original_enemy_frontal_approach_6500_stop_after_full_escape':samples[-1]});capture_before_close();assert u.PostMessageW(hwnd,0x10,0,0);break
   if saw_lower_floor and gpos[1]>1200 and gpos[2]>-40000 and separation>7500:
    events.append({'original_lower_floor_to_upper_stair_cycle_observed_from_safe_escape':samples[-1]});capture_before_close();assert u.PostMessageW(hwnd,0x10,0,0);break
   time.sleep(.03);continue"""
assert s.count(old)==1;s=s.replace(old,new);assert s.count('while time.monotonic()-started<49:')==1;s=s.replace('while time.monotonic()-started<49:','while time.monotonic()-started<42:')
s=s.replace("'scope':'Actual J123", "'scope':'Consolidated full normal escape and neutral original enemy-cycle observation, no far aim or traversal microprobes. Actual J123")
ast.parse(s);dst.write_text(s,newline='\n')
(L/'resume-combat-escape-cycle-review.json').write_text(json.dumps(dict(source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),candidate_sha256=hashlib.sha256(dst.read_bytes()).hexdigest(),reason='Original170 sustained western burst landed three real weakpoint hits3094to2188. Consolidate the established full east escape with neutral source-cycle observation instead of unproductive far aim or staircase chase. No movement after final destination; source injury/PID/collision and6500 frontal guards remain.',validation='AST compile; exact source controller augmentation; shorter42s bound. Actual full escape plus enemy cycle pending.'),indent=2)+'\n');print(dst)
