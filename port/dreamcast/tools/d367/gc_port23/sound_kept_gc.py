#!/usr/bin/env python3
"""sound_kept_gc.py <ps2_audio banks map.json>... > sound-kept-gc.tsv   (lane gcleft26, 2026-10-27; sound plan A)

Writes the reviewed list of wavetable samples that keep their GameCube PCM: the rows of a tools/ps2_audio.py banks map
(--json) whose sample got no PS2 VAG (ps2 null: no PS2 match at the matcher floor). A later map overrides an earlier
one for the same (file, block, sample), so pass the release-wide map first and the set maps after it.
Columns: file, block (spec#block name), sample, reason, owner.

The allowlist (allowlist.json) holds runtime identities (whole sound banks, which carry ps2 provenance), so per-sample
GameCube PCM is reviewed here instead. gca_bytes.py reads this file for the report-only "GC-ASSET (bytes)" row.
Regenerate: run ps2_audio.py banks on the release disc tree (default specs, then --files 'bgm/doorse.dat#*,em/pl14.drs')
and pass both maps.
"""
import json, sys

REASON = 'no PS2 match at matcher floor'
OWNER = 'gcleft26'


def main(paths):
    rows = {}
    for p in paths:
        for f in json.load(open(p))['files']:
            for b in f.get('blocks', []):
                for r in b.get('rows', []):
                    key = (f['spec'], b['name'], r['i'])
                    if r.get('ps2'):
                        rows.pop(key, None)
                    else:
                        rows[key] = True
    print('# sound-kept-gc.tsv: wavetable samples that keep GameCube PCM (gc_port23/sound_kept_gc.py; %d rows)' % len(rows))
    print('# file\tblock\tsample\treason\towner')
    for (spec, blk, i) in sorted(rows):
        print('%s\t%s\t%d\t%s\t%s' % (spec, blk, i, REASON, OWNER))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
