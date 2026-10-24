from pathlib import Path
import subprocess,json,hashlib,datetime
repo='/root/work/lanes/gc-motion24';out=Path('/mnt/c/Game Dev/Emulators/codex-lanes/ROOT-INTEGRATION-PREVIEW-VIS-COMPOSE-20261024.json')
assert not out.exists()
def git(*a,data=None):return subprocess.run(['git','-C',repo,*a],input=data,capture_output=True)
def ok(*a,data=None):
 r=git(*a,data=data);assert r.returncode==0,(a,r.stdout.decode(),r.stderr.decode());return r.stdout.decode().strip()
base='fb254e82ee6f9a3d9e34d53d1d442348a46b9cf2';gc='aab201ceac0e18107f64a3212398afe916793327';vis='7eb109ea14ff3fe635e687c2e21629c3f6cfa865';compose=ok('rev-parse','7ab940cb3')
assert ok('rev-parse','HEAD')==gc and not ok('status','--porcelain')
first=ok('merge-tree','--write-tree',gc,vis).splitlines()[0]
synthetic=ok('commit-tree',first,'-p',gc,'-p',vis,data=b'Unreachable root textual integration preview; not qualified or landed.\n')
r=git('merge-tree','--write-tree',synthetic,compose)
result={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'integration':base,'gc':gc,'visibility':vis,'composition_checkpoint':compose,'gc_visibility_tree':first,'unreachable_preview_commit':synthetic,'compose_returncode':r.returncode,'compose_output':r.stdout.decode(),'stderr':r.stderr.decode(),'scope':'Creates only unreachable Git merge-tree/commit-tree objects and this receipt. No refs/worktrees/source/recipes/SDK/guest changed. Composition checkpoint is not final; textual result is not semantic/target qualification.'}
if r.returncode==0:
 tree=r.stdout.decode().splitlines()[0];result['combined_tree']=tree
 for p in ['port/dreamcast/tools/d367/rr/recipe.conf']:
  assert not ok('diff','--name-only',base,tree,'--',p)
 result['changed_vs_visibility_runtime']=ok('diff','--name-status',vis,tree,'--','port/dreamcast/game','src/game').splitlines()
assert ok('rev-parse','HEAD')==gc and not ok('status','--porcelain')
out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));print('receipt_sha256',hashlib.sha256(out.read_bytes()).hexdigest())
