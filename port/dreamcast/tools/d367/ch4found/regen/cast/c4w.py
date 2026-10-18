"""ch4regen copy of /c/tmp/ch4/cast/c4w.py (ch4found16 10-17): ps2_cast.py with armor-em3c-00w / -02w presets.
Tree = the rebuilt ch4found lane tree (real path; Windows python cannot follow the lanes-20261016/ch4found symlink)."""
import sys
T = '//wsl.localhost/Ubuntu-24.04/root/probe/lanes-20261018/ch4regen/tree/port/dreamcast/tools'
sys.path.insert(0, T)
import ps2_cast as pc  # noqa: E402

for _n, _q in (('armor-em3c-00', 'armor-em3c-00w'), ('armor-em3c-02', 'armor-em3c-02w')):
    pc.PRESETS[_q] = dict(pc.PRESETS[_n], sections=pc.PRESETS[_n]['sections'] + [(0xc, 'weapon-a', 0xd), (0xe, 'weapon-b', 0xf)])
sys.argv = ['ps2_cast.py'] + sys.argv[1:]
sys.exit(pc.main())
