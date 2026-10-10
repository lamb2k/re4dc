#!/usr/bin/env python3
"""ps2leon: the owner path's admission checks on the generated headers, offline: platform/include/
coarse_actor_preflight.h preflight_chunk (array sizes, palettes <= 256, weights, palette indices, blob header, meshlet
table, records, strips <= 64 indices, triangle counts) for every chunk of ps2leon_runtime.h and every hair run of
ps2leon_hair_runs.h (role 7's positions / normals / weights with the run's UV array and stream), plus the
coarse_skin.h limits (single-bone entries weigh exactly 1.0) and the plan totals.

  preflight.py <dir with ps2leon_runtime.h + ps2leon_hair_runs.h> [more dirs]
  preflight.py --bundle <leon4k_runtime.h> <leon_hair_runs.h>       (today's play headers)
"""
import re, struct, sys
from pathlib import Path

ARRAY = re.compile(r'alignas\(32\)\s+static\s+(?:const\s+)?unsigned\s+char\s+(\w+)\[\]\s*=\s*\{([^}]*)\};', re.S)
WEIGHTS = re.compile(r'static const Weight (\w+)_weights\[\] = \{(.*?)\};', re.S)
CHUNK = re.compile(r'\{(\d+),(\d+),(\d+),(\d+),(\d+),(\d+),(i\d+)_pos,')
RUN = re.compile(r'\{run(\d+),sizeof\(run\d+\),(\d+),(\d+),(\d+)\}')


def arrays(text):
    return {m.group(1): bytes(int(v, 0) for v in m.group(2).replace('\n', '').split(',') if v.strip()) for m in ARRAY.finditer(text)}


def weights(text):
    out = {}
    for m in WEIGHTS.finditer(text):
        rows = []
        for r in re.finditer(r'\{\{(\d+),(\d+),(\d+)\},(\d+),\{([^}]*)\}\}', m.group(2)):
            b = tuple(map(int, r.groups()[:3])); n = int(r.group(4))
            vals = [float.fromhex(v.strip().rstrip('f')) for v in r.group(5).split(',')]
            rows.append((b, n, vals))
        out[m.group(1)] = rows
    return out


def f32(x):
    return struct.unpack('<f', struct.pack('<f', x))[0]


def preflight(pos, nrm, uv, stream, wrows, npos, nnrm, npal, ntri, bones=119):
    if not (0 < npos <= 65535 and 0 < nnrm <= 65535 and 0 < npal <= 256 and len(pos) >= npos * 8 and len(nrm) >= nnrm * 8 and uv and len(uv) % 4 == 0 and len(wrows) >= npal):
        return 'Array'
    for b, n, vals in wrows[:npal]:
        if not 0 < n <= 3:
            return 'Weights'
        s = f32(0.0)
        for k in range(n):
            v = f32(vals[k])
            if b[k] >= bones or v < 0 or v > 1:
                return 'Weights'
            s = f32(s + v)
        if abs(s - 1.0) > 0.0001:
            return 'Weights'
        if n == 1 and f32(vals[0]) != 1.0:
            return 'SkinOneBone'   # coarse_group_build refuses a one-bone entry that does not weigh exactly 1
    for i in range(npos):
        if struct.unpack_from('<H', pos, i * 8 + 6)[0] >= npal:
            return 'Palette'
    for i in range(nnrm):
        if struct.unpack_from('<H', nrm, i * 8 + 6)[0] >= npal:
            return 'Palette'
    s = stream
    if len(s) < 32 or len(s) > 1 << 20:
        return 'Header'
    if s[0] != 0xfe or s[1] != 3 or (s[2] & 0x83) or s[3] or struct.unpack_from('<H', s, 12)[0] or struct.unpack_from('<H', s, 14)[0]:
        return 'Header'
    if struct.unpack_from('<f', s, 28)[0] < 0:
        return 'Header'
    nm = struct.unpack_from('<H', s, 4)[0]; rec = struct.unpack_from('<H', s, 8)[0] * 4; idx = struct.unpack_from('<H', s, 10)[0] * 4
    if not nm or len(s) < 32 + nm * 8 or rec < 32 + nm * 8 or idx < rec or idx > len(s):
        return 'Table'
    records = indices = tris = 0
    longest = 0
    for m in range(nm):
        counts, first, off = struct.unpack_from('<IHH', s, 32 + m * 8)
        nv, ni, nt = counts & 255, (counts >> 8) & 4095, counts >> 20
        if not nv or nv > 128 or not ni or ni > 1024 or not nt or first != records or off != indices:
            return 'Table'
        if (records + nv) * 6 > idx - rec or idx + indices + ni > len(s):
            return 'Table'
        for v in range(nv):
            a, b, c = struct.unpack_from('<3H', s, rec + (records + v) * 6)
            if a >= npos or b >= nnrm or c * 4 >= len(uv):
                return 'Record'
        ln = t = 0
        for j in range(ni):
            x = s[idx + indices + j]
            ln += 1
            if (x & 127) >= nv or ln > 64:
                return 'Strip (length %d)' % ln
            if x & 128:
                if ln < 3:
                    return 'Strip'
                longest = max(longest, ln)
                t += ln - 2; ln = 0
        if ln or t != nt:
            return 'Count'
        records += nv; indices += ni; tris += nt
    if tris != ntri:
        return 'Count'
    return 'None (meshlets %d records %d indices %d longest strip %d)' % (nm, records, indices, longest)


def check(runtime, hair):
    rt, ht = Path(runtime).read_text(), Path(hair).read_text()
    A, W = arrays(rt), weights(rt)
    H = arrays(ht)
    ok = True
    chunks = {}
    for m in CHUNK.finditer(rt):
        info, npos, nnrm, npal, ntri, sb = map(int, m.groups()[:6]); p = m.group(7)
        chunks[info] = (p, npos, nnrm, npal, ntri)
        r = preflight(A[p + '_pos'], A[p + '_nrm'], A[p + '_uv'], A[p + '_gx'], W[p], npos, nnrm, npal, ntri)
        ok &= r.startswith('None')
        print('  chunk %d: tris %4d pos %4d nrm %4d pal %3d stream %5d -> %s' % (info, ntri, npos, nnrm, npal, sb, r))
    p, npos, nnrm, npal, _ = chunks[7]
    for m in RUN.finditer(ht):
        i, ntri, mat, aid = map(int, m.groups())
        r = preflight(A[p + '_pos'], A[p + '_nrm'], H['uv'], H['run%d' % i], W[p], npos, nnrm, npal, ntri)
        ok &= r.startswith('None')
        print('  hair run %d: material %d asset %d tris %4d -> %s' % (i, mat, aid, ntri, r))
    pal = re.search(r'palette_count=(\d+)', ht)
    print('  hair header palette_count %s, chunk 7 palettes %d: %s' % (pal.group(1), npal, 'OK' if int(pal.group(1)) == npal else 'MISMATCH'))
    ok &= int(pal.group(1)) == npal
    print('PREFLIGHT', 'PASS' if ok else 'FAIL')
    return ok


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[0] == '--bundle':
        check(a[1], a[2])
    else:
        for d in a:
            print(d)
            check(Path(d) / 'ps2leon_runtime.h', Path(d) / 'ps2leon_hair_runs.h')
