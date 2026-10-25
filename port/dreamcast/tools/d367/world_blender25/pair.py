# world-blender25: tier-2 pixel diff of frozen Flycast stills (last good shot of each run). usage: pair.py <evdir> <ref run> <arm run>...
import glob, os, sys
import numpy as np
from PIL import Image
E = sys.argv[1]
def still(run):
    for d in sorted(glob.glob(f'{E}/{run}/shots/t*'))[::-1]:
        p = d + '/frames/fb0.png'
        if os.path.exists(p):
            return p, np.asarray(Image.open(p).convert('RGB'), np.int16)
    raise SystemExit('no still for ' + run)
rp, ra = still(sys.argv[2])
for run in sys.argv[3:]:
    tp, ta = still(run)
    d = np.abs(ta - ra); m = d.max(2); n = int((m > 0).sum())
    print(f'{run} vs {sys.argv[2]}: px differ {n} ({100*n/m.size:.2f}%), >8 levels {int((m > 8).sum())} '
          f'({100*(m > 8).sum()/m.size:.2f}%), >32 {int((m > 32).sum())} ({100*(m > 32).sum()/m.size:.2f}%), max {int(d.max())}')
    vis = np.clip(m * 8, 0, 255).astype(np.uint8)
    Image.fromarray(np.concatenate([ra.astype(np.uint8), ta.astype(np.uint8), np.stack([vis]*3, 2)], 1)).save(
        f'{E}/hotspot/flycast-pair-{sys.argv[2]}-vs-{run}.png')
    Image.fromarray(ta.astype(np.uint8)).save(f'{E}/hotspot/flycast-{run}.png')
Image.fromarray(ra.astype(np.uint8)).save(f'{E}/hotspot/flycast-{sys.argv[2]}.png')
