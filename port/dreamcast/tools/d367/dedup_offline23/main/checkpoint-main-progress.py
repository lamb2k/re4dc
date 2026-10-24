from pathlib import Path
import os, subprocess, tempfile, json
repo='/root/work/lanes/world-merge23'
branch='refs/heads/wip/dedup-offline23-main-20261023'
lane=Path('/mnt/c/Game Dev/Emulators/codex-lanes/dedup-offline23')
def git(*a,**k): return subprocess.check_output(['git','-C',repo,*a],**k).decode().strip()
base=git('rev-parse',branch)
assert base=='39eb8ced9bdac2f3654913e9e3952f547b2ce22b'
head=git('rev-parse','HEAD'); assert not git('status','--porcelain')
files=('main-build-controls.sh','main-stage-qa.sh','main-master-base.sh','main-build-diagnostic.sh','main-run-bounded.sh','main-run-console-r2.sh','cross-still.txt','MAIN-QUALIFICATION.md','checkpoint-main-progress.py')
with tempfile.TemporaryDirectory(prefix='dd3-progress-') as tmp:
 env=dict(os.environ,GIT_INDEX_FILE=str(Path(tmp)/'index'))
 git('read-tree',base,env=env)
 for name in files:
  content=(lane/name).read_bytes(); assert len(content)<1048576 and b'\0' not in content
  blob=git('hash-object','-w','--stdin',input=content)
  git('update-index','--add','--cacheinfo',f'100644,{blob},port/dreamcast/tools/d367/dedup_offline23/main/{name}',env=env)
 tree=git('write-tree',env=env)
 commit=git('commit-tree',tree,'-p',base,input=b'Checkpoint target OFF identity and bounded dedup qualification\n\nRecord preliminary harness mistake separately from console-mode repeats. Explicit source-only allowlist, no private assets or media.\n')
 git('update-ref',branch,commit,base)
 subprocess.run(['git','-C',repo,'push','origin',branch+':'+branch],check=True)
 assert git('rev-parse','HEAD')==head and not git('status','--porcelain')
 print(json.dumps(dict(commit=commit,branch=branch)))
