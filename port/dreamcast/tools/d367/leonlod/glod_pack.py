#!/usr/bin/env python3
"""leonlod GANADO_LOD run-time package: every Ganado mesh rung of the PS2 cast in one disc file, and the image header
without the rung data.

  glod_pack.py pack <out.re4gl> <bundle header> <name>=<rung dir> ...
  glod_pack.py derive <bundle header> <package> <out dir>
  glod_pack.py show <package>

<bundle header>  the play bundle's ganado_cast_runtime.h (PS2_GANADO_DIR; cast_bundle.py): its appearance order and,
                 for the first level, its own arrays (level 0 = today's Ganados, byte for byte).
<rung dir>       glod_rung.py + glod_native.sh output: <rung>/<appearance>/runtime/castmodel_runtime.h. The first
                 level is given as `today=bundle` (the bundle header's arrays).

Each level carries roles 0 (body) and 1 (head) of every appearance; the hands (roles 2 / 3) stay in the image (the
hand-pose slots). The skeleton, bind, signatures and atlas are the bundle's.

Package (little endian):
  header (64 B)    magic 'GLP1', version 1, level count, the largest level's bytes, directory bytes, file bytes,
                   FNV-1a 32 of every byte after the header, appearance count, 8 reserved words
  levels           name[8]; offset32, bytes, skin stream bytes (coarse_group_build of every chunk of the level, hands
                   included), reserved; then per appearance and role (0, 1) 16 words: role, positions, normals,
                   palettes, triangles, stream bytes, offsets[5] and sizes[5] of positions | normals | uv | stream |
                   weights (from the level's start)
  level data       each array at a 32-byte boundary; a level starts at a 32-byte boundary
derive: ganado_cast_runtime_lod.h = the bundle header without the role 0 / 1 arrays (their chunk rows read null until
the game loads a level), and ganado_lod_caps.h (buffer = the largest level, level count, record size).
"""
import re, struct, sys
from pathlib import Path

MAGIC, VERSION = 0x31504C47, 1
ROLES = (0, 1)
ARRAY = re.compile(r'alignas\(32\)\s+static\s+(?:const\s+)?unsigned\s+char\s+(\w+)\[\]\s*=\s*\{([^}]*)\};', re.S)
WEIGHTS = re.compile(r'static const (?:\w+::)?Weight (\w+)_weights\[\] = \{(.*?)\n\};', re.S)


def fnv(b):
    h = 0x811C9DC5
    for x in b:
        h = ((h ^ x) * 0x01000193) & 0xFFFFFFFF
    return h


def r32(n):
    return (n + 31) & ~31


def hexf(s):
    s = s.strip().rstrip('f')
    return float.fromhex(s) if 'p' in s or 'x' in s else float(s)


def arrays(text):
    return {m.group(1): bytes(int(v, 0) for v in m.group(2).replace('\n', '').split(',') if v.strip())
            for m in ARRAY.finditer(text)}


def weights(text):
    """prefix -> (bytes of 16-byte Weight rows, [(count, bones)] rows)."""
    out = {}
    for m in WEIGHTS.finditer(text):
        b, rows = bytearray(), []
        for r in re.finditer(r'\{\{(\d+),(\d+),(\d+)\},(\d+),\{([^}]*)\}\}', m.group(2)):
            vals = [hexf(v) for v in r.group(5).split(',')]
            bones = (int(r.group(1)), int(r.group(2)), int(r.group(3)))
            c = int(r.group(4))
            b += struct.pack('<4B3f', *bones, c, *vals)
            rows.append((c, bones[:c]))
        out[m.group(1)] = (bytes(b), rows)
    return out


def group_bytes(rows):
    """coarse_skin.h coarse_group_build: one 16-byte header per (count, bones) group + 24 bytes per entry (as
    ps2leon pack_arm.py; checked against the bundle's skin_stream_bytes)."""
    return 16 * len(set(rows)) + 24 * len(rows)


def bundle(path):
    t = Path(path).read_text()
    names = re.search(r'appearance_names\[\d+\] = \{([^}]*)\}', t).group(1).replace('"', '').replace(' ', '').split(',')
    rows = re.findall(r'\{(\d+),(\d+),(\d+),(\d+),(\d+),(\d+),(a(\d+)_i(\d+))_pos,\w+,\w+,\w+,\w+\}', t)
    chunk = {(int(r[7]), int(r[8])): tuple(int(x) for x in r[:6]) for r in rows}
    skin = int(re.search(r'skin_stream_bytes=(\d+);', t).group(1))
    return t, names, chunk, skin


def app_source(name, d, k, bundle_text, bchunk):
    """(arrays, weights, chunk rows) of appearance k: from the bundle (d None) or a rung's castmodel_runtime.h."""
    if d is None:
        A, W = arrays(bundle_text), weights(bundle_text)
        get = lambda r, part: A['a%d_i%d_%s' % (k, r, part)]
        getw = lambda r: W['a%d_i%d' % (k, r)]
        rows = {r: bchunk[(k, r)] for r in range(4)}
    else:
        t = (Path(d) / name / 'runtime' / 'castmodel_runtime.h').read_text()
        A, W = arrays(t), weights(t)
        get = lambda r, part: A['i%d_%s' % (r, part)]
        getw = lambda r: W['i%d' % r]
        rows = {}
        for m in re.finditer(r'^\{(\d+),(\d+),(\d+),(\d+),(\d+),(\d+),i(\d+)_pos', t, re.M):
            rows[int(m.group(7))] = tuple(int(m.group(g)) for g in range(1, 7))
    return get, getw, rows


def level(spec, bpath):
    name, src = spec.split('=', 1)
    bt, names, bchunk, bskin = bundle(bpath)
    d = None if src == 'bundle' else src
    data, roles, skin = bytearray(), [], 0

    def put(b):
        nonlocal data
        off = len(data)
        data += b + bytes(r32(len(b)) - len(b))
        return off, len(b)
    for k, app in enumerate(names):
        get, getw, rows = app_source(app, d, k, bt, bchunk)
        for r in range(4):
            skin += group_bytes(getw(r)[1])
        for r in ROLES:
            si, pc, nc, pal, tri, sb = rows[r]
            assert si == r, (name, app, r, si)
            offs, sizes = [], []
            for part in ('pos', 'nrm', 'uv', 'gx'):
                o, s = put(get(r, part)); offs.append(o); sizes.append(s)
            wb, wrows = getw(r)
            o, s = put(wb); offs.append(o); sizes.append(s)
            assert s == 16 * pal == 16 * len(wrows), (name, app, r)
            assert sizes[3] == sb, (name, app, r, sizes[3], sb)
            if d is not None:   # a rung never has more palettes / triangles than today's chunk
                assert pal <= bchunk[(k, r)][3] and tri <= bchunk[(k, r)][4], (name, app, r)
            roles.append((r, pc, nc, pal, tri, sb, offs, sizes))
        if d is not None:   # the hands of a rung must be today's (they stay in the image)
            bget, bgetw, brows = app_source(app, None, k, bt, bchunk)
            for r in (2, 3):
                assert rows[r] == brows[r] and all(get(r, p) == bget(r, p) for p in ('pos', 'nrm', 'uv', 'gx')), (name, app, r)
    return dict(name=name, roles=roles, data=bytes(data), skin=skin, apps=len(names), bskin=bskin)


def pack(out, bpath, specs):
    levels = [level(s, bpath) for s in specs]
    assert levels[0]['skin'] == levels[0]['bskin'], ('skin formula', levels[0]['skin'], levels[0]['bskin'])
    for L in levels:
        assert L['skin'] <= levels[0]['bskin'], (L['name'], L['skin'])
    napps = levels[0]['apps']
    level_bytes = 8 + 16 + 64 * 2 * napps
    dir_bytes = 64 + level_bytes * len(levels)
    body, recs, at = bytearray(), [], r32(dir_bytes)
    for L in levels:
        off = at + len(body)
        recs.append((L, off))
        body += L['data'] + bytes(r32(len(L['data'])) - len(L['data']))
    d = bytearray()
    for L, off in recs:
        e = L['name'].encode()[:8].ljust(8, b'\0') + struct.pack('<4I', off // 32, len(L['data']), L['skin'], 0)
        for r, pc, nc, pal, tri, sb, offs, sizes in L['roles']:
            e += struct.pack('<16I', r, pc, nc, pal, tri, sb, *offs, *sizes)
        assert len(e) == level_bytes
        d += e
    rest = bytes(d) + bytes(r32(dir_bytes) - dir_bytes) + bytes(body)
    biggest = max(len(L['data']) for L in levels)
    head = struct.pack('<8I', MAGIC, VERSION, len(levels), biggest, dir_bytes, 64 + len(rest), fnv(rest), napps) + bytes(32)
    Path(out).write_bytes(head + rest)
    print('package %s: %d levels, %d bytes, largest level %d' % (out, len(levels), 64 + len(rest), biggest))
    for L, off in recs:
        tri = [x[4] for x in L['roles']]
        print('  %-6s %6d bytes at %6d skin %5d  body+head triangles %s (sum %d)' % (L['name'], len(L['data']), off, L['skin'],
              tri, sum(tri)))


def show(pkg):
    b = Path(pkg).read_bytes()
    m, v, n, big, db, fb, h, napps = struct.unpack_from('<8I', b, 0)
    assert m == MAGIC and v == VERSION and fb == len(b) and fnv(b[64:]) == h, 'bad package'
    level_bytes = 8 + 16 + 64 * 2 * napps
    print('levels', n, 'appearances', napps, 'largest', big, 'file', fb)
    for i in range(n):
        e = b[64 + i * level_bytes:64 + (i + 1) * level_bytes]
        name = e[:8].rstrip(b'\0').decode()
        off32, nb, skin, _ = struct.unpack_from('<4I', e, 8)
        tri = [struct.unpack_from('<16I', e, 24 + 64 * j)[4] for j in range(2 * napps)]
        print(' ', i, name, off32 * 32, nb, 'skin', skin, 'triangles', tri)
    return n, big, napps, level_bytes


def derive(bpath, pkg, out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    n, big, napps, level_bytes = show(pkg)
    t = Path(bpath).read_text()
    _, names, _, _ = bundle(bpath)
    assert len(names) == napps
    for k in range(napps):
        for r in ROLES:
            for part in ('gx', 'nrm', 'pos', 'uv'):
                t, c = re.subn(r'alignas\(32\)\s+static\s+(?:const\s+)?unsigned\s+char\s+a%d_i%d_%s\[\]\s*=\s*\{[^}]*\};\n' % (k, r, part), '', t)
                assert c == 1, (k, r, part)
            t, c = re.subn(r'static const Weight a%d_i%d_weights\[\] = \{.*?\n\};\n' % (k, r), '', t, flags=re.S)
            assert c == 1, (k, r)
            p = 'a%d_i%d' % (k, r)
            t, c = re.subn(r'\{%d,\d+,\d+,\d+,\d+,\d+,%s_pos,%s_nrm,%s_uv,%s_gx,%s_weights\}' % (r, p, p, p, p, p),
                           '{%d,0,0,0,0,0,nullptr,nullptr,nullptr,nullptr,nullptr}' % r, t)
            assert c == 1, (k, r)
    t = t.replace('#pragma once', '#pragma once\n// leonlod glod_pack.py derive: roles 0 / 1 (body, head) of every appearance come from the '
                  'GANADO_LOD package at run time.', 1)
    (out / 'ganado_cast_runtime_lod.h').write_text(t)
    (out / 'ganado_lod_caps.h').write_text('#pragma once\n// glod_pack.py derive from %s\nnamespace ganado_lod_caps {\n'
                                           'constexpr unsigned levels=%d,buffer_bytes=%d,magic=0x%08xu,version=%d,level_record=%d,'
                                           'appearances=%d;\n}\n' % (Path(pkg).name, n, r32(big), MAGIC, VERSION, level_bytes, napps))
    print('derived into', out)


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    if cmd == 'pack':
        pack(sys.argv[2], sys.argv[3], sys.argv[4:])
    elif cmd == 'show':
        show(sys.argv[2])
    elif cmd == 'derive':
        derive(*sys.argv[2:5])
    else:
        raise SystemExit(__doc__)
