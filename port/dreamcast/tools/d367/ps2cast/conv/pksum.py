import json, glob, os, struct
W = '/root/probe/lanes-20261014/ps2cast/work/conv'
REL = '/root/probe/lanes-20261014/fullplay/work/rel-36cb116398e91c40/tree/dc/native'
for d in sorted(glob.glob(W + '/reg-*-ch1*')):
    if d.endswith('.log') or 'reg-all' in d: continue
    m = json.load(open(d + '/registry-manifest.json')); rp = m['room_package']; c = rp['counts']
    room = rp['room'].lower().lstrip('0')
    old = REL + '/r%s/registry.re4nmr' % room
    oarena = None
    if os.path.exists(old):
        b = open(old, 'rb').read(); sz, skin = struct.unpack_from('<I', b, 16)[0], struct.unpack_from('<I', b, 28)[0]; oarena = ((sz + 31) & ~31) + skin
    pk = open(d + '/package/r%s/registry.re4nmr' % rp['room'].lower()[1:] if rp['room'].startswith('0') else '', 'rb').read()
    off, n, cnt = struct.unpack_from('<3I', pk, 64 + 16 * 4 + 4)
    keys = ['%08x-%08x' % struct.unpack_from('<2I', pk, off + 16 * t) for t in range(cnt)]
    tex, vram = [], 0
    for k in keys:
        x = d + '/tex/' + k + '.re4tex'
        if not os.path.exists(x): tex.append(k + '(token)'); continue
        b = open(x, 'rb').read(); toff = struct.unpack_from('<8s10I', b, 0)[5]; v = struct.unpack_from('<64s8I', b, toff)[5]; vram += v; tex.append('%s:%d' % (k, v))
    print('%s %s bytes=%d arena=%d (release arena %s) desc=%d fpart=%d ftex=%d role=%d sblob=%d max_bones? tex=%d vram=%d sha=%s %s' % (
        os.path.basename(d), rp['room'], rp['bytes'], rp['arena'], oarena, c['desc'], c['fpart'], c['ftex'], c['role'], c['sblob'], len(tex), vram, rp['sha256'][:16], ' '.join(tex)))
