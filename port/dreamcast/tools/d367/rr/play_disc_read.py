#!/usr/bin/env python3
"""play_disc_read.py: PLAY-DISC-READ gate (lane coldread27, 2026-11-02; report-only until the coordinator arms it).

  play_disc_read.py [--ms N] [--json out] <run-output.txt | evidence dir>...

Workspace rule (graphics memory): disc re-reads during gameplay are gaps that fail a check. Console report: El Gigante
(r119) falls to 2.7 fps after he breaks objects (cold em2b motion keys + Leon clips read synchronously in EmMgr.move /
Player). This gate reads the DISCRD lines the game already logs (DISC_READ_METER=1: QA discs, census twins built with
it) and fails a run when a GAMEPLAY one-second window blocked the game thread (or a re4-task) on the disc for more than
--ms ms per second (default 100, Flycast; console read rates are higher, so the console threshold is lower).

A window is the PACE vmu line of that second (win_vb vblanks); its DISCRD line and MOTSTAT line follow it. Windows that
are NOT gameplay and are skipped:
  - room loads: the windows a "DISCRD: room=... load_ms=N" line covers (walked back from that line by N ms),
  - the room-entry texture preload (a "native texture preload: ... us=N" line with N >= 200 ms in the window),
  - the entry settle: windows drawing <= 2 frames in the 10 s after a room line or a warp placement,
  - route movies (a "route movie start" .. "route movie terminal" span),
  - windows with no PACE vmu line before them (boot / title).
Builds from lane coldread27 on tag each DISCRD window line " phase=play|load|movie" (dvd_read_safe.cpp) and, with
DISC_READ_LOG=2, list the files read per window ("DRF:" lines); a tagged window is judged by its tag, the heuristics
above only serve older logs.
Exit 1 when any run has a gameplay window above the threshold (report-only callers ignore the exit code)."""
import argparse, json, os, re, sys

PACE = re.compile(r'^PACE vmu t=(\d+) win_vb=(\d+) drawn=(\d+)')
WIN = re.compile(r'^DISCRD: window_ms=(\d+) reads=(\d+) kb=(\d+) block_ms=(\d+) .*other=(\S+)(?: phase=(\w+))?')
DRF = re.compile(r'^DRF: phase=\w+ file=(\S+) reads=(\d+) kb=(\d+) ms=(\d+)(?: us=\d+)?(?: open_us=(\d+))? thr=(\S+)')
ROOM = re.compile(r'^DISCRD: room=([0-9a-f]+) load_ms=(\d+)')
MOT = re.compile(r'^MOTSTAT: window_ms=\d+ misses=(\d+) evictions=(\d+) kb=(\d+) .*heap4=(-?\d+)')
PRE = re.compile(r'^native texture preload: .* us=(\d+)')
WARP = re.compile(r'warp: placed room=([0-9a-f]{3})|room enter.*room=([0-9a-f]{3})|phase=enter room=([0-9a-f]{3})')


def windows(path):
    try:
        L = open(path, errors='replace').read().replace('\x00', '').splitlines()
    except OSError:
        return []
    ws, cur, room, movie, settle, pend = [], None, '?', False, 10000, False
    for l in L:
        m = WARP.search(l)
        if m:
            room = next(g for g in m.groups() if g)
        if l.startswith('route movie start'):
            movie = True
        if l.startswith('route movie terminal'):
            movie = False
        m = PACE.match(l)
        if m:
            cur = dict(t=int(m.group(1)), ms=int(m.group(2)) * 1000 // 60, drawn=int(m.group(3)), room=room,
                       block=0, reads=0, kb=0, other='-', miss=None, mkb=None, heap4=None, load=False, movie=movie, phase=None, files=[])
            if pend or (settle > 0 and cur['drawn'] <= 2):   # pend: a load / preload line logged before this window's PACE line
                pend = False
                cur['load'] = True
            settle -= cur['ms']
            ws.append(cur)
            continue
        m = ROOM.match(l)
        if m:
            room = m.group(1)
            left = int(m.group(2))
            for w in reversed(ws):   # the load ran over the windows before this line
                w['load'] = True
                w['room'] = room
                left -= w['ms']
                if left <= 0:
                    break
            settle, pend = 10000, True   # the room's entry settle: windows that draw <= 2 frames in the next 10 s are entry, not play
            continue
        if m := WARP.search(l):
            settle = 10000
        if cur is None:
            continue
        m = WIN.match(l)
        if m:
            wm = max(1, int(m.group(1)))
            cur.update(block=int(m.group(4)) * 1000 // wm, reads=int(m.group(2)), kb=int(m.group(3)), other=m.group(5),
                       phase=m.group(6))
            continue
        m = DRF.match(l)
        if m:
            cur['files'].append('%s:%sms%s/%sKB/%s' % (m.group(1), m.group(4), '+open%dms' % (int(m.group(5)) // 1000) if m.group(5) else '', m.group(3), m.group(6)))
            continue
        m = PRE.match(l)
        if m and int(m.group(1)) >= 200000:
            pend = True
            continue
        m = MOT.match(l)
        if m:
            cur.update(miss=int(m.group(1)), mkb=int(m.group(3)), heap4=int(m.group(4)))
    for w in ws:   # a phase-tagged build (DISCRD ... phase=) decides directly; the heuristics only serve older logs
        if w['phase']:
            w['load'], w['movie'] = w['phase'] == 'load', w['phase'] == 'movie'
    return ws


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('paths', nargs='+')
    ap.add_argument('--ms', type=int, default=int(os.environ.get('PLAY_DISC_READ_MS', '100')))
    ap.add_argument('--json')
    a = ap.parse_args()
    files = []
    for p in a.paths:
        if os.path.isdir(p):
            for d, _, fs in os.walk(p):
                files += [os.path.join(d, f) for f in fs if f == 'run-output.txt']
        else:
            files.append(p)
    res, bad, metered = [], 0, 0
    for f in sorted(files):
        ws = windows(f)
        has = any(w['block'] or w['reads'] for w in ws)
        if not has:
            continue
        metered += 1
        play = [w for w in ws if not w['load'] and not w['movie'] and w['room'] != '?']   # boot / title windows have no room yet
        over = [w for w in play if w['block'] > a.ms]
        worst = max(play, key=lambda w: w['block']) if play else None
        r = dict(run=f, windows=len(ws), play=len(play), over=len(over),
                 worst=worst and {k: worst[k] for k in ('room', 't', 'block', 'reads', 'kb', 'other', 'miss', 'mkb', 'heap4', 'drawn')},
                 rows=[{k: w[k] for k in ('room', 't', 'block', 'reads', 'kb', 'other', 'miss', 'mkb', 'heap4', 'drawn', 'phase', 'files')} for w in over])
        res.append(r)
        bad += bool(over)
        for w in over:
            # miss / mkb / heap4 stay None in a build without MOTSTAT lines (no motion meter): printed as '-'
            v = {k: ('-' if w[k] is None else w[k]) for k in ('miss', 'mkb', 'heap4')}
            print('PLAY-DISC-READ over room=%s t=%d block_ms/s=%d reads=%d kb=%d motion_misses=%s motion_kb=%s heap4=%s drawn=%d waited=%s files=%s run=%s'
                  % (w['room'], w['t'], w['block'], w['reads'], w['kb'], v['miss'], v['mkb'], v['heap4'], w['drawn'], w['other'],
                     ','.join(w['files'][:4]) or '-', f))
    print('PLAY-DISC-READ %s: %d metered runs, %d with a gameplay window over %d ms/s (Flycast)'
          % ('FAIL' if bad else 'PASS', metered, bad, a.ms))
    if a.json:
        json.dump(dict(pass_=not bad, ms=a.ms, runs=res), open(a.json, 'w'), indent=1)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
