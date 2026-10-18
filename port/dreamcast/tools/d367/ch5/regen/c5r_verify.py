#!/usr/bin/env python3
"""ch5regen: match regenerated files to missing targets by sha256.
usage: c5r_verify.py <missing-src.tsv> <found.tsv(out, appended)> <dir>...
Prints per-dir counts; appends 'target_path<TAB>sha<TAB>file' lines for new matches."""
import hashlib, os, sys
want = {}
for line in open(sys.argv[1]):
    p, size, sha, run, s = line.rstrip('\n').split('\t')
    want.setdefault(sha, []).append(p)
done = set()
if os.path.exists(sys.argv[2]):
    for line in open(sys.argv[2]): done.add(line.split('\t')[1])
new = []
for d in sys.argv[3:]:
    n = m = 0
    for root, _, files in os.walk(d):
        for f in files:
            fp = os.path.join(root, f)
            if os.path.islink(fp): continue
            n += 1
            h = hashlib.sha256(open(fp, 'rb').read()).hexdigest()
            if h in want and h not in done:
                done.add(h); m += 1
                for p in want[h]: new.append('%s\t%s\t%s\n' % (p, h, fp))
    print(d, 'files', n, 'new-matches', m)
open(sys.argv[2], 'a').write(''.join(new))
tot = sum(len(v) for k, v in want.items() if k in done)
print('total matched targets', tot, 'of', sum(len(v) for v in want.values()))
