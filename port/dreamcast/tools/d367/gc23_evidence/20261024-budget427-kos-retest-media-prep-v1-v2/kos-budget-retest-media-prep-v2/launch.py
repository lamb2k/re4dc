"""Isolated direct source loader, root-pinned exact source kit."""
from pathlib import Path
import hashlib,json,os,sys,types
assert __debug__ and sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
here=Path(__file__).resolve().parent;raw=(here/'TOOLCHAIN-SEAL.json').read_bytes()
assert hashlib.sha256(raw).hexdigest()==os.environ.get('GC_BUDGET_RETEST_TOOLS'),'Exact new root allocation required'
pins=json.loads(raw)['members']
for n,pin in pins.items():
 data=(here/n).read_bytes();assert len(data)==pin['size'] and hashlib.sha256(data).hexdigest()==pin['sha256']
for n in ['core','stage']:
 path=here/(n+'.py');m=types.ModuleType(n);m.__file__=str(path);sys.modules[n]=m;exec(compile(path.read_bytes(),str(path),'exec',dont_inherit=True),m.__dict__)
sys.modules['stage'].main()
