#!/usr/bin/env python3
# assets-dc texture audit: every dc/tex.pak package texture -> format, payload, mips, pow2, bytes.
import struct, sys, collections, json
pak = sys.argv[1]; out = sys.argv[2]
b = open(pak, 'rb').read()
_, _, cnt, io, _ = struct.unpack_from('<8s4I', b, 0)
FMT = {0: 'rgb565', 1: 'argb1555', 2: 'argb4444', 3: 'pal4', 4: 'pal4a', 5: 'pal8a'}
PAY = {0: 'linear', 1: 'twiddled', 2: 'vq'}
rows = []
for i in range(cnt):
    k0, k1, o, n = struct.unpack_from('<4I', b, io + 16 * i)
    p = b[o:o + n]
    (mg, ver, hs, stride, tc, toff, doff, dsz, crc, sic, fl) = struct.unpack_from('<8s10I', p, 0)
    for t in range(tc):
        q = toff + t * stride
        mat = p[q:q + 64].split(b'\0')[0].decode('latin1')
        w, h, f, to, ts, tf, pay = struct.unpack_from('<7I', p, q + 64)
        rows.append(dict(key='%08x-%08x' % (k0, k1), mat=mat, w=w, h=h, fmt=FMT.get(f, str(f)),
                         pay=PAY.get(pay, str(pay)), mip=bool(tf & 4), alpha=bool(tf & 1), topdrop=bool(tf & (1 << 30)),
                         bytes=ts, pkgbytes=n, ntex=tc))
json.dump(rows, open(out, 'w'))
pow2 = lambda x: x & (x - 1) == 0
c = collections.Counter((r['fmt'], r['pay'], r['mip']) for r in rows)
by = collections.Counter();
for r in rows: by[(r['fmt'], r['pay'], r['mip'])] += r['bytes']
print('textures', len(rows), 'packages', cnt, 'pak bytes', len(b))
for k, v in sorted(c.items(), key=lambda x: -by[x[0]]): print('%-10s %-9s mip=%d n=%5d bytes=%9d' % (k[0], k[1], k[2], v, by[k]))
print('non-pow2', sum(1 for r in rows if not (pow2(r['w']) and pow2(r['h']))))
print('mat prefixes', collections.Counter(r['mat'][:6] for r in rows).most_common(30))
