import json, sys, pathlib, hashlib
sys.path.insert(0, '/root/probe/lanes-20261015/castle/tree/port/dreamcast/tools/d367')
sys.path.insert(0, '/root/probe/lanes-20261015/castle/tree/port/dreamcast/tools/d367/vram')
import texpack
from vq_pak import read_pak
W = pathlib.Path('/root/probe/lanes-20261015/castle/vq-c31')
src = read_pak((W / 'src.pak').read_bytes()); vqp = read_pak((W / 'vq.pak').read_bytes())
r = json.load(open(W / 'work/vq-report.json'))
low = [e for e in r['images'] if e['psnr_db'] < 29.0]
name = lambda e: e.get('key') or e.get('name')
for e in low:
    kk = tuple(int(x, 16) for x in name(e).split('-')); vqp[kk] = src[kk]
kept = [e for e in r['images'] if e['psnr_db'] >= 29.0]
out, _ = texpack.build(vqp); texpack.verify(out)
(W / 'tex-c31vq.pak').write_bytes(out)
(W / 'vq-c31-final-keys.txt').write_text('\n'.join(sorted(name(e) for e in kept)) + '\n')
print('VQ kept', len(kept), 'restored', len(low), 'before', sum(e['before_vram'] for e in kept), 'after', sum(e['after_vram'] for e in kept))
print('pak', len(out), hashlib.sha256(out).hexdigest())
