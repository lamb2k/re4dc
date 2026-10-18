#!/usr/bin/env python3
"""Re-extract ps2cast inputs (em/<a>.drs verbatim from the GC debug ISO, as ps2_cast.inputs did) and check recorded shas.
usage: c4r-drs.py <tools dir> <outdir> <expect.tsv: name sha>"""
import sys, hashlib
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from assetpipe.rooms import GcIso
ISO = '/mnt/c/Game Dev/Emulators/Resident Evil 4 Debug (Disc 1)/Resident Evil 4 Debug (Disc 1).iso'
out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
exp = dict(l.split() for l in open(sys.argv[3]) if l.strip())
iso = GcIso(ISO)
for n in sorted(exp):
    b = iso.read('em/' + n)
    (out / n).write_bytes(b)
    h = hashlib.sha256(b).hexdigest()
    print(n, 'exact' if h == exp[n] else 'DIFF ' + h)
