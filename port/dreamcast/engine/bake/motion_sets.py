"""motion_sets.py: a room's motion clip set from captured play (lane eng-svc3; SERVICES.md section 16).

The skeleton service logs every clip it binds ("skel: clip <address> identity <identity> baked" or "... not in the
pack: decoded from its keys"). The clips a room's actors play in its captures are the room's set: motion_keys.py
--set <file> bakes rows for those clips only; any other clip is decoded from its own keys at run time (exact, slower,
counted as "outside the pack"), so a capture that missed a clip costs time, not correctness. A capture's misses are
the clips to add at the next bake.

    python3 motion_sets.py --out r101.lst <run.log> [<run.log> ...]

Writes one identity a line (motion_keys.py --set reads identities and archive:entry labels alike).
"""
import argparse
import re
import sys

LINE = re.compile(r'skel: clip [0-9a-f]+ (?:\(\d+ joints, )?identity ([0-9a-f]{8})')


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', required=True)
    ap.add_argument('logs', nargs='+')
    a = ap.parse_args()
    ids, missed = set(), set()
    for path in a.logs:
        for line in open(path, errors='replace'):
            m = LINE.search(line)
            if not m:
                continue
            ids.add(m.group(1))
            if 'not in the pack' in line:
                missed.add(m.group(1))
    with open(a.out, 'w') as f:
        f.write('# %d clips from %d captures (motion_sets.py); %d of them were outside the pack\n' % (len(ids), len(a.logs), len(missed)))
        for i in sorted(ids):
            f.write(i + '\n')
    print('%s: %d clips (%d outside the pack in the captures)' % (a.out, len(ids), len(missed)), file=sys.stderr)


if __name__ == '__main__':
    main()
