from pathlib import Path
import hashlib,py_compile
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18')
src=L/'owned-window-recovered-j-r201-sustained-front9000-death-first-still.py';assert hashlib.sha256(src.read_bytes()).hexdigest()=='865930f70a112f51e2def3c86c46a803fa7f983ce4c8b0a887ff06b16cf11ada';s=src.read_text()
old='   if math.hypot(pos[0]-gpos[0],pos[2]-gpos[2])<=9000:'
new="   if math.hypot(pos[0]-gpos[0],pos[2]-gpos[2])<=9000 and row['Garrador_routines'][0]!=2:"
assert s.count(old)==1;s=s.replace(old,new,1)
s=s.replace('front_facing_boss_within9000_early_disengagement_no_shot','active_front_facing_boss_within9000_early_disengagement_no_shot',1)
s=s.replace("'scope':'Resumed sustained combat:","'scope':'Resumed sustained combat:9000 front guard checks active enemy rather than original damage-routine2 pose rotation; actual shot still requires strongrear, exact ray/laser/part37. Original death branch precedes shot-pending timeout. Anyinjury/phase/PID/resource guards unchanged. Historical base:",1)
dst=L/'owned-window-recovered-j-r201-sustained-activefront9000-deathfirst-still.py';assert not dst.exists();dst.write_text(s,encoding='utf-8');py_compile.compile(str(dst),doraise=True);print(dst.name,hashlib.sha256(dst.read_bytes()).hexdigest())
