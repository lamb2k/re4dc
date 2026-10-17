# drlmap.py <files.txt (isoinfo -l)> <run dir> [offset]: map the DRL: drive reads inside the measured bench window to disc
# files (lane zeroread17). Prints per file: reads, sectors, threads; and the per-read list.
import re, sys, os, bisect, collections
lst, run = sys.argv[1], sys.argv[2]
off = int(sys.argv[3]) if len(sys.argv) > 3 else 150
ext = []  # (lba, sectors, path)
cur = '/'
for l in open(lst, encoding='latin-1'):
    m = re.match(r'Directory listing of (.*)$', l.strip())
    if m:
        cur = m.group(1); continue
    m = re.match(r'^[-d][-rwx]{9}\s+\d+\s+\d+\s+\d+\s+(\d+)\s+\S+\s+\d+\s+\d+\s+\[\s*(\d+)\s+\d+\]\s+(.*)$', l.rstrip())
    if not m:
        continue
    size, lba, name = int(m.group(1)), int(m.group(2)), m.group(3)
    if name == '..':
        continue
    path = cur if name == '.' else cur + name
    if name == '.':
        path = cur + '(dir)'
    ext.append((lba, max(1, (size + 2047) // 2048), path))
ext.sort()
starts = [e[0] for e in ext]


def find(sec):
    i = bisect.bisect_right(starts, sec) - 1
    best = None
    while i >= 0 and ext[i][0] > sec - 100000:
        if ext[i][0] <= sec < ext[i][0] + ext[i][1] and (best is None or ext[i][1] > best[1]):
            best = ext[i]
        if best and ext[i][0] < best[0]:
            break
        i -= 1
    return best[2] if best else '?%d' % sec


t = open(os.path.join(run, 'run-output.txt'), encoding='latin-1').read().splitlines()
inw = False
per = collections.OrderedDict()
rows = []
for l in t:
    if re.match(r'bench: scene \d+ begin', l): inw = True
    if re.match(r'bench: scene \d+ end', l): inw = False
    if not inw: continue
    m = re.match(r'DRL: (\w) sec=(\d+) n=(\d+) thr=(\S+)', l)
    if m:
        kind, sec, n, thr = m.group(1), int(m.group(2)), int(m.group(3)), m.group(4)
        f = find(sec - off)
        p = per.setdefault(f, [0, 0, set()]); p[0] += 1; p[1] += n if kind == 'S' else 0; p[2].add(thr + ':' + kind)
        rows.append((kind, sec, n, thr, f))
    elif l.startswith(('motion miss', 'native texture', 'native ui: load', 'texpack')) or 'tex load' in l:
        rows.append(('#', 0, 0, '', l[:150]))
for f, (r, s, th) in sorted(per.items(), key=lambda x: -x[1][0]):
    print('%4d reads %5d sectors  %-50s %s' % (r, s, f, ','.join(sorted(th))))
if '-v' in sys.argv:
    for r in rows: print(r)
