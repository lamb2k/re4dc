from pathlib import Path
import ast,hashlib,json
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18');src=L/'owned-window-recovered-j-r201-sealed-health-far-track-weakpoint-still.py';dst=L/'owned-window-recovered-j-r201-sustained-early-disengage-still.py';assert not dst.exists()
s=src.read_text();old='if math.hypot(pos[0]-gpos[0],pos[2]-gpos[2])<=3500:';assert s.count(old)==1;s=s.replace(old,'if math.hypot(pos[0]-gpos[0],pos[2]-gpos[2])<=6500:').replace('front_facing_boss_within3500_close_without_shot','front_facing_boss_within6500_early_disengagement_no_shot')
assert s.count('while time.monotonic()-started<46:')==1;s=s.replace('while time.monotonic()-started<46:','while time.monotonic()-started<42:')
s=s.replace("'scope':'Actual recovered83", "'scope':'Resumed sustained combat: unchanged6shot/hit unit, stronger6500 frontal disengagement and shorter42s controller bound. Actual recovered83")
ast.parse(s);dst.write_text(s,newline='\n')
(L/'resume-sustained-combat-review.json').write_text(json.dumps(dict(source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),candidate_sha256=hashlib.sha256(dst.read_bytes()).hexdigest(),reason='129 got genuine hit but3500 frontal checkpoint left no escape time at220HP.145 immediatehit and146 escape passed1200/90. Keep known six-shot sustained combat unit with6500 early frontal checkpoint; shorten host bound42s to preserve launch/screenshot headroom.',unchanged=['Source actual ray and laser weakpoint37 predicates','Strong rear and stable target guards','Any injury stop','Exact PID path start-time identity','Original damage/death callback semantics','Original max6 shots/hits'],validation='AST compile and exactly two guard changes; runtime pending.'),indent=2)+'\n')
print(dst)
