"""Isolated read-only OFF reuse or ON stage all-file/IP/redirect verifier."""
from pathlib import Path
import argparse,hashlib,json,sys,types
HERE=Path(__file__).resolve().parent
assert __debug__ and sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
a=argparse.ArgumentParser();a.add_argument('--tools-sha256',required=True);a.add_argument('--arm',choices=['off','on'],required=True);a.add_argument('--out',type=Path,required=True);v=a.parse_args()
assert hashlib.sha256((HERE/'TOOLCHAIN-SEAL.json').read_bytes()).hexdigest()==v.tools_sha256
for n,pin in json.loads((HERE/'TOOLCHAIN-SEAL.json').read_text())['members'].items():
 raw=(HERE/n).read_bytes();assert len(raw)==pin['size'] and hashlib.sha256(raw).hexdigest()==pin['sha256']
p=HERE/'core.py';k=types.ModuleType('core');k.__file__=str(p);sys.modules['core']=k;exec(compile(p.read_bytes(),str(p),'exec'),k.__dict__)
k.sealed();k.validate_binding(k.read(HERE/'BINDING.json'));c,pins=k.adapter();b=types.ModuleType('bind');b.validate=k.validate_binding;sys.modules['bind']=b;rb=k.source('readback_direct',k.OLD/'readback.py',pins['readback.py']['sha256'])
assert v.out.is_absolute() and v.out==v.out.resolve() and not v.out.exists()
k.fresh(v.out,rb.check(v.arm,k.OFF if v.arm=='off' else k.FINAL/'on'))
