"""ext.py <track03.bin 2352> <outdir> name...: extract files (by ISO path, case-insensitive) from a raw GD data track."""
import struct, sys, os
TB = 45000
f = open(sys.argv[1], 'rb')
def sec(lba):
    f.seek((lba - TB) * 2352 + 16); return f.read(2048)
pvd = sec(TB + 16) if sec(TB + 16)[1:6] == b'CD001' else None
if pvd is None:
    pvd = sec(16 + TB)
root = pvd[156:190]
files = {}
def walk(lba, size, pre):
    data = b''.join(sec(lba + i) for i in range((size + 2047) // 2048))
    i = 0
    while i < len(data):
        ln = data[i]
        if ln == 0:
            i = (i // 2048 + 1) * 2048; continue
        r = data[i:i + ln]; i += ln
        el = struct.unpack('<I', r[2:6])[0]; es = struct.unpack('<I', r[10:14])[0]
        nm = r[33:33 + r[32]]
        if nm in (b'\0', b'\1'): continue
        nm = nm.decode().split(';')[0]
        if r[25] & 2: walk(el, es, pre + nm + '/')
        else: files[(pre + nm).upper()] = (el, es)
walk(struct.unpack('<I', root[2:6])[0], struct.unpack('<I', root[10:14])[0], '')
os.makedirs(sys.argv[2], exist_ok=True)
for n in sys.argv[3:]:
    el, es = files[n.upper()]
    d = b''.join(sec(el + i) for i in range((es + 2047) // 2048))[:es]
    open(os.path.join(sys.argv[2], n.replace('/', '_')), 'wb').write(d)
    print(n, el, es)
