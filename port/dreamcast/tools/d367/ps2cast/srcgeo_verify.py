#!/usr/bin/env python3
"""srcgeo_verify.py <store dir> [--tree <checkout>]: simulate re4dc_actor_archive_adopt over a srcgeo store (lane srcgeo 11-17).
Reads <store>/chain.txt (the input archives, from gen.sh), the store's converted em/*.drs and every dc/native/*/*.re4nmr, and
reports per package how many SBlob rows adopt a PS2-derived BIN (ok_new), a GameCube BIN the archive still carries (ok_gc), a
GameCube row whose archive BIN was converted (CLASH: the cast would decline it), or an archive this set does not carry
(external). Exit 1 on any CLASH."""
import json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]
import ps2_accessories as pa  # noqa: E402
import src_blob_patch as sp  # noqa: E402

store = Path(sys.argv[1])
arcs = []
for line in (store / 'chain.txt').read_text().splitlines():
    kind, name, path, *_ = line.split()
    if kind == 'arch' and (store / 'em' / (name + '.drs')).is_file():
        arcs.append(dict(name=name, old=pa.Payload(Path(path).read_bytes()), new=pa.Payload((store / 'em' / (name + '.drs')).read_bytes())))
bad = 0
tot = dict(ok_new=0, ok_gc=0, clash=0, external=0)
for f in sorted((store / 'dc/native').glob('*/*.re4nmr')):
    v = sp.verify_rows(f.read_bytes(), arcs)
    print('%s/%s ok_new=%d ok_gc=%d clash=%s external=%s' % (f.parent.name, f.name, v['ok_new'], v['ok_gc'], v['clash'], v['external']))
    for k in ('ok_new', 'ok_gc'):
        tot[k] += v[k]
    tot['clash'] += len(v['clash'])
    tot['external'] += len(v['external'])
    bad += len(v['clash'])
print('TOTAL', json.dumps(tot))
sys.exit(1 if bad else 0)
