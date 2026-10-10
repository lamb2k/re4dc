#!/usr/bin/env python3
"""ps2leon counts table: per-part triangles, vertices and draw work of today's Leon (play bundle), arm A, arm B and the
GameCube Leon. Parts by bone region (leon_sources.bone_regions; a triangle goes to the part with the largest summed
weight over its corners): head/face/hair, torso/back/shoulders, arms/hands, legs/feet.

Draw work from the runtime headers (FE/v3 blobs): owner draw runs (roles 0..6 one each + the hair runs: each run is
its own TA header / material switch), meshlets, records (transformed vertices), strips, strip corners, palette runs
(matrix switches inside meshlets), palette entries (skinned matrices per frame), plan palette / workspace bytes and the
generated array bytes. The roles 0..6 draw their chunk blob (i<k>_gx); role 7 draws the hair runs.

  counts.py <out counts.json>
"""
import json, re, struct, sys
from collections import Counter
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import leon_sources as ls  # noqa: E402
sys.path.insert(0, str(ls.TREE / 'port/dreamcast/tools/d367/charbake'))
from cb_blob import Blob  # noqa: E402

R = ls.WORK
ARRAY = re.compile(r'alignas\(32\)\s+static\s+(?:const\s+)?unsigned\s+char\s+(\w+)\[\]\s*=\s*\{([^}]*)\};', re.S)
CHUNK = re.compile(r'\{(\d+),(\d+),(\d+),(\d+),(\d+),(\d+),(i\d+)_pos,')
RUN = re.compile(r'\{run(\d+),sizeof\(run\d+\),(\d+),(\d+),(\d+)\}')
PARTS = ['head', 'torso', 'arms', 'legs']


def arrays(text):
    return {m.group(1): bytes(int(v, 0) for v in m.group(2).replace('\n', '').split(',') if v.strip()) for m in ARRAY.finditer(text)}


def mesh_parts(mesh):
    parents, _ = ls.gc_skeleton()
    reg = ls.bone_regions(parents)
    W = mesh['weights']
    parts, roles = Counter(), Counter()
    verts = set()
    for t in mesh['triangles']:
        parts[ls.triangle_region([W[c['vertex']] for c in t['corners']], reg)] += 1
        roles[t['source_info']] += 1
        verts.update((t['source_info'], c['vertex']) for c in t['corners'])
    return dict(parts={p: parts[p] for p in PARTS}, roles={r: roles[r] for r in range(8)}, triangles=sum(parts.values()), vertices=len(verts))


def blob_work(blob, pos, nrm):
    b = Blob(blob)
    st = b.stats()
    pr = 0
    for m in b.table:
        key = None
        for rec in m['records']:
            k2 = (struct.unpack_from('<H', pos, rec[0] * 8 + 6)[0], struct.unpack_from('<H', nrm, rec[1] * 8 + 6)[0])
            if k2 != key:
                pr += 1; key = k2
    return dict(meshlets=st['meshlets'], records=st['records'], strips=st['strips'], corners=st['indices'], palette_runs=pr, triangles=st['triangles'])


def header_work(runtime, hair):
    rt, ht = Path(runtime).read_text(), Path(hair).read_text()
    A, H = arrays(rt), arrays(ht)
    chunks = {int(m.group(1)): (m.group(7), int(m.group(2)), int(m.group(3)), int(m.group(4)), int(m.group(5))) for m in CHUNK.finditer(rt)}
    tot = Counter()
    runs = 0
    for i in range(7):
        p = chunks[i][0]
        w = blob_work(A[p + '_gx'], A[p + '_pos'], A[p + '_nrm'])
        tot.update(w); runs += 1
    p7 = chunks[7][0]
    hair_runs = 0
    for m in RUN.finditer(ht):
        w = blob_work(H['run%d' % int(m.group(1))], A[p7 + '_pos'], A[p7 + '_nrm'])
        tot.update(w); runs += 1; hair_runs += 1
    pals = [chunks[i][3] for i in range(8)]
    r32 = lambda x: (x + 31) & ~31
    data = sum(len(v) for v in A.values()) + 16 * sum(pals) + sum(len(v) for v in H.values())
    positions = sum(chunks[i][1] for i in range(8))
    normals = sum(chunks[i][2] for i in range(8))
    return dict(draw_runs=runs, hair_runs=hair_runs, palette_entries=sum(pals), positions=positions, normals=normals,
                plan_palette_bytes=sum(r32(n * 48) for n in pals), plan_workspace_bytes=max(r32(n * 114) for n in pals),
                array_bytes=data, **dict(tot))


def gc_work():
    batches = 0
    for r in range(8):
        g = ls.gc_role(r)
        # GX draw batches: consecutive triangles sharing (material, part)
        prev = None
        for mp in g['tri_material']:
            if mp != prev:
                batches += 1; prev = mp
    return dict(draw_batches=batches)


def main():
    out = Path(sys.argv[1])
    B = ls.PRIV / 'play-actor-bundle-20260928'
    rows = {}
    rows['today'] = dict(label="today's Leon (leon4k, play bundle)", **mesh_parts(ls.leon_mesh()),
                         work=header_work(B / 'leon4k_runtime.h', B / 'leon_hair_runs.h'),
                         work_charbake_hair=header_work(B / 'leon4k_runtime.h', R / 'arms/today/ps2leon_hair_runs.h'))
    for k, lab in (('a', 'A: PS2 Leon (PS2_LEON=1)'), ('b', 'B: hybrid (PS2_LEON=2)')):
        rows[k] = dict(label=lab, **mesh_parts(json.loads((R / 'arms' / k / 'mesh.json').read_text())),
                       work=header_work(R / 'arms' / k / 'ps2leon_runtime.h', R / 'arms' / k / 'ps2leon_hair_runs.h'))
    gc = json.loads((R / 'arms/gc/mesh.json').read_text())
    rows['gc'] = dict(label='GameCube Leon (source)', **mesh_parts(gc), work=gc_work())
    # the PS2 Leon as stored on the disc (including the zero-area strip joints arm A drops)
    ps2 = json.loads((R / 'analysis.json').read_text())['ps2']
    rows['ps2_stored'] = dict(label='PS2 Leon as stored', triangles=sum(v['tris'] for v in ps2.values()),
                              parts={p: sum(v['regions'].get(p, 0) for v in ps2.values()) for p in PARTS})
    out.write_text(json.dumps(rows, indent=1))
    hdr = '%-36s %6s %6s %6s %6s %6s | %6s %6s %6s %5s %6s %6s %5s %5s' % ('', 'head', 'torso', 'arms', 'legs', 'tris', 'verts', 'recs', 'corn', 'strip', 'palrun', 'pals', 'runs', 'mlts')
    print(hdr)
    for k in ('today', 'a', 'b', 'gc'):
        r = rows[k]; w = r['work']
        p = r['parts']
        if k == 'gc':
            print('%-36s %6d %6d %6d %6d %6d | %6d %s batches %d' % (r['label'], p['head'], p['torso'], p['arms'], p['legs'], r['triangles'], r['vertices'], ' ' * 20, w['draw_batches']))
        else:
            print('%-36s %6d %6d %6d %6d %6d | %6d %6d %6d %5d %6d %6d %5d %5d' % (r['label'], p['head'], p['torso'], p['arms'], p['legs'], r['triangles'], w['positions'],
                  w['records'], w['corners'], w['strips'], w['palette_runs'], w['palette_entries'], w['draw_runs'], w['meshlets']))
    w = rows['today']['work_charbake_hair']
    print('%-36s %s | %6d %6d %6d %5d %6d %6d %5d %5d' % ('  today with CHARBAKE_HAIR=1', ' ' * 34, w['positions'], w['records'], w['corners'], w['strips'], w['palette_runs'], w['palette_entries'], w['draw_runs'], w['meshlets']))
    for k in ('today', 'a', 'b'):
        w = rows[k]['work']
        print(k, 'plan palette', w['plan_palette_bytes'], 'workspace', w['plan_workspace_bytes'], 'arrays', w['array_bytes'], 'normals', w['normals'])
    print('PS2 stored', rows['ps2_stored'])


if __name__ == '__main__':
    main()
