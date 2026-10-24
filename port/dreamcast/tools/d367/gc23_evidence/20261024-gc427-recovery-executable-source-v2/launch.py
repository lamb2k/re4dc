"""Exact root-pinned direct source before any imports from this kit."""
from pathlib import Path
import hashlib,json,os,sys,types
if not __debug__:raise RuntimeError('Optimized Python refused')
assert __debug__ and sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
HERE=Path(__file__).resolve().parent;raw=(HERE/'TOOLCHAIN-SEAL.json').read_bytes();assert hashlib.sha256(raw).hexdigest()==os.environ.get('GC_BUDGET_RETEST_GUEST_TOOLS'),'Root exact guest-kit allocation required'
pins=json.loads(raw)['members']
for n,v in pins.items():
 raw=(HERE/n).read_bytes();assert len(raw)==v['size'] and hashlib.sha256(raw).hexdigest()==v['sha256']
mode='post_slot' if sys.argv[1:2]==['--post-slot'] else 'controller';assert mode=='post_slot' or len(sys.argv)==1
for name,alias in [('common','guest_common'),(mode,'owned_guest_entry')]:
 p=HERE/(name+'.py');m=types.ModuleType(alias);m.__file__=str(p);sys.modules[alias]=m;exec(compile(p.read_bytes(),str(p),'exec',dont_inherit=True),m.__dict__)
sys.argv=[str(HERE/(mode+'.py')),*sys.argv[2:]] if mode=='post_slot' else [str(HERE/'controller.py')]
sys.modules['owned_guest_entry'].main()
