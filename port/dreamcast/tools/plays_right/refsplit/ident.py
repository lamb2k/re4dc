"""ident.py <run A run-output.txt> <run B run-output.txt> [--prefixes LT,LE,LF,LU,LL] [--json out]

Trace identity of two old-game runs (lane eng-ref): the logic-trace lines (LT, LU, LL, LE, LF by default) in order,
compared line for line. Reports how many are identical, the first difference (both lines), and per prefix the first
differing tick. For the split proof: the split image with `rsplit 0` against the unsplit image must be identical;
with the split on, the first difference must be the generator state (LT r=) at or after the first presentation draw
(RS line).
"""
import argparse, json, re, sys


def lines(path, prefixes):
    out, rs = [], []
    for l in open(path, encoding='latin-1'):
        p = l[:3]
        if p.rstrip() in prefixes and l[2] == ' ' and l[3:5] == 't=':
            l = l.rstrip('\n')
            if p.startswith('LE'):   # work and vtable addresses differ between two images: not state
                l = re.sub(r' (a|vt)=[0-9a-f]+', '', l)
            out.append(l)
        elif l.startswith('RS t='):
            rs.append(l.strip())
    return out, rs


def tick(l):
    m = re.match(r'\w\w t=(\d+)', l)
    return int(m.group(1)) if m else -1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('a'); ap.add_argument('b')
    ap.add_argument('--prefixes', default='LT,LE,LF,LU,LL')
    ap.add_argument('--to', type=int, default=10 ** 9, help='last tick compared')
    ap.add_argument('--json')
    a = ap.parse_args()
    pre = set(a.prefixes.split(','))
    A, ars = lines(a.a, pre)
    B, brs = lines(a.b, pre)
    A = [l for l in A if tick(l) <= a.to]
    B = [l for l in B if tick(l) <= a.to]
    n = min(len(A), len(B))
    first = next((i for i in range(n) if A[i] != B[i]), None)
    same = first if first is not None else n
    res = dict(a=a.a, b=a.b, lines_a=len(A), lines_b=len(B), identical_prefix=same,
               identical=first is None and len(A) == len(B),
               last_tick_a=tick(A[-1]) if A else None, last_tick_b=tick(B[-1]) if B else None,
               first_rs_a=next((r for r in ars if not r.startswith('RS t=0 pd=0')), None),
               first_rs_b=next((r for r in brs if not r.startswith('RS t=0 pd=0')), None))
    if first is not None:
        la, lb = A[first], B[first]
        fa = dict(kv.split('=', 1) for kv in la.split()[1:] if '=' in kv)
        fb = dict(kv.split('=', 1) for kv in lb.split()[1:] if '=' in kv)
        res['first_difference'] = dict(index=first, tick=tick(la), a=la[:240], b=lb[:240],
                                       fields=[k for k in fa if fa.get(k) != fb.get(k)])
    print(json.dumps(res, indent=1))
    if a.json:
        open(a.json, 'w').write(json.dumps(res, indent=1))


if __name__ == '__main__':
    main()
