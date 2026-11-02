"""fx.py <unarmed.json> --prep <prepared em31 dir> [--movies r332s00,r332s10,...] [--no-reg] [--no-gctex]
lane final16: Saddler's data on an r332 fixture: em/em31.drs (+ dc/mot/*.fcv when streamed), em31's GC model textures
loose (dc/tex/<c>/<key>.re4tex, the stress16b tex-em31 set; skipped with --no-gctex), the r332 registry package
(dc/native/r332/registry.re4nmr) and its two PS2 VQ atlases, and the chosen route movies (st3 lane 288x192 .seq)."""
import json, os, sys, glob
a = sys.argv[1:]
f = a[0]
opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d
L = '/root/probe/lanes-20261016/final16'
prep = opt('--prep')
movies = [m for m in (opt('--movies', '') or '').split(',') if m]
d = json.load(open(f)); r = d['replace']
for k in [k for k in r if k.startswith('dc/mot/') and 'em31' in os.path.basename(r[k])]:
    del r[k]
r['em/em31.drs'] = '%s/em31.drs' % prep
nm = 0
if os.path.isdir(prep + '/mot'):
    for m in sorted(os.listdir(prep + '/mot')):
        r['dc/mot/' + m] = prep + '/mot/' + m; nm += 1
nt = 0
if '--no-gctex' not in a:
    for t in sorted(glob.glob(L + '/prepem/tex-em31/*.re4tex')):
        b = os.path.basename(t); r['dc/tex/%s/%s' % (b[0], b)] = t; nt += 1
nr = 0
if '--no-reg' not in a:
    r['dc/native/r332/registry.re4nmr'] = L + '/reg/reg-r332/package/r332/registry.re4nmr'
    for t in sorted(glob.glob(L + '/reg/reg-r332/tex/*.re4tex')):
        b = os.path.basename(t); r['dc/tex/%s/%s' % (b[0], b)] = t; nr += 1
M = '/root/probe/lanes-20261014/st3/movies/movies-288x192-full'
for k in [k for k in r if k.startswith('dc/movie/r33')]:
    del r[k]
for m in movies:
    r['dc/movie/%s.seq' % m] = '%s/%s/%s.seq' % (M, m, m)
for k, v in r.items():
    assert os.path.exists(v), (k, v)
d['remove'] = [x for x in d.get('remove', []) if x not in r]
d['provenance'].setdefault('final16', {}).update(prep=prep, movies=movies, gctex=nt, reg_tex=nr, mot=nm)
json.dump(d, open(f, 'w'), indent=1, sort_keys=True)
print('fx', os.path.basename(f), 'mot', nm, 'gctex', nt, 'regtex', nr, 'movies', movies)
