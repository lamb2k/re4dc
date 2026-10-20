"""fbdiff.py <frames dir A> <frames dir B>: pixel identity of fb0/fb1 (tier 2)."""
import sys
from pathlib import Path
import numpy as np
from PIL import Image
a, b = Path(sys.argv[1]), Path(sys.argv[2])
for n in ('fb0.png', 'fb1.png'):
    x = np.asarray(Image.open(a / n).convert('RGB')).astype(int)
    y = np.asarray(Image.open(b / n).convert('RGB')).astype(int)
    d = np.abs(x - y).sum(2) > 0
    print(n, 'IDENTICAL' if not d.any() else 'DIFF pixels=%d max=%d' % (d.sum(), np.abs(x - y).max()))
