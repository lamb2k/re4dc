from pathlib import Path
import subprocess,json,hashlib,datetime
REPO=Path('/root/work/lanes/gc-port23')
OUT=Path('/mnt/c/Game Dev/Emulators/codex-lanes/ROOT-INTEGRATION-READINESS-20261024.json')
base='fb254e82ee6f9a3d9e34d53d1d442348a46b9cf2';gc='1d63cffe3a232c402418f2f2d919e7abae476957';rain='bca44d58a1fa0a51fd87ba94deba8cba925c8998'
def git(*args):return subprocess.run(['git','-C',str(REPO),*args],capture_output=True,text=True)
def checked(*args):
 r=git(*args);assert r.returncode==0,(args,r.stderr);return r.stdout.strip()
heads={str(p):subprocess.check_output(['git','-C',str(p),'rev-parse','HEAD'],text=True).strip() for p in [REPO,Path('/root/work/lanes/water-rain24')]}
for p,h in heads.items():assert not subprocess.check_output(['git','-C',p,'status','--porcelain'],text=True).strip()
remote=checked('ls-remote','origin','refs/heads/t15/int').split()[0];assert remote==base
for h in [gc,rain]:assert git('merge-base','--is-ancestor',base,h).returncode==0
m=git('merge-tree','--write-tree',gc,rain)
receipt=dict(time=datetime.datetime.now(datetime.timezone.utc).isoformat(),scope='Read-only textual integration preview of independently frozen GC and rain source. Writes only unreachable Git merge-tree objects and this receipt; no branch, working tree, recipe, SDK or guest mutation. Not an integrated qualification.',base=base,gc=gc,rain=rain,remote_current=remote,merge_exit=m.returncode,merge_stdout=m.stdout,merge_stderr=m.stderr,heads_before=heads)
assert m.returncode==0,(m.stdout,m.stderr)
tree=m.stdout.splitlines()[0];assert len(tree)==40
receipt['preview_tree']=tree
receipt['rain_delta_from_gc']=checked('diff','--name-status',gc,tree).splitlines()
receipt['runtime_whitespace_checks']={}
for label,h,paths in [('gc',gc,['port/dreamcast/game','src/game']),('rain',rain,['src/game/filter06.cpp','port/dreamcast/game/effects30.mk'])]:
 r=git('diff','--check',base,h,'--',*paths);receipt['runtime_whitespace_checks'][label]=dict(exit=r.returncode,stdout=r.stdout,stderr=r.stderr);assert r.returncode==0
receipt['notes']=['Frozen GC source is superseded for further qualification by the in-progress isolated catalog audit; do not land this preview.','Archived source-proof metadata has original CRLF/trailing bytes; preserve identities rather than silently normalizing receipts.','GC complete catalog, required consumer coverage, KOS/H2 and real producer terminal acknowledgements remain open.','Rain live lifecycle, memory and still/look acceptance remain open.','No production options were enabled. Default-off source qualification does not authorize a look change.']
for p,h in heads.items():assert subprocess.check_output(['git','-C',p,'rev-parse','HEAD'],text=True).strip()==h;assert not subprocess.check_output(['git','-C',p,'status','--porcelain'],text=True).strip()
OUT.write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(dict(preview_tree=tree,merge_exit=m.returncode,delta_files=len(receipt['rain_delta_from_gc']),runtime_whitespace='pass',receipt_sha256=hashlib.sha256(OUT.read_bytes()).hexdigest()),indent=2))