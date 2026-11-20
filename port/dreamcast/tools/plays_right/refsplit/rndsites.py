"""rndsites.py <src root> [files...]: every call of the game generator (Rnd, fRand0_1, fRand1_1) with its enclosing
function (the last line at column 0 that opens a function) and the source line. TSV: file, line, function, call, text."""
import re, sys, os
root = sys.argv[1]
files = sys.argv[2:]
if not files:
    for d, _, fs in os.walk(root):
        for f in fs:
            if f.endswith(('.cpp', '.c')):
                files.append(os.path.relpath(os.path.join(d, f), root).replace(os.sep, '/'))
call = re.compile(r'\b(Rnd|fRand0_1|fRand1_1)\s*\(\s*\)')
fn = re.compile(r'^(?:[A-Za-z_][\w:<>\*&\s,]*?\s)?\**([A-Za-z_~][\w:~]*)\s*\(')
for rel in sorted(files):
    if rel.endswith('game/rnd.cpp'):
        continue
    lines = open(os.path.join(root, rel), encoding='latin-1').read().split('\n')
    cur = '?'
    for i, l in enumerate(lines):
        if l and not l[0].isspace() and not l.startswith(('#', '//', '/*', '{', '}')) and '(' in l \
                and not l.rstrip().endswith(';'):
            m = fn.match(re.sub(r'^extern "C"\s+', '', l))
            if m and m.group(1) not in ('if', 'for', 'while', 'switch', 'return'):
                cur = m.group(1)
        for m in call.finditer(l):
            s = l.strip()
            if s.startswith('//'):
                continue
            print('%s\t%d\t%s\t%s\t%s' % (rel, i + 1, cur, m.group(1), s[:150]))
