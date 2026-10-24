from pathlib import Path
import os, subprocess, tempfile, json
repo='/root/work/lanes/world-merge23'
branch='refs/heads/wip/dedup-offline23-main-20261023'
lane=Path('/mnt/c/Game Dev/Emulators/codex-lanes/dedup-offline23')
def git(*a,**k): return subprocess.check_output(['git','-C',repo,*a],**k).decode().strip()
base=git('rev-parse',branch)
assert base=='40a2bc15f3ef819ff92f25db8d3c249ff04a8303'
head=git('rev-parse','HEAD'); assert not git('status','--porcelain')
files=('main-look-f330-r3.sh','cross-f330.txt','farm-f330.txt','forest-f330.txt','compare-look-f330.py','main-master-diagnostic.sh','main-run-gate.sh','main-judge-census.sh','judge-kos-fight.py','judge-gdemu-identity.py','main-prepare-current.sh','main-build-current-on.sh','main-full-h2-approved.sh','judge-full-h2.py','MAIN-QUALIFICATION.md','checkpoint-main-gates.py')
with tempfile.TemporaryDirectory(prefix='dd3-progress-') as tmp:
 env=dict(os.environ,GIT_INDEX_FILE=str(Path(tmp)/'index'))
 git('read-tree',base,env=env)
 for name in files:
  content=(lane/name).read_bytes(); assert len(content)<1048576 and b'\0' not in content
  blob=git('hash-object','-w','--stdin',input=content)
  git('update-index','--add','--cacheinfo',f'100644,{blob},port/dreamcast/tools/d367/dedup_offline23/main/{name}',env=env)
 tree=git('write-tree',env=env)
 commit=git('commit-tree',tree,'-p',base,input=b'Checkpoint dedup image, memory and full-route qualification helpers\n\nFull H2 playback and unchanged matched heap observed; historical94KB baseline not yet established. Current integration is prepared separately. Explicit source-only allowlist, no private assets/media.\n')
 git('update-ref',branch,commit,base)
 subprocess.run(['git','-C',repo,'push','origin',branch+':'+branch],check=True)
 assert git('rev-parse','HEAD')==head and not git('status','--porcelain')
 print(json.dumps(dict(commit=commit,branch=branch)))
