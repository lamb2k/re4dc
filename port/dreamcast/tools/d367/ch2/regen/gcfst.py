import struct, sys
p = sys.argv[1]; pat = sys.argv[2:]
f = open(p, 'rb')
f.seek(0x424); fst_off, fst_sz = struct.unpack('>II', f.read(8))
f.seek(fst_off); fst = f.read(fst_sz)
n = struct.unpack('>I', fst[8:12])[0]
strs = fst[n * 12:]
def name(o): return strs[o:strs.index(b'\0', o)].decode('latin1')
paths = {}; stack = [(0, n, '')]
i = 1
dirs = [('', n)]
def walk(start, end, prefix):
    i = start
    while i < end:
        w0, a, b = struct.unpack('>III', fst[i*12:i*12+12])
        nm = name(w0 & 0xffffff)
        if w0 >> 24:
            walk(i + 1, b, prefix + nm + '/'); i = b
        else:
            paths[prefix + nm] = (a, b); i += 1
walk(1, n, '')
print('files', len(paths))
for k, v in sorted(paths.items()):
    if any(x.lower() in k.lower() for x in pat):
        print(k, v[1])
