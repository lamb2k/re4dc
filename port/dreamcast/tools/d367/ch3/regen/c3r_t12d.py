"""c3r_t12d.py TOOLS T121PAK NEWTEXDIR OUT: tex-t12d.pak = tex-t121.pak (b097d061) minus the blackps2/newtex keys
(t12dark h6: 'tex-t12d.pak + 293 new keys, no key changed'), rebuilt with texpack.build; also via tex_wrapsafe."""
import hashlib, os, struct, subprocess, sys
T, src, nt, out = sys.argv[1:5]
sys.path[:0] = [T + '/d367', T + '/d367/vram', T]
import texpack
from vq_pak import read_pak
p = read_pak(open(src, 'rb').read())
newk = set()
for f in os.listdir(nt):
    if f.endswith('.re4tex'): newk.add(tuple(int(x, 16) for x in f[:-7].split('-')))
print('t121 entries', len(p), 'newtex keys', len(newk), 'in pak', len(newk & set(p)))
q = {k: v for k, v in p.items() if k not in newk}
b, _ = texpack.build(q); texpack.verify(b); open(out, 'wb').write(b)
print('build', len(b), hashlib.sha256(b).hexdigest()[:16])
hdr = open(src, 'rb').read(64)
print('t121 header', struct.unpack_from('<8s5I', hdr, 0))
print('t12d header', struct.unpack_from('<8s5I', b, 0))
