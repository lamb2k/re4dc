import sys, os, hashlib, collections
src = sys.argv[1]
c = collections.Counter(); hit = []
for line in open(src):
    path, size, sha, run, s = line.rstrip('\n').split('\t')
    k = '/'.join(s.split('/')[:6])
    if os.path.isfile(s):
        h = hashlib.sha256(open(s, 'rb').read()).hexdigest()
        if h == sha: c[(k, 'match')] += 1; hit.append(line)
        else: c[(k, 'differ')] += 1
    else: c[(k, 'gone')] += 1
for k, v in sorted(c.items()): print(v, *k)
open(sys.argv[2], 'w').write(''.join(hit))
