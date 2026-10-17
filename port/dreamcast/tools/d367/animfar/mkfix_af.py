# mkfix_af.py <outroot>: lane animfar17 fixture dirs. bench = the cap16 14-scene set (Flycast twin window 300..600,
# kill rig from 330 every 60, 3 kills; scene 7 = FARM C6 ANIM, 8 = NOANIM). gA / gC / gW / gD = the gameplay-equivalence
# gate scenes (scene 1 = warp.txt, a long window so the run goes on until the 60 s cap / stop marker; scenes 2..14 the
# bench set, unused).
import os, shutil, subprocess, sys
out = sys.argv[1]
MK = '/mnt/c/Game Dev/Emulators/cap16-20261016/py/mkfix.py'
bench = os.path.join(out, 'bench')
subprocess.check_call(['python3', MK, bench, '300', '600', '330', '60', '3'])
R103 = "room 0x103\npos -47609 12 7084\nang 1.889\n"
DOOR = "room 0x103\npos 9470 38 -759\nang 0.8406\n"
gates = {
    'gA': R103 + "inv default\ngod\ncap 6\nmistcut 0\nalivelog 150\nkill 0 150 0x103\nkillrep 8 60\nbench 1 300 5000 GATE A\n",
    'gC': R103 + "inv default\ngod\ncap 6\nmistcut 0\nalivelog 150\nkill 0x28 100 0x103\nkillrep 2 90\nbench 1 300 5000 GATE C\n",
    'gW': R103 + "inv default\ngod\ncap 6\nmistcut 0\nalivelog 150\nkill 0x26 100 0x103\nkillrep 2 90\nbench 1 300 5000 GATE W\n",
    'gD': DOOR + "inv default\ngod\ncap 6\nmistcut 0\nalivelog 150\nact 30 fwd 20\nact 60 a 4\nact 150 a 4\nact 240 a 4\nbench 1 300 5000 GATE D\n",
}
for g, txt in gates.items():
    d = os.path.join(out, g)
    if os.path.exists(d):
        shutil.rmtree(d)
    shutil.copytree(bench, d)
    open(os.path.join(d, 'warp.txt'), 'w', newline='\n').write('name animfar-%s\n' % g + txt)
print('ok', out)
