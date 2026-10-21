from pathlib import Path
import ast,hashlib,json
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18');src=L/'owned-window-recovered-j-r201-Green-Herb-use-still.py';dst=L/'owned-window-recovered-j-r201-Green-Herb-use-window-ready-still.py';assert not dst.exists()
s=src.read_text();old=" assert u.EnumWindows(enum,0)and len(found)==1,('owned window lookup failed',found);hwnd=found[0];base=None"
new=""" window_deadline=time.monotonic()+5
 while not found:
  check();assert time.monotonic()<window_deadline,'Exact owned SDL window was not ready within5s';assert u.EnumWindows(enum,0)
  if not found:time.sleep(.025)
 assert len(found)==1,('owned window lookup failed',found);hwnd=found[0];base=None"""
assert s.count(old)==1;s=s.replace(old,new);ast.parse(s);dst.write_text(s,newline='\n')
(L/'resume-herb-window-ready-review.json').write_text(json.dumps(dict(source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),candidate_sha256=hashlib.sha256(dst.read_bytes()).hexdigest(),defect='Actual133 controller enumerated once before exact owned SDL window existed; zero inputs, health903 unchanged, guest harness exited at recorded49.968s. No healing pass.',repair='Bounded5s PID+path+start-time-checked window readiness, using existing owned enumeration. Every other herb inventory and health predicate unchanged.',validation='AST compile; one exact startup predicate replacement; runtime pending.'),indent=2)+'\n')
print(dst)
