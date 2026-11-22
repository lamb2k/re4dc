#!/usr/bin/env python3
"""crashcheck.py <serial> --crash A,B,.. [--clean C,D,..] [--control flipaddr|flippc|fliptick|noscreen]

The crash screen's check (lane eng-crash1; core/crash_screen.cpp, boot file CRASHCTL; build_console_disc.sh's
CRASH_CONTROLS scenes). On the serial log of a console-loop disc (Flycast or console):
  - each scene named by --crash, in schedule order, printed its "E1 CRASHCTL armed: ... expect code C pc P addr A" line,
    then the crash screen's serial copy: "CRASHSCREEN FAULT code C pc P pr .. addr A" with the planted event, pc and
    (for an address fault) address; "CRASHSCREEN <image> scene .. room .. tick T" with T the planted tick; and
    "CRASHSCREEN END rows N"; and the selector's "CDISC RESULT .. <name> FAILED state CRASHED .. why: CRASHED exc C pc P";
  - each scene named by --clean has "CDISC RESULT .. <name> OK" and no crash screen.
--control mutates the log first (one digit of the first screen's address, its pc or its tick changed, or the screens
removed): the check must then FAIL. Prints one line per scene and "CRASHCHECK PASS" or "CRASHCHECK FAIL"; exit 0 / 1.
"""
import argparse, re, sys

ap = argparse.ArgumentParser()
ap.add_argument('serial')
ap.add_argument('--crash', required=True)
ap.add_argument('--clean', default='')
ap.add_argument('--control', choices=['flipaddr', 'flippc', 'fliptick', 'noscreen'])
a = ap.parse_args()
text = open(a.serial, errors='replace').read().replace('\r', '')


def flip(m, g):
    s = m.group(0)
    i = m.start(g) - m.start(0) + len(m.group(g)) - 1
    return s[:i] + ('0' if s[i] != '0' else '1') + s[i + 1:]


if a.control == 'flipaddr':
    text = re.sub(r'CRASHSCREEN FAULT code \w+ pc \w+ pr \w+ addr (\w+)', lambda m: flip(m, 1), text, count=1)
elif a.control == 'flippc':
    text = re.sub(r'CRASHSCREEN FAULT code \w+ pc (\w+)', lambda m: flip(m, 1), text, count=1)
elif a.control == 'fliptick':
    text = re.sub(r'CRASHSCREEN \w+ scene \w+ room \w+ tick (\d+)', lambda m: flip(m, 1), text, count=1)
elif a.control == 'noscreen':
    text = '\n'.join(l for l in text.split('\n') if not l.startswith('CRASHSCREEN'))

lines = text.split('\n')
results = {}
for l in lines:
    m = re.match(r'CDISC RESULT \d+ (\S+) (OK|FAILED) state (\S+).*?(?: why: (.*))?$', l)
    if m: results[m.group(1)] = (m.group(2), m.group(3), m.group(4) or '')
# the armed lines and the screens, in order; a screen belongs to the armed line before it
arms = []
for i, l in enumerate(lines):
    m = re.search(r'E1 CRASHCTL armed: .* at tick (\d+), expect code (\w+) pc (\w+) addr (\S+)', l)
    if m:
        arms.append(dict(line=i, tick=int(m.group(1)), code=m.group(2), pc=m.group(3), addr=m.group(4)))
screens = [i for i, l in enumerate(lines) if l.startswith('CRASHSCREEN FAULT ')]
ok = True
crash = [s for s in a.crash.split(',') if s]
clean = [s for s in a.clean.split(',') if s]
if len(arms) != len(crash):
    print(f'armed lines {len(arms)}, crash scenes named {len(crash)}: WRONG'); ok = False
for k, name in enumerate(crash):
    bad = []
    if k >= len(arms):
        print(f'{name}: no armed line: WRONG'); ok = False; continue
    arm = arms[k]
    nxt = arms[k + 1]['line'] if k + 1 < len(arms) else len(lines)
    sc = [i for i in screens if arm['line'] < i < nxt]
    if not sc:
        bad.append('no crash screen')
    else:
        i = sc[0]
        m = re.match(r'CRASHSCREEN FAULT code (\w+) pc (\w+) pr (\w+) addr (\w+)', lines[i])
        if not m: bad.append('fault row does not parse')
        else:
            if m.group(1) != arm['code']: bad.append(f"code {m.group(1)} planted {arm['code']}")
            if m.group(2) != arm['pc']: bad.append(f"pc {m.group(2)} planted {arm['pc']}")
            if arm['addr'] != '-' and m.group(4) != arm['addr']: bad.append(f"addr {m.group(4)} planted {arm['addr']}")
        seg = lines[i:nxt]
        t = [re.match(r'CRASHSCREEN (\w+) scene (\w+) room (\w+) tick (\d+)', l) for l in seg]
        t = [x for x in t if x]
        if not t: bad.append('no scene row')
        elif int(t[0].group(4)) != arm['tick']: bad.append(f"tick {t[0].group(4)} planted {arm['tick']}")
        if not any(l.startswith('CRASHSCREEN END rows') for l in seg): bad.append('no END row')
    r = results.get(name)
    if not r: bad.append('no selector result')
    else:
        if r[0] != 'FAILED' or r[1] != 'CRASHED': bad.append(f'selector {r[0]} state {r[1]}')
        m = re.search(r'CRASHED exc (\w+) pc (\w+)', r[2])
        if not m: bad.append(f'selector reason "{r[2]}"')
        else:
            if int(m.group(1), 16) != int(arm['code'], 16): bad.append(f'selector exc {m.group(1)}')
            if int(m.group(2), 16) != int(arm['pc'], 16): bad.append(f'selector pc {m.group(2)}')
    tag = 'ok' if not bad else 'WRONG: ' + '; '.join(bad)
    print(f"{name}: planted code {arm['code']} pc {arm['pc']} addr {arm['addr']} tick {arm['tick']}: {tag}")
    ok &= not bad
for name in clean:
    r = results.get(name)
    tag = 'ok' if r and r[0] == 'OK' else f'WRONG: {r}'
    print(f'{name} (clean): selector {r[0] if r else "-"}: {tag}')
    ok &= tag == 'ok'
print('CRASHCHECK', 'PASS' if ok else 'FAIL', f'(control {a.control})' if a.control else '')
sys.exit(0 if ok else 1)
