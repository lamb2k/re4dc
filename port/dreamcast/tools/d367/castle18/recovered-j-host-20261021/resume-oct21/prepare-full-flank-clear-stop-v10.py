from pathlib import Path
import hashlib
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18');p=L/'owned-window-recovered-j-r201-full-flank-combat-clear-stop-v10-still.py';assert not p.exists();s=(L/'owned-window-recovered-j-r201-full-stair-flank-and-combat-v9-still.py').read_text().replace('Full flank did not complete within25s; refuse aim/combat after stopped movement','Full movement stopped or25s elapsed; refuse aim/combat until full flank and unchangedhealth');compile(s,str(p),'exec');p.write_text(s);print(p.name,hashlib.sha256(p.read_bytes()).hexdigest())
