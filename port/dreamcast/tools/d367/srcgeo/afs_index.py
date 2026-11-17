#!/usr/bin/env python3
"""afs_index.py <out.json> [PS2 iso]: {name: [[iso offset, size], ...]} of the PS2 BIO4DAT.AFS entries (lane srcgeo 11-17).
fxproof26/ps2afs.py keys by name only and keeps the LAST entry of a duplicated name, which is a size-0 stub for em1d.dat, em12.dat
and others (the real file is the first entry). srcgeo_store.py reads the first entry with size > 0."""
import json, struct, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'fxproof26'))
import ps2afs  # noqa: E402

out = sys.argv[1]
iso = sys.argv[2] if len(sys.argv) > 2 else ps2afs.ISO
f = open(iso, 'rb')
fs = ps2afs.iso_files(f)
o, _sz = fs['/DATA/BIO4DAT.AFS']
f.seek(o)
h = f.read(8)
n = struct.unpack_from('<I', h, 4)[0]
tab = f.read(8 * n + 8)
ents = [struct.unpack_from('<II', tab, 8 * i) for i in range(n)]
no, ns = struct.unpack_from('<II', tab, 8 * n)
f.seek(o + no)
nt = f.read(ns)
res = {}
for i, (eo, es) in enumerate(ents):
    res.setdefault(nt[48 * i:48 * i + 32].rstrip(b'\0').decode('latin1'), []).append((o + eo, es))
json.dump(res, open(out, 'w'))
print(len(res), 'names')
