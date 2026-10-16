import json, sys, subprocess, pathlib
sys.path.insert(0, '/root/probe/lanes-20261015/castle/tree/port/dreamcast/tools/d367')
sys.path.insert(0, '/root/probe/lanes-20261015/castle/tree/port/dreamcast/tools/d367/vram')
import texpack
from vq_pak import read_pak
L = pathlib.Path('/root/probe/lanes-20261015/castle')
FIX = json.load(open(L / 'fix/castle-t12b.json'))['replace']
pkgs = read_pak(open(FIX['dc/tex.pak'], 'rb').read())
keys = (L / 'vq-c31-keys.txt').read_text().split()
added = 0
for k in keys:
    kk = tuple(int(x, 16) for x in k.split('-'))
    if kk not in pkgs:
        pkgs[kk] = open(FIX['dc/tex/%s/%s.re4tex' % (k[0], k)], 'rb').read(); added += 1
W = L / 'vq-c31'; W.mkdir(exist_ok=True)
out, _ = texpack.build(pkgs); texpack.verify(out)
(W / 'src.pak').write_bytes(out)
print('src pak', len(pkgs), 'packages, loose added', added)
