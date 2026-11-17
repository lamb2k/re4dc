#!/usr/bin/env python3
"""lab32_session.py: the scripted console lab session (lane lab32, 2026-11-17). PC side; Python 3 standard library only.

The console boots the lab QA disc (LAB32=1; REMOTE LINK ON), the DreamPi runs `qalink_pi.py serve --review28`, and this
script drives the whole A/B list over the QA link with no disc swap and no one at the controls:

  per scene (a camera-correct preset)
    per arm  (a `KNOB PRESET <arm>` on the same ELF; the speed switches are run-time bytes)
      KNOB PRESET <arm> -> TELEPORT <preset> (a full room entry, so room-entry knobs apply) -> wait until landed + free play
      -> settle -> capture <capture> s (fps / speed / PT rows / PMC counters) -> PCS SNAP x <snaps> (symbolised)
    the control arm is repeated at the end of the scene (drift / noise estimate)
  then a free-play window per scene (control arm) whose WORLD_STILL log lines give the real-play still-camera share.

Outputs in --out (default E:\\RE4DC-Lanes\\lab32\\session-<date>): one row per scene x arm in results.tsv, results.md (a table
per scene with per-second counter totals, not per-picture, and the delta against the scene's control), profiles.md (top
functions and area shares per snap, symbolised with --nm), wstill.md, the raw capture logs, DIAG snapshots and .pcs dumps.
A run can be resumed: finished (scene, arm) rows in results.tsv are skipped.

  python lab32_session.py --pi re4pi --nm E:\\RE4DC-Lanes\\lab32\\lab\\nm.txt                     (the whole plan)
  python lab32_session.py --pi re4pi --nm ... --scenes cross,p103h --arms control,fix4         (a subset)
  python lab32_session.py --pi re4pi --dry-run                                                 (print the plan and the times)
  python lab32_session.py --local <pi.log> --settle 5 --capture 8 --free 20 --snaps 1 ...      (Flycast, modem emulation)
  python lab32_session.py --report DIR --nm ...                                                (rebuild the tables from a run)

Labels: every number in the tables is console unless the run was --local (Flycast: counts and flow only, never timing).
"""
import argparse, collections, datetime, glob, os, re, statistics, struct, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
QALINK = os.path.join(HERE, 'qalink.py')
PCS_FROM_LOG = os.path.join(HERE, 'pcs_from_log.py')

# arm groups (KNOB PRESET names in qa_menu.cpp; `KNOBS` on the link lists the bytes)
TIERS = {   # --tier: arms per scene family (control is repeated last as control#2 unless --no-repeat)
    'core': {'v': ['control', 'fix4'], 'l': ['control', 'fix4'], 'c': ['control', 'fix4']},
    'std': {'v': ['control', 'fix4', 'all31', 'movca', 'leon3'], 'l': ['control', 'fix4', 'spawn4', 'spawn8'],
            'c': ['control', 'fxcut3', 'castle', 'fix4']},
    'full': {'v': ['control', 'all31', 'fix4', 'charvis2', 'ps31', 'movca', 'leon2', 'leon3'],
             'l': ['control', 'r10b', 'spawn4', 'spawn8', 'fix4', 'fxcut3', 'leon3'],
             'c': ['control', 'fxcut3', 'castle', 'charvis2', 'fix4']},
}
VILLAGE, LAKE, CASTLE = 'v', 'l', 'c'
# name, preset id (mkqa), room (hex, for the landed check), arms
SCENES = [
    ('cross',      'r101x', '101', VILLAGE),
    ('bell',       'r101',  '101', VILLAGE),
    ('farm-entry', 'r103',  '103', VILLAGE),
    ('hayfork',    'p103h', '103', VILLAGE),
    ('quiet-farm', 'p103q', '103', VILLAGE),
    ('r100-entry', 'r100',  '100', VILLAGE),
    ('r100-spotB', 'p100b', '100', VILLAGE),
    ('dellago-boat', 'r10b', '10b', LAKE),
    ('dellago-fight', 'r10bd', '10b', LAKE),
    ('castle-gate', 'r200', '200', CASTLE),
]
EV = {'24': 'Istall', '25': 'Dstall', '04': 'OCrd', '05': 'OCwr', '08': 'Imiss'}
COLS = [('fps', 'fps', '%.1f', 1), ('fps.speed', 'speed%', '%.0f', 1), ('ms10.logic', 'logic ms', '%.1f', 0.1),
        ('ms10.fx', 'fx ms', '%.1f', 0.1), ('pmc.Istall', 'I stall M/s', '%.1f', 1e-6), ('pmc.Dstall', 'D stall M/s', '%.1f', 1e-6),
        ('pmc.OCrd', 'OC rd M/s', '%.2f', 1e-6), ('pmc.OCwr', 'OC wr k/s', '%.0f', 1e-3), ('pmc.Imiss', 'I miss M/s', '%.2f', 1e-6),
        ('kos.free', 'kos free', '%.0f', 1), ('fx_live', 'fx live', '%.0f', 1), ('still_pct', 'still %', '%.0f', 1)]
AREAS = [('world draw', r'vp::|walk_lean|ps2_pass|chunk_|strips_|clip_strip|MeshDraw|scenery|world|Scenery|sg_|ps2w'),
         ('pose/skeleton', r'pwc|pmc_run|Motion|InverseKin|partsWorld|skik|PSMTX|Parts'),
         ('characters draw', r'avk_|skin|light_|propGate|actor|Actor|Model|al4|L_al'),
         ('effects', r'Esp|Ps2fx|Fx|fx_|cEsp|Effect'),
         ('collision', r'line_leaf|Collision|collision|Hit|hit_|Line|col_')]


class Run:
    def __init__(self, a):
        self.a = a
        self.out = a.out
        os.makedirs(self.out, exist_ok=True)
        self.log = open(os.path.join(self.out, 'session.log'), 'a', encoding='utf-8')

    def say(self, s):
        line = '%s %s' % (time.strftime('%H:%M:%S'), s)
        print(line, flush=True)
        self.log.write(line + '\n')
        self.log.flush()

    def q(self, *words, timeout=420):
        """One qalink.py action; returns (rc, stdout). The link tools do their own retries and pacing."""
        cmd = [sys.executable, QALINK]
        if self.a.local:
            cmd += ['--local', self.a.local]
        else:
            cmd += ['--pi', self.a.pi]
        cmd += ['--review28', '--out', self.out] + list(words)
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout or '') + (r.stderr or '')

    def send(self, text, timeout=420):
        return self.q('send', *text.split(), timeout=timeout)

    def idle(self, limit=60):
        for _ in range(limit // 2):
            _, o = self.send('PCS STATUS')
            if 'state=1' in o:
                return True
            time.sleep(2)
        return False

    def landed(self, preset, room, limit=240):
        """The preset is in (DIAG shows room=<room> preset=<id>), the game runs at speed and Leon is in free play."""
        t0 = time.time()
        while time.time() - t0 < limit:
            _, o = self.send('DIAG')
            if re.search(r'^room=%s preset=%s\b' % (room, re.escape(preset)), o, re.M) and \
               re.search(r'^fps=[0-9.]+ speed=(9[0-9]|1[0-9][0-9])', o, re.M):
                drv = [l for l in o.splitlines() if l.startswith('drv ')]
                if not drv or 'free=1' in drv[0]:
                    return int(time.time() - t0)
            time.sleep(3)
        return None


def summ(path):
    d = {}
    for line in open(path, errors='replace'):
        m = re.match(r'(\S+)\s+(-?[\d.]+)\s+\(n=', line)
        if m:
            d[m.group(1)] = float(m.group(2))
    return d


def parse_capture(out, label):
    """Row of numbers from one capture: summary means, PMC2 per-second totals (total * 59.94 / win_vb), WSTILL share."""
    r = {}
    sm = sorted(glob.glob(os.path.join(out, label + '*.summary.txt')))
    if not sm:
        return None
    r.update(summ(sm[-1]))
    logs = [p for p in sorted(glob.glob(os.path.join(out, label + '*.log'))) if not p.endswith('.summary.txt')]
    pmc = collections.defaultdict(list)
    drawn = still = 0
    lines = []
    for f in [os.path.join(out, label + '-diag-start.txt')] + logs[-1:] + [os.path.join(out, label + '-diag-end.txt')]:
        if os.path.exists(f):
            lines += open(f, errors='replace').read().splitlines()
    for line in lines:
        m = re.search(r'PMC2: ev=(\w+)\+(\w+) total=(\d+)\+(\d+) drawn=\d+ win_vb=(\d+)', line)
        if m and int(m.group(5)):
            vb = int(m.group(5))
            for e, t in ((m.group(1), m.group(3)), (m.group(2), m.group(4))):
                pmc[EV.get(e, e)].append(int(t) * 59.94 / vb)
        m = re.search(r'WSTILL frame=\d+ room=\w+ drawn=(\d+) still=(\d+)', line)
        if m:
            drawn += int(m.group(1))
            still += int(m.group(2))
        m = re.search(r'\bfx_live=(\d+)|\bfx live[= ](\d+)', line)
        if m:
            r['fx_live'] = float(m.group(1) or m.group(2))
    for k, v in pmc.items():
        r['pmc.' + k] = statistics.mean(v)
    if drawn:
        r['still_pct'] = 100.0 * still / drawn
        r['still_drawn'] = drawn
    return r


def load_nm_sized(path):
    """sh-elf-nm -n -S -C lines: addr size type name (size optional)."""
    out = []
    for line in open(path, errors='replace'):
        m = re.match(r'^([0-9a-fA-F]{8})\s+(?:([0-9a-fA-F]{8})\s+)?([tTwWdDbBrR])\s+(.*)$', line.rstrip())
        if m:
            out.append((int(m.group(1), 16), int(m.group(2), 16) if m.group(2) else 0, m.group(4)))
    out.sort()
    return out


def symbolize(pcs, nm):
    import bisect
    if not nm:
        return None
    addrs = [s[0] for s in nm]
    data = open(pcs, 'rb').read()
    n = (len(data) - 128) // 8
    hist = collections.Counter()
    tid = collections.Counter()
    for i in range(n):
        w0, w1 = struct.unpack_from('<II', data, 128 + 8 * i)
        if w1 == 0xFFFFFFFF:
            continue
        pc = 0x8c000000 | ((w0 & 0x7fffff) << 1)
        tid[w0 >> 23] += 1
        k = bisect.bisect_right(addrs, pc) - 1
        hist[nm[k][2] if k >= 0 else '?'] += 1
    return hist, tid, sum(hist.values())


def area_of(name):
    for a, rx in AREAS:
        if re.search(rx, name):
            return a
    return 'other'


def profile_text(label, snaps, nm):
    tot = collections.Counter()
    n = 0
    for p in snaps:
        r = symbolize(p, nm)
        if r:
            tot.update(r[0])
            n += r[2]
    if not n:
        return '== %s: no samples\n' % label
    areas = collections.Counter()
    for f, c in tot.items():
        areas[area_of(f)] += c
    s = '== %s: %d samples\n   ' % (label, n) + '  '.join('%s %d%%' % (a, round(100.0 * c / n)) for a, c in areas.most_common()) + '\n'
    for f, c in tot.most_common(8):
        s += '   %4.1f%%  %s\n' % (100.0 * c / n, f[:90])
    return s


def read_rows(path):
    rows = []
    if os.path.exists(path):
        hdr = None
        for line in open(path, encoding='utf-8'):
            f = line.rstrip('\n').split('\t')
            if hdr is None:
                hdr = f
                continue
            rows.append(dict(zip(hdr, f)))
    return rows


def write_tables(out, rows, local):
    """results.md: one table per scene (arm rows, control first) with the delta against the scene's first control row."""
    tag = 'Flycast (counts and flow only, no timing)' if local else 'console'
    L = ['# lab32 session tables (%s)' % tag, '', 'Per-second counter totals (PMC2 total x 59.94 / win_vb), not per picture. Logic / fx in ms per tick.', '']
    scenes = []
    for r in rows:
        if r['scene'] not in scenes:
            scenes.append(r['scene'])
    for sc in scenes:
        rs = [r for r in rows if r['scene'] == sc]
        L += ['## %s (%s)' % (sc, rs[0]['preset']), '',
              '| arm | ' + ' | '.join(c[1] for c in COLS) + ' | d fps | d D stall M/s | d I stall M/s |',
              '|---|' + '---:|' * (len(COLS) + 3)]
        base = next((r for r in rs if r['arm'] == 'control'), None)

        def num(r, k):
            try:
                return float(r[k]) if r.get(k, '') != '' else None
            except ValueError:
                return None
        for r in rs:
            cells = []
            for c in COLS:
                v = num(r, c[0])
                cells.append('-' if v is None else c[2] % (v * c[3]))
            d = []
            for k, sc_ in (('fps', 1), ('pmc.Dstall', 1e-6), ('pmc.Istall', 1e-6)):
                a, b = num(r, k), num(base, k) if base else None
                d.append('-' if a is None or b is None else '%+.2f' % ((a - b) * sc_))
            L.append('| %s | %s | %s |' % (r['arm'] + ('#2' if r.get('rep') == '2' else ''), ' | '.join(cells), ' | '.join(d)))
        L.append('')
    open(os.path.join(out, 'results.md'), 'w', encoding='utf-8', newline='\n').write('\n'.join(L) + '\n')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--pi', default=os.environ.get('QALINK_PI', 're4pi'))
    ap.add_argument('--local', default='', help='pi.log of a qalink_pi.py serve on this PC (Flycast modem emulation)')
    ap.add_argument('--out', default='')
    ap.add_argument('--nm', default='', help='sh-elf-nm -n -S -C output of the lab ELF (nm.txt next to the staged disc)')
    ap.add_argument('--scenes', default='', help='comma list of scene names or preset ids (default all)')
    ap.add_argument('--tier', default='std', choices=sorted(TIERS), help='arm set per scene family (core ~2 h, std ~4 h, full ~6 h)')
    ap.add_argument('--arms', default='', help='comma list of KNOB PRESET names (default the scene\'s own list)')
    ap.add_argument('--settle', type=int, default=20)
    ap.add_argument('--capture', type=int, default=30)
    ap.add_argument('--snaps', type=int, default=2)
    ap.add_argument('--free', type=int, default=180, help='free-play window per scene in seconds (0 = none)')
    ap.add_argument('--free-mode', default='script', choices=['idle', 'script', 'user'],
                    help='script: look-around / aim-hold pad scripts; idle: no input (best case for stillness); user: you play')
    ap.add_argument('--no-repeat', action='store_true', help='do not repeat the control arm at the end of each scene')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--report', default='', help='rebuild results.md / profiles.md from an existing run folder and exit')
    a = ap.parse_args()
    if a.report:
        a.out = a.report
    if not a.out:
        a.out = os.path.join(r'E:\RE4DC-Lanes\lab32', 'session-' + datetime.date.today().strftime('%Y%m%d'))
    run = Run(a)
    nm = load_nm_sized(a.nm) if a.nm and os.path.exists(a.nm) else None
    tsv = os.path.join(a.out, 'results.tsv')
    keys = ['scene', 'preset', 'arm', 'rep'] + [c[0] for c in COLS] + ['still_drawn', 'landed_s']
    if a.report:
        write_tables(a.out, read_rows(tsv), bool(a.local))
        print('tables rebuilt in', a.out)
        return 0
    want_s = [s for s in a.scenes.split(',') if s]
    scenes = [s for s in SCENES if not want_s or s[0] in want_s or s[1] in want_s]
    want_a = [x for x in a.arms.split(',') if x]
    per = 60 + a.settle + a.capture + 40 * a.snaps
    total = 0
    plan = []
    for name, preset, room, arms in scenes:
        al = [x for x in (want_a or TIERS[a.tier][arms])]
        if not a.no_repeat and 'control' in al:
            al = al + ['control#2']
        plan.append((name, preset, room, al))
        total += per * len(al) + (a.free + 60 if a.free else 0)
    if a.dry_run:
        for name, preset, room, al in plan:
            print('%-14s %-6s room %s: %s' % (name, preset, room, ' '.join(al)))
        print('about %d min' % (total // 60))
        return 0
    done = {(r['scene'], r['arm'] + ('#2' if r.get('rep') == '2' else '')) for r in read_rows(tsv)}
    if not os.path.exists(tsv):
        open(tsv, 'w', encoding='utf-8', newline='\n').write('\t'.join(keys) + '\n')
    rc, o = run.send('PING')
    run.say('PING: ' + o.strip().splitlines()[-1][:160] if o.strip() else 'PING: no answer')
    if rc:
        run.say('no link; stopping')
        return 1
    run.send('QA LEON ON')
    run.say('KNOBS: ' + ' '.join(run.send('KNOBS')[1].split())[:300])
    profiles = open(os.path.join(a.out, 'profiles.md'), 'a', encoding='utf-8', newline='\n')
    wst = open(os.path.join(a.out, 'wstill.md'), 'a', encoding='utf-8', newline='\n')
    for name, preset, room, arms in plan:
        run.say('=== scene %s (preset %s, room %s)' % (name, preset, room))
        for arm in arms:
            real = arm.split('#')[0]
            rep = '2' if '#' in arm else '1'
            if (name, arm) in done:
                run.say('skip %s / %s (done)' % (name, arm))
                continue
            label = '%s-%s' % (name, arm.replace('#', ''))
            run.idle()
            rc, o = run.send('KNOB PRESET ' + real)
            run.say('%s: %s' % (arm, (o.strip().splitlines() or ['?'])[-1][:200]))
            if rc or ' ERR ' in o:
                run.say('KNOB PRESET failed (is this the lab disc?); skipping the arm')
                continue
            run.send('TELEPORT ' + preset)
            ld = run.landed(preset, room)
            if ld is None:
                run.say('NOT LANDED: %s / %s; skipping' % (name, arm))
                continue
            time.sleep(a.settle)
            run.send('DIAG')  # warm
            _, d0 = run.send('DIAG')
            open(os.path.join(a.out, label + '-diag-start.txt'), 'w', encoding='utf-8').write(d0)
            run.q('capture', 'start', label)
            time.sleep(a.capture)
            run.q('capture', 'stop', label)
            _, d1 = run.send('DIAG')
            open(os.path.join(a.out, label + '-diag-end.txt'), 'w', encoding='utf-8').write(d1)
            snaps = []
            for k in range(a.snaps):
                run.idle()
                time.sleep(3)
                _, o = run.send('PCS SNAP', timeout=600)
                tp = os.path.join(a.out, '%s-snap%d.txt' % (label, k + 1))
                open(tp, 'w', encoding='utf-8').write(o)
                subprocess.run([sys.executable, PCS_FROM_LOG, tp, os.path.join(a.out, '%s-snap%d' % (label, k + 1))],
                               capture_output=True, text=True)
                snaps += glob.glob(os.path.join(a.out, '%s-snap%d-*.pcs' % (label, k + 1)))
            row = parse_capture(a.out, label) or {}
            row.update(scene=name, preset=preset, arm=real, rep=rep, landed_s=ld)
            open(tsv, 'a', encoding='utf-8', newline='\n').write(
                '\t'.join('' if row.get(k) is None else ('%.4g' % row[k] if isinstance(row[k], float) else str(row[k])) for k in keys) + '\n')
            profiles.write(profile_text(label, snaps, nm) + '\n')
            profiles.flush()
            run.say('%s / %s: fps=%s speed=%s Dstall=%s' % (name, arm, row.get('fps'), row.get('fps.speed'), row.get('pmc.Dstall')))
        if a.free:
            run.idle()
            run.send('KNOB PRESET control')
            run.send('TELEPORT ' + preset)
            if run.landed(preset, room) is not None:
                time.sleep(a.settle)
                label = '%s-free-%s' % (name, a.free_mode)
                run.q('capture', 'start', label)
                t0 = time.time()
                scripts = ['look-around', 'aim-hold']
                k = 0
                while time.time() - t0 < a.free:
                    if a.free_mode == 'script':
                        run.send('SCRIPT ' + scripts[k % 2], timeout=120)
                        k += 1
                    else:
                        time.sleep(min(10, max(1, a.free - (time.time() - t0))))
                run.q('capture', 'stop', label)
                r = parse_capture(a.out, label) or {}
                wst.write('| %s | %s | %s s | %s | %s |\n' % (name, preset, a.free, a.free_mode,
                          ('%.0f%% of %d drawn frames' % (r['still_pct'], r['still_drawn'])) if 'still_pct' in r else 'no WSTILL lines'))
                wst.flush()
                run.say('free play %s: still %s' % (name, r.get('still_pct')))
        write_tables(a.out, read_rows(tsv), bool(a.local))
    run.send('KNOB PRESET control')
    run.say('done; tables in ' + a.out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
