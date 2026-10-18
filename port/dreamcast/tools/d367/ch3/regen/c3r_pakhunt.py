"""c3r_pakhunt.py TOOLS OUTDIR PAK...: find wanted (key, sha) entries inside paks; write hits to OUTDIR/<key>.re4tex"""
import hashlib, os, sys
T, O = sys.argv[1:3]; sys.path[:0] = [T + '/d367', T + '/d367/vram', T]
from vq_pak import read_pak
want = {(0x628a66ab, 0x711d6b46): '3b1ce03f', (0x8479815d, 0x291af55c): '727032c3', (0xae7dbfdd, 0x0de5a07d): '857db02d'}
os.makedirs(O, exist_ok=True)
for pk in sys.argv[3:]:
    p = read_pak(open(pk, 'rb').read())
    for k, s in want.items():
        if k in p:
            h = hashlib.sha256(p[k]).hexdigest()
            print(os.path.basename(pk), '%08x-%08x' % k, h[:8], 'HIT' if h.startswith(s) else '')
            if h.startswith(s): open(os.path.join(O, '%08x-%08x.re4tex' % k), 'wb').write(p[k])
