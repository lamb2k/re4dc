#!/usr/bin/env python3
"""motion_hot.py <motion-residency-report.json> <out hot.json> <run-output.txt>... [--profile TEXT]
(lane ch5found16 round 4, 2026-10-16): a motion hot set for tools/prepare_enemy_motions.py --hot-audit, from Flycast runs.

Input archive: the enemy prepared with every FCV streamed (an empty hot audit, e.g. {"source_complete": false,
"union": {"source_arc_indices": []}}). Runs: a MOTION_MISS_LOG=1 build (game30.mk) with that archive on the disc; each
`motion miss #N: archive=<resident body bytes> entry=<record> bytes=<clip bytes> ...` line of the binding whose archive
size equals the report's resident_body_bytes names a clip the enemy played (an all-cold archive misses on every first
use). The record index is the report's entries[] order (checked: the logged clip size must equal entries[i].bytes).
Output: the --hot-audit format, union.source_arc_indices = those clips' ARC indices (ARC(n) numbering, as the enemy's
source names them), plus per-clip first-miss counts. Generic: any MOTION_SMALL enemy (em36, em39, Saddler em31 ...)."""
import json, re, sys

MISS = re.compile(r'motion miss #(\d+): archive=(\d+) entry=(\d+) bytes=(\d+)')


def main(a):
    prof = None
    if '--profile' in a:
        i = a.index('--profile'); prof = a[i + 1]; del a[i:i + 2]
    rep, out, logs = a[0], a[1], a[2:]
    r = json.load(open(rep))
    body, ents = r['resident_body_bytes'], r['entries']
    if any(e.get('hot') for e in ents):
        raise SystemExit('motion_hot: the report already has hot clips; use the all-cold preparation')
    seen, misses = {}, 0
    for f in logs:
        for ln in open(f, errors='replace'):
            m = MISS.search(ln)
            if not m or int(m.group(2)) != body:
                continue
            i, size = int(m.group(3)), int(m.group(4))
            if i >= len(ents) or ents[i]['bytes'] != size:
                raise SystemExit('motion_hot: %s: entry %d bytes %d does not match the report' % (f, i, size))
            misses += 1
            seen[i] = seen.get(i, 0) + 1
    if not seen:
        raise SystemExit('motion_hot: no motion miss line of archive %d in the logs' % body)
    arcs = sorted({x for i in seen for x in ents[i]['source_arc_indices']})
    hot_bytes = sum(ents[i]['bytes'] for i in seen)
    d = {'source_complete': False,
         'profile': prof or 'run-derived hot set (MOTION_MISS_LOG): clips played in %d run(s)' % len(logs),
         'union': {'source_arc_indices': arcs},
         'runs': logs, 'contract': r.get('contract'), 'source_sha256': r.get('source_sha256'),
         'clips': {str(ents[i]['source_arc_indices'][0]): {'entry': i, 'bytes': ents[i]['bytes'], 'misses': n}
                   for i, n in sorted(seen.items())},
         'hot_payload_bytes': hot_bytes, 'cold_clips': len(ents) - len(seen)}
    json.dump(d, open(out, 'w'), indent=1)
    print('motion_hot: %d of %d clips hot (%d B), %d miss lines, -> %s' % (len(seen), len(ents), hot_bytes, misses, out))


if __name__ == '__main__':
    main(sys.argv[1:])
