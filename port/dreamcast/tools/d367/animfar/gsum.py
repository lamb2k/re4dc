# gsum.py <run dir>...: gameplay-equivalence summary per gate run
import re, sys, os, collections
for d in sys.argv[1:]:
    p = os.path.join(d, 'run-output.txt')
    if not os.path.exists(p): print(os.path.basename(d), 'no log'); continue
    t = open(p, encoding='latin-1').read().splitlines()
    kills = [re.search(r'kill (0x..) hp<=0 at room frame (\d+)', l) for l in t]
    kills = [(m.group(1), int(m.group(2))) for m in kills if m]
    items = [re.search(r'item new no=\d+ id=(..) num=(\d+) pos=\S+ room (\w+) frame (\d+)', l) for l in t]
    items = [(m.group(1), int(m.group(4))) for m in items if m]
    an = [l for l in t if 'warp: animals' in l]
    alive = [l for l in t if l.startswith('warp: alive')]
    rooms = [re.search(r'room enter (\w+)', l).group(1) for l in t if 'warp: room enter' in l]
    halts = sum(1 for l in t if 'HALT' in l or 'RE4DC MISSING' in l or 'Out of memory' in l)
    ac = collections.Counter(re.search(r'alivecap: (\w+)', l).group(1) for l in t if 'alivecap:' in l)
    last = max([int(m.group(1)) for l in t for m in [re.search(r'frame (\d+)', l)] if m and 'warp: alive' in l] or [0])
    print(f"{os.path.basename(d):9s} rooms {rooms} last alive-frame {last} kills {len(kills)} {[k for k,_ in kills]} @ {[f for _,f in kills]}")
    print(f"          items {len(items)} {items}")
    print(f"          animals first/last: {an[0][14:60] if an else '-'} | {an[-1][14:60] if an else '-'}; alivecap {dict(ac)}; halts {halts}")
