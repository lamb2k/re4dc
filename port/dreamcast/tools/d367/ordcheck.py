#!/usr/bin/env python3
"""Stale-order check for a LINK_ORDER file (game30.mk; written by ordgen_c3.py).

A link order goes stale as code changes: sections it names disappear (renamed / removed functions; ld ignores
them) and new hot code (new kernels, split functions) is left at its default place in .text. This reports, for
an order file against the objects of a current build and hwproject evidence of the current code:
  - rules naming no current input section (stale rules);
  - per evidence run, the hw ms of the run's functions whose input section the order places ("covered"),
    against the run's total and the part in library / unmapped code (never placeable).
Regenerate with ordgen_c3.py when covered falls well below placeable (2026-10-04: the r101-square order on
r21y code covered 47-57% of the house / fight / square hw ms, the regenerated order 87-88%, placeable ~88%).

usage: ordcheck.py --objdir <OBJDIR of a current build> [--evidence-root D] [--exclude REGEX]
                   <order.ld> <hwproject evidence dir name>...

Lane layout30 (2026-11-11) adds two checks for a console-profile order (ordgen_c3.py --pcs):
  --collide ELF...  the conflict proxy of ordgen_c3.py --pcs (hot node pairs of one thread phase sharing a cache set,
                    from the console samples replayed at each ELF's addresses; a layout proxy, NOT timing) and the
                    review's world-draw pairs, for the profiled ELF and each given ELF.
      ordcheck.py --objdir <profiled OBJDIR> --pcs '<dir>/*-snap*.pcs' --pcs-elf <profiled ELF> --collide <arm ELF>
  --identity A.elf B.elf   placement-only identity: (with --identity-objdir) every object file byte-identical;
                    the same symbols with the same sizes; every function's bytes equal except words / branch
                    displacements whose targets are the same symbol + offset in each ELF; every data section
                    (.rodata, .data, ...) the same size and equal word for word up to the same relocation rule.
                    PASS when nothing else differs (lines listed otherwise).
      ordcheck.py --objdir <A OBJDIR> --identity-objdir <B OBJDIR> --identity A.elf B.elf"""
import argparse
import bisect
import collections
import glob
import os
import re
import struct
import subprocess
import sys

ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
ap.add_argument("--objdir", required=True)
ap.add_argument("--evidence-root", default=os.environ.get("HWM_EVIDENCE", "/mnt/d/Flycast-Evidence/re4-dreamcast"))
ap.add_argument("--tools", default="/opt/toolchains/dc/sh-elf/bin/sh-elf-")
ap.add_argument("--exclude", default="^(re4dc_pace_end|re4dc_vi_retrace_count)$",
                help="regex of functions (demangled) whose hw ms is not hardware work (the pacing spin)")
ap.add_argument("--pcs", nargs="*", default=[])
ap.add_argument("--pcs-elf")
ap.add_argument("--pcs-scenes", default="")
ap.add_argument("--archives", default="/root/work/kos-re4dc-d367/lib/dreamcast/libkallisti.a,"
                "/opt/toolchains/dc/sh-elf/sh-elf/lib/libc.a,/opt/toolchains/dc/sh-elf/sh-elf/lib/libm.a,"
                "/opt/toolchains/dc/sh-elf/lib/gcc/sh-elf/15.2.0/libgcc.a")
ap.add_argument("--beta", type=float, default=4.0)
ap.add_argument("--collide", nargs="*", default=None)
ap.add_argument("--identity", nargs=2, default=None)
ap.add_argument("--identity-objdir", default="")
ap.add_argument("order", nargs="?")
ap.add_argument("runs", nargs="*")
a = ap.parse_args()


def run(*args):
    return subprocess.run(list(args), capture_output=True, text=True, check=True).stdout


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def collide(a):
    import ordpcs as P
    P.TOOLS = a.tools
    objs = P.Objects(a.objdir, [x for x in a.archives.split(",") if x], a.tools)
    L0 = P.Layout(P.Elf(a.pcs_elf), objs)
    files = sorted({f for g in a.pcs for f in glob.glob(g)})
    ev = P.Evidence(L0, files, set(s for s in a.pcs_scenes.split(",") if s) or None,
                    "^(thd_idle_task|re4dc_pace_end|re4dc_vi_retrace_count)$")
    base = None
    for e in [a.pcs_elf] + list(a.collide):
        L = L0 if e == a.pcs_elf else P.Layout(P.Elf(e), objs)
        miss = [k for k in ev.hot if k not in L.start]
        tot, pairs = P.conflict(ev, lambda k: L.start.get(k), a.beta)
        s = sum(tot.values())
        base = s if base is None else base
        print("%s: conflict proxy %.3f (%+.0f%% vs profiled) by phase %s; sampled sections not found %d (%.2f%% busy)" % (
            e, s, 100.0 * (s - base) / max(base, 1e-9), " ".join("%s %.3f" % kv for kv in sorted(tot.items())),
            len(miss), sum(ev.hot[k] for k in miss)))
        for l in P.named_pairs(L, lambda k: L.start.get(k)):
            print(l)
        # hot code footprint: bytes of sections holding 50 / 90 / 99% of busy time, and their span in .text
        hk = sorted((k for k in ev.hot if k in L.start), key=lambda k: -ev.hot[k])
        acc, tgt, allh = 0.0, [50, 90, 99], sum(ev.hot.values())
        for i, k in enumerate(hk):
            acc += ev.hot[k]
            while tgt and acc >= tgt[0] * allh / 100.0:
                sel = hk[:i + 1]
                lo = min(L.start[x] for x in sel)
                hi = max(L.start[x] + L.size[x] for x in sel)
                print("  %d%% of busy time: %d sections, %d B of code, spread over %d B of .text" % (
                    tgt[0], len(sel), sum(L.size[x] for x in sel), hi - lo))
                tgt.pop(0)


def identity(a):
    import ordpcs as P
    A, B = P.Elf(a.identity[0]), P.Elf(a.identity[1])
    bad = []
    if a.identity_objdir:
        fa = {os.path.relpath(f, a.objdir): f for f in glob.glob(a.objdir + "/**/*.o", recursive=True)}
        fb = {os.path.relpath(f, a.identity_objdir): f for f in glob.glob(a.identity_objdir + "/**/*.o", recursive=True)}
        diff = [r for r in sorted(set(fa) & set(fb)) if P.obj_digest(fa[r]) != P.obj_digest(fb[r])]
        only = sorted(set(fa) ^ set(fb))
        print("objects (all sections but debug info): %d compared, %d differ%s, %d only in one objdir%s" % (
            len(set(fa) & set(fb)), len(diff), (": " + " ".join(diff[:8])) if diff else "", len(only),
            (": " + " ".join(only[:8])) if only else ""))
        bad += ["object differs: " + r for r in diff] + ["object only in one: " + r for r in only]

    def symtab(E):
        d = {}
        for name, val, sz, typ, bind, shn, f in E.syms:
            if shn == 0 or not name:
                continue
            d.setdefault((f, name), (val, sz, typ))
        return d
    SA, SB = symtab(A), symtab(B)
    ka, kb = set(SA), set(SB)
    if ka != kb:
        bad.append("symbol sets differ: %d only in A, %d only in B (%s)" % (
            len(ka - kb), len(kb - ka), " ".join(n for f, n in sorted(ka ^ kb)[:6])))
    sized = [k for k in ka & kb if SA[k][1] != SB[k][1]]
    if sized:
        bad.append("symbol sizes differ: %d (%s)" % (len(sized), " ".join(n for f, n in sized[:6])))

    def resolver(E, S):
        alloc = [(s[3], s[3] + s[5]) for s in E.alloc_sections()]
        pts = sorted({(v, k) for k, (v, sz, t) in S.items()
                      if any(lo <= v < hi for lo, hi in alloc) and t != 3})     # not STT_SECTION
        av = [p[0] for p in pts]
        kv = [p[1] for p in pts]

        def sym(x):
            if not any(lo <= x <= hi for lo, hi in alloc):
                return None
            i = bisect.bisect_right(av, x) - 1
            if i < 0:
                return None
            v = av[i]
            j = bisect.bisect_left(av, v)
            return (min(kv[j:i + 1]), x - v)          # aliases at one address: the smallest key
        return sym
    ra, rb = resolver(A, SA), resolver(B, SB)
    n_fun = n_same = n_reloc = 0
    unexplained = []
    for k in sorted(ka & kb):
        va, sz, typ = SA[k]
        vb = SB[k][0]
        if typ != 2 or sz == 0 or not (A.text_lo <= va < A.text_hi):
            continue
        n_fun += 1
        ba, bb = A.bytes_at(va, sz), B.bytes_at(vb, sz)
        if ba is None or bb is None:
            unexplained.append("%s: bytes not found" % k[1])
            continue
        if ba == bb:
            n_same += 1
            continue
        ok_pos, before = set(), len(unexplained)
        for o in range(0, sz - 1, 2):
            if ba[o:o + 2] == bb[o:o + 2] or o in ok_pos:
                continue
            ha, = struct.unpack_from("<H", ba, o)
            hb, = struct.unpack_from("<H", bb, o)
            if ha >> 12 == hb >> 12 and ha >> 12 in (0xA, 0xB):          # bra / bsr: same target?
                da = (ha & 0xFFF) - (0x1000 if ha & 0x800 else 0)
                db = (hb & 0xFFF) - (0x1000 if hb & 0x800 else 0)
                ta, tb = ra(va + o + 4 + 2 * da), rb(vb + o + 4 + 2 * db)
                if ta is not None and ta == tb:
                    continue
            wo = ((va + o) & ~3) - va                                    # the aligned literal word holding it
            if 0 <= wo and wo + 4 <= sz and ((vb + wo) & 3) == 0:
                xa, = struct.unpack_from("<I", ba, wo)
                xb, = struct.unpack_from("<I", bb, wo)
                sa, sb = ra(xa), rb(xb)
                if sa is not None and sa == sb:
                    ok_pos.update((wo, wo + 2))
                    continue
            unexplained.append("%s+%#x: %04x vs %04x" % (k[1], o, ha, hb))
        if len(unexplained) == before:
            n_reloc += 1
    print("functions: %d compared, %d byte-identical, %d differ only by relocated addresses, %d unexplained halfwords" % (
        n_fun, n_same, n_reloc, len(unexplained)))
    bad += unexplained
    # data sections word by word
    for s in A.alloc_sections():
        name, typ, fl, addr, off, size = s
        t = B.sec.get(name)
        if name == ".text" or typ == 8:
            if typ == 8 and (t is None or t[5] != size):
                bad.append("%s size %d vs %s" % (name, size, t and t[5]))
            continue
        if t is None or t[5] != size:
            bad.append("%s size %d vs %s" % (name, size, t and t[5]))
            continue
        da, db = A.b[off:off + size], B.b[t[4]:t[4] + size]
        if da == db:
            print("%s: %d B identical" % (name, size))
            continue
        nrel, nbad = 0, []
        for o in range(0, size - 3, 4):
            if da[o:o + 4] == db[o:o + 4]:
                continue
            xa, = struct.unpack_from("<I", da, o)
            xb, = struct.unpack_from("<I", db, o)
            sa, sb = ra(xa), rb(xb)
            if sa is not None and sa == sb:
                nrel += 1
            else:
                sy = ra(addr + o)
                nbad.append("%s+%#x (%s): %08x vs %08x" % (name, o, sy and "%s+%#x" % (sy[0][1], sy[1]), xa, xb))
        print("%s: %d B, %d words differ only by relocated addresses, %d unexplained%s" % (
            name, size, nrel, len(nbad), (": " + "; ".join(nbad[:6])) if nbad else ""))
        bad += nbad
    print(".text size %d vs %d (%+d B of alignment padding)" % (A.text_hi - A.text_lo, B.text_hi - B.text_lo,
                                                              (B.text_hi - B.text_lo) - (A.text_hi - A.text_lo)))
    print("IDENTITY %s (%d unexplained differences)" % ("PASS" if not bad else "FAIL", len(bad)))
    for b in bad[:30]:
        print("  " + b)
    return not bad


if a.collide is not None:
    collide(a)
    sys.exit(0)
if a.identity:
    sys.exit(0 if identity(a) else 1)
if not a.order or not a.runs:
    ap.error("give <order.ld> and hwproject runs, or --collide / --identity")

where, secs = {}, set()
for o in sorted(glob.glob(a.objdir + "/**/*.o", recursive=True)):
    base = os.path.basename(o)
    for l in run(a.tools + "objdump", "-t", o).splitlines():
        p = l.split()
        if len(p) >= 5 and p[-3].startswith(".text"):
            where.setdefault(p[-1], (base, p[-3]))
    for l in run(a.tools + "objdump", "-h", o).splitlines():
        p = l.split()
        if len(p) >= 3 and p[1].startswith(".text"):
            secs.add((base, p[1]))

rules, stale = set(), []
for l in open(a.order):
    m = re.match(r"\s*\*(\S+?)\((\S+?)\)", l)
    if m:
        rules.add((m.group(1), m.group(2)))
        if m.group(1) != "_kos_startup.o" and (m.group(1), m.group(2)) not in secs:
            stale.append("%s(%s)" % (m.group(1), m.group(2)))
print("%s: %d rules, %d naming no current section%s" % (
    os.path.basename(a.order), len(rules), len(stale), (": " + " ".join(stale[:8])) if stale else ""))

for name in a.runs:
    E = os.path.join(a.evidence_root, name)
    ELF = E + "/re4dc-game.elf"
    nm = run(a.tools + "nm", ELF).splitlines()
    nmc = run(a.tools + "nm", "-C", ELF).splitlines()
    dem2m = {}
    for m, d in zip(nm, nmc):
        pm, pd = m.split(None, 2), d.split(None, 2)
        if len(pm) == 3 and len(pd) == 3:
            dem2m.setdefault(pd[2], pm[2])
    L = open(E + "/proj/rep/functions.tsv").read().splitlines()
    h = L[0].split("\t")
    fi, hi = h.index("func"), h.index("hw_ms")
    tot = cov = unk = 0.0
    miss = collections.Counter()
    for l in L[1:]:
        f = l.split("\t")
        if a.exclude and re.search(a.exclude, f[fi]):
            continue
        w = float(f[hi])
        tot += w
        s = where.get(dem2m.get(f[fi], ""))
        if s is None:
            unk += w
        elif s in rules or (s[0], ".text") in rules:
            cov += w
        else:
            miss[f[fi]] += w
    print("  %s: covered %.1f of %.1f hw ms (%.0f%%; placeable %.0f%%); hottest unplaced: %s" % (
        name, cov, tot, 100 * cov / max(tot, 1e-9), 100 * (tot - unk) / max(tot, 1e-9),
        ", ".join("%s %.2f" % (k[:40], v) for k, v in miss.most_common(4))))
