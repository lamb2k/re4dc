#!/usr/bin/env python3
"""Per-role / per-region triangle split of GC, PS2 and today's Leon; PS2 bone-table comparison; textures used."""
import json, sys
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import leon_sources as ls  # noqa

parents, rest = ls.gc_skeleton()
reg = ls.bone_regions(parents)
out = {}
print('== GC skeleton (bone parent rest region)')
for b in range(len(parents)):
    print(f'  {b:3d} {parents[b]:4d} {rest[b][0]:8.1f} {rest[b][1]:8.1f} {rest[b][2]:8.1f} {reg[b]}')

print('\n== GC roles')
gc_rows = {}
for r in range(8):
    g = ls.gc_role(r)
    cw = [[g['weights'][p] for p in t] for t in g['tris']]
    regs = Counter(ls.triangle_region(c, reg) for c in cw)
    bones = sorted({b for w in g['weights'] for b, _ in w})
    mats = Counter(m for m, _ in g['tri_material'])
    uvs = np.asarray([c[2] for t in g['corners'] for c in t])
    gc_rows[r] = dict(tris=len(g['tris']), positions=len(g['positions']), regions=dict(regs), bones=bones,
                      materials=dict(mats), uv_min=uvs.min(0).tolist(), uv_max=uvs.max(0).tolist(),
                      bindings=[str(b) for b in g['bindings']])
    print(f'role {r} {g["name"]:10s} tris {len(g["tris"]):5d} pos {len(g["positions"]):5d} regions {dict(regs)} materials {dict(mats)} uv {uvs.min(0).round(3)}..{uvs.max(0).round(3)}')
    print(f'      bones {bones}')
    print(f'      bindings {[str(b) for b in g["bindings"]][:8]}')
out['gc'] = gc_rows

print('\n== PS2 roles')
ps2_rows = {}
for r in range(8):
    p = ls.ps2_role(r)
    ids, pr, prest = p['bone_ids'], p['bone_parents'], p['bone_rest']
    # bone identity vs GC: same parent and accumulated rest within 0.01 mm
    same = {}
    for i, b in enumerate(ids):
        d = float(np.abs(prest[i] - rest[b]).max()) if b < len(rest) else None
        same[b] = (pr[i] == parents[b] or (pr[i] == -1)) and d is not None and d < 0.5, d, pr[i], parents[b] if b < len(parents) else None
    used = sorted({b for _, cs in p['tris'] for c in cs for b, _ in c['w']})
    bad = [b for b in used if not same[b][0]]
    # region via GC region when the bone is identical, else by the PS2 parent chain's first identical bone
    def preg(b):
        while not same.get(b, (False,))[0]:
            par = pr[ids.index(b)]
            if par < 0:
                return reg[b] if b < len(reg) else 'torso'
            b = par
        return reg[b]
    regs = Counter()
    for _, cs in p['tris']:
        acc = defaultdict(float)
        for c in cs:
            for b, w in c['w']:
                acc[preg(b)] += w
        regs[max(acc.items(), key=lambda kv: (kv[1], -ls.REGIONS.index(kv[0])))[0]] += 1
    mats = Counter(p['bin'].materials[t]['diffuse'] for t, _ in p['tris'])
    pos = {tuple(round(x, 4) for x in c['p']) for _, cs in p['tris'] for c in cs}
    uvs = np.asarray([c['uv'] for _, cs in p['tris'] for c in cs])
    ps2_rows[r] = dict(tris=len(p['tris']), unique_positions=len(pos), regions=dict(regs), bones_used=used,
                       mismatched_bones={b: dict(rest_diff=same[b][1], ps2_parent=same[b][2], gc_parent=same[b][3]) for b in bad},
                       materials=dict(mats), uv_min=uvs.min(0).tolist(), uv_max=uvs.max(0).tolist(),
                       material_rows=[m['raw'] for m in p['bin'].materials])
    print(f'role {r} {p["name"]:10s} tris {len(p["tris"]):5d} pos {len(pos):5d} regions {dict(regs)} tex {dict(mats)} uv {uvs.min(0).round(3)}..{uvs.max(0).round(3)}')
    print(f'      bones used {used}; mismatched {[(b, round(same[b][1] or -1, 2), same[b][2], same[b][3]) for b in bad]}')
out['ps2'] = ps2_rows

print('\n== today (leon-hair-v2 mesh.json)')
m = ls.leon_mesh()
W = m['weights']
cur = {}
for r in range(8):
    ts = [t for t in m['triangles'] if t['source_info'] == r]
    regs = Counter(ls.triangle_region([W[c['vertex']] for c in t['corners']], reg) for t in ts)
    vs = {c['vertex'] for t in ts for c in t['corners']}
    cur[r] = dict(tris=len(ts), positions=len(vs), regions=dict(regs))
    print(f'role {r} tris {len(ts):5d} pos {len(vs):5d} regions {dict(regs)}')
out['today'] = cur
for k, rows in (('gc', gc_rows), ('ps2', ps2_rows), ('today', cur)):
    tot = Counter()
    for r in rows.values():
        tot.update(r['regions'])
    print(k, 'total', sum(r['tris'] for r in rows.values()), dict(tot))
(ls.WORK / 'analysis.json').write_text(json.dumps(out, indent=1))
