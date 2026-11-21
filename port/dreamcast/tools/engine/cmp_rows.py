#!/usr/bin/env python3
"""cmp_rows.py: one measure for both sides of the old-port / engine comparison (lane eng-cmp1, 2026-11-21).

    cmp_rows.py engine <serial.txt> [--json out]
    cmp_rows.py old <run-output.txt> --from F --to F [--json out]

Reads logs only. Per presented picture it gives two numbers:
  interval  display fields between this picture's flip and the previous picture's flip (59.94 fields a second);
  work      CPU time spent making the picture, waits excluded (ms).
Summaries: mean, p99 (nearest rank), worst, count over two fields (interval) / over 33.3 ms (work), and pictures a
second presented = 59.94 / mean interval.

Engine (console disc, E1-family scenes LEON, HILL, FIGHT): the image's own ROW lines of pictures 41 to 640, split by the
selector's `CDISC RUN <n> <scene>` lines. interval = `fields`; work = frame - wait - pvr (the selector's "busy": the
frame less the pacer's wait and the wait for the graphics chip). One picture a logic tick.

Old port (release recipe + DBG_WARP=1 + PACE_HOLD_LOG=2 + GAME_TICK_LOG=1; read_log.py output):
  `PT f=<f>-<f> n=1 ... remain=R/R ...` one per game iteration (tick_log.cpp): R = microseconds from the iteration's start
      (after the pacer's begin) to DRAW REMAIN: all logic and drawing work, before the vblank wait (src/game/main.cpp);
  `PACE pic sub= tgt= flip=F ticks=K lat_us=` one per presented picture (pace_present.cpp): interval = F - previous F;
      K = the pacer's tick count when the picture was submitted. K maps to the game frame f of the iteration that made
      it by a constant offset (the pacer re-anchors at room entry): taken as the most common (last PT f before the
      line) - K over the run.
  A picture's work = the sum of R over the iterations since the previous presented picture (an iteration whose picture
  the pacer dropped still ran its logic and is paid by the next presented one).
  --from/--to select pictures whose iteration's game frame f is in the window (the warp rig's act frames are on the
  same clock: pad frame = f - 171 on these fixtures).
Every number either side gives here is a Flycast number unless the log came from a console.
"""
import argparse, collections, json, re

FIELD_HZ = 59.94


def summ(v, over):
    s = sorted(v); n = len(s)
    if not n:
        return dict(n=0)
    return dict(n=n, mean=round(sum(v) / n, 3), p99=round(s[min(n - 1, int(0.99 * n))], 3), worst=round(s[-1], 3),
                over=sum(1 for x in v if x > over))


def engine(path):
    scenes = {}; cur = None
    for line in open(path, encoding='latin-1'):
        m = re.match(r'CDISC RUN \d+ (\S+) ', line)
        if m:
            cur = m.group(1); scenes[cur] = []; continue
        if cur and line.startswith('ROW '):
            f = line.split()
            if len(f) % 2:
                continue
            try:
                d = {f[i]: int(f[i + 1]) for i in range(2, len(f) - 1, 2)}; d['n'] = int(f[1])
            except ValueError:
                continue
            if 'frame' in d and 'fields' in d:
                scenes[cur].append(d)
    out = {}
    for name, rows in scenes.items():
        R = [r for r in rows if 41 <= r['n'] <= 640]
        if len(R) != 600 or len({r['n'] for r in R}) != 600:
            continue
        iv = [r['fields'] for r in R]
        work = [(r['frame'] - r['wait'] - r.get('pvr', 0)) / 1000 for r in R]
        si = summ(iv, 2)
        out[name] = dict(pictures=len(R), interval_fields=si, fps=round(FIELD_HZ / si['mean'], 2),
                         work_ms=summ(work, 33.3), draw_ms=summ([r['draw'] / 1000 for r in R], 14.0),
                         logic_ms=summ([r['tick'] / 1000 for r in R], 33.3),
                         window='pictures 41-640 (engine ticks 41-640, one picture a tick)')
    return out


def old(path, lo, hi):
    rem = {}; tot = {}; pics = []; last_f = None; overruns = 0; act = None; bad_pic = 0
    for line in open(path, encoding='latin-1'):
        if line.startswith('[LOG OVERRUN'):
            overruns += 1
        m = re.match(r'warp: act \d+ .* pad=(\d+) ', line)
        if m and act is None:
            act = [int(m.group(1)), None]   # the first act: its pad frame, then the next picture's tick count
        if line.startswith('PACE pic ') and act is not None and act[1] is None:
            act[1] = int(re.search(r' ticks=(\d+)', line).group(1))
        if line.startswith('PT f='):
            m = re.match(r'PT f=(\d+)-(\d+) n=(\d+)', line)
            if not m or m.group(1) != m.group(2) or m.group(3) != '1':
                continue
            f = int(m.group(2)); last_f = f
            r = re.search(r' remain=(\d+)/', line)
            t = re.search(r' total=(\d+)/', line)
            if r: rem[f] = int(r.group(1))
            if t: tot[f] = int(t.group(1))
        elif line.startswith('PACE pic '):
            m = re.match(r'PACE pic sub=(\d+) tgt=(\d+) flip=(\d+) ticks=(\d+) lat_us=(\d+)\s*$', line)
            if not m:   # a line cut by another writer (seen in the interpreter build): counted, not guessed
                bad_pic += 1; continue
            d = dict(zip(('sub', 'tgt', 'flip', 'ticks', 'lat_us'), map(int, m.groups())))
            d['last_f'] = last_f; pics.append(d)
    offs = collections.Counter(p['last_f'] - p['ticks'] for p in pics if p['last_f'] is not None)
    # Without PT lines (a build without GAME_TICK_LOG): the first warp act line. Its pad frame P is game frame P + 170
    # for the picture printed next (eng-cmp1 calibration on the PT runs: pad frame = frame - 171, printed one
    # iteration later); with PT lines both are reported as a check.
    act_off = act[0] + 170 - act[1] if act and act[1] is not None else None
    off = offs.most_common(1)[0][0] if offs else act_off
    for p in pics:
        p['f'] = p['ticks'] + off
    win = []; missing = 0
    for a, b in zip(pics, pics[1:]):
        if not lo <= b['f'] <= hi:
            continue
        w = 0.0
        for f in range(a['f'] + 1, b['f'] + 1):
            if f in rem: w += rem[f] / 1000
            else: missing += 1
        win.append(dict(f=b['f'], interval=b['flip'] - a['flip'], work=w, iters=b['f'] - a['f']))
    si = summ([p['interval'] for p in win], 2)
    frames = [f for f in rem if lo <= f <= hi]
    return dict(window='game frames %d-%d' % (lo, hi), frames=len(frames), pictures=len(win),
                interval_fields=si, fps=round(FIELD_HZ / si['mean'], 2) if si.get('n') else None,
                work_ms=summ([p['work'] for p in win], 33.3),
                work_per_iteration_ms=summ([rem[f] / 1000 for f in frames], 33.3),
                iteration_total_ms=summ([tot[f] / 1000 for f in frames if f in tot], 33.3),
                pictures_covering_2plus_iterations=sum(1 for p in win if p['iters'] > 1),
                missing_iterations=missing, tick_offset=off, tick_offset_votes=offs.most_common(3),
                tick_offset_from_first_act=act_off,
                pace_pic_lines=len(pics), pace_pic_lines_cut=bad_pic, log_overruns=overruns)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('side', choices=['engine', 'old']); ap.add_argument('log')
    ap.add_argument('--from', dest='lo', type=int); ap.add_argument('--to', dest='hi', type=int)
    ap.add_argument('--json')
    a = ap.parse_args()
    res = engine(a.log) if a.side == 'engine' else old(a.log, a.lo, a.hi)
    txt = json.dumps(res, indent=1)
    if a.json:
        open(a.json, 'w').write(txt + '\n')
    print(txt)


if __name__ == '__main__':
    main()
