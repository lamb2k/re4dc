from pathlib import Path
import json,hashlib,shutil,datetime
L=Path(__file__).parent;D=Path(r'C:\Flycast-Evidence\re4-dreamcast\castle18-20261018\Test21\recovered-j-content-20261021');H=Path(r'\\wsl.localhost\Ubuntu-24.04\root\probe\codex-castle18\port\dreamcast\tools\d367\castle18\controlled-script-events-20261021');cap=D/'route-walk-controlled-event003';dest=H/'controlled003';dest.mkdir(exist_ok=False);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
files=[]
for name in ['controlled-events-observer.json','run-start.json','run-result.json','owned-resource-guard.json','owned-process.json']:
 p=cap/name;shutil.copyfile(p,dest/name);files.append(dict(path=str(p),sha256=sha(p)))
p=D/'controlled-event003-closed-proof.json';shutil.copyfile(p,dest/'closed-proof.json')
for p in sorted((cap/'shots').glob('controlled-*/controlled-context.json')):
 shutil.copyfile(p,dest/(p.parent.name+'-context.json'));files.append(dict(path=str(p),sha256=sha(p),context=json.loads(p.read_text())))
for name in ['controlled-event003-warp.txt','observe-controlled-r201-event003.py','run-controlled-event003.py','run-controlled-event003.sh','prepare-controlled-event004.py','controlled-event004-warp.txt','observe-controlled-r208-event004.py','run-controlled-event004.py','run-controlled-event004.sh','extract-r208-frozen-controlled-areas.py']:
 p=L/name;shutil.copyfile(p,H/name)
p=D/'r208-frozen-selected-source-AEV-controlled-20261021.json';shutil.copyfile(p,H/p.name)
record=dict(scope='CONTROLLED TEST failure/partial. No secondary-wave or exit PASS. PriorRSF0+5 are SETUP only. Authentic127/294 preserved. No combat or hardware acceptance.',state_sha256=sha(cap/'data/disc.state'),source=518,health=[912,1440,0,600],outcome='Native goto60 reached AEV16. Primary alive cap occupied; secondary58/59/5A absent. Enemy attacks killed Ashley before A360; sourceStop80400100 prevented action, no204/208 transition. Closed under V4 bound. No replay/rollback.',visual_inspection='Secondary-region fb0 shows hall/HUD; final fb0 visibly shows Ashley collapsed. Exact source intervals and PNG hashes retained in contexts.',files=files,next='Independent controlled208 DebugTrg pressure-bypass/crank-rise then native204door fixture004 prepared, awaiting root allocation; bridge/footings/plates not exercised.',invalid_proposal='No003b created/launched. dead-list command only clears ESL alive, does not populate actual death table, so cannot assume it suppresses original primary respawn.')
(dest/'HANDBACK.json').write_text(json.dumps(record,indent=2)+'\n')
for name in ['HANDBACK.md','INBOX.md']:
 p=L/name;s=p.read_text(encoding='utf-8');p.write_text('CURRENT USER OBJECTIVE: Teleport/event coverage ACTIVE; no user input needed. No guest active. Controlled003 closed with legitimate Ashley death before exit; no secondary/transition acceptance. Independent004 fixture prepared, awaits root allocation. Authentic127/294 immutable.\n\n'+s,encoding='utf-8')
print(dest)
