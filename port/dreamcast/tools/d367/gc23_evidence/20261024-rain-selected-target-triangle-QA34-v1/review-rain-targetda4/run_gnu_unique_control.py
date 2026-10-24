"""Exact da4 ABI-format counterexample; stdlib/synthetic ELF only."""
from pathlib import Path
import argparse,sys,tempfile,json
ap=argparse.ArgumentParser();ap.add_argument('--tools',required=True);a=ap.parse_args();sys.path.insert(0,a.tools)
import test_preparation as t,readback
with tempfile.TemporaryDirectory(prefix='rain-gnuunique-',dir='/dev/shm') as d:
 p=Path(d)/'before';q=Path(d)/'after'
 for path,value in [(p,0),(q,2)]:t.elf(path,text=b'\x09\x00\x0b\x00'*2,reloc_symbol=2,symbind=10,symtype=1,symval=value)
 readback.require_identity(readback.Elf(p),readback.Elf(q))
 print(json.dumps(dict(scope='Historical exactda4 wrongly accepted unsupported ABI',accepted=True,binding=10,type=1,value_before=0,value_after=2,symbol_size=4,section_size=8,SDK=0),indent=2))
