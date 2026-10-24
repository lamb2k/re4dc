#!/usr/bin/env python3
"""Bounded fail-closed checks; run only in this lane's isolated idle checkout.

The generated macro is altered temporarily and restored byte-for-byte in a
finally block. No other source, SDK, recipe, programme or asset is touched.
Run under the shared build-slot lease; this script itself never starts a guest.
"""
import argparse, hashlib, json, subprocess, sys
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--report', type=Path, required=True)
a=p.parse_args()
here=Path(__file__).resolve().parent
macro=here.parents[2]/'game/platform/backface_sh4zam_area.inc'
original=macro.read_bytes()
def check(expected, *extra):
    r=subprocess.run([sys.executable,str(here/'generate.py'),'--check',*extra],capture_output=True,text=True)
    assert r.returncode != 0 and expected in r.stdout+r.stderr, (r.returncode,r.stdout,r.stderr)
    return dict(result='refused',reason=expected)
results={}
try:
    macro.write_bytes(original+b'\n/* deliberate stale-macro control */\n')
    results['stale_macro']=check('Generated SH4ZAM area macro is stale')
finally:
    macro.write_bytes(original)
assert macro.read_bytes()==original
results['unqualified_compiler']=check('Unqualified SH-4 compiler:', '--compiler','/usr/bin/g++')
r=subprocess.run([sys.executable,str(here/'generate.py'),'--check'],capture_output=True,text=True)
assert r.returncode==0, (r.stdout,r.stderr)
results['restored_macro']=dict(result='accepted',sha256=hashlib.sha256(original).hexdigest())
a.report.write_text(json.dumps(dict(controls=results,scope='source/target-object build checks only'),indent=2)+'\n')
print(json.dumps(results))
