#!/usr/bin/env python3
r"""re4_bridge_proof.py: drive an RE4 engine image through dc-qalink's bridge, as QA Link Cloud does, and record what
happened (lane eng-link2, 2026-11-23; docs/engine/CONSOLE_LOOP.md section 17). Python 3.10+, standard library only.

    re4_bridge_proof.py <bridge url> <out dir> --push <e1.elf> [--args "..."] [--plan full|readx|plain|increment]

The bridge (dc-qalink pc/qalink_bridge.py) must already be linked to a loader (Flycast or a console) and, for the main
mode, serve the staged RE4 disc folder whole (--disc <folder> --whole). Plans:
  full       push and run the village image; live rows; 3 screen grabs; the menu opened by the PC for 6 s (a grab while
             open) and closed; warp farm then warp village (each must land: the live rows' room); RESET back to the
             loader; push again and force a crash (back with its report); push a third time and end it (exit 0)
  readx      CONTROL: push, live rows, then option readx=1 (a pack read inside play), then end: re4_link_check.py must FAIL
  plain      push, wait for live rows for 20 s, end (the link-off control image gives none: the check must FAIL)
  increment  push, live rows, one grab, leave it running (the owner's next increment)
Every time recorded is the wall clock of this PC around the bridge's answers: tier "flycast" or "console" as the bridge
says. Writes <out>/proof.json (steps, runs, stills, the session ids); tools/consoleloop/re4_link_check.py judges it.
"""
import argparse, hashlib, json, os, sys, time, urllib.error, urllib.request, uuid

BY = 're4dc tools/consoleloop/re4_bridge_proof.py'


class Bridge:
    def __init__(self, url):
        self.url = url.rstrip('/')

    def get(self, path, timeout=15):
        r = urllib.request.Request(self.url + path, headers={'X-Contract': '1'})
        with urllib.request.urlopen(r, timeout=timeout) as f:
            return json.loads(f.read())

    def post(self, path, body=None, timeout=180):
        r = urllib.request.Request(self.url + path, method='POST',
                                   data=json.dumps(body if body is not None else {}).encode(),
                                   headers={'Content-Type': 'application/json', 'X-Contract': '1', 'X-By': BY})
        try:
            with urllib.request.urlopen(r, timeout=timeout) as f:
                return f.status, json.loads(f.read())
        except urllib.error.HTTPError as e:
            b = e.read()
            try:
                return e.code, json.loads(b)
            except ValueError:
                return e.code, {'error': b[:300].decode('latin-1')}

    def push(self, path, args, deadline_s):
        raw = open(path, 'rb').read()
        b = uuid.uuid4().hex
        fields = (('sha256', hashlib.sha256(raw).hexdigest()), ('args', args), ('name', os.path.basename(path)),
                  ('deadline_s', str(deadline_s)))
        parts = [('--%s\r\nContent-Disposition: form-data; name="%s"\r\n\r\n%s\r\n' % (b, k, v)).encode() for k, v in fields]
        parts.append(('--%s\r\nContent-Disposition: form-data; name="program"; filename="%s"\r\n\r\n' %
                      (b, os.path.basename(path))).encode() + raw + b'\r\n')
        body = b''.join(parts) + ('--%s--\r\n' % b).encode()
        r = urllib.request.Request(self.url + '/v0/runs', data=body, method='POST', headers={
            'Content-Type': 'multipart/form-data; boundary=%s' % b, 'X-Contract': '1', 'X-By': BY})
        with urllib.request.urlopen(r, timeout=120) as f:
            return json.loads(f.read())


class Proof:
    def __init__(self, br, out):
        self.br, self.out, self.t0 = br, out, time.time()
        self.steps, self.runs = [], []
        os.makedirs(out, exist_ok=True)

    def step(self, name, ok, **kw):
        s = dict(name=name, ok=bool(ok), at_s=round(time.time() - self.t0, 2), **kw)
        self.steps.append(s)
        print('%7.2f s  %-26s %s  %s' % (s['at_s'], name, 'ok' if ok else 'FAILED',
                                        json.dumps({k: v for k, v in kw.items()})[:220]), flush=True)
        self.save()
        return ok

    def save(self, sessions=False):
        st = {}
        try:
            st = self.br.get('/v0/status')
        except OSError:
            pass
        if sessions:   # the runs' session files (the bridge's records), for re4_link_check.py to read offline
            d = os.path.join(self.out, 'sessions')
            os.makedirs(d, exist_ok=True)
            ids = [r['id'] for r in self.runs]
            for s in self.br.get('/v0/sessions').get('sessions', []):
                if any(i in s['id'] for i in ids):
                    req = urllib.request.Request(self.br.url + '/v0/sessions/%s' % s['id'], headers={'X-Contract': '1'})
                    with urllib.request.urlopen(req, timeout=60) as f:
                        open(os.path.join(d, s['id'] + '.jsonl'), 'wb').write(f.read())
            for r in self.runs:
                try:
                    j = self.br.get('/v0/runs/%s' % r['id'])
                    r.update(state=j.get('state'), times=j.get('times'), way_back=j.get('way_back'),
                             summary=j.get('summary'), crash=j.get('crash'))
                    open(os.path.join(d, 'report-%s.txt' % r['id']), 'w', encoding='utf-8').write(j.get('report') or '')
                except OSError:
                    pass
        json.dump({'tool': BY, 'plan': getattr(self, 'plan', None), 'bridge': self.br.url, 'tier': st.get('tier'),
                   'steps': self.steps, 'runs': self.runs,
                   'session': st.get('session')}, open(os.path.join(self.out, 'proof.json'), 'w'), indent=1)

    def wait(self, pred, timeout, every=0.5):
        end = time.time() + timeout
        while time.time() < end:
            try:
                v = pred()
                if v:
                    return v
            except OSError:
                pass
            time.sleep(every)
        return None

    def loader_idle(self, timeout=120):
        """the loader back and beaconing, no program linked"""
        def f():
            st = self.br.get('/v0/status')
            d = st.get('device') or {}
            return st if st.get('link') == 'up' and not st.get('active_run') and \
                not (d.get('program') or {}).get('linked') and d.get('state') in ('idle', None, 'done') else None
        return self.wait(f, timeout)

    def run_state(self, rid):
        return self.br.get('/v0/runs/%s' % rid)

    def push_and_link(self, prog, args, deadline_s, label):
        t = time.time()
        run = self.br.push(prog, args, deadline_s)
        rid = run['id']
        self.runs.append({'id': rid, 'label': label, 'args': args})
        linked = self.wait(lambda: (lambda d: d if (d.get('program') or {}).get('linked') else None)(
            self.br.get('/v0/device')), 120)
        self.step('push %s' % label, bool(linked), run=rid, seconds_to_link=round(time.time() - t, 2),
                  push_s=(self.run_state(rid).get('times') or {}).get('push_s'))
        return rid

    def rows_after(self, n0, timeout=60):
        """the newest picture the bridge holds, once it passes n0"""
        return self.wait(lambda: (lambda s: s if (s.get('n') or 0) > n0 else None)(self.br.get('/v0/status')), timeout)

    def room_now(self):
        s = self.br.get('/v0/summary?slowest=1')
        return s

    def end_state(self, rid, timeout=180):
        r = self.wait(lambda: (lambda x: x if x.get('state') not in ('queued', 'sending', 'running') else None)(
            self.run_state(rid)), timeout)
        return r or self.run_state(rid)

    def grab(self, label):
        t = time.time()
        try:
            code, j = self.br.post('/v0/stills', {'timeout_s': 20}, timeout=45)
        except OSError as e:   # the bridge did not answer (Flycast run r1: 12 CRC rounds, then no answer)
            code, j = None, {'error': str(e)[:100]}
        ok = self.step('grab %s' % label, code == 200 and j.get('crc_ok'), code=code, id=j.get('id'),
                       picture=j.get('picture'), error=j.get('error'), seconds=round(time.time() - t, 2))
        if not ok:   # a failed grab may leave the program paused (bridge 0.2.0): resume it so the plan goes on
            try:
                self.br.post('/v0/command', {'cmd': 'resume'}, timeout=20)
            except OSError:
                pass
        return ok

    def cmd(self, body, label):
        t = time.time()
        code, j = self.br.post('/v0/command', body, timeout=60)
        return self.step(label, code == 200 and j.get('ok'), code=code, n=j.get('n'), error=j.get('error'),
                         seconds=round(time.time() - t, 2)), j


def room_of_newest(br, session):
    """the newest row's room, from the session file the bridge is writing (GET /v0/sessions/{id}: ndjson)"""
    if not session:
        return None, None
    req = urllib.request.Request(br.url + '/v0/sessions/%s' % session, headers={'X-Contract': '1'})
    with urllib.request.urlopen(req, timeout=30) as f:
        lines = f.read().decode('utf-8', 'replace').splitlines()
    for line in reversed(lines):
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if r.get('t') == 'row' and r.get('x'):
            return r['x'].get('room'), r.get('n')
    return None, None


def warp_and_land(p, preset, room, timeout=90):
    ok, j = p.cmd({'cmd': 'warp', 'preset': preset}, 'warp %s (asked)' % preset)
    t = time.time()

    def landed():
        st = p.br.get('/v0/status')
        r, n = room_of_newest(p.br, st.get('session'))
        return (r, n) if r == room else None
    got = p.wait(landed, timeout, every=1.0)
    p.step('warp %s landed' % preset, bool(got) and ok, room_want='%03x' % room,
           room_seen='%03x' % got[0] if got else None, picture=got[1] if got else None,
           seconds=round(time.time() - t, 2))


def main():
    try:
        return run()
    finally:
        if PROOF:
            PROOF.save(sessions=True)


PROOF = None


def run():
    global PROOF
    ap = argparse.ArgumentParser()
    ap.add_argument('bridge')
    ap.add_argument('out')
    ap.add_argument('--push', required=True)
    ap.add_argument('--args', default='root=E1 ticks=9000 rows=skip')
    ap.add_argument('--plan', default='full', choices=['full', 'readx', 'plain', 'increment', 'loads', 'smoke'])
    ap.add_argument('--deadline', type=int, default=600)
    ap.add_argument('--part', type=int, default=0, choices=[0, 1, 2], help='plan full: both halves (0) or one')
    a = ap.parse_args()
    br = Bridge(a.bridge)
    p = PROOF = Proof(br, a.out)
    p.plan = a.plan
    st = p.loader_idle(180)
    p.step('loader linked, idle', bool(st), tier=(st or {}).get('tier'), udp_bind=(st or {}).get('udp_bind'))
    if not st:
        return 2
    try:
        dsk = br.get('/v0/disc')
        p.step('network disc served', dsk.get('mode') in ('whole', 'overlay'), mode=dsk.get('mode'),
               files=dsk.get('count'), served=dsk.get('served'), manifest=(dsk.get('sha256') or '')[:16])
    except (OSError, ValueError) as e:
        p.step('network disc served', False, error=str(e)[:120])

    rid = p.push_and_link(a.push, a.args, a.deadline, 'run 1')
    s = p.rows_after(0, 120)
    p.step('live rows', bool(s), picture=(s or {}).get('n'))
    if a.plan == 'plain':
        time.sleep(20)
        p.cmd({'cmd': 'option', 'name': 'end', 'value': 1}, 'end the run')
        r = p.end_state(rid)
        p.step('run 1 ended', r.get('state') == 'done', state=r.get('state'), times=r.get('times'))
        return 0
    if a.plan == 'loads':   # room-entry times: the first room, then farm and village warps, then end
        time.sleep(3)
        warp_and_land(p, 'farm', 0x103)
        warp_and_land(p, 'village', 0x101)
        time.sleep(2)
        p.cmd({'cmd': 'option', 'name': 'end', 'value': 1}, 'end the run')
        r = p.end_state(rid)
        p.step('run 1 ended', r.get('state') == 'done', state=r.get('state'), times=r.get('times'))
        return 0
    if a.plan == 'readx':
        time.sleep(5)
        p.cmd({'cmd': 'option', 'name': 'readx', 'value': 1}, 'CONTROL readx (pack read in play)')
        time.sleep(5)
        p.cmd({'cmd': 'option', 'name': 'end', 'value': 1}, 'end the run')
        r = p.end_state(rid)
        p.step('run 1 ended', r.get('state') == 'done', state=r.get('state'), times=r.get('times'))
        return 0
    if a.plan == 'increment':
        p.grab('1')
        return 0
    if a.plan == 'smoke':   # a re-pin smoke: push, live rows, one grab, RESET back to the loader
        time.sleep(3)
        p.grab('1')
        t = time.time()
        code, j = br.post('/v0/command', {'cmd': 'reset', 'level': 'return'}, timeout=120)
        r = p.end_state(rid, 120)
        back = p.loader_idle(120)
        p.step('RESET back to the loader', code == 200 and bool(back), rung=j.get('rung'), way_back=j.get('way_back'),
               state=r.get('state'), seconds=round(time.time() - t, 2))
        return 0
    # (plan full: the screen grabs come last, in run 3: in Flycast run r1 a failing grab stopped the program's link)
    # --part 2: only the second half (crash, third push, grabs): stock Flycast's adapter thread can stop the emulator
    # ("SH4 exception when blocked", runs r2 and r3), so a Flycast session may carry the halves one at a time
    if a.part == 2:
        return part2(p, a, rid)
    # the menu: opened by the PC for 6 s, then the rows must move on again
    n_before = (br.get('/v0/status').get('n') or 0)
    p.cmd({'cmd': 'option', 'name': 'menu', 'value': 6}, 'menu open (6 s)')
    time.sleep(2.5)
    held = br.get('/v0/status').get('n') or 0
    time.sleep(2.0)
    held2 = br.get('/v0/status').get('n') or 0
    p.step('menu holds the game', held2 == held, picture_before=n_before, picture_held=held, picture_held_later=held2)
    s = p.rows_after(held2, 30)
    p.step('menu closed, play resumed', bool(s), picture=(s or {}).get('n'))
    warp_and_land(p, 'farm', 0x103)
    warp_and_land(p, 'village', 0x101)
    # RESET from the PC: back to the loader
    t = time.time()
    code, j = br.post('/v0/command', {'cmd': 'reset', 'level': 'return'}, timeout=120)
    r = p.end_state(rid, 120)
    back = p.loader_idle(120)
    p.step('RESET back to the loader', code == 200 and bool(back), rung=j.get('rung'), way_back=j.get('way_back'),
           state=r.get('state'), seconds=round(time.time() - t, 2))
    if a.part == 1:
        return 0
    return part2(p, a, None)


def part2(p, a, rid0):
    br = p.br
    if rid0:   # part 2 alone: the first run is ended (exit 0) before the crash run
        p.cmd({'cmd': 'option', 'name': 'end', 'value': 1}, 'end run 1')
        r = p.end_state(rid0, 180)
        p.step('run 1 ended', r.get('state') == 'done' and bool(p.loader_idle(120)), state=r.get('state'))
    # push again, crash: back with its report
    rid2 = p.push_and_link(a.push, a.args, a.deadline, 'run 2 (crash)')
    p.rows_after(0, 60)
    time.sleep(3)
    t = time.time()
    p.cmd({'cmd': 'option', 'name': 'crash', 'value': 1}, 'forced crash (asked)')
    r2 = p.end_state(rid2, 180)
    back = p.loader_idle(120)
    p.step('crash back with its report', r2.get('state') == 'crashed' and bool(back), state=r2.get('state'),
           crash=r2.get('crash'), way_back=r2.get('way_back'), report_bytes=len(r2.get('report') or ''),
           seconds=round(time.time() - t, 2))
    # a third push, no disc change: run and end
    rid3 = p.push_and_link(a.push, a.args, a.deadline, 'run 3 (no disc change)')
    s = p.rows_after(0, 60)
    time.sleep(3)
    for i in range(1, 4):
        p.grab('%d' % i)
        time.sleep(2)
    p.cmd({'cmd': 'option', 'name': 'menu', 'value': 8}, 'menu open for the grab (8 s)')
    time.sleep(2)
    p.grab('menu open')
    time.sleep(8)
    p.cmd({'cmd': 'option', 'name': 'end', 'value': 1}, 'end the run')
    r3 = p.end_state(rid3, 180)
    p.step('run 3 ended', r3.get('state') == 'done' and bool(s), state=r3.get('state'), times=r3.get('times'))
    p.loader_idle(120)
    p.save()
    return 0


if __name__ == '__main__':
    sys.exit(main())
