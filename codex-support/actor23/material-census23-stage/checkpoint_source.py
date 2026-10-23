"""Checkpoint only owned source through a temporary index; frozen checkout untouched."""
from pathlib import Path
import os,subprocess
REPO='/root/probe/codex-actor-owner-witness23'
SOURCE='f2405bb06ebaff6e2a7681479d5308ec5d3b988a'
BRANCH='refs/heads/codex/material-census23-support'
LANE=Path('/mnt/c/Game Dev/Emulators/codex-lanes/actor-visibility23')
INDEX=LANE/'material-census23-stage/.source-index'
def main():
 if os.name=='nt':raise SystemExit('Run this source-only checkpoint under WSL')
 if INDEX.exists():raise ValueError('prior temporary index exists; preserve')
 def git(*args,input=None,env=None):return subprocess.check_output(['git','-C',REPO,*args],input=input,env=env).decode().strip()
 before=git('status','--porcelain');head=git('rev-parse','HEAD')
 prior=subprocess.run(['git','-C',REPO,'rev-parse','--verify',BRANCH],capture_output=True,text=True)
 parent=prior.stdout.strip() if prior.returncode==0 else SOURCE
 env=dict(os.environ,GIT_INDEX_FILE=str(INDEX))
 try:
  git('read-tree',parent,env=env)
  rows=[]
  for name in ('material-census23-stage','material-census23-run'):
   for path in sorted((LANE/name).rglob('*')):
    if not path.is_file() or '__pycache__' in path.parts or path.name in ('.source-index','HOST-TEST-RESULTS.json','STATUS.md','HANDBACK.md','ADAPTATION.json','adapt_sources.py'):continue
    target='codex-support/actor23/'+path.relative_to(LANE).as_posix()
    blob=git('hash-object','-w','--stdin',input=path.read_bytes())
    rows.append('100644 '+blob+'\t'+target+'\n')
  git('update-index','--index-info',input=''.join(rows).encode(),env=env)
  tree=git('write-tree',env=env)
  commit=git('commit-tree',tree,'-p',parent,input=b'Add source-only corrected material census support; external review pins pending\n')
  git('update-ref',BRANCH,commit,parent if prior.returncode==0 else '0'*40)
  git('push','origin',BRANCH+':'+BRANCH)
  if git('status','--porcelain')!=before or git('rev-parse','HEAD')!=head:raise ValueError('frozen checkout changed')
  print(commit)
 finally:
  if INDEX.exists():INDEX.unlink()
if __name__=='__main__':main()
