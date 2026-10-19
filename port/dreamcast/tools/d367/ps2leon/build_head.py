#!/usr/bin/env python3
"""ps2leon flying head (lane garr18, 2026-10-19; LEON_HEADLESS data set v2): the PS2 head Leon's head-loss deaths throw
(SetObj01(player arc 0xC, TPL 7): em10 / em25 / em2c / em2d / em31 / em32 / emwep), stored INSIDE the player archive.

  build_head.py <out dir> <dc pl00.drs> <dc pl08.drs>

The GameCube arc 0xC (55,232 bytes, 1,635 vertices, 23 display lists) is replaced in both player archives by a stub
the source can still load and never draws, followed by the native payload (coordinator 10-19, option (c): same archive
heap, no static image growth):
  stub     the original BIN header and pHead record, a 2-vertex position array holding the original bound's min and
           max corners (getBoundingBox and every bound reader see the same box), no normals / colours / UVs, the
           weight table, the 23 ModelPart headers (material bytes kept, stream size 0, nPoly 0) and the flip table.
           cModInfoMgr::create, calcModelAddr, trans / shadow / mirror walk the display lists: nothing to draw.
  payload  little-endian, 32-aligned after the stub (re4dc_stub_payload in the runtime finds it from the relocated
           header and proves magic, size and CRC once per address): the PS2 pl00 arc 0xC (1,736 triangles, one bone,
           1,045 face triangles on the atlas face tile, 691 hair triangles on hair material 1) packed by arm A's
           pipeline as role 7 (pack_coarse_actor, build_blob, verify_blob, patch_header), one face run (atlas UVs) and
           one hair run (hair-image UVs, material 1), as pack_arm.py builds the hair runs.
Only the stub is in GameCube byte order; the DC archives are the given mirrored files with entry 8 replaced by
le_mirror's fmt_bin of the stub plus the payload (checked: the mirror of the original arc 0xC equals both given DC
entries). Outputs: pl00.drs, pl08.drs (DC, for the disc), stub-be.bin, actor_material_records_leon_head.inc (the
stub's identity rows), report-head.json.
"""
import copy, hashlib, json, re, struct, sys, tempfile, zlib
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import leon_sources as ls  # noqa: E402
import build_arm_a as ba  # noqa: E402
import build_hands as bh  # noqa: E402
import pack_arm as pa  # noqa: E402
import drs  # noqa: E402
import le_mirror  # noqa: E402

ARC, ENTRY, ROLE = 0xC, 0xC - 4, 7
FACE_KEY, HAIR_KEY = 'dde6f32a-0b7cfdcf', 'ac381b1a-3ade84b1'
MAGIC = 0x48344552  # 'RE4H'
HEADER_WORDS = 32


def be32(b, o):
    return struct.unpack_from('>I', b, o)[0]


def be16(b, o):
    return struct.unpack_from('>H', b, o)[0]


def a32(n):
    return (n + 31) & ~31


# ---------------------------------------------------------------- stub (GameCube byte order)
def make_stub(g):
    assert be32(g, 0x3C) == 0x20030818 and g[0x19] == 1 and g[0x18] == 1 and be32(g, 0x2C) == 0 and be32(g, 0x40) == 0
    head, vtx, nrm, clr, tex, wgt, parts, flip = (be32(g, o) for o in (0x00, 0x30, 0x34, 0x0C, 0x10, 0x14, 0x1C, 0x44))
    nv, nd = be16(g, 0x38), be16(g, 0x1A)
    assert head == 0x60 and vtx == 0x80 and parts % 32 == 0 and flip and flip + 0x20 == len(g), (head, vtx, flip, len(g))
    V = np.frombuffer(g[vtx:vtx + nv * 8], '>i2').reshape(nv, 4)[:, :3].astype(int)
    lo, hi = V.min(0), V.max(0)
    out = bytearray(g[:0x80])                       # header + pHead record
    v_at = len(out)
    out += struct.pack('>4h', *lo, 0) + struct.pack('>4h', *hi, 0)
    out += bytes(a32(len(out)) - len(out))
    w_at = len(out)
    out += g[wgt:parts]                             # weight table (rigid: one entry)
    out += bytes(a32(len(out)) - len(out))
    p_at = len(out)
    at = parts
    for _ in range(nd):
        h = bytearray(g[at:at + 0x20]); n = be32(h, 0x18)
        struct.pack_into('>2I', h, 0x18, 0, 0)
        out += h; at += 0x20 + n
    f_at = len(out)
    out += g[flip:flip + 0x20]
    for off, val in ((0x0C, v_at + 16), (0x10, v_at + 16), (0x14, w_at), (0x1C, p_at), (0x30, v_at), (0x34, v_at + 16),
                     (0x44, f_at)):
        struct.pack_into('>I', out, off, val)
    struct.pack_into('>2H', out, 0x38, 2, 0)
    return bytes(out), dict(lo=lo.tolist(), hi=hi.tolist(), vertices=nv, displists=nd, stub_bytes=len(out))


def mirror_bin(b, label):
    nb = bytearray(b)
    s = le_mirror.Swapper(nb, label)
    with s.bounded(0, len(nb)):
        le_mirror.fmt_bin(s, 0, len(nb), label)
    return bytes(nb)


# ---------------------------------------------------------------- DC (little-endian) drs container
def dc_parse(d):
    recs, o = [], 0x20
    while True:
        r = struct.unpack_from('<8I', d, o); o += 32
        if r[0] == 0xFFFFFFFF:
            break
        recs.append(r)
    # The DC mirror (le_mirror compact) keeps the record table, the original region and the sound bank where they were
    # and appends the body it loads at the end of the file: record 0 = (0, size, 0, offset), offset + size = file size.
    assert len(recs) == 2 and recs[0][0] == 0 and recs[0][2] == 0 and recs[0][3] + recs[0][1] == len(d), recs
    off0 = recs[0][3]
    body = d[off0:]
    count, rel = struct.unpack_from('<2I', body, 0)
    offs = list(struct.unpack_from('<%dI' % count, body, 16))
    tags = [body[16 + 4 * count + 4 * i:][:4] for i in range(count)]
    end = rel or len(body)
    ents = [body[offs[i]:offs[i + 1] if i + 1 < count else end] for i in range(count)]
    return dict(prefix=d[:off0], recs=recs, count=count, rel=body[rel:] if rel else None, tags=tags, ents=ents,
                offs0=offs[0], hdr=body[:offs[0]], offs=offs)


def shift_native_table(a, entry, delta):
    """The prepared archive's "NTR" entry (texture_package.cpp SourceIdentityTable::adopt: R4NTBL, version 1, 12-byte
    entries of body offsets record / header / TPL, word 28 = the bytes ReadPlayerData reads, CRC-32 of the entries):
    every offset after `entry` moves by -delta and the read size shrinks by delta."""
    after = a['offs'][entry + 1]
    n = 0
    for i, t in enumerate(a['tags']):
        if t != b'NTR\0':
            continue
        e = bytearray(a['ents'][i])
        assert e[:8] == b'R4NTBL\0\0' and struct.unpack_from('<I', e, 8)[0] == 1 and struct.unpack_from('<I', e, 16)[0] == 12
        count = struct.unpack_from('<I', e, 12)[0]
        assert zlib.crc32(bytes(e[32:32 + 12 * count])) & 0xffffffff == struct.unpack_from('<I', e, 20)[0]
        for k in range(count):
            for j in range(3):
                o = 32 + 12 * k + 4 * j
                v = struct.unpack_from('<I', e, o)[0]
                assert v < a['offs'][entry] or v >= after, 'a native record inside the replaced entry'
                if v >= after:
                    struct.pack_into('<I', e, o, v - delta)
        struct.pack_into('<I', e, 28, struct.unpack_from('<I', e, 28)[0] - delta)
        struct.pack_into('<I', e, 20, zlib.crc32(bytes(e[32:32 + 12 * count])) & 0xffffffff)
        a['ents'][i] = bytes(e); n += 1
    assert n == 1, n


def dc_pack(a):
    count = a['count']
    out = bytearray(struct.pack('<4I', count, 0, 0, 0))
    offs, off = [], a['offs0']
    for e in a['ents']:
        offs.append(off); off += len(e)
    rel_off = off if a['rel'] is not None else 0
    struct.pack_into('<I', out, 4, rel_off)
    out += struct.pack('<%dI' % count, *offs)
    for t in a['tags']:
        out += t
    out += a['hdr'][len(out):a['offs0']]
    for e in a['ents']:
        out += e
    if a['rel'] is not None:
        out += a['rel']
    body = bytes(out)
    pre = bytearray(a['prefix'])
    r = a['recs'][0]
    struct.pack_into('<8I', pre, 0x20, r[0], len(body), r[2], r[3], *r[4:])
    s = a['recs'][1]
    assert s[0] == 4 or s[3] != len(a['prefix']) + 0, s  # a "no sound bank" slot would point at the old file end
    return bytes(pre) + body


# ---------------------------------------------------------------- PS2 head -> role 7 of arm A's mesh
def head_mesh():
    m, tris = bh.ps2_section('pl00', ARC)
    base = json.loads((ls.WORK / 'arms/a/mesh.json').read_text())
    mesh = copy.deepcopy(base)
    mesh['triangles'] = [t for t in mesh['triangles'] if t['source_info'] != ROLE]
    vid, face, hair = {}, [], []
    for node, cs in tris:
        P = np.asarray([c['p'] for c in cs], float)
        if np.linalg.norm(np.cross(P[1] - P[0], P[2] - P[0])) < 1e-6:
            continue
        mt = m.materials[node]
        is_hair = mt['diffuse'] == 0 and mt['opacity'] == 1
        assert is_hair or mt['diffuse'] == 2, mt
        key = HAIR_KEY if is_hair else FACE_KEY
        tc = []
        for c in cs:
            assert all(int(b) == 0 for b, x in c['w']), c['w']
            pk = tuple(np.round(c['p'], 4))
            if pk not in vid:
                vid[pk] = len(mesh['positions_mm'])
                mesh['positions_mm'].append([float(x) for x in c['p']])
                mesh['weights'].append([[0, 1.0]])
            u, v = c['raw']['uv'][0] / 256.0, c['raw']['uv'][1] / 256.0
            corner = dict(vertex=vid[pk], normal=[float(x) for x in c['n']], uv=ba.atlas_uv(key, u, v))
            if is_hair:
                corner['src_uv'] = [u, v]
            tc.append(corner)
        t = dict(source_info=ROLE, corners=tc)
        if is_hair:
            t['material'] = 1
        (hair if is_hair else face).append(t)
    mesh['triangles'] += face + hair
    mesh['source_info_counts'] = {str(k): sum(t['source_info'] == k for t in mesh['triangles']) for k in range(8)}
    return mesh, len(face), len(hair)


WROW = re.compile(r'\{\{(\d+),(\d+),(\d+)\},(\d+),\{([^}]*)\}\}')


def weight_bytes(text):
    out = bytearray()
    for b0, b1, b2, c, vals in WROW.findall(text):
        v = [float.fromhex(x.strip().rstrip('f')) if 'x' in x else float(x.strip().rstrip('f'))
             for x in vals.split(',') if x.strip()] + [0.0, 0.0, 0.0]
        out += struct.pack('<4B3f', int(b0), int(b1), int(b2), int(c), *v[:3])
    assert out, 'no weights parsed'
    return bytes(out)


def c_bytes(text):
    return bytes(int(v, 0) for v in text.replace('\n', '').split(',') if v.strip())


def sub_run(bb, native, uvb, sel_tris, flags, bounds):
    """one restripified run over the role's chunk arrays: sel_tris = [(vi, ni, uvi) x3] (pack_arm.hair_runs' build)."""
    with tempfile.TemporaryDirectory(prefix='ps2leon-head-') as d:
        d = Path(d)
        cs = [c for t in sel_tris for c in t]
        (d / 'info0.gx').write_bytes(bytes([0x90]) + struct.pack('>H', len(cs)) + b''.join(struct.pack('>3H', *c) for c in cs))
        (d / 'info0.pos').write_bytes((native / ('info%d.pos' % ROLE)).read_bytes())
        (d / 'info0.nrm').write_bytes((native / ('info%d.nrm' % ROLE)).read_bytes())
        (d / 'info0.uv').write_bytes(uvb)
        ch = bb.Chunk(bb.load_chunk(d, 0))
    best = None
    for mode in ('boundary', 'near', 'palette'):
        for wd in (0.0, 0.02, 0.1):
            metas = bb.build(ch, mode, wd, 8)
            cst, st = bb.cost(metas)
            if best is None or cst < best[0]:
                best = (cst, metas)
    blob = bytearray(bb.assemble(ch, best[1]))
    blob[2] = flags
    blob[16:32] = bounds
    return bytes(blob) + bytes((-len(blob)) % 32)


def build_payload(mesh, nface, nhair, work):
    arrays, wt, row = bh.pack_role(mesh, ROLE, work)
    pc, nc, pal, tri, sb = row
    assert pal == 1 and tri == nface + nhair, (row, nface, nhair)
    native = work / 'native'
    bb = pa.load('build_blob', pa.FAST / 'build_blob.py')
    g = (native / ('info%d.gx' % ROLE)).read_bytes()
    n = struct.unpack('>H', g[1:3])[0]
    corners = [struct.unpack('>3H', g[3 + 6 * k:9 + 6 * k]) for k in range(n)]
    assert n == 3 * tri
    main_blob = (work / 'blob' / ('info%d.meshlets' % ROLE)).read_bytes()
    bounds = main_blob[16:32]
    role_tris = [t for t in mesh['triangles'] if t['source_info'] == ROLE]
    face_sel = [tuple(corners[3 * k + j] for j in range(3)) for k in range(nface)]
    face = sub_run(bb, native, (native / ('info%d.uv' % ROLE)).read_bytes(), face_sel, main_blob[2], bounds)
    uvs, uvid, hair_sel = [], {}, []
    for k in range(nface, tri):
        t = role_tris[k]
        st = [c['src_uv'] for c in t['corners']]
        du = -min(0, int(min(s[0] for s in st) // 1)); dv = -min(0, int(min(s[1] for s in st) // 1))
        tc = []
        for j, s in enumerate(st):
            w = (round((s[0] + du) * 32768), round((s[1] + dv) * 32768))
            assert 0 <= w[0] <= 65535 and 0 <= w[1] <= 65535, w
            if w not in uvid:
                uvid[w] = len(uvs); uvs.append(w)
            vi, ni, _ = corners[3 * k + j]
            tc.append((vi, ni, uvid[w]))
        hair_sel.append(tuple(tc))
    huv = b''.join(struct.pack('<2H', *w) for w in uvs)
    hair = sub_run(bb, native, huv, hair_sel, min(pa.uv_excess(uvs), 31) << 2, bounds)
    parts = [('pos', c_bytes(arrays['pos'])), ('nrm', c_bytes(arrays['nrm'])), ('uv', c_bytes(arrays['uv'])),
             ('gx', c_bytes(arrays['gx'])), ('w', weight_bytes(wt)), ('face', face), ('huv', huv), ('hair', hair)]
    assert len(dict(parts)['gx']) == sb, (len(dict(parts)['gx']), sb)
    body, offs = bytearray(), {}
    at = HEADER_WORDS * 4
    for name, data in parts:
        offs[name] = (at + len(body), len(data))
        body += data + bytes(a32(len(data)) - len(data))
    total = HEADER_WORDS * 4 + len(body)
    words = [MAGIC, 1, total, zlib.crc32(bytes(body)) & 0xffffffff, ROLE, pc, nc, pal, tri, sb]
    for name in ('pos', 'nrm', 'uv', 'gx', 'w'):
        words += list(offs[name])
    words += [*offs['face'], nface, *offs['huv'], *offs['hair'], nhair, 1]
    words += [0] * (HEADER_WORDS - len(words))
    assert len(words) == HEADER_WORDS
    payload = struct.pack('<%dI' % HEADER_WORDS, *words) + bytes(body)
    return payload, dict(positions=pc, normals=nc, palettes=pal, triangles=tri, face_triangles=nface, hair_triangles=nhair,
                         stream_bytes=sb, face_run=len(face), hair_run=len(hair), hair_uv=len(huv), payload_bytes=total,
                         offsets={k: v[0] for k, v in offs.items()})


def records(tree, stub_be_drs, out):
    import gen_neck_records as gnr
    mr = gnr.load(str(tree))
    archive, _pt, le = mr.archive_facts(str(tree))
    P, M, B, f = gnr.rows(mr, archive.Archive(str(stub_be_drs)), le, 'pl00', ARC)
    hdr = ['// LEON_HEADLESS v2 (build_head.py, lane garr18): the flying head stub, player archive arc 0xC (pl00 / pl08',
           '// identical), entry sha256 %s (stub + native payload). Generated; do not edit.' % f['sha256']]
    out.write_text('\n'.join(hdr + P + [M, '#define RE4DC_LEON_HEAD_BLOB ' + B.rstrip(',')]) + '\n')
    return f


def main():
    out, dc00, dc08 = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    out.mkdir(parents=True, exist_ok=True)
    gpl, _ = ls.gc_archives()
    g = gpl.entries[ENTRY][1]
    assert gpl.entries[ENTRY][0] == b'BIN\0' and len(g) == 55232
    stub, srep = make_stub(g)
    mesh, nface, nhair = head_mesh()
    payload, prep = build_payload(mesh, nface, nhair, out / 'work')
    be_entry = stub + bytes(a32(len(stub)) - len(stub)) + payload
    be_entry += b'\xcd' * (a32(len(be_entry)) - len(be_entry))
    dc_entry = mirror_bin(be_entry, 'pl/0xC-stub')
    assert dc_entry[len(stub):] == be_entry[len(stub):], 'fmt_bin touched the payload'
    want = mirror_bin(g, 'pl/0xC')
    rep = dict(source='PS2 pl00 arc 0xC (USA disc) + GC arc 0xC stub', stub=srep, payload=prep,
               gc_entry_bytes=len(g), new_entry_bytes=len(be_entry), saved_bytes=len(g) - len(be_entry), archives={})
    for name, path in (('pl00', dc00), ('pl08', dc08)):
        d = path.read_bytes()
        a = dc_parse(d)
        assert dc_pack(a) == d, '%s: DC container round trip differs' % name
        assert a['tags'][ENTRY] == b'BIN\0' and a['ents'][ENTRY] == want, '%s: DC entry 8 is not the mirrored GC arc 0xC' % name
        delta = len(a['ents'][ENTRY]) - len(dc_entry)
        assert delta > 0 and delta % 32 == 0, delta
        shift_native_table(a, ENTRY, delta)
        a['ents'][ENTRY] = dc_entry
        new = dc_pack(a)
        b = dc_parse(new)
        assert b['ents'][ENTRY] == dc_entry and all(b['ents'][i] == a['ents'][i] for i in range(a['count'])) and b['rel'] == a['rel']
        (out / ('%s.drs' % name)).write_bytes(new)
        rep['archives'][name] = dict(src_bytes=len(d), src_sha256=hashlib.sha256(d).hexdigest(), out_bytes=len(new),
                                     out_sha256=hashlib.sha256(new).hexdigest())
    # GameCube-order archive holding the stub entry, for the identity rows (bin_facts reads an archive)
    gd = drs.Drs(ls._cached('pl00.drs', lambda: None))
    gd.entries[ENTRY] = (gd.entries[ENTRY][0], be_entry)
    (out / 'work').mkdir(exist_ok=True)
    stub_drs = out / 'work' / 'pl00-stub-be.drs'
    stub_drs.write_bytes(gd.pack())
    (out / 'stub-be.bin').write_bytes(be_entry)
    f = records(ls.TREE, stub_drs, out / 'actor_material_records_leon_head.inc')
    rep['records_entry_sha256'] = f['sha256']
    (out / 'report-head.json').write_text(json.dumps(rep, indent=1))
    print(json.dumps(rep, indent=1))


if __name__ == '__main__':
    main()
