"""Recovery planning and read-only guards. No guest or media write entry point."""
from pathlib import Path
import hashlib,json,os

SOURCE='427784b1f48aa30742850bb5025925ab619b740e'
PARENT='7b5120956b13f1d25f50280120686a8efe45ed70f09ca14042722cb4eaa9997e'
DELTA=5*1024**3//4
AGGREGATE=13*1024**3//2
ADMIT=26*1024**3
FLOOR=24*1024**3
ON_TRACK='86d1f4107417912abc74af0e2005a3bbd79a2eed03e543721db6e022dd815dfa'
OFF_PROGRAM='e0168b780b102356c9bc3ee785753a659be6a020b1d1d3f8db92f14a90c16de5'

def require(ok,reason):
 if not ok:raise ValueError(reason)

def identity(path):
 p=Path(path)
 with p.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
 return dict(size=p.stat().st_size,sha256=digest)

def verify(path,pin):require(identity(path)==pin,'Exact file identity changed: '+str(path))

def unique_bytes(members):
 """Count aliases once only when dev/inode, length and digest all agree."""
 seen={};total=0
 for path,v in members.items():
  require(type(v['size']) is int and v['size']>=0,'Invalid length')
  require(type(v['dev']) is int and type(v['ino']) is int and v['ino']>0,'Invalid inode')
  require(type(v['nlink']) is int and v['nlink']>=1,'Invalid link count')
  require(len(v['sha256'])==64 and all(c in '0123456789abcdef' for c in v['sha256']),'Invalid digest')
  key=v['dev'],v['ino'];same=v['size'],v['sha256']
  require(key not in seen or seen[key]==same,'One inode has conflicting file identities')
  if key not in seen:seen[key]=same;total+=v['size']
 return total

def scan(roots):
 """Full read-only inventory. Missing roots and any symlink are refusals."""
 members={}
 for text in roots:
  root=Path(text)
  require(root.is_absolute() and root==root.resolve() and root.is_dir(),'Missing/noncanonical inventory root')
  for p in sorted(root.rglob('*')):
   require(not p.is_symlink(),'Symlink refused')
   if p.is_dir():continue
   require(p.is_file(),'Nonregular file refused')
   before=p.stat();v=identity(p);after=p.stat()
   require((before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns)==(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns),'File changed while hashing')
   members[str(p)]={**v,'dev':after.st_dev,'ino':after.st_ino,'nlink':after.st_nlink}
 return dict(roots=list(roots),members=members,unique_bytes=unique_bytes(members))

def unchanged(baseline,actual):
 require(set(baseline['members'])==set(actual['members']),'Baseline membership changed')
 for path,pin in baseline['members'].items():
  got=actual['members'][path]
  require(all(got[k]==pin[k] for k in ['size','dev','ino','sha256']),'Baseline byte/inode changed')
  require(got['nlink']>=pin['nlink'],'Baseline link count decreased')
 require(unique_bytes(actual['members'])==baseline['unique_bytes'],'Baseline total changed')

def bounds(baseline,current,C_free,admission=False):
 unchanged(baseline,dict(members={p:current[p] for p in baseline['members'] if p in current}))
 total=unique_bytes(current);delta=total-baseline['unique_bytes']
 require(type(C_free) is int and C_free>=(ADMIT if admission else FLOOR),'C floor/admission')
 require(0<=delta<=DELTA,'New allocation delta cap1.25GiB')
 require(total<=AGGREGATE,'Retained+new aggregate cap6.5GiB')
 return dict(baseline_unique_bytes=baseline['unique_bytes'],new_unique_bytes=delta,aggregate_bytes=total,C_free=C_free)

def binding_guard(binding):
 """UNKNOWN cannot become an allocated baseline or guest authorization."""
 require(binding['source']==SOURCE and binding['predecessor_guest_seal']==PARENT,'Wrong source/lineage')
 require(binding['state']=='FRESH_OFF_AND_ON_INDEPENDENTLY_READ_BACK','Recovery media pending')
 require(binding['old_baseline_disappearance_acknowledged'] is True,'Missing explicit recovery context')
 require(binding['restored_old_image_identity'] is False,'New OFF is not old image restoration')
 require(binding['off_build_provenance']=='RAIN_PRODUCED_DISABLED_PAYLOAD_EQUIVALENT','Invented OFF build provenance')
 require(binding['off_program_sha256']==OFF_PROGRAM,'OFF main mismatch')
 require(binding['on_track_identity']==dict(size=1024618496,sha256=ON_TRACK),'Corrected ON track mismatch')
 require(binding['all14_exact'] is True and binding['assets1697_exact'] is True and binding['IP_exact'] is True and binding['redirects6_exact'] is True,'Incomplete payload binding')
 for key in ['off_root','on_root','off_readback_path','on_readback_path']:
  require(isinstance(binding[key],str) and binding[key].startswith('/') and '..' not in Path(binding[key]).parts,'Missing exact media/readback path')
 for key in ['off_track_identity','off_readback_identity','on_readback_identity']:
  pin=binding[key];require(isinstance(pin,dict) and type(pin.get('size')) is int and pin['size']>0,'Missing actual identity')
  require(isinstance(pin.get('sha256'),str) and len(pin['sha256'])==64 and all(c in '0123456789abcdef' for c in pin['sha256']),'Missing actual SHA256')

def readback_media(binding):
 """Rehash both actual discs; receipts alone never stand in for actual files."""
 binding_guard(binding)
 for arm in ['off','on']:
  root=Path(binding[arm+'_root']);require(root.is_dir() and root==root.resolve(),'Invalid actual media root')
  verify(binding[arm+'_readback_path'],binding[arm+'_readback_identity'])
  verify(root/'track03.iso',binding[arm+'_track_identity'])
 return 'ACTUAL_TRACKS_REHASHED_PAYLOAD_AND_RECEIPT_SCHEMA_REVIEW_STILL_REQUIRED'

if __name__=='__main__':
 raise SystemExit('Preparation only: no stage or guest entry point; protected OFF readback is pending.')
