"""Direct-source only; exact root-pinned seal, no adjacent pyc imports."""
from pathlib import Path
import hashlib,json,os,sys,types
assert __debug__ and sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
here=Path(__file__).resolve().parent;raw=(here/'TOOLCHAIN-SEAL.json').read_bytes()
assert hashlib.sha256(raw).hexdigest()==os.environ.get('GC_BUDGET_QA_TOOLS')
for name,pin in json.loads(raw)['members'].items():
 data=(here/name).read_bytes();assert {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}==pin
path=here/'controller.py';m=types.ModuleType('continued');m.__file__=str(path);sys.modules[m.__name__]=m;exec(compile(path.read_bytes(),str(path),'exec',dont_inherit=True),m.__dict__);m.main()
