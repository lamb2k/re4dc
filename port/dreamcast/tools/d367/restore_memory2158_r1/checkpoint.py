"""Checkpoint only this owned source unit; no checkout, private evidence or image data."""
from pathlib import Path
import hashlib,json,os,subprocess
P=Path('/mnt/c/Game Dev/Emulators/codex-lanes/world-scratch23/memory-restore2158-r1');REPO=Path('/root/probe/codex-actor-owner-witness23');PARENT='18a9db3b400721c00ab5aa3a912cbd5681547919';REF='refs/heads/codex/restore-memory2158-r1';PREFIX='port/dreamcast/tools/d367/restore_memory2158_r1'
def git(*a,env=None,data=None):return subprocess.check_output(['git','-C',str(REPO),*a],env=env,input=data)
def main():
 assert git('rev-parse','HEAD').decode().strip()==PARENT and git('status','--porcelain')==b''
 assert git('remote','get-url','--push','origin').decode().strip()=='https://github.com/lamb2k/re4dc.git'
 assert subprocess.run(['git','-C',str(REPO),'show-ref','--verify','--quiet',REF]).returncode==1
 index=P/'CHECKPOINT-INDEX.tmp';assert not index.exists();env=dict(os.environ,GIT_INDEX_FILE=str(index));rows=[]
 names=['restore.py','test_restore.py','checkpoint.py','README.md','STATUS.md','HANDBACK.md']
 try:
  git('read-tree',PARENT,env=env)
  for name in names:
   data=(P/name).read_bytes();blob=git('hash-object','-w','--stdin',data=data).decode().strip();path=PREFIX+'/'+name;git('update-index','--add','--cacheinfo','100644',blob,path,env=env);rows.append(dict(path=path,bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),blob=blob))
  tree=git('write-tree',env=env).decode().strip();commit=git('commit-tree',tree,'-p',PARENT,data=b'Checkpoint exact memory2158 restoration source and miniature path guards\n\nSource-only WIP; no private image or actual evidence data. Actual restoration and runtime admission remain pending main.\n').decode().strip();git('update-ref',REF,commit,'0'*40)
  for row in rows:assert hashlib.sha256(git('show',commit+':'+row['path'])).hexdigest()==row['sha256']
  git('push','origin',REF+':'+REF);assert git('ls-remote','origin',REF).decode().split()[0]==commit
  assert git('rev-parse','HEAD').decode().strip()==PARENT and git('status','--porcelain')==b''
  r=dict(status='OWNED_SOURCE_ONLY_WIP_CHECKPOINT_PUSHED',commit=commit,parent=PARENT,branch=REF,origin='https://github.com/lamb2k/re4dc.git',remote_readback=True,checkout_and_index_unchanged=True,source_files=rows,private_image_or_evidence_data_committed=False,actual_restore=False)
  (P/'CHECKPOINT.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items()if k!='source_files'}))
 finally:
  if index.exists():index.unlink()
if __name__=='__main__':main()
