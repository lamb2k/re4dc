"""c3r_paksrc.py TOOLSDIR OUTPAK KEYFILE SEARCHDIR...: build a src tex.pak of the 16-bit source packages for KEYFILE's keys,
found as <key>.re4tex under SEARCHDIRs (first hit wins, files that are already VQ are skipped)."""
import os, sys
tools, outp, keyfile = sys.argv[1:4]
sys.path[:0] = [tools, tools + '/d367', tools + '/d367/vram']
import texpack, vq_native_ui as vq
keys = open(keyfile).read().split()
idx = {}
for d in sys.argv[4:]:
    for root, _, fs in os.walk(d):
        for f in fs:
            if f.endswith('.re4tex'):
                k = f[:-7]
                if k in keys and k not in idx:
                    b = open(os.path.join(root, f), 'rb').read()
                    try:
                        w, h, fmt, flags, extra = vq.read_package(b)
                    except Exception:
                        continue
                    idx[k] = b
pk = {tuple(int(x, 16) for x in k.split('-')): b for k, b in idx.items()}
out, _ = texpack.build(pk); texpack.verify(out); open(outp, 'wb').write(out)
miss = [k for k in keys if k not in idx]
open(outp + '.keys', 'w').write('\n'.join(sorted(idx)) + '\n')
print('found', len(idx), 'of', len(keys), 'missing', miss[:20])
