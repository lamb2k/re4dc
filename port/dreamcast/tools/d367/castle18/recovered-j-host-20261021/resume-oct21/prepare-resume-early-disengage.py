from pathlib import Path
import ast,hashlib,json
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18')
src=L/'owned-window-recovered-j-r201-sealed-health-far-track-weakpoint-still.py'
dst=L/'owned-window-recovered-j-r201-one-hit-early-disengage-still.py';assert not dst.exists()
s=src.read_text()
old="   if hits>=6 or shots>=6:events.append({'bounded_six_shot_or_hit_segment_complete':dict(row)});capture_before_close();assert u.PostMessageW(hwnd,0x10,0,0);break"
new="   if hits>=1 or shots>=1:transition(set());events.append({'confirmed_hit_immediate_disengagement_checkpoint':dict(row)});capture_before_close();assert u.PostMessageW(hwnd,0x10,0,0);break"
assert s.count(old)==1;s=s.replace(old,new)
old="if math.hypot(pos[0]-gpos[0],pos[2]-gpos[2])<=3500:"
assert s.count(old)==1;s=s.replace(old,"if math.hypot(pos[0]-gpos[0],pos[2]-gpos[2])<=6500:")
s=s.replace("front_facing_boss_within3500_close_without_shot","front_facing_boss_within6500_early_disengagement_no_shot")
s=s.replace("'scope':'Actual recovered83", "'scope':'Host-only resumed control: immediate first confirmed hit checkpoint and stronger6500 front-facing disengagement. Actual recovered83")
ast.parse(s);dst.write_text(s,newline='\n')
(L/'resume-early-disengagement-source-review.json').write_text(json.dumps(dict(source=str(src),source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),candidate=str(dst),candidate_sha256=hashlib.sha256(dst.read_bytes()).hexdigest(),reason='Actual130 source charge killed220HP Leon after129 controller waited through enemy stair descent. Stop immediately after first confirmed weakpoint damage, and twice the former frontal range, preserving actual damage/death and all source ray/laser/health/PID guards. No gameplay writes or game source change.',validation='AST compile and exactly one replacement of each original control predicate; actual Flycast use pending.'),indent=2)+'\n')
print(dst)
