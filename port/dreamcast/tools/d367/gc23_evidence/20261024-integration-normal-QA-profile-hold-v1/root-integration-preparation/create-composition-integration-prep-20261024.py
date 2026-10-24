from pathlib import Path
import subprocess,json,datetime
repo='/root/work/lanes/gc-motion24';tree=Path('/root/work/lanes/codex-composition-int24');branch='wip/codex-composition-int24-20261024';base='fb254e82ee6f9a3d9e34d53d1d442348a46b9cf2'
assert not tree.exists()
def run(*argv):
 r=subprocess.run(argv,capture_output=True,text=True);assert r.returncode==0,(argv,r.stdout[-3000:],r.stderr[-3000:]);return r.stdout.strip()
assert run('git','-C',repo,'ls-remote','origin','refs/heads/t15/int').split()[0]==base
run('git','-C',repo,'worktree','add','-b',branch,str(tree),base)
units=[('GC gate catalog Motion','aab201ceac0e18107f64a3212398afe916793327'),('effective0 visibility prerequisite','7eb109ea14ff3fe635e687c2e21629c3f6cfa865'),('PVS batch lifecycle defaultoff','b6b4fa7a3cf3a5244d28a31eae9a8bf42f18ce45'),('rain causal diagnostic defaultoff','da413ff058f88fa136375ecff629610fc59c0e51')]
rows=[]
for label,sha in units:
 assert not run('git','-C',str(tree),'status','--porcelain')
 result=run('git','-C',str(tree),'merge','--no-ff',sha,'-m','Prepare '+label+' for integrated source review; experimental defaults remain off')
 rows.append({'unit':label,'source':sha,'local_preparation_merge':run('git','-C',str(tree),'rev-parse','HEAD')})
assert not run('git','-C',str(tree),'diff','--name-only',base,'HEAD','--','port/dreamcast/tools/d367/rr/recipe.conf','assets','data','DATA','port/dreamcast/assets')
assert not run('git','-C',str(tree),'status','--porcelain')
r={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'LOCAL_INTEGRATION_PREPARATION_ONLY','base':base,'tree':str(tree),'branch':branch,'units':rows,'HEAD':run('git','-C',str(tree),'rev-parse','HEAD'),'claims':'Root only: strict cross-feature admission, selected-source integration and source/host review preparation. No SDK or guest allocation. Frozen author trees unchanged.','limits':'No integration or branch push, recipe/asset/SD/publication change, performance/heap/cut or hardware acceptance. Textual clean merges are not semantic qualification.'}
out=Path('/mnt/c/Game Dev/Emulators/codex-lanes/ROOT-COMPOSITION-INTEGRATION-PREP-20261024.json');assert not out.exists();out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
