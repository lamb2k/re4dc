#!/usr/bin/env python3
"""castgc/mkfix.py (lane castgc17): one warp per route room for the CAST-GC census runs (<= 60 s each), then the fixtures of both arms.
Warps go to tools/d367/castgc/warps/<room>.txt (in Git); fixtures to /root/probe/lanes-20261016/castgc/k/fix.
Arms: g16rW = the test 16 source (tag test-72871476-20261016, T15_FS= T15_WV=, data T16_DATA) and g17rW = t15/int
ch2/ch2-build.sh rW (data T17_DATA), both with NATIVE_MODEL_REGISTRY_CENSUS=1 NATIVE_MODEL_REGISTRY_CENSUS_PERIOD=150.
Door-entry warps (r10b / r10e / r11b) read /tmp/sr1.json (stage_route.py --stage 1 --json /tmp/sr1.json)."""
import json, os, re, subprocess, sys
from pathlib import Path

TREE = Path('/root/probe/lanes-20261016/castgc17/port/dreamcast/tools/d367')
T16 = Path('/root/probe/lanes-20261016/t16src/port/dreamcast/tools/d367')
OUT = TREE / 'castgc' / 'warps'
FIX = Path('/root/probe/lanes-20261016/castgc/k/fix')
OUT.mkdir(parents=True, exist_ok=True); FIX.mkdir(parents=True, exist_ok=True)

# room -> source: ('preset', name) | ('file', path in tools/d367) | ('door', None)
CH1 = {
    'r100': ('preset', 'r100-s20'), 'r101': ('preset', 'r101-bell-fight'), 'r102': ('file', 'worldtest16/warps/r102-c1.txt'),
    'r103': ('preset', 'r103-entry'), 'r104': ('preset', 'r104-entry-noevt'), 'r105': ('preset', 'r105-entry'),
    'r106': ('preset', 'r106-entry'), 'r107': ('preset', 'r107-entry'), 'r108': ('file', 'worldtest16/warps/r108-c1.txt'),
    'r109': ('preset', 'r109-entry'), 'r10a': ('file', 'worldtest16/warps/r10a-c1.txt'), 'r10b': ('door', None),
    'r10c': ('preset', 'r10c-entry'), 'r10e': ('door', None), 'r117': ('preset', 'r117-entry'),
    'r118': ('preset', 'r118-entry'), 'r119': ('file', 'ch4found/warps/vq-r119.txt'), 'r11a': ('preset', 'r11a-entry'),
    'r11b': ('door', None),
}
CH2 = {
    'r111': ('file', 'ch2/warps/k-r111.txt'), 'r112': ('file', 'ch2/warps/e-r112.txt'), 'r113': ('file', 'ch2/warps/k-r113.txt'),
    'r11c': ('file', 'ch2/warps/e-r11c.txt'), 'r11d': ('file', 'ch2/warps/k-r11d.txt'), 'r11e': ('file', 'ch2/warps/e-r11e.txt'),
    'r10f': ('file', 'ch2/warps/k-r10f.txt'), 'r11f': ('file', 'ch2/warps/e-r11f.txt'), 'r200': ('file', 'ch2/warps/k-r200.txt'),
}
DROP = re.compile(r'^(freeze|viewdist|dump|shot|still|quit|stop)\b')
sr = json.load(open('/tmp/sr1.json'))['rooms']


def door_in(room):
    for src, r in sorted(sr.items()):
        for d in r['doors']:
            if d['dst'] == room and src != room:
                return src, d
    sys.exit('no door into ' + room)


for room, (kind, arg) in {**CH1, **CH2}.items():
    if kind == 'preset':
        tmp = OUT / ('.' + room)
        subprocess.run([sys.executable, str(TREE / 'warp.py'), arg, '-o', str(tmp)], check=True, stdout=subprocess.DEVNULL)
        body = tmp.read_text().splitlines(); tmp.unlink(); src = 'warp.py preset ' + arg
    elif kind == 'file':
        body = (TREE / arg).read_text().splitlines(); src = 'tools/d367/' + arg
    else:
        frm, d = door_in(room)
        body = ['name cg-%s' % room, 'room 0x%s' % room[1:], 'pos %d %d %d' % tuple(d['pos']), 'ang %.3f' % d['angle'],
                'inv default', 'act 360 fwd 12']
        src = 'stage_route.py door %s no %d -> %s (dstPos / dstAngle)' % (frm, d['no'], room)
    body = [l for l in body if not DROP.match(l.strip())]
    if not any(l.strip() == 'god' for l in body):
        body.append('god')
    text = ['# lane castgc17 CAST-GC census warp for %s (<= 60 s): %s; still-capture lines (freeze / viewdist / dump) removed,'
            % (room, src), '# god added. Census build: NATIVE_MODEL_REGISTRY_CENSUS=1 NATIVE_MODEL_REGISTRY_CENSUS_PERIOD=150.'] + body
    (OUT / (room + '.txt')).write_text('\n'.join(text) + '\n')


def data_line(tools, name):
    return subprocess.run([sys.executable, '-c', "import importlib.util as u;s=u.spec_from_file_location('t','%s/test11/t11-fix.py');"
                           "m=u.module_from_spec(s);s.loader.exec_module(m);print(m.%s)" % (tools, name)],
                          check=True, capture_output=True, text=True).stdout.strip()


env = dict(os.environ, PKG_SRC='/root/probe/lanes-20261015/t15k/pkgsrc-t14cand')  # warn mode: the 22 short lists are chapter 4 (ch4found), outside this census
arms = [('g16rW', T16, data_line(T16, 'T16_DATA'), CH1), ('g17rW', TREE, data_line(TREE, 'T17_DATA'), {**CH1, **CH2})]
for lab, tools, data, rooms in arms:
    print(lab, data)
    for room in rooms:
        e = dict(env)
        if lab == 'g16rW':
            pass
        r = subprocess.run([sys.executable, str(tools / 'test11' / 't11-fix.py'), lab, str(FIX / ('%s-%s.json' % (room, lab))),
                            '--data', data, '--warp', str(OUT / (room + '.txt'))], env=e, capture_output=True, text=True)
        if r.returncode == 0:  # STAGE_OVL images (t15/int f7782076 T15_SO) need st1_x / st2_0 / sscrn: every candidate overlay
            fx = str(FIX / ('%s-%s.json' % (room, lab)))
            r = subprocess.run([sys.executable, str(TREE / 'texchk' / 'fixture_arm.py'), fx, fx + '.tmp', lab],
                               capture_output=True, text=True)
            if r.returncode == 0:
                os.replace(fx + '.tmp', fx)
        o = (r.stdout + r.stderr).strip().splitlines()
        print(lab, room, 'rc=%d' % r.returncode, o[-1][:160] if o else '')
