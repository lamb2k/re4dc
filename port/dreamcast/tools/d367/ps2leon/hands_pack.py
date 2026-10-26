#!/usr/bin/env python3
"""ps2leon hand package (issue #26, 2026-10-13; crowd.mk LEON_HAND_PACK): every hand pose of one outfit as a disc
package that the game reads into a small fixed cache, instead of 100 KB of hand tables in the image.

  hands_pack.py pack <ps2leon_runtime.h> <hands dir> <inventory.json> <out.re4hp> [--report out.json]
  hands_pack.py derive <ps2leon_runtime.h> <out header>
  hands_pack.py show <package.re4hp>
  hands_pack.py addkey <in.re4hp> <out.re4hp> <role> <positions> <normals> <palette> <vertex_hash> <blob>

pack: the arm's standard hands (roles 5 / 6 of ps2leon_runtime.h: i5_* / i6_*) plus every pose of build_hands.py's
ps2leon_hands.h (its report-hands.json gives each pose's GC sources), in one file:
  header (32 B)  magic 'LHP1', version 1, row / blob / source counts, slot caps, directory bytes, file bytes, FNV-1a
                 of everything after the header
  rows   (12 B)  role, blob, then the GC runtime key (positions, normals, palette, vertex_hash); keys may share a blob
  blobs  (24 B)  role, flags (1 standard, 2 home), counts (positions, normals, palette, triangles), the five array
                 sizes, stream bytes, file offset / 32; the blob bytes are positions | normals | uv | stream | weights, each
                 array at a 32-byte boundary
  sources (4 B)  GC archive -> blob, for the prefetch at a weapon equip: weapon number (wepNN = NN, pl0e = 0x8e,
                 pl0f = 0x8f), arc, blob
  blob bytes, 32-byte aligned, from the directory end.
A blob larger than its side's slot cap (SLOT_CAP) is left out (its keys draw the standard hand) and listed in the report.
The home poses (prefetched at room load and kept): pl00 arc 0x12 (right, the empty hand) and pl00 arc 0x14 (left).

derive: ps2leon_runtime.h without the standard hands' arrays (i5_* / i6_*): rows 5 / 6 of leon4k::chunks keep their
counts with null arrays; the game points them at its hand slots (coarse_actor_leon_hands.inc). The image then holds
no hand geometry; the hands come from the package.

addkey (wep19-26, 2026-10-26): one more row (GC runtime key -> an existing blob), for a hand BIN whose bytes were
converted to PS2 geometry (ps2cast/ps2_weapons.py --hands): its runtime key changes, the drawn blob does not. The
directory grows by one row, every blob offset moves by the directory growth, blob bytes and sources are kept.

Pure Python (no numpy): runs at build time in WSL and on the Windows host.
"""
import hashlib, json, re, struct, sys
from pathlib import Path

MAGIC = 0x3150484C        # 'LHP1'
VERSION = 1
SLOT_CAP = {5: 6144, 6: 6400}   # coarse_actor_leon_hands.inc kSlotBytes: the fixed draw slots (right, left)
CAPS = dict(rows=24, blobs=24, sources=48)   # the resident directory's capacity (coarse_actor_leon_hands.inc)
FLAG_STANDARD, FLAG_HOME, FLAG_ALT = 1, 2, 4
HOME = {5: ('pl00', 0x12), 6: ('pl00', 0x14)}
# Alternating poses (seen swapping with the standard hand in real time: h2 / f6s, 2026-10-13): prefetched with the
# standard hand at room load and at weapon equip when the weapon has no hand of its own on that side.
ALT = {6: ('pl00', 0x16)}
ARR = re.compile(r'alignas\(32\)\s+static\s+(?:const\s+)?unsigned\s+char\s+(\w+?)_(pos|nrm|uv|gx)\[\]\s*=\s*\{([^}]*)\};', re.S)
WGT = re.compile(r'static\s+const\s+(?:leon4k::)?Weight\s+(\w+?)_weights\[\]\s*=\s*\{(.*?)\};\n', re.S)
WROW = re.compile(r'\{\{(\d+),(\d+),(\d+)\},(\d+),\{([^,}]+),([^,}]+),([^,}]+)\}\}')


def a32(n):
    return (n + 31) & ~31


def fnv(b):
    h = 0x811C9DC5
    for x in b:
        h = ((h ^ x) * 0x01000193) & 0xFFFFFFFF
    return h


def cfloat(s):
    s = s.strip()
    if s.endswith('f'):
        s = s[:-1]
    return float.fromhex(s) if 'x' in s else float(s)


def arrays(text):
    """name -> {pos, nrm, uv, gx: bytes, weights: bytes}"""
    out = {}
    for m in ARR.finditer(text):
        out.setdefault(m.group(1), {})[m.group(2)] = bytes(int(x) for x in m.group(3).replace('\n', '').split(',') if x.strip())
    for m in WGT.finditer(text):
        w = b''
        for r in WROW.finditer(m.group(2)):
            b0, b1, b2, n = (int(r.group(i)) for i in range(1, 5))
            w += struct.pack('<4B3f', b0, b1, b2, n, *(cfloat(r.group(i)) for i in range(5, 8)))
        out.setdefault(m.group(1), {})['weights'] = w
    return out


def chunk_rows(text, ns_prefix):
    """{name: (role, pc, nc, pal, tri, stream_bytes)} from a 'static Chunk chunks[] = {...};' table."""
    body = re.search(r'static Chunk chunks\[\] = \{(.*?)\};', text, re.S).group(1)
    out = {}
    for m in re.finditer(r'\{(\d+),(\d+),(\d+),(\d+),(\d+),(\d+),(\w+?)_pos,', body):
        out[m.group(7)] = tuple(int(m.group(i)) for i in range(1, 7))
    return out


def blob_of(role, row, arr):
    pc, nc, pal, tri, sb = row[1:]
    parts = [arr['pos'], arr['nrm'], arr['uv'], arr['gx'], arr['weights']]
    assert len(parts[0]) >= pc * 8 and len(parts[1]) >= nc * 8 and len(parts[4]) == pal * 16, (role, row)
    data = b''.join(p + b'\0' * (a32(len(p)) - len(p)) for p in parts)
    return dict(role=role, pc=pc, nc=nc, pal=pal, tri=tri, sb=sb, sizes=[len(p) for p in parts], data=data)


def wep_no(file):
    if file.startswith('wep'):
        return int(file[3:])
    return {'pl0e': 0x8E, 'pl0f': 0x8F}.get(file)


def pack(runtime_h, hands_dir, inv_json, out, report=None):
    rt = Path(runtime_h).read_text()
    rta, rtr = arrays(rt), chunk_rows(rt, 'i')
    sig = re.search(r'static const SourceSignature signatures\[\] = \{(.*?)\};', rt, re.S).group(1)
    sigs = [tuple(int(x, 0) for x in re.sub(r'u\b', '', s).split(',')) for s in re.findall(r'\{([^}]*)\}', sig)]
    hd = Path(hands_dir)
    ht = (hd / 'ps2leon_hands.h').read_text()
    ha, hr = arrays(ht), chunk_rows(ht, 'h')
    rep_h = json.loads((hd / 'report-hands.json').read_text())
    inv = json.loads(Path(inv_json).read_text())
    blobs, rows, sources, left_out = [], [], [], []
    # standard hands first (blob 0 right, 1 left): keyed by the arm's GC source signature of roles 5 / 6
    key_blob = {}
    for role in (5, 6):
        b = blob_of(role, rtr['i%d' % role], rta['i%d' % role])
        b['flags'] = FLAG_STANDARD
        b['name'] = 'standard-%d' % role
        assert len(b['data']) <= SLOT_CAP[role], ('standard hand over the slot cap', role, len(b['data']))
        blobs.append(b)
        k = (role,) + sigs[role]
        rows.append(k + (len(blobs) - 1,))
        key_blob[k] = len(blobs) - 1
    # the poses, in build_hands order
    pose_blob = {}
    for p in rep_h['poses']:
        if p.get('status') != 'ps2':
            left_out.append(dict(pose=p['pose'], why=p.get('reason', p.get('status'))))
            continue
        name = 'h%d' % p['index']
        role = p['role']
        b = blob_of(role, hr[name], ha[name])
        if len(b['data']) > SLOT_CAP[role]:
            left_out.append(dict(pose=p['pose'], sources=p['sources'], bytes=len(b['data']), why='over the slot cap %d' % SLOT_CAP[role]))
            continue
        home = any(s == '%s/%#x' % HOME[role] for s in p['sources'])
        b['flags'] = FLAG_HOME if home else 0
        if role in ALT and any(s == '%s/%#x' % ALT[role] for s in p['sources']):
            b['flags'] |= FLAG_ALT
        b['name'] = name + ' ' + ','.join(p['sources'][:3])
        blobs.append(b)
        pose_blob[p['pose']] = len(blobs) - 1
        for k in p['keys']:
            kk = (role,) + tuple(k)
            assert kk not in key_blob, kk
            rows.append(kk + (len(blobs) - 1,))
            key_blob[kk] = len(blobs) - 1
    for e in inv:
        role = {'right': 5, 'left': 6}[e['side']]
        k = (role, e['key']['positions'], e['key']['normals'], e['key']['palette'], e['key']['vertex_hash'])
        w = wep_no(e['file'])
        if w is None or e.get('ada_only') or k not in key_blob:
            continue
        sources.append((w, e['arc'], key_blob[k]))
    assert len(rows) <= CAPS['rows'] and len(blobs) <= CAPS['blobs'] and len(sources) <= CAPS['sources'], \
        (len(rows), len(blobs), len(sources))
    dir_bytes = a32(32 + 12 * len(rows) + 24 * len(blobs) + 4 * len(sources))
    off = dir_bytes
    for b in blobs:
        b['offset'] = off
        off += len(b['data'])
    body = b''
    for r in rows:
        body += struct.pack('<BBHHHI', r[0], r[5], r[1], r[2], r[3], r[4])
    for b in blobs:
        assert b['offset'] % 32 == 0 and b['offset'] >> 5 < 65536
        body += struct.pack('<BBHHHH', b['role'], b['flags'], b['pc'], b['nc'], b['pal'], b['tri'])
        body += struct.pack('<5H', *b['sizes']) + struct.pack('<HH', b['sb'], b['offset'] >> 5)
    for s in sources:
        body += struct.pack('<BBH', *s)
    body += b'\0' * (dir_bytes - 32 - len(body))
    body += b''.join(b['data'] for b in blobs)
    hdr = struct.pack('<IHHHHIIIII', MAGIC, VERSION, len(rows), len(blobs), len(sources), SLOT_CAP[5], SLOT_CAP[6],
                      dir_bytes, 32 + len(body) - 0, fnv(body))
    assert len(hdr) == 32
    data = hdr + body
    Path(out).write_bytes(data)
    rep = dict(file=str(out), bytes=len(data), sha256=hashlib.sha256(data).hexdigest(), dir_bytes=dir_bytes,
               rows=len(rows), blobs=[dict(index=i, name=b['name'], role=b['role'], flags=b['flags'], bytes=len(b['data']),
                                           triangles=b['tri'], offset=b['offset']) for i, b in enumerate(blobs)],
               sources=[dict(wep=s[0], arc=s[1], blob=s[2]) for s in sources], left_out=left_out,
               max_blob={r: max(len(b['data']) for b in blobs if b['role'] == r) for r in (5, 6)})
    if report:
        Path(report).write_text(json.dumps(rep, indent=1))
    print(json.dumps(dict(bytes=len(data), sha256=rep['sha256'], rows=len(rows), blobs=len(blobs), sources=len(sources),
                          max_blob=rep['max_blob'], left_out=[(x['pose'], x['why']) for x in left_out])))


def derive(runtime_h, out):
    t = Path(runtime_h).read_text()
    n0 = len(t)
    t, k = re.subn(r'alignas\(32\)\s+static\s+(?:const\s+)?unsigned\s+char\s+i[56]_(?:pos|nrm|uv|gx)\[\]\s*=\s*\{[^}]*\};\n?', '', t)
    assert k == 8, k
    t, k = re.subn(r'static\s+const\s+(?:leon4k::)?Weight\s+i[56]_weights\[\]\s*=\s*\{.*?\};\n', '', t, flags=re.S)
    assert k == 2, k
    t, k = re.subn(r'\{([56]),(\d+),(\d+),(\d+),(\d+),(\d+),i[56]_pos,i[56]_nrm,i[56]_uv,i[56]_gx,i[56]_weights\}',
                   r'{\1,\2,\3,\4,\5,\6,nullptr,nullptr,nullptr,nullptr,nullptr}', t)
    assert k == 2, k
    assert not re.search(r'\bi[56]_(pos|nrm|uv|gx|weights)\b', t)
    head = ('// Derived by tools/d367/ps2leon/hands_pack.py derive from %s (sha256 %s): the standard hands (roles 5 / 6)\n'
            '// are not in the image; LEON_HAND_PACK reads them from the hand package. Build output, do not edit.\n'
            % (Path(runtime_h).name, hashlib.sha256(Path(runtime_h).read_bytes()).hexdigest()[:16]))
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(out) + '.tmp')
    tmp.write_text(head + t)
    tmp.replace(out)
    print('derive: %s %d -> %d bytes' % (out, n0, len(t)))


def addkey(src, out, role, pc, nc, pal, vh, blob):
    d = Path(src).read_bytes()
    m, v, nr, nb, ns, cr, cl, db, fb, h = struct.unpack_from('<IHHHHIIIII', d, 0)
    assert m == MAGIC and v == VERSION and fb == len(d) and h == fnv(d[32:]), 'bad package'
    o = 32
    rows = [struct.unpack_from('<BBHHHI', d, o + 12 * i) for i in range(nr)]
    o += 12 * nr
    blobs = [list(struct.unpack_from('<BBHHHH5HHH', d, o + 24 * i)) for i in range(nb)]
    o += 24 * nb
    srcs = d[o:o + 4 * ns]
    data = d[db:]
    key = (role, pc, nc, pal, vh)
    assert all((r[0],) + r[2:] != key for r in rows), 'key already present'
    assert 0 <= blob < nb and blobs[blob][0] == role, ('blob is not on this side', blob, role)
    rows.append((role, blob, pc, nc, pal, vh))
    assert len(rows) <= CAPS['rows'], len(rows)
    ndb = a32(32 + 12 * len(rows) + 24 * nb + 4 * ns)
    body = b''.join(struct.pack('<BBHHHI', *r) for r in rows)
    for b in blobs:
        off = (b[-1] << 5) - db + ndb
        assert off % 32 == 0 and off >> 5 < 65536
        body += struct.pack('<BBHHHH5HHH', *(b[:-1] + [off >> 5]))
    body += srcs
    body += b'\0' * (ndb - 32 - len(body))
    body += data
    hdr = struct.pack('<IHHHHIIIII', MAGIC, VERSION, len(rows), nb, ns, cr, cl, ndb, 32 + len(body), fnv(body))
    Path(out).write_bytes(hdr + body)
    print('addkey: rows %d -> %d, directory %d -> %d, %d -> %d bytes' % (nr, len(rows), db, ndb, len(d), 32 + len(body)))


def show(path):
    d = Path(path).read_bytes()
    m, v, nr, nb, ns, cr, cl, db, fb, h = struct.unpack_from('<IHHHHIIIII', d, 0)
    assert m == MAGIC and v == VERSION and fb == len(d) and h == fnv(d[32:]), 'bad package'
    print('rows %d blobs %d sources %d caps %d/%d dir %d file %d' % (nr, nb, ns, cr, cl, db, fb))
    o = 32
    for i in range(nr):
        print(' row', struct.unpack_from('<BBHHHI', d, o)); o += 12
    for i in range(nb):
        print(' blob', i, struct.unpack_from('<BBHHHH5HHH', d, o)); o += 24
    for i in range(ns):
        print(' src', struct.unpack_from('<BBH', d, o)); o += 4


if __name__ == '__main__':
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    if a and a[0] == 'pack':
        rp = sys.argv[sys.argv.index('--report') + 1] if '--report' in sys.argv else None
        if rp in a:
            a.remove(rp)
        pack(a[1], a[2], a[3], a[4], rp)
    elif a and a[0] == 'derive':
        derive(a[1], a[2])
    elif a and a[0] == 'addkey':
        addkey(a[1], a[2], *(int(x, 0) for x in a[3:9]))
    elif a and a[0] == 'show':
        show(a[1])
    else:
        raise SystemExit(__doc__)
