#!/usr/bin/env python3
"""coll_compare.py <gc root (st1/st2 .das)> <ps2 dir (rXXX.dat)> <rooms...>   (lane assets-dc, 2026-11-02; read only)

Compares the GameCube and PS2 room collision (SAT = static, EAT = event/object collision, both the SAT format) per room.
Per section: vertex / polygon (floor, slope, wall) / block counts, identical or not (polygon sets compared as triangles of
vertex coordinates rounded to 1 unit, order free), and the regions that differ: triangles only in GC (PS2 removed:
walk-through on PS2 / possible invisible wall on our GC data) or only in PS2 (PS2 added), clustered on a 2 m XZ grid,
reported as bounding boxes in metres. Byte-swap cost: the 32/16-bit words the loader swaps from GC big-endian.
Nothing is changed; collision is gameplay and stays the user's decision.
"""
import struct, sys, os, collections
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..'))
import room_smd  # noqa: E402


def sections(data, e):
    if (data[0] & 0x80) == 0:
        return [0]
    n = data[1]
    return list(struct.unpack_from(e + '%dI' % n, data, 4))


def parse(data, base, e):
    hdr = struct.unpack_from(e + 'BB9H', data, base)
    _, _, nv, nn, ne, _, npol, nfl, nsl, nwa, nbl = hdr
    o = base + struct.calcsize(e + 'BB9H')
    V = [struct.unpack_from(e + '3f', data, o + 12 * i) for i in range(nv)]
    po = o + 12 * (nv + nn + ne)
    P = [struct.unpack_from(e + '7H2xI', data, po + 20 * i) for i in range(npol)]
    tris = []
    for p in P:
        tris.append(tuple(sorted(tuple(round(c) for c in V[k]) for k in p[:3])) + (p[7] & 0xffff,))
    # swapped words: header (9 halves) + floats (nv+nn+ne)*3 + polygons 7 halves + 1 word + blocks ~ (6f + 4H + I)
    words32 = (nv + nn + ne) * 3 + npol + nbl * 7
    halves = 9 + npol * 7 + nbl * 4
    return dict(nv=nv, npol=npol, nfl=nfl, nsl=nsl, nwa=nwa, nbl=nbl, tris=tris, w32=words32, h16=halves)


def collision(path, gc):
    d = open(path, 'rb').read()
    if d[:32] == room_smd.CONTAINER_MAGIC:
        d = room_smd.decode_das(d)
    e = room_smd.archive_endian(d)
    out = collections.OrderedDict()
    for i, (tag, s, t) in enumerate(room_smd.tagged_entries(d, e)):
        if tag in (b'SAT\0', b'EAT\0'):
            blob = d[s:t]
            try:
                for j, b in enumerate(sections(blob, e)):
                    out['%s%d.%d' % (tag[:3].decode(), i, j)] = parse(blob, b, e)
            except (struct.error, IndexError) as x:
                out['%s%d' % (tag[:3].decode(), i)] = dict(error=str(x))
    return out, e


def boxes(tris):
    cells = collections.defaultdict(list)
    for t in tris:
        xs = [v[0] for v in t[:3]]; ys = [v[1] for v in t[:3]]; zs = [v[2] for v in t[:3]]
        cells[(int(sum(xs) / 3 // 2000), int(sum(zs) / 3 // 2000))].append((min(xs), min(ys), min(zs), max(xs), max(ys), max(zs)))
    # merge adjacent cells into clusters
    seen, out = set(), []
    for c in cells:
        if c in seen: continue
        stack, grp = [c], []
        seen.add(c)
        while stack:
            x = stack.pop(); grp += cells[x]
            for dx in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    y = (x[0] + dx, x[1] + dz)
                    if y in cells and y not in seen:
                        seen.add(y); stack.append(y)
        b = [min(g[i] for g in grp) for i in range(3)] + [max(g[i] for g in grp) for i in range(3, 6)]
        out.append((len(grp), [round(v / 1000, 1) for v in b]))
    return sorted(out, reverse=True)


def main():
    gcr, ps2, rooms = sys.argv[1], sys.argv[2], sys.argv[3:]
    print('room\tsection\tgc_polys(f/s/w)\tps2_polys(f/s/w)\tsame\tgc_only\tps2_only\tswap_words\tregions (tris: x0,y0,z0..x1,y1,z1 m)')
    for r in rooms:
        st = 'st1' if r[1] == '1' else 'st2'
        gp, pp = os.path.join(gcr, st, r + '.das'), os.path.join(ps2, r + '.dat')
        if not os.path.exists(gp) or not os.path.exists(pp) or os.path.getsize(pp) == 0:
            print('%s\t-\tmissing %s' % (r, 'gc' if not os.path.exists(gp) else 'ps2')); continue
        try:
            g, _ = collision(gp, True); p, pe = collision(pp, False)
        except Exception as x:  # noqa: BLE001
            print('%s\t-\terror %s' % (r, x)); continue
        names = list(dict.fromkeys(list(g) + list(p)))
        for n in names:
            a, b = g.get(n), p.get(n)
            if not a or not b or 'error' in a or 'error' in b:
                print('%s\t%s\t%s\t%s\tsection only on one side' % (r, n, 'yes' if a else 'no', 'yes' if b else 'no')); continue
            A, B = collections.Counter(a['tris']), collections.Counter(b['tris'])
            go, po = list((A - B).elements()), list((B - A).elements())
            same = 'identical' if not go and not po else ('geometry same, attrs differ' if
                   collections.Counter(t[:3] for t in a['tris']) == collections.Counter(t[:3] for t in b['tris']) else 'differs')
            reg = []
            if same == 'differs':
                gb = boxes([t for t in go]); pb = boxes([t for t in po])
                reg = ['GC-only %d@%s' % x for x in gb[:3]] + ['PS2-only %d@%s' % x for x in pb[:3]]
            print('%s\t%s\t%d(%d/%d/%d)\t%d(%d/%d/%d)\t%s\t%d\t%d\t%d+%dh\t%s' % (
                r, n, a['npol'], a['nfl'], a['nsl'], a['nwa'], b['npol'], b['nfl'], b['nsl'], b['nwa'], same,
                len(go), len(po), a['w32'], a['h16'], '; '.join(reg)), flush=True)


if __name__ == '__main__':
    main()
