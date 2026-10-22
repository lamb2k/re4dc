"""Prepare one bounded recovered-J arm; never launches a guest or edits a controller."""
from pathlib import Path
import hashlib,json,re,sys,math,shlex
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18');D=Path(r'C:\Flycast-Evidence\re4-dreamcast\castle18-20261018\Test21\recovered-j-content-20261021')
assert len(sys.argv)==7,'usage: newN controller.py targets_xz tolerance room_hex scope'
n=int(sys.argv[1]);controller=sys.argv[2];targets=sys.argv[3];tol=int(sys.argv[4]);room=sys.argv[5];scope=sys.argv[6]
assert re.fullmatch(r'owned-window-recovered-j-[A-Za-z0-9_-]+\.py',controller)
assert controller!='owned-window-recovered-j-r207-table-Wait-Platinum-bounded.py','Failed running-table control is not a qualified replay'
assert room in ['200','202','207','203','201','208','204']and 30<=tol<=300
points=[tuple(map(float,p.split(',')))for p in targets.split(';')];assert 1<=len(points)<=12 and all(len(p)==2 and all(math.isfinite(v)and abs(v)<100000 for v in p)for p in points)
cp=L/controller;source=cp.read_text();compile(source,str(cp),'exec');assert len(scope)<=1000 and '\n'not in scope
finished=[]
for cap in D.glob('route-walk*'):
 if cap.is_dir()and re.fullmatch(r'route-walk\d+',cap.name)and(cap/'run-result.json').exists()and(cap/'data/disc.state').exists():
  r=json.loads((cap/'run-result.json').read_text());assert r['emulator_exited'],'Finish owned guest first'
  finished.append((int(cap.name[10:]),cap))
old,seed=max(finished);assert n==old+1,('Only latest actual lineage may continue',old,n)
proof=json.loads((D/(seed.name+'-checkpoint-proof.json')).read_text());state_sha=hashlib.sha256((seed/'data/disc.state').read_bytes()).hexdigest();assert state_sha==proof['state_sha256'];assert json.loads((seed/'run-start.json').read_text())['disc_sha256']=='b67ac21eff8d819ef9ca5f0997b4c16401cb98a3d304feb65aa4b90f7affbeb6'
name=f'route-walk{n:02d}';py=L/f'run-recovered-j-{name}.py';sh=L/f'run-recovered-j-{name}.sh';receipt=L/f'recovered-j-arm{n:02d}-preparation.json'
assert all(not p.exists()for p in[py,sh,receipt,D/name,D/'segments'/name,D/(name+'-inputs.json'),D/(name+'-controller-ready.json')]),'Never overwrite prepared/actual evidence'
s=(L/'run-recovered-j-route-walk40.py').read_text();assert "cap=D/'route-walk40';seed=D/'route-walk39'"in s
s=s.replace("cap=D/'route-walk40';seed=D/'route-walk39'",f"cap=D/{name!r};seed=D/{seed.name!r}")
s,count=re.subn(r"assert state_sha=='[0-9a-f]{64}'",f'assert state_sha=={state_sha!r}',s);assert count==1
s,count=re.subn(r"targets='[^']*';controller_path=L/'[^']*'",lambda _:f'targets={targets!r};controller_path=L/{controller!r}',s);assert count==1
s,count=re.subn(r"scope='[^']*',seed=",lambda _:f'scope={scope!r},seed=',s);assert count==1
s,count=re.subn(r"str\(cap\),targets,'[0-9]+','[0-9a-f]+'",lambda _:f'str(cap),targets,{str(tol)!r},{room!r}',s);assert count==1
s,count=re.subn(r"'--name','[^']*'",lambda _:f"'--name','castle21-recoveredJ-{name}'",s);assert count==1
s=s.replace("'--seconds','50'","'--seconds','47'").replace("'--period','10'","'--period','0'").replace('16*1024**3+128*1024**2','18*1024**3+328*1024**2')
compile(s,str(py),'exec');py.write_text(s,newline='\n')
winpath=str(py);shell='set -euo pipefail\nexport TRACE_SLOTS=16 TRACE_LOCK_OWNER=castle21\nbash /root/probe/codex-castle18/port/dreamcast/tools/d367/trace_lock.sh /mnt/c/Users/lambd/AppData/Local/Programs/Python/Python312/python.exe '+shlex.quote(winpath)+'\n';sh.write_text(shell,newline='\n')
record=dict(scope='PREPARED ONLY, one41sinner/47.5sabsolute guarded arm, periodic captures disabled to retain uninterrupted bell window, final owned screenshot retained; no guest, continuous loop, new assets/program or guard change.',new_run=name,seed=seed.name,seed_sha256=state_sha,source_frame=proof['source_frame'],health=proof['health'],controller=controller,controller_sha256=hashlib.sha256(cp.read_bytes()).hexdigest(),targets=points,tolerance=tol,room=room,action=scope,driver_sha256=hashlib.sha256(py.read_bytes()).hexdigest());receipt.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))