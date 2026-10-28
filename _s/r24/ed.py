import sys
p = sys.argv[1] + '/port/dreamcast/tools/d367/test11/t11-fix.py'
s = open(p).read()
a = "    d['remove'] = sorted(rm)\n    d.setdefault('provenance', {})['t11']"
assert s.count(a) == 1
s = s.replace(a, "    motion_key_gate(r, rm, rec)\n" + a)
b = "def graft_all(grafts, r, out, rec):\n"
assert s.count(b) == 1
s = s.replace(b, '''def motion_key_gate(r, rm, rec):
    """MOTION-KEYS (lane cast-ps2-25 10-26, Test 25 r100 house siege halted on "RE4DC MISSING: motion key read"): every
    dc/mot key the live MTC table of a staged archive names must not be on the fixture's remove list (a data set took a
    key off the disc that a later-staged archive still streams, e.g. a stale em/em1X.drs with GameCube Ganado motion over
    pmgan24's). The whole-tree check (keys present on the final disc) is rr's MOTION-KEYS row (motion/mot_refs.py)."""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'motion'))
    import mot_refs
    bad, n = {}, 0
    for k, v in sorted(r.items()):
        if not (isinstance(v, str) and k.endswith(('.drs', '.dar', '.arc', '.das')) and os.path.isfile(v)):
            continue
        b = open(v, 'rb').read()
        if mot_refs.MAGIC not in b:
            continue
        for _p, keys in mot_refs.tables(b):
            for key in keys:
                n += 1
                if 'dc/mot/%s.fcv' % key in rm and 'dc/mot/%s.fcv' % key not in r:
                    bad.setdefault(key, []).append(k)
    assert not bad, ('MOTION-KEYS: staged archives stream dc/mot keys the fixture removes (check the order of the '
                     'motion sets and stale stores, e.g. PS2SND24D)', {k: sorted(set(v)) for k, v in bad.items()})
    rec.append('motion keys gate: %d MTC rows of staged archives, none removed' % n)


''' + b)
a2 = "PS2SND24D = os.environ.get('PS2SND24D', '/root/re4data/private/ps2snd24-20261024')"
assert s.count(a2) == 1
s = s.replace(a2, """# Default = the regenerated store the release recipe exports (rr/recipe.conf; lane cast-ps2-25 10-26): the older
# ps2snd24-20261024 em/em1[1-7].drs carry the GameCube Ganado motion pmgan24 replaced, whose keys pmgan24 removes; staged
# after pmgan24 (worldopt26's arms, no recipe export) they halted the r100 house siege on a missing dc/mot key.
PS2SND24D = os.environ.get('PS2SND24D', '/root/re4data/private/ps2snd24-t24-20261024')""")
open(p, 'w').write(s)
print('ok')
