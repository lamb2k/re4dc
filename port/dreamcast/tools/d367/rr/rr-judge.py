#!/usr/bin/env python3
"""rr-judge.py <work dir> <tree> <rr bin dir>   (WSL; lane rr)

Judges one rr cycle (quick or full tier) from its build steps and Flycast job logs, writes <work>/verdict.txt
(PASS / FAIL), <work>/result.json and C:\\Game Dev\\Emulators\\RELEASE-READY.md (the last cycle; the last good
candidate is named at the top whatever this cycle's verdict).
Known, accepted rows (rr/known.txt) are reported as KNOWN, not FAIL.
"""
import json, os, re, subprocess, sys, time
from pathlib import Path

W, T, BIN = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
D367 = T / 'port/dreamcast/tools/d367'
REPORT = Path('/mnt/c/Game Dev/Emulators/RELEASE-READY.md')
RR_HOME = Path(os.environ.get('RR_HOME', '/root/rr'))
env = dict(l.split('=', 1) for l in (W / 'cycle.env').read_text().split('\n') if '=' in l)
EVU = Path(env['ev']); J = EVU / '_jobs'
tier = env.get('tier', 'quick')
known = set()
kf = BIN / 'known.txt'
if kf.exists():
    known = {tuple(l.split()[:2]) for l in kf.read_text().splitlines() if l.strip() and not l.startswith('#')}

def rd(p):
    try:
        return Path(p).read_text(errors='replace')
    except OSError:
        return ''

def runlog(name):
    return rd(EVU / name / 'run-output.txt').replace('\x00', '')

checks = []   # (name, status PASS/FAIL/KNOWN/SKIP, detail)
def add(n, ok, detail, knownrow=False):
    checks.append((n, 'PASS' if ok else ('KNOWN' if knownrow else 'FAIL'), detail))

steps = []
for l in rd(W / 'steps.tsv').splitlines():
    p = l.split('\t')
    if len(p) == 4 and all(x.lstrip('-').isdigit() for x in p[1:]):
        steps.append((p[0], int(p[1]), int(p[2]), int(p[3])))
srt = {s[0]: s for s in steps}
jobs = []
for l in rd(J / 'times.tsv').splitlines():
    p = l.split('\t')
    if len(p) == 4 and all(x.lstrip('-').isdigit() for x in p[1:]):
        jobs.append((p[0], int(p[1]), int(p[2]), int(p[3])))

build_ok = env.get('build_ok') == '1'
for s in ('trees', 'build-release', 'build-twins', 'package', 'bases'):
    if s in srt:
        add('step ' + s, srt[s][3] == 0, 'rc=%d, %d s' % (srt[s][3], srt[s][2] - srt[s][1]))
    elif not build_ok:
        checks.append(('step ' + s, 'SKIP', 'not run (an earlier step failed)'))

image = rd(W / 'image.sha256').strip()
add('missing.txt empty', build_ok or 'missing.txt not empty' not in rd(W / 'cycle.log'),
    'release build out-rr%srP' % env['sha'][:7])
for prof in ('loader', 'standard'):
    t = rd(W / ('pkg/logs/disc_lint-%s-rr%srP.txt' % (prof, env['sha'][:7]))).strip().splitlines()
    if t:   # t16-package.sh stops on any disc_lint violation, so a finished package step means both passed
        add('disc_lint ' + prof, 'package' in srt and srt['package'][3] == 0, t[-1][:120])

extra = {}
if build_ok and jobs:
    bad = re.compile(r'HALT|FAULT|RE4DC MISSING|Out of memory')
    # boot
    o = runlog('boot')
    add('boot to title', 'state title=' in o and not bad.search(o), 'title reached' if 'state title=' in o else 'no title line')
    # h2: s30 cliff movie
    o = runlog('h2')
    m = re.findall(r'route movie terminal=(\d) id=10030 frames=(\d+)/(\d+)[^\n]*', o)
    hb = re.findall(r'route movie terminal=\d id=10030 [^\n]*heap_before=(\d+)', o)
    extra['s30_heap_before'] = hb[-1] if hb else None
    if m:
        t, a, b = m[-1]
        add('h2 s30 movie', a == b == '340' and not bad.search(o), 'frames %s/%s, heap_before %s' % (a, b, hb[-1] if hb else '?'))
    else:
        add('h2 s30 movie', False, 'no s30 movie line (%s)' % ('HALT' if 'HALT' in o else 'not reached'))
    # KOS
    for n, _, _, rc in jobs:
        if n.startswith('kos'):
            lg = rd(J / (n + '.log'))
            hr = [int(x) for x in re.findall(r'min_headroom=(\d+)', lg)]
            extra.setdefault('kos_min_headroom', [])
            extra['kos_min_headroom'] += hr
            add('KOS 48 KiB ' + (n[4:] or 'fight'), 'GATE PASS' in lg, ', '.join(l.split(' held')[0] + ' headroom ' + (re.search(r'min_headroom=(\d*)', l).group(1) or '?')
                                                                   for l in lg.splitlines() if l.startswith(('PASS kos', 'FAIL kos'))) or lg.strip()[-120:])
    # GDEMU
    for n, _, _, rc in jobs:
        if n.startswith('gdemu'):
            lg = rd(J / (n + '.log'))
            g = re.findall(r'GDEMU RACE GATE[^\n]*', lg)
            add('GDEMU race ' + n, bool(g) and 'PASS' in g[-1], g[-1] if g else lg.strip()[-120:])
    # census
    rooms = rd(W / 'census-rooms.txt').split()
    logs = [EVU / ('cg-' + r) / 'run-output.txt' for r in rooms if (EVU / ('cg-' + r) / 'run-output.txt').exists()]
    if rooms:
        add('census ran', len(logs) == len(rooms), '%d/%d rooms: %s' % (len(logs), len(rooms), ' '.join(rooms)))
    if logs:
        cg = subprocess.run(['python3', str(D367 / 'cast_gc.py')] + [str(x) for x in logs] + ['--not-drawn', '--label', 'rr', '--json', str(EVU / 'castgc.json')],
                            capture_output=True, text=True)
        (EVU / 'castgc.txt').write_text(cg.stdout + cg.stderr)
        line = [l for l in cg.stdout.splitlines() if l.startswith('CAST-GC')]
        add('CAST-GC', bool(line) and line[-1].rstrip().endswith('(PASS)'), line[-1][:160] if line else 'rc=%d' % cg.returncode)
        nd = [l for l in cg.stdout.splitlines() if 'NOT-DRAWN' in l]
        extra['not_drawn'] = nd[:6]
        # NOT-DRAWN judged (lane notdrawn20, 10-20, #42): an enemy alive in logic and in view in >= 2 samples with no
        # census draw row FAILS unless castgc/notdrawn-allow.tsv lists it with a reason and an owner (cast_gc.py --not-drawn).
        ndl = [l for l in nd if l.startswith('NOT-DRAWN rr:')]
        add('NOT-DRAWN', bool(ndl) and ndl[-1].rstrip().endswith('(PASS)'),
            (ndl[-1][:160] if ndl else 'no NOT-DRAWN summary (rc=%d)' % cg.returncode) +
            ''.join('; ' + ' '.join(l.split()[:3]) for l in cg.stdout.splitlines() if l.rstrip().endswith(' FAIL')))
        lf = []
        for x in logs:
            r = subprocess.run(['python3', str(D367 / 'mcheck/leongc_check.py'), str(x)], capture_output=True, text=True)
            last = (r.stdout.strip().splitlines() or [''])[-1]
            if 'PASS' not in last:
                lf.append(x.parent.name[3:])
        add('LEON-GC', not lf, '%d/%d PASS%s' % (len(logs) - len(lf), len(logs), (' (fail: ' + ' '.join(lf) + ')') if lf else ''))
        tx = subprocess.run(['bash', str(D367 / 'texchk/texchk.sh')] + [str(x) for x in logs], capture_output=True, text=True)
        (EVU / 'texchk.txt').write_text(tx.stdout + tx.stderr)
        tf, cur = [], None
        for l in tx.stdout.splitlines():
            m2 = re.match(r'== .*/cg-(r[0-9a-f]+)/run-output\.txt', l)
            if m2:
                cur = m2.group(1)
            elif l.startswith('  TEXCHK FAIL') and cur:   # per-log verdict (indented), not the summary line
                tf.append(cur); cur = None
        unk = [r for r in tf if ('texchk', r) not in known]
        add('TEXCHK', not unk, '%d/%d PASS%s' % (len(logs) - len(tf), len(logs), (' (fail: ' + ' '.join(tf) + (', known: ' + ' '.join(r for r in tf if r not in unk) if len(unk) < len(tf) else '') + ')') if tf else ''),
            knownrow=False)
        vr, halts = [], []
        for x in logs:
            o = x.read_text(errors='replace').replace('\x00', '')
            n = x.parent.name[3:]
            if o.count('no contiguous'):
                vr.append('%s %d' % (n, o.count('no contiguous')))
            if bad.search(o):
                halts.append(n)
        add('VRAM no-contiguous 0', not vr, 'all rooms 0' if not vr else ', '.join(vr))
        add('census HALT/FAULT/MISSING 0', not halts, 'none' if not halts else ' '.join(halts))
    for n, _, _, rc in jobs:
        if n.startswith('cap-'):
            o = runlog(n)
            add(n, not bad.search(o), 'peak alive %s' % (max([int(x) for x in re.findall(r'warp: alive (\d+)', o)] or [0])))
        if n == 'kit':
            add('kit-check + kit-boot', rc == 0, (rd(J / 'kit.log').strip().splitlines() or ['no log'])[-1][:160])
        if n == 'relchecks':
            lg = rd(J / 'relchecks.log')
            v = re.findall(r'verdict rc=[^\n]*', lg)
            add('release checks (fp_gate)', bool(v) and 'rc=0' in v[-1], v[-1] if v else lg.strip()[-160:])

    # decisions pairs (full tier): decision_cmp verdict judges; logic_trace_diff STRICT is reported
    G = T / 'port/dreamcast/tools/game30'
    for w in ('h2', 'bell', 'door103', 'r11b'):
        r, t = EVU / ('st-%s-tR' % w) / 'run-output.txt', EVU / ('st-%s-tT' % w) / 'run-output.txt'
        if not (r.exists() and t.exists()):
            continue
        s = subprocess.run(['python3', str(G / 'logic_trace_diff.py'), str(r), str(t), '--align', 'frame', '--json', str(EVU / ('strict-%s.json' % w))],
                           capture_output=True, text=True)
        try:
            sv = json.loads((EVU / ('strict-%s.json' % w)).read_text()).get('verdict')
        except (OSError, ValueError):
            sv = 'n/a'
        d = subprocess.run(['python3', str(G / 'decision_cmp.py'), str(r), str(t), '--align', 'frame'], capture_output=True, text=True)
        (EVU / ('dcmp-%s.txt' % w)).write_text(d.stdout + d.stderr)
        vl = [l for l in d.stdout.splitlines() if 'verdict' in l.lower()]
        add('decisions ' + w, d.returncode == 0, 'decision_cmp: %s; STRICT: %s' % ((vl[0] if vl else 'rc=%d' % d.returncode)[:100], sv))

if (W / 'kit-skip.txt').exists():
    checks.append(('kit-check + kit-boot', 'SKIP', rd(W / 'kit-skip.txt').strip()))
fails = [c for c in checks if c[1] == 'FAIL']
verdict = 'PASS' if build_ok and jobs and not fails else 'FAIL'
(W / 'verdict.txt').write_text(verdict + '\n')

def hm(t):
    return time.strftime('%H:%M:%S', time.localtime(t))
lg = {}
lgp = RR_HOME / 'state/last-good'
if verdict == 'PASS':
    lg = {'sha': env['sha'], 'id': env['id'], 'image': image}
elif lgp.exists():
    lg = dict(l.split('=', 1) for l in lgp.read_text().splitlines() if '=' in l)
out = ['# RELEASE-READY (lane rr: always-ready release candidate)', '',
       'Updated %s by `rr-cycle.sh` (WSL watcher, every 10 min when origin/t15/int moves). Commands: `rr.sh status | cycle | full | package <tag>`.' % time.strftime('%Y-%m-%d %H:%M'), '']
if lg:
    out += ['**Last good candidate:** t15/int %s, image %s, cycle %s, disc `%s`.' % (lg.get('sha', '')[:8], lg.get('image', '')[:16], lg.get('id', ''),
            (lg.get('cand') or rd(W / 'cand.txt').strip()).replace('/mnt/c/', 'C:\\').replace('/', '\\') + '\\gdemu'), '']
else:
    out += ['**Last good candidate:** none yet.', '']
out += ['## This cycle: %s (%s tier)' % (verdict, tier), '',
        '- t15/int %s; recipe: %s' % (env['sha'][:8], subprocess.run(['bash', '-c', '. "%s/recipe.conf"; echo "$RR_RECIPE_NAME"' % BIN], capture_output=True, text=True).stdout.strip()),
        '- image (objcopy -R .stack) %s' % (image[:16] or 'n/a'),
        '- heap 4 before s30: %s' % (extra.get('s30_heap_before') or 'n/a'),
        '- KOS min headroom: %s' % (min(extra['kos_min_headroom']) if extra.get('kos_min_headroom') else 'n/a'),
        '- evidence: %s' % env.get('evw', ''), '',
        '| check | result | detail |', '|---|---|---|']
out += ['| %s | %s | %s |' % (n, s, d.replace('|', '/')) for n, s, d in checks]
if extra.get('not_drawn'):
    out += ['', 'NOT-DRAWN rows (judged, see the NOT-DRAWN check): ' + '; '.join(x.strip() for x in extra['not_drawn'])]
out += ['', '## Wall times', '', '| step | seconds |', '|---|---|']
out += ['| %s | %d |' % (n, e - s) for n, s, e, rc in steps]
if jobs:
    out += ['', 'Flycast jobs (%d, slots <= 12): first start %s, last end %s.' % (len(jobs), hm(min(j[1] for j in jobs)), hm(max(j[2] for j in jobs))), '',
            '| job | seconds | rc |', '|---|---|---|']
    out += ['| %s | %d | %d |' % (n, e - s, rc) for n, s, e, rc in sorted(jobs, key=lambda j: j[2] - j[1], reverse=True)]
out += ['', '## Diff since the last good candidate', '', '```']
out += rd(W / 'diff-log.txt').strip().splitlines()[:40] or ['(none)']
out += ['```', '', '## Knobs vs the newest published knob file', '', '```']
out += rd(W / 'knobs-diff.txt').strip().splitlines()[:40] or ['(not written)']
out += ['```', '']
(W / 'result.json').write_text(json.dumps({'verdict': verdict, 'checks': checks, 'steps': steps, 'jobs': jobs, 'extra': extra}, indent=1))
txt = '\n'.join(out) + '\n'
(W / 'RELEASE-READY.md').write_text(txt)
REPORT.write_text(txt)
print(verdict, '%d checks, %d failed' % (len(checks), len(fails)))
for c in fails:
    print('FAIL', c[0], c[2])
