p = '/root/probe/worldtest16-20261016/tree/port/dreamcast/tools/ps2_world_vert_ladder.py'
s = open(p).read()
a = s.index("CLASS_RULE = (")
b = s.index("\n\n\ndef classify_parts")
rule = ("CLASS_RULE = ('terrain = opaque pass AND planarity < 0.55 (area share within 10 deg of the 6 strongest normal '\n"
        "              'directions of the part) AND >= 70% of the area in terrain-shaped pieces: ground / cliff (at least 4 m '\n"
        "              'wide in both horizontal axes) or rock (at least 0.8 m wide in both, no taller than 1.5x its width); '\n"
        "              'everything else (planar walls / roofs / furniture, beams, planks, posts, trunks, branches, small props, '\n"
        "              'cut-out cards) is structure')")
s = s[:a] + rule + s[b:]
open(p, 'w').write(s)
import ast
ast.parse(s)
print('ok')
