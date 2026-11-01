#!/usr/bin/env python3
"""swap-program.py: put a freshly built game program into a published RE4DC GDEMU test disc.

    swap-program.py <release> <program> <outdir> [--replace DISC/PATH=FILE ...] [--add DISC/PATH=FILE ...]

<release>  a published GDEMU test zip (RE4DC-...-GDEMU.zip, with gdemu/disc.gdi and three tracks)
           or a directory holding disc.gdi and its tracks (an extracted gdemu folder).
<program>  the build output directory (build-public.sh OUT, or any build with re4dc-game.elf and the
           *.ovl overlays beside it), or a single re4dc-game.elf / 1ST_READ.BIN.
<outdir>   receives disc.gdi, track01 and track02 (copied unchanged), a new track03 and SHA256SUMS.txt.

What it writes, the way the release packaging (tools/d367/mkgdi.sh) does:
  * 1ST_READ.BIN = the ELF as a raw binary (sh-elf-objcopy -R .stack -O binary). It is NOT
    scrambled: the boot ROM descrambles only on a CD-R (MIL-CD) disc, never on a GD-ROM.
  * The program's overlays (pl0f.ovl, em2f.ovl, sscrn.ovl ...) go to /dc/<name>.ovl. They are linked
    against this ELF's addresses, so a program without its own overlays would crash in those rooms.

The disc layout is read from the image:
  standard  the release image from test 16 on: the standard GD-ROM layout that mkdcdisc writes
            (CONTRIBUTING-PORT.md section 8). Track 3 runs to LBA 549150, the end of a real GD-ROM; the
            files sit at the outer end of the disc and 1ST_READ.BIN is the last file, 150 sectors before
            the end. The track keeps its length, so IP.BIN (with its TOC1), the volume descriptors and the
            path tables are not touched. The new 1ST_READ.BIN ends where the old one ended, so it stays the
            last file; when it is longer, the files it would cover move into the free (zero) area in front
            of the first file. Any other file that grew moves there too; a file that still fits its sectors
            is rewritten in place. Sectors no file uses any more are zeroed, as mkdcdisc leaves them.
  legacy    the images of earlier releases (track 3 ends with its last file): a file that grew is appended
            after the end of track 3 and the volume size grows with it.
Only the changed files' directory records (extent and size, in the ISO9660, Rock Ridge and Joliet trees)
are rewritten. Changed sectors of a raw 2,352-byte track get fresh MODE1 headers and EDC/ECC, so GDEMU and
Flycast read the result as any other GDI. A new file (--add) gets a directory record in each tree (with a
Rock Ridge name when the disc has them). Afterwards the new track 3 is read back: every swapped file must
read back byte for byte, every file must lie inside the track with no overlaps and, on a standard disc,
1ST_READ.BIN must still be the last file at the same end. Then check the image with
    python3 port/dreamcast/tools/d367/disc_lint.py <outdir>/disc.gdi
Only the Python standard library is needed (plus sh-elf-objcopy when given an ELF).
"""
import argparse, hashlib, os, shutil, struct, subprocess, sys, zipfile
from pathlib import Path

RAW, USER = 2352, 2048
HD_LBA = 45000
HD_END = 549150  # end of the GD-ROM high-density area (LBA)


def die(msg):
    sys.exit('swap-program: ' + msg)


def nsec(size):
    return (size + USER - 1) // USER


# ---- MODE1 sector EDC/ECC (ECMA-130), as tools/d367/mode1raw.c --------------------------------
EDC = []
for i in range(256):
    e = i
    for _ in range(8):
        e = (e >> 1) ^ (0xD8018001 if e & 1 else 0)
    EDC.append(e)
F_LUT = [((i << 1) ^ (0x11D if i & 0x80 else 0)) & 0xFF for i in range(256)]
B_LUT = [0] * 256
for i in range(256):
    B_LUT[i ^ F_LUT[i]] = i


def edc(buf):
    e = 0
    for b in buf:
        e = (e >> 8) ^ EDC[(e ^ b) & 0xFF]
    return e


def ecc_block(s, major_count, minor_count, major_mult, minor_inc, dest):
    size = major_count * minor_count
    for major in range(major_count):
        index = (major >> 1) * major_mult + (major & 1)
        a = b = 0
        for _ in range(minor_count):
            t = s[0xC + index]
            index += minor_inc
            if index >= size:
                index -= size
            a ^= t
            b ^= t
            a = F_LUT[a]
        a = B_LUT[F_LUT[a] ^ b]
        s[dest + major] = a
        s[dest + major + major_count] = a ^ b


def bcd(v):
    # minutes past 99 (the high-density area runs to minute 122) keep the tens<<4 | units form, as mkdcdisc
    return ((v // 10) << 4) | (v % 10)


def mode1_sector(lba, data):
    assert len(data) == USER
    s = bytearray(RAW)
    s[0:12] = b'\x00' + b'\xff' * 10 + b'\x00'
    a = lba + 150
    s[12:16] = bytes((bcd(a // 4500), bcd(a // 75 % 60), bcd(a % 75), 1))
    s[16:16 + USER] = data
    s[0x810:0x814] = struct.pack('<I', edc(s[0:0x810]))
    ecc_block(s, 86, 24, 2, 86, 0x81C)
    ecc_block(s, 52, 43, 86, 88, 0x8C8)
    return bytes(s)


# ---- track 3 access -----------------------------------------------------------------------------
class Track:
    """Track 3 as user sectors addressed by absolute LBA; ss = 2352 (raw MODE1) or 2048 (.iso)."""

    def __init__(self, path, ss):
        self.f = open(path, 'r+b')
        self.ss = ss
        self.sectors = os.path.getsize(path) // ss

    @property
    def end(self):
        return HD_LBA + self.sectors

    def raw(self, i):
        self.f.seek(i * self.ss)
        return self.f.read(self.ss)

    def user(self, lba, n=1):
        out = bytearray()
        for k in range(n):
            i = lba + k - HD_LBA
            if i < 0 or i >= self.sectors:
                die('LBA %d is outside track 3 (%d..%d)' % (lba + k, HD_LBA, self.end))
            self.f.seek(i * self.ss + (16 if self.ss == RAW else 0))
            out += self.f.read(USER)
        return bytes(out)

    def write(self, lba, data):
        data = data.ljust(USER, b'\0')
        i = lba - HD_LBA
        self.f.seek(i * self.ss)
        self.f.write(mode1_sector(lba, data) if self.ss == RAW else data)
        self.sectors = max(self.sectors, i + 1)

    def write_blob(self, lba, blob):
        for k in range(nsec(len(blob))):
            self.write(lba + k, blob[k * USER:(k + 1) * USER])

    def read_blob(self, lba, size):
        return self.user(lba, nsec(size))[:size] if size else b''


def both(v, n):
    le, be = ('<I', '>I') if n == 4 else ('<H', '>H')
    return struct.pack(le, v) + struct.pack(be, v)


def patch_user(t, lba, off, data):
    sec = bytearray(t.user(lba))
    sec[off:off + len(data)] = data
    t.write(lba, bytes(sec))


# ---- ISO9660 / Rock Ridge / Joliet --------------------------------------------------------------
def susp_entries(t, rec):
    """[(signature, entry bytes)] of a directory record's system use area, CE continuations followed."""
    nl = rec[32]
    o = 33 + nl + (0 if nl & 1 else 1)
    area, out, hops = rec[o:], [], 0
    while True:
        p, ce = 0, None
        while p + 4 <= len(area):
            ln, ver = area[p + 2], area[p + 3]
            if ln < 4 or ver not in (1, 2):
                break
            e = area[p:p + ln]
            out.append((bytes(e[0:2]), bytes(e)))
            if e[0:2] == b'CE':
                ce = (struct.unpack_from('<I', e, 4)[0], struct.unpack_from('<I', e, 12)[0],
                      struct.unpack_from('<I', e, 20)[0])
            p += ln
        if ce is None or hops > 8:
            return out
        hops += 1
        blk, off, ln = ce
        area = t.user(blk, nsec(off + ln))[off:off + ln]


def rr_name(entries):
    nm = None
    for sig, e in entries:
        if sig == b'NM' and not e[4] & 6:  # not CURRENT / PARENT
            nm = (nm or '') + e[5:].decode('latin-1')
    return nm


class Tree:
    """One directory hierarchy (the primary volume with its Rock Ridge names, or the Joliet one)."""

    def __init__(self, t, vd_lba, joliet):
        d = t.user(vd_lba)
        self.vd_lba, self.joliet = vd_lba, joliet
        root = d[156:156 + 34]
        self.root = (struct.unpack_from('<I', root, 2)[0], struct.unpack_from('<I', root, 10)[0])
        pts = struct.unpack_from('<I', d, 132)[0]
        tabs = [struct.unpack_from('<I', d, 140)[0], struct.unpack_from('<I', d, 144)[0],
                struct.unpack_from('>I', d, 148)[0], struct.unpack_from('>I', d, 152)[0]]
        self.meta_end = max([lba + nsec(pts) for lba in tabs if lba] + [0])
        self.rock_ridge = False
        self.files, self.dirs = {}, {}
        self.walk(t)

    def records(self, t, lba, size):
        for k in range(nsec(size)):
            sec = t.user(lba + k)
            o = 0
            while o < USER and sec[o]:
                n = sec[o]
                yield lba + k, o, sec[o:o + n]
                o += n

    def name(self, t, rec):
        raw = rec[33:33 + rec[32]]
        if raw in (b'\0', b'\1'):
            return None
        if self.joliet:
            return raw.decode('utf-16-be').split(';')[0]
        entries = susp_entries(t, rec)
        for sig, e in entries:  # Rock Ridge continuation areas belong to the ISO tables too
            if sig == b'CE':
                ce = struct.unpack_from('<I', e, 4)[0]
                self.meta_end = max(self.meta_end, ce + nsec(struct.unpack_from('<I', e, 12)[0] +
                                                             struct.unpack_from('<I', e, 20)[0]))
        nm = rr_name(entries)
        if nm is not None:
            self.rock_ridge = True
            return nm
        return raw.decode('latin-1').split(';')[0].rstrip('.')

    def walk(self, t):
        stack = [('', self.root[0], self.root[1])]
        while stack:
            prefix, lba, size = stack.pop()
            if prefix.lower() in self.dirs:
                continue
            self.dirs[prefix.lower()] = (lba, size)
            self.meta_end = max(self.meta_end, lba + nsec(size))
            for rlba, off, rec in self.records(t, lba, size):
                name = self.name(t, rec)
                if name is None:
                    continue
                ext, ln, flags = struct.unpack_from('<I', rec, 2)[0], struct.unpack_from('<I', rec, 10)[0], rec[25]
                path = prefix + '/' + name
                if flags & 2:
                    stack.append((path, ext, ln))
                else:
                    self.files.setdefault(path.lower(), []).append((rlba, off, ext, ln))


def volumes(t):
    """Primary and Joliet trees of track 3, and the end of the volume descriptor set."""
    trees, end = [], HD_LBA + 16
    for k in range(16, 64):
        d = t.user(HD_LBA + k)
        if d[1:6] != b'CD001':
            break
        end = HD_LBA + k + 1
        if d[0] == 255:
            break
        if d[0] == 1 or (d[0] == 2 and d[88:91] in (b'%/@', b'%/C', b'%/E')):
            trees.append(Tree(t, HD_LBA + k, d[0] == 2))
    if not trees or trees[0].joliet:
        die('no ISO9660 primary volume in track 3')
    return trees, end


def iso_ident(name, taken):
    """An ISO9660 level-1 identifier for a new file (upper case 8.3; the Rock Ridge / Joliet name is the real one)."""
    base, _, ext = name.upper().rpartition('.') if '.' in name else (name.upper(), '', '')
    clean = lambda s: ''.join(c if c.isalnum() or c == '_' else '_' for c in s)
    base, ext = clean(base)[:8] or '_', clean(ext)[:3]
    for n in range(100):
        b = base if n == 0 else (base[:8 - len(str(n)) - 1] + '~' + str(n))
        ident = b + ('.' + ext if ext else '') + ';1'
        if ident not in taken:
            return ident
    die('no free ISO9660 name for %s' % name)


# ---- the swap -----------------------------------------------------------------------------------
class Disc:
    def __init__(self, t):
        self.t = t
        self.trees, vd_end = volumes(t)
        self.meta_end = max([vd_end] + [tr.meta_end for tr in self.trees])
        ip = t.user(HD_LBA)
        self.boot = '/' + ip[0x60:0x70].decode('latin-1').strip().lower()
        # every file once, by its primary-tree path: [extent, sectors]
        self.live = {}
        for tr in self.trees:
            for p, recs in tr.files.items():
                if recs[0][3] and p not in self.live:
                    self.live[p] = [recs[0][2], nsec(recs[0][3])]
        self.standard = t.end == HD_END
        last = max(self.live.items(), key=lambda kv: kv[1][0] + kv[1][1], default=(None, None))[0]
        self.boot_last = self.standard and last == self.boot
        self.boot_end = (self.live[self.boot][0] + self.live[self.boot][1]) if self.boot in self.live else None
        self.low = min([v[0] for v in self.live.values()] + [t.end])
        self.written, self.freed = set(), set()
        self.report = []

    def recs(self, path):
        out = []
        for tr in self.trees:
            out += tr.files.get(path, [])
        return out

    def alloc(self, n):
        """n sectors: in front of the first file (standard) or after the end of the track (legacy)."""
        if self.standard:
            new = self.low - n
            if new < self.meta_end:
                die('no free space left in front of the first file (needs %d sectors at LBA %d, the ISO tables end at %d)'
                    % (n, new, self.meta_end))
            self.low = new
            return new
        new = self.t.end
        if new + n > HD_END:
            die('track 3 would pass the end of the GD-ROM high-density area')
        return new

    def put(self, lba, blob):
        self.t.write_blob(lba, blob)
        self.written.update(range(lba, lba + nsec(len(blob))))

    def point(self, path, lba, size):
        for rlba, off, _, _ in self.recs(path):
            patch_user(self.t, rlba, off + 2, both(lba, 4) + both(size, 4))
        for tr in self.trees:
            if path in tr.files:
                tr.files[path] = [(r[0], r[1], lba, size) for r in tr.files[path]]
        if size:
            self.live[path] = [lba, nsec(size)]
        else:
            self.live.pop(path, None)

    def move(self, path, why):
        ext, n = self.live[path]
        size = self.recs(path)[0][3]
        blob = self.t.read_blob(ext, size)
        new = self.alloc(n)
        self.put(new, blob)
        self.freed.update(range(ext, ext + n))
        self.point(path, new, size)
        self.report.append('%-22s %9d bytes  lba %d -> %d (moved: %s)' % (path, size, ext, new, why))

    def replace(self, path, blob):
        recs = self.recs(path)
        if not recs:
            die('%s is not on the disc' % path)
        ext, ln = recs[0][2], recs[0][3]
        if any(r[2] != ext or r[3] != ln for r in recs):
            die('%s has directory records with different extents' % path)
        old_n, n = nsec(ln), nsec(len(blob))
        if ln == len(blob) and self.t.read_blob(ext, ln) == blob:
            self.report.append('%-22s %9d bytes  unchanged' % (path, ln))
            return
        if path == self.boot and self.boot_last:
            new = self.boot_end - n
            if new < self.meta_end:
                die('%s does not fit on the disc' % path)
            for p, (e, k) in sorted(self.live.items(), key=lambda kv: -kv[1][0]):
                if p != path and e < ext and e + k > new:
                    self.move(p, 'room for the longer ' + path.lstrip('/'))
            self.freed.update(range(ext, ext + old_n))
            how = '' if new == ext else ' (ends at lba %d, the last file)' % self.boot_end
        elif n <= old_n:
            new = ext
            self.freed.update(range(ext + n, ext + old_n))
            how = ''
        else:
            new = self.alloc(n)
            self.freed.update(range(ext, ext + old_n))
            how = ' (moved in front of the first file)' if self.standard else ' (appended)'
        self.put(new, blob)
        self.point(path, new, len(blob))
        self.report.append('%-22s %9d -> %9d bytes  lba %d -> %d%s' % (path, ln, len(blob), ext, new, how))

    def add(self, path, blob):
        key = path.lower()
        if self.recs(key):
            die('%s is already on the disc (use --replace)' % path)
        parent, name = path.rsplit('/', 1)
        new = self.alloc(max(1, nsec(len(blob))))
        self.put(new, blob)
        for tr in self.trees:
            if parent.lower() not in tr.dirs:
                die('directory %s/ is not on the disc' % parent)
            dlba, dsize = tr.dirs[parent.lower()]
            taken, template = set(), None
            for _, _, rec in tr.records(self.t, dlba, dsize):
                taken.add(bytes(rec[33:33 + rec[32]]).decode('latin-1'))
                if template is None and not rec[25] & 2:
                    template = rec
            if tr.joliet:
                ident, susp = name.encode('utf-16-be'), b''
            else:
                ident = iso_ident(name, taken).encode('latin-1')
                susp = b''
                if tr.rock_ridge:
                    if template is None:  # an empty directory: any file record of the tree
                        rlba, off, _, _ = next(iter(tr.files.values()))[0]
                        sec = self.t.user(rlba)
                        template = sec[off:off + sec[off]]
                    keep = [e for sig, e in susp_entries(self.t, template) if sig in (b'PX', b'TF')]
                    nm = name.encode('latin-1')
                    susp = b''.join(keep) + b'NM' + bytes((5 + len(nm), 1, 0)) + nm
            rec = bytearray(33 + len(ident) + (0 if len(ident) & 1 else 1)) + susp
            if len(rec) & 1:
                rec += b'\0'
            rec[0] = len(rec)
            rec[2:10] = both(new, 4)
            rec[10:18] = both(len(blob), 4)
            rec[18:25] = template[18:25] if template is not None else bytes((126, 10, 12, 0, 0, 0, 0))
            rec[25] = 0
            rec[28:32] = both(1, 2)
            rec[32] = len(ident)
            rec[33:33 + len(ident)] = ident
            last = dlba + nsec(dsize) - 1
            sec = self.t.user(last)
            o = 0
            while o < USER and sec[o]:
                o += sec[o]
            if o + len(rec) > USER:
                die('no room for %s in the last sector of %s/' % (path, parent))
            patch_user(self.t, last, o, bytes(rec))
            tr.files[key] = [(last, o, new, len(blob))]
        if blob:
            self.live[key] = [new, nsec(len(blob))]
        self.report.append('%-22s %9s -> %9d bytes  lba %d (added)' % (path, '-', len(blob), new))

    def finish(self):
        if self.standard:
            zero = sorted(self.freed - self.written)
            for lba in zero:
                self.t.write(lba, b'')
            if zero:
                self.report.append('zeroed %d sectors no file uses any more' % len(zero))
        else:
            # legacy: the volume size (both-endian at byte 80) of every descriptor covers the appended sectors
            for tr in self.trees:
                if struct.unpack_from('<I', self.t.user(tr.vd_lba), 80)[0] < self.t.sectors:
                    patch_user(self.t, tr.vd_lba, 80, both(self.t.sectors, 4))


def verify(t, want, standard, boot, boot_end):
    """Read the written track back: swapped files byte for byte, extents inside the track and disjoint, the boot file
    still last on a standard disc."""
    d = Disc(t)
    for path, blob in want.items():
        recs = d.recs(path)
        if not recs or any(r[2] != recs[0][2] or r[3] != len(blob) for r in recs):
            die('check: %s has wrong directory records after the swap' % path)
        if t.read_blob(recs[0][2], len(blob)) != blob:
            die('check: %s does not read back as written' % path)
    spans = sorted((e, e + n, p) for p, (e, n) in d.live.items())
    for (a0, a1, pa), (b0, b1, pb) in zip(spans, spans[1:]):
        if b0 < a1:
            die('check: %s and %s overlap' % (pa, pb))
    if spans and (spans[0][0] < d.meta_end or spans[-1][1] > t.end):
        die('check: a file lies outside the data area of track 3')
    if standard and boot_end is not None:
        if spans[-1][2] != boot or spans[-1][1] != boot_end or t.end != HD_END:
            die('check: %s is no longer the last file ending at LBA %d' % (boot, boot_end))
    return len(spans)


# ---- inputs and outputs -------------------------------------------------------------------------
def program_files(prog, objcopy):
    prog = Path(prog)
    out = {}
    elf = prog / 're4dc-game.elf' if prog.is_dir() else prog
    if elf.suffix.lower() == '.elf':
        tmp = elf.with_name('.swap-prog.bin')
        subprocess.check_call([objcopy, '-R', '.stack', '-O', 'binary', str(elf), str(tmp)])
        out['/1st_read.bin'] = tmp.read_bytes()
        tmp.unlink()
    else:
        out['/1st_read.bin'] = elf.read_bytes()
    if prog.is_dir():
        for o in sorted(prog.glob('*.ovl')):
            out['/dc/' + o.name.lower()] = o.read_bytes()
    if not out['/1st_read.bin']:
        die('empty program')
    return out


def gdi_tracks(gdi):
    return [l.split() for l in gdi.splitlines()[1:] if l.strip()]


def unpack_release(src, out, disc=1):
    """Copy disc.gdi and its tracks from a zip or a directory into out. A two-disc game zip (Disc 1 in gdemu/, Disc 2 in
    disc2/; test 26 on) gives the disc picked by --disc."""
    src = Path(src)
    out.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        gdi = (src / 'disc.gdi').read_bytes().decode()
        for n in ['disc.gdi'] + [l[4] for l in gdi_tracks(gdi)]:
            shutil.copyfile(src / n, out / n)
        return gdi
    with zipfile.ZipFile(src) as z:
        gdis = [n for n in z.namelist() if n.lower().endswith('disc.gdi')]
        if len(gdis) > 1:
            gdis = [n for n in gdis if n.lower() == ('disc2/disc.gdi' if disc == 2 else 'gdemu/disc.gdi')]
        elif disc != 1:
            die('%s holds one disc; --disc %d asked' % (src, disc))
        if len(gdis) != 1:
            die('expected one disc.gdi in %s, found %d' % (src, len(gdis)))
        base = gdis[0][:-len('disc.gdi')]
        gdi = z.read(gdis[0]).decode()
        for n in ['disc.gdi'] + [l[4] for l in gdi_tracks(gdi)]:
            with z.open(base + n) as r, open(out / n, 'wb') as w:
                shutil.copyfileobj(r, w, 1 << 22)
    return gdi


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('release')
    ap.add_argument('program')
    ap.add_argument('outdir')
    ap.add_argument('--replace', action='append', default=[], metavar='DISC/PATH=FILE',
                    help='also replace another disc file, e.g. debug/config.txt=my.txt')
    ap.add_argument('--add', action='append', default=[], metavar='DISC/PATH=FILE',
                    help='add a file that is not on the disc yet, e.g. dc/padscript.txt=padscript-newgame.txt')
    ap.add_argument('--disc', type=int, default=1, choices=(1, 2), help='which disc of a two-disc game zip (default 1)')
    ap.add_argument('--objcopy', default=os.environ.get('SH_OBJCOPY', 'sh-elf-objcopy'))
    ap.add_argument('--selftest', action='store_true', help='re-encode the first sectors and compare (EDC/ECC check)')
    a = ap.parse_args()
    out = Path(a.outdir)
    if out.exists() and any(out.iterdir()):
        die('%s is not empty' % out)
    blobs = program_files(a.program, a.objcopy)
    if a.disc == 2:   # Disc 2 carries no village rooms: discsets/mkdisc2.py drops the stage-1 overlays
        blobs = {k: v for k, v in blobs.items() if not (k.startswith('/dc/st1_') and k.endswith('.ovl'))}
    for r in a.replace:
        k, v = r.split('=', 1)
        blobs['/' + k.strip('/').lower()] = Path(v).read_bytes()
    adds = {}
    for r in a.add:
        k, v = r.split('=', 1)
        adds['/' + k.strip('/')] = Path(v).read_bytes()
    gdi = unpack_release(a.release, out, a.disc)
    lines = gdi_tracks(gdi)
    t3 = [l for l in lines if int(l[1]) == HD_LBA]
    if len(t3) != 1 or t3[0][3] not in (str(RAW), str(USER)):
        die('track 3 must be a MODE1 data track at LBA %d (got %s)' % (HD_LBA, t3))
    t = Track(out / t3[0][4], int(t3[0][3]))
    if t.ss == RAW:
        first = t.raw(16)
        if mode1_sector(HD_LBA + 16, first[16:16 + USER]) != first:
            die('sector encoder does not reproduce the disc (not a MODE1 raw track?)')
        if a.selftest:
            for i in range(0, min(t.sectors, 64)):
                r = t.raw(i)
                assert mode1_sector(HD_LBA + i, r[16:16 + USER]) == r, i
            print('selftest: 64 sectors re-encode byte-identical')
    d = Disc(t)
    print('layout %s: track 3 lba %d..%d, %d files, first file at lba %d, %s %s' % (
        'standard' if d.standard else 'legacy', HD_LBA, t.end, len(d.live), d.low, d.boot.lstrip('/'),
        'last, ends at lba %d' % d.boot_end if d.boot_last else 'at lba %s' % (d.live.get(d.boot, ['?'])[0])))
    # other files first, so a longer boot file finds them already placed
    for path in sorted(blobs, key=lambda p: p == d.boot):
        d.replace(path, blobs[path])
    for path, blob in adds.items():
        d.add(path, blob)
    d.finish()
    want = dict(blobs)
    want.update({p.lower(): b for p, b in adds.items()})
    n = verify(t, want, d.standard, d.boot, d.boot_end if d.boot_last else None)
    t.f.close()
    for l in d.report:
        print(l)
    print('check: %d swapped files read back, %d files inside track 3 without overlaps%s' % (
        len(want), n, ', %s last' % d.boot.lstrip('/') if d.boot_last else ''))
    print('track03 sectors %d (lba %d..%d of %d)' % (t.sectors, HD_LBA, HD_LBA + t.sectors, HD_END))
    with open(out / 'SHA256SUMS.txt', 'w') as w:
        for l in lines:
            h = hashlib.sha256()
            with open(out / l[4], 'rb') as f:
                for c in iter(lambda: f.read(1 << 22), b''):
                    h.update(c)
            w.write('%s  %s\n' % (h.hexdigest(), l[4]))
    print('wrote %s/disc.gdi' % out)


if __name__ == '__main__':
    main()
