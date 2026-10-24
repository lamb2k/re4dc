#!/usr/bin/env python3
"""ps2_motion.py (lane purge-motion24, 2026-10-24): the PS2 version's FCV/SEQ motion into a prepared (little-endian) drs.

  ps2_motion.py leon <payload.drs> <ps2 iso> <ps2 dat name> <out.drs> [--report out.json]

PS2 motion (BIO4DAT.AFS plNN.dat / emNN.dat) is the GameCube FCV/SEQ codec stored little-endian, entry for entry in
the same archive slots. The port's prepared drs already holds le_mirror's host image of each GC member
(fmt_fcv: every u16/f32/s16 field swapped, same layout; fmt_fcvseq: count + key frame u16 swapped, Se/Free bytes kept).
  FCV: the PS2 bytes ARE that host image (proved per member: the PS2 entry parses after a structural LE->BE swap and
       re-serialises to the same bytes with fcv.serialise(m, '<')).
  SEQ: the PS2 key is one u32 (frame << 16 | Se << 8 | Free); the host key is {u16 frame, u8 Se, u8 Free}.
Members are replaced IN PLACE: a PS2 member must fit its slot (the slot's tail is refilled with 0xCD), so every archive
offset, the appended head data (garr18h) and every other byte stay. Non-motion members are never touched.
Refuses: a tag mismatch, a PS2 member that does not round-trip, a member larger than its slot.
"""
import argparse, hashlib, json, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..'))                       # port/dreamcast/tools (ps2_bin)
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', '..', '..', 'tools'))   # repo tools (motion.fcv)
import ps2_bin  # noqa: E402
from motion import fcv  # noqa: E402

FILL = 0xCD


def fcv_le_to_be(d):
    """Structural swap of a little-endian FCV entry to the GC big-endian layout (fcv.parse's input)."""
    b = bytearray(d)

    def sw(o, w):
        b[o:o + w] = d[o:o + w][::-1]
    n = d[2]
    sw(0, 2)
    if n == 0:
        sw(4, 4)
        return bytes(b)
    infos = struct.unpack('<%dH' % n, d[3:3 + 2 * n])
    for i in range(n):
        sw(3 + 2 * i, 2)
    o = (3 + 3 * n + 3) & ~3
    sw(o, 4)
    o += 4
    ofs = struct.unpack('<%dI' % n, d[o:o + 4 * n])
    for i in range(n):
        sw(o + 4 * i, 4)
    for i in range(n):
        vf, tf = fcv.FCC_FMT[infos[i] >> 12]
        fields = [vf] + ([tf, tf] if tf else [])
        p = ofs[i]
        for _ in range(3):
            k, = struct.unpack('<H', d[p:p + 2])
            sw(p, 2)
            p += 2
            for _m in range(k):
                sw(p, 2)
                p += 2
            for _m in range(k):
                for f in fields:
                    w = fcv.FMT_SIZE[f]
                    if w > 1:
                        sw(p, w)
                    p += w
    return bytes(b)


def ps2_fcv_host(d):
    """The PS2 FCV entry as the port's host image (== the entry itself, proved)."""
    if d[2] == 0:
        return d  # empty motion (maxFrame, no joints): read as such by both layouts
    m = fcv.parse(fcv_le_to_be(d))
    if fcv.serialise(m, '<') != d:
        raise ValueError('PS2 FCV does not round-trip through the codec')
    return d


def ps2_seq_host(d):
    count, = struct.unpack('<H', d[:2])
    if d[3] != 0:
        raise ValueError('PS2 SEQ pad byte not zero')
    b = bytearray(d)
    for i in range(count):
        w, = struct.unpack_from('<I', d, 4 + 4 * i)
        struct.pack_into('<HBB', b, 4 + 4 * i, w >> 16, (w >> 8) & 0xFF, w & 0xFF)
    be = bytearray(b)  # validate through the GC parser (BE view of the host image)
    be[0:2] = b[1::-1][:2]
    for i in range(count):
        o = 4 + 4 * i
        be[o:o + 2] = b[o:o + 2][::-1]
    fcv.parse_seq(bytes(be))
    return bytes(b)


def host_len(tag, d):
    """Logical length of a host-image member (its slot may run further: the last member / appended data)."""
    if tag == 'FCV':
        if d[2] == 0:
            return 32
        n = d[2]
        o = (3 + 3 * n + 3) & ~3
        return struct.unpack_from('<I', d, o)[0]
    count, = struct.unpack('<H', d[:2])
    return (4 + 4 * count + 31) & ~31


def le_body(d):
    n, rel = struct.unpack_from('<II', d, 0x400)
    offs = struct.unpack_from('<%dI' % n, d, 0x410)
    tags = [d[0x410 + 4 * n + 4 * i:0x414 + 4 * n + 4 * i].rstrip(b'\0').decode('ascii', 'replace') for i in range(n)]
    ends = list(offs[1:]) + [rel or (len(d) - 0x400)]
    return [(tags[i], 0x400 + offs[i], 0x400 + ends[i]) for i in range(n)]


def leon(args):
    d = bytearray(open(args.payload, 'rb').read())
    src = bytes(d)
    ps2raw = ps2_bin.afs_read(args.iso, args.name)
    ps2 = {i: (t, b) for i, t, b in ps2_bin.dat_entries(ps2raw)}
    rep = {'payload': args.payload, 'payload_sha256': hashlib.sha256(src).hexdigest(), 'ps2': args.name,
           'ps2_sha256': hashlib.sha256(ps2raw).hexdigest(), 'same': [], 'replaced': []}
    for i, (tag, a, e) in enumerate(le_body(src)):
        if tag not in ('FCV', 'SEQ'):
            continue
        if i not in ps2 or ps2[i][0] != tag:
            raise SystemExit('member %d %s: PS2 entry missing or tagged %s' % (i, tag, ps2.get(i, ('-',))[0]))
        new = ps2_fcv_host(ps2[i][1]) if tag == 'FCV' else ps2_seq_host(ps2[i][1])
        old = src[a:a + host_len(tag, src[a:e])]
        if new == old:
            rep['same'].append(i)
            continue
        if len(new) > e - a:
            raise SystemExit('member %d %s: PS2 %d B does not fit slot %d B' % (i, tag, len(new), e - a))
        tail = min(e, a + max(len(old), len(new)))  # refill only the motion's own bytes; data after it stays
        d[a:a + len(new)] = new
        d[a + len(new):tail] = bytes([FILL]) * (tail - a - len(new))
        r = {'member': i, 'tag': tag, 'gc_bytes': len(old), 'ps2_bytes': len(new)}
        if tag == 'FCV' and new[2]:
            r['max_frame'] = [struct.unpack('<H', old[:2])[0], struct.unpack('<H', new[:2])[0]]
            r['joints'] = [old[2], new[2]]
        if tag == 'SEQ':
            r['keys'] = [[list(struct.unpack_from('<HBB', x, 4 + 4 * k)) for k in range(struct.unpack('<H', x[:2])[0])]
                         for x in (old, new)]
        rep['replaced'].append(r)
    open(args.out, 'wb').write(d)
    rep['out_sha256'] = hashlib.sha256(bytes(d)).hexdigest()
    rep['changed_bytes'] = sum(1 for x, y in zip(src, d) if x != y)
    if args.report:
        json.dump(rep, open(args.report, 'w'), indent=1)
    print('%s: %d motion members PS2-identical, %d replaced %s; %d bytes changed; out %s' % (
        args.name, len(rep['same']), len(rep['replaced']), [r['member'] for r in rep['replaced']],
        rep['changed_bytes'], rep['out_sha256'][:16]))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('leon')
    for k in ('payload', 'iso', 'name', 'out'):
        p.add_argument(k)
    p.add_argument('--report')
    a = ap.parse_args()
    leon(a)


if __name__ == '__main__':
    main()
