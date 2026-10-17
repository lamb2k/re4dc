# mkfix.py <outdir> <begin> <end> <kill start> <kill gap> <kill count>: the 14 cap comparison scenes (warp.txt,
# bench2..14.txt) of "RE4DC Cap Compare (NOT THE GAME)" (lane cap16, CAP_COMPARE=1 BENCHMARK=1).
#   1-4  r101 cross (the public benchmark's scene 1 spot: Leon by the burning cross facing the square), cap 3 / 4 / 5 / 6
#   5-8  r103 farm from the r101 door (warp.py r103-entry: where the player arrives after the village fight), cap 3 / 6,
#        animals as shipped (test 16 = PS2 list: 3 cows, 3 chickens, the dog) and animals off (`dead` = not spawned)
# Every scene: god mode, no pad input, the crowd alerted at room frame 30 (they converge on Leon and grab him), and
# from <kill start> the kill rig kills the live Ganado nearest to Leon every <kill gap> frames (<kill count> kills: hurt
# and death animations, blood, drops) - the worst moments of the fight inside the measured window. Same fixture text
# per arm except the cap / animals line, each scene from a soft reset (same start state).
import sys, os
out, b, e, ks, kg, kn = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]), int(sys.argv[6])
os.makedirs(out, exist_ok=True)
ANIMALS = '0x51 0x52 0x53 0x56 0x5A 0x5B 0x5D'   # r103 list entries alive on test 16 (PS2 list): cows, dog, chickens
R101 = """room 0x101
pos -7914 0 2000
ang 1.5708
find 0x00002000
"""
R103 = """room 0x103
pos -47609 12 7084
ang 1.889
"""
scenes = [
    ('r101-c3', R101, 3, False, 'R101 CAP 3'),
    ('r101-c4', R101, 4, False, 'R101 CAP 4'),
    ('r101-c5', R101, 5, False, 'R101 CAP 5'),
    ('r101-c6', R101, 6, False, 'R101 CAP 6'),
    ('farm-c3', R103, 3, False, 'FARM C3 ANIM'),
    ('farm-c3-noanim', R103, 3, True, 'FARM C3 NOANIM'),
    ('farm-c6', R103, 6, False, 'FARM C6 ANIM'),
    ('farm-c6-noanim', R103, 6, True, 'FARM C6 NOANIM'),
]
# 9-14 (coordinator 10-16, "rendering transparency layers"): the cap 6 fights with translucent draws left out
# (MIST_CUT runtime mask, draw-time only): T1 16 = the PS2 world's translucent pass, T2 237 = every effect sprite class
# (haze, glows, dust, fire, shots / blood, water), T3 255 = both ("no alpha at all"). T0 = scenes 4 and 7.
MIST = {}
for k, (room, rn) in enumerate(((R101, 'R101'), (R103, 'FARM'))):
    for t, mask in ((1, 16), (2, 237), (3, 255)):
        MIST[len(scenes)] = mask
        scenes.append(('%s-c6-t%d' % (rn.lower(), t), room, 6, False, '%s C6 T%d' % (rn, t)))
for i, (nm, room, cap, noanim, title) in enumerate(scenes):
    f = 'warp.txt' if i == 0 else 'bench%d.txt' % (i + 1)
    rid = '0x101' if 'room 0x101' in room else '0x103'
    txt = f"""name cap-{nm}
# RE4DC Cap Compare (lane cap16, NOT THE GAME) scene {i + 1}: cap {cap}{', animals off' if noanim else ''}. God, no pad input,
# alert at room frame 30, kill rig from {ks} every {kg} frames ({kn} kills, nearest Ganado). Measure {b}..{e}.
{room}inv default
god
cap {cap}
mistcut {MIST.get(i, 0)}
"""
    if noanim:
        txt += f"dead {ANIMALS}\n"
    txt += f"""alert 30
alivelog 150
kill 0 {ks} {rid}
killrep {kn - 1} {kg}
bench {i + 1} {b} {e} {title}
"""
    open(os.path.join(out, f), 'w', newline='\n').write(txt)
    assert len(txt) < 2048
print('ok', out)
