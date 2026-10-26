"""PS2 RE4 ISO -> BIO4DAT.AFS entries (name, iso offset, size). Lane fxproof26."""
import struct, json, os
ISO = '/mnt/c/Users/Public/ps2/DVD/Resident Evil 4 (USA).iso'
CACHE = '/root/work/lanes/fxproof26/afs.json'


def iso_files(f):
    f.seek(16 * 2048)
    pvd = f.read(2048)
    root = pvd[156:156 + 34]
    out = {}

    def walk(lba, size, path):
        f.seek(lba * 2048)
        d = f.read(size)
        i = 0
        while i < len(d):
            l = d[i]
            if l == 0:
                i = (i // 2048 + 1) * 2048
                continue
            elba, esz = struct.unpack_from('<I', d, i + 2)[0], struct.unpack_from('<I', d, i + 10)[0]
            fl = d[i + 25]
            nl = d[i + 32]
            nm = d[i + 33:i + 33 + nl].decode('latin1').split(';')[0]
            if nm not in ('\0', '\1'):
                p = path + '/' + nm
                if fl & 2:
                    walk(elba, esz, p)
                else:
                    out[p] = (elba * 2048, esz)
            i += l
    walk(struct.unpack_from('<I', root, 2)[0], struct.unpack_from('<I', root, 10)[0], '')
    return out


def entries():
    if os.path.exists(CACHE):
        return json.load(open(CACHE))
    with open(ISO, 'rb') as f:
        files = iso_files(f)
        res = {}
        for p, (o, sz) in files.items():
            if not p.upper().endswith('.AFS'):
                continue
            f.seek(o)
            h = f.read(8)
            if h[:3] != b'AFS':
                continue
            n = struct.unpack_from('<I', h, 4)[0]
            tab = f.read(8 * n + 8)
            ents = [struct.unpack_from('<II', tab, 8 * i) for i in range(n)]
            no, ns = struct.unpack_from('<II', tab, 8 * n)
            names = []
            if no:
                f.seek(o + no)
                nt = f.read(ns)
                names = [nt[48 * i:48 * i + 32].rstrip(b'\0').decode('latin1') for i in range(n)]
            for i, (eo, es) in enumerate(ents):
                nm = names[i] if i < len(names) else '%d' % i
                res['%s:%s' % (p.split('/')[-1], nm)] = (o + eo, es)
    json.dump(res, open(CACHE, 'w'))
    return res


def read(name):
    o, s = entries()[name]
    with open(ISO, 'rb') as f:
        f.seek(o)
        return f.read(s)


if __name__ == '__main__':
    e = entries()
    print(len(e))
    import collections
    print(collections.Counter(k.split(':')[0] for k in e))
    print([k for k in e if 'BIO4DAT' in k][:40])
