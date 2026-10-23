"""One fresh full ON/OFF programme; main creates source tree after fresh admission."""
from pathlib import Path
import argparse,datetime,fcntl,hashlib,json,os,re,signal,subprocess,time
P=Path(__file__).resolve().parent
B=json.loads((P/'BASIS.json').read_bytes());T=Path(B['tree']);R=Path(B['work']);SOURCE=B['source'];MiB=1024**2

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def git(*args):return subprocess.check_output(['git','-C',str(T),*args],text=True).strip()
def charge(root):
 if not root.exists():return 0
 total=4096
 for base,dirs,files in os.walk(root,followlinks=False):
  for name in dirs+files:
   p=Path(base)/name;st=p.lstat();total+=4096 if p.is_dir()else (st.st_size+4095)//4096*4096
 return total

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('arm',choices=('on','off'));ap.add_argument('--resources',required=True);ap.add_argument('--resources-sha256',required=True);ap.add_argument('--release-priority-clear',action='store_true',required=True);ap.add_argument('--execute',action='store_true');a=ap.parse_args()
 resource=Path(a.resources);assert sha(resource)==a.resources_sha256
 admission=json.loads(resource.read_bytes());age=(datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat(admission['utc'].replace('Z','+00:00'))).total_seconds()
 assert 0<=age<=60 and admission['admitted']is True and not admission['errors']
 assert admission['root_cap']==16*1024**3 and admission['projected_peak']<=admission['root_cap'] and admission['successor_cap']==736*MiB
 assert admission['floor']==20468203520
 assert T.is_dir()and T.resolve()==T and R.is_dir()and R.resolve()==R
 assert git('rev-parse','HEAD')==SOURCE and git('branch','--show-current')==B['branch'] and not git('status','--porcelain')
 subprocess.run(['git','-C',str(T),'merge-base','--is-ancestor',B['parent'],SOURCE],check=True)
 remote=git('ls-remote','origin',B['source_ref']);assert remote.split()[0]==SOURCE
 for row in B['private_authority']:
  p=Path(row['path']);assert p.stat().st_size==row['bytes']and sha(p)==row['sha256']
 authority=json.loads(Path(B['private_allocation']).read_bytes())
 for row in authority['inputs']:
  p=Path(row['path']);assert p.stat().st_size==row['bytes']and sha(p)==row['sha256']
 for bucket in json.loads(Path(B['private_readback']).read_bytes()).values():
  if isinstance(bucket,list):
   for row in bucket:
    if isinstance(row,dict)and {'path','bytes','sha256'}.issubset(row):
     p=Path(row['path']);assert p.stat().st_size==row['bytes']and sha(p)==row['sha256']
 label=os.environ.get('ACTOR23_ARM_OUTPUT',a.arm)
 assert (a.arm,label)in (('on','on2'),('off','off')), 'ON successor must use ACTOR23_ARM_OUTPUT=on2'
 sdk_receipt=R/'SDK-COPY-READBACK.json'
 assert sdk_receipt.is_file(), 'Main must admit and verify retained SDK subset copy first'
 sdk=json.loads(sdk_receipt.read_bytes());assert sdk['status']=='RETAINED_SDK54_COPY_VERIFIED_SOURCE_ONLY' and sdk['source']==SOURCE
 for row in json.loads((P/'SDK-COPY-MANIFEST.json').read_bytes())['files']:
  q=T/'port/dreamcast/game/third_party/sh4zam'/row['relative'];assert q.stat().st_size==row['bytes']and sha(q)==row['sha256']
 O=R/label;marker=T/'port/dreamcast/game/obj';log=R/(label+'-build.log')
 assert not O.exists()and not marker.exists()and not marker.is_symlink()and not log.exists(), 'Preserve prior outputs; no automatic retry'
 metadata=Path(git('rev-parse','--absolute-git-dir'))
 def guard():
  src=charge(T)+charge(metadata);on=charge(R/'on')+charge(R/'on2');off=charge(R/'off');work=charge(R);tmp=sum(charge(R/x/'temp')for x in ('on','on2','off'));common=work-on-off+tmp
  assert src<=64*MiB and on<=320*MiB and off<=320*MiB and common<=32*MiB,(src,on,off,common)
  assert src+work<=736*MiB,(src,work)
  assert __import__('shutil').disk_usage('/mnt/c').free>=admission['floor']+admission['guest_peak']
  return dict(source_with_git_metadata=src,on=on,off=off,common_including_tmp=common,aggregate=src+work)
 guard()
 if not a.execute:print(json.dumps(dict(status='READ_ONLY_BUILD_READY',source=SOURCE,arm=a.arm,charge=guard(),build=False)));return
 locks=[]
 try:
  for name in ('/root/probe/d367-build.lock','/root/probe/d367-build2.lock'):
   f=open(name,'a')
   try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);locks.append(f);break
   except BlockingIOError:f.close()
  else:raise RuntimeError('NO_SHARED_SLOT; release priority/no waiting')
  f=open(R/'tree.lock','a');fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);locks.append(f)
  assert not O.exists()and not marker.exists()and not marker.is_symlink()and git('rev-parse','HEAD')==SOURCE and not git('status','--porcelain')
  assert (datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat(admission['utc'].replace('Z','+00:00'))).total_seconds()<=60, 'Refresh admission before allocation'
  O.mkdir();(O/'temp').mkdir();(O/'link-scratch').mkdir();marker.symlink_to(O/'link-scratch',target_is_directory=True)
  env=dict(os.environ,D367_SLOT_HELD='1',ACTOR23_SCRIPTS=str(P),ACTOR23_ARM_OUTPUT=label,TMPDIR=str(O/'temp'),JOBS='1')
  failure=None;proc=None
  try:
   with log.open('xb')as output:
    proc=subprocess.Popen(['bash',str(P/'build.sh'),a.arm],stdout=output,stderr=subprocess.STDOUT,env=env,start_new_session=True)
    while proc.poll()is None:guard();time.sleep(1)
    assert proc.returncode==0, 'Full build/evidence failed; preserve all outputs'
   try:os.killpg(proc.pid,0)
   except ProcessLookupError:pass
   else:raise RuntimeError('Build parent ended with remaining group processes; closing before lease release')
   guard();assert marker.is_symlink()and marker.resolve()==O/'link-scratch';marker.unlink()
   assert git('rev-parse','HEAD')==SOURCE and not git('status','--porcelain')
   (O/'FINAL-LITERAL-CLEAN.json').write_text(json.dumps(dict(source=SOURCE,clean=True,only_owned_generated_marker_retired=True,link_scratch_preserved=str(O/'link-scratch'),charge=guard(),runtime_admitted=False),indent=2)+'\n')
  except BaseException as e:
   failure=repr(e)
   if proc:
    try:os.killpg(proc.pid,signal.SIGTERM)
    except ProcessLookupError:pass
    try:proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
     os.killpg(proc.pid,signal.SIGKILL);proc.wait()
    while True:
     try:os.killpg(proc.pid,0);os.killpg(proc.pid,signal.SIGKILL)
     except ProcessLookupError:break
     time.sleep(.1)
   raise
  finally:
   (O/'RUN-RESULT.json').write_text(json.dumps(dict(source=SOURCE,arm=a.arm,output_label=label,exit_code=proc.returncode if proc else None,error=failure,build_log=str(log),runtime_admitted=False,stage=False,guest=False),indent=2)+'\n')
 finally:
  for f in reversed(locks):f.close()
if __name__=='__main__':main()
