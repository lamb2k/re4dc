"""c3r_loosemap.py LANE OUT.json: key -> WSL path of verified loose 16-bit textures for LANE (my replay + harvest)."""
import json, os, sys
S = os.path.dirname(os.path.abspath(__file__))
lane, outp = sys.argv[1], sys.argv[2]
L = json.load(open(os.path.join(S, 'missing.json'))); f = json.load(open(os.path.join(S, 'cover.json')))
UNC = '\\\\wsl.localhost\\Ubuntu-24.04'
def wsl(p):
    q = p.replace('\\', '/')
    if q.startswith('//wsl.localhost/Ubuntu-24.04'): return q[len('//wsl.localhost/Ubuntu-24.04'):]
    if p[1:3] == ':\\': return '/mnt/' + p[0].lower() + p[2:].replace('\\', '/')
    return p
lm = {}
for p in L[lane]:
    k = lane + '|' + p
    if p.startswith('dc/tex/') and k in f: lm[p.split('/')[-1][:-7]] = wsl(f[k][0])
H = os.path.join(r'C:\Game Dev\Emulators\re4-assets-private\harvest18-20261018', lane, 'dc', 'tex')
for root, _, fs in os.walk(H):
    for x in fs:
        if x.endswith('.re4tex') and x[:-7] not in lm: lm[x[:-7]] = wsl(os.path.join(root, x))
json.dump(lm, open(outp, 'w')); print(len(lm))
