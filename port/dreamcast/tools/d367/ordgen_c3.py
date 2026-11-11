#!/usr/bin/env python3
"""Profile-guided code placement for the game ELF (game30.mk LINK_ORDER=<file>; exact: placement only).

The SH-4's 8 KB instruction cache is direct mapped: code that runs together conflicts when its addresses
meet modulo 8 KB. This writes an ld --section-ordering-file that puts the hot code first in .text, as
call chains clustered to at most --max bytes (HFSort's C3):
  - call edges are exact: every static call site (bsr / bra to another function; jsr / jmp @rN after a
    PC-relative literal load of the target) weighted by its execution count in the run's trace/counts.bin
    (per-instruction counts over the counted ticks), summed over the given hwproject evidence runs;
  - nodes are input sections (a C / C++ function's .text.<name>, an assembler object's whole .text);
    hotness is hw ms from each run's proj/rep/functions.tsv;
  - in decreasing hotness, a node's cluster is appended to the cluster of its most frequent caller while
    the merged cluster stays <= --max bytes; clusters are then placed by density (hotness per byte).
Library code (libc, libgcc, KOS) stays where it is.

r101 square, 2026-09-25 (8 KB clusters from a never-draw and a drawn run): never-draw work -1.25 hw ms
(I-miss 4.67 -> 3.74 ms), every tick drawn -0.94; logic trace STRICT, every decision identical. 4 KB
clusters: -0.77 / -0.97. Hottest-first without clustering: +0.17 / +0.05.

usage: ordgen_c3.py --objdir <OBJDIR of a build with the same code> [--max 8192] [--limit 400000]
                    [--evidence-root D] [--exclude REGEX] [--skip-weight W] -o <out.ld> <hwproject evidence dir name>...
Regenerate after code changes (sections it names that no longer exist are ignored by ld).

--pcs (lane layout30, 2026-11-11): the same order from CONSOLE evidence instead of the model. Hotness = the PC
sampler's share of busy time per input section (every scene weighted equally); call edges = the sampled return
address (PR) when the instruction before it is a call, plus static call sites at a small weight; phases = threads
(tid 1 main / draw, the scene's logic task, KOS service threads; code two threads both use is "shared"). C3 merges
only within a phase and puts the callee's cluster BEFORE its caller (innermost first). Clusters are then laid out
greedily: of the next --lookahead clusters by density, the one whose hot lines land on the least-used cache sets of
its own phase (and of the call partners already placed) goes next, so code that alternates in one loop does not share
sets and the main and logic threads' code interleave in the cache index space. Hot archive members (KOS, libc, libm,
libgcc: memcpy / memset are ~2.5% of console samples) are placed too (*libc.a:libc_a-memcpy.o(.text)).
usage: ordgen_c3.py --pcs '<dir>/*-snap*.pcs' --pcs-elf <profiled ELF> --objdir <that build's OBJDIR>
                    [--pcs-scenes a,b,..] [--report R.txt] -o <out.ld>"""
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
ap.add_argument("--max", type=int, default=8192, help="largest cluster in bytes (the I-cache size)")
ap.add_argument("--limit", type=int, default=400000, help="bytes of hot code to place")
ap.add_argument("--pcs", nargs="*", default=[], help="console PC-sampler dumps (globs); switches to console evidence")
ap.add_argument("--pcs-elf", help="the ELF the samples were taken on (built from --objdir)")
ap.add_argument("--pcs-scenes", default="", help="comma list of scene names (file name before -snap) to use")
ap.add_argument("--archives", default="/root/work/kos-re4dc-d367/lib/dreamcast/libkallisti.a,"
                "/opt/toolchains/dc/sh-elf/sh-elf/lib/libc.a,/opt/toolchains/dc/sh-elf/sh-elf/lib/libm.a,"
                "/opt/toolchains/dc/sh-elf/lib/gcc/sh-elf/15.2.0/libgcc.a",
                help="archives whose hot members may be placed (comma list)")
ap.add_argument("--kos-startup", default="/root/work/kos-re4dc-d367/lib/dreamcast/_kos_startup.o")
ap.add_argument("--static-weight", type=float, default=0.05,
                help="weight of a static call site between two sampled sections, x the cooler one's share")
ap.add_argument("--min-hot", type=float, default=0.004, help="smallest share (percent of busy time) to place")
ap.add_argument("--lookahead", type=int, default=20)
ap.add_argument("--beta", type=float, default=4.0, help="extra conflict weight for call partners")
ap.add_argument("--no-callee-first", action="store_true")
ap.add_argument("--no-avoid", action="store_true", help="place clusters by density only")
ap.add_argument("--report", default="")
ap.add_argument("--evidence-root", default=os.environ.get("HWM_EVIDENCE", "/mnt/d/Flycast-Evidence/re4-dreamcast"))
ap.add_argument("--tools", default="/opt/toolchains/dc/sh-elf/bin/sh-elf-")
ap.add_argument("--exclude", default="",
                help="regex of functions (demangled) whose hw ms is not hardware work, e.g. the pacing spin "
                     "re4dc_pace_end|re4dc_vi_retrace_count (a PACE_FORCE run books Flycast's wait there)")
ap.add_argument("--skip-weight", type=float, default=0.0,
                help="also add W x the hw ms of the run's skipped ticks (proj-skip/rep/functions.tsv, from "
                     "perf-20261004 modesplit.sh): more weight for the code of never-drawn ticks (logic)")
ap.add_argument("-o", "--out", required=True)
ap.add_argument("runs", nargs="*")
a = ap.parse_args()
TOOLS = a.tools


def pcs_order(a):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import ordpcs as P
    P.TOOLS = a.tools
    elf = P.Elf(a.pcs_elf)
    archives = [x for x in a.archives.split(",") if x]
    objs = P.Objects(a.objdir, archives, a.tools)
    L = P.Layout(elf, objs)
    files = sorted({f for g in a.pcs for f in glob.glob(g)})
    scenes = set(s for s in a.pcs_scenes.split(",") if s) or None
    ev = P.Evidence(L, files, scenes, a.exclude)
    placeable = {k for k in L.start if not k[0].startswith("_kos_startup")}
    hot = {k: w for k, w in ev.hot.items() if k in placeable}
    # caller edges: sampled return edges + static call sites between sampled sections
    callers = collections.defaultdict(collections.Counter)
    for (x, y), w in ev.edges.items():
        if x in placeable and y in placeable:
            callers[y][x] += w
    for x, y in sorted(ev.static):
        if x in hot and y in hot:
            callers[y][x] += a.static_weight * min(hot[x], hot[y])
    grp = {k: ev.group(k) for k in hot}
    size = {k: L.size[k] for k in hot}
    # C3 within a phase, callee cluster first
    cluster = {k: [k] for k in hot}
    cof = {k: k for k in hot}
    csize = dict(size)
    chot = dict(hot)
    cgrp = dict(grp)
    merges = 0
    for k, w in sorted(hot.items(), key=lambda kv: -kv[1]):
        if w < a.min_hot or not callers[k]:
            continue
        c = max(callers[k].items(), key=lambda kv: (kv[1], kv[0]))[0]
        if c not in cof:
            continue
        A, B = cof[c], cof[k]
        if A == B or csize[A] + csize[B] > a.max or not P.compatible(cgrp[A], cgrp[B]):
            continue
        cluster[A] = cluster[B] + cluster[A] if not a.no_callee_first else cluster[A] + cluster[B]
        for n in cluster[B]:
            cof[n] = A
        csize[A] += csize[B]
        chot[A] += chot[B]
        cgrp[A] = cgrp[A] if cgrp[A] != "shared" else cgrp[B]
        del cluster[B], csize[B], chot[B], cgrp[B]
        merges += 1
    pool = sorted((c for c in cluster if chot[c] >= a.min_hot), key=lambda c: (-(chot[c] / max(csize[c], 32)), c))
    # greedy placement over the cache sets
    st = subprocess.run([a.tools + "objdump", "-h", a.kos_startup], capture_output=True, text=True).stdout
    m = re.search(r"\s\.text\s+([0-9a-f]+)", st)
    cursor = P.TEXT_BASE + (int(m.group(1), 16) if m else 0)
    occ = {g: [0.0] * P.SETS for g in ("main", "logic", "svc", "shared")}
    placed_lines, addr, seq = {}, {}, []
    partners = collections.defaultdict(set)
    for (x, y) in sorted(ev.edges):
        partners[x].add(y)
        partners[y].add(x)

    def seen(g, s):
        if g == "shared":
            return occ["main"][s] + occ["logic"][s] + occ["svc"][s] + occ["shared"][s]
        return occ[g][s] + occ["shared"][s]

    def lay(c, cur):
        out = []
        for k in cluster[c]:
            al = objs.secs[k]["align"]
            cur = (cur + al - 1) // al * al
            out.append((k, cur, P.line_weights(ev, k, cur, size[k])))
            cur += size[k]
        return out, cur

    total = 0
    while pool and total < a.limit:
        best = None
        for i, c in enumerate(pool[:max(1, a.lookahead if not a.no_avoid else 1)]):
            lines, end = lay(c, cursor)
            cost = 0.0
            for k, ad, lw in lines:
                g = grp[k]
                for s, w in lw.items():
                    cost += w * seen(g, s)
                for p in partners[k]:
                    if p in placed_lines:
                        af = P.affinity(ev, k, p)
                        pl = placed_lines[p]
                        for s, w in lw.items():
                            cost += a.beta * af * w * pl.get(s, 0.0)
            score = (cost / max(chot[c], 1e-9), i)
            if best is None or score < best[0]:
                best = (score, c, lines, end)
        _, c, lines, end = best
        pool.remove(c)
        for k, ad, lw in lines:
            addr[k] = ad
            placed_lines[k] = lw
            g = grp[k]
            for s, w in lw.items():
                occ[g][s] += w
            seq.append(k)
        total += end - cursor
        cursor = end
    rules = []
    for k in seq:
        obj, sec = k
        if k in L.comdat and sec != ".text":
            rules.append("*(%s)" % sec)
        else:
            rules.append("*%s(%s)" % (objs.rel[obj], sec))
    cov = sum(hot[k] for k in seq)
    with open(a.out, "w") as f:
        f.write("/* ordgen_c3.py --pcs: clusters <= %d B by thread phase, callee first, set-aware placement; %d input "
                "sections, %d B, %.1f%% of %.1f%% mapped console busy time (unmapped %.1f%%); scenes: %s; ELF %s */\n" % (
                    a.max, len(rules), total, cov, sum(ev.hot.values()), sum(ev.unmapped.values()),
                    " ".join("%s:%d" % (s, ev.nsamples[s]) for s in ev.scenes), os.path.basename(a.pcs_elf)))
        f.write("/* %s */\n" % " ".join(os.path.basename(x) if i == 0 else x for i, x in enumerate(sys.argv)).replace("*/", "* /"))
        f.write(".text : {\n  *_kos_startup.o(.text)\n")
        for r in rules:
            f.write("  %s\n" % r)
        f.write("}\n")
    print("%s: %d sections, %d B, %.1f%% of busy time placed, %d merges, %d sampled edges, %d static edges" % (
        a.out, len(rules), total, cov, merges, len(ev.edges), len(ev.static)))
    if a.report:
        names = P.demangle({L.name[k] for k in hot})
        nm = lambda k: names.get(L.name[k], L.name[k])[:70]
        # the same node set on both sides: the sections this order places
        before, bp = P.conflict(ev, lambda k: L.start.get(k) if k in addr else None, a.beta)
        after, ap_ = P.conflict(ev, lambda k: addr.get(k), a.beta)
        with open(a.report, "w") as R:
            R.write("ordgen_c3.py --pcs report (layout proxy, NOT timing)\n")
            R.write("ELF %s; objdir %s\nscenes %s\n" % (a.pcs_elf, a.objdir, dict(ev.nsamples)))
            R.write("mapped sections %d (%d of %d text bytes), overlapping claims dropped %d, unmapped busy %.2f%%: %s\n" % (
                len(L.start), L.covered()[0], L.covered()[1], L.overlaps, sum(ev.unmapped.values()),
                ", ".join("%s %.2f" % (n, w) for n, w in ev.unmapped.most_common(6))))
            gt = collections.Counter()
            for k, w in hot.items():
                gt[grp[k]] += w
            R.write("busy time by phase: %s\n" % ", ".join("%s %.1f%%" % kv for kv in gt.most_common()))
            R.write("placed: %d sections, %d B, %.1f%% of busy time; %d clusters, %d C3 merges\n\n" % (
                len(seq), total, cov, len([c for c in cluster if chot[c] >= a.min_hot]), merges))
            R.write("conflict proxy (sum over hot node pairs sharing a cache set, same phase; lower is better):\n")
            for g in sorted(set(before) | set(after)):
                R.write("  %-7s before %8.3f  after (predicted) %8.3f  (%+.0f%%)\n" % (
                    g, before[g], after[g], 100.0 * (after[g] - before[g]) / max(before[g], 1e-9)))
            R.write("  %-7s before %8.3f  after (predicted) %8.3f  (%+.0f%%)\n\n" % (
                "all", sum(before.values()), sum(after.values()),
                100.0 * (sum(after.values()) - sum(before.values())) / max(sum(before.values()), 1e-9)))
            R.write("review world-draw pairs, before:\n%s\n" % "\n".join(P.named_pairs(L, lambda k: L.start.get(k))))
            R.write("review world-draw pairs, after (predicted):\n%s\n\n" % "\n".join(P.named_pairs(L, lambda k: addr.get(k))))
            R.write("top conflicting pairs before:\n")
            for (x, y), c in bp.most_common(12):
                R.write("  %7.3f  %s  <->  %s\n" % (c, nm(x), nm(y)))
            R.write("top conflicting pairs after (predicted):\n")
            for (x, y), c in ap_.most_common(12):
                R.write("  %7.3f  %s  <->  %s\n" % (c, nm(x), nm(y)))
            R.write("\nclusters in placement order (first 60): address, phase, bytes, busy %, members (callee first)\n")
            done = set()
            for k in seq:
                c = cof[k]
                if c in done:
                    continue
                done.add(c)
                if len(done) > 60:
                    break
                R.write("  %08x %-6s %5d B %5.2f%%  %s\n" % (addr[cluster[c][0]], cgrp[c], csize[c], chot[c],
                                                           " | ".join(nm(n) for n in cluster[c][:8]) +
                                                           (" | +%d" % (len(cluster[c]) - 8) if len(cluster[c]) > 8 else "")))
        print("report %s: conflict proxy before %.3f after %.3f" % (a.report, sum(before.values()), sum(after.values())))


if a.pcs:
    pcs_order(a)
    sys.exit(0)
if not a.runs:
    ap.error("give hwproject evidence runs or --pcs")


def run(*args):
    return subprocess.run(list(args), capture_output=True, text=True, check=True).stdout


# objects: symbol (as stored, leading underscore) -> input section; input section -> size
where, secsize = {}, {}
for o in sorted(glob.glob(a.objdir + "/**/*.o", recursive=True)):
    base = os.path.basename(o)
    for l in run(TOOLS + "objdump", "-t", o).splitlines():
        p = l.split()
        if len(p) >= 5 and p[-3].startswith(".text"):
            where.setdefault(p[-1], (base, p[-3]))
    for l in run(TOOLS + "objdump", "-h", o).splitlines():
        p = l.split()
        if len(p) >= 3 and p[1].startswith(".text"):
            secsize[(base, p[1])] = int(p[2], 16)

hot = collections.Counter()
edge = collections.Counter()
rx = re.compile(r"^\s*([0-9a-f]+):\s+(\S+)\s+(.*)$")
lit = re.compile(r"mov\.l\s+.*?,(r\d+)\s+!\s*([0-9a-f]+)")
for name in a.runs:
    E = os.path.join(a.evidence_root, name)
    ELF = E + "/re4dc-game.elf"
    raw = open(E + "/trace/counts.bin", "rb").read()
    cnt = struct.unpack("<%dI" % (len(raw) // 4), raw)
    nm = run(TOOLS + "nm", "-n", ELF).splitlines()
    nmc = run(TOOLS + "nm", "-n", "-C", ELF).splitlines()
    assert len(nm) == len(nmc)
    starts, names, dem2m, start_of = [], [], {}, {}
    for m, d in zip(nm, nmc):
        pm = m.split(None, 2)
        if len(pm) != 3 or pm[1] not in ("t", "T", "W"):
            continue
        ad = int(pm[0], 16)
        starts.append(ad)
        names.append(pm[2])
        start_of.setdefault(ad, pm[2])
        dem2m.setdefault(d.split(None, 2)[2], pm[2])

    def fn(ad):
        i = bisect.bisect_right(starts, ad) - 1
        return names[i] if i >= 0 else None

    reps = [("/proj/rep/functions.tsv", 1.0)]
    if a.skip_weight:
        reps.append(("/proj-skip/rep/functions.tsv", a.skip_weight))
    for rep, wt in reps:
        L = open(E + rep).read().splitlines()
        h = L[0].split("\t")
        fi, hi = h.index("func"), h.index("hw_ms")
        for l in L[1:]:
            f = l.split("\t")
            if a.exclude and re.search(a.exclude, f[fi]):
                continue
            m = dem2m.get(f[fi])
            if m:
                hot[m] += wt * float(f[hi])
    recent = {}
    for line in run(TOOLS + "objdump", "-d", "--no-show-raw-insn", ELF).splitlines():
        mm = rx.match(line)
        if not mm:
            continue
        pc, op, args = int(mm.group(1), 16), mm.group(2), mm.group(3)
        if op == "mov.l":
            lm = lit.search(line)
            if lm:
                recent[lm.group(1)] = (int(lm.group(2), 16), pc)
            continue
        tgt = None
        if op in ("jsr", "jmp"):
            r = args.split("@")[-1].strip()
            if r in recent and pc - recent[r][1] < 64:
                tgt = recent[r][0]
        elif op in ("bsr", "bra"):
            t = re.search(r"([0-9a-f]+) <", args)
            if t:
                tgt = int(t.group(1), 16)
        if tgt is None or tgt not in start_of:
            continue
        caller, callee = fn(pc), start_of[tgt]
        if caller is None or caller == callee:
            continue
        i = (pc - 0x8c000000) >> 1
        c = cnt[i] if 0 <= i < len(cnt) else 0
        if c:
            edge[(caller, callee)] += c

nhot = collections.Counter()
for s, w in hot.items():
    if s in where:
        nhot[where[s]] += w
callers = collections.defaultdict(collections.Counter)
for (x, y), w in edge.items():
    kx, ky = where.get(x), where.get(y)
    if kx and ky and kx != ky:
        callers[ky][kx] += w

cluster = {k: [k] for k in nhot}
cof = {k: k for k in nhot}
csize = {k: secsize.get(k, 0) for k in nhot}
chot = dict(nhot)
merges = 0
for k, w in nhot.most_common():
    if w < 0.002 or not callers[k]:
        continue
    c = max(callers[k].items(), key=lambda kv: kv[1])[0]
    if c not in cof:
        continue
    A, B = cof[c], cof[k]
    if A == B or csize[A] + csize[B] > a.max:
        continue
    cluster[A] += cluster[B]
    for n in cluster[B]:
        cof[n] = A
    csize[A] += csize[B]
    chot[A] += chot[B]
    del cluster[B], csize[B], chot[B]
    merges += 1

order = sorted(cluster, key=lambda c: (-(chot[c] / max(csize[c], 32)), c))
rules, total, cov = [], 0, 0.0
for c in order:
    if chot[c] < 0.002:
        continue
    if total + csize[c] > a.limit:
        break
    rules += ["*%s(%s)" % n for n in cluster[c]]
    total += csize[c]
    cov += chot[c]
with open(a.out, "w") as f:
    f.write("/* ordgen_c3.py: clusters <= %d B, %d input sections, %d B, %.2f of %.2f hw ms; runs: %s%s */\n" % (
        a.max, len(rules), total, cov, sum(hot.values()), " ".join(a.runs),
        ("; excluded: " + a.exclude if a.exclude else "") + ("; skip weight %g" % a.skip_weight if a.skip_weight else "")))
    f.write(".text : {\n  *_kos_startup.o(.text)\n")
    for r in rules:
        f.write("  %s\n" % r)
    f.write("}\n")
print("%s: %d sections, %d B, %.2f of %.2f hw ms placed, %d merges, %d call edges" % (
    a.out, len(rules), total, cov, sum(hot.values()), merges, len(edge)))
