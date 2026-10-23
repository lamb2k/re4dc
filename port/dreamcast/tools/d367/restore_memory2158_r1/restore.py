"""Exact e086 restoration from retained ce034+delta. WSL only, deliberate execute."""
from pathlib import Path
import argparse,contextlib,datetime,fcntl,hashlib,importlib.util,json,os,shutil,stat,time
HERE=Path(__file__).resolve().parent
CROOT=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/pvs23-20261022')
STAGE=CROOT/'scratch23-2158baff-memory-q01';BASE=CROOT/'actor23-10395a10-on-q01/base/track03.iso'
TARGET=STAGE/'base/track03.iso';TEMP=TARGET.with_name('.track03.restore-e086-r1.tmp');RESULT=TARGET.with_name('restore-e086-r1-result.json')
ARCHIVE=STAGE/'iso-delta-actor-ce034';MANIFEST=ARCHIVE/'delta/manifest.json';BLOB=ARCHIVE/'delta/changed-blocks.bin'
SIZE=1028859904;TARGET_SHA='e0860b747b84fb10edc2db7ee66d0e91b42479fd201d2c80305cd8bfc1ef013b'
BASE_SIZE=1028911104;BASE_SHA='ce034ff75d5c6eb125a5036b5c55afa1805de1beac75711cd41b73f366d854ad'
ROOT_CAP=16*1024**3;PACKAGE_CAP=3758096384;FLOOR=20468203520;GUEST=60*1024**2;META=256*1024
LOCKS=(Path('/root/probe/lanes/world-scratch23-integration/tree.lock'),Path('/root/probe/pvs23-package-20261022-v1/.pvs23-package.lock'))
def require(ok,msg):
 if not ok:raise ValueError(msg)
def sha(path):
 with Path(path).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def token(s):return s.st_dev,s.st_ino,s.st_size,s.st_mode,s.st_mtime_ns,s.st_ctime_ns
def object_id(s):return s.st_dev,s.st_ino,stat.S_IFMT(s.st_mode)
def canonical(path):
 p=Path(path);require(p.is_absolute()and p.resolve()==p and not p.is_symlink(),'literal canonical path required: '+str(p));return p
class Directory:
 """Retain every ancestor; named and DFD views must still name the same objects."""
 def __init__(self,path):
  self.path=canonical(path);self.rows=[]
  try:
   for p in (*reversed(self.path.parents),self.path):
    fd=os.open(p,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW);s=os.fstat(fd);require(stat.S_ISDIR(s.st_mode),'directory required');self.rows.append((p,fd,object_id(s)))
   self.fd=self.rows[-1][1];self.check()
  except BaseException:self.close();raise
 def check(self):
  require(self.path.resolve()==self.path,'directory ancestor alias/rename')
  for p,fd,before in self.rows:
   require(object_id(os.fstat(fd))==before==object_id(os.stat(p,follow_symlinks=False)),'literal parent/DFD identity changed: '+str(p))
 def anchored(self,name):return Path('/proc/self/fd')/str(self.fd)/name
 def close(self):
  for _,fd,_ in reversed(self.rows):os.close(fd)
  self.rows=[]
 def __enter__(self):return self
 def __exit__(self,*a):self.close()
class Input:
 def __init__(self,path,size):
  self.path=canonical(path);self.directory=Directory(self.path.parent);self.fd=None
  try:
   self.fd=os.open(self.path.name,os.O_RDONLY|os.O_NOFOLLOW,dir_fd=self.directory.fd);s=os.fstat(self.fd);require(stat.S_ISREG(s.st_mode)and s.st_size==size,'input exact regular extent');self.before=token(s);self.check()
  except BaseException:self.close();raise
 def check(self):
  self.directory.check();require(token(os.fstat(self.fd))==self.before==token(os.stat(self.path.name,dir_fd=self.directory.fd,follow_symlinks=False))==token(os.stat(self.path,follow_symlinks=False)),'retained input/named path changed')
 @property
 def anchored(self):return self.directory.anchored(self.path.name)
 def close(self):
  if self.fd is not None:os.close(self.fd);self.fd=None
  self.directory.close()
 def __enter__(self):return self
 def __exit__(self,*a):self.close()
def absent(directory,name):
 try:os.stat(name,dir_fd=directory.fd,follow_symlinks=False)
 except FileNotFoundError:return
 raise FileExistsError('Preserve existing owned name; no overwrite/retry: '+name)
def named_writer(directory,name,writer):
 s=os.fstat(writer.fileno());require(stat.S_ISREG(s.st_mode),'regular owned writer');require(token(os.stat(name,dir_fd=directory.fd,follow_symlinks=False))==token(s)==token(os.stat(directory.path/name,follow_symlinks=False)),'owned writer/DFD/literal file differ');return s
def publish(directory,temp_name,target_name,writer,event=lambda _:None):
 directory.check();absent(directory,target_name);before=named_writer(directory,temp_name,writer);require(before.st_nlink==1,'owned temporary has an unexpected extra link');event('BEFORE_EXCLUSIVE_LINK')
 directory.check();named_writer(directory,temp_name,writer)
 os.link(temp_name,target_name,src_dir_fd=directory.fd,dst_dir_fd=directory.fd,follow_symlinks=False)
 # Linking changes ctime/nlink; compare the current complete file token across all views.
 directory.check();current=named_writer(directory,target_name,writer);require(object_id(current)==object_id(before)and current.st_size==before.st_size and current.st_nlink==2,'publication changed file inode/extent/link count');named_writer(directory,temp_name,writer);os.fsync(directory.fd);event('LINK_VERIFIED_LITERAL_SAME_INODE')
 directory.check();named_writer(directory,target_name,writer);named_writer(directory,temp_name,writer)
 os.unlink(temp_name,dir_fd=directory.fd);os.fsync(directory.fd)
 directory.check();require(named_writer(directory,target_name,writer).st_nlink==1,'published target has an unexpected extra link');return object_id(os.fstat(writer.fileno()))
def admission(r,now=None):
 now=now or datetime.datetime.now(datetime.timezone.utc);age=(now-datetime.datetime.fromisoformat(r['utc'].replace('Z','+00:00'))).total_seconds()
 require(0<=age<=60 and r.get('admitted')is True and r.get('package_one_guest_admitted')is True and not r.get('errors'),'fresh successful root/future guest admission required')
 require(r['root_cap']==ROOT_CAP and r['package_cap']==PACKAGE_CAP and r['floor']==FLOOR and r['guest_peak']==GUEST,'fixed root/package/future guest contract')
 # Root projected_peak already contains its future guest reservation. Package_current does not.
 require(r['projected_peak']+SIZE+META<=ROOT_CAP and r['package_current_bytes']+SIZE+META+GUEST<=PACKAGE_CAP,'one ISO+256KiB+future guest exceeds admitted root/package')
 require(r['c_free']>=FLOOR+SIZE+META+GUEST,'C floor/one ISO/metadata/future guest absent')
 require(any(CROOT.is_relative_to(Path(x['path']))for x in r['roots']),'root receipt does not cover evidence tree')
def read_json(path,pin):
 path=canonical(path);require(path.stat().st_size<=2*1024**2 and sha(path)==pin,'small JSON pin differs');return json.loads(path.read_text(encoding='utf-8-sig'))
def unit(path,pin):
 box=canonical(path);seal=read_json(box/'SOURCE-SEAL.json',pin)
 for name,row in seal['files'].items():
  q=box/name;require(q.parent==box and q.stat().st_size==row['bytes']and sha(q)==row['sha256']and not q.is_symlink(),'sealed immutable source differs')
def load_core():
 root=HERE.parent;box=root/'memory-archive2158';unit(box,'d77bcc4cea0e026b956ba7ff5daef3c3960938410c275aa0967469b385e4bfb2');unit(root/'recovery-native-base','6ac95b80291fbd1ac5ab173f01e96602c68a75d1e4b6aa0d535834c6986bf080')
 spec=importlib.util.spec_from_file_location('retained_memory2158_archive_core',box/'archive_core.py');core=importlib.util.module_from_spec(spec);spec.loader.exec_module(core);return core

def metadata():
 rows=json.loads((HERE/'INPUTS.json').read_text())['files'];data={}
 for r in rows:data[r['path']]=read_json(r['path'],r['sha256']);require(Path(r['path']).stat().st_size==r['bytes'],'metadata size changed')
 m=data[str(MANIFEST)];require((m['base'],m['base_size'],m['base_sha256'],m['target_size'],m['target_sha256'],m['blob']['path'],m['blob']['size'],m['blob']['sha256'])==(str(BASE),BASE_SIZE,BASE_SHA,SIZE,TARGET_SHA,str(BLOB),4532224,'9b1f021daf760930c83d819ce2c638c02181c3bd7087f1d09ad97f790b9c978e'),'fixed original delta/base/target binding')
 require(m['status']=='EXACT_CLOSED_STAGE_ACTOR_BASE_LOSSLESS_DELTA'and m['restored_sha256']==TARGET_SHA and m['every_restored_byte_compared_to_recovered_target']is True,'original full replay evidence absent')
 require(data[str(STAGE/'stage-receipt.json')]['members']['track03.iso']==dict(size=SIZE,sha256=TARGET_SHA),'old fade stage target binding')
 return m

def stream_to_writer(core,recovery,base,blob,manifest,writer,guard=lambda:None):
 total=0
 for raw in core.iter_restored(recovery,base,manifest,blob,guard):
  require(type(raw)is bytes and 0<len(raw)<=65536,'original bounded stream block');total+=len(raw);require(total<=manifest['target_size']and writer.write(raw)==len(raw),'exact bounded write required')
 require(total==manifest['target_size'],'full restore extent required');writer.flush();os.fsync(writer.fileno());guard()
 writer.seek(0);h=hashlib.sha256()
 while raw:=writer.read(1024**2):h.update(raw);guard()
 require(h.hexdigest()==manifest['target_sha256'],'independent written target full readback failed');return h.hexdigest()

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execute',action='store_true')
 for n in ('root-admission','review'):p.add_argument('--'+n,type=Path);p.add_argument('--'+n+'-sha256')
 p.add_argument('--source-seal-sha256');a=p.parse_args()
 if not a.execute:print(json.dumps(dict(status='SOURCE_ONLY_NOT_EXECUTED',base=str(BASE),target=str(TARGET),target_sha256=TARGET_SHA,one_image_bytes=SIZE,metadata_reserve=META,future_guest_reserve=GUEST)));return
 require(os.name=='posix'and str(HERE).startswith('/mnt/c/'),'WSL literal C source required');require(all((a.root_admission,a.root_admission_sha256,a.review,a.review_sha256,a.source_seal_sha256)),'explicit reviewed source and main resource admission required')
 seal=read_json(HERE/'SOURCE-SEAL.json',a.source_seal_sha256)
 for name,r in seal['files'].items():
  q=HERE/name;require(q.parent==HERE and q.stat().st_size==r['bytes']and sha(q)==r['sha256']and not q.is_symlink(),'current restore unit changed')
 review=read_json(a.review,a.review_sha256);require(review.get('status')=='CLEAR'and review.get('restore_source_seal_sha256')==a.source_seal_sha256,'exact independent restore source review required')
 core=load_core();manifest=metadata();recovery=core.load_recovery();recovery.validate_delta(manifest,manifest['blob']['size'])
 with contextlib.ExitStack()as stack:
  leases=[]
  for path in LOCKS:
   lease=stack.enter_context(Input(path,canonical(path).stat().st_size));fcntl.flock(lease.fd,fcntl.LOCK_EX|fcntl.LOCK_NB);lease.check();leases.append(lease)
  directory=stack.enter_context(Directory(TARGET.parent))
  for path in (TARGET,TEMP,RESULT):absent(directory,path.name)
  resource=read_json(a.root_admission,a.root_admission_sha256);admission(resource)
  # No large input stat/open is reachable before deliberate execute+review+leases+admission.
  base=stack.enter_context(Input(BASE,BASE_SIZE));blob=stack.enter_context(Input(BLOB,manifest['blob']['size']))
  record=dict(status='STARTED_UNPUBLISHED',source_seal_sha256=a.source_seal_sha256,review_sha256=a.review_sha256,root_admission_sha256=a.root_admission_sha256,base=str(BASE),target=str(TARGET),temporary=str(TEMP),target_bytes=SIZE,events=[],published=False,source_media_modified=False,stage_fade_modified=False,case_results_modified=False,runtime_acceptance=False)
  fd=os.open(RESULT.name,os.O_RDWR|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=directory.fd);receipt=stack.enter_context(os.fdopen(fd,'w+'));directory.check();named_writer(directory,RESULT.name,receipt)
  def save():
   raw=json.dumps(record,indent=2)+'\n';require(len(raw.encode())<=32768,'receipt metadata bound');receipt.seek(0);receipt.write(raw);receipt.truncate();receipt.flush();os.fsync(receipt.fileno())
  writer=None
  def guard():
   directory.check();base.check();blob.check()
   for lease in leases:lease.check()
   used=0 if writer is None else os.fstat(writer.fileno()).st_size;require(used<=SIZE,'single owned image extent exceeded')
   require(shutil.disk_usage(directory.path).free>=FLOOR+GUEST+META+max(0,SIZE-used),'C floor/future guest/remaining image reservation lost')
  def event(name):record['events'].append(name);save()
  started=time.monotonic();save()
  try:
   guard();fd=os.open(TEMP.name,os.O_RDWR|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=directory.fd)
   with os.fdopen(fd,'w+b')as writer:
    directory.check();named_writer(directory,TEMP.name,writer)
    # Proc paths are aliases through our held source parent DFDs. Original core
    # reopens only these anchored directories; literal names/descriptors are rechecked.
    actual=stream_to_writer(core,recovery,base.anchored,blob.anchored,manifest,writer,guard);event('ORIGINAL_STREAM_AND_FULL_WRITTEN_TARGET_HASH_VERIFIED')
    metadata();require(sha(a.root_admission)==a.root_admission_sha256,'resource receipt changed');guard()
    record['published_inode']=publish(directory,TEMP.name,TARGET.name,writer,event);record['published']=True;guard();published_stamp=token(os.fstat(writer.fileno()))
   directory.check();base.check();blob.check();require(token(os.stat(TARGET,follow_symlinks=False))==published_stamp,'final literal target changed')
   record.update(status='EXACT_E086_RESTORED_NO_RUNTIME_ACCEPTANCE',restored_sha256=actual,full_written_target_readback=True,elapsed_seconds=time.monotonic()-started);save();directory.check();named_writer(directory,RESULT.name,receipt);require(token(os.stat(TARGET,follow_symlinks=False))==published_stamp,'literal target changed after result');print(json.dumps(record))
  except BaseException as e:
   record.update(status='FAILED_PRESERVED_NO_ACCEPTANCE',error=repr(e),elapsed_seconds=time.monotonic()-started);save();raise
if __name__=='__main__':main()
