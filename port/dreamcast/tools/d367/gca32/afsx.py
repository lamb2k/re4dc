"""afsx.py <iso> <out> pattern...: BIO4DAT.AFS entries, non-empty only (first non-empty wins)."""
import fnmatch, os, re, struct, subprocess, sys
iso, out, pats = sys.argv[1], sys.argv[2], sys.argv[3:]
lst = subprocess.run(['isoinfo', '-l', '-i', iso], capture_output=True, text=True).stdout
m = re.search(r'\s(\d+)\s+\[\s*(\d+)\s+\d+\]\s+BIO4DAT\.AFS', lst, re.I)
base = int(m.group(2)) * 2048
with open(iso, 'rb') as f:
    f.seek(base); hdr = f.read(8); n = struct.unpack('<I', hdr[4:8])[0]
    tab = struct.unpack('<%dI' % (2 * n + 2), f.read(8 * n + 8))
    ents = [(tab[2 * i], tab[2 * i + 1]) for i in range(n)]
    noff = tab[2 * n]
    if noff == 0:
        f.seek(base + ents[0][0] - 8); noff = struct.unpack('<I', f.read(4))[0]
    f.seek(base + noff); names = f.read(48 * n)
    os.makedirs(out, exist_ok=True)
    done = set()
    for i, (o, sz) in enumerate(ents):
        nm = names[48 * i:48 * i + 32].split(bytes(1))[0].decode('latin1')
        if sz and nm.lower() not in done and any(fnmatch.fnmatch(nm.lower(), p) for p in pats):
            f.seek(base + o); open(os.path.join(out, nm), 'wb').write(f.read(sz)); done.add(nm.lower())
            print(i, nm, sz)
