#!/usr/bin/env python3
"""rr_speed.py <ref dir> <cand dir> [--tol-ms X] [--tol-pct P] [--scenes a,b,..]   (lane guards28, 2026-10-28)

Release-to-release speed gate: compares the SH-4 hardware-model projection (MODELLED hw ms per drawn frame, CPU side)
of the candidate against the live release on the benchmark scenes. Each dir holds hwmodel-<label>-<scene>/proj/
projection.txt (rr-speed-hw.sh). A scene FAILS when cand > ref + max(tol_ms, tol_pct% of ref). A scene missing on
either side FAILS (a gate that did not measure must not pass). Prints one row per scene and a last line
"SPEED PASS|FAIL ..." that rr-judge.py reads. Exit 0 PASS, 1 FAIL.
Note: this is the CPU model only. GPU-side regressions (more vertices / TA load with the CPU flat, e.g. n256 in Test 24)
need the cache-model Flycast or console row; see the README.
"""
import re
import sys
from pathlib import Path

SCENES = ['cross', 'bell', 'farm', 'house', 'r11c']


def arg(name, default, cast=float):
    return cast(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default


def ms(d, scene):
    hits = sorted(Path(d).glob(f'hwmodel-*-{scene}/proj/projection.txt'))
    if not hits:
        return None
    m = re.search(r'hardware projection\s+([\d.]+) ms', hits[-1].read_text(errors='replace'))
    return float(m.group(1)) if m else None


def main():
    pos = [a for i, a in enumerate(sys.argv[1:], 1) if not a.startswith('--') and sys.argv[i - 1] not in ('--tol-ms', '--tol-pct', '--scenes')]
    ref, cand = pos[0], pos[1]
    tol_ms, tol_pct = arg('--tol-ms', 1.0), arg('--tol-pct', 3.0)
    scenes = arg('--scenes', ','.join(SCENES), str).split(',')
    print(f'ref  {ref}\ncand {cand}\n(SH-4 hw model, MODELLED, hw ms per drawn frame; tolerance max({tol_ms:g} ms, {tol_pct:g}%))')
    print('| scene | ref | cand | delta | limit | result |\n|---|---|---|---|---|---|')
    bad, parts = [], []
    for s in scenes:
        a, b = ms(ref, s), ms(cand, s)
        if a is None or b is None:
            bad.append(s)
            parts.append(f'{s} not measured')
            print(f'| {s} | {a} | {b} | - | - | FAIL (not measured) |')
            continue
        lim = max(tol_ms, a * tol_pct / 100.0)
        ok = b - a <= lim
        if not ok:
            bad.append(s)
        parts.append(f'{s} {a:.1f}->{b:.1f} ({b - a:+.1f})')
        print(f'| {s} | {a:.1f} | {b:.1f} | {b - a:+.1f} | +{lim:.1f} | {"PASS" if ok else "FAIL"} |')
    print(('SPEED FAIL (slower or not measured: ' + ' '.join(bad) + '): ' if bad else 'SPEED PASS: ') + ', '.join(parts) + ' ms MODELLED')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
