import struct, sys, bisect, collections
pcs, syms = sys.argv[1], sys.argv[2]
lo = float(sys.argv[3]) if len(sys.argv) > 3 else 300
S = []
for l in open(syms, encoding='utf-8', errors='ignore'):
    p = l.rstrip('\n').split(' ', 2)
    if len(p) == 3:
        try: S.append((int(p[0], 16), p[2]))
        except ValueError: pass
S.sort(); A = [a for a, _ in S]
def name(x):
    i = bisect.bisect_right(A, x) - 1
    if i < 0: return '?%08x' % x
    if x - S[i][0] > 0x20000: return 'ovl/heap %08x' % (x & ~0xfff)
    return S[i][1]
raw = open(pcs, 'rb').read()
frames = []; cur = None; recs = []
for off in range(128, len(raw) - 7, 8):
    w0, w1 = struct.unpack_from('<II', raw, off)
    if w1 == 0xFFFFFFFF: continue
    if w1 & 0x80000000 and not (w1 & 0x70000000):
        if cur is not None: frames.append((cur, recs))
        cur, recs = w0, []
        continue
    pc = 0x8c000000 | ((w0 & 0x7fffff) << 1); pr = 0x8c000000 | ((w1 & 0x7fffff) << 1); tid = w0 >> 23
    recs.append((pc, pr, tid))
heavy = [f for f in frames if len(f[1]) >= lo]
light = [f for f in frames if len(f[1]) < lo]
print('frames', len(frames), 'heavy(>=%d ms)' % lo, len(heavy), 'first heavy', heavy[0][0] if heavy else None,
      'samples heavy', sum(len(r) for _, r in heavy))
for label, fs in (('HEAVY', heavy), ('LIGHT', light[-60:])):
    c = collections.Counter(); cp = collections.Counter(); ct = collections.Counter()
    n = 0
    for _, r in fs:
        for pc, pr, tid in r:
            c[name(pc)] += 1; cp[(name(pc), name(pr))] += 1; ct[tid] += 1; n += 1
    print('==', label, 'samples', n, 'tids', ct.most_common(4))
    for k, v in c.most_common(25): print('  %5.1f%% %s' % (100.0 * v / max(n, 1), k))
    print('  -- pc <- pr')
    for (a, b), v in cp.most_common(15): print('  %5.1f%% %s <- %s' % (100.0 * v / max(n, 1), a, b))
