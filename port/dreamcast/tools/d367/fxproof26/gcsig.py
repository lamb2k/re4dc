"""GameCube effect pictures (every EFF/etc-eff TPL of the given room archives) -> signatures. Lane fxproof26.

  gcsig.py <out prefix> st1/r100 st1/r101 ...   writes <out>.sig + <out>.tsv (key ctx w h)
"""
import sys
from pathlib import Path
sys.path.insert(0, '/root/work/lanes/fxproof26')
T = '/root/work/lanes/fxproof26/wt/port/dreamcast/tools'
sys.path[:0] = [T, T + '/d367/vram', T + '/d367/test12fx']
import fx_ps2_sheet as SH  # noqa
from assetpipe.rooms import GcIso  # noqa
import sigs  # noqa
ISO = '/root/work/re4-dreamcast/orig/G4BE08/re4_debug_disc1.iso'
WORK = Path('/root/work/lanes/fxproof26/gc')


def main(out, rooms):
    WORK.mkdir(exist_ok=True)
    g = GcIso(ISO)
    fs, ft = open(out + '.sig', 'wb'), open(out + '.tsv', 'w')
    for r in rooms:
        rel = r.lower() + '.das'
        p = WORK / Path(rel).name
        if not p.exists():
            p.write_bytes(g.read(g.find(rel) or rel))
        pics = SH.gc_pictures([(rel, p)])
        for ctx, l in sorted(pics.items()):
            for key, w, h, px in l:
                fs.write(sigs.sig_rgba(w, h, px))
                ft.write('%s\t%s\t%d\t%d\n' % (key, ctx, w, h))
        print(r, len(pics))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2:])
