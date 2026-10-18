"""ch5regen: scan every harvested tex*.pak (harvest.db files) for entries whose bytes match the still-missing
st3-pak-loose targets (by key and sha). Reads only index + same-size entries. Read-only.
usage: c5r_pakscan.py <harvest.db> <missing-src.tsv> <found.tsv> [extra pak paths...]"""
import sqlite3, struct, hashlib, sys, os
db, miss, found = sys.argv[1:4]
done = {l.split('\t')[0] for l in open(found)}
want = {}  # key -> (sha, size, path)
for l in open(miss):
    p, size, sha, run, s = l.rstrip('\r\n').split('\t')
    if p in done or 'st3-pak-loose' not in s:
        continue
    want[os.path.basename(p)[:-7]] = (sha, int(size), p)
print('want', len(want))
shas = {v[0]: k for k, v in want.items()}
c = sqlite3.connect(db)
paks = [r[0] for r in c.execute("select distinct path from files where path like '%.pak'")] + sys.argv[4:]
hits = {}
for pk in paks:
    if not os.path.exists(pk):
        continue
    try:
        with open(pk, 'rb') as f:
            h = f.read(2048)
            cnt, io, do = struct.unpack_from('<III', h, 12)
            if cnt == 0 or cnt > 200000 or do <= io:
                continue
            f.seek(io); idx = f.read(cnt * 16)
            keyed = 0
            for i in range(cnt):
                a, b, o, s = struct.unpack_from('<IIII', idx, i * 16)
                k = '%08x-%08x' % (a, b)
                if k in want:
                    keyed += 1
                    f.seek(o); d = f.read(s); hs = hashlib.sha256(d).hexdigest()
                    tag = 'MATCH' if hs == want[k][0] else 'key-only size %d vs %d' % (s, want[k][1])
                    print(tag, k, pk)
                    if hs == want[k][0]:
                        hits.setdefault(k, pk)
    except Exception as e:
        print('ERR', pk, e)
print('matched keys', len(hits), sorted(hits))
