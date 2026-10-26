#!/usr/bin/env python3
"""pfire26.py: the PS2 torch fire effect sets for the chapter 1-2 torch rooms (lane purge-audit26, 2026-10-26).

  pfire26.py --room r10c --dar <release room .dar> --out <new .dar> [--json report.json]

PS2 moved the GameCube torches (cEmTorch et1400 / et0c00 / et3800, effect files et14.eff / et0c.eff / et38.eff) out of
the etc list: the body is a scenario SMD placement (our PS2 world draws it) and the flame is a set in the room EFF's SST
table (started at room entry, list type 0xFFFF, or by an effect area). Our room EFF is the GameCube one, so the flames
were lost with PS2_ETS_MATCH=2. This tool, member by member:

  1. takes the PS2 rNNN.dat EFF SST sets that hold a torch flame record (torch positions: the GC ETS rows the
     PS2_ETS_MATCH=2 table drops; a set qualifies when a record lies within 500 units of one; same rule as
     ets_ps2_evidence.py);
  2. drops a record the GameCube room EFF already draws (same esp Id and position within 50 units in a GC SST);
  3. keeps an area-bound set's area type when the GC room EAR entry of that area is byte-identical to the PS2 one,
     else the set starts at room entry (type 0xFFFF; logged as approximation);
  4. writes them as a texture-less EFF v0xB (est / path / efm / texture tables empty; the records sample the core
     and room texture ids the game already registers with PS2 pictures: every id is checked against the DC core
     EFF and the room EFF of the payload);
  5. replaces the room ETM's et14.eff (the GC torch flame file, now dead: every et1400 entry is dropped) with that
     file; ETM sub-file offsets and the payload's native ESQ / NTR tables are rebased (rows that pointed into the old
     et14.eff are dropped and listed).
Records are the PS2 bytes unchanged (le_mirror.fmt_sequence field map = PS2 little-endian layout, proved on 85
byte-identical GC/PS2 records). Runtime: PS2_FIRE_SST=1 (EtcModel.cpp / eff_sys.cpp).
"""
import argparse, hashlib, json, re, struct, sys, zlib
from pathlib import Path
T = Path(__file__).resolve().parent.parent.parent
sys.path[:0] = [str(T), str(T / '../../../tools')]
import ps2_objects as po  # noqa
import ps2_bin as pb  # noqa
import room_smd as rs  # noqa

OWNER = 0x68
CORE_DAS = '/root/re4data/private/ps2snd24-t24-20261024/etc/core.das'


def al(n, a=32):
    return (n + a - 1) // a * a


def eff_tables(b, en):
    h = struct.unpack_from(en + '12I', b, 0)
    def idt(o):
        n = struct.unpack_from(en + 'I', b, o)[0]
        return [struct.unpack_from(en + 'HHI', b, o + 4 + 8 * k) for k in range(n)]
    out = dict(hdr=h, tex=[x[0] for x in idt(h[1])] if h[1] else [], sst=[])
    if h[3] and h[9]:
        lst = idt(h[3])
        n = struct.unpack_from(en + 'I', b, h[9])[0]
        offs = struct.unpack_from(en + '%dI' % n, b, h[9] + 4)
        for k, of in enumerate(offs):
            p = h[9] + of
            num = struct.unpack_from(en + 'H', b, p)[0]
            out['sst'].append(dict(pos=k, ent=lst[k], head=b[p:p + 0x30],
                                   recs=[b[p + 0x30 + r * 300:p + 0x30 + (r + 1) * 300] for r in range(num)]))
    return out


def rec_pos(r):
    return struct.unpack_from('<3f', r, 0xC)


def tex_refs(r):
    out = set()
    if r[1] not in (3, 9, 0xC) and r[1] < 0xFC:
        out.add(r[2])
    if r[0xC5]:
        out.add(r[0xC5])
    return out


def core_tex_ids():
    d = Path(CORE_DAS).read_bytes()
    best = []
    for o in range(0, len(d) - 48, 32):
        h = struct.unpack_from('<12I', d, o)
        if h[0] == 0xB and 0 < h[1] < 0x100 and h[1] % 4 == 0 and all(x < 4 << 20 for x in h[1:]):
            n = struct.unpack_from('<I', d, o + h[1])[0]
            if 0 < n < 256:
                ids = [struct.unpack_from('<H', d, o + h[1] + 4 + 8 * k)[0] for k in range(n)]
                if all(i < 256 for i in ids) and len(set(ids)) == n:
                    best = best + ids
    return set(best)


def torch_points(room):
    src = (T / '../../../src/game/EtcModel.cpp').read_text()
    rows = {(int(i, 16), int(n, 16)) for r, i, n in re.findall(r'\{0x([0-9a-f]+), 0x([0-9A-F]+), 0x([0-9A-F]+)\},  // r', src)
            if int(r, 16) == int(room[1:], 16) and int(i, 16) in (0x14, 0x0C, 0x38, 0x1C)}
    gd = Path('/root/work/lanes/purge-props24-scratch/gcarc/%s.arc' % room).read_bytes()
    pts = []
    for t, s, e in rs.tagged_entries(gd, '>'):
        if (t.rstrip(b'\0') if isinstance(t, bytes) else t) == b'ETS':
            n = struct.unpack_from('>H', gd, s)[0]
            for k in range(n):
                p = s + 16 + k * 40
                ident, slot = struct.unpack_from('>2H', gd, p)
                if (ident, slot) in rows:
                    pts.append(((ident, slot), struct.unpack_from('>6f', gd, p + 16)[3:6]))
    return pts


def ear_entries(b):
    n = struct.unpack_from('<I', b, 0)[0]
    return [b[16 + i * 152:16 + (i + 1) * 152] for i in range(n)]


def build_eff(sets):
    """sets: [(id, type, x4, head bytes, [records])] -> texture-less LE EFF v0xB."""
    out = bytearray(48)
    def empty_tbl():
        o = len(out); out.extend(struct.pack('<I', 0)); return o
    o_tex = empty_tbl(); o_tpl = empty_tbl(); o_anm = empty_tbl()
    o_est_l = empty_tbl(); o_est_d = empty_tbl()
    o_path_l = empty_tbl(); o_path_d = empty_tbl()
    o_efm_i = empty_tbl(); o_efm = empty_tbl()
    o_sst_l = len(out)
    out += struct.pack('<I', len(sets))
    for sid, typ, x4, _, _ in sets:
        out += struct.pack('<HHI', sid, typ, x4)
    out += bytes(al(len(out)) - len(out))
    o_sst_d = len(out)
    out += struct.pack('<I', len(sets)) + bytes(4 * len(sets))
    out += bytes(al(len(out)) - len(out))
    for k, (sid, typ, x4, head, recs) in enumerate(sets):
        struct.pack_into('<I', out, o_sst_d + 4 + 4 * k, len(out) - o_sst_d)
        h = bytearray(head)
        struct.pack_into('<H', h, 0, len(recs))
        out += h
        for r in recs:
            out += r
        out += bytes(al(len(out)) - len(out))
    struct.pack_into('<12I', out, 0, 0xB, o_tex, o_est_l, o_sst_l, o_path_l, o_efm_i, o_tpl, o_anm, o_est_d, o_sst_d,
                     o_path_d, o_efm)
    return bytes(out)


def remap_tables(old, new, inner, drop_inside):
    """ps2_objects.remap_native_tables, plus: rows whose offsets fall inside the replaced sub-file are dropped."""
    oe, ne = rs.tagged_entries(old, '<'), rs.tagged_entries(new, '<')
    spans = sorted((s, e, ne[i][1], i) for i, (t, s, e) in enumerate(oe))
    lo, hi = drop_inside

    def mapped(x):
        for s, e, s2, i in spans:
            if s <= x < e:
                if inner and i in inner:
                    for a, b, a2, repl in inner[i]:
                        if a <= x - s < b:
                            if repl and x - s >= a + 0x40:
                                raise ValueError('offset %#x inside a replaced sub-file' % x)
                            return x - s - a + a2 + s2
                    raise ValueError('offset %#x outside sub-files' % x)
                return x - s + s2
        raise ValueError('offset %#x outside every entry' % x)
    out = bytearray(new)
    dropped = {}
    for i, (tag, s, e) in enumerate(ne):
        if tag not in po.NATIVE_TABLES:
            continue
        magic, ver, cnt, row, crc, w24, w28 = struct.unpack_from('<8s6I', out, s)
        if row != 12 or ver != 1 or zlib.crc32(out[s + 32:s + 32 + 12 * cnt]) & 0xffffffff != crc:
            raise ValueError('%s table header not understood' % tag)
        rows = [struct.unpack_from('<3I', out, s + 32 + 12 * r) for r in range(cnt)]
        keep = []
        for a, b, c in rows:
            xs = [a] if tag == b'ESQ\0' else [a, b, c]
            if any(lo <= x < hi for x in xs):
                dropped[tag.rstrip(b'\0').decode()] = dropped.get(tag.rstrip(b'\0').decode(), 0) + 1
                continue
            if tag == b'ESQ\0':
                keep.append((mapped(a), b, c))
                if old[a:a + b] != new[mapped(a):mapped(a) + b]:
                    raise ValueError('ESQ row did not move intact')
            else:
                keep.append((mapped(a), mapped(b), mapped(c)))
                for x, ln in ((a, 32), (b, 36), (c, 12)):
                    if old[x:x + ln] != new[mapped(x):mapped(x) + ln]:
                        raise ValueError('NTR row did not move intact')
        for r, v in enumerate(keep):
            struct.pack_into('<3I', out, s + 32 + 12 * r, *v)
        for r in range(len(keep), cnt):
            struct.pack_into('<3I', out, s + 32 + 12 * r, 0, 0, 0)
        if tag == b'ESQ\0':
            w24 = len(new)
        else:
            w28 = len(new)
        crc = zlib.crc32(out[s + 32:s + 32 + 12 * len(keep)]) & 0xffffffff
        struct.pack_into('<8s6I', out, s, magic, ver, len(keep), row, crc, w24, w28)
    return bytes(out), dropped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--room', required=True)
    ap.add_argument('--dar', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--json')
    a = ap.parse_args()
    room = a.room
    dar = Path(a.dar).read_bytes()
    kind, size, dest, off = struct.unpack_from('<4I', dar, 0x20)
    for p in range(0x40, 0x400, 0x20):
        k2, s2, d2, o2 = struct.unpack_from('<4I', dar, p)
        if k2 == 0xFFFFFFFF:
            break
        if o2 + s2 > off:
            raise ValueError('dar: an entry lies after the payload')
    pay = dar[off:off + size]
    le = rs.tagged_entries(pay, '<')
    idx = pb.afs_index(po.PS2_ISO)
    pd = {}
    for i, t, b in pb.dat_entries(pb.afs_read(po.PS2_ISO, room + '.dat', idx)):
        pd.setdefault(t, b)
    p2 = eff_tables(pd['EFF'], '<')
    gc_eff = next(pay[s:e] for t, s, e in le if t.rstrip(b'\0') == b'EFF')
    g = eff_tables(gc_eff, '<')
    gc_ear = next((pay[s:e] for t, s, e in le if t.rstrip(b'\0') == b'EAR'), b'\0' * 16)
    pts = torch_points(room)
    rep = dict(room=room, dar_in=a.dar, dar_in_sha256=hashlib.sha256(dar).hexdigest(), torches=len(pts), sets=[],
               approximations=[], dropped_dup=0)
    known_tex = core_tex_ids() | set(g['tex'])
    for etm_t, s, e in le:
        if etm_t.rstrip(b'\0') == b'ETM':
            for nm, a0, a1 in po.etm_entries(pay[s:e], '<'):
                if nm.endswith('.eff') and nm != 'et14.eff':
                    eb = pay[s + a0 + 0x40:s + a1]
                    if struct.unpack_from('<I', eb, 0)[0] == 0xB:
                        known_tex |= set(eff_tables(eb, '<')['tex'])
    gc_recs = [(r[1], rec_pos(r)) for st in g['sst'] for r in st['recs']]
    sets = []
    used = set()
    for st in p2['sst']:
        near = [tp for tp in pts if any(abs(rec_pos(r)[0] - tp[1][0]) < 500 and abs(rec_pos(r)[2] - tp[1][2]) < 500 and
                                        abs(rec_pos(r)[1] - tp[1][1]) < 1500 for r in st['recs'])]
        if not near:
            continue
        sid, typ, x4 = st['ent']
        recs = []
        for r in st['recs']:
            p = rec_pos(r)
            if any(i == r[1] and all(abs(x - y) < 50 for x, y in zip(q, p)) for i, q in gc_recs):
                rep['dropped_dup'] += 1
                continue
            miss = tex_refs(r) - known_tex
            if miss:
                raise ValueError('%s SST%d: texture ids %s are registered by no core / room EFF' % (room, sid, sorted(miss)))
            recs.append(r)
        if not recs:
            continue
        ntyp = typ
        if typ != 0xFFFF:
            pa = [x for x in ear_entries(pd.get('EAR', b'\0' * 16)) if x[2] == typ]
            ga = [x for x in ear_entries(gc_ear) if x[2] == typ]
            if not pa or pa != ga:
                ntyp = 0xFFFF
                rep['approximations'].append('SST%d area %d: GC EAR differs (%d GC / %d PS2 entries); starts at room entry'
                                             % (sid, typ, len(ga), len(pa)))
        used.update(tp[0] for tp in near)
        if sid > 0x2F:
            raise ValueError('%s SST id %d above the SstSet key range' % (room, sid))
        sets.append((sid, ntyp, x4, st['head'], recs))   # PS2 id kept: it is also the display flag bit (SetSstDispFlag)
        rep['sets'].append(dict(ps2_pos=st['pos'], ps2_id=sid, ps2_type=typ, type=ntyp, records=len(recs),
                                torches=['et%02x00#%d' % tp[0] for tp in near]))
    missing = [tp[0] for tp in pts if tp[0] not in used]
    rep['torches_without_flame'] = ['et%02x00#%d' % m for m in missing]
    if not sets:
        raise ValueError('%s: no PS2 fire set' % room)
    eff = build_eff(sets)
    # replace ETM et14.eff
    ei = next(i for i, (t, s, e) in enumerate(le) if t.rstrip(b'\0') == b'ETM')
    lb = pay[le[ei][1]:le[ei][2]]
    lents = po.etm_entries(lb, '<')
    newetm = bytearray(lb[:0x20])
    moves = [(0, 0x20, 0, False)]
    lo = hi = None
    for nm, ls, le_ in lents:
        body = lb[ls:le_]
        repl = nm == 'et14.eff'
        if repl:
            h = bytearray(body[:0x40])
            sz = al(0x40 + len(eff))
            struct.pack_into('<I', h, 0, sz if struct.unpack_from('<I', h, 0)[0] else 0)
            body = bytes(h) + eff + bytes(sz - 0x40 - len(eff))
            lo, hi = le[ei][1] + ls + 0x40, le[ei][1] + le_
            rep['et14_bytes'] = [le_ - ls, len(body)]
        moves.append((ls, le_, len(newetm), repl))
        newetm += body
    if lo is None:
        raise ValueError('no et14.eff in the ETM')
    newetm += bytes(al(len(newetm)) - len(newetm))
    newpay = po.rebuild_tagged(pay, '<', {ei: bytes(newetm)})
    newpay, rep['native_rows_dropped'] = remap_tables(pay, newpay, {ei: moves}, (lo, hi))
    out = bytearray(dar[:off]) + newpay
    out += bytes(al(len(out), 2048) - len(out))
    struct.pack_into('<4I', out, 0x20, 0, len(newpay), 0, off)
    Path(a.out).write_bytes(bytes(out))
    rep.update(payload_in=len(pay), payload_out=len(newpay), dar_out=a.out, dar_out_sha256=hashlib.sha256(out).hexdigest(),
               tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    if a.json:
        Path(a.json).write_text(json.dumps(rep, indent=1))
    print('%s sets %s dup-dropped %d approx %d no-flame %s payload %d -> %d native dropped %s' % (
        room, [(x['ps2_id'], x['type'], x['records']) for x in rep['sets']], rep['dropped_dup'], len(rep['approximations']),
        rep['torches_without_flame'], len(pay), len(newpay), rep['native_rows_dropped']))


if __name__ == '__main__':
    main()
