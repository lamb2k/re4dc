#!/usr/bin/env python3
"""Lab33 console session. Each bracket shares its closing control with the next bracket.
A window is 600 complete drawn-picture intervals following the confirmed preset landing.
Use --dry-run for the plan and --local for a Flycast modem run.
"""
import argparse, collections, datetime, glob, os, re, statistics, struct, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
QALINK = os.path.join(HERE, 'qalink.py')
PCS_FROM_LOG = os.path.join(HERE, 'pcs_from_log.py')

# arm groups (KNOB PRESET names in qa_menu.cpp; `KNOBS` on the link lists the bytes)
CORE = ['noworld', 'nochars', 'nofx', 'nohud', 'nodraw', 'aa']
STD = CORE + ['fix4', 'all31', 'charvis2', 'ps31', 'leon2', 'leon3', 'spawn4', 'movca']
TIERS = {'core': CORE, 'std': STD}
SCENES = [
    ('cross', 'r101x', '101'),
    ('bell', 'r101', '101'),
    ('hayfork', 'p103h', '103'),
    ('quiet-farm', 'p103q', '103'),
    ('farm-entry', 'r103', '103'),
    ('r100-entry', 'r100', '100'),
]
EV = {'24': 'Istall', '25': 'Dstall', '04': 'OCrd', '05': 'OCwr', '08': 'Imiss'}
COLS = [('fps', 'fps', '%.1f', 1), ('fps.speed', 'speed%', '%.0f', 1), ('ms10.logic', 'logic ms', '%.1f', 0.1),
        ('ms10.fx', 'fx ms', '%.1f', 0.1), ('pmc.Istall', 'I stall M/s', '%.1f', 1e-6), ('pmc.Dstall', 'D stall M/s', '%.1f', 1e-6),
        ('pmc.OCrd', 'OC rd M/s', '%.2f', 1e-6), ('pmc.OCwr', 'OC wr k/s', '%.0f', 1e-3), ('pmc.Imiss', 'I miss M/s', '%.2f', 1e-6),
        ('kos.free', 'kos free', '%.0f', 1), ('fx_live', 'fx live', '%.0f', 1), ('still_pct', 'still %', '%.0f', 1)]
COLS += [(k, k + ' ms', '%.2f', 1) for k in ('mean', 'p99', 'worst','world','chars','fx','hud')]
COLS += [(k, k, '%.0f', 1) for k in ('pictures','ticks','over33','over50')]

def get_window(run):
    end = time.monotonic() + 240
    while time.monotonic() < end:
        rc, reply = run.send('INTERVAL READ')
        m = re.search(r'\bINTERVAL n=600 ticks=(\d+) sum=(\d+) p99=(\d+) worst=(\d+) over33=(\d+) over50=(\d+) world=(\d+) chars=(\d+) fx=(\d+) hud=(\d+)', reply)
        if not rc and m:
            ticks, total, p99, worst, over33, over50, *phase = map(int,m.groups())
            if ticks < 600 or not 0 < p99 <= worst or not 0 <= over50 <= over33 <= 600:
                raise RuntimeError('invalid interval row: ' + m.group())
            row = dict(pictures=600,ticks=ticks,mean=total/600000,p99=p99/1000,worst=worst/1000,over33=over33,over50=over50)
            row.update(zip(('world','chars','fx','hud'), (v/600000 for v in phase)))
            return row, reply
        time.sleep(3)
    raise RuntimeError('600-picture window missing')

AREAS = [('world draw', r'vp::|walk_lean|ps2_pass|chunk_|strips_|clip_strip|MeshDraw|scenery|world|Scenery|sg_|ps2w'),
         ('pose/skeleton', r'pwc|pmc_run|Motion|InverseKin|partsWorld|skik|PSMTX|Parts'),
         ('characters draw', r'avk_|skin|light_|propGate|actor|Actor|Model|al4|L_al'),
         ('effects', r'Esp|Ps2fx|Fx|fx_|cEsp|Effect'),
         ('collision', r'line_leaf|Collision|collision|Hit|hit_|Line|col_')]


# Full room-entry preset positions and Leon yaw (milliradians) from mkqa.
POSE = {'r101x':(-7914,2000,1571), 'r101':(-7914,-254,2960),
        'p103h':(-30717,-13585,2784), 'p103q':(-44074,5598,-1211),
        'r103':(-47609,7084,1889), 'r100':(-82910,-38480,-129)}

def near_preset(preset,m):
    x,z,yaw = POSE[preset]
    angle_error = (int(m[5])-yaw+3142)%6283-3142
    return abs(int(m[2])-x)<500 and abs(int(m[4])-z)<500 and abs(angle_error)<300

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
        env = os.environ.copy()
        if self.a.local:
            env['USERPROFILE' if os.name == 'nt' else 'HOME'] = os.path.abspath(self.out)
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
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
               re.search(r'^fps=[1-9][0-9.]* speed=[1-9]', o, re.M):
                rc, pos = self.send('LABPOS')
                m = re.search(r'drv room=(\w+) pos=(-?\d+),(-?\d+),(-?\d+) ang=(-?\d+).*? free=1\b', pos)
                if not rc and m and m.group(1) == room and near_preset(preset,m):
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
    L = ['# lab33 session tables (%s)' % tag, '', 'Per-second counter totals (PMC2 total x 59.94 / win_vb), not per picture. Logic / fx in ms per tick.', '']
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
            L.append('| %s | %s | %s |' % (r['arm'] + (('#' + r['rep']) if r.get('rep', '1') != '1' else ''), ' | '.join(cells), ' | '.join(d)))
        L.append('')
    open(os.path.join(out, 'results.md'), 'w', encoding='utf-8', newline='\n').write('\n'.join(L) + '\n')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--pi', default=os.environ.get('QALINK_PI', 're4pi'))
    ap.add_argument('--local', default='', help='pi.log of a qalink_pi.py serve on this PC (Flycast modem emulation)')
    ap.add_argument('--out', default='')
    ap.add_argument('--nm', default='', help='sh-elf-nm -n -S -C output of the lab ELF (nm.txt next to the staged disc)')
    ap.add_argument('--scenes', default='', help='comma list of scene names or preset ids (default all)')
    ap.add_argument('--tier', default='core', choices=sorted(TIERS), help='four core scenes or six standard scenes')
    ap.add_argument('--arms', default='', help='comma list of KNOB PRESET names (default the scene\'s own list)')
    ap.add_argument('--settle', type=int, default=5)
    ap.add_argument('--capture', type=int, default=30)
    ap.add_argument('--snaps', type=int, default=0)
    ap.add_argument('--free', type=int, default=0, help='free-play window per scene in seconds (0 = none)')
    ap.add_argument('--free-mode', default='script', choices=['idle', 'script', 'user'],
                    help='script: look-around / aim-hold pad scripts; idle: no input (best case for stillness); user: you play')
    ap.add_argument('--no-repeat', action='store_true', help='do not repeat the control arm at the end of each scene')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--report', default='', help='rebuild results.md / profiles.md from an existing run folder and exit')
    a = ap.parse_args()
    if a.report:
        a.out = a.report
    if not a.out:
        a.out = os.path.join(r'E:\RE4DC-Lanes\lab33', 'session-' + datetime.date.today().strftime('%Y%m%d'))
    run = Run(a)
    nm = load_nm_sized(a.nm) if a.nm and os.path.exists(a.nm) else None
    tsv = os.path.join(a.out, 'results.tsv')
    keys = ['scene', 'preset', 'arm', 'rep'] + [c[0] for c in COLS] + ['still_drawn', 'landed_s']
    if a.report:
        write_tables(a.out, read_rows(tsv), bool(a.local))
        print('tables rebuilt in', a.out)
        return 0
    want_s = [s for s in a.scenes.split(',') if s]
    known = {v for scene in SCENES for v in scene[:2]}
    if set(want_s) - known:
        ap.error('unknown scene ' + ','.join(sorted(set(want_s) - known)))
    scenes = [s for s in SCENES if s[0] in want_s or s[1] in want_s] if want_s else SCENES[:4 if a.tier == 'core' else 6]
    targets = a.arms.split(',') if a.arms else TIERS[a.tier]
    allowed = set(STD) | {'control', 'delay10'}
    if set(targets) - allowed:
        ap.error('unknown arm ' + ','.join(sorted(set(targets) - allowed)))
    total = 0
    plan = []
    for name, preset, room in scenes:
        bracket = targets if a.no_repeat else ['control']
        if not a.no_repeat:
            for arm in targets:
                if arm != 'control':
                    bracket.extend([arm,'control'])
        counts = collections.Counter()
        al = []
        for arm in bracket:
            counts[arm] += 1
            al.append(arm if counts[arm] == 1 else '%s#%d' % (arm, counts[arm]))
        plan.append((name,preset,room,al))
        fps = {'cross':18.4,'bell':16.5,'hayfork':10.4,'quiet-farm':29.3,'farm-entry':18.4,'r100-entry':21.9}[name]
        total += (55 + a.settle + max(a.capture,600/fps) + 40*a.snaps) * len(al) + (a.free + 60 if a.free else 0)
    if a.dry_run:
        for name, preset, room, al in plan:
            print('%-14s %-6s room %s: %s' % (name, preset, room, ' '.join(al)))
        print('about %d min' % (total // 60))
        return 0
    done = {(r['scene'], r['arm'] + (('#' + r['rep']) if r.get('rep', '1') != '1' else '')) for r in read_rows(tsv)}
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
            rep = arm.partition('#')[2] or '1'
            if (name, arm) in done:
                run.say('skip %s / %s (done)' % (name, arm))
                continue
            label = '%s-%s' % (name, arm.replace('#', ''))
            run.idle()
            rc, o = run.send('KNOB PRESET ' + real)
            run.say('%s: %s' % (arm, (o.strip().splitlines() or ['?'])[-1][:200]))
            if rc or ('OK KNOB PRESET ' + real + ':') not in o:
                run.say('KNOB PRESET failed')
                return 1
            rc, reply = run.send('TELEPORT ' + preset)
            if rc or 'OK TELEPORT' not in reply:
                return 1
            ld = run.landed(preset, room)
            if ld is None:
                run.say('NOT LANDED: %s / %s; skipping' % (name, arm))
                return 1
            time.sleep(a.settle)
            run.send('DIAG')  # warm
            _, d0 = run.send('DIAG')
            open(os.path.join(a.out, label + '-diag-start.txt'), 'w', encoding='utf-8').write(d0)
            rc, reply = run.q('capture','start',label)
            if rc:
                raise RuntimeError('capture start failed: ' + reply)
            try:
                rc, reply = run.send('INTERVAL START')
                if rc or 'INTERVAL n=0 ' not in reply:
                    raise RuntimeError('interval start failed: ' + reply)
                time.sleep(a.capture)
                window, raw = get_window(run)
                with open(os.path.join(a.out,label+'-interval.txt'),'w') as f:
                    f.write(raw)
            finally:
                rc, reply = run.q('capture','stop',label)
            if rc:
                raise RuntimeError('capture stop failed: ' + reply)
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
            if 'ms10.logic' not in row:
                raise RuntimeError('capture missing logic measurement: ' + label)
            row.update(window)
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
