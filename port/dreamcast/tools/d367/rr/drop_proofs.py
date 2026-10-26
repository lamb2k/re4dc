#!/usr/bin/env python3
"""drop_proofs.py: DROP-PROOF release gate (lane purge-audit26, 2026-10-26).

  drop_proofs.py <tree> <knobs file> [<proofs.tsv>] [--json OUT]

Every drop / cut / empty decision the release recipe makes must have a row in rr/drop-proofs.tsv with its PS2 evidence
(the file and offset, or the source line, showing the PS2 does not draw it, or that we draw it another way). Drops are
enumerated from the tree, not from the table:
  ets      <room> et<id>00#<slot>   src/game/EtcModel.cpp g_ps2_ets_drop (PS2_ETS_MATCH=2)
  fxnone   <room|any> <crc-fnv>     port/dreamcast/game/platform/fx_none_cut.inc (FX_PS2_NONE_CUT)
  etmempty <room> <member>          tools/d367/purge24/gen24.sh EMP[] (--etm-empty; props24p window panes)
  knob     - <NAME=VALUE>           a knob of DROP_KNOBS set non-zero in the built knob list
A drop counts only when its knob is on in <knobs file> (resolved-knobs.txt / release-knobs.txt: K=V tokens).

Row verdicts (column 4):
  drop-ok            proved: evidence (column 5) must cite the PS2 file + offset or source line
  fixed:K=V          a wrong drop the recipe compensates; FAILS unless K=V is in the knob list
  delegated:<lane>   another lane owns the item (e.g. windows26 for the et0000 / et2500 panes)
  speed-cut          a deliberate speed cut (FX_LEVEL / FX_TRIM ...), not a PS2-absence claim
  unproven           evidence is the generator's claim only; reported, does not fail
  wrong              a known wrong drop with no fix yet; FAILS
FAIL: a drop with no row, an empty evidence column, a wrong row, or a fixed: row whose knob is not in the recipe.
Last line: "DROP-PROOF PASS|FAIL: n drops, n proved, n fixed, n delegated, n speed, n unproven, n missing, n bad".
"""
import json, re, sys
from pathlib import Path

DROP_KNOBS = ('PS2_ETS_MATCH', 'FX_PS2_NONE_CUT', 'EFM_PS2_CUT', 'FX_LEVEL', 'FX_TRIM', 'HAZE_SPRITE_CUT', 'ESP_CUT_EARLY',
              'FX_SPRITE_TRIM', 'FX_STRIP21', 'FOLIAGE_TRIM', 'GANADO_ATLAS_DROP', 'PRELOAD_SKIP_GCIDLE', 'GC_STUB_SKIP')


def knobs(path):
    out = {}
    for tok in Path(path).read_text(errors='replace').split():
        if '=' in tok:
            k, v = tok.split('=', 1)
            out[k.strip('"\'')] = v.strip('"\'')
    return out


def on(kn, k):
    return kn.get(k, '0') not in ('0', '')


def drops(tree, kn):
    out = []
    if on(kn, 'PS2_ETS_MATCH') and kn.get('PS2_ETS_MATCH') == '2':
        src = (tree / 'src/game/EtcModel.cpp').read_text()
        body = src[src.index('g_ps2_ets_drop[] = {'):]
        body = body[:body.index('};')]
        for room, ident, no in re.findall(r'\{0x([0-9a-fA-F]+), 0x([0-9a-fA-F]+), 0x([0-9a-fA-F]+)\}', body):
            out.append(('ets', 'r%03x' % int(room, 16), 'et%02x00#%d' % (int(ident, 16), int(no, 16))))
    if on(kn, 'FX_PS2_NONE_CUT'):
        inc = (tree / 'port/dreamcast/game/platform/fx_none_cut.inc').read_text()
        for room, c, f in re.findall(r'\{0x([0-9a-f]+), 0x([0-9a-f]{8}), 0x([0-9a-f]{8})\}', inc):
            out.append(('fxnone', 'any' if room == 'ffff' else 'r%03x' % int(room, 16), '%s-%s' % (c, f)))
    gen = tree / 'port/dreamcast/tools/d367/purge24/gen24.sh'
    if gen.exists():
        for room, members in re.findall(r'EMP\[(r[0-9a-f]{3})\]=([^;\s]+)', gen.read_text()):
            for m in members.split(','):
                out.append(('etmempty', room, m))
    for k in DROP_KNOBS:
        if on(kn, k):
            out.append(('knob', '-', '%s=%s' % (k, kn[k])))
    return sorted(set(out))


def main(argv):
    js = None
    if '--json' in argv:
        i = argv.index('--json'); js = argv[i + 1]; argv = argv[:i] + argv[i + 2:]
    tree, kpath = Path(argv[0]), argv[1]
    tsv = Path(argv[2]) if len(argv) > 2 else Path(__file__).with_name('drop-proofs.tsv')
    kn = knobs(kpath)
    rows = {}
    for line in tsv.read_text().splitlines():
        if not line.strip() or line.startswith('#'):
            continue
        f = line.split('\t')
        if len(f) < 5:
            print('BADROW %s' % line[:160]); continue
        rows[(f[0], f[1], f[2])] = (f[3], f[4])
    n = dict(drops=0, proved=0, fixed=0, delegated=0, speed=0, unproven=0, missing=0, bad=0)
    report = []
    for d in drops(tree, kn):
        n['drops'] += 1
        r = rows.get(d)
        if r is None:
            n['missing'] += 1; report.append(('MISSING', d, '')); continue
        verdict, ev = r
        if not ev.strip():
            n['bad'] += 1; report.append(('NOEVIDENCE', d, verdict)); continue
        if verdict == 'drop-ok':
            n['proved'] += 1
        elif verdict.startswith('fixed:'):
            k, _, v = verdict[6:].partition('=')
            if kn.get(k) == v:
                n['fixed'] += 1
            else:
                n['bad'] += 1; report.append(('FIX-NOT-IN-RECIPE', d, verdict))
        elif verdict.startswith('delegated:'):
            n['delegated'] += 1
        elif verdict == 'speed-cut':
            n['speed'] += 1
        elif verdict == 'unproven':
            n['unproven'] += 1; report.append(('UNPROVEN', d, ev[:100]))
        else:
            n['bad'] += 1; report.append(('WRONG' if verdict == 'wrong' else 'BADVERDICT', d, verdict))
    for tag, d, why in report:
        print('%s %s %s %s %s' % (tag, d[0], d[1], d[2], why))
    ok = n['missing'] == 0 and n['bad'] == 0
    if js:
        Path(js).write_text(json.dumps(dict(ok=ok, counts=n, report=[[t, list(d), w] for t, d, w in report]), indent=1))
    print('DROP-PROOF %s: %d drops, %d proved, %d fixed, %d delegated, %d speed, %d unproven, %d missing, %d bad'
          % ('PASS' if ok else 'FAIL', n['drops'], n['proved'], n['fixed'], n['delegated'], n['speed'], n['unproven'],
             n['missing'], n['bad']))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
