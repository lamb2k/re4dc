#!/usr/bin/env python3
"""ps2leon: pack an approved render mesh (mesh.json) into the two private runtime headers PS2_LEON includes, with the
existing tools only: character-prototype pack_coarse_actor.py (native arrays, palettes) and the cl lane's fastpath
build_blob.py / verify_blob.py / patch_header.py (FE/v3 meshlet blobs), as today's play bundle was made.

  pack_arm.py <mesh.json> <out dir> [--today]

Writes <out>/native (pack output), <out>/blob (meshlets), <out>/ps2leon_runtime.h (namespace leon4k, the
leon4k_runtime.h API: chunks, weights, signatures, bind + the plan constants the PS2_LEON code reads) and
<out>/ps2leon_hair_runs.h (namespace leon_hair_runs, the leon_hair_runs.h API: role 7's draw as one owned run per hair
material, material 2 first as CHARBAKE_HAIR's leon_hair_runs_g2.h, each restripified by build_blob.py; the runs' UV
array holds each corner's UV in its hair image, the triangles' src_uv / material from the mesh), plus report.json.
The signatures and the bind table are today's (the game's GC infos and skeleton do not change).

--today: the mesh is today's leon-hair-v2 mesh.json; the hair runs' src_uv / material are recovered from the atlas
UVs (inverse of build_leon_4k.py's tile map) and every array is compared with the play bundle's leon4k_runtime.h and
leon_hair_runs.h (a check that this pipeline reproduces the play assets).
"""
import hashlib, importlib.util, json, re, struct, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import leon_sources as ls  # noqa: E402

PROTO = ls.PROTO
FAST = PROTO / 'tools/fastpath'
BUNDLE = ls.PRIV / 'play-actor-bundle-20260928'
TODAY_RUNTIME = BUNDLE / 'leon4k_runtime.h'
TODAY_HAIR = BUNDLE / 'leon_hair_runs.h'
TILES = json.loads((PROTO / 'deliverables/leon-4k/asset-report.json').read_text())['source_uv_tiles']
HAIR_TILE = {'ac381b1a-3ade84b1': 1, '7a9de1fd-0e415f15': 2}
# the frozen pl08 header the ACTOR_PL08_PACK identity was generated from (same chunk fields: 797/859/214/1138, 24/34/2/27,
# 54/60/3/94 at source infos 0, 1, 6 = pl08 roles 0, 1, 8)
PL08_FROZEN = ls.PRIV / 'architect-review-20261003/tools/supervisor-20261003/native-scene/pl08/leon_pl08_runtime.h'
ARRAY = re.compile(r'alignas\(32\)\s+static\s+(?:const\s+)?unsigned\s+char\s+(\w+)\[\]\s*=\s*\{([^}]*)\};', re.S)
WEIGHTS = re.compile(r'static const Weight (\w+)_weights\[\] = \{(.*?)\};', re.S)


def sha(b):
    return hashlib.sha256(b).hexdigest()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def c_arrays(text):
    return {m.group(1): bytes(int(v, 0) for v in m.group(2).replace('\n', '').split(',') if v.strip()) for m in ARRAY.finditer(text)}


def weight_rows(text):
    """prefix -> [(bones tuple, count)] of each `static const Weight <prefix>_weights[]` table."""
    out = {}
    for m in WEIGHTS.finditer(text):
        rows = []
        for r in re.finditer(r'\{\{(\d+),(\d+),(\d+)\},(\d+),', m.group(2)):
            b0, b1, b2, c = map(int, r.groups())
            rows.append(((b0, b1, b2)[:c], c))
        out[m.group(1)] = rows
    return out


def group_bytes(rows):
    """coarse_skin.h coarse_group_build: one 16-byte header per (count, bones) group + 24 bytes per entry."""
    return 16 * len({(c, b) for b, c in rows}) + 24 * len(rows)


def r32(x):
    return (x + 31) & ~31


def src_uv_from_atlas(u, v):
    """inverse of build_leon_4k.py's tile map: mesh.json atlas UV -> (GC-convention UV in its image, image key)."""
    x, y = u * 512, (1 - v) * 512
    for k, t in TILES.items():
        if t['x'] <= x < t['x'] + t['width'] and t['y'] <= y < t['y'] + t['height']:
            return ((x - t['x'] - 2) / t['inner_width'], 1 - (y - t['y'] - 2) / t['inner_height']), k.replace('SourceTex_', '')
    raise ValueError((u, v))


def uv_excess(uvs):
    ex = 0
    for u, v in uvs:
        for a in (abs(u), abs(v)):
            if not a:
                continue
            while not (a & 1):
                a >>= 1
            if a.bit_length() > 8:
                ex = max(ex, a.bit_length() - 8)
    return ex


def byte_array(name, data, writable=False):
    t = 'alignas(32) static ' + ('' if writable else 'const ') + 'unsigned char %s[] = {\n' % name
    return t + ''.join(','.join(str(b) for b in data[i:i + 24]) + ',\n' for i in range(0, len(data), 24)) + '};\n'


def run(*cmd):
    r = subprocess.run([sys.executable, *map(str, cmd)], capture_output=True, text=True)
    if r.returncode:
        raise SystemExit('failed: %s\n%s%s' % (' '.join(map(str, cmd)), r.stdout, r.stderr))
    return r.stdout


def hair_runs(mesh, native, bb, today):
    """role 7's triangles (mesh order = info7.gx order) -> one blob per material, material 2 first."""
    g = (native / 'info7.gx').read_bytes()
    n = struct.unpack('>H', g[1:3])[0]
    corners = [struct.unpack('>3H', g[3 + 6 * k:9 + 6 * k]) for k in range(n)]
    hair = [t for t in mesh['triangles'] if t['source_info'] == 7]
    assert len(hair) * 3 == n
    uvs, uvid, tris = [], {}, []
    for k, t in enumerate(hair):
        if today:
            su = [src_uv_from_atlas(*c['uv']) for c in t['corners']]
            mats = {HAIR_TILE[key] for _, key in su}
            assert len(mats) == 1
            mat, st = mats.pop(), [s for s, _ in su]
        else:
            mat, st = t['material'], [c['src_uv'] for c in t['corners']]
        # the hair images repeat: shift the whole triangle by whole images so every corner is >= 0 (u16 UV words)
        du = -min(0, int(min(s[0] for s in st) // 1)); dv = -min(0, int(min(s[1] for s in st) // 1))
        tc = []
        for j, s in enumerate(st):
            w = (round((s[0] + du) * 32768), round((s[1] + dv) * 32768))
            assert 0 <= w[0] <= 65535 and 0 <= w[1] <= 65535, w
            if w not in uvid:
                uvid[w] = len(uvs); uvs.append(w)
            vi, ni, _ = corners[3 * k + j]
            tc.append((vi, ni, uvid[w]))
        tris.append((mat, tuple(tc)))
    uvb = b''.join(struct.pack('<2H', *w) for w in uvs)
    main_blob = (native.parent / 'blob' / 'info7.meshlets').read_bytes()
    bounds = main_blob[16:32]
    flags = min(uv_excess(uvs), 31) << 2
    blobs, rows = [], []
    for m in (2, 1):
        sel = [tc for mm, tc in tris if mm == m]
        if not sel:
            continue
        with tempfile.TemporaryDirectory(prefix='ps2leon-hair-') as d:
            d = Path(d)
            cs = [c for t in sel for c in t]
            (d / 'info0.gx').write_bytes(bytes([0x90]) + struct.pack('>H', len(cs)) + b''.join(struct.pack('>3H', *c) for c in cs))
            (d / 'info0.pos').write_bytes((native / 'info7.pos').read_bytes())
            (d / 'info0.nrm').write_bytes((native / 'info7.nrm').read_bytes())
            (d / 'info0.uv').write_bytes(uvb)
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
        blob[2] = flags            # one uv excess for the hair's whole UV array
        blob[16:32] = bounds       # the full-hair bounds: the fog gate decides the hair as a whole, as today's runs
        blob = bytes(blob) + bytes((-len(blob)) % 32)
        blobs.append(blob)
        rows.append(dict(material=m, asset_id=29 + len(rows), triangles=len(sel), pinned=len(ch.pinned), seed=mode, w_dist=wd, **st))
    out = ['// Private generated (ps2leon pack_arm.py): role 7 drawn as one owned run per hair material, restripified by the\n'
           '// fastpath build_blob.py. No copied positions, normals or weights (they are ps2leon_runtime.h chunk 7).\n'
           '#pragma once\nnamespace leon_hair_runs {\n', byte_array('uv', uvb)]
    for i, b in enumerate(blobs):
        out.append(byte_array('run%d' % i, b))
    out.append('struct Run { const unsigned char* stream; unsigned bytes,triangles,material,asset_id; };\nstatic const Run runs[] = {\n')
    for i, r in enumerate(rows):
        out.append('{run%d,sizeof(run%d),%d,%d,%d},\n' % (i, i, r['triangles'], r['material'], r['asset_id']))
    pal = len({struct.unpack_from('<3hH', (native / 'info7.pos').read_bytes(), 8 * k)[3] for k in range(len((native / 'info7.pos').read_bytes()) // 8)})
    out.append('};\nstatic constexpr unsigned role=7,palette_count=%d,run_count=%d;\n}\n' % (pal, len(rows)))
    return ''.join(out), dict(uv_entries=len(uvs), flags=flags, runs=rows, tris=tris, uvs=uvs)


def main():
    a = sys.argv[1:]
    today = '--today' in a
    a = [x for x in a if x != '--today']
    mesh_path, out = Path(a[0]), Path(a[1])
    out.mkdir(parents=True, exist_ok=True)
    mesh = json.loads(mesh_path.read_text())
    pca = load('pack_coarse_actor', PROTO / 'tools/pack_coarse_actor.py')
    native, blobd = out / 'native', out / 'blob'
    pca.pack(mesh_path, ls.LEON_SOURCE, native, 'leon4k')
    print(run(FAST / 'build_blob.py', native, blobd, '--report', out / 'blob-report.json'))
    print(run(FAST / 'verify_blob.py', blobd, blobd))
    tmp = out / 'runtime.tmp.h'
    print(run(FAST / 'patch_header.py', native / 'leon4k_native.h', blobd, tmp))
    head = tmp.read_text()
    ref = TODAY_RUNTIME.read_text()
    tail = ref[ref.index('struct SourceSignature'):].rsplit('}', 1)[0]
    nrep = json.loads((native / 'native-report.json').read_text())
    pals = {c['info']: c['palettes'] for c in nrep['chunks']}
    assert sorted(pals) == list(range(8))
    rows = weight_rows(head)
    plan_palette = sum(r32(pals[i] * 48) for i in range(8))
    plan_workspace = max(r32(pals[i] * 114) for i in range(8))
    shared_palette = sum(r32(pals[i] * 48) for i in range(2, 8))
    shared_workspace = max(r32(pals[i] * 114) for i in range(2, 8))
    skin_pl00 = sum(group_bytes(rows['i%d' % i]) for i in range(8))
    skin_shared = sum(group_bytes(rows['i%d' % i]) for i in range(2, 8))
    # pl08's own roles 0, 1, 8 (the frozen pl08 header: i0 / i1 / i6; the ACTOR_PL08_PACK package carries the same
    # tables, actor_pl08_pack_identity.inc): palettes 214, 2, 3 (coarse_actor_owner_pl08.inc)
    p8 = weight_rows(PL08_FROZEN.read_text())
    p8 = {'r0': p8['i0'], 'r1': p8['i1'], 'r8': p8['i6']}
    pl08_own = {k: len(v) for k, v in p8.items()}
    assert pl08_own == {'r0': 214, 'r1': 2, 'r8': 3}, pl08_own
    skin_pl08 = skin_shared + sum(group_bytes(p8[k]) for k in ('r0', 'r1', 'r8'))
    pl08_palette = sum(r32(len(p8[k]) * 48) for k in ('r0', 'r1', 'r8')) + shared_palette
    pl08_workspace = max([shared_workspace] + [r32(len(p8[k]) * 114) for k in ('r0', 'r1', 'r8')])
    skin_stream = max(24576, r32(max(skin_pl00, skin_pl08)))
    consts = ('// ps2leon (PS2_LEON): the plan constants coarse_actor_owner_leon.inc / _pl08.inc / coarse_actor.cpp check\n'
              '// instead of leon4k\'s literals (32000 / 26112, pl08 26144 / 26112, skin stream 24576).\n'
              'static constexpr unsigned plan_palette_bytes=%d,plan_workspace_bytes=%d;\n'
              'static constexpr unsigned pl08_plan_palette_bytes=%d,pl08_plan_workspace_bytes=%d;\n'
              'static constexpr unsigned skin_stream_bytes=%d; // max(24576, pl00 %d, pl08 %d)\n'
              % (plan_palette, plan_workspace, pl08_palette, pl08_workspace, skin_stream, skin_pl00, skin_pl08))
    # the play bundle's form: the meshlet streams are const (.rodata) and Chunk::stream a const pointer
    head = head.replace('unsigned char *stream;', 'const unsigned char *stream;', 1)
    head = re.sub(r'alignas\(32\) static unsigned char (i\d+_gx)\[\]', r'alignas(32) static const unsigned char \1[]', head)
    text = head.rsplit('}', 1)[0] + tail + consts + '}\n'
    text = text.replace('// Private generated asset. Do not commit.', '// Private generated asset (ps2leon pack_arm.py from %s). Do not commit.' % mesh_path.name, 1)
    (out / 'ps2leon_runtime.h').write_text(text)
    tmp.unlink()
    bb = load('build_blob', FAST / 'build_blob.py')
    htext, hrep = hair_runs(mesh, native, bb, today)
    (out / 'ps2leon_hair_runs.h').write_text(htext)
    arrays = c_arrays(text)
    data = {k: len(v) for k, v in arrays.items()}
    rep = dict(mesh=str(mesh_path), mesh_sha256=sha(mesh_path.read_bytes()), triangles=nrep['triangles'],
               chunks=[dict(info=c['info'], triangles=c['triangles'], positions=c['positions'], normals=c['normals'], uvs=c['uvs'],
                            palettes=c['palettes'], blob_bytes=data['i%d_gx' % c['info']]) for c in nrep['chunks']],
               plan_palette_bytes=plan_palette, plan_workspace_bytes=plan_workspace, pl08_plan_palette_bytes=pl08_palette,
               pl08_plan_workspace_bytes=pl08_workspace, skin_stream_pl00=skin_pl00, skin_stream_pl08=skin_pl08,
               skin_stream_bytes=skin_stream, pl08_own_palettes=pl08_own,
               runtime_array_bytes=sum(data.values()) + sum(16 * pals[i] for i in range(8)),
               hair_array_bytes=sum(len(v) for v in c_arrays(htext).values()),
               hair=dict(uv_entries=hrep['uv_entries'], flags=hrep['flags'], runs=hrep['runs']),
               headers={n: sha((out / n).read_bytes()) for n in ('ps2leon_runtime.h', 'ps2leon_hair_runs.h')},
               tools={n: sha(p.read_bytes()) for n, p in (('pack_coarse_actor.py', PROTO / 'tools/pack_coarse_actor.py'),
                      ('build_blob.py', FAST / 'build_blob.py'), ('verify_blob.py', FAST / 'verify_blob.py'),
                      ('patch_header.py', FAST / 'patch_header.py'), ('pack_arm.py', Path(__file__)))})
    if today:
        refa = c_arrays(ref)
        cmp = {}
        for k, v in refa.items():
            cmp[k] = 'SAME' if arrays.get(k) == v else ('MISSING' if k not in arrays else 'DIFF %d vs %d bytes' % (len(arrays[k]), len(v)))
        rep['today_runtime_arrays'] = cmp
        rep['today_weights_same'] = weight_rows(ref) == rows

        def skeleton(t):
            """the header without its data: every declaration and the chunk table, minus the first comment line and the
            appended ps2leon constants."""
            t = re.sub(r'\{\n[0-9,\n]*\};', '{...};', t)
            t = re.sub(r'(static const (?:Weight \w+|SourceSignature signatures)\[\] = )\{.*?\};', r'\1{...};', t, flags=re.S)
            t = re.sub(r'(static const float bind\[\d+\]\[12\] = )\{.*?\};', r'\1{...};', t, flags=re.S)
            skip = ('// ps2leon', '// instead of', 'static constexpr unsigned plan_', 'static constexpr unsigned pl08_', 'static constexpr unsigned skin_')
            return [l for l in t.splitlines()[1:] if not l.startswith(skip)]
        rep['today_header_skeleton_same'] = skeleton(ref) == skeleton(text)
        rep['today_chunks_same'] = re.findall(r'\{(\d+,\d+,\d+,\d+,\d+,\d+),i\d+_pos', ref) == re.findall(r'\{(\d+,\d+,\d+,\d+,\d+,\d+),i\d+_pos', text)
        # hair: per triangle (positions, uv words, material) as a multiset vs the play runs
        hb = c_arrays(TODAY_HAIR.read_text())
        sys.path.insert(0, str(ls.TREE / 'port/dreamcast/tools/d367/charbake'))
        from cb_blob import Blob, canon  # noqa
        P = (native / 'info7.pos').read_bytes()
        pos = [struct.unpack_from('<3hH', P, 8 * k)[:3] for k in range(len(P) // 8)]
        tuv = [struct.unpack_from('<2H', hb['uv'], 4 * k) for k in range(len(hb['uv']) // 4)]
        want = []
        for m in re.finditer(r'\{run(\d+),sizeof\(run\d+\),(\d+),(\d+),(\d+)\}', TODAY_HAIR.read_text()):
            i, ntri, mat, aid = map(int, m.groups())
            for t in Blob(hb['run%d' % i]).triangles():
                if t:
                    want.append((mat, canon(tuple((pos[c[0]], tuv[c[2]]) for c in t))))
        got = [(mat, canon(tuple((pos[c[0]], hrep['uvs'][c[2]]) for c in tc))) for mat, tc in hrep['tris']]
        exact = sorted(got) == sorted(want)
        def close(a, b):
            return a[0] == b[0] and all(pa[0] == pb[0] and abs(pa[1][0] - pb[1][0]) <= 2 and abs(pa[1][1] - pb[1][1]) <= 2 for pa, pb in zip(a[1], b[1]))
        ws = sorted(want); gs = sorted(got)
        near = len(ws) == len(gs) and all(close(x, y) for x, y in zip(gs, ws))
        rep['today_hair'] = dict(exact=exact, within_2_uv_units=near, triangles=len(got), play_flags=Blob(hb['run0']).flags, flags=hrep['flags'])
    (out / 'report.json').write_text(json.dumps(rep, indent=1))
    print(json.dumps({k: v for k, v in rep.items() if k not in ('chunks', 'hair', 'tools', 'today_runtime_arrays')}, indent=1))
    if today:
        print(json.dumps(rep['today_runtime_arrays']))


if __name__ == '__main__':
    main()
