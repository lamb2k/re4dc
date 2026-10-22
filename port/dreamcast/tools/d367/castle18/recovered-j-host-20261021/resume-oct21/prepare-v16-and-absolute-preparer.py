from pathlib import Path
import hashlib,json
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18')
p=L/'owned-window-recovered-j-r201-South-escape-bell-quiet-combat-v16-still.py';assert not p.exists()
s=(L/'owned-window-recovered-j-r201-South-escape-bell-quiet-combat-v15-still.py').read_text()
s=s.replace('while time.monotonic()-started<42:','while time.monotonic()-started<41:')
s=s.replace(' def transition(wanted):\n',' def transition(wanted):\n  if wanted:assert time.time()-(owner[\'start_filetime\']/10000000-11644473600)<41,\'41s process-age inner input deadline\'\n',1)
needle="pos=struct.unpack('<3f',read(pl+0x94,12));yaw="
a=s.index(needle,s.index('guest_started=time.monotonic()'))
s=s[:a]+s[a:].replace(needle,"pos=struct.unpack('<3f',read(pl+0x94,12));assert -2300<pos[1]<-1500 and(pos[0]>=18000 or pos[2]<=-44500),('Actual lowerfloor/region guard',pos);yaw=",1)
# Same global process clock; never reset it across bell and quiet movement.
s=s.replace('while time.monotonic()-guest_started<25:', 'while time.monotonic()-guest_started<33:')
needle="gun=next(i for i in inventory()if i['id']==0x23);assert gun['bullet']>0 and shots==0,'Exactly one ordinary bell shot maximum'"
assert s.count(needle)==1
s=s.replace(needle,"assert time.time()-(owner['start_filetime']/10000000-11644473600)<23,'Need at least10s remaining quiet movement and18s total before committing bell round';"+needle,1)
s=s.replace("assert bell_complete,'No originalbellcallback; refusequietflank/combat'","assert bell_complete,'No originalbellcallback; refusequietflank/combat'\n assert time.time()-(owner['start_filetime']/10000000-11644473600)<25,'Bellcallback too late for bounded immediate quiet/combat'",1)
s=s.replace('42sTOTALcontroller/50sexternalcap; allmovementsubset25s','41sINNER input /47.5sABSOLUTE process cap; allmovementsubset33s and bell shot must precede23s')
s=s.replace('all actualY/region/noUpperstairs','actualY/regionchecked in fast+quiet movement and heldaim/noUpperstairs')
compile(s,str(p),'exec');p.write_text(s);print(p.name,hashlib.sha256(p.read_bytes()).hexdigest())
# Additive preparer; historical profiles retain original bytes.
p=L/'prepare-recovered-j-41inner-47absolute-arm.py';assert not p.exists();s=(L/'prepare-recovered-j-bounded-arm.py').read_text();needle="compile(s,str(py),'exec');py.write_text(s,newline='\\n')";assert needle in s
replacement="s=s.replace(\"'--seconds','50'\",\"'--seconds','47'\").replace(\"'--period','10'\",\"'--period','0'\").replace('16*1024**3+128*1024**2','18*1024**3+328*1024**2')\n"+needle
s=s.replace(needle,replacement,1).replace('one existing50s guarded arm','one41sinner/47.5sabsolute guarded arm, periodic captures disabled to retain uninterrupted bell window, final owned screenshot retained')
compile(s,str(p),'exec');p.write_text(s);print(p.name)
