"""c3g_ps2esl.py ISO OUTDIR: extract emleon0N.esl from PS2 BIO4DAT AFS (LBA 446273) as OUTDIR/ps2_emleon0N.esl."""
import os, struct, sys
iso, out = sys.argv[1], sys.argv[2]
f = open(iso, 'rb'); base = 446273 * 2048
f.seek(base); h = f.read(8); assert h[:4] == b'AFS\0', h
n = struct.unpack('<I', h[4:])[0]
tab = f.read(8 * n + 8)
ents = [struct.unpack('<II', tab[i * 8:i * 8 + 8]) for i in range(n)]
no, ns = struct.unpack('<II', tab[8 * n:8 * n + 8])
if no == 0:
    f.seek(base + ents[0][0] - 8); no, ns = struct.unpack('<II', f.read(8))
f.seek(base + no); nt = f.read(ns)
os.makedirs(out, exist_ok=True)
for i, (o, s) in enumerate(ents):
    nm = nt[i * 48:i * 48 + 32].split(b'\0')[0].decode('latin1').lower()
    if nm.startswith('emleon') and nm.endswith('.esl'):
        f.seek(base + o); d = f.read(s)
        open(os.path.join(out, 'ps2_' + nm), 'wb').write(d); print('ok', nm, s)
