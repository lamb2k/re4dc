#!/usr/bin/env python3
"""charbake hair regroup (D367, 2026-10-10): Leon's 14 source-ordered hair material runs as 2 runs, one per material,
each restripified. Stdlib only (Windows or WSL Python).

  cb_hair.py <leon_hair_runs.h> <leon4k_runtime.h> <out leon_hair_runs_g2.h> [--report r.json]

Input: the play bundle's leon_hair_runs.h (hair-adapter-r2: 14 runs alternating the two hair materials, every
triangle its own 3-corner strip; 20 meshlets, 1,347 records, 4,317 strip corners) and leon4k_runtime.h (role 7
positions / normals for coincidence and the record order). Output: the same namespace and API (uv, runs[], role,
palette_count, run_count) with run_count 2: material 2's 221 triangles then material 1's 1,218, as the knob
CHARBAKE_HAIR=1 (coarse_actor_owner_leon.inc) draws them: 9 runs per Leon instead of 21, 2 hair headers instead of 14.

Kept: every triangle (the same (vi, ni, ti) corner tuples, winding by strip parity), the UV array byte for byte, the
role 7 palette, positions, normals and weights (only referenced, never copied), each blob's header flags and the
full-hair bounds (the fog gate decides the hair as a whole, as before). Changed: the draw order. Coincident
triangles (63 pairs over the same three positions, 59 of them one per material) keep their relative order and corner
rotation: within a material they are pinned (fastpath build_blob.py: same meshlet, 3-corner strips in reference
order); across materials the regroup emits material 2 first, which the tool checks is each pair's source order.
With WORLD_AUTOSORT (the play recipe once the PS2 world draws) the PVR sorts translucent polygons itself, so the
order of non-coincident hair triangles matters only where overlapping cards tie: measured in Flycast, about 300
scattered edge pixels of a close-up blend differently (at most 33..49 levels; not visible at 1x). In a presort frame
it is an arbitrary order either way (hair depth writes are off).

Strips and meshlets come from the cl lane's fastpath build_blob.py (private store tools/fastpath, pinned below),
run as for every actor blob of the play bundle; this tool only feeds it the regrouped triangle lists.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import struct
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cb_blob import Blob, c_arrays, canon  # noqa: E402

STORE = Path(os.environ.get('CHARBAKE_STORE', 'C:/Game Dev/Emulators/re4-assets-private'))
FASTPATH = STORE / 'character-prototype-20260925/tools/fastpath/build_blob.py'
PINS = {
    'leon_hair_runs.h': '5df6f798c9ac9346726e151107a90dec7327d096b83f6a22856036a10b969634',
    'leon4k_runtime.h': '375a27d9678352556dca7c963327e5ac8a06c25021b4d10c4e1d9274a9a94ab8',
    'build_blob.py': None,   # recorded in the report
}
RUN = re.compile(r'\{run(\d+),sizeof\(run\d+\),(\d+),(\d+),(\d+)\}')


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def load_fastpath():
    spec = importlib.util.spec_from_file_location('build_blob', FASTPATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    a = sys.argv[1:]
    report_path = None
    if '--report' in a:
        i = a.index('--report'); report_path = Path(a[i + 1]); del a[i:i + 2]
    hair_h, leon_h, out_h = map(Path, a[:3])
    hb, lb = hair_h.read_bytes(), leon_h.read_bytes()
    for name, b in (('leon_hair_runs.h', hb), ('leon4k_runtime.h', lb)):
        if sha(b) != PINS[name]:
            raise SystemExit('%s changed (sha256 %s)' % (name, sha(b)))
    harr = c_arrays(hair_h)
    larr = c_arrays(leon_h)
    runs = []
    for m in RUN.finditer(hb.decode()):
        i, tris, mat, aid = map(int, m.groups())
        runs.append(dict(index=i, triangles=tris, material=mat, asset_id=aid, blob=Blob(harr['run%d' % i])))
    assert len(runs) == 14 and [r['asset_id'] for r in runs] == list(range(29, 43))
    first = runs[0]['blob']
    flags, bounds = first.data[2], first.data[16:32]
    for r in runs:
        assert r['blob'].data[2] == flags and r['blob'].data[16:32] == bounds and r['blob'].levels == 0 and r['blob'].rs == 3
    pos = larr['i7_pos']
    P = [struct.unpack_from('<3hH', pos, 8 * k) for k in range(len(pos) // 8)]
    # Source order: every triangle with its material and emitted corner rotation.
    src = []
    for r in runs:
        for t in r['blob'].triangles():
            assert t is not None
            src.append((r['material'], t))
    assert len(src) == 1439
    mats = []
    for m, _ in src:
        if m not in mats:
            mats.append(m)
    # Cross-material coincident pairs must already be in the regrouped material order.
    groups = {}
    for k, (m, t) in enumerate(src):
        groups.setdefault(tuple(sorted(P[c[0]][:3] for c in t)), []).append((k, m))
    coincident = [g for g in groups.values() if len(g) > 1]
    for g in coincident:
        order = [mats.index(m) for k, m in sorted(g)]
        assert order == sorted(order), 'a coincident group would change order across materials: %s' % g
    bb = load_fastpath()
    blobs, rows = [], []
    for mi, m in enumerate(mats):
        tris = [t for mm, t in src if mm == m]
        with tempfile.TemporaryDirectory(prefix='cbhair-') as d:
            d = Path(d)
            corners = [c for t in tris for c in t]
            (d / 'info0.gx').write_bytes(bytes([0x90]) + struct.pack('>H', len(corners)) +
                                         b''.join(struct.pack('>3H', *c) for c in corners))
            (d / 'info0.pos').write_bytes(larr['i7_pos'])
            (d / 'info0.nrm').write_bytes(larr['i7_nrm'])
            (d / 'info0.uv').write_bytes(harr['uv'])
            ch = bb.Chunk(bb.load_chunk(d, 0))
        best = None
        for mode in ('boundary', 'near', 'palette'):
            for wd in (0.0, 0.02, 0.1):
                metas = bb.build(ch, mode, wd, 8)
                cst, st = bb.cost(metas)
                if best is None or cst < best[0]:
                    best = (cst, st, metas, mode, wd)
        cst, st, metas, mode, wd = best
        blob = bytearray(bb.assemble(ch, metas))
        # Keep the runs' header flags (uv excess) and the full-hair bounds: the fog gate keeps deciding the hair as a
        # whole, exactly as the 14 runs did.
        blob[2] = flags
        blob[16:32] = bounds
        blob = bytes(blob) + bytes((-len(blob)) % 32)
        nb = Blob(blob)
        got = sorted(canon(t) for t in nb.triangles() if t is not None)
        want = sorted(canon(t) for t in tris)
        assert got == want and sum(1 for t in nb.triangles() if t is None) == 0, 'triangle set / winding changed'
        # Coincident triangles within this material (pinned) keep their order inside each group and their rotation.
        em = [t for t in nb.triangles()]
        for g in {tuple(ch.unit[i]) for i in ch.pinned}:
            ref = [tris[i] for i in sorted(g)]
            assert [t for t in em if t in set(ref)] == ref, 'coincident group order / rotation changed'
        blobs.append(blob)
        st = {k: v for k, v in nb.stats().items() if k != 'triangles'}
        rows.append(dict(material=m, asset_id=29 + mi, triangles=len(tris), pinned=len(ch.pinned), seed=mode, w_dist=wd,
                         **st))
    # Header: the same namespace and API as leon_hair_runs.h.
    out = ['// Private generated (charbake cb_hair.py): leon_hair_runs.h regrouped, one run per hair material, restripified.\n'
           '// Same corner tuples, winding, UV words, palette, flags and bounds; no copied positions, normals or weights.\n'
           '#pragma once\nnamespace leon_hair_runs {\n']

    def array(name, data):
        out.append('alignas(32) static const unsigned char ' + name + '[] = {\n')
        out.extend(','.join(str(v) for v in data[i:i + 24]) + ',\n' for i in range(0, len(data), 24))
        out.append('};\n')
    array('uv', harr['uv'])
    for i, b in enumerate(blobs):
        array('run%d' % i, b)
    out.append('struct Run { const unsigned char* stream; unsigned bytes,triangles,material,asset_id; };\n')
    out.append('static const Run runs[] = {\n')
    for i, r in enumerate(rows):
        out.append('{run%d,sizeof(run%d),%d,%d,%d},\n' % (i, i, r['triangles'], r['material'], r['asset_id']))
    out.append('};\nstatic constexpr unsigned role=7,palette_count=229,run_count=%d;\n}\n' % len(rows))
    text = ''.join(out).encode()
    out_h.write_bytes(text)
    old = dict(meshlets=sum(r['blob'].stats()['meshlets'] for r in runs), records=sum(r['blob'].stats()['records'] for r in runs),
               indices=sum(r['blob'].stats()['indices'] for r in runs), strips=sum(r['blob'].stats()['strips'] for r in runs),
               runs=len(runs), bytes=sum(len(r['blob'].data) for r in runs))
    new = dict(meshlets=sum(r['meshlets'] for r in rows), records=sum(r['records'] for r in rows),
               indices=sum(r['indices'] for r in rows), strips=sum(r['strips'] for r in rows), runs=len(rows),
               bytes=sum(len(b) for b in blobs))
    rep = dict(tool='tools/d367/charbake/cb_hair.py', inputs={hair_h.name: sha(hb), leon_h.name: sha(lb),
               'build_blob.py': sha(FASTPATH.read_bytes())}, output=dict(path=out_h.name, sha256=sha(text), bytes=len(text)),
               coincident_groups=len(coincident), before=old, after=new, runs=rows)
    print(json.dumps(dict(before=old, after=new, output=rep['output']), indent=1))
    if report_path:
        report_path.write_text(json.dumps(rep, indent=1))


if __name__ == '__main__':
    main()
