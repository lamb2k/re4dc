#!/usr/bin/env python3
"""cmp.py <control> <arm>...: hw-model comparison of SKIN_SH4ZAM / logic arms (MODELLED hw ms per frame).
Rows: whole-frame total, buckets, and the actor skinning functions; delta vs control; corrected = delta x factor."""
import csv, re, sys, os
E = '/mnt/c/Flycast-Evidence/re4-dreamcast/sh4zam-skin-20261015'
PAT = re.compile(sys.argv[1] if sys.argv[1].startswith('re:') and False else
                 r'avk_|pass_positions|coarse_skin|re4dc_shz|probe_dirs|owner_.*(palettes|bind)|MakeWeight|zam_|'
                 r'PSMTX|PSVEC|re4dc_sincosf|sinf$|cosf$|hitCheck|emSphere|AtCk|orientation|BoxWorld|memset|memcpy|movmem|'
                 r'L_store|L_al4')
FACTOR = float(os.environ.get('FACTOR', '1.25'))
def load(n):
    f = f'{E}/hwmodel-{n}/proj/rep/functions.tsv'
    rows = {}
    with open(f) as fh:
        for r in csv.DictReader(fh, delimiter='\t'):
            name = r['func'].replace('(anonymous namespace)::', '').split('(')[0]
            rows[name] = rows.get(name, 0.0) + float(r['hw_ms'])
            rows.setdefault('#insn:' + name, 0.0)
            rows['#insn:' + name] += float(r['insn_pf'])
    areas = {}
    af = f'{E}/hwmodel-{n}/proj/rep/areas.tsv'
    if os.path.exists(af):
        with open(af) as fh:
            for r in csv.DictReader(fh, delimiter='\t'):
                k = list(r.keys())
                areas[r[k[0]]] = float(r.get('hw_ms', r.get('hw', 0)) or 0)
    rep = open(f'{E}/hwmodel-{n}/proj/report.txt').read()
    m = re.search(r'hardware projection\s+([\d.]+)', rep)
    tot = float(m.group(1)) if m else 0
    return rows, areas, tot
args = sys.argv[1:]
c = args[0]
C, CA, CT = load(c)
for a in args[1:]:
    A, AA, AT = load(a)
    print(f'=== {a} vs {c}: total {AT:.2f} vs {CT:.2f} (delta {AT-CT:+.2f} MODELLED)')
    keys = sorted({k for k in list(C) + list(A) if not k.startswith('#') and PAT.search(k)},
                  key=lambda k: -max(C.get(k, 0), A.get(k, 0)))
    dsum = 0
    for k in keys:
        cv, av = C.get(k, 0), A.get(k, 0)
        if max(cv, av) < 0.004:
            continue
        d = av - cv
        dsum += d
        ci, ai = C.get('#insn:' + k, 0), A.get('#insn:' + k, 0)
        print(f'  {k[:44]:44s} {cv:7.3f} -> {av:7.3f}  {d:+7.3f}   insn {ci:9.0f} -> {ai:9.0f}')
    print(f'  sum of listed deltas {dsum:+.3f} MODELLED, corrected x{FACTOR} {dsum*FACTOR:+.3f}')
    for k in sorted(set(CA) | set(AA)):
        d = AA.get(k, 0) - CA.get(k, 0)
        if abs(d) >= 0.03:
            print(f'  area {k:30s} {CA.get(k,0):7.2f} -> {AA.get(k,0):7.2f} {d:+.2f}')
