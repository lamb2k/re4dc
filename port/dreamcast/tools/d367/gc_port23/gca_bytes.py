#!/usr/bin/env python3
"""gca_bytes.py <catalog.json> [--json out] [--base catalog.json]   (lane gcleft26, 2026-10-26)

Report-only summary of a byte-following GC-ASSET catalog (make_catalog.sh with PROVENANCE_FOLLOW_BYTES=1): the rows
whose provenance is gc or unknown, counted per kind and per room / archive (st1/r101.dar -> r101, em/em12.drs -> em12,
everything else by its top directory). rr-gca.sh runs it each cycle; rr-judge.py shows it as the KNOWN row
"GC-ASSET (bytes)" (never FAIL) so the GameCube data the whole-file credit hides stays visible until it is converted.
--base: the default (whole-file credit) catalog of the same disc; the summary then also counts the rows that only
byte-following moves to gc.
"""
import argparse, collections, json, re, sys


def group(src):
    s = src.split('#', 1)[0].lower()
    m = re.search(r'(?:^|/)(r[0-9a-f]{3})[^/]*$', s) or re.search(r'(?:^|/)(em[0-9a-f]{2}|pl[0-9a-f]{2}|wep[0-9a-f]{2})[^/]*$', s)
    if m:
        return m.group(1)
    return s.split('/', 1)[0] if '/' in s else s or '?'


def rows(path):
    return json.load(open(path))['entries']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('catalog')
    ap.add_argument('--json')
    ap.add_argument('--base')
    a = ap.parse_args()
    e = rows(a.catalog)
    kinds = collections.Counter()
    rooms = collections.defaultdict(collections.Counter)
    for r in e:
        p = r.get('provenance')
        if p in ('gc', 'unknown'):
            kinds['%s %s' % (p, r['kind'])] += 1
            rooms[group(r.get('source', ''))][p] += 1
    moved = None
    if a.base:
        bp = {(r['kind'], r['id'], r.get('source')): r.get('provenance') for r in rows(a.base)}
        moved = collections.Counter(r['kind'] for r in e if r.get('provenance') == 'gc'
                                    and bp.get((r['kind'], r['id'], r.get('source'))) == 'ps2')
    gc = sum(v for k, v in kinds.items() if k.startswith('gc '))
    unk = sum(v for k, v in kinds.items() if k.startswith('unknown '))
    out = dict(gc=gc, unknown=unk, kinds=dict(sorted(kinds.items())),
               rooms={k: dict(v) for k, v in sorted(rooms.items())},
               moved_by_bytes=dict(sorted(moved.items())) if moved is not None else None)
    if a.json:
        json.dump(out, open(a.json, 'w'), indent=1)
    top = sorted(rooms.items(), key=lambda kv: -kv[1]['gc'])
    print('GC-ASSET (bytes): gc %d unknown %d%s; rooms %s' % (
        gc, unk, '' if moved is None else ' (byte-following moves %d ps2->gc: %s)' % (
            sum(moved.values()), ' '.join('%s=%d' % kv for kv in sorted(moved.items()))),
        ' '.join('%s=%d' % (k, v['gc']) for k, v in top if v['gc'])))
    return 0


if __name__ == '__main__':
    sys.exit(main())
