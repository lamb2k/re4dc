p = '/root/probe/worldtest16-20261016/tree/port/dreamcast/docs/KNOWN_ISSUES.md'
s = open(p, encoding='utf-8').read()
old = ("| In the village (r101) the burning stake has lost its crossbar and a plank of the pyre, and the fence by the house on the "
       "right of the square shows only its posts (the simplified village scenery of test 15) | test 15 | 🟢 Fixed in test 16: the "
       "stake, the pyre and the fences around the square keep their full detail (checked in game at the village cross) | |\n")
new = ("| In the village (r101) the burning stake has lost its crossbar and a plank of the pyre (the simplified village scenery "
       "of test 15) | test 15 | 🟢 Fixed in test 16: the stake and the pyre keep their full detail (checked in game at the village "
       "cross) | |\n"
       "| In the village (r101) the fence by the house on the right of the square shows only its posts, without its rails (the "
       "simplified village scenery of test 15) | test 15 | ⏸️ Open: keeping that fence's detail in the scenery simplification did "
       "not bring the rails back, so they are lost in a later step; a hand fix is planned | |\n")
assert s.count(old) == 1
s = s.replace(old, new)
o = '| ⏸️ Open | Known, not yet worked on | 12 |'
assert s.count(o) == 1
s = s.replace(o, '| ⏸️ Open | Known, not yet worked on | 13 |')
open(p, 'w', encoding='utf-8').write(s)
print('ok')
