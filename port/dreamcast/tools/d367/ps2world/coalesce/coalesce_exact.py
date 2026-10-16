#!/usr/bin/env python3
"""Private r101 spatial32v3 experiment: coalesce exactly three adjacent ranges.

Never rewrites input or a preexisting destination. No geometry conversion, build,
runtime patch, emulator, texture conversion, or installation is performed.
"""
import argparse
import hashlib
import json
import math
import struct
import subprocess
import zlib
from pathlib import Path

PAIRS = ((206, 175, 176), (208, 195, 196), (209, 219, 220))
EXPECTED = {
    'ps2-wv5.re4mesh': '5dd5e15f8c9826cd7db02a2e2ff3f86488ce8cba7efdba2e4d4cf8194f62e732',
    'ps2-world.re4mesh': 'd8a9866e92e0ba0123016e5eca13e526c63526c121310f7423d011a8a6a7e95a',
    'ps2-world.r4pw': '4d6e573c2e3863e0a62d0de10195b8beb73e5982f89be41f954845559f161d34',
    'ps2-world.ids': '209fb771330bc0740e1d5adb452f07da76f48371e1ffd9ba4b468cd948f89054',
    'ps2-wv5.r4sg': 'abebbb02fcc447083c30f27c6e39d8a7acace6cc9f70875b1cda64c2607a5fae',
    'ps2-world.r4sg': 'd39e5cdb032985f75c82ee4a55056fa108fb25f05c74983926d3769cea31dbe6',
}
RUNTIME = {
    'port/dreamcast/game/platform/native_static.cpp': '8eb55017c0726bf51bd2d9996e8ee3aa8c0905e9cae20f26c3de22ae266a2aa3',
    'port/dreamcast/game/platform/native_ui.cpp': 'f3fec7ba272579a213bcbefc8e5a3b55e62c1f1ea193d21627a4754878fca210',
    'port/dreamcast/room/instanced_mesh.hpp': 'bf43408d054e448ff6052ac9c46ebc00b92a2495979c4555919a663724d2aff3',
}
FORMATS = {'meshes': '<HBBHHIII12f', 'parts': '<IIBBBBII4f',
           'lets': '<IIIHH6H', 'verts': '<6H', 'plods': '<II',
           'clusters': '<6HII', 'levels': '<IIf'}

def sha(data):
    return hashlib.sha256(data).hexdigest()

def mesh_read(blob):
    h = struct.unpack_from('<4s19I', blob)
    l = struct.unpack_from('<8I', blob, 80)
    assert h[:2] == (b'R4IM', 3) and h[2] == len(blob)
    assert h[3] == zlib.crc32(blob[80:])
    assert h[16:] == (2, 0, 0, 0) and l[5:] == (0, 0, 0)
    sections = {'meshes': (h[10], h[4]), 'parts': (h[11], h[5]),
                'lets': (h[12], h[6]), 'verts': (h[13], h[7]),
                'plods': (l[2], h[5]), 'clusters': (l[3], l[0]),
                'levels': (l[4], l[1])}
    p = {'h': h, 'l': l, 'raw': blob, 'sections': sections}
    for name, (offset, count) in sections.items():
        s = struct.Struct(FORMATS[name])
        assert offset >= 112 and offset % 4 == 0 and offset + count*s.size <= len(blob)
        p[name] = [s.unpack_from(blob, offset+i*s.size) for i in range(count)]
    for offset, count, stride in ((h[14], h[8], 1), (h[15], h[9], 4)):
        assert offset >= 112 and offset % 4 == 0 and offset+count*stride <= len(blob)
    assert 1 <= h[9] <= 16
    p['strip'] = blob[h[14]:h[14]+h[8]]
    return p

def corners(p, m):
    indexed = bool(m[4] & 0x8000)
    offsets = struct.unpack_from('<%dH' % m[3], p['strip'], m[1]) if indexed else range(m[3])
    return [m[0]+x for x in offsets]

def pool(p, part):
    if not part[7]:
        return None
    lets = p['lets'][part[6]:part[6]+part[7]]
    # Mirrors MeshPackage::part_pool, including its first_vertex lower bound.
    return min(m[0] for m in lets), max(max(corners(p, m))+1 for m in lets)

def validate_mesh(p):
    h = p['h']
    counts = {'strips': 0, 'strip_corners': 0, 'cluster_memberships': 0,
              'level_memberships': 0, 'nonempty_parts': 0}
    for m in p['meshes']:
        assert m[6] <= h[5] and m[7] <= h[5]-m[6]
        assert all(x > 0 and math.isfinite(x) for x in m[11:14])
    previous = 0
    for part, plod in zip(p['parts'], p['plods']):
        assert part[5] == 0 and part[6] <= h[6] and part[7] <= h[6]-part[6]
        assert plod[0] <= len(p['clusters']) and plod[1] <= len(p['clusters'])-plod[0]
        bounds = pool(p, part)
        if bounds:
            assert bounds[0] >= previous and bounds[1] <= h[7]
            previous = bounds[1]
            counts['nonempty_parts'] += 1
        for cl in p['clusters'][plod[0]:plod[0]+plod[1]]:
            counts['cluster_memberships'] += 1
            assert cl[7] and cl[6] <= len(p['levels']) and cl[7] <= len(p['levels'])-cl[6]
            error = 0.0
            for lv in p['levels'][cl[6]:cl[6]+cl[7]]:
                counts['level_memberships'] += 1
                assert error <= lv[2] < 3e38
                error = lv[2]
                assert lv[0] >= part[6] and lv[1] <= part[7]
                assert lv[0]-part[6] <= part[7]-lv[1]
    for m in p['lets']:
        table = 2*m[3] if m[4] & 0x8000 else 0
        assert 0 < m[3] <= 256 and m[0] <= h[7]
        assert not table or m[1] % 2 == 0
        assert m[1]+table+m[2] <= len(p['strip'])
        assert all(0 <= x < h[7] for x in corners(p, m))
        at = m[1]+table
        end = at+m[2]
        total = 0
        while at < end:
            n = p['strip'][at]
            assert n >= 3 and at+1+n <= end
            assert all(x < m[3] for x in p['strip'][at+1:at+1+n])
            at += 1+n
            total += 1
            counts['strip_corners'] += n
        assert at == end and total == m[4] & 0x7fff
        counts['strips'] += total
    return counts

def side_read(blob, p):
    h = struct.unpack_from('<4s7I', blob)
    assert h[:2] == (b'R4PW', 1) and h[3:5] == (p['h'][5], p['h'][4])
    assert len(blob) == 32+16*h[3]+52*h[2] and zlib.crc32(blob[32:]) == h[5]
    meta = [struct.unpack_from('<IIHH4B', blob, 32+16*i) for i in range(h[3])]
    places = [struct.unpack_from('<HH12f', blob, 32+16*h[3]+52*i) for i in range(h[2])]
    for r in meta:
        assert r[4] <= 2 and r[5] <= 2 and 0 < r[2] <= 1024 and 0 < r[3] <= 1024
    assert all(r[0] < h[4] and r[1] < h[2] and all(map(math.isfinite, r[2:])) for r in places)
    return h, meta, places

def validate_groups(blob, p, side_crc, padded=False):
    h = struct.unpack_from('<4s7I', blob)
    size = 32+16*h[2]*h[3]
    assert h[:3] == (b'R4SG', 1, p['h'][6]) and 1 <= h[3] <= 8
    assert h[4:7] == (p['h'][3], p['h'][2], side_crc)
    assert size <= len(blob) and h[7] == zlib.crc32(blob[32:size])
    assert (padded and not any(blob[size:])) or size == len(blob)
    groups = 0
    for li, m in enumerate(p['lets']):
        last = 0
        cs = corners(p, m)
        strip_base = m[1]+(2*m[3] if m[4] & 0x8000 else 0)
        for g in range(h[3]):
            r = struct.unpack_from('<7H2B', blob, 32+16*(li*h[3]+g))
            end = r[6]
            if end == last:
                continue
            assert last < end <= m[2] and r[7] <= r[8] < m[3]
            at = last
            while at < end:
                n = p['strip'][strip_base+at]
                assert n >= 3 and at+1+n <= end
                for k in p['strip'][strip_base+at+1:strip_base+at+1+n]:
                    assert r[7] <= k <= r[8]
                    v = p['verts'][cs[k]]
                    assert all(r[a] <= v[a] <= r[a+3] for a in range(3))
                at += n+1
            assert at == end
            last = end
            groups += 1
        assert last == m[2]
    return {'groups_per_meshlet': h[3], 'nonempty_groups': groups,
            'record_crc': '%08x' % h[7], 'logical_bytes': size,
            'allocated_file_bytes': len(blob)}

def state(p, meta, pi):
    part = p['parts'][pi]
    # PS2 path ignores source offset/size and legacy texture index. Preserve
    # all remaining flags and exact UV float bits; include all sidecar fields.
    uv = p['raw'][p['h'][11]+36*pi+20:p['h'][11]+36*pi+36]
    return tuple(meta[pi]), part[3:6], uv.hex()

def traversal(p, meta, places):
    result = []
    for row, pl in enumerate(places):
        m = p['meshes'][pl[0]]
        for render_pass in range(3):
            for pi in range(m[6], m[6]+m[7]):
                if meta[pi][4] != render_pass:
                    continue
                fc, nc = p['plods'][pi]
                for ci in range(fc, fc+nc):
                    # Equal ordered entries with unchanged cluster/level/meshlet
                    # arrays establish arbitrary per-cluster LOD/cull-subset order.
                    result.append((row, pl[0], render_pass, ci, state(p, meta, pi)))
    return result

def patch_mesh(blob, p):
    out = bytearray(blob)
    allowed = set(range(12, 16))
    patches = []
    for _, a, b in PAIRS:
        for offset, old, new in (
            (p['h'][11]+36*a+16, p['parts'][a][7], p['parts'][a][7]+p['parts'][b][7]),
            (p['h'][11]+36*b+16, p['parts'][b][7], 0),
            (p['l'][2]+8*a+4, p['plods'][a][1], p['plods'][a][1]+p['plods'][b][1]),
            (p['l'][2]+8*b+4, p['plods'][b][1], 0)):
            assert struct.unpack_from('<I', out, offset)[0] == old
            struct.pack_into('<I', out, offset, new)
            allowed.update(range(offset, offset+4))
            patches.append({'offset': offset, 'old': old, 'new': new})
    struct.pack_into('<I', out, 12, zlib.crc32(out[80:]))
    changed = [i for i, (a, b) in enumerate(zip(blob, out)) if a != b]
    assert set(changed) <= allowed and len(out) == len(blob)
    return bytes(out), patches, changed

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--gate-manifest', type=Path, required=True)
    ap.add_argument('--runtime-tree', type=Path, required=True)
    ap.add_argument('--resolved-knobs', type=Path, required=True)
    args = ap.parse_args()
    assert not args.out.exists(), 'destination must be new'
    assert args.source.resolve() != args.out.resolve()
    src = {name: (args.source/name).read_bytes() for name in EXPECTED}
    assert {k: sha(v) for k, v in src.items()} == EXPECTED, 'input is not reviewed spatial32v3'
    for name, digest in RUNTIME.items():
        assert sha((args.runtime_tree/name).read_bytes()) == digest, name
    diff = subprocess.check_output(['git', '-C', str(args.runtime_tree), 'diff',
                                   '3e303c5e', 'HEAD', '--', *RUNTIME], text=True)
    assert not diff, 'reviewed runtime files differ from pricing revision'
    knobs_blob = args.resolved_knobs.read_bytes()
    knobs = dict(line.split('=', 1) for line in knobs_blob.decode().splitlines() if '=' in line)
    for key, value in {'PS2_PVS': '0', 'WORLD_VERT': '1', 'WORLD_VERT_LEVEL': '5',
                       'PS2_WORLD_R11F_OWNER': '0', 'PS2_WORLD_TRANSITION_OWNER': '0',
                       'PS2_WORLD_SOURCE_OWNER': '0', 'MESH_LOD': '1'}.items():
        assert knobs[key] == value, (key, knobs.get(key))
    p = mesh_read(src['ps2-wv5.re4mesh'])
    fallback = mesh_read(src['ps2-world.re4mesh'])
    before = validate_mesh(p)
    validate_mesh(fallback)
    assert src['ps2-wv5.re4mesh'][16:] == src['ps2-world.re4mesh'][16:len(src['ps2-wv5.re4mesh'])]
    sh, meta, places = side_read(src['ps2-world.r4pw'], p)
    ih = struct.unpack_from('<4s3I', src['ps2-world.ids'])
    assert ih == (b'R4ID', 1, sh[2], sh[5]) and len(src['ps2-world.ids']) % 32 == 0
    ids = src['ps2-world.ids'][16:16+sh[2]]
    assert len(ids) == len(places)
    gate_blob = args.gate_manifest.read_bytes()
    gate = json.loads(gate_blob)
    gated = {o['placement'] for o in gate['objects']}
    spatial_report = json.loads((args.source/'report.json').read_text())
    assert sorted(gated) == spatial_report['protected_gate_placements'] == list(range(209, 223))
    for o in gate['objects']:
        assert places[o['placement']][0] == o['mesh']
        assert places[o['placement']][1] == o['placement']
        # Manifest em identifies the source object kind, not this independent
        # R4ID byte. Gate rows are protected even when their ID is baked (255).
    protected = {i for i, pl in enumerate(places) if pl[1] <= 2 or pl[1] in gated or ids[pl[1]] < 250}
    protected_meshes = {places[i][0] for i in protected}
    lineage = []
    for mi, a, b in PAIRS:
        m = p['meshes'][mi]
        assert b == a+1 and m[6] <= a < b < m[6]+m[7]
        assert mi not in protected_meshes
        uses = [i for i, pl in enumerate(places) if pl[0] == mi]
        assert uses and all(i not in protected for i in uses)
        assert meta[a] == meta[b] and meta[a][4] == 0
        assert p['parts'][a][2] == 1 and p['parts'][b][2] == 2
        assert p['parts'][a][3:6] == p['parts'][b][3:6] == (255, 0, 0)
        assert state(p, meta, a) == state(p, meta, b)
        pa, pb = p['parts'][a], p['parts'][b]
        la, lb = p['plods'][a], p['plods'][b]
        assert pa[7] and pb[7] and la[1] and lb[1]
        assert pa[6]+pa[7] == pb[6] and la[0]+la[1] == lb[0]
        assert pool(p, pa)[1] == pool(p, pb)[0]
        lineage.append({'mesh': mi, 'parts': [a, b], 'placements': uses,
                        'placement_ids': [places[i][1] for i in uses],
                        'object_ids': [ids[places[i][1]] for i in uses],
                        'part_records_before': [pa, pb], 'part_lods_before': [la, lb],
                        'vertex_pools_before': [pool(p, pa), pool(p, pb)],
                        'sidecar_record': meta[a], 'uv_bits': state(p, meta, a)[2]})
    before_groups = validate_groups(src['ps2-wv5.r4sg'], p, sh[5])
    validate_groups(src['ps2-world.r4sg'], p, sh[5], padded=True)
    out = dict(src)
    patches = {}
    for name, package in (('ps2-wv5.re4mesh', p), ('ps2-world.re4mesh', fallback)):
        out[name], words, offsets = patch_mesh(src[name], package)
        patches[name] = {'uint32_patches': words, 'changed_byte_offsets': offsets,
                         'header_crc_before': '%08x' % package['h'][3],
                         'header_crc_after': '%08x' % struct.unpack_from('<I', out[name], 12)[0]}
    q = mesh_read(out['ps2-wv5.re4mesh'])
    after = validate_mesh(q)
    validate_mesh(mesh_read(out['ps2-world.re4mesh']))
    for name in ('ps2-wv5.r4sg', 'ps2-world.r4sg'):
        g = bytearray(src[name])
        struct.pack_into('<I', g, 16, q['h'][3])
        out[name] = bytes(g)
        assert out[name][:16] == src[name][:16] and out[name][20:] == src[name][20:]
    after_groups = validate_groups(out['ps2-wv5.r4sg'], q, sh[5])
    validate_groups(out['ps2-world.r4sg'], q, sh[5], padded=True)
    assert before_groups == after_groups
    assert out['ps2-world.r4pw'] == src['ps2-world.r4pw']
    assert out['ps2-world.ids'] == src['ps2-world.ids']
    for name in ('meshes', 'lets', 'verts', 'clusters', 'levels', 'strip'):
        assert p[name] == q[name], name
    assert traversal(p, meta, places) == traversal(q, meta, places)
    assert before['nonempty_parts']-after['nonempty_parts'] == 3
    assert all(before[k] == after[k] for k in before if k != 'nonempty_parts')
    for mi in protected_meshes:
        m = p['meshes'][mi]
        for pi in range(m[6], m[6]+m[7]):
            assert p['parts'][pi] == q['parts'][pi] and p['plods'][pi] == q['plods'][pi]
    report = {
        'status': 'HOST_INVARIANTS_PASS_RUNTIME_PRICING_PENDING',
        'scope': 'Three adjacent opaque range pairs; source/runtime untouched; opt-in only',
        'source': str(args.source.resolve()), 'output': str(args.out.resolve()),
        'runtime_revision': '3e303c5e', 'runtime_build': 'cxt16baserW',
        'runtime_elf_sha256_parent_provided': '1f98fe56859c114ad09a818dd4b6f33658c42c73d11229186ec5ad9428cef8c6',
        'runtime_source_sha256': RUNTIME, 'resolved_knobs_sha256': sha(knobs_blob),
        'converter_sha256': sha(Path(__file__).read_bytes()),
        'gate_manifest_sha256': sha(gate_blob), 'gated_placement_ids': sorted(gated),
        'protected_placement_rows': sorted(protected), 'protected_meshes': sorted(protected_meshes),
        'gate_manifest_note': 'Original gate sidecar CRC predates spatial batching; placement and mesh identities independently checked against current sidecar and spatial report. Manifest em is an object kind, not an R4ID byte; gate rows remain protected even when their ID is 255.',
        'files': {name: {'bytes': len(data), 'source_sha256': sha(src[name]),
                         'output_sha256': sha(data), 'same_size': len(data) == len(src[name])}
                  for name, data in out.items()},
        'before': before, 'after': after, 'groups': after_groups, 'pairs': lineage,
        'patches': patches, 'traversal_cluster_instances': len(traversal(p, meta, places)),
        'unchanged': ['all vertex bytes/colors', 'mesh grids/transforms/bounds', 'all meshlets/pool indices',
                      'all strip bytes/winding/order', 'all clusters/bounds', 'all LOD levels/errors',
                      'all sidecar bytes/materials/placements', 'all dynamic IDs', 'all strip-group records',
                      'all six file capacities and allocation inputs', 'ordered cluster instances with per-cluster state'],
        'runtime_admission': 'Python mirror of active MeshPackage and sidecar/ID/group admission, plus stronger group range/bounds and lineage checks; no compiled/runtime validation',
        'empty_rows': 'Parent mesh ranges and total part rows remain unchanged; c.parts and c.native still increment; MeshDraw setup, run, result and end_direct calls remain. Empty rows never reach draw/bind.',
        'savings_claim': '0 to 3 redundant binds/end-direct/cache setups potentially removed when both ranges of each pair draw; no timing or full per-part-fee saving claimed',
        'fallback': 'Padded L0 mesh is valid and same topology. Padded L0 R4SG retains selected-L5 identity and deliberate runtime size mismatch, exactly as source fixture; missing L5 uses ungrouped path.',
        'runtime_constraints': ['Use reviewed cxt16baserW WORLD_VERT_LEVEL=5 runtime and all six assets together',
                                'PS2_PVS=0; external CRC-keyed derived data would need regeneration for other builds',
                                'No transition/R11F/source-owner per-part UV callbacks in reviewed build',
                                'Texture/header counters, cache lifetime, and resource-failure behavior can differ; visual and model checks remain pending'],
    }
    # All validation completes before creating any output asset.
    args.out.mkdir(parents=True)
    assets = args.out/'assets'
    assets.mkdir()
    for name, data in out.items():
        (assets/name).write_bytes(data)
        assert (assets/name).read_bytes() == data
    (args.out/'invariants.json').write_text(json.dumps(report, indent=2)+'\n')
    fixture = {'opt_in_only': True, 'room': 'r101', 'runtime': 'cxt16baserW',
               'replacement_root': str(assets.resolve()),
               'replacements': {f'dc/native/r101/{k}': str((assets/k).resolve()) for k in out},
               'runtime_validation': 'pending; do not publish or promote'}
    (args.out/'fixture.json').write_text(json.dumps(fixture, indent=2)+'\n')
    assert {k: sha((args.source/k).read_bytes()) for k in EXPECTED} == EXPECTED
    print(json.dumps({'status': report['status'], 'output': str(args.out),
                      'nonempty_parts_before': before['nonempty_parts'],
                      'nonempty_parts_after': after['nonempty_parts'],
                      'all_capacities_preserved': True, 'pairs': len(PAIRS)}, indent=2))

if __name__ == '__main__':
    main()
