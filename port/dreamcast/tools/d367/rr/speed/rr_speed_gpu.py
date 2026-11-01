#!/usr/bin/env python3
"""rr_speed_gpu.py <evidence dir> <ref label> <cand label> [--tol-pct P] [--scenes a,b,..]   (lane guards28, 2026-10-28)

GPU-side half of the release-to-release speed gate (gpu-scene.sh runs; cache-model Flycast, flycast-console cstat build).
Per scene, candidate vs reference:
  SQ->TA bytes per frame  = mean CSTAT sq_flush/f x 32 (each store-queue flush sends one 32-byte burst to the TA)
  TA list bytes           = the TA_STATS peak display-list size of the window (vertices + polygon headers the TA
                            stored: the vertex/poly load; the emulator has no separate vertex counter)
A scene FAILS when either is more than tol_pct (SPEED_GPU_TOL_PCT, default 5) higher, when a side was not measured,
or when the fast run did not reach the scene's room (the QA teleporter list moved). Last line
"SPEED-GPU PASS|FAIL ..." for rr-judge.py. Numbers are labelled cache-model Flycast (not console, not hwmodel).
"""
import re
import sys
from pathlib import Path

SCENES = ['cross', 'bell', 'farm', 'house', 'r11c']
ROOM = {'cross': '101', 'bell': '101', 'farm': '103', 'house': '100', 'r11c': '11c'}


def arg(name, default, cast=float):
    return cast(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default


def kv(line):
    return {k: float(v) for k, v in re.findall(r'(\S+?)=(-?[\d.]+)(?=\s|$)', line)}


def rd(p):
    try:
        return Path(p).read_text(errors='replace').replace('\x00', '')
    except OSError:
        return ''


def measure(ev, x, sc):
    cs = [kv(l) for l in rd(ev / 'stats' / f'{x}-{sc}-cstat.txt').splitlines() if l.startswith('CSTAT frame')]
    cs = [c for c in cs if c.get('ms/f', 0) > 0 and 'sq_flush/f' in c]
    ta = [int(v) for v in re.findall(r'TA window render=\d+ max=(\d+)', rd(ev / 'stats' / f'{x}-{sc}-ta.txt'))]
    ta = ta or [int(v) for v in re.findall(r'TA peak render=\d+ bytes=(\d+)', rd(ev / 'stats' / f'{x}-{sc}-ta.txt'))]
    rooms = re.findall(r'room=([0-9a-f]{3})\b', rd(ev / 'runs' / f'{x}-{sc}-fast' / 'run-output.txt'))
    # Leon died in the window (death demo): the scene is not comparable (cross keys turn on the QA god toggle)
    if any('DIEDEMO' in rd(ev / 'runs' / f'{x}-{sc}-{k}' / 'run-output.txt') for k in ('warm', 'meas')):
        return None, 'died'
    if not cs or not ta:
        return None, rooms[-1] if rooms else '?'
    sq = sum(c['sq_flush/f'] for c in cs) / len(cs) * 32
    return (sq, max(ta), len(cs) * 60), rooms[-1] if rooms else '?'


def main():
    pos = [a for i, a in enumerate(sys.argv[1:], 1) if not a.startswith('--') and sys.argv[i - 1] not in ('--tol-pct', '--scenes')]
    ev, ref, cand = Path(pos[0]), pos[1], pos[2]
    tol = arg('--tol-pct', 5.0)
    scenes = arg('--scenes', ','.join(SCENES), str).split(',')
    print(f'ref {ref}  cand {cand}  ({ev})\n(cache-model Flycast, flycast-console cstat; not console ms; tolerance +{tol:g}%)')
    print('| scene | room ref/cand | SQ->TA B/frame ref | cand | delta | TA list B ref | cand | delta | frames | result |')
    print('|---|---|---|---|---|---|---|---|---|---|')
    bad, parts = [], []
    for s in scenes:
        (a, ra), (b, rb) = measure(ev, ref, s), measure(ev, cand, s)
        want = ROOM.get(s)
        if a is None or b is None or (want and (ra != want or rb != want)):
            bad.append(s)
            why = ('Leon died in the window' if 'died' in (ra, rb) else 'not measured') if a is None or b is None \
                else f'wrong room ({ra}/{rb}, want {want})'
            parts.append(f'{s} {why}')
            print(f'| {s} | {ra}/{rb} | - | - | - | - | - | - | - | FAIL ({why}) |')
            continue
        dq, dt = (b[0] / a[0] - 1) * 100, (b[1] / a[1] - 1) * 100
        ok = dq <= tol and dt <= tol
        if not ok:
            bad.append(s)
        parts.append(f'{s} SQ {dq:+.1f}% TA {dt:+.1f}%')
        print(f'| {s} | {ra}/{rb} | {a[0]:.0f} | {b[0]:.0f} | {dq:+.1f}% | {a[1]} | {b[1]} | {dt:+.1f}% | {a[2]}/{b[2]} | {"PASS" if ok else "FAIL"} |')
    print(('SPEED-GPU FAIL (more GPU work or not comparable: ' + ' '.join(bad) + '): ' if bad else 'SPEED-GPU PASS: ') + ', '.join(parts)
          + ' (cache-model Flycast)')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
