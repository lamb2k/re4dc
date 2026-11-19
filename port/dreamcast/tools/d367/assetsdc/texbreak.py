import json, sys, collections, re
rows = json.load(open(sys.argv[1]))
def cls(m):
    ml = m.lower()
    if ml.startswith('hud') or 'font' in ml or 'ui' == ml[:2]: return 'ui'
    if ml.startswith('source'): return 'world-source'
    mm = re.match(r'ps2 (r\d+)', ml)
    if mm: return 'ps2-room-obj'
    if ml.startswith('ps2-so'): return 'world-ps2src'
    if 'leon' in ml or 'cast' in ml or 'ganado' in ml or 'ps2mas' in ml or ml.startswith('ps2 ga'): return 'character'
    if ml.startswith('ps2 it') or ml.startswith('ps2 we') or ml.startswith('ps2 br'): return 'item/weapon/breakable'
    return 'other:' + ml[:10]
def vq_bytes(r):
    base = 2048 + r['w'] * r['h'] // 4
    return base
agg = collections.defaultdict(lambda: collections.Counter())
for r in rows:
    c = cls(r['mat']); a = agg[c]
    a['n'] += 1; a['bytes'] += r['bytes']
    raw16 = r['fmt'] in ('rgb565', 'argb4444', 'argb1555') and r['pay'] != 'vq'
    if raw16:
        a['raw16'] += 1; a['raw16_bytes'] += r['bytes']
        # VQ target with mips (4/3 of indices): saving vs today
        tgt = 2048 + (r['w'] * r['h'] // 4) * 4 // 3
        a['vq_save'] += max(0, r['bytes'] - tgt)
    if not r['mip'] and c != 'ui':
        a['nomip'] += 1
        if r['w'] >= 64: a['nomip64'] += 1
print('%-24s %6s %10s %6s %10s %6s %6s %10s' % ('class', 'n', 'bytes', 'raw16', 'raw16B', 'nomip', '>=64', 'VQsaveB'))
T = collections.Counter()
for c, a in sorted(agg.items(), key=lambda x: -x[1]['bytes']):
    print('%-24s %6d %10d %6d %10d %6d %6d %10d' % (c, a['n'], a['bytes'], a['raw16'], a['raw16_bytes'], a['nomip'], a['nomip64'], a['vq_save']))
    T.update(a)
print('%-24s %6d %10d %6d %10d %6d %6d %10d' % ('TOTAL', T['n'], T['bytes'], T['raw16'], T['raw16_bytes'], T['nomip'], T['nomip64'], T['vq_save']))
# size distribution of raw16
print(collections.Counter((r['w'], r['h']) for r in rows if r['pay'] != 'vq' and r['fmt'] in ('rgb565','argb4444')).most_common(12))
