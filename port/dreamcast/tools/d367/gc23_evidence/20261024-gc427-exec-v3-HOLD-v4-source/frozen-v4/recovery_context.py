"""Explicit current recovery context; older source/capacity objects stay intact."""
from pathlib import Path
import hashlib,json,os,sys,types
if not __debug__:raise RuntimeError('Optimized Python refused')
HERE=Path(__file__).resolve().parent
SOURCE='427784b1f48aa30742850bb5025925ab619b740e'
PRODUCER_OFF='8ce5ee2d00027268c3e69c9c300b819c1b14c63f'
MEDIA_TOOL_SOURCE='c3dd19b999d3c36e76318a4d3825f8d1ca7310ec'
MEDIA_TOOL_SEAL='9377c8e8e06162def84513751ffe76dd78ef186bf0bef97a3ede53890eb39814'
MEDIA_TOOL_ROOT=HERE.parent.parent/'rain-diag24/qa-media-observer-ext4-v5'
OFF=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/rain-diag24-20261024/_qa-media-8ce-recovery-v4/base-off')
ON=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/gc-motion24-20261024/kos-budget-retest-media-v2/on')
FINAL=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/gc-motion24-20261024/kos-budget-retest-guest-v2')
DELTA=5*1024**3//4;AGG=13*1024**3//2;ADMIT=26*1024**3;FLOOR=24*1024**3
BASELINE_ROOTS=[
 '/mnt/c/Flycast-Evidence/re4-dreamcast/gc-motion24-20261024/qa-memory-media-aab-v1',
 '/root/probe/gc-motion24-qa-media-v1',
 '/mnt/c/Flycast-Evidence/re4-dreamcast/gc-motion24-20261024/kos-census-media-v1',
 '/root/probe/gc-motion24-kos-census-media-v1',
 *[str(HERE.parent/n) for n in ['qa-memory-media-prep','kos-census-media-prep-v1','kos-budget-retest-media-prep-v1','kos-budget-retest-media-prep-v2']],
 '/root/probe/gc-motion24-kos-budget-retest-media-v2',
 '/mnt/c/Flycast-Evidence/re4-dreamcast/gc-motion24-20261024/kos-budget-retest-media-v2',
 *[str(HERE.parent/n) for n in ['kos-budget-retest-guest-prep-v1','kos-budget-retest-guest-prep-v2','kos-budget-retest-stage-root-v1','review-kos-budget-retest-media-poststage-v1']],
 str(HERE.parent/'kos-budget-retest-guest-exec-v2'),str(HERE.parent/'kos-budget-retest-guest-exec-v3'),str(OFF)]

def need(ok,why):
 if not ok:raise RuntimeError(why)

def read(p):return json.loads(Path(p).read_bytes())

def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def row(p):return dict(size=Path(p).stat().st_size,sha256=sha(p))

def verify(p,pin):need(row(p)==pin,'Exact identity changed: '+str(p))

def total(members):
 seen={};count=0
 for p,v in members.items():
  key=v['dev'],v['ino'];value=v['size']
  need(type(value) is int and value>=0 and type(key[0]) is int and type(key[1]) is int and key[1]>0,'Invalid inode/size')
  need(key not in seen or seen[key]==value,'Conflicting length on shared inode')
  if key not in seen:seen[key]=value;count+=value
 return count

def inventory(roots,hashes=False,allow_absent=False):
 members={};digests={};absent=[]
 for text in roots:
  root=Path(text);need(root.is_absolute() and root==root.resolve() and not root.is_symlink(),'Noncanonical owned root')
  if not root.exists():
   need(allow_absent,'Owned baseline root disappeared');absent.append(text);continue
  need(root.is_dir(),'Owned root is not a directory')
  for p in sorted(root.rglob('*')):
   need(not p.is_symlink(),'Owned symlink refused')
   if p.is_dir():continue
   need(p.is_file(),'Nonregular owned file')
   a=p.stat();v=dict(size=a.st_size,dev=a.st_dev,ino=a.st_ino,nlink=a.st_nlink)
   if hashes:
    key=a.st_dev,a.st_ino
    if key not in digests:digests[key]=sha(p)
    v['sha256']=digests[key]
    b=p.stat();need((a.st_dev,a.st_ino,a.st_size,a.st_mtime_ns)==(b.st_dev,b.st_ino,b.st_size,b.st_mtime_ns),'File changed during full inventory')
   members[str(p)]=v
 return dict(roots=list(roots),members=members,unique_bytes=total(members),absent_roots=absent)

def compare_baseline(b,now,hashes=False):
 need(set(now['members'])==set(b['members']),'Current retained baseline membership changed')
 for p,v in b['members'].items():
  got=now['members'][p]
  need(all(got[k]==v[k] for k in ['size','dev','ino']),'Current retained baseline inode/size changed')
  need(got['nlink']>=v['nlink'],'Current retained baseline nlink decreased')
  if hashes:need(got['sha256']==v['sha256'],'Current retained baseline digest changed')
 need(now['unique_bytes']==b['unique_bytes'],'Current retained baseline unique total changed')

def binding_guard(j):
 need(j.get('status')=='BOUND_FRESH_RECOVERY_OFF_AND_ON_FULL_READBACK_NO_GUEST','Protected OFF/current baseline remain UNKNOWN')
 need(j['source']==SOURCE and j['off_actual_producer_source']==PRODUCER_OFF,'Wrong source/build provenance')
 need(j['off_payload_equivalence_only'] is True and j['old_image_restoration_claim'] is False,'OFF provenance/restoration relabel refused')
 need(j['off_base']==str(OFF) and j['on_base']==str(ON),'Wrong protected media roots')
 need(j['old_disappearance']['identity']['sha256']=='9409bd8b090ec545cf7e927fc68ac63266b558c4907493deabee91a0836aef85','Missing unchanged old disappearance manifest')
 need(j['baseline_path']==str(HERE/'CURRENT-BASELINE.json'),'Wrong successor baseline path')
 need(j['poststage']['path']==str(HERE.parent/'review-kos-budget-retest-media-poststage-v2/FINAL-READBACK.json'),'Wrong independent current media review')
 for k in ['baseline_identity','poststage']:
  pin=j[k]['identity'] if k=='poststage' else j[k]
  digest=pin.get('sha256','');need(type(pin.get('size')) is int and pin['size']>0 and isinstance(digest,str) and len(digest)==64 and all(ch in '0123456789abcdef' for ch in digest),'Missing actual pinned identity')

def account(baseline,now,new,free,required):
 compare_baseline(baseline,now)
 for p in set(now['members'])&set(new['members']):need(all(now['members'][p][k]==new['members'][p][k] for k in ['size','dev','ino']),'Overlapping owned path changed during accounting')
 aggregate=total({**now['members'],**new['members']});delta=aggregate-baseline['unique_bytes']
 need(required in [ADMIT,FLOOR] and type(free) is int and free>=required,'C admission/floor')
 need(0<=delta<=DELTA and aggregate<=AGG,'Explicit successor delta/aggregate capacity')
 return dict(prior_unique_bytes=baseline['unique_bytes'],new_unique_bytes=delta,aggregate_bytes=aggregate,delta_cap=DELTA,aggregate_cap=AGG,C_free=free,retained_roots=baseline['roots'],new_runtime_roots=new['roots'],absent_runtime_roots=new['absent_roots'])

def producer_guard(report,read_files=True):
 p=report['media_producer']
 need(p['tool_source']==MEDIA_TOOL_SOURCE and p['seal']['path']==str(MEDIA_TOOL_ROOT/'TOOLCHAIN-SEAL.json') and p['seal']['identity']==dict(size=8896,sha256=MEDIA_TOOL_SEAL),'Actual media producer must be frozen ext4V5, not historicalV4')
 need(p['off_complete']['path']==str(OFF/'COMPLETE.json'),'Wrong fresh OFF completion path')
 if read_files:
  verify(p['seal']['path'],p['seal']['identity']);seal=read(p['seal']['path'])
  for name,pin in seal['members'].items():verify(MEDIA_TOOL_ROOT/name,pin)
  verify(p['off_complete']['path'],p['off_complete']['identity']);complete=read(p['off_complete']['path'])
  need(complete['status']=='STAGED_READBACK_PASS_GUEST_PENDING' and complete['arm']=='off' and complete['source']==PRODUCER_OFF,'Not an actual fresh Rain-produced OFF completion')
  need(complete['tool_seal_sha256']==MEDIA_TOOL_SEAL and complete['programme']=='e0168b780b102356c9bc3ee785753a659be6a020b1d1d3f8db92f14a90c16de5','OFF programme/actual producer mismatch')
  need(complete['assets_exact'] is True and complete['all14_exact'] is True and complete['redirect_records']==6,'Incomplete producer payload readback')
  need(complete['tracks']==report['arms']['off']['tracks'],'Actual OFF completion track pins differ')

GDI='3\n1 0 4 2048 track01.iso 0\n2 756 0 2352 track02.raw 0\n3 45000 4 2048 track03.iso 0\n'
def metadata_semantics(meta):
 need(set(meta)=={'kind','tree','elf','warp_lba','pad_lba','w11_lba','fixture_bytes','gdi'},'Unexpected host base metadata fields')
 for name,value in [('warp_lba',400),('pad_lba',420),('w11_lba',440),('fixture_bytes',8192)]:need(type(meta[name]) is int and meta[name]==value,'Wrong host base fixture layout')
 need(meta['gdi']==GDI,'Wrong host base GDI/track identities')
 for name in ['kind','tree','elf']:need(isinstance(meta[name],str) and 0<len(meta[name])<=4096 and not any(c in meta[name] for c in '\0\r\n'),'Invalid host base provenance metadata')

def unique_json_pairs(pairs):
 result={}
 for key,value in pairs:need(key not in result,'Duplicate host base JSON field');result[key]=value
 return result

def host_metadata(path,track_sha256):
 """Authenticate all host fields fp_run consumes, not only the ISO payload."""
 path=Path(path);pins={}
 need(isinstance(track_sha256,str) and len(track_sha256)==64 and all(c in '0123456789abcdef' for c in track_sha256),'Missing actual track hash for host metadata')
 raw_files={}
 for name in ['base.json','track03.sha256']:
  p=path/name;need(p.is_file() and not p.is_symlink(),'Missing/nonregular host base metadata')
  before=p.stat();need(0<before.st_size<=16384,'Host base metadata length outside bound');raw=p.read_bytes();after=p.stat()
  need((before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns)==(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns),'Host metadata changed while reading')
  pins[name]=dict(size=len(raw),sha256=hashlib.sha256(raw).hexdigest());raw_files[name]=raw
 metadata_semantics(json.loads(raw_files['base.json'],object_pairs_hook=unique_json_pairs))
 need(raw_files['track03.sha256'] in [track_sha256.encode(),(track_sha256+'\n').encode(),(track_sha256+'\r\n').encode()],'Wrong host base track hash sidecar')
 return pins

def adapt(base,c):
 j=read(HERE/'RECOVERY-BINDING.json');binding_guard(j)
 verify(j['baseline_path'],j['baseline_identity']);verify(j['old_disappearance']['path'],j['old_disappearance']['identity']);verify(j['poststage']['path'],j['poststage']['identity'])
 baseline=read(j['baseline_path']);need(baseline['status']=='EXPLICIT_CURRENT_RETAINED_BASELINE_AFTER_VERIFIED_FRESH_OFF','Not a completed recovery baseline')
 need(baseline['roots']==BASELINE_ROOTS and total(baseline['members'])==baseline['unique_bytes'],'Missing/reordered explicit retained root or invalid accounting')
 need(baseline['allocation']==dict(new_delta_cap=DELTA,aggregate_cap=AGG,C_start=ADMIT,C_floor=FLOOR),'Changed successor allocation')
 # Source/capacity from the old sealed object is never modified. The namespace
 # retains only unchanged source readers and protocols, with explicit new guards.
 k=types.SimpleNamespace(**base.__dict__);k.OFF=OFF;k.FINAL=FINAL;k.DELTA=DELTA;k.AGG=AGG;k.ADMIT=ADMIT;k.FLOOR=FLOOR
 def baseline_check(links_changed=False):
  need(links_changed is True,'Only explicit current nlink-increase policy supported')
  actual=inventory(baseline['roots'],hashes=True);compare_baseline(baseline,actual,True);return baseline
 def capacity(required=FLOOR):
  now=inventory(baseline['roots']);compare_baseline(baseline,now)
  old_guest=HERE.parent/'kos-budget-retest-guest-root-review-v1';need(not old_guest.exists(),'Unallocated historical guest metadata root appeared')
  new=inventory([str(HERE),str(FINAL),*map(str,c.META_ROOTS)],allow_absent=True)
  fs=os.statvfs('/mnt/c');free=fs.f_bavail*fs.f_frsize
  return account(baseline,now,new,free,required)
 def check_poststage(g,arm,hash_tracks=True):
  need(arm in ['off','on'] and g['poststage']==j['poststage'],'Wrong current recovery poststage grant')
  verify(j['poststage']['path'],j['poststage']['identity']);report=read(j['poststage']['path'])
  need(report['status']=='CLEAR_RECOVERY_PAYLOAD_READBACK_ONLY_NO_GUEST' and report['payload_contract_source']==SOURCE,'Not independent current media CLEAR')
  producer_guard(report)
  r=report['arms'][arm];need(r['base']==str(OFF if arm=='off' else ON),'Rebound actual media root')
  need(r['actual_producer_source']==(PRODUCER_OFF if arm=='off' else SOURCE),'Rebound build provenance')
  expected=base.read(c.MEDIA/(arm.upper()+'-EXPECTED-MANIFEST.json'))
  need(r['manifest']==expected and len(r['redirect_records'])==6,'Incomplete actual payload/redirect identity')
  need(r['tracks']['track03.iso']['sha256']==('86d1f4107417912abc74af0e2005a3bbd79a2eed03e543721db6e022dd815dfa' if arm=='on' else j['off_actual_track_sha256']),'Wrong actual track identity')
  need(host_metadata(OFF if arm=='off' else ON,r['tracks']['track03.iso']['sha256'])==r['host_base_metadata'],'Host metadata differs from independent current readback')
  if hash_tracks:
   actual=media_readback(base,c,arm,OFF if arm=='off' else ON)
   need(all(actual[key]==r[key] for key in ['manifest','redirect_records','tracks']),'Fresh actual ISO/file/IP/redirect readback changed')
  return r
 k.baseline_check=baseline_check;k.capacity=capacity;k.check_poststage=check_poststage
 return k

def media_readback(base,c,arm,path):
 """Existing sealed all-file/IP/redirect reader, new explicit actual root only."""
 common,pins=base.adapter();bind=types.ModuleType('bind');bind.validate=base.validate_binding;sys.modules['bind']=bind
 rb=base.source('recovery_all_file_readback',base.OLD/'readback.py',pins['readback.py']['sha256'])
 return rb.check(arm,Path(path))
