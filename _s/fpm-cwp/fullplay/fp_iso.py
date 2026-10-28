#!/usr/bin/env python3
"""fp_iso.py: ISO9660 reader/patcher for the full-play gate (tools/d367/fullplay).

The release GD-ROM keeps its game tree in track 3: IP.BIN in the 16 system sectors, then an ISO9660 tree whose
directory extents are absolute LBAs (mkgdi.sh: genisoimage -C 0,45000). Tracks are raw 2352-byte MODE1 sectors
(user data at +16) or plain 2048-byte sectors.

  fp_iso.py extract  <track> <outdir> [--lba 45000] [--manifest out.json] [--ipbin IP.BIN]
  fp_iso.py manifest <track> [--lba 45000] -o out.json         (path -> size, sha256 of every file)
  fp_iso.py diff     <a.json> <b.json> [--allow REGEX]...         (exit 1 on a difference not allowed)
  fp_iso.py redirect <track03.iso> <path> <lba> <bytes> [--lba 45000]
        point every directory record of <path> (ISO9660 + Joliet trees) at <lba>/<bytes>, in place (2048 track)

Names come from Rock Ridge NM entries in the primary tree (the Joliet tree is used only by `redirect`).
"""
import hashlib, json, os, re, struct, sys

class Track:
    def __init__(self, path, lba):
        self.f = open(path, 'rb')
        size = os.fstat(self.f.fileno()).st_size
        if size % 2352 == 0 and size % 2048 != 0:
            self.raw = True
        elif size % 2048 == 0 and size % 2352 != 0:
            self.raw = False
        else:  # ambiguous: look for the MODE1 sync pattern
            self.f.seek(0); self.raw = self.f.read(12) == b'\x00' + b'\xff' * 10 + b'\x00'
        self.ss = 2352 if self.raw else 2048
        self.base = lba
        self.count = size // self.ss

    def read(self, lba, n=1):
        out = bytearray()
        for i in range(n):
            rel = lba + i - self.base
            if rel < 0 or rel >= self.count:
                raise ValueError('LBA %d outside the track (base %d, %d sectors)' % (lba + i, self.base, self.count))
            self.f.seek(rel * self.ss + (16 if self.raw else 0))
            out += self.f.read(2048)
        return bytes(out)

    def read_bytes(self, lba, nbytes):
        return self.read(lba, (nbytes + 2047) // 2048)[:nbytes]

def records(data):
    i = 0
    while i < len(data):
        ln = data[i]
        if ln == 0:  # records never cross a sector: skip to the next one
            i = (i // 2048 + 1) * 2048
            continue
        yield i, data[i:i + ln]
        i += ln

def rr_name(rec):
    nl = rec[32]
    su = 33 + nl + (0 if nl % 2 else 1)
    name, j = b'', su
    while j + 4 <= len(rec):
        sig, ln = rec[j:j + 2], rec[j + 2]
        if ln < 4:
            break
        if sig == b'NM':
            name += rec[j + 5:j + ln]
        j += ln
    # raw bytes as the file system sees them (one disc name is Shift-JIS): fsdecode keeps them byte-exact
    return os.fsdecode(name) if name else None

def walk(tr, root_rec, joliet=False):
    """yield (path, extent, size, is_dir, dir_lba, offset_in_dir) for every entry below root_rec."""
    stack = [('', struct.unpack_from('<I', root_rec, 2)[0], struct.unpack_from('<I', root_rec, 10)[0])]
    seen = set()
    while stack:
        prefix, ext, size = stack.pop()
        if ext in seen:
            continue
        seen.add(ext)
        data = tr.read(ext, (size + 2047) // 2048)
        for off, rec in records(data[:size]):
            nl = rec[32]
            raw = rec[33:33 + nl]
            if raw in (b'\x00', b'\x01'):
                continue
            if joliet:
                name = raw.decode('utf-16-be')
            else:
                name = rr_name(rec) or os.fsdecode(raw)
            name = name.split(';')[0]
            if not joliet and name.endswith('.') and rr_name(rec) is None:
                name = name[:-1]
            e, s, fl = struct.unpack_from('<I', rec, 2)[0], struct.unpack_from('<I', rec, 10)[0], rec[25]
            path = prefix + '/' + name
            isdir = bool(fl & 2)
            yield path, e, s, isdir, ext, off
            if isdir:
                stack.append((path, e, s))

def volume_roots(tr):
    pvd = svd = None
    lba = tr.base + 16
    while True:
        d = tr.read(lba)
        t = d[0]
        if d[1:6] != b'CD001':
            raise ValueError('no volume descriptor at LBA %d' % lba)
        if t == 1 and pvd is None:
            pvd = d
        elif t == 2 and d[88:91] in (b'%/@', b'%/C', b'%/E'):
            svd = d
        elif t == 255:
            break
        lba += 1
    return pvd[156:190], (svd[156:190] if svd else None)

def files(tr):
    root, _ = volume_roots(tr)
    return [(p, e, s) for p, e, s, isdir, _, _ in walk(tr, root) if not isdir]

def sha(b):
    return hashlib.sha256(b).hexdigest()

def cmd_extract(a):
    tr = Track(a.track, a.lba)
    man = {}
    for p, e, s in sorted(files(tr)):
        b = tr.read_bytes(e, s) if s else b''
        man[p.lstrip('/')] = dict(size=s, sha256=sha(b))
        if a.outdir:
            dst = os.path.join(a.outdir, p.lstrip('/'))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, 'wb') as f:
                f.write(b)
    if a.ipbin:
        with open(a.ipbin, 'wb') as f:
            f.write(tr.read(tr.base, 16))
    if a.manifest:
        with open(a.manifest, 'w') as f:
            json.dump(man, f, indent=0, sort_keys=True)
    print('files %d bytes %d' % (len(man), sum(v['size'] for v in man.values())))

def cmd_diff(a):
    x, y = json.load(open(a.a)), json.load(open(a.b))
    allow = [re.compile(r) for r in a.allow]
    bad = []
    rows = []
    for k in sorted(set(x) | set(y)):
        if x.get(k) == y.get(k):
            continue
        kind = 'only-a' if k not in y else 'only-b' if k not in x else 'differs'
        ok = any(r.fullmatch(k) for r in allow)
        rows.append('%s %s %s' % ('allowed' if ok else 'DIFF', kind, k))
        if not ok:
            bad.append(k)
    for r in rows:
        print(r)
    same = sum(1 for k in set(x) & set(y) if x[k] == y[k])
    print('identical %d, differing %d (not allowed %d)' % (same, len(rows), len(bad)))
    sys.exit(1 if bad else 0)

def cmd_redirect(a):
    tr = Track(a.track, a.lba)
    assert not tr.raw, 'redirect works on a 2048-byte track'
    pvd_root, svd_root = volume_roots(tr)
    hits = 0
    for root, joliet in ((pvd_root, False), (svd_root, True)):
        if root is None:
            continue
        for p, e, s, isdir, dlba, off in walk(tr, root, joliet):
            if p.lower() != a.path.lower():
                continue
            pos = (dlba - tr.base) * 2048 + off
            with open(a.track, 'r+b') as f:
                f.seek(pos + 2); f.write(struct.pack('<I', a.to) + struct.pack('>I', a.to))
                f.seek(pos + 10); f.write(struct.pack('<I', a.bytes) + struct.pack('>I', a.bytes))
            hits += 1
            print('redirect %s %s: extent %d -> %d, size %d -> %d' % ('joliet' if joliet else 'iso9660', p, e, a.to, s, a.bytes))
    if hits == 0:
        sys.exit('redirect: %s not found' % a.path)

if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest='cmd', required=True)
    e = sp.add_parser('extract'); e.add_argument('track'); e.add_argument('outdir', nargs='?')
    e.add_argument('--lba', type=int, default=45000); e.add_argument('--manifest'); e.add_argument('--ipbin')
    m = sp.add_parser('manifest'); m.add_argument('track'); m.add_argument('--lba', type=int, default=45000)
    m.add_argument('-o', dest='manifest', required=True)
    d = sp.add_parser('diff'); d.add_argument('a'); d.add_argument('b'); d.add_argument('--allow', action='append', default=[])
    r = sp.add_parser('redirect'); r.add_argument('track'); r.add_argument('path'); r.add_argument('to', type=int)
    r.add_argument('bytes', type=int); r.add_argument('--lba', type=int, default=45000)
    a = ap.parse_args()
    if a.cmd == 'extract':
        cmd_extract(a)
    elif a.cmd == 'manifest':
        a.outdir = None; a.ipbin = None; cmd_extract(a)
    elif a.cmd == 'diff':
        cmd_diff(a)
    else:
        cmd_redirect(a)
