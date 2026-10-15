"""stilldiff.py <ref run> <test run>... : the newest frozen still of each run (shots/t*/frames/fb0.png, not the blue crash
screen) against the ref: differing pixels, max / mean channel delta, and a diff image (strict/still-<ref>-<test>.png)."""
import sys, glob, os
import numpy as np
from PIL import Image
E = 'D:/Flycast-Evidence/re4-dreamcast/sh4zam-20261015'

def still(run):
    for d in sorted(glob.glob(f'{E}/{run}/capture/shots/t*'))[::-1]:
        p = d + '/frames/fb0.png'
        if not os.path.exists(p):
            continue
        a = np.asarray(Image.open(p).convert('RGB'), np.int16)
        m = a.reshape(-1, 3).mean(0)
        if m[2] <= m[0] + 30:
            return p, a
    return None, None

rp, ra = still(sys.argv[1])
print('ref', rp)
for t in sys.argv[2:]:
    tp, ta = still(t)
    if ta is None or ta.shape != ra.shape:
        print(t, 'no comparable still', tp); continue
    d = np.abs(ta - ra)
    px = (d.max(2) > 0)
    n = int(px.sum())
    print(f'{t}: {os.path.basename(os.path.dirname(os.path.dirname(tp)))} px differ {n} of {px.size} ({100*n/px.size:.3f}%), '
          f'max delta {int(d.max())}, mean delta over all px {d.mean():.4f}, mean over differing px {d.max(2)[px].mean() if n else 0:.2f}, '
          f'px > 8 levels {int((d.max(2) > 8).sum())}')
    vis = np.clip(d.max(2) * 8, 0, 255).astype(np.uint8)
    os.makedirs(f'{E}/strict', exist_ok=True)
    Image.fromarray(vis).save(f'{E}/strict/still-{sys.argv[1]}-{t}.png')
    side = np.concatenate([ra, ta], 1).astype(np.uint8)
    Image.fromarray(side).save(f'{E}/strict/pair-{sys.argv[1]}-{t}.png')
