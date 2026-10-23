"""Save an explicit source-only allowlist without changing a frozen checkout."""
from pathlib import Path
import json, os, subprocess, tempfile

REPO='/root/probe/codex-actor-visibility23-integration'
LANE=Path('/mnt/c/Game Dev/Emulators/codex-lanes/actor-visibility23')
BRANCH='refs/heads/codex/actor-qualification23-support'
BASE='eea7526a0a42f12ea8b32fe07106479dc2729a4e'
DEST='port/dreamcast/tools/d367/actor_visibility23'

def git(*args, **kw):
    return subprocess.check_output(['git','-C',REPO,*args],**kw).decode().strip()

assert git('rev-parse',BRANCH)==BASE
assert not git('status','--porcelain')
head=git('rev-parse','HEAD')
files={DEST+'/'+n:LANE/n for n in ('retire-on2-generated-marker.py','checkpoint-main-resumption23.py')}
for n in ('run-proof.py','proof.sh','compile_evidence.py'):
    files[DEST+'/material23-proof-r1/'+n]=LANE/'material23-proof-r1'/n
for n in ('MAIN-MEMORY-QUALIFICATION-HANDOFF.md','STATUS.md'):
    files[DEST+'/checkpoint-20261023/'+n]=LANE/n
files[DEST+'/checkpoint-20261023/CODEX-STATUS-20261022.md']=LANE.parent/'CODEX-STATUS-20261022.md'
with tempfile.TemporaryDirectory(prefix='actor-main-checkpoint-') as tmp:
    env=dict(os.environ,GIT_INDEX_FILE=str(Path(tmp)/'index'))
    git('read-tree',BASE,env=env)
    for dest,src in sorted(files.items()):
        data=src.read_bytes()
        assert len(data)<1048576 and b'\x00' not in data
        blob=git('hash-object','-w','--stdin',input=data)
        git('update-index','--add','--cacheinfo',f'100644,{blob},{dest}',env=env)
    tree=git('write-tree',env=env)
    commit=git('commit-tree',tree,'-p',BASE,input=b'Checkpoint post-link proof tools and current resumption handoff\n\nSource-only explicit allowlist. Preserve original failed post-build receipt and all linked outputs. No private assets, binaries or captures; no runtime or physical acceptance claimed.\n')
    git('update-ref',BRANCH,commit,BASE)
    subprocess.run(['git','-C',REPO,'push','origin',BRANCH+':'+BRANCH],check=True)
    assert git('rev-parse','HEAD')==head and not git('status','--porcelain')
    print(json.dumps(dict(commit=commit,branch=BRANCH,files=list(files),frozen_head=head,frozen_clean=True),indent=2))
