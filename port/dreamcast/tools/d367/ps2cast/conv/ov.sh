# per-room disc overlays (master.sh layout): dc/native/rXXX/registry.re4nmr + the textures that room's package names
# (+ the ARGB4444 pair packages of its masked sections)
W=/root/probe/lanes-20261014/ps2cast/work/conv
python3 - <<'P'
import os, struct, shutil, glob, json
W = '/root/probe/lanes-20261014/ps2cast/work/conv'
PAIRS = {'bat-em29-00': [W + '/mask-bat-em29-00'], 'fish-em27-00': [W + '/mask-fish-em27-00'],
         'merchant13-c0': ['/root/probe/codex-ch23-enemies-20261013/models/merchant13-c0-mask-robe', '/root/probe/codex-ch23-enemies-20261013/models/merchant13-c0-mask-cloth'],
         'merchant13-o0': ['/root/probe/codex-ch23-enemies-20261013/models/merchant13-o0-mask-robe', '/root/probe/codex-ch23-enemies-20261013/models/merchant13-o0-mask-cloth']}
for d in sorted(glob.glob(W + '/reg-*-ch1*')):
    if d.endswith('.log') or 'reg-all' in d: continue
    m = json.load(open(d + '/registry-manifest.json')); rp = m['room_package']; room = rp['disc_path'].split('/')[2]
    o = W + '/ov-' + room; shutil.rmtree(o, ignore_errors=True); os.makedirs(o + '/dc/native/' + room)
    shutil.copy2(d + '/' + rp['path'], o + '/dc/native/' + room + '/registry.re4nmr')
    pk = open(d + '/' + rp['path'], 'rb').read(); off, n, cnt = struct.unpack_from('<3I', pk, 64 + 16 * 4 + 4)
    keys = ['%08x-%08x' % struct.unpack_from('<2I', pk, off + 16 * t) for t in range(cnt)]
    files = [d + '/tex/' + k + '.re4tex' for k in keys if os.path.exists(d + '/tex/' + k + '.re4tex')]
    for desc in rp['descriptors']:
        for md in PAIRS.get(desc['name'], []):
            files += [f for f in glob.glob(md + '/*.re4tex')]
    for f in sorted(set(files)):
        k = os.path.basename(f); os.makedirs(o + '/dc/tex/' + k[0], exist_ok=True); shutil.copy2(f, o + '/dc/tex/' + k[0] + '/' + k)
    print(room, sorted(os.path.relpath(x, o) for x in glob.glob(o + '/**/*.*', recursive=True)))
P
