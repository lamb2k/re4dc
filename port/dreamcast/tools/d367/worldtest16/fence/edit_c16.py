"""edit_c16.py (WSL): land r101 C16 in landA: WT16D -> world-r101-wt16c16-20261016, KNOWN_ISSUES fence row fixed in 16."""
R = '/root/probe/worldtest16-20261016/landA/port/dreamcast/'


def edit(path, pairs):
    s = open(path, encoding='utf-8').read()
    for a, b in pairs:
        assert s.count(a) == 1, (path, a[:70], s.count(a))
        s = s.replace(a, b)
    open(path, 'w', encoding='utf-8').write(s)
    print('edited', path)


edit(R + 'tools/d367/test11/t11-fix.py', [
    ("# six files and R4PW tables as wv32r101 (replaces it). re4-assets-private/world-r101-wt16-20261016 (SHA256SUMS, RECIPE.txt).\n"
     "WT16D = os.environ.get('WT16D', PRIV + '/world-r101-wt16-20261016')",
     "# six files and R4PW tables as wv32r101 (replaces it). Since 10-16 evening: set C16 = that set + mesh 0x17 (the house-front\n"
     "# fence rails, which the per-vertex reduction collapsed) at level 0, re4-assets-private/world-r101-wt16c16-20261016\n"
     "# (SHA256SUMS, RECIPE.txt); the first set (C4, test 16 until then) stays in world-r101-wt16-20261016 (WT16D overrides).\n"
     "WT16D = os.environ.get('WT16D', PRIV + '/world-r101-wt16c16-20261016')"),
])
edit(R + 'docs/KNOWN_ISSUES.md', [
    ("| In the village (r101) the fence by the house on the right of the square shows only its posts, without its rails (the "
     "simplified village scenery of test 15) | test 15 | ⏸️ Open: keeping that fence's detail in the scenery simplification did "
     "not bring the rails back, so they are lost in a later step; a hand fix is planned | |",
     "| In the village (r101) the fence by the house on the right of the square shows only its posts, without its rails (the "
     "simplified village scenery of test 15) | test 15 | 🟢 Fixed in test 16: the house front that holds the rails keeps its "
     "full detail (checked in game at the village cross) | |"),
    ('| 🟢 Fixed in test 8 / 9 / 9.1 / 10 / 12 / 12.1 / 13 / 15 / 16 | Fixed and checked in our tests; the problem was not console-only | 23 |',
     '| 🟢 Fixed in test 8 / 9 / 9.1 / 10 / 12 / 12.1 / 13 / 15 / 16 | Fixed and checked in our tests; the problem was not console-only | 24 |'),
    ('| ⏸️ Open | Known, not yet worked on | 12 |', '| ⏸️ Open | Known, not yet worked on | 11 |'),
])
