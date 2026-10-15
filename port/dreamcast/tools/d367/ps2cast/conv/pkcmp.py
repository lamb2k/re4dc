"""pkcmp.py <old package> <new package>: every descriptor of the old room package is carried byte-identically by the
new one (descriptor record, its chunk refs' geometry arrays, textures, parents and binds); lists the additions."""
import struct, sys
K = ['desc', 'ref', 'geom', 'blob', 'tex', 'parents', 'bind', 'fmodel', 'fpart', 'ftex', 'role', 'sblob']
def load(p):
    b = open(p, 'rb').read(); sec = {}
    for k in range(12):
        kind, off, n, cnt = struct.unpack_from('<4I', b, 64 + 16 * k); sec[K[k]] = (off, n, cnt)
    return b, sec
def u(b, o): return struct.unpack_from('<I', b, o)[0]
def descs(b, sec):
    off, n, cnt = sec['desc']; out = []; pb = 0
    for d in range(cnt):
        r = b[off + 48 * d: off + 48 * d + 48]
        name = r[:16].rstrip(b'\0').decode(); w = struct.unpack_from('<8I', r, 16)
        out.append(dict(name=name, rec=r, words=w))
    return out
def chunk(b, sec, gi):
    goff = sec['geom'][0] + 64 * gi; blob = sec['blob'][0]; g = struct.unpack_from('<16I', b, goff)
    pc, nc, palc, tris, sb, uvb = g[0], g[1], g[2], g[3], g[4], g[5]
    arr = lambda o, n: b[blob + o: blob + o + n]
    return (g[:8], arr(g[8], pc * 8), arr(g[9], nc * 8), arr(g[10], uvb), arr(g[11], sb), arr(g[12], palc * 16))
def tex(b, sec, t): return b[sec['tex'][0] + 16 * t: sec['tex'][0] + 16 * t + 16]
a, sa = load(sys.argv[1]); c, sc = load(sys.argv[2])
da, dc = descs(a, sa), descs(c, sc)
ok = True; pa = pc_ = 0
for i, d in enumerate(da):
    e = dc[i] if i < len(dc) else None
    if not e or e['name'] != d['name']: print('MISSING/ORDER', d['name']); ok = False; continue
    # words: appearance, model id, bones, sections, first_chunk, skin_bytes, (parents/binds offsets...)
    same_rec = d['rec'][:16] == e['rec'][:16] and d['words'][:4] == e['words'][:4] and d['words'][5] == e['words'][5]
    bones, nsec, f0a, f0c = d['words'][2], d['words'][3], d['words'][4], e['words'][4]
    for s in range(nsec):
        ra = struct.unpack_from('<4I', a, sa['ref'][0] + 16 * (f0a + s)); rc = struct.unpack_from('<4I', c, sc['ref'][0] + 16 * (f0c + s))
        if chunk(a, sa, ra[0]) != chunk(c, sc, rc[0]): print(d['name'], 'section', s, 'geometry DIFFERS'); ok = False
        if tex(a, sa, ra[1]) != tex(c, sc, rc[1]): print(d['name'], 'section', s, 'texture DIFFERS'); ok = False
        if ra[2] != rc[2]: print(d['name'], 'section', s, 'info word differs'); ok = False
        if (ra[3] == 0) != (rc[3] == 0): print(d['name'], 'mask word presence differs'); ok = False
    P = lambda b, s_, o, n: b[s_['parents'][0] + o: s_['parents'][0] + o + n]
    B = lambda b, s_, o, n: b[s_['bind'][0] + 48 * o: s_['bind'][0] + 48 * (o + n)]
    if P(a, sa, pa, bones) != P(c, sc, pc_, bones) or B(a, sa, pa, bones) != B(c, sc, pc_, bones): print(d['name'], 'skeleton DIFFERS'); ok = False
    pa += bones; pc_ += bones
    if not same_rec: print(d['name'], 'descriptor record differs', d['words'], e['words']); ok = False
print('CARRIED' if ok else 'NOT CARRIED', [d['name'] for d in da], 'added', [d['name'] for d in dc[len(da):]], 'bytes %d -> %d' % (len(a), len(c)))
