"""who.py <run.pcs> <syms> [min-ms] [top]: non-idle samples in heavy frames (>= min-ms), by (tid, pc fn, pr fn)."""
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
        cur, recs = w0, []; continue
    recs.append((0x8c000000 | ((w0 & 0x7fffff) << 1), 0x8c000000 | ((w1 & 0x7fffff) << 1), w0 >> 23))
heavy = [f for f in frames if len(f[1]) >= lo]
c = collections.Counter(); t = collections.Counter()
for _, r in heavy:
    for pc, pr, tid in r:
        t[(tid, name(pc) == 'thd_idle_task')] += 1
        if name(pc) != 'thd_idle_task': c[(tid, name(pc)[:80], name(pr)[:80])] += 1
print('tid split', sorted(t.items()))
for k, v in c.most_common(int(sys.argv[4]) if len(sys.argv) > 4 else 30): print(v, k)
print('heavy frames', [(f, len(r)) for f, r in heavy][:50])
if len(sys.argv) > 5:
    for f, r in frames:
        if f < int(sys.argv[5]): continue
        cc = collections.Counter()
        for pc, pr, tid in r:
            n = name(pc)
            k = 'idle' if n == 'thd_idle_task' else ('serial' if 'serial_wait' in n else ('motion' if 'Binding' in n or 'Binding' in name(pr) or 'crc32' in n else 't%d' % tid))
            cc[k] += 1
        print(f, len(r), dict(cc.most_common(6)))
