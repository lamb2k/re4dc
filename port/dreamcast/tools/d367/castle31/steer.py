"""steer.py: closed-loop driver for one fp_run.py capture (Windows Python; lane castle31, test tooling only).

    python steer.py --cap <fp_run capture dir> --plan <plan file> [--wait-pid 90]

Runs beside fp_run.py (start it first or at the same time; fp_run creates the capture dir). It reads the game's RAM
log (run-output.txt) live and posts keys ONLY to the windows of that capture's own Flycast process (flycast.pid,
PostMessage WM_KEYDOWN/UP by handle). No global input (no SendInput, keybd_event or SendKeys); if the process has no
window it refuses to run (exit 2). Keys use the capture's own map that fp_run writes for --keys (pass an empty keys file):
analog I/J/K/L = su/sd/sl/sr, triggers F/V = lt/rt, a/b/x/y/start.

The game side is the warp rig's `plpos N` line (dbgwarp_bridge.cpp): Leon's room, position, angle (rad*1000; facing
is (sin a, cos a) in x/z), life, the nearest live enemy and the live count. Plan lines (# comments):
    goto X Z [tol] [timeout]      tank-steer to (X, Z) in the current room (tol default 700 units)
    face X Z                      turn on the spot toward (X, Z)
    run 0|1                       from now on, run (hold B) on straight legs longer than 1.5 m
    rescue 0|1                    a goto first chases Ashley's carrier (off when the warp `ashley` line frees her)
    autofight R                   from now on, a goto stops to fight when a creature is within R (0 = off)
    room R [timeout]            wait until the plpos room is R (hex) -- after walking through a door
    log REGEX [timeout]           wait until REGEX appears in new log text
    press KEYS [hold]             tap keys (k1+k2), default hold 0.15 s
    hold KEYS SECS                hold keys for SECS
    mash KEY SECS                 tap KEY every 0.12 s for SECS
    dismiss [N]                   close a pickup/message screen: step back (sd); if Leon cannot move, tap A and retry
    wait SECS
    fight [secs] [range]          face the nearest live enemy within range (default 9000), aim (rt) and fire (a);
                                  reloads (b) every 9 shots; ends when none is in range or after secs (default 40)
    end                           release everything and idle
    @LABEL                        a place `--from LABEL` can start from
Writes <cap>/steer.log (actions) and <cap>/steer.json (rooms, peak Ganados alive, kills seen, stalls).
"""
import argparse, ctypes, json, math, re, subprocess, sys, time
from ctypes import wintypes as W
from pathlib import Path

user32 = ctypes.WinDLL('user32', use_last_error=True)
WNDENUMPROC = ctypes.WINFUNCTYPE(W.BOOL, W.HWND, W.LPARAM)
KEYS = dict(su=(0x17, 0x49), sd=(0x25, 0x4B), sl=(0x24, 0x4A), sr=(0x26, 0x4C), lt=(0x21, 0x46), rt=(0x2F, 0x56),
            a=(0x2D, 0x58), b=(0x2E, 0x43), x=(0x1F, 0x53), y=(0x20, 0x44), start=(0x1C, 0x0D))
PL = re.compile(r'warp: pl room (\w+) frame (\d+) pos (-?\d+) (-?\d+) (-?\d+) ang (-?\d+) life (-?\d+)'
                r'(?: em (-?\d+) (-?\d+) (-?\d+) (\w+) n (\d+))?')
ALIVE = re.compile(r'warp: alive (\d+) room (\w+)')
ASH = re.compile(r'warp: ash room \w+ frame \d+ pos (-?\d+) (-?\d+) (-?\d+) life (-?\d+) st1 ([0-9a-f]+)')


def windows_of(pid):
    out = []

    def cb(h, _):
        p = W.DWORD()
        user32.GetWindowThreadProcessId(h, ctypes.byref(p))
        if p.value == pid:
            out.append(h)
        return True
    user32.EnumWindows(WNDENUMPROC(cb), 0)
    return out


def wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


class Steer:
    def __init__(self, cap, pid, hwnds):
        self.cap, self.pid, self.hwnds = cap, pid, hwnds
        self.down = set(); self.pos = 0; self.text = ''; self.pl = None; self.pl_t = 0
        self.logf = open(cap / 'steer.log', 'a')
        self.rep = dict(rooms=[], alive_peak=0, live_peak=0, kills_seen=0, stalls=[], steps=[])
        self.last_alive = None
        self.autofight = 0
        self.running = 0
        self.ash = None
        self.rescue_on = 1   # `rescue 0|1`: a goto first chases and shoots Ashley's carrier (real play)
        self.rescues = 0
        self.maps = None     # --maps DIR: rXXX.sat per room for rescue routes (navplan.py beside this file)

    def log(self, s):
        self.logf.write('%.1f %s\n' % (time.monotonic(), s)); self.logf.flush()

    def post(self, name, up):
        sc, vk = KEYS[name]
        lp = 1 | (sc << 16) | ((1 << 30) | (1 << 31) if up else 0)
        for h in self.hwnds:
            user32.PostMessageW(h, 0x101 if up else 0x100, vk, lp)

    def keys(self, want):
        want = set(want)
        for k in self.down - want:
            self.post(k, True)
        for k in want - self.down:
            self.post(k, False)
        self.down = want

    def poll(self):
        if time.monotonic() - getattr(self, 'live_t', 0) > 1.0:  # stop with our Flycast (never touch another window)
            self.live_t = time.monotonic()
            if not windows_of(self.pid):
                self.log('flycast gone: stop'); self.down = set(); self.save()
                raise SystemExit(0)
        p = self.cap / 'run-output.txt'
        with open(p, 'rb') as f:
            f.seek(self.pos); new = f.read().decode('ascii', 'replace'); self.pos += len(new)
        self.text = (self.text + new)[-100000:]
        for m in PL.finditer(new):
            g = m.groups()
            self.pl = dict(room=g[0], frame=int(g[1]), x=int(g[2]), y=int(g[3]), z=int(g[4]), ang=int(g[5]) / 1000.0,
                           life=int(g[6]), ex=int(g[7] or 0), ey=int(g[8] or 0), ez=int(g[9] or 0), eid=g[10], n=int(g[11] or 0))
            self.pl_t = time.monotonic()
            if not self.rep['rooms'] or self.rep['rooms'][-1] != g[0]:
                self.rep['rooms'].append(g[0]); self.log('room %s' % g[0])
            self.rep['live_peak'] = max(self.rep['live_peak'], self.pl['n'])
        for m in re.finditer(r'warp: pl room .*? rno (\d+)/(\d+)/(\d+)', new):
            self.rno = tuple(int(v) for v in m.groups())
        for m in ASH.finditer(new):
            g = m.groups()
            self.ash = dict(x=int(g[0]), y=int(g[1]), z=int(g[2]), life=int(g[3]), carried=bool(int(g[4], 16) & 0x10000))
        for m in ALIVE.finditer(new):
            a = int(m.group(1))
            self.rep['alive_peak'] = max(self.rep['alive_peak'], a)
            if self.last_alive is not None and a < self.last_alive:
                self.rep['kills_seen'] += self.last_alive - a
            self.last_alive = a
        return new

    def sleep(self, s):
        t = time.monotonic() + s
        while time.monotonic() < t:
            self.poll(); time.sleep(0.05)

    def goto(self, x, z, tol=700, timeout=20):
        t0 = time.monotonic(); best = None; best_t = t0; retries = 0
        while time.monotonic() - t0 < timeout:
            self.poll()
            pl = self.pl
            if not pl or time.monotonic() - self.pl_t > 1.0:
                self.keys([]); time.sleep(0.05); continue
            if getattr(self, 'rno', (0,))[0] == 4 and self.rno[2] == 1:  # grabbed (bomb hug / choke): shake off with A
                n = 0
                while getattr(self, 'rno', (0,))[0] == 4 and self.rno[2] == 1 and n < 60:
                    self.post('a', False); self.sleep(0.05); self.post('a', True); self.sleep(0.07); n += 1
                self.log('shake: %d taps rno %s' % (n, self.rno)); best, best_t = None, time.monotonic(); continue
            if self.rescue_on and self.ash and self.ash['carried']:
                self.log('rescue: %s' % self.rescue())
                best, best_t = None, time.monotonic(); continue
            if self.autofight and pl['n'] and abs(pl['ey'] - pl['y']) < 1500 and math.hypot(pl['ex'] - pl['x'], pl['ez'] - pl['z']) < self.autofight:
                self.log('autofight: %s at %d' % (self.fight(30, self.autofight * 1.5),
                                                  math.hypot(pl['ex'] - pl['x'], pl['ez'] - pl['z'])))
                best, best_t = None, time.monotonic(); continue
            dx, dz = x - pl['x'], z - pl['z']; d = math.hypot(dx, dz)
            if d < tol:
                self.keys([]); return 'ok %d' % d
            if best is None or d < best - 200:
                best, best_t = d, time.monotonic()
            elif time.monotonic() - best_t > 4:
                if retries < 2:  # back off and try again (a body, Ashley or a stagger in the way)
                    retries += 1
                    self.keys(['sd']); self.sleep(0.6); self.keys([]); self.sleep(0.3)
                    best, best_t = None, time.monotonic(); continue
                self.keys([]); self.rep['stalls'].append(dict(goto=[x, z], at=[pl['x'], pl['z']], d=int(d)))
                return 'stall %d' % d
            err = wrap(math.atan2(dx, dz) - pl['ang'])
            k = []
            if abs(err) > 0.15:
                k.append('sl' if err > 0 else 'sr')
            if abs(err) < 0.7:
                k.append('su')
                if self.running and abs(err) < 0.3 and d > 1500:
                    k.append('b')  # run (B held + forward)
            self.keys(k); time.sleep(0.05)
        self.keys([]); return 'timeout'

    def face(self, x, z, timeout=5):
        t0 = time.monotonic()
        while time.monotonic() - t0 < timeout:
            self.poll(); pl = self.pl
            if not pl or time.monotonic() - self.pl_t > 1.0:
                self.keys([]); time.sleep(0.05); continue
            err = wrap(math.atan2(x - pl['x'], z - pl['z']) - pl['ang'])
            if abs(err) < 0.1:
                self.keys([]); return 'ok'
            self.keys(['sl' if err > 0 else 'sr']); time.sleep(0.03)
        self.keys([]); return 'timeout'

    def navroute(self, pl, a):
        sat = Path(self.maps) / ('r%s.sat' % pl['room'].lower())
        if not sat.exists():
            return []
        try:
            out = subprocess.run([sys.executable, str(Path(__file__).with_name('navplan.py')), str(sat), str(pl['x']),
                                  str(pl['z']), str(pl['y']), str(a['x']), str(a['z']), '--gy', str(a['y']), '--cell', '300'],
                                 capture_output=True, text=True, timeout=40, creationflags=0x08000000).stdout
        except subprocess.TimeoutExpired:
            return []
        r = [tuple(int(v) for v in l.split()[1:3]) for l in out.splitlines() if l.startswith('goto ')]
        self.log('rescue route %d points' % len(r))
        return r

    def rescue(self, secs=30):
        """Ashley carried off: run at her; within 4 m face her (the carrier holds her on the shoulder) and shoot."""
        t0 = time.monotonic(); shots = 0; last = 0
        self.rescues += 1
        while time.monotonic() - t0 < secs:
            self.poll(); pl, a = self.pl, self.ash
            if not pl or not a or time.monotonic() - self.pl_t > 1.0:
                self.keys([]); time.sleep(0.05); continue
            if not a['carried']:
                break
            if getattr(self, 'rno', (0,))[0] == 4 and self.rno[2] == 1:
                self.post('a', False); self.sleep(0.05); self.post('a', True); self.sleep(0.07); continue
            dx, dz = a['x'] - pl['x'], a['z'] - pl['z']; d = math.hypot(dx, dz)
            err = wrap(math.atan2(dx, dz) - pl['ang'])
            if (d > 4000 or abs(a['y'] - pl['y']) > 1500) and self.maps:
                # another floor or far: a walk route to her from navplan (the room's .sat in --maps), re-planned every 6 s
                if time.monotonic() - getattr(self, 'route_t', 0) > 6:
                    self.route_t = time.monotonic(); self.route = self.navroute(pl, a)
                wp = next(((x, z) for x, z in (self.route or []) if math.hypot(x - pl['x'], z - pl['z']) > 600), None)
                if wp:
                    err = wrap(math.atan2(wp[0] - pl['x'], wp[1] - pl['z']) - pl['ang'])
                    self.route = self.route[self.route.index(wp):]
            if d > 4000 or abs(a['y'] - pl['y']) > 1500:
                k = ['sl' if err > 0 else 'sr'] if abs(err) > 0.15 else []
                if abs(err) < 0.7:
                    k += ['su', 'b']
                self.keys(k); time.sleep(0.05); continue
            k = ['rt'] + ([('sl' if err > 0 else 'sr')] if abs(err) > 0.08 else [])
            self.keys(k)
            if abs(err) <= 0.12 and time.monotonic() - last > 0.6:
                self.post('a', False); time.sleep(0.08); self.post('a', True); shots += 1; last = time.monotonic()
            time.sleep(0.05)
        self.keys([])
        return 'rescue shots %d carried %s' % (shots, bool(self.ash and self.ash['carried']))

    def fight(self, secs=40, rng=9000):
        t0 = time.monotonic(); shots = 0; last_shot = 0
        while time.monotonic() - t0 < secs:
            self.poll(); pl = self.pl
            if not pl or time.monotonic() - self.pl_t > 1.0:
                self.keys([]); time.sleep(0.05); continue
            if not pl['n']:
                break
            dx, dz = pl['ex'] - pl['x'], pl['ez'] - pl['z']; d = math.hypot(dx, dz)
            if d > rng or abs(pl['ey'] - pl['y']) >= 1500:  # no vertical aim: same floor only
                break
            err = wrap(math.atan2(dx, dz) - pl['ang'])
            k = ['rt']
            if abs(err) > 0.08:
                k.append('sl' if err > 0 else 'sr')
            self.keys(k)
            if abs(err) <= 0.12 and time.monotonic() - last_shot > 0.6:
                self.post('a', False); time.sleep(0.08); self.post('a', True)
                shots += 1; last_shot = time.monotonic()
                if shots % 9 == 0:
                    self.post('b', False); time.sleep(0.1); self.post('b', True); self.sleep(1.5)
            time.sleep(0.05)
        self.keys([]); return 'shots %d' % shots

    def wait_rx(self, rx, timeout, room=None):
        t0 = time.monotonic(); r = re.compile(rx) if rx else None; self.text = ''
        while time.monotonic() - t0 < timeout:
            self.poll()
            if room is not None and self.pl and self.pl['room'].lower() == room:
                return 'ok'
            if r is not None and r.search(self.text):
                return 'ok'
            time.sleep(0.1)
        return 'timeout'

    def run(self, plan, start=None):
        plan = [l.split('#')[0].strip() for l in plan]
        plan = [l for l in plan if l]
        # A restored run first replays the RAM log from before the save: wait until the game runs (two advancing
        # plpos frames seen after the log went quiet), so the first press lands on a live frame.
        t0 = time.monotonic(); seen = []
        while time.monotonic() - t0 < 15:  # a modal screen holds room frames: start anyway after 15 s
            self.poll()
            if self.pl and time.monotonic() - t0 > 2 and (not seen or seen[-1] != self.pl['frame']):
                seen.append(self.pl['frame'])
                if len(seen) >= 3 and seen[-1] > seen[-2] > seen[-3]:
                    break
            time.sleep(0.1)
        self.sleep(1.0)
        if start:  # --from LABEL: start at the `@LABEL` line (settings lines before it still apply)
            i0 = plan.index('@' + start)
            for l in plan[:i0]:
                if l.startswith('rescue '):
                    self.rescue_on = int(l.split()[1])
                if l.startswith('autofight '):
                    self.autofight = float(l.split()[1])
                if l.startswith('run '):
                    self.running = int(l.split()[1])
            self.log('from @%s (line %d)' % (start, i0))
            plan = plan[i0 + 1:]
        elif plan and plan[0] == 'resume':  # continue a plan another segment started: from the goto nearest Leon now
            t0 = time.monotonic()
            while not self.pl and time.monotonic() - t0 < 30:
                self.poll(); time.sleep(0.1)
            gs = [(i, l.split()) for i, l in enumerate(plan) if l.startswith('goto ')]
            rm = [(i, l) for i, l in enumerate(plan) if l.startswith('room ')]
            i0 = 1
            if self.pl and gs:
                room = self.pl['room'].lower()
                # gotos after the last `room R` line that names the current room (or all, if none does)
                start = max([i for i, l in rm if l.split()[1].lower() == room] or [0])
                cand = [(math.hypot(int(t[1]) - self.pl['x'], int(t[2]) - self.pl['z']), i) for i, t in gs if i > start]
                if cand:
                    i0 = min(cand)[1]
            self.log('resume at line %d: %s' % (i0, plan[i0] if i0 < len(plan) else '-'))
            for l in plan[1:i0]:
                if l.startswith('rescue '):
                    self.rescue_on = int(l.split()[1])
                if l.startswith('autofight '):
                    self.autofight = float(l.split()[1])
                if l.startswith('run '):
                    self.running = int(l.split()[1])
            plan = plan[i0:]
        for line in plan:
            line = line.split('#')[0].strip()
            if not line or line.startswith('@') or line == 'resume':
                continue
            t = line.split(); c = t[0]
            if c == 'goto':
                r = self.goto(int(t[1]), int(t[2]), *(float(v) for v in t[3:5]))
            elif c == 'autofight':
                self.autofight = float(t[1]); r = 'ok'
            elif c == 'rescue':
                self.rescue_on = int(t[1]); r = 'ok'
            elif c == 'run':
                self.running = int(t[1]); r = 'ok'
            elif c == 'face':
                r = self.face(int(t[1]), int(t[2]))
            elif c == 'room':
                r = self.wait_rx(None, float(t[2]) if len(t) > 2 else 30, room=t[1].lower())
            elif c == 'log':
                r = self.wait_rx(t[1], float(t[2]) if len(t) > 2 else 30)
            elif c == 'press':
                ks = t[1].split('+')
                for k in ks:
                    self.post(k, False)
                time.sleep(float(t[2]) if len(t) > 2 else 0.15)
                for k in ks:
                    self.post(k, True)
                r = 'ok'
            elif c == 'dismiss':  # dismiss N: close a pickup/message screen. Test-walk first; press A only while Leon
                r = 'stuck'       # cannot move (never fires A at a free mount or prop).
                for _ in range(int(t[1]) if len(t) > 1 else 6):
                    self.poll(); p0 = dict(self.pl or {})
                    self.keys(['sd']); self.sleep(0.6); self.keys([]); self.sleep(0.4)
                    p1 = self.pl or {}
                    if p0 and p1 and math.hypot(p1['x'] - p0['x'], p1['z'] - p0['z']) > 60:
                        r = 'free'; break
                    self.post('a', False); self.sleep(0.25); self.post('a', True); self.sleep(2.0)
            elif c == 'mash':  # mash KEY SECS: tap every 0.12 s (cranks, struggle prompts)
                t1 = time.monotonic() + float(t[2])
                while time.monotonic() < t1:
                    dn = float(t[3]) if len(t) > 3 else 0.05; up = float(t[4]) if len(t) > 4 else 0.07
                    self.post(t[1], False); self.sleep(dn); self.post(t[1], True); self.sleep(up)
                r = 'ok'
            elif c == 'hold':
                self.keys(t[1].split('+')); self.sleep(float(t[2])); self.keys([]); r = 'ok'
            elif c == 'wait':
                self.sleep(float(t[1])); r = 'ok'
            elif c == 'fight':
                r = self.fight(*(float(v) for v in t[1:3]))
            elif c == 'end':
                self.keys([]); r = 'ok'
            else:
                raise SystemExit('steer: bad plan line: ' + line)
            pl = self.pl or {}
            self.log('%s -> %s at %s %s %s life %s n %s' % (line, r, pl.get('room'), pl.get('x'), pl.get('z'),
                                                        pl.get('life'), pl.get('n')))
            self.rep['steps'].append(dict(step=line, result=r, room=pl.get('room'), x=pl.get('x'), z=pl.get('z')))
            self.save()
            if c == 'end':
                break
        self.keys([])

    def save(self):
        (self.cap / 'steer.json').write_text(json.dumps(self.rep, indent=1) + '\n')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cap', required=True); ap.add_argument('--plan', required=True)
    ap.add_argument('--wait-pid', type=float, default=90)
    ap.add_argument('--from', dest='start', help='start at the plan line @LABEL instead of `resume`')
    ap.add_argument('--maps', help='directory of rXXX.sat files (room collision) for rescue routes')
    a = ap.parse_args()
    cap = Path(a.cap); t0 = time.monotonic()
    while not (cap / 'flycast.pid').exists() or not (cap / 'run-output.txt').exists():
        if time.monotonic() - t0 > a.wait_pid:
            sys.exit('steer: no capture pid in %s' % cap)
        time.sleep(0.5)
    pid = int((cap / 'flycast.pid').read_text())
    hw = []
    while not hw and time.monotonic() - t0 < a.wait_pid:
        hw = windows_of(pid); time.sleep(0.5)
    if not hw:
        print('steer: refusing: Flycast pid %d has no window' % pid); sys.exit(2)
    s = Steer(cap, pid, hw)
    s.maps = a.maps
    s.log('start pid %d windows %d plan %s' % (pid, len(hw), a.plan))
    try:
        s.run(Path(a.plan).read_text().splitlines(), a.start)
    finally:
        s.keys([]); s.save()
    print(json.dumps({k: s.rep[k] for k in ('rooms', 'alive_peak', 'live_peak', 'kills_seen', 'stalls')}))


if __name__ == '__main__':
    main()
