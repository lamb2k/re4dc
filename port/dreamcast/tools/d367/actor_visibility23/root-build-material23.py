from pathlib import Path
import argparse,datetime,fcntl,hashlib,json,subprocess,sys
L=Path('/mnt/c/Game Dev/Emulators/codex-lanes/actor-visibility23')
P=L/'build-eligibility-witness23'
SOURCE='f2405bb06ebaff6e2a7681479d5308ec5d3b988a'
BASE='f1a6807c7324260c664fa1ca3d33d4b60a62712a'
REPO=Path('/root/probe/codex-actor-owner-witness23')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def git(repo,*args,**kw):return subprocess.check_output(['git','-C',str(repo),*args],**kw)
def main():
 a=argparse.ArgumentParser();a.add_argument('--resources',required=True);a.add_argument('--resources-sha256',required=True);args=a.parse_args()
 resource=Path(args.resources)
 if sha(resource)!=args.resources_sha256:raise ValueError('Resource receipt changed')
 r=json.loads(resource.read_bytes())
 age=(datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat(r['utc'])).total_seconds()
 if not(0<=age<=60 and r['admitted'] and not r['errors'] and r['successor_cap']==736*1024**2):raise ValueError('Fresh successor allocation required')
 review=L/'review/MATERIAL-ROUTE23-RUNTIME-REVIEW-CLEAR.json'
 if sha(review)!='40e8ea30bf372c43d5818754551e9e9b3814b6e0c4c897dbcebd53c68d86ccda':raise ValueError('Exact runtime source review required')
 runtime=['coarse_actor_owner_ganado.inc','platform/native_actor_fast.cpp','platform/actor_visibility23.cc','platform/include/actor_visibility23.h','platform/include/actor_visibility23_material.h','platform/include/actor_visibility23_witness.h']
 subprocess.run(['git','-C',str(REPO),'diff','--exit-code',BASE,SOURCE,'--',*['port/dreamcast/game/'+p for p in runtime]],check=True)
 b=json.loads((P/'BASIS.json').read_bytes());T=Path(b['tree']);R=Path(b['work'])
 if b['source']!=SOURCE or T.exists() or R.exists():raise ValueError('Fresh exact source/output roots required')
 R.mkdir(parents=True)
 lock=(R/'tree.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 try:
  subprocess.run(['git','-C',str(REPO),'worktree','add','--no-checkout','-b',b['branch'],str(T),SOURCE],check=True)
  old=Path('/root/probe/codex-actor-visibility23-integration')
  patterns=git(old,'rev-parse','--git-path','info/sparse-checkout').decode().strip()
  sparse=Path(patterns)
  if not sparse.is_absolute():sparse=old/sparse
  subprocess.run(['git','-C',str(T),'sparse-checkout','set','--no-cone','--stdin'],input=sparse.read_bytes(),check=True)
  subprocess.run(['git','-C',str(T),'checkout',b['branch']],check=True)
  if git(T,'rev-parse','HEAD').decode().strip()!=SOURCE or git(T,'status','--porcelain').strip():raise ValueError('New source not exactly clean')
  (R/'MAIN-PREPARATION.json').write_text(json.dumps(dict(source=SOURCE,resource=str(resource),resource_sha256=args.resources_sha256,source_tree=str(T),preserved_source=str(REPO),guest=False),indent=2)+'\n')
 finally:lock.close()
 subprocess.run([sys.executable,'-B',str(P/'run.py'),'on','--resources',str(resource),'--resources-sha256',args.resources_sha256,'--release-priority-clear','--execute'],check=True)
if __name__=='__main__':main()