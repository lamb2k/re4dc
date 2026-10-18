"""arcaudit.py <src.cpp> [macro]: every ARC(n) use, by the innermost call it is an argument of (or the statement)."""
import re
import sys
from collections import defaultdict

src = open(sys.argv[1], errors='replace').read()
mac = sys.argv[2] if len(sys.argv) > 2 else 'ARC'
lines = src.split('\n')
starts = [0]
for l in lines:
    starts.append(starts[-1] + len(l) + 1)


def lineno(pos):
    lo, hi = 0, len(starts) - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if starts[mid] <= pos:
            lo = mid
        else:
            hi = mid - 1
    return lo + 1


out = defaultdict(list)
for m in re.finditer(r'\b%s\((0x[0-9A-Fa-f]+|\d+|[A-Za-z_][\w+\- ]*)\)' % mac, src):
    # walk back to find the innermost open paren
    depth = 0
    i = m.start() - 1
    while i >= 0:
        c = src[i]
        if c == ')':
            depth += 1
        elif c == '(':
            if depth == 0:
                break
            depth -= 1
        elif c in ';{}' and depth == 0:
            i = -1
            break
        i -= 1
    if i < 0:
        call = '<stmt>'
        argpos = -1
    else:
        j = i - 1
        while j >= 0 and src[j] == ' ':
            j -= 1
        k = j
        while k >= 0 and (src[k].isalnum() or src[k] in '_:.>-'):
            k -= 1
        call = src[k + 1:j + 1] or '<paren>'
        # argument position
        seg = src[i + 1:m.start()]
        d = 0
        argpos = 0
        for c in seg:
            if c in '([':
                d += 1
            elif c in ')]':
                d -= 1
            elif c == ',' and d == 0:
                argpos += 1
    ln = lineno(m.start())
    out[(call, argpos)].append((m.group(1), ln, lines[ln - 1].strip()[:110]))
for (call, pos), v in sorted(out.items(), key=lambda kv: (-len(kv[1]), kv[0])):
    ids = sorted(set(x[0] for x in v), key=lambda s: int(s, 0) if re.match(r'^(0x[0-9A-Fa-f]+|\d+)$', s) else 1 << 30)
    print('%-28s arg%-2d n=%-3d ids=%s' % (call, pos, len(v), ' '.join(ids)))
    if '-v' in sys.argv or call in ('<stmt>', '<paren>'):
        for x in v[:12]:
            print('      L%d %s' % (x[1], x[2]))
