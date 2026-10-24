"""Explicit successor allocation; all older sealed caps remain unchanged."""
from pathlib import Path
import hashlib,json,os,sys,types
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'kos-census-media-prep-v1'
SOURCE='427784b1f48aa30742850bb5025925ab619b740e'
PARENT_SEAL='812c92f2eb0ec29a41051754e16c44de87a8ea7bfeebd066da0ac41524e11a3c'
FINAL=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/gc-motion24-20261024/kos-budget-retest-media-v2')
WORK=Path('/root/probe/gc-motion24-kos-budget-retest-media-v2')
AGG=13*1024**3//2;DELTA=5*1024**3//4;ADMIT=26*1024**3;FLOOR=24*1024**3
OFF=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/gc-motion24-20261024/qa-memory-media-aab-v1/base-off')
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def row(p):return dict(size=Path(p).stat().st_size,sha256=sha(p))
def read(p):return json.loads(Path(p).read_text())
def fresh(p,j):
 with Path(p).open('x') as f:json.dump(j,f,indent=1);f.write('\n')
def verify(p,pin):assert row(p)=={'size':pin.get('size',pin.get('bytes')),'sha256':pin['sha256']},str(p)
def source(name,path,expected):
 raw=Path(path).read_bytes();assert hashlib.sha256(raw).hexdigest()==expected
 m=types.ModuleType(name);m.__file__=str(path);sys.modules[name]=m;exec(compile(raw,str(path),'exec',dont_inherit=True),m.__dict__);return m
def parent():
 assert sha(OLD/'TOOLCHAIN-SEAL.json')==PARENT_SEAL
 pins=read(OLD/'TOOLCHAIN-SEAL.json')['members']
 for n,v in pins.items():verify(OLD/n,v)
 return source('common',OLD/'common.py',pins['common.py']['sha256']),pins
def scan(roots,hashes=False):
 seen=set();files={};total=0
 for root in map(Path,roots):
  assert not root.is_symlink()
  for p in sorted(root.rglob('*')):
   assert not p.is_symlink(),str(p)
   if not p.is_file():continue
   s=p.stat();key=(s.st_dev,s.st_ino);v=dict(size=s.st_size,dev=s.st_dev,ino=s.st_ino,nlink=s.st_nlink)
   if hashes:v['sha256']=sha(p)
   files[str(p)]=v
   if key not in seen:seen.add(key);total+=s.st_size
 return total,files,seen
def baseline_check(links_changed=False):
 b=read(HERE/'BASELINE.json');_,actual,_=scan(b['roots'])
 assert set(actual)==set(b['members']),'Historical media membership changed'
 for path,pin in b['members'].items():
  got=actual[path]
  assert all(got[k]==pin[k] for k in ['size','dev','ino']),('Historical inode changed',path)
  assert got['nlink']>=pin['nlink'] if links_changed else got['nlink']==pin['nlink']
  verify(path,pin)
 return b
def capacity(required=FLOOR):
 b=read(HERE/'BASELINE.json');prior,_,seen=scan(b['roots']);delta=0
 for root in [HERE,FINAL,WORK]:
  _,files,_=scan([root])
  for pin in files.values():
   k=(pin['dev'],pin['ino'])
   if k not in seen:seen.add(k);delta+=pin['size']
 s=os.statvfs('/mnt/c');free=s.f_bavail*s.f_frsize
 assert free>=required,'C floor/admission'
 assert prior==b['unique_bytes'],'Historical baseline byte total changed'
 assert delta<=DELTA,'Successor delta1.25GiB exceeded'
 assert prior+delta<=AGG,'Historical+successor aggregate6.5GiB exceeded'
 return dict(prior_unique_bytes=prior,new_unique_bytes=delta,aggregate_bytes=prior+delta,delta_cap=DELTA,aggregate_cap=AGG,C_free=free)
def sealed():
 for n,v in read(HERE/'TOOLCHAIN-SEAL.json')['members'].items():verify(HERE/n,v)
def adapter():
 c,pins=parent();c.HERE=HERE;c.SOURCE=SOURCE;c.FINAL=FINAL;c.WORK=WORK;c.CAP=AGG;c.ADMIT=ADMIT;c.FLOOR=FLOOR
 c.owned_bytes=lambda:capacity()['aggregate_bytes'];c.bounds=lambda required=FLOOR:capacity(required);c.tool_integrity=sealed
 # Replace the original spec loader with authenticated direct source, preserving
 # official ISO semantics while never consulting adjacent unverified pyc.
 def iso():
  p=read(HERE/'BASE-PLAN.json')['official_iso_tool'];return source('official_iso_direct',Path(p['path']),p['identity']['sha256'])
 c.iso_tool=iso
 run_child=c.run_child
 def isolated_child(argv,*args,**kwargs):
  if str(argv[0])==str(c.WINPY):argv=[argv[0],'-I','-S','-B',*argv[1:]]
  return run_child(argv,*args,**kwargs)
 c.run_child=isolated_child
 return c,pins
def validate_binding(j):
 assert j['source']==SOURCE and j['target_review']['status']=='CLEAR_STATIC_TARGET_READBACK_ONLY'
 for pin in [j['terminal'],j['target_review']['receipt'],j['target_review']['readback'],j['durable_manifest']]:verify(pin['path'],pin['identity'])
 review=read(j['target_review']['receipt']['path']);assert review['verdict']=='CLEAR_STATIC_TARGET_READBACK_ONLY' and review['source']==SOURCE
 assert j['target_review']['receipt']['identity']['sha256']=='3d207941b8a91c191f8487f5a5d2553fa07cf9d262fddb50be0437bcdb972d66'
 t=read(j['terminal']['path']);assert t['complete'] and t['source']==SOURCE
 assert t['arms']['off']['reused'] and not t['arms']['off']['new_SDK']
 for arm in ['off','on']:
  a=j['arms'][arm];assert t['arms'][arm]['complete']
  files={**a['programmes'],'re4dc-game.elf':a['ELF']}
  assert set(files)==set(t['arms'][arm]['files'])
  for name,pin in files.items():verify(pin['path'],pin['identity']);assert pin['identity']=={'size':t['arms'][arm]['files'][name]['bytes'],'sha256':t['arms'][arm]['files'][name]['sha256']}
  verify(HERE/(arm.upper()+'-EXPECTED-MANIFEST.json'),a['expected'])
 assert j['arms']['off']['programmes']['program.bin']['identity']['sha256']=='e0168b780b102356c9bc3ee785753a659be6a020b1d1d3f8db92f14a90c16de5'
 return j
