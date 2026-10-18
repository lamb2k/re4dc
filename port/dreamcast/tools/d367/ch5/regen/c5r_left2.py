"""ch5regen: list missing-src targets not yet in found.tsv. usage: c5r_left2.py <missing-src.tsv> <found.tsv>"""
import sys
done = {l.split('\t')[0] for l in open(sys.argv[2])}
for l in open(sys.argv[1]):
    p, size, sha, run, s = l.rstrip('\r\n').split('\t')
    if p not in done:
        print(p, sha[:8], s.split('/private/')[-1].split('/files/')[0] if '/private/' in s else s[-60:])
