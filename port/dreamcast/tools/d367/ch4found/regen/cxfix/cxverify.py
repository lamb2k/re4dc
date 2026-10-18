#!/usr/bin/env python3
"""Compare replay output against cx-targets.tsv. usage: c4r-cxverify.py <targets.tsv> <outroot> [room...]
Prints per room/dir: target count, present, byte-exact, mismatched, absent; writes <outroot>/verify.tsv."""
import hashlib, sys, collections
from pathlib import Path

T = sys.argv[1]
OUT = Path(sys.argv[2])
rooms = set(sys.argv[3:])
P = '/root/probe/codex-cx-fixtures-20261013/output/'
stat = collections.defaultdict(collections.Counter)
rows = []
for l in open(T):
    src, s, z, h, lane, p = l.rstrip('\n').split('\t')
    if not src.startswith(P):
        continue
    rel = src[len(P):]
    room = rel.split('/')[0]
    if rooms and room not in rooms:
        continue
    key = (room, rel.split('/')[1])
    f = OUT / rel
    if not f.exists():
        r = 'absent'
    else:
        r = 'exact' if hashlib.sha256(f.read_bytes()).hexdigest() == s else 'diff'
    stat[key][r] += 1
    rows.append((rel, s, r))
for k in sorted(stat):
    print(k[0], k[1], dict(stat[k]))
tot = collections.Counter(r for _, _, r in rows)
print('TOTAL', dict(tot))
with open(OUT / 'verify.tsv', 'a') as f:
    for rel, s, r in rows:
        f.write('%s\t%s\t%s\n' % (rel, s, r))
