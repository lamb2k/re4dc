#!/usr/bin/env python3
"""leonlod run-time package (LEON_LOD=1, ps2leon.mk): every Leon rung in one disc file, and the image header without
the rung data.

  lod_pack.py pack <out.re4lp> <name>=<arm dir> ...        (arm dir: pack_arm.py's ps2leon_runtime.h + _hair_runs.h)
  lod_pack.py derive <runtime header> <hair runs header> <package> <out dir>
  lod_pack.py show <package>

The first level is the boot default's reference (arm A = today's Leon). Each level carries roles 0, 1, 2, 3, 4 and 7
(body, jacket, knife, face, head, hair) and the hair run; the hands (roles 5 / 6) stay LEON_HAND_PACK's.

Package (little endian):
  header (64 B)     magic 'LLP1', version 1, level count, the largest level's bytes, directory bytes, file bytes,
                    FNV-1a 32 of every byte after the header, 9 reserved words
  levels (448 B)    name[8]; offset32, bytes; plan palette / workspace bytes (pl00, pl08); hair palette count, hair
                    triangles, material, asset id, hair uv offset / size, hair run offset / size; then per role
                    (0, 1, 2, 3, 4, 7) 16 words: role, positions, normals, palettes, triangles, stream bytes, offsets[5]
                    and sizes[5] of positions | normals | uv | stream | weights (offsets from the level's start)
  level data        each array at a 32-byte boundary; a level starts at a 32-byte boundary
derive: the image header keeps the signatures, bind table, roles 5 / 6 rows (hands) and the constants, and drops the
arrays of roles 0-4 and 7 (their chunk rows read null until the game loads a level); the hair header keeps the run
count and material mask with a writable run row. Plus leon_lod_caps.h: the buffer the game reserves (the largest
level) and the level count.
"""
import re, struct, sys
from pathlib import Path

MAGIC, VERSION = 0x31504C4C, 1
ROLES = (0, 1, 2, 3, 4, 7)
LEVEL_BYTES = 448
ARRAY = re.compile(r'alignas\(32\)\s+static\s+(?:const\s+)?unsigned\s+char\s+(\w+)\[\]\s*=\s*\{([^}]*)\};', re.S)
WEIGHTS = re.compile(r'static const (?:leon4k::)?Weight (\w+)_weights\[\] = \{(.*?)\n\};', re.S)
ROW = re.compile(r'^\{(\d+),(\d+),(\d+),(\d+),(\d+),(\d+),(\w+),(\w+),(\w+),(\w+),(\w+)\},$', re.M)


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
    """prefix -> bytes of `struct Weight { unsigned char bone[3], count; float value[3]; }` rows (16 B each)."""
    out = {}
    for m in WEIGHTS.finditer(text):
        b = bytearray()
        for r in re.finditer(r'\{\{(\d+),(\d+),(\d+)\},(\d+),\{([^}]*)\}\}', m.group(2)):
            vals = [hexf(v) for v in r.group(5).split(',')]
            b += struct.pack('<4B3f', int(r.group(1)), int(r.group(2)), int(r.group(3)), int(r.group(4)), *vals)
        out[m.group(1)] = bytes(b)
    return out


def const(text, name):
    m = re.search(r'\b%s=(\d+)' % name, text)
    return int(m.group(1))


def level(name, d):
    rt = (Path(d) / 'ps2leon_runtime.h').read_text()
    hr = (Path(d) / 'ps2leon_hair_runs.h').read_text()
    A, Wt = arrays(rt), weights(rt)
    rows = {int(m.group(1)): m for m in ROW.finditer(rt)}
    H = arrays(hr)
    run = re.search(r'\{run0,sizeof\(run0\),(\d+),(\d+),(\d+)\}', hr)
    data = bytearray()

    def put(b):
        nonlocal data
        off = len(data)
        data += b + bytes(r32(len(b)) - len(b))
        return off, len(b)
    roles = []
    for r in ROLES:
        m = rows[r]
        offs, sizes = [], []
        for part in ('pos', 'nrm', 'uv', 'gx'):
            o, s = put(A['i%d_%s' % (r, part)]); offs.append(o); sizes.append(s)
        o, s = put(Wt['i%d' % r]); offs.append(o); sizes.append(s)
        pc, nc, pal, tri, sb = (int(m.group(k)) for k in range(2, 7))
        assert s == 16 * pal, (name, r, s, pal)
        assert sizes[3] == sb or True
        roles.append((r, pc, nc, pal, tri, sb, offs, sizes))
    uo, us = put(H['uv'])
    ro, rs = put(H['run0'])
    hdr = dict(name=name, plan=(const(rt, 'plan_palette_bytes'), const(rt, 'plan_workspace_bytes'),
                                const(rt, 'pl08_plan_palette_bytes'), const(rt, 'pl08_plan_workspace_bytes')),
               hair=(const(hr, 'palette_count'), int(run.group(1)), int(run.group(2)), int(run.group(3)), uo, us, ro, rs),
               roles=roles, data=bytes(data))
    assert const(hr, 'run_count') == 1 and const(hr, 'material_mask') == 2, name
    return hdr


def pack(out, specs):
    levels = [level(*s.split('=', 1)) for s in specs]
    dir_bytes = 64 + LEVEL_BYTES * len(levels)
    body, recs, at = bytearray(), [], r32(dir_bytes)
    for L in levels:
        off = at + len(body)
        recs.append((L, off))
        body += L['data'] + bytes(r32(len(L['data'])) - len(L['data']))
    d = bytearray()
    for L, off in recs:
        e = L['name'].encode()[:8].ljust(8, b'\0')
        e += struct.pack('<2I', off // 32, len(L['data'])) + struct.pack('<4I', *L['plan']) + struct.pack('<8I', *L['hair'])
        for r, pc, nc, pal, tri, sb, offs, sizes in L['roles']:
            e += struct.pack('<16I', r, pc, nc, pal, tri, sb, *offs, *sizes)
        assert len(e) == LEVEL_BYTES, len(e)
        d += e
    rest = bytes(d) + bytes(r32(dir_bytes) - dir_bytes) + bytes(body)
    biggest = max(len(L['data']) for L in levels)
    head = struct.pack('<7I', MAGIC, VERSION, len(levels), biggest, dir_bytes, 64 + len(rest), fnv(rest)) + bytes(36)
    Path(out).write_bytes(head + rest)
    print('package %s: %d levels, %d bytes, largest level %d' % (out, len(levels), 64 + len(rest), biggest))
    for L, off in recs:
        print('  %-6s %6d bytes at %d  roles %s hair tri %d' % (L['name'], len(L['data']), off,
              [x[4] for x in L['roles']], L['hair'][1]))


def show(pkg):
    b = Path(pkg).read_bytes()
    m, v, n, big, db, fb, h = struct.unpack_from('<7I', b, 0)
    assert m == MAGIC and v == VERSION and fb == len(b) and fnv(b[64:]) == h, 'bad package'
    print('levels', n, 'largest', big, 'file', fb)
    for i in range(n):
        e = b[64 + i * LEVEL_BYTES:64 + (i + 1) * LEVEL_BYTES]
        name = e[:8].rstrip(b'\0').decode()
        off32, nb = struct.unpack_from('<2I', e, 8)
        print(' ', i, name, off32 * 32, nb, 'plan', struct.unpack_from('<4I', e, 16), 'hair', struct.unpack_from('<8I', e, 32))
    return n, big


def derive(rt_path, hair_path, pkg, out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    n, big = show(pkg)
    t = Path(rt_path).read_text()
    for r in ROLES:
        for part in ('pos', 'nrm', 'uv', 'gx'):
            t, k = re.subn(r'alignas\(32\)\s+static\s+const\s+unsigned\s+char\s+i%d_%s\[\]\s*=\s*\{[^}]*\};\n' % (r, part), '', t)
            assert k == 1, (r, part)
        t, k = re.subn(r'static const Weight i%d_weights\[\] = \{.*?\n\};\n' % r, '', t, flags=re.S)
        assert k == 1, r
        t, k = re.subn(r'^\{%d,(\d+),(\d+),(\d+),(\d+),(\d+),i%d_pos,i%d_nrm,i%d_uv,i%d_gx,i%d_weights\},$' % ((r,) * 6),
                       '{%d,0,0,0,0,0,nullptr,nullptr,nullptr,nullptr,nullptr},' % r, t, flags=re.M)
        assert k == 1, r
    t = t.replace('#pragma once', '#pragma once\n// leonlod lod_pack.py derive: roles 0-4 and 7 come from the LEON_LOD package at run time.', 1)
    (out / 'ps2leon_runtime_lod.h').write_text(t)
    h = Path(hair_path).read_text()
    pc = const(h, 'palette_count')
    asset = re.search(r'\{run0,sizeof\(run0\),\d+,(\d+),(\d+)\}', h)
    hd = ('// leonlod lod_pack.py derive of ps2leon_hair_runs.h: the hair run comes from the LEON_LOD package.\n'
          '#pragma once\nnamespace leon_hair_runs {\n'
          'struct Run { const unsigned char* stream; unsigned bytes,triangles,material,asset_id; };\n'
          'static Run runs[] = {\n{nullptr,0,0,%s,%s},\n};\n'
          'static constexpr unsigned role=7,run_count=1,material_mask=2,boot_palette_count=%d;\n}\n') % (asset.group(1), asset.group(2), pc)
    (out / 'ps2leon_hair_runs_lod.h').write_text(hd)
    (out / 'leon_lod_caps.h').write_text('#pragma once\n// lod_pack.py derive from %s\nnamespace leon_lod_caps {\n'
                                         'constexpr unsigned levels=%d,buffer_bytes=%d,magic=0x%08xu,version=%d,level_record=%d;\n}\n'
                                         % (Path(pkg).name, n, r32(big), MAGIC, VERSION, LEVEL_BYTES))
    print('derived into', out)


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'pack':
        pack(sys.argv[2], sys.argv[3:])
    elif cmd == 'show':
        show(sys.argv[2])
    elif cmd == 'derive':
        derive(*sys.argv[2:6])
    else:
        raise SystemExit(__doc__)
