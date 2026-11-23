#!/usr/bin/env python3
r"""re4_link_check.py: judge an RE4 engine run through dc-qalink's bridge (lane eng-link2, 2026-11-23;
docs/engine/CONSOLE_LOOP.md section 17). Python 3.10+, standard library only.

    re4_link_check.py <proof dir> [--expect full|rows]

Reads what tools/consoleloop/re4_bridge_proof.py wrote (<proof dir>/proof.json, sessions/*.jsonl: the bridge's session
records, sessions/report-<run>.txt) and checks, each a row PASS or FAIL:
  rows       live rows arrived (at least 100), every one with the room and Leon's position
  guards     the play-file guards (counters discopen, discread: opens and reads of a file inside play) stayed 0 in
             every record; the engine's report line "E1 FILES in play" says opens 0 reads 0 sector-requests 0
  steps      every step the proof recorded is ok
 (--expect full, the default for plan full, adds)
  grabs      at least 4 screen grabs with their CRC right
  menu       the menu's trace lane shows it opened and closed
  warps      the farm (r103) and then the village (r101) reached by the rows after the warps
  loads      room-entry times reported by the image (E1 QL LOADTIME / live log "load:")
Exit 0 when every row passes, 1 otherwise. Controls (must FAIL): plan readx (a pack read inside play: guards), plan
plain on the link-off image (SENDABLE=1 DCQL_ENABLE=0: no rows).
"""
import argparse, glob, json, os, re, sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('proof', nargs='+', help='one proof folder, or the halves of plan full (--part 1, --part 2)')
    ap.add_argument('--expect', choices=['full', 'rows'])
    a = ap.parse_args()
    pjs = [json.load(open(os.path.join(d, 'proof.json'), encoding='utf-8')) for d in a.proof]
    pj = dict(pjs[0], steps=[s for x in pjs for s in x.get('steps', [])])
    expect = a.expect or ('full' if pj.get('plan') == 'full' else 'rows')
    recs, reports = [], {}
    for d in a.proof:
        for f in sorted(glob.glob(os.path.join(d, 'sessions', '*.jsonl'))):
            for line in open(f, encoding='utf-8', errors='replace'):
                try:
                    recs.append(json.loads(line))
                except ValueError:
                    pass
        reports.update({os.path.basename(f)[7:-4]: open(f, encoding='utf-8', errors='replace').read()
                        for f in glob.glob(os.path.join(d, 'sessions', 'report-*.txt'))})
    rows_out = []

    def row(name, ok, seen):
        rows_out.append((name, ok, seen))
        print('%-8s %s  %s' % (name, 'PASS' if ok else 'FAIL', seen))

    rows = [r for r in recs if r.get('t') == 'row']
    with_x = [r for r in rows if isinstance(r.get('x'), dict) and r['x'].get('room') is not None and r['x'].get('pos')]
    row('rows', len(rows) >= 100 and len(with_x) == len(rows),
        '%d rows, %d with room and position' % (len(rows), len(with_x)))
    ctr = [r for r in recs if r.get('t') == 'ctr']
    bad = [(r.get('n'), r['v'].get('discopen'), r['v'].get('discread')) for r in ctr
           if (r.get('v') or {}).get('discopen') or (r.get('v') or {}).get('discread')]
    files = []
    for rid, t in reports.items():
        for m in re.finditer(r'E1 FILES in play: opens (\d+) reads (\d+) sector-requests (\d+)', t):
            files.append((rid, int(m.group(1)), int(m.group(2)), int(m.group(3))))
    bad_rep = [f for f in files if f[1] or f[2] or f[3]]
    row('guards', not bad and not bad_rep and bool(ctr),
        '%d counter records, %d with a file in play (first %s); reports: %s' %
        (len(ctr), len(bad), bad[:1], ', '.join('%s opens %d reads %d sectors %d' % f for f in files) or 'no E1 FILES line'))
    st = pj.get('steps', [])
    row('steps', bool(st) and all(s['ok'] for s in st), '%d of %d ok; failed: %s' %
        (sum(1 for s in st if s['ok']), len(st), [s['name'] for s in st if not s['ok']]))
    if expect == 'full':
        grabs = [r for r in recs if r.get('t') == 'still' and r.get('crc_ok')]
        row('grabs', len(grabs) >= 4, '%d grabs with CRC ok' % len(grabs))
        tr = [r.get('label') for r in recs if r.get('t') == 'trace']
        row('menu', 'menu open' in tr and 'menu closed' in tr, 'trace labels: %s' % [x for x in tr if 'menu' in (x or '')])
        rooms = [r['x']['room'] for r in with_x]
        i103 = rooms.index(0x103) if 0x103 in rooms else -1
        back = i103 >= 0 and 0x101 in rooms[i103:]
        row('warps', back, 'rooms in order: %s' % ' > '.join('%03x' % x for i, x in enumerate(rooms)
                                                             if i == 0 or rooms[i - 1] != x))
        loads = [r.get('msg') for r in recs if r.get('t') == 'log' and (r.get('msg') or '').startswith('load:')]
        row('loads', len(loads) >= 3, '; '.join(loads))
    ok = all(o for _, o, _ in rows_out)
    print('VERDICT %s (%s, plan %s, tier %s)' % ('PASS' if ok else 'FAIL', expect, pj.get('plan'), pj.get('tier')))
    json.dump({'verdict': ok, 'proofs': a.proof, 'rows': [{'row': n, 'ok': o, 'seen': s} for n, o, s in rows_out]},
              open(os.path.join(a.proof[0], 'check.json'), 'w'), indent=1)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
