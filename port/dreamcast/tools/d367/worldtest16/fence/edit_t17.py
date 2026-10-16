"""edit_t17.py (WSL): land17: KI fence row -> test 17; wt17terr (r108 + r10a terrain-only level 5) appended to T15_DATA."""
R = '/root/probe/worldtest16-20261016/land17/port/dreamcast/'


def edit(path, pairs):
    s = open(path, encoding='utf-8').read()
    for a, b in pairs:
        assert s.count(a) == 1, (path, a[:70], s.count(a))
        s = s.replace(a, b)
    open(path, 'w', encoding='utf-8').write(s)
    print('edited', path)


edit(R + 'docs/KNOWN_ISSUES.md', [
    ("simplified village scenery of test 15) | test 15 | 🟢 Fixed in test 16: the house front that holds the rails",
     "simplified village scenery of test 15) | test 15, 16 | 🟢 Fixed in test 17: the house front that holds the rails"),
    ('| 🟢 Fixed in test 8 / 9 / 9.1 / 10 / 12 / 12.1 / 13 / 15 / 16 |', '| 🟢 Fixed in test 8 / 9 / 9.1 / 10 / 12 / 12.1 / 13 / 15 / 16 / 17 |'),
])
p = R + 'tools/d367/test11/t11-fix.py'
s = open(p, encoding='utf-8').read()
old = "T15_DATA = T14_DATA + ',cast15,glod,res16,snd16,res16h,vq16w,water16i,wt16r101,fsh'"
assert s.count(old) == 1, 'T15_DATA line moved: re-read it'
s = s.replace(old, "T15_DATA = T14_DATA + ',cast15,glod,res16,snd16,res16h,vq16w,water16i,wt16r101,wt17terr,fsh'")
anchor = "for _n in ('res16c', 'res16d', 'res16e', 'res16f', 'res16g'):\n"
assert s.count(anchor) == 1
s = s.replace(anchor,
    "# Test 17 terrain-only world level 5 for r108 + r10a (lane/worldtest16 B, user plan 10-16: terrain/rock only, no structural\n"
    "# cuts; coordinator 10-16: land r108 -1.01 and r10a -0.56 ms MODELLED). Level 0 is unchanged; WORLD_VERT_LEVEL=5 loads these.\n"
    "# re4-assets-private/world-terrain-wt17-20261016 (SHA256SUMS, RECIPE.txt, class.json per room).\n"
    "WT17TD = os.environ.get('WT17TD', PRIV + '/world-terrain-wt17-20261016')\n"
    "DATA['wt17terr'] = {'dc/native/' + _r + '/ps2-wv5.re4mesh': WT17TD + '/' + _r + '/ps2-wv5.re4mesh' for _r in ('r108', 'r10a')}\n"
    + anchor)
open(p, 'w', encoding='utf-8').write(s)
print('edited', p)
