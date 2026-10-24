"""Small sealed media/observer support; source only until separate root allocation."""
from pathlib import Path
import hashlib,json,os,sys,types
HERE=Path(__file__).resolve().parent
SOURCE='8ce5ee2d00027268c3e69c9c300b819c1b14c63f'
def need(ok,why):
 if not ok:raise RuntimeError(why)
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def row(p):return {'size':Path(p).stat().st_size,'sha256':sha(p)}
def read(p):return json.loads(Path(p).read_bytes())
def native(p):
 p=str(p)
 if os.name=='nt' and p.startswith('/mnt/c/'):p='C:/'+p[7:]
 elif os.name=='nt' and p.startswith('/'):p='//wsl.localhost/Ubuntu-24.04'+p
 return Path(p)
def verify(p,pin):
 p=native(p);need(not p.is_symlink() and row(p)==pin,'Pinned input changed '+str(p))
def fresh(p,value):
 with Path(p).open('x') as f:json.dump(value,f,indent=2);f.write('\n')
def load_source(name,path,pin=None):
 p=Path(path);raw=p.read_bytes()
 if pin:need({'size':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}==pin,'Source pin changed')
 m=types.ModuleType(name);m.__file__=str(p);sys.modules[name]=m;exec(compile(raw,str(p),'exec',dont_inherit=True),m.__dict__);return m
def verify_kit(scope):
 need(__debug__ and sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode,'Use Python -I -S -B')
 seal=HERE/'TOOLCHAIN-SEAL.json';need(os.environ.get('RAIN_QA_'+scope.upper()+'_ALLOCATED')==sha(seal),'Separate exact root '+scope+' grant required')
 x=read(seal)
 for n,p in x['members'].items():verify(HERE/n,p)
 plan=read(HERE/'PLAN.json');need(plan['source']==SOURCE,'source');return plan
def release_active():
 for p in Path('/proc').iterdir():
  if not p.name.isdigit():continue
  try:a=[x.decode(errors='replace') for x in (p/'cmdline').read_bytes().split(b'\0') if x]
  except (OSError,ProcessLookupError):continue
  if not a or Path(a[0]).name not in {'bash','python','python3','python3.12'}:continue
  for x in a[1:5]:
   if x in {'-c','-m'}:break
   if x.startswith('-'):continue
   if Path(x).name in {'rr-cycle.sh','rr-cycle.py','rr-qa.sh','rr-qa.py','rr-jobs.sh','rr-jobs.py'}:return True
   break
 return False


def verify_documented_alias(alias,fact):
 """Checks a documented host-tool alias, never enables generic input symlinks."""
 alias=Path(alias);target=Path(fact['canonical_path'])
 need(alias.is_symlink(),'Documented host alias is no longer a symlink')
 need(os.readlink(alias)==fact['link_text'],'Host alias link text drift')
 need(target.is_absolute() and target==target.resolve() and not target.is_symlink(),'Canonical host tool must be a regular canonical file')
 need(alias.resolve()==target,'Host alias target drift')
 verify(target,fact['identity'])

def verify_inputs(plan):
 need(plan.get('host_python_path')=='/usr/bin/python3.12','Only reviewed regular host Python target')
 aliases=plan.get('host_tool_aliases',{})
 need(set(aliases)=={'/usr/bin/python3'},'Only documented interpreter alias is allowed')
 fact=aliases['/usr/bin/python3']
 need(fact=={'link_text':'python3.12','canonical_path':'/usr/bin/python3.12','identity':plan['host_python']},'Exact interpreter alias mapping required')
 # Windows consumers use canonical UNC payloads / explicit WSL canonical argv;
 # alias metadata is verified by the Linux parent before allocating their child.
 if os.name!='nt':verify_documented_alias('/usr/bin/python3',fact)
 for p,pin in plan['input_pins'].items():verify(p,pin)
 return {'verified_inputs':len(plan['input_pins']),'canonical_host_python':plan['host_python_path'],'documented_alias_checked_on_Linux':os.name!='nt'}
