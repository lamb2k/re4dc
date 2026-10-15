#!/usr/bin/env python3
"""xmruns.py [--apply] file...: runs of >= 2 consecutive PSMTXMultVec / PSMTXMultVecSR statements through the same
matrix become RE4DC_XM_LOAD(m) + RE4DC_XM_POINT / RE4DC_XM_DIR (include/re4dc_xm.h; GAME_SH4ZAM_LOGIC). Knob off the
macros expand to the same PSMTX calls. A statement whose output aliases the matrix expression is not merged."""
import re, sys

PAT = re.compile(r'^(\s*)PSMTXMultVec(SR)?\(\s*([^,]+?)\s*,\s*([^,]+?)\s*,\s*([^;]+?)\s*\);\s*(//.*)?$')
apply = '--apply' in sys.argv
files = [a for a in sys.argv[1:] if not a.startswith('--')]
total = 0
for fn in files:
    src = open(fn, encoding='latin-1').read().split('\n')
    out = []
    i = 0
    nrun = 0
    while i < len(src):
        m = PAT.match(src[i])
        if not m:
            out.append(src[i]); i += 1; continue
        mat = m.group(3)
        j = i + 1
        while j < len(src):
            mj = PAT.match(src[j])
            if not mj or mj.group(3) != mat or mj.group(1) != m.group(1):
                break
            j += 1
        if j - i < 2:
            out.append(src[i]); i += 1; continue
        # the matrix must not be written by the run (outputs never name the matrix)
        mats = mat.replace(' ', '')
        bad = any(mats in PAT.match(src[k]).group(5).replace(' ', '') for k in range(i, j))
        if bad:
            out.extend(src[i:j]); i = j; continue
        ind = m.group(1)
        out.append(f'{ind}RE4DC_XM_LOAD({mat});')
        for k in range(i, j):
            mk = PAT.match(src[k])
            mac = 'RE4DC_XM_DIR' if mk.group(2) else 'RE4DC_XM_POINT'
            tail = (' ' + mk.group(6)) if mk.group(6) else ''
            out.append(f'{ind}{mac}({mat}, {mk.group(4)}, {mk.group(5)});{tail}')
        print(f'{fn}:{i+1}-{j}: {j-i} x {mat}')
        nrun += 1
        i = j
    if nrun:
        total += nrun
        if not any('re4dc_xm.h' in l for l in out):
            for k, l in enumerate(out):
                if l.startswith('#include'):
                    out.insert(k + 1, '#include "re4dc_xm.h" // GAME_SH4ZAM_LOGIC (lane sh4zam-direct)')
                    break
        if apply:
            open(fn, 'w', encoding='latin-1', newline='').write('\n'.join(out))
print('runs', total, 'applied' if apply else '(dry run)')
