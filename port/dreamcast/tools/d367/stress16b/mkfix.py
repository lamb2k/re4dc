# mkfix.py <outdir> <begin> <end>: the four Saddler stress scenes (warp.txt, bench2..4.txt).
import sys, os
out, b, e = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
os.makedirs(out, exist_ok=True)
scenes = [('warp.txt', 0, 'FULL'), ('bench2.txt', 1, 'G70'), ('bench3.txt', 2, 'G50'), ('bench4.txt', 0, 'FULL 2')]
for i, (f, lod, nm) in enumerate(scenes):
    open(os.path.join(out, f), 'w', newline='\n').write(f"""name stress-saddler-{nm.lower().replace(' ', '')}
# Saddler stress disc (lane stress16b, NOT THE GAME): r119 (village at night, after the Gigante: rsf 0x119 0) stands in
# for the final island room r332. Saddler (em31: body + tentacle, STRESS_SADDLER idle / head-attack loop, no boss logic)
# set 6 m in front of Leon at room frame 30; registry level {lod} (0 full PS2 cast, 1 g70, 2 g50). God, no pad input.
# Leon stands where the Gigante fixtures fight (124500 2251 10888, facing -x into the open village). Settle to room frame {b}, measure {b}..{e}.
room 0x119
pos 124500 2251 10888
ang -1.571
rsf 0x119 0
inv default
god
saddler 30 rel 6000 {lod}
bench {i + 1} {b} {e} SADDLER {nm}
""")
print('ok', out)
