import sys, collections, re
found = set(l.split('\t')[0] for l in open(sys.argv[2]))
c = collections.Counter(); left = []
for line in open(sys.argv[1]):
    p, size, sha, run, s = line.rstrip('\n').split('\t')
    k = re.sub(r'r3[0-9a-f]{2}', 'rXXX', '/'.join(s.split('/')[:8]))
    k = re.sub(r'/[0-9a-f]{8}-[0-9a-f]{8}\.re4tex$|/cache/[0-9a-f]+$', '', k)
    ok = p in found
    c[(k, ok)] += 1
    if not ok: left.append(line)
for k in sorted(set(x[0] for x in c)):
    print('%5d ok %5d left  %s' % (c[(k, True)], c[(k, False)], k))
print('found', len(found), 'left', len(left))
open(sys.argv[3], 'w').write(''.join(left))
