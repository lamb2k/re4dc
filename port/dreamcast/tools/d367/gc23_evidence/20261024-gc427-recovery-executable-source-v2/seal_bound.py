"""After real root handback, seal current bindings for separate guest review.

No SDK, staging or guests. An approved guest grant is never written here.
"""
from pathlib import Path
import hashlib,json,sys,types
HERE=Path(__file__).resolve().parent
def row(p):
 with Path(p).open('rb') as f:d=hashlib.file_digest(f,'sha256').hexdigest()
 return dict(size=Path(p).stat().st_size,sha256=d)
def read(p):return json.loads(Path(p).read_bytes())
def fresh(n,j):
 with (HERE/n).open('x') as f:json.dump(j,f,indent=1);f.write('\n')
def load(name,path):
 m=types.ModuleType(name);m.__file__=str(path);sys.modules[name]=m;exec(compile(Path(path).read_bytes(),str(path),'exec',dont_inherit=True),m.__dict__);return m
if __name__=='__main__':
 if not (__debug__ and sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode):raise SystemExit('Isolated nonoptimized source only')
 for name,pin in read(HERE/'SOURCE-REVIEW-SEAL.json')['members'].items():
  if row(HERE/name)!=pin:raise SystemExit('Reviewed source changed')
 c=load('guest_common',HERE/'common.py');r=load('recovery_context',HERE/'recovery_context.py')
 for name,pin in read(c.MEDIA/'TOOLCHAIN-SEAL.json')['members'].items():c.verify(c.MEDIA/name,pin)
 if c.sha(c.MEDIA/'TOOLCHAIN-SEAL.json')!=c.MEDIA_SEAL:raise SystemExit('Old reader source changed')
 base=load('bound_stage_core',c.MEDIA/'core.py');k=r.adapt(base,c)
 binding=read(HERE/'RECOVERY-BINDING.json');g=read(HERE/'ROOT-GUEST-GRANT-TEMPLATE.json');g['poststage']=binding['poststage']
 if g['approved'] is not False or (HERE/'attempts').exists():raise SystemExit('Not a fresh unallocated kit')
 for arm in ['off','on']:k.check_poststage(g,arm)
 k.baseline_check(links_changed=True);resources=k.capacity(k.ADMIT)
 for i in range(4):c.check_fresh(c.case(i,k))
 c.check_inputs(g,k)
 for root in c.META_ROOTS:
  g['metadata_allowlists'][str(root)]=sorted(p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file())
 g['metadata_allowlists'][str(c.META_ROOTS[2])]=['ROOT-GUEST-GRANT.json','root-guest-observer.py','CONTROLLER.log','PROCESS.json']
 fresh('ROOT-GUEST-GRANT-BOUND-TEMPLATE.json',g)
 fresh('BOUND-HOST-READBACK.json',dict(status='CURRENT_BINDING_ALL_FILES_BASELINE_RESOURCES_READBACK_NO_GUEST',source=c.SOURCE,binding=row(HERE/'RECOVERY-BINDING.json'),baseline=row(HERE/'CURRENT-BASELINE.json'),resources=resources,cases=4,actual_media=True,guest_permission=False,SDK=0,stage=0,guest=0))
 files={p.name:row(p) for p in HERE.iterdir() if p.is_file()}
 fresh('TOOLCHAIN-SEAL.json',dict(status='BOUND_SOURCE_HOST_FOR_INDEPENDENT_REVIEW_NO_GUEST_GRANT',source=c.SOURCE,members=files))
 for name,pin in files.items():
  if row(HERE/name)!=pin:raise SystemExit('Final sealed bytes changed')
 fresh('READBACK.json',dict(status='BOUND_SOURCE_HOST_SEAL_READBACK_NO_GUEST',seal=row(HERE/'TOOLCHAIN-SEAL.json'),members=len(files),actual_binding=row(HERE/'RECOVERY-BINDING.json'),guest_permission=False))
 print(json.dumps(dict(seal=row(HERE/'TOOLCHAIN-SEAL.json'),readback=row(HERE/'READBACK.json'))))
