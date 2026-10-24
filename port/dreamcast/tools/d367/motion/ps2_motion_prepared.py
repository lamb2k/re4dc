#!/usr/bin/env python3
"""ps2_motion_prepared.py (lane purge-motion24, 2026-10-24): PS2 motion into a PREPARED enemy archive (Ganados).

  ps2_motion_prepared.py rewrite <payload.drs> <ps2 iso> <ps2 dat name> <outdir> [--mot-dir <disc dc/mot>]
  ps2_motion_prepared.py verify  <rewritten.drs> <payload.drs> <ps2 iso> <ps2 dat name> <mot dir>...

A prepared archive (tools/prepare_enemy_motions.py, then acc12 / motion_flags rewrites) is a DVD container whose type-0
record points at a little-endian body at the end of the file:
  header  u32 count, rel, 0, 0; u32 offsets[count]; char tags[count][4]; members from offset 0x1600 on
  members the source slots in offset order; a cold or hot FCV keeps only its resident prefix (header + key offset table,
          32-byte rounded) and its full key data is the file /cd/dc/mot/<crc32>-<fnv1a>.fcv; FCVs without an MTC row
          (empty, over the 32 KiB slot) stay whole
  tables  ESQ (R4ESQTBL: effect records, archive offsets), NTR (R4NTBL: texture payload/header/TPL archive offsets),
          MTC (R4MOTBL v2: per clip resident offset, bytes, crc, fnv, hot flag), each with a CRC-32 and the archive size
  REL     the 64-byte static module descriptor (rel = its offset)
rewrite: every FCV / SEQ member gets the PS2 entry of the same slot (BIO4DAT.AFS emNN.dat; PS2 FCV = the host image,
PS2 SEQ = one u32 per key). The body is laid out again: members keep their order, FCV prefixes take the PS2 joint
count, every archive offset (body table, rel, ESQ / NTR / MTC rows, table archive-size words) is remapped, MTC rows are
rebuilt with the PS2 key identities, and each clip keeps its slot's hot flag (the zr17 / zr17b hot sets). Non-motion
members keep their bytes. New key files are written to <outdir>/dc/mot. The container keeps everything before the body.
verify: decodes every FCV slot from the rewritten archive + the key files (prefix == key head, crc / fnv), compares it
with the PS2 entry, checks SEQ members, the non-motion members against the input payload, table CRCs and that every
ESQ / NTR row points at the same bytes as before.
"""
import argparse, bisect, hashlib, json, os, struct, sys, zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', '..'))
import ps2_bin  # noqa: E402
from ps2_motion import ps2_fcv_host, ps2_seq_host, host_len  # noqa: E402

MAX_CLIP = 32768
U32 = lambda b, o: struct.unpack_from('<I', b, o)[0]


def prefix(p):
    n = p[2]
    return ((3 + 3 * n + 3) & ~3) + 4 + 4 * n


def al32(n):
    return (n + 31) & ~31


def fnv1a(b):
    h = 2166136261
    for x in b:
        h = ((h ^ x) * 16777619) & 0xffffffff
    return h


def key_of(b):
    return '%08x-%08x' % (zlib.crc32(b) & 0xffffffff, fnv1a(b))


class Prepared:
    def __init__(self, d):
        self.d = d
        size, base = struct.unpack_from('<I4xI', d, 32 + 4)
        assert U32(d, 32) == 0 and base + size == len(d), 'type-0 body must end the container'
        self.base, self.size = base, size
        b = self.b = d[base:base + size]
        n, rel = struct.unpack_from('<2I', b)
        self.n, self.rel = n, rel
        assert len(b) - rel == 64, 'expected the 64-byte static REL descriptor'
        self.offs = list(struct.unpack_from('<%dI' % n, b, 16))
        self.tags = [bytes(b[16 + 4 * n + 4 * i:20 + 4 * n + 4 * i]) for i in range(n)]
        self.first = min(o for o in self.offs if o)
        self.tab = {}
        for t in (b'ESQ\0', b'NTR\0', b'MTC\0'):
            self.tab[t] = self.offs[self.tags.index(t)]
        self.boundary = min(self.tab.values())
        assert self.tags[-3:] == [b'ESQ\0', b'NTR\0', b'MTC\0'], self.tags[-3:]
        self.starts = sorted(set(o for o in self.offs if self.first <= o < self.boundary))
        self.ends = self.starts[1:] + [self.boundary]
        mo = self.tab[b'MTC\0']
        assert b[mo:mo + 8] == b'R4MOTBL\0' and U32(b, mo + 8) == 2
        cnt = U32(b, mo + 12)
        self.mtc = {}
        for k in range(cnt):
            off, sz, crc, fnv, hot = struct.unpack_from('<5I', b, mo + 32 + 20 * k)
            self.mtc[off] = dict(bytes=sz, crc=crc, fnv=fnv, hot=hot, key='%08x-%08x' % (crc, fnv))

    def slots_at(self, off):
        return [i for i, o in enumerate(self.offs) if o == off and self.tags[i] != b'\0\0\0\0']

    def member(self, off):
        return self.b[off:self.ends[self.starts.index(off)]]


def ps2_entries(iso, name):
    raw = ps2_bin.afs_read(iso, name)
    return raw, {i: (t, b) for i, t, b in ps2_bin.dat_entries(raw)}


def rewrite(a):
    src = open(a.payload, 'rb').read()
    P = Prepared(src)
    raw, ps2 = ps2_entries(a.iso, a.name)
    rep = dict(payload=a.payload, payload_sha256=hashlib.sha256(src).hexdigest(), ps2=a.name,
               ps2_sha256=hashlib.sha256(raw).hexdigest(), clips=[], seq_changed=[], keys_new=[])
    keys = {}
    new_members = []  # (old start, old end, new bytes, mtc row or None)
    for s, e in zip(P.starts, P.ends):
        m = P.b[s:e]
        slots = P.slots_at(s)
        tag = P.tags[slots[0]] if slots else None
        if tag not in (b'FCV\0', b'SEQ\0'):
            new_members.append((s, e, m, None))
            continue
        assert all(P.tags[i] == tag for i in slots), 'mixed alias at %#x' % s
        cands = set()
        for i in slots:
            if i not in ps2 or ps2[i][0] != tag.rstrip(b'\0').decode():
                raise SystemExit('slot %d %s: PS2 entry missing or tagged %s' % (i, tag, ps2.get(i, ('-',))[0]))
            cands.add(ps2[i][1])
        if len(cands) != 1:
            raise SystemExit('slots %s alias one member but their PS2 entries differ' % slots)
        p = cands.pop()
        if tag == b'SEQ\0':
            new = ps2_seq_host(p)
            new = new + bytes([0xCD]) * (al32(len(new)) - len(new))
            old = m[:host_len('SEQ', m)]
            if new[:len(old)] != old or len(new) != len(old):
                rep['seq_changed'].append(slots)
            new_members.append((s, e, new, None))
            continue
        new = ps2_fcv_host(p)
        assert len(new) % 32 == 0, 'PS2 FCV not 32-byte sized'
        row = P.mtc.get(s)
        oldfull = None
        if row:
            oldfull = dict(bytes=row['bytes'], key=row['key'], max_frame=struct.unpack_from('<H', m)[0], joints=m[2])
        else:
            oldfull = dict(bytes=len(m), max_frame=struct.unpack_from('<H', m)[0], joints=m[2])
        c = dict(slots=slots, arc=[i + 4 for i in slots], gc=oldfull, ps2_bytes=len(new),
                 ps2_max_frame=struct.unpack_from('<H', new)[0], ps2_joints=new[2])
        pre = prefix(new) if new[2] else 0
        if row and new[2] and len(new) <= MAX_CLIP and al32(pre) < len(new):  # the slot's residency policy is kept
            k = key_of(new)
            if k in keys and keys[k] != new:
                raise SystemExit('motion identity collision ' + k)
            keys[k] = new
            hot = row['hot'] if row else 0
            res = new[:pre] + bytes(al32(pre) - pre)
            c.update(key=k, hot=hot, streamed=True)
            new_members.append((s, e, res, dict(bytes=len(new), crc=zlib.crc32(new) & 0xffffffff, fnv=fnv1a(new), hot=hot)))
        else:
            if row:
                rep.setdefault('notes', []).append('slot %s: PS2 clip stays whole (was streamed)' % slots)
            c.update(streamed=False)
            new_members.append((s, e, new, None))
        c['changed'] = (row is None and new != m) or (row is not None and c.get('key') != row['key'])
        rep['clips'].append(c)
    # layout
    hdr = P.b[:P.first]
    out = bytearray(hdr)
    starts_new = []
    for s, e, nb, _ in new_members:
        starts_new.append(len(out))
        out += nb
    boundary_new = len(out)
    old_starts = [s for s, _, _, _ in new_members]
    changed_size = {s: (len(nb) != e - s) for s, e, nb, _ in new_members}

    def mapped(x):
        if x >= P.boundary:  # tables + REL keep their sizes and order
            return boundary_new + (x - P.boundary)
        if x < P.first:
            return x
        k = bisect.bisect_right(old_starts, x) - 1
        s = old_starts[k]
        if x != s and changed_size[s]:
            raise SystemExit('archive offset %#x points inside a resized member %#x' % (x, s))
        return starts_new[k] + (x - s)
    # tables: same sizes, rows remapped
    esq_o, ntr_o, mtc_o = P.tab[b'ESQ\0'], P.tab[b'NTR\0'], P.tab[b'MTC\0']
    esq = bytearray(P.b[esq_o:ntr_o]); ntr = bytearray(P.b[ntr_o:mtc_o]); mtc = bytearray(P.b[mtc_o:P.rel])
    rel_desc = P.b[P.rel:]
    final = boundary_new + len(esq) + len(ntr) + len(mtc) + len(rel_desc)
    for t, stride, fields in ((esq, 12, (0,)), (ntr, 12, (0, 4, 8))):
        cnt = U32(t, 12)
        assert U32(t, 16) == stride
        for r in range(cnt):
            for f in fields:
                o = 32 + stride * r + f
                struct.pack_into('<I', t, o, mapped(U32(t, o)))
        struct.pack_into('<I', t, 20, zlib.crc32(bytes(t[32:32 + stride * cnt])) & 0xffffffff)
    struct.pack_into('<I', esq, 24, final)
    struct.pack_into('<I', ntr, 28, final)
    rows = [(starts_new[k], r) for k, (_, _, _, r) in enumerate(new_members) if r]
    cap = (len(mtc) - 32) // 20
    if len(rows) > cap:
        raise SystemExit('MTC table has room for %d rows, need %d' % (cap, len(rows)))
    tbl = b''.join(struct.pack('<5I', o, r['bytes'], r['crc'], r['fnv'], r['hot']) for o, r in rows)
    mtc[32:] = tbl + bytes(len(mtc) - 32 - len(tbl))
    struct.pack_into('<I', mtc, 12, len(rows))
    struct.pack_into('<I', mtc, 20, zlib.crc32(tbl) & 0xffffffff)
    struct.pack_into('<I', mtc, 24, final)
    out += esq + ntr + mtc + rel_desc
    assert len(out) == final
    struct.pack_into('<I', out, 4, final - 64)
    for i, o in enumerate(P.offs):
        struct.pack_into('<I', out, 16 + 4 * i, mapped(o))
    cont = bytearray(src[:P.base]) + out
    struct.pack_into('<I', cont, 32 + 4, len(out))
    os.makedirs(os.path.join(a.outdir, 'em'), exist_ok=True)
    os.makedirs(os.path.join(a.outdir, 'dc', 'mot'), exist_ok=True)
    name = os.path.basename(a.payload)
    open(os.path.join(a.outdir, 'em', name), 'wb').write(cont)
    have = set(os.listdir(a.mot_dir)) if a.mot_dir else set()
    for k, v in sorted(keys.items()):
        fn = k + '.fcv'
        if fn in have:
            assert open(os.path.join(a.mot_dir, fn), 'rb').read() == v
            continue
        open(os.path.join(a.outdir, 'dc', 'mot', fn), 'wb').write(v)
        rep['keys_new'].append(fn)
    ch = [c for c in rep['clips'] if c['changed']]
    rep.update(out_sha256=hashlib.sha256(bytes(cont)).hexdigest(), body_bytes=[P.size, len(out)],
               hot_bytes=[sum(r['bytes'] for r in P.mtc.values() if r['hot']), sum(r['bytes'] for _, r in rows if r['hot'])],
               mtc_rows=[len(P.mtc), len(rows)], fcv_members=len(rep['clips']), fcv_changed=len(ch),
               length_changes=[dict(arc=c['arc'], gc=c['gc']['max_frame'], ps2=c['ps2_max_frame']) for c in ch
                               if c['gc']['max_frame'] != c['ps2_max_frame']])
    json.dump(rep, open(os.path.join(a.outdir, 'report-%s.json' % os.path.splitext(name)[0]), 'w'), indent=1)
    print('%s: %d FCV members (%d PS2-changed), %d SEQ changed, %d length changes, body %d -> %d B, hot %d -> %d B, '
          'MTC rows %d -> %d, new keys %d' % (name, len(rep['clips']), len(ch), len(rep['seq_changed']),
                                              len(rep['length_changes']), P.size, len(out), rep['hot_bytes'][0],
                                              rep['hot_bytes'][1], len(P.mtc), len(rows), len(rep['keys_new'])))


def verify(a):
    new = Prepared(open(a.rewritten, 'rb').read())
    old = Prepared(open(a.payload, 'rb').read())
    _, ps2 = ps2_entries(a.iso, a.name)
    mot = {}
    for d in a.mot:
        for f in os.listdir(d):
            mot.setdefault(f, os.path.join(d, f))
    bad = []
    nb, ob = new.b, old.b
    assert new.n == old.n and new.tags == old.tags
    assert new.d[:36] + new.d[40:old.base] == old.d[:36] + old.d[40:old.base], 'container head changed (beyond the body size word)'
    ok = dict(fcv_streamed=0, fcv_whole=0, seq=0, other=0)
    for i in range(new.n):
        t = new.tags[i]
        if t in (b'ESQ\0', b'NTR\0', b'MTC\0', b'\0\0\0\0'):
            continue
        no, oo = new.offs[i], old.offs[i]
        if t == b'FCV\0':
            want = ps2_fcv_host(ps2[i][1])
            row = new.mtc.get(no)
            m = new.member(no)
            if row:
                f = mot.get(row['key'] + '.fcv')
                if not f:
                    bad.append('slot %d: key file %s missing' % (i, row['key'])); continue
                k = open(f, 'rb').read()
                pre = prefix(k)
                if zlib.crc32(k) & 0xffffffff != row['crc'] or fnv1a(k) != row['fnv'] or len(k) != row['bytes']:
                    bad.append('slot %d: key identity' % i)
                if m != k[:pre] + bytes(al32(pre) - pre):
                    bad.append('slot %d: resident prefix != key head' % i)
                for j in range(k[2]):
                    q = U32(k, pre - 4 * k[2] + 4 * j)
                    if q < pre or q >= len(k):
                        bad.append('slot %d: key offset out of range' % i)
                got = k; ok['fcv_streamed'] += 1
            else:
                got = m; ok['fcv_whole'] += 1
            if got != want:
                bad.append('slot %d: decoded clip != PS2' % i)
        elif t == b'SEQ\0':
            want = ps2_seq_host(ps2[i][1])
            if new.member(no)[:len(want)] != want:
                bad.append('slot %d: SEQ != PS2' % i)
            ok['seq'] += 1
        else:
            if new.member(no) != old.member(oo):
                bad.append('slot %d %s: non-motion member changed' % (i, t))
            ok['other'] += 1
    for t, stride, fields in ((b'ESQ\0', 12, (0,)), (b'NTR\0', 12, (0, 4, 8))):
        no_, oo_ = new.tab[t], old.tab[t]
        cnt = U32(nb, no_ + 12)
        if zlib.crc32(nb[no_ + 32:no_ + 32 + stride * cnt]) & 0xffffffff != U32(nb, no_ + 20):
            bad.append('%s crc' % t)
        for r in range(cnt):
            for f in fields:
                x, y = U32(nb, no_ + 32 + stride * r + f), U32(ob, oo_ + 32 + stride * r + f)
                if nb[x:x + 32] != ob[y:y + 32]:
                    bad.append('%s row %d field %d points elsewhere' % (t, r, f))
    mo = new.tab[b'MTC\0']
    if zlib.crc32(nb[mo + 32:mo + 32 + 20 * U32(nb, mo + 12)]) & 0xffffffff != U32(nb, mo + 20):
        bad.append('MTC crc')
    for t in (b'ESQ\0', b'MTC\0'):
        if U32(nb, new.tab[t] + 24) != len(nb):
            bad.append('%s archive size' % t)
    if U32(nb, new.tab[b'NTR\0'] + 28) != len(nb):
        bad.append('NTR archive size')
    if nb[new.rel:] != ob[old.rel:]:
        bad.append('REL descriptor changed')
    hot_old = {tuple(old.slots_at(o)) for o, r in old.mtc.items() if r['hot']}
    hot_new = {tuple(new.slots_at(o)) for o, r in new.mtc.items() if r['hot']}
    if hot_old != hot_new:
        bad.append('hot set differs')
    print('VERIFY %s: %s %s' % ('PASS' if not bad else 'FAIL', json.dumps(ok), '; '.join(bad[:20])))
    return 0 if not bad else 1


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('rewrite')
    for k in ('payload', 'iso', 'name', 'outdir'):
        p.add_argument(k)
    p.add_argument('--mot-dir')
    v = sub.add_parser('verify')
    for k in ('rewritten', 'payload', 'iso', 'name'):
        v.add_argument(k)
    v.add_argument('mot', nargs='+')
    a = ap.parse_args()
    if a.cmd == 'rewrite':
        rewrite(a)
    else:
        sys.exit(verify(a))


if __name__ == '__main__':
    main()
