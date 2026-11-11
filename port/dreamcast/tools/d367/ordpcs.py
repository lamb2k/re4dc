"""ordpcs.py: console PC-sampler evidence for ordgen_c3.py --pcs and ordcheck.py --collide / --identity (a module,
no command line of its own).

Input sections ("nodes") are found in an ELF by their symbols: every .text input section of the build's objects
(and of the archive members the link pulled in: KOS, libc, libm, libgcc) is located at (address of one of its
symbols in the ELF) - (that symbol's offset in the section). A PCS sample (platform/pc_sampler.cpp, read_pcs.py
format) is then booked to (node, offset in node), so the same samples can be replayed on another layout of the
same objects. Caller edges come from the sampled PR when the instruction before it is a call (jsr / bsr / bsrf).
"""
import bisect
import collections
import glob
import hashlib
import os
import re
import struct
import subprocess

TOOLS = "/opt/toolchains/dc/sh-elf/bin/sh-elf-"
TEXT_BASE = 0x8C010000
LINE = 32
SETS = 256                      # 8 KB direct-mapped I-cache: 256 lines of 32 B
PCS_GAP, PCS_MARKER, PCS_PC_FOREIGN, PCS_PR_FOREIGN = 0xFFFFFFFF, 0x80000000, 0x10000000, 0x20000000


def run(*args):
    return subprocess.run(list(args), capture_output=True, text=True, check=True).stdout


def demangle(names):
    names = list(names)
    if not names:
        return {}
    out = subprocess.run(["c++filt", "-_"], input="\n".join(names), capture_output=True, text=True).stdout.splitlines()
    return dict(zip(names, out)) if len(out) == len(names) else {n: n for n in names}


# ---------------------------------------------------------------- ELF (32-bit LE) without external tools
class Elf:
    def __init__(self, path):
        self.path = path
        b = open(path, "rb").read()
        self.b = b
        shoff, = struct.unpack_from("<I", b, 0x20)
        shentsize, shnum, shstrndx = struct.unpack_from("<HHH", b, 0x2E)
        sh = [struct.unpack_from("<IIIIIIIIII", b, shoff + i * shentsize) for i in range(shnum)]
        so = sh[shstrndx][4]

        def cstr(off):
            return b[off:b.index(b"\0", off)].decode("latin-1")
        self.secs = []                  # (name, type, flags, addr, offset, size)
        for s in sh:
            self.secs.append((cstr(so + s[0]), s[1], s[2], s[3], s[4], s[5]))
        self.sec = {s[0]: s for s in self.secs}
        # symbols with their FILE context (locals follow their FILE symbol)
        self.syms = []                  # (name, value, size, type, bind, shndx, file)
        for i, s in enumerate(sh):
            if s[1] != 2:               # SHT_SYMTAB
                continue
            strt = sh[s[6]][4]
            cur = ""
            for k in range(s[5] // 16):
                nm, val, sz, info, oth, shn = struct.unpack_from("<IIIBBH", b, s[4] + k * 16)
                typ, bind = info & 15, info >> 4
                name = cstr(strt + nm)
                if typ == 4:            # STT_FILE
                    cur = name
                    continue
                self.syms.append((name, val, sz, typ, bind, shn, cur if bind == 0 else ""))
        t = self.sec[".text"]
        self.text_lo, self.text_hi = t[3], t[3] + t[5]
        self.text = b[t[4]:t[4] + t[5]]

    def read16(self, addr):
        o = addr - self.text_lo
        return struct.unpack_from("<H", self.text, o)[0] if 0 <= o <= len(self.text) - 2 else None

    def read32(self, addr):
        o = addr - self.text_lo
        return struct.unpack_from("<I", self.text, o)[0] if 0 <= o <= len(self.text) - 4 else None

    def alloc_sections(self):
        return [s for s in self.secs if s[2] & 2 and s[5]]            # SHF_ALLOC

    def bytes_at(self, addr, n):
        for name, typ, fl, a, off, sz in self.secs:
            if fl & 2 and typ != 8 and a <= addr and addr + n <= a + sz:   # not NOBITS
                return self.b[off + addr - a: off + addr - a + n]
        return None


def stem(path):
    return re.sub(r"\.(c|cc|cpp|cxx|s|S|o)$", "", os.path.basename(path.split(":")[-1]))


# ---------------------------------------------------------------- objects and archive members
OBJ_HDR = re.compile(r"^(\S.*?):\s+file format \S+")
SYM = re.compile(r"^([0-9a-f]{8}) (.{7}) (\S+)\t([0-9a-f]+) ?(.*)$")
HDR = re.compile(r"^\s*\d+\s+(\S+)\s+([0-9a-f]{8})\s+[0-9a-f]{8}\s+[0-9a-f]{8}\s+[0-9a-f]{8}\s+2\*\*(\d+)")


class Objects:
    """.text input sections of an object directory plus archive members: key = (object, section)."""

    def __init__(self, objdir, archives=(), tools=TOOLS):
        self.secs = {}                  # key -> dict(size, align, syms=[(name, value, global)])
        self.rel = {}                   # object -> its file name for the order rule
        objs = sorted(glob.glob(objdir + "/**/*.o", recursive=True))
        base_n = collections.Counter(os.path.basename(o) for o in objs)
        for i in range(0, len(objs), 150):
            chunk = objs[i:i + 150]
            self._parse(run(tools + "objdump", "-h", "-t", *chunk), None, objdir, base_n)
        for a in archives:
            if os.path.exists(a):
                self._parse(run(tools + "objdump", "-h", "-t", a), a, objdir, base_n)

    def _parse(self, text, archive, objdir, base_n):
        obj = None
        for l in text.splitlines():
            m = OBJ_HDR.match(l)
            if m and not l.startswith("In archive"):
                f = m.group(1)
                if archive:
                    obj = "%s:%s" % (os.path.basename(archive), os.path.basename(f))
                    self.rel[obj] = obj                  # *libc.a:libc_a-memcpy.o(.text)
                else:
                    r = os.path.relpath(f, objdir)
                    obj = r
                    b = os.path.basename(r)
                    # basename unless two objects share it (platform/dvd.o, src/game/dvd.o): then dir/basename
                    self.rel[obj] = b if base_n[b] == 1 else "/".join(r.split("/")[-2:])
                continue
            if obj is None:
                continue
            m = HDR.match(l)
            if m and m.group(1).startswith(".text"):
                k = (obj, m.group(1))
                d = self.secs.setdefault(k, {"size": 0, "align": 1, "syms": []})
                d["size"], d["align"] = int(m.group(2), 16), 1 << int(m.group(3))
                continue
            m = SYM.match(l)
            if m and m.group(3).startswith(".text"):
                flags, sec, val = m.group(2), m.group(3), int(m.group(1), 16)
                name = m.group(5).split()[-1] if m.group(5).split() else ""
                if not name or flags[5] in "dD":
                    continue
                k = (obj, sec)
                d = self.secs.setdefault(k, {"size": 0, "align": 1, "syms": []})
                d["syms"].append((name, val, flags[0] in "gu!" or flags[1] == "w", flags[1] == "w"))


# ---------------------------------------------------------------- where every input section sits in an ELF
class Layout:
    def __init__(self, elf, objs):
        self.elf = elf
        glob_a, loc_a = {}, collections.defaultdict(list)
        for name, val, sz, typ, bind, shn, f in elf.syms:
            if not (elf.text_lo <= val < elf.text_hi + 0x100):
                continue
            if bind in (1, 2):
                glob_a.setdefault(name, val)
            else:
                loc_a[(stem(f), name)].append(val)
        start, self.comdat, bad = {}, set(), 0
        for k, d in objs.secs.items():
            if d["size"] == 0:
                continue
            a = None
            for name, val, isglob, weak in sorted(d["syms"], key=lambda s: not s[2]):
                if isglob:
                    a = glob_a.get(name)
                else:
                    c = loc_a.get((stem(k[0]), name), [])
                    a = c[0] if len(c) == 1 else None
                if a is not None:
                    a -= val
                    if weak:
                        self.comdat.add(k)
                    break
            if a is None or not (elf.text_lo <= a and a + d["size"] <= elf.text_hi + 0x100):
                continue
            start[k] = a
        # a COMDAT section claimed by several objects resolves to the kept copy for each: keep one claimant
        by = {}
        for k in sorted(start, key=lambda k: (start[k], k)):
            s = (start[k], objs.secs[k]["size"])
            if s in by:
                self.comdat.add(by[s])
                continue
            by[s] = k
        self.start = {k: s[0] for s, k in by.items()}
        self.size = {k: objs.secs[k]["size"] for k in self.start}
        iv = sorted((a, k) for k, a in self.start.items())
        self.iv_a, self.iv_k = [], []
        for a, k in iv:
            if self.iv_a and a < self.iv_a[-1] + self.size[self.iv_k[-1]]:
                bad += 1                # overlapping claim: a mapping error, dropped
                continue
            self.iv_a.append(a)
            self.iv_k.append(k)
        self.overlaps = bad
        # names: the section's first global symbol (else first), for reports
        self.name = {}
        for k in self.start:
            syms = sorted(objs.secs[k]["syms"], key=lambda s: (not s[2], s[1]))
            self.name[k] = syms[0][0] if syms else k[1]
        # unmapped code (sections the objects do not explain): ELF symbols
        fs = sorted((v, n) for n, v, sz, t, b, shn, f in elf.syms
                    if elf.text_lo <= v < elf.text_hi and t in (0, 2) and not n.startswith((".L", "L_", "$")))
        self.fs_a = [v for v, n in fs]
        self.fs_n = [n for v, n in fs]

    def at(self, pc):
        """(node key, offset) or (('?', symbol), offset) for code no input section explains."""
        i = bisect.bisect_right(self.iv_a, pc) - 1
        if i >= 0 and pc < self.iv_a[i] + self.size[self.iv_k[i]]:
            return self.iv_k[i], pc - self.iv_a[i]
        j = bisect.bisect_right(self.fs_a, pc) - 1
        return ("?", self.fs_n[j] if j >= 0 else "?"), 0

    def covered(self):
        return sum(self.size.values()), self.elf.text_hi - self.elf.text_lo


# ---------------------------------------------------------------- samples
def is_call(elf, pr):
    op = elf.read16(pr - 4)
    if op is None:
        return False
    return (op & 0xF0FF) == 0x400B or (op & 0xF000) == 0xB000 or (op & 0xF0FF) == 0x0003


class Evidence:
    """Console samples on the profiled layout.
    hot[key]   percent of busy time (every scene weighted equally)
    cls[key]   Counter of percent by thread class: main (tid 1), logic (the scene's busiest other tid), svc
    offs[key]  Counter of sample offsets in the node
    edges      Counter (caller key, callee key) -> percent of samples with that return edge"""

    def __init__(self, layout, pcs_files, scenes=None, exclude=""):
        self.L = layout
        by_scene = collections.defaultdict(list)
        for f in sorted(pcs_files):
            sc = re.sub(r"-snap\d.*$", "", os.path.basename(f))
            if scenes and sc not in scenes:
                continue
            by_scene[sc].append(f)
        self.scenes = sorted(by_scene)
        self.hot = collections.Counter()
        self.cls = collections.defaultdict(collections.Counter)
        self.offs = collections.defaultdict(collections.Counter)
        self.edges = collections.Counter()
        self.nsamples = collections.Counter()
        self.unmapped = collections.Counter()
        dm_names = {}
        excl = re.compile(exclude) if exclude else None
        for sc, files in by_scene.items():
            recs = []
            for f in files:
                b = open(f, "rb").read()[128:]
                for i in range(0, len(b) - 7, 8):
                    w0, w1 = struct.unpack_from("<II", b, i)
                    if w1 == PCS_GAP or w1 & PCS_MARKER or w1 & PCS_PC_FOREIGN:
                        continue
                    recs.append((w0 >> 23, 0x8C000000 | ((w0 & 0x7FFFFF) << 1),
                                 None if w1 & PCS_PR_FOREIGN else 0x8C000000 | ((w1 & 0x7FFFFF) << 1)))
            if not recs:
                continue
            tids = collections.Counter(t for t, pc, pr in recs if t != 1)
            logic = tids.most_common(1)[0][0] if tids else -1
            w = 100.0 / len(by_scene) / len(recs)
            self.nsamples[sc] = len(recs)
            for tid, pc, pr in recs:
                k, off = layout.at(pc)
                if k[0] == "?":
                    self.unmapped[k[1]] += w
                    continue
                if excl:
                    nm = layout.name[k]
                    if nm not in dm_names:
                        dm_names[nm] = demangle([nm])[nm]
                    if excl.search(dm_names[nm]):
                        continue
                c = "main" if tid == 1 else "logic" if tid == logic else "svc"
                self.hot[k] += w
                self.cls[k][c] += w
                self.offs[k][off] += 1
                if pr is not None and is_call(layout.elf, pr):
                    kc, _ = layout.at(pr)
                    if kc[0] != "?" and kc != k:
                        self.edges[(kc, k)] += w
        # static call sites between mapped nodes (bsr / bra / jsr / jmp after a PC-relative literal of the target)
        self.static = set()
        elf = layout.elf
        starts = set(layout.start.values())
        recent = {}
        t = elf.text
        for o in range(0, len(t) - 1, 2):
            op = t[o] | t[o + 1] << 8
            pc = elf.text_lo + o
            hi = op >> 12
            tgt = None
            if hi == 0xD:
                lit = (pc & ~3) + 4 + (op & 0xFF) * 4
                v = elf.read32(lit)
                if v is not None:
                    recent[(op >> 8) & 15] = (v, pc)
                continue
            if (op & 0xF0DF) == 0x400B:             # jsr / jmp @Rn
                r = recent.get((op >> 8) & 15)
                if r and pc - r[1] < 64:
                    tgt = r[0]
            elif hi in (0xA, 0xB):                  # bra / bsr
                d = op & 0xFFF
                d = d - 0x1000 if d & 0x800 else d
                tgt = pc + 4 + d * 2
            if tgt in starts:
                a, _ = layout.at(pc)
                b, _ = layout.at(tgt)
                if a[0] != "?" and b[0] != "?" and a != b:
                    self.static.add((a, b))

    def group(self, k, shared=0.3):
        c = self.cls.get(k)
        if not c:
            return "cold"
        tot = sum(c.values())
        top = c.most_common(2)
        if len(top) > 1 and top[1][1] >= shared * tot and {top[0][0], top[1][0]} != {"logic", "svc"}:
            return "shared"
        return top[0][0]


def compatible(ga, gb):
    """Thread classes whose code can evict each other inside one loop: the same class, or code both use."""
    return ga == gb or "shared" in (ga, gb)


def line_weights(ev, k, addr, size):
    """{cache set: weight}: half the node's time spread by bytes, half by where its samples fell."""
    h = ev.hot.get(k, 0.0)
    out = collections.defaultdict(float)
    if h <= 0 or size <= 0:
        return out
    a = addr
    end = addr + size
    while a < end:
        nxt = min(end, (a // LINE + 1) * LINE)
        out[(a // LINE) % SETS] += 0.5 * h * (nxt - a) / size
        a = nxt
    offs = ev.offs.get(k)
    if offs:
        n = sum(offs.values())
        for o, c in offs.items():
            out[((addr + o) // LINE) % SETS] += 0.5 * h * c / n
    else:
        for s in list(out):
            out[s] *= 2
    return out


def affinity(ev, a, b):
    if a == b:
        return 0.0
    e = ev.edges.get((a, b), 0.0) + ev.edges.get((b, a), 0.0)
    m = min(ev.hot.get(a, 0.0), ev.hot.get(b, 0.0))
    return min(1.0, e / m) if m > 0 else 0.0


def conflict(ev, addr_of, beta=4.0):
    """Layout conflict proxy (not timing): sum over pairs of hot nodes of compatible thread classes that share a
    cache set of w_a * w_b * (1 + beta * call affinity). Returns (total by class, Counter of node pairs)."""
    occ = collections.defaultdict(list)
    for k in ev.hot:
        a = addr_of(k)
        if a is None:
            continue
        g = ev.group(k)
        for s, w in line_weights(ev, k, a, ev.L.size[k]).items():
            occ[s].append((k, w, g))
    tot = collections.Counter()
    pairs = collections.Counter()
    for s, lst in occ.items():
        lst.sort(key=lambda x: -x[1])
        for i in range(len(lst)):
            ka, wa, ga = lst[i]
            for j in range(i + 1, len(lst)):
                kb, wb, gb = lst[j]
                if ka == kb or not compatible(ga, gb):
                    continue
                c = wa * wb * (1 + beta * affinity(ev, ka, kb))
                tot[ga if ga == gb else "shared"] += c
                pairs[(ka, kb) if ka < kb else (kb, ka)] += c
    return tot, pairs


def ranges(addr, size):
    """cache-index byte ranges (address mod 8 KB) of [addr, addr + size)"""
    lo, out = addr % 8192, []
    left = size
    while left > 0:
        n = min(left, 8192 - lo)
        out.append((lo, lo + n))
        left -= n
        lo = 0
    return out


def overlap(a1, s1, a2, s2):
    t = 0
    for x0, x1 in ranges(a1, s1):
        for y0, y1 in ranges(a2, s2):
            t += max(0, min(x1, y1) - max(x0, y0))
    return t


# the review's world-draw pairs (REVIEW-ANSWER-20261111.md section 2 item 1): functions that alternate once per meshlet
PAIRS_A = r"transform_sched<3u>|vp::walk_lean\(|Emitter::clip_strip<|transform_sched_ix"
PAIRS_B = r"MeshDraw::chunk_emit|ScenerySelector::chunk_select\(|sg_pick_planes_fused_lean|\)::ps2_pass\("


def named_pairs(L, addr_of, pa=PAIRS_A, pb=PAIRS_B):
    """lines: each named function's address, size and cache-index range, then the A x B index overlaps in bytes"""
    names = demangle(L.name.values())
    sel = lambda rx: sorted((names.get(L.name[k], L.name[k]), k) for k in L.start if re.search(rx, names.get(L.name[k], "")))
    A, B = sel(pa), sel(pb)
    out = []
    for n, k in A + B:
        ad = addr_of(k)
        if ad is None:
            continue
        out.append("  %08x %6d B  index %s  %s" % (ad, L.size[k], ", ".join("%04x-%04x" % r for r in ranges(ad, L.size[k])),
                                                    n[:60]))
    tot = 0
    for na, ka in A:
        for nb, kb in B:
            x, y = addr_of(ka), addr_of(kb)
            if x is None or y is None:
                continue
            o = overlap(x, L.size[ka], y, L.size[kb])
            tot += o
            if o:
                out.append("  overlap %5d B  %s  x  %s" % (o, na[:40], nb[:40]))
    out.append("  total A x B index overlap %d B" % tot)
    return out


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def obj_digest(path):
    """sha256 of an object's sections other than debug info / .comment (debug info holds the build directory)"""
    b = open(path, "rb").read()
    shoff, = struct.unpack_from("<I", b, 0x20)
    shentsize, shnum, shstrndx = struct.unpack_from("<HHH", b, 0x2E)
    sh = [struct.unpack_from("<IIIIIIIIII", b, shoff + i * shentsize) for i in range(shnum)]
    so = sh[shstrndx][4]
    h = hashlib.sha256()
    for s in sh:
        name = b[so + s[0]:b.index(b"\0", so + s[0])]
        if re.match(rb"^(\.rela?)?\.debug|^\.comment$", name):
            continue
        h.update(name + b"\0" + struct.pack("<IIII", s[1], s[2], s[5], s[8]))
        if s[1] != 8:
            h.update(b[s[4]:s[4] + s[5]])
    return h.hexdigest()
