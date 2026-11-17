#!/usr/bin/env python3
"""island_motion_prov.py ROWS.tsv OUT.tsv REPORT.json...  (lane island-gca, 2026-11-17)
Reviewed rows for Disc 3 motion keys proven byte-identical to the PS2 clip. REPORT.json = motion/ps2_motion_prepared.py rewrite
report of an island archive against the PS2 USA ISO. When the report says every FCV member was compared (clips == fcv_members)
and none changed (fcv_changed == 0, seq_changed empty), every clip key the archive carries equals the PS2 entry of its slot:
those keys are credited to the PS2 archive. A report with changes credits only the unchanged clips that carry a key."""
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent / 'gc_port23'), str(HERE.parent)]
import build_catalog as bc  # noqa: E402
rows = [l.rstrip('\n').split('\t') for l in open(sys.argv[1]) if l.strip()]
want = {}
for r in rows:
    if r[1] == 'motion':
        want.setdefault(r[2], set()).add(r[3])
def keys_of(p):
    b = Path(p).read_bytes()
    bodies = [b] + ([b[bc.DRS_TABLE:]] if p.endswith('.drs') and len(b) > bc.DRS_TABLE else [])
    bodies += [body for _a, body in bc.record_bodies(b)]
    ks = set()
    for body in bodies:
        ks.update(k for k, _ in bc.motion_clips(body))
    return ks
out, got = [], set()
for rp in sys.argv[3:]:
    j = json.load(open(rp))
    whole = len(j['clips']) == j['fcv_members'] and j['fcv_changed'] == 0 and not j['seq_changed']
    ks = keys_of(j['payload']) if whole else {c['key'] for c in j['clips'] if c.get('key') and not c.get('changed', True)}
    for k in sorted(ks & set(want)):
        for h in want[k]:
            if (k, h) in got:
                continue
            got.add((k, h))
            out.append(('motion', k, h, h, 'PS2 USA BIO4DAT.AFS %s clip (same slot; the PS2 clip equals the island clip)' % j['ps2'],
                        'motion/ps2_motion_prepared.py rewrite report %s on %s: %s' % (
                            Path(rp).name, Path(j['payload']).name,
                            'all %d FCV members and every SEQ equal the PS2 entry (0 changed)' % j['fcv_members'] if whole else 'clip changed=false')))
open(sys.argv[2], 'w').write('\n'.join('\t'.join(x) for x in out) + '\n')
print('motion keys wanted', sum(len(v) for v in want.values()), 'proven', len(out))
for k, hs in want.items():
    for h in hs:
        if (k, h) not in got:
            print('UNPROVEN', k, h[:12])
