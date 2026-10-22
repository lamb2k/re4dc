#!/usr/bin/env python3
"""Build the original strip oracle with the verified SH4 C FMAC lowering.

Only the determinant expression changes in the generated private header. The
source CPU1 reference is read-only. Host execution remains distinct from SH4.
"""
import argparse, hashlib, json, subprocess
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--output',type=Path,required=True)
a=p.parse_args(); out=a.output.resolve(); assert out.is_dir()
here=Path(__file__).resolve().parent
src=here.parents[2]/'room'/'backface_emit.hpp'
old='float area = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax);'
new='float area = std::fma(bx - ax, cy - ay, -((by - ay) * (cx - ax)));'
text=src.read_text(); assert text.count(old)==1
header=out/'backface_emit.hpp'; assert not header.exists()
header.write_text('#include <cmath>\n'+text.replace(old,new))
lib=out/'oracle.so'; assert not lib.exists()
cmd=['g++','-O2','-fno-fast-math','-ffp-contract=off','-shared','-fPIC',
     '-I'+str(out),'-I'+str(here/'include'),str(here/'oracle.cpp'),'-o',str(lib)]
subprocess.run(cmd,check=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
receipt=out/'oracle-contract.json'; assert not receipt.exists()
receipt.write_text(json.dumps(dict(source_header=str(src),source_sha256=sha(src),
 generated_sha256=sha(header),library_sha256=sha(lib),command=cmd,
 target_order='rounded second product, fneg, FMAC first product plus negative second',
 scope='host target-lowered C template oracle; actual target opcodes separately pinned'),indent=2)+'\n')
