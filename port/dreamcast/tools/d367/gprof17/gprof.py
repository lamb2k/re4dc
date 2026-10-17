#!/usr/bin/env python3
"""gprof.py: gameplay profile tables (lane gprof17, 2026-10-17). Design: GAMEPLAY-PROFILE-20261017.md.

  gprof.py pcs RUN.pcs SYMS [--ovl SYMS[@DELTA]]... [--out-log run-output.txt] [--skip-s S] [--top N] [--tid T]
  gprof.py hw HWMODEL_DIR... [--top N]

pcs (FLYCAST, emulated guest time): a PC sampler ring dump (read_pcs.py) of a PC_SAMPLER=1 build, ideally with
  PC_SAMPLER_PHASE=1. SYMS is the capture's syms.txt (nm -C format "addr type name") or the ELF itself (needs nm on
  PATH: sh-elf-nm / kos-nm / nm). Every sample counts, so the bucket table and the phase table each sum to the whole
  sampled frame (= 1000 / frames-per-second of the loop markers); idle and waits are their own row. Shared helpers
  (memcpy, matrix maths, sin/cos) are charged to their caller through the sample's PR. Code outside the ELF symbol
  table (enemy modules, st*_*.ovl overlays, heap thunks) shows as "ovl/heap" until its symbols are loaded with
  --ovl: an nm -C listing (or ELF) of the overlay link, optionally with @DELTA (hex) added to every address when the
  overlay was linked at a different base than it ran at.
  Phases: a sample tagged with marker P ran after P; the game stamps the END of a phase (ProcessTickGet(no, name)
  = "name" finished), so a run of samples tagged P that is followed by marker Q belongs to phase Q. Samples after the
  last marker of a frame (before the next FRAME START) are "after <P> (pace/vsync)". Names come from the PCSPH lines
  in --out-log; without them phases print as ids.
hw (MODELLED, SH-4 hardware model, work only plus the wait rows): hwproject functions.tsv bucketed with
  tools/d367/benchmark/bench-split.py (same bucket names as pcs mode). Never mix the two tables' numbers.
"""
import argparse
import bisect
import collections
import importlib.util
import re
import shutil
import statistics
import struct
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('bench_split', HERE.parent / 'benchmark' / 'bench-split.py')
bs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bs)

IDLE = 'idle/wait'
OVL = 'ovl/heap'
FOREIGN = 'outside RAM (BIOS/ROM)'
SHARED = 'shared math/copies'
ORDER = [b for b in bs.ORDER if b != 'kos/sound/idle'] + ['kos/sound', IDLE, OVL, FOREIGN]
# Wait/idle functions: bench-split's WAIT rows plus the KOS idle thread and the vsync/genwait sleeps.
IDLE_RE = re.compile(r'^(main|re4dc_pace_end|re4dc_vi_retrace_count|thd_idle_task|thd_block_now|thd_schedule|'
                     r'genwait_wait|sem_wait\w*|cond_wait\w*|mutex_lock\w*|thd_sleep\w*|vblank_\w*|'
                     r're4dc_\w*(vsync|wait)\w*|pvr_wait_ready|arch_sleep)$')
OVL_GAP = 0x20000  # a PC further than this past the nearest symbol is treated as unknown code (as ch4found who.py)
GAP_W1 = 0xFFFFFFFF


def norm(a):
    return 0x0C000000 | (a & 0xFFFFFF)


class Syms:
    def __init__(self):
        self.s = []

    def load(self, spec):
        path, delta = spec, 0
        if '@' in spec:
            path, d = spec.rsplit('@', 1)
            delta = int(d, 16)
        p = Path(path)
        if p.read_bytes()[:4] == b'\x7fELF':
            nm = next((n for n in ('sh-elf-nm', 'kos-nm', 'nm') if shutil.which(n)), None)
            if not nm:
                sys.exit(f'{path}: an ELF needs nm on PATH (or pass syms.txt)')
            text = subprocess.run([nm, '-C', '-n', str(p)], capture_output=True, text=True, check=True).stdout
        else:
            text = p.read_text(encoding='utf-8', errors='ignore')
        n = 0
        for line in text.splitlines():
            f = line.split(' ', 2)
            if len(f) != 3 or f[1] not in 'TtWw':
                continue
            try:
                a = int(f[0], 16)
            except ValueError:
                continue
            self.s.append((norm(a + delta), f[2].strip()))
            n += 1
        return n

    def done(self):
        self.s.sort()
        self.a = [x for x, _ in self.s]

    def name(self, pc):
        i = bisect.bisect_right(self.a, pc) - 1
        if i < 0 or pc - self.s[i][0] > OVL_GAP:
            return None
        return self.s[i][1]


def short(fn):
    return fn.split('(')[0]


def classify(fn):
    if fn is None:
        return OVL
    s = short(fn)
    if IDLE_RE.match(s):
        return IDLE
    b = bs.bucket(s, '')
    return 'kos/sound' if b == 'kos/sound/idle' else b


def read_pcs(path):
    raw = Path(path).read_bytes()
    hdr = struct.unpack_from('<32I', raw, 0)
    recs, gaps = [], 0
    for off in range(128, len(raw) - 7, 8):
        w0, w1 = struct.unpack_from('<II', raw, off)
        if w1 == GAP_W1:
            gaps += w0
            recs.append(('gap', w0))
        elif w1 & 0x80000000 and not (w1 & 0x70000000):
            recs.append(('frame', w0))
        else:
            recs.append(('s', norm((w0 & 0x7FFFFF) << 1), norm((w1 & 0x7FFFFF) << 1), w0 >> 23, (w1 >> 23) & 31,
                         w1 & 0x10000000, w1 & 0x20000000))
    return hdr, recs, gaps


def phase_names(log):
    names = {}
    if log:
        for m in re.finditer(r'PCSPH id=(\d+) no=(-?\d+) name=([^\r\n]*)',
                             Path(log).read_text(encoding='utf-8', errors='ignore')):
            names[int(m.group(1))] = m.group(3).strip()
    names.setdefault(30, '(phase ids exhausted)')
    names.setdefault(31, '(no marker yet)')
    return names


def label_phases(samples, names):
    """samples: list of tags in time order (one frame-loop span or the whole run). Returns per-sample phase labels."""
    out = [None] * len(samples)
    i = 0
    n = len(samples)
    while i < n:
        j = i
        while j < n and samples[j] == samples[i]:
            j += 1
        p = samples[i]
        pname = names.get(p, f'phase{p}')
        if j < n:
            q = names.get(samples[j], f'phase{samples[j]}')
            lab = f'after {pname} (pace/vsync)' if q == 'FRAME START' else q
        else:
            lab = f'after {pname} (open)'
        for k in range(i, j):
            out[k] = lab
        i = j
    return out


def pcs_mode(a):
    sy = Syms()
    print(f'symbols: {sy.load(a.syms)} from {a.syms}')
    for o in a.ovl or []:
        print(f'symbols: {sy.load(o)} from {o} (overlay)')
    sy.done()
    hdr, recs, gaps = read_pcs(a.pcs)
    hz = hdr[4] or 1000
    phase_src = hdr[17]
    names = phase_names(a.out_log)
    # Frame spans between loop markers; --skip-s drops the first S seconds of samples (boot / warp).
    skip = int(a.skip_s * hz)
    seen = 0
    frames, cur, started = [], [], False
    for r in recs:
        if r[0] == 'gap':
            cur, started = [], False  # a host overrun: drop the broken frame
            continue
        if r[0] == 'frame':
            if started and cur is not None and seen > skip:
                frames.append(cur)
            cur, started = [], True
            continue
        seen += 1
        if started and (a.tid is None or r[3] == a.tid):
            cur.append(r)
    if not frames:
        sys.exit('no complete frames after --skip-s')
    tot = sum(len(f) for f in frames)
    ms_per_sample = 1000.0 / hz
    nf = len(frames)
    per = lambda c: c * ms_per_sample / nf
    flen = sorted(len(f) * ms_per_sample for f in frames)
    p = lambda q: flen[min(len(flen) - 1, int(q * len(flen)))]
    print(f'FLYCAST (emulated guest time): {hz} Hz, {nf} loop frames, {tot} samples, host gaps {gaps} records'
          f'{", tid " + str(a.tid) if a.tid is not None else ""}')
    print(f'sampled frame: mean {per(tot):.2f} ms, p50 {statistics.median(flen):.1f}, p99 {p(0.99):.1f}, '
          f'max {flen[-1]:.1f} ms (check: 1000 / loop fps)')

    cache = {}

    def fn_of(pc):
        if pc not in cache:
            cache[pc] = sy.name(pc)
        return cache[pc]

    bucket_c = collections.Counter()
    fn_c = collections.defaultdict(collections.Counter)
    phase_c = collections.Counter()
    phase_b = collections.defaultdict(collections.Counter)
    # Label over the whole stream (a phase run can cross a loop marker); frames are contiguous between host gaps.
    flat = [r for f in frames for r in f]
    labels = label_phases([r[4] for r in flat], names) if phase_src == 2 else [None] * len(flat)
    if True:
        for r, lab in zip(flat, labels):
            _, pc, pr, tid, st, pcf, prf = r
            if pcf:
                b, fn = FOREIGN, '(outside RAM)'
            else:
                fn = fn_of(pc)
                b = classify(fn)
                if b == SHARED and not prf:  # charge shared helpers to the caller
                    cb = classify(fn_of(pr))
                    if cb not in (SHARED, OVL, IDLE):
                        b = cb
                fn = short(fn) if fn else f'{OVL} {pc & ~0xFFF:08x}'
            bucket_c[b] += 1
            fn_c[b][fn] += 1
            if lab is not None:
                phase_c[lab] += 1
                phase_b[lab][b] += 1

    print('\n| bucket (FLYCAST ms per loop frame) | ms | % |')
    print('|---|---|---|')
    for b in ORDER + sorted(set(bucket_c) - set(ORDER)):
        if bucket_c[b]:
            print(f'| {b} | {per(bucket_c[b]):.2f} | {100.0 * bucket_c[b] / tot:.1f} |')
    print(f'| **sampled frame** | **{per(tot):.2f}** | 100.0 |')
    if bucket_c[OVL] > 0.05 * tot:
        print(f'note: {OVL} is {100.0 * bucket_c[OVL] / tot:.0f}% of the frame: load overlay symbols (--ovl) '
              'before trusting the enemy AI row')

    if phase_src == 2:
        print('\n| game phase (FLYCAST ms per loop frame) | ms | % | top buckets |')
        print('|---|---|---|---|')
        for lab, c in phase_c.most_common():
            tb = ', '.join(f'{b} {per(n):.2f}' for b, n in phase_b[lab].most_common(3))
            print(f'| {lab} | {per(c):.2f} | {100.0 * c / tot:.1f} | {tb} |')
        print(f'| **sampled frame** | **{per(sum(phase_c.values())):.2f}** | 100.0 | |')
    else:
        print(f'\n(no phase table: header stage source = {phase_src}; build with PC_SAMPLER_PHASE=1)')

    if a.top:
        print()
        for b in ORDER + sorted(set(fn_c) - set(ORDER)):
            if fn_c[b]:
                print(f'{b} {per(bucket_c[b]):.2f}: ' +
                      ', '.join(f'{n[:48]} {per(c):.2f}' for n, c in fn_c[b].most_common(a.top)))
        em = collections.Counter()
        for fn, c in fn_c['enemy logic/AI'].items():
            m = re.match(r'(cEm\w+)::', fn)
            if m:
                em[m.group(1)] += c
        if em:
            print('enemy types: ' + ', '.join(f'{k} {per(c):.2f}' for k, c in em.most_common()))


def hw_mode(a):
    print('| bucket (hw ms per frame, MODELLED, SH-4 model) | ' + ' | '.join(Path(d).name for d in a.dirs) + ' |')
    print('|---|' + '---|' * len(a.dirs))
    res = []
    for d in a.dirs:
        import csv
        rows = list(csv.DictReader((Path(d) / 'proj/rep/functions.tsv').open(encoding='utf-8'), delimiter='\t'))
        o, f = collections.Counter(), collections.defaultdict(list)
        for r in rows:
            ms = float(r['hw_ms'])
            b = IDLE if r['func'] in bs.WAIT or IDLE_RE.match(r['func']) else bs.bucket(r['func'], r.get('file', ''))
            b = 'kos/sound' if b == 'kos/sound/idle' else b
            o[b] += ms
            f[b].append((ms, r['func']))
        res.append((d, o, f))
    for b in ORDER:
        if any(o[b] for _, o, _ in res):
            print(f'| {b} | ' + ' | '.join(f'{o[b]:.2f}' for _, o, _ in res) + ' |')
    print('| **total work (no idle/wait)** | ' +
          ' | '.join(f'**{sum(v for k, v in o.items() if k != IDLE):.2f}**' for _, o, _ in res) + ' |')
    print('(shared helpers stay in their own row here: the model has no caller information)')
    if a.top:
        for d, o, f in res:
            print(f'\n{Path(d).name}:')
            for b in ORDER:
                if b in f:
                    print(f'  {b} {o[b]:.2f}: ' + ', '.join(f'{n[:40]} {m:.2f}' for m, n in sorted(f[b], reverse=True)[:a.top]))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='mode', required=True)
    p = sub.add_parser('pcs')
    p.add_argument('pcs')
    p.add_argument('syms')
    p.add_argument('--ovl', action='append')
    p.add_argument('--out-log')
    p.add_argument('--skip-s', type=float, default=0.0)
    p.add_argument('--top', type=int, default=8)
    p.add_argument('--tid', type=int)
    h = sub.add_parser('hw')
    h.add_argument('dirs', nargs='+')
    h.add_argument('--top', type=int, default=0)
    a = ap.parse_args()
    (pcs_mode if a.mode == 'pcs' else hw_mode)(a)


if __name__ == '__main__':
    main()
