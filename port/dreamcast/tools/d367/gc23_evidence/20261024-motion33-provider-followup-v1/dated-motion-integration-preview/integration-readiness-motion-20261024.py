from pathlib import Path
import subprocess,json,hashlib,datetime
repo=Path('/root/work/lanes/gc-motion24')
base='fb254e82ee6f9a3d9e34d53d1d442348a46b9cf2'
gc='aab201ceac0e18107f64a3212398afe916793327'
runtime='fce285ddd77ced898b40f49ae310b91a539b7b5d'
rain='bca44d58a1fa0a51fd87ba94deba8cba925c8998'
out=Path('/mnt/c/Game Dev/Emulators/codex-lanes/ROOT-INTEGRATION-READINESS-MOTION-20261024.json')
def git(*args):return subprocess.run(['git','-c','index.threads=1','-c','core.preloadIndex=false','-C',str(repo),*args],capture_output=True,text=True)
def checked(*args):
 r=git(*args);assert r.returncode==0,(args,r.stdout,r.stderr);return r.stdout.strip()
heads={str(p):subprocess.check_output(['git','-C',str(p),'rev-parse','HEAD'],text=True).strip() for p in [repo,Path('/root/work/lanes/water-rain24')]}
assert heads[str(repo)]==gc
for p in heads:assert not subprocess.check_output(['git','-C',p,'status','--porcelain'],text=True).strip(),p
remote=checked('ls-remote','origin','refs/heads/t15/int').split()[0];assert remote==base
for h in [gc,rain]:assert git('merge-base','--is-ancestor',base,h).returncode==0
assert not checked('diff','--name-only',runtime,gc,'--','port/dreamcast/game','src/game')
m=git('merge-tree','--write-tree',gc,rain);assert m.returncode==0,(m.stdout,m.stderr)
tree=m.stdout.splitlines()[0];assert len(tree)==40
changed=checked('diff','--name-status',gc,tree).splitlines()
assert len(changed)==8
assert checked('diff','--name-only',base,tree,'--','port/dreamcast/tools/d367/rr/recipe.conf')==''
assert checked('diff','--name-only',base,tree,'--','assets','data','DATA','port/dreamcast/assets')==''
checks={}
for name,h in [('current-gc',gc),('rain',rain)]:
 r=git('diff','--check',base,h,'--','port/dreamcast/game','src/game');assert r.returncode==0,(name,r.stdout);checks[name]=r.returncode
review=Path('/mnt/c/Game Dev/Emulators/codex-lanes/gc-port23/review-motion24/REVIEW-CLEAR.json')
r=json.loads(review.read_text());assert r['status']=='CLEAR' and r['runtime_source']==runtime
for p,h in heads.items():assert subprocess.check_output(['git','-C',p,'rev-parse','HEAD'],text=True).strip()==h;assert not subprocess.check_output(['git','-C',p,'status','--porcelain'],text=True).strip()
receipt={'status':'CURRENT_MOTION_CATALOG_RAIN_TEXTUAL_PREVIEW_CLEAR','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Writes only unreachable Git merge-tree objects and this receipt. No branch/worktree/recipe/SDK/guest mutation; not integrated qualification or landing.','integration':base,'gc_metadata_head':gc,'gc_runtime':runtime,'rain_runtime':rain,'preview_tree':tree,'rain_delta':changed,'runtime_whitespace':checks,'heads_unchanged':heads,'recipe_unchanged':True,'listed_asset_roots_unchanged':True,'motion_review_sha256':hashlib.sha256(review.read_bytes()).hexdigest(),'remaining':['Successor full programme/overlay OFF identity and ON pricing','Configured catalog and required consumer coverage','Both memory and runtime/census/gameplay gates','Producer terminal acknowledgements','Rain source/lifecycle/appearance acceptance','Physical acceptance'],'prior_preview_preserved':True}
out.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'tree':tree,'delta_files':len(changed),'receipt_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'SDK_or_guest':False}))