"""mkwarps.py: round 2 warp files for the 28 island route rooms not run in round 1 (lane ch5found16).
Base = the st3 lane's walk (or fight1 / post) warp; adds `god`, `alivelog 60` and, in Ganado rooms, a kill rig
(`kill <id> <frame>` + `killrep <n> <gap>`) so waves are sent, held, released and finished inside 60 s."""
import os, re
S = '/root/probe/lanes-20261014/st3/fixtures'
OUT = '/root/probe/lanes-20261016/ch5found/fixtures/wp2'
os.makedirs(OUT, exist_ok=True)
# room: (base view, kill id or None, kill count)
PLAN = {
    'r305': ('walk', 0x1e, 9), 'r306': ('walk', None, 0), 'r307': ('walk', None, 0), 'r308': ('walk', None, 0),
    'r30b': ('walk', 0x1f, 11), 'r30c': ('walk', 0x1f, 11), 'r30e': ('walk', 0x1e, 12), 'r309': ('walk', None, 0),
    'r30a': ('walk', None, 0), 'r310': ('walk', None, 0), 'r311': ('walk', 0x1f, 14), 'r312': ('walk', None, 0),
    'r30f': ('fight1', 0x1f, 40), 'r315': ('walk', 0x1e, 2), 'r316': ('post', 0x1e, 10), 'r317': ('walk', None, 0),
    'r318': ('walk', None, 0), 'r31a': ('walk', None, 0), 'r31b': ('walk', None, 0), 'r31d': ('walk', 0x1e, 9),
    'r31c': ('walk', None, 0), 'r320': ('walk', 0x1d, 40), 'r321': ('walk', 0x1f, 4), 'r325': ('walk', None, 0),
    'r326': ('walk', None, 0), 'r327': ('fight1', 0x1d, 34), 'r329': ('post', None, 0), 'r330': ('walk', 0x1f, 4),
}
for r, (view, kid, n) in PLAN.items():
    src = '%s/%s/cx-%s-%s.txt' % (S, r, r, view)
    lines = [l for l in open(src).read().split('\n') if l.strip()]
    keep = []
    for l in lines:
        if re.match(r'(kill|killrep|alivelog|god|name)\b', l):
            continue
        keep.append(l)
    out = ['name cx-%s-r2' % r, '# ch5found16 round 2: %s base %s; god, alivelog 60%s' % (r, os.path.basename(src),
           ', kill rig 0x%02x x%d gap 40' % (kid, n) if kid else '')] + keep + ['god', 'alivelog 60']
    if kid:
        out += ['kill 0x%02x 200' % kid, 'killrep %d 40' % (n - 1)]
    open('%s/cx-%s-r2.txt' % (OUT, r), 'w').write('\n'.join(out) + '\n')
    print(r, view, 'kill' if kid else '-')
