"""Checkpoint an explicit source-only allowlist without touching the build tree."""
from pathlib import Path
import json, os, subprocess, tempfile
repo='/root/work/lanes/world-merge23'
base='af09f0a2bfd32f2ecc29bda6a71a1de42bcf2b34'
branch='refs/heads/wip/dedup-offline23-main-20261023'
lane=Path('/mnt/c/Game Dev/Emulators/codex-lanes/dedup-offline23')
def git(*args,**kw):return subprocess.check_output(['git','-C',repo,*args],**kw).decode().strip()
subprocess.run(['git','-C',repo,'show-ref','--verify','--quiet',branch],check=False)
assert subprocess.run(['git','-C',repo,'show-ref','--verify','--quiet',branch]).returncode==1
head=git('rev-parse','HEAD');assert not git('status','--porcelain')
with tempfile.TemporaryDirectory(prefix='dedup-main-checkpoint-') as tmp:
    env=dict(os.environ,GIT_INDEX_FILE=str(Path(tmp)/'index'))
    git('read-tree',base,env=env)
    for name in ('main-build-on.sh','main-build-on-r2.sh','MAIN-QUALIFICATION.md','checkpoint-main-qualification.py'):
        content=(lane/name).read_bytes();assert len(content)<1048576 and b'\0' not in content
        blob=git('hash-object','-w','--stdin',input=content)
        dest='port/dreamcast/tools/d367/dedup_offline23/main/'+name
        git('update-index','--add','--cacheinfo',f'100644,{blob},{dest}',env=env)
    tree=git('write-tree',env=env)
    commit=git('commit-tree',tree,'-p',base,input=b'Checkpoint dedup qualification launchers and live continuation\n\nExplicit source/docs only. Preserve the active target build and failed first attempt. Host/offline counts are not console gains.\n')
    git('update-ref',branch,commit,'0'*40)
    subprocess.run(['git','-C',repo,'push','origin',branch+':'+branch],check=True)
    assert git('rev-parse','HEAD')==head and not git('status','--porcelain')
    print(json.dumps(dict(commit=commit,branch=branch,build_tree_untouched=True)))
