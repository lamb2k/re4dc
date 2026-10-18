"""c3r_castlefill.py TOOLS TEXC34 HUNTDIR LOOSEMAP: add ae7dbfdd (16-bit source, from tex-c34) and the VQ'd entries of
628a66ab / 8479815d (from tex-c34; their 16-bit sources are lost) as 'VQ:' entries to the loose map. SUBSTITUTE: the
final sha decides whether tex-c34's VQ bytes equal castle c31's."""
import hashlib, json, os, sys
T, pk, H, lm = sys.argv[1:5]; pk2 = sys.argv[5]; sys.path[:0] = [T + '/d367', T + '/d367/vram', T]
from vq_pak import read_pak
p = read_pak(open(pk2, 'rb').read()); p.update({k: v for k, v in read_pak(open(pk, 'rb').read()).items()}); m = json.load(open(lm))
m['ae7dbfdd-0de5a07d'] = H + '/ae7dbfdd-0de5a07d.re4tex'
m['8479815d-291af55c'] = H + '/8479815d-291af55c.re4tex'  # 16-bit source 727032c3 from bfc-r209-final
P = '/mnt/c/Game Dev/Emulators/re4-assets-private/payload-t164-20261018/tree/dc/tex/'
for k in ['235002b4-f139d9b1', '41387140-38190dc7', '7a0e9581-c9525524', 'ec263da4-b1dfb0a2']: m[k] = P + k[0] + '/' + k + '.re4tex'
m['67a581c9-a3339122'] = H + '/67a581c9-a3339122.re4tex'  # bfc-r209-final disc
for k in ['628a66ab-711d6b46']:
    kk = tuple(int(x, 16) for x in k.split('-')); f = H + '/vq-' + k + '.re4tex'
    open(f, 'wb').write(p[kk]); m[k] = 'VQ:' + f; print(k, hashlib.sha256(p[kk]).hexdigest()[:8], len(p[kk]))
json.dump(m, open(lm, 'w'), indent=0)
