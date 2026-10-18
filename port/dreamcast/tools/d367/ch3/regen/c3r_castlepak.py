"""c3r_castlepak.py TOOLS T12D OUTDIR LOOSEMAP.json: replay castle tex chain 10-15:
 c31: t12d + c31 keys (124 kept + 9 restored) -> VQ, restore <29 dB -> tex-c31vq (a158e04b)
 c32: c31vq + c32 keys (100 + 10) -> tex-c32vq (bd2cc3f0)
 c33: c32vq + 4 r206 keys -> vq.pak as is (f1a3433c)
 c33b: c33 + 8 keys -> restore <29 -> tex-c33b (15975911)
LOOSEMAP: {key: path} for loose .re4tex sources."""
import hashlib, json, os, subprocess, sys
T, t12d, O, lm = sys.argv[1:5]
D = T + '/d367'; sys.path[:0] = [D, D + '/vram', T]
import texpack
from vq_pak import read_pak
loose = json.load(open(lm))
kl = lambda f: [l.split()[0] for l in open(f) if l.strip() and not l.startswith('#')]
c31 = kl(D + '/vram/vq16-c31.txt') + '1f706b85-a3a5a27c 45780136-ce6cd0af 5498155d-18d309bd 5faee1db-099f72b1 8ae599ab-81faeb23 8fb3f08f-aa8205df ae7dbfdd-0de5a07d e5209b2b-f15e113b ef071711-6dbe99cb'.split()
c32 = kl(D + '/vram/vq16-c32.txt') + '1f706b85-a3a5a27c 328a61a7-e4983cff 45780136-ce6cd0af 5498155d-18d309bd 5faee1db-099f72b1 67a581c9-a3339122 8fb3f08f-aa8205df 97b79a1a-2c730f73 ae7dbfdd-0de5a07d ef071711-6dbe99cb'.split()
c33 = '18f8a477-36daa0ed bff20ed7-81bf193e cba25b9f-85b58969 d6480ddc-76810580'.split()
c33b = '2270bb80-7e974480 45780136-ce6cd0af 119ec0e0-ea7b99d5 091dc6a0-641ccd27 f8e76302-b983fc64 e80798e0-772ec609 2ba66557-6649a502 2e49209c-cb3151cc'.split()
print('keys', len(c31), len(c32), len(c33), len(c33b))
K = lambda k: tuple(int(x, 16) for x in k.split('-'))
def step(name, base, keys, revert, want):
    W = os.path.join(O, name); os.makedirs(W, exist_ok=True)
    p = dict(base); miss = []; pre = {}
    for k in keys:
        if K(k) not in p:
            if k in loose and loose[k].startswith('VQ:'): pre[K(k)] = open(loose[k][3:], 'rb').read()
            elif k in loose: p[K(k)] = open(loose[k], 'rb').read()
            else: miss.append(k)
    keys = [k for k in keys if K(k) not in pre]
    if miss: print(name, 'MISSING loose', miss); sys.exit(1)
    s, _ = texpack.build(p); open(W + '/src.pak', 'wb').write(s)
    subprocess.run(['python3', D + '/vram/vq_pak.py', W + '/src.pak', W + '/vq.pak', W + '/work'] + keys, check=True, stdout=subprocess.DEVNULL, cwd=D)
    src = read_pak(s); vqp = read_pak(open(W + '/vq.pak', 'rb').read())
    if pre: vqp.update(pre); revert = True
    if revert:
        for e in json.load(open(W + '/work/vq-report.json'))['images']:
            if e['psnr_db'] < 29.0: k = e.get('key') or e.get('name'); vqp[K(k)] = src[K(k)]
        out, _ = texpack.build(vqp)
    else: out = open(W + '/vq.pak', 'rb').read()
    h = hashlib.sha256(out).hexdigest(); open(W + '/out.pak', 'wb').write(out)
    print(name, len(out), h[:8], 'OK' if h.startswith(want) else 'want ' + want); sys.stdout.flush()
    return read_pak(out)
b = read_pak(open(t12d, 'rb').read())
b = step('c31', b, c31, True, 'a158e04b')
b = step('c32', b, c32, True, 'bd2cc3f0')
b = step('c33', b, c33, False, 'f1a3433c')
b = step('c33b', b, c33b, True, '15975911')
