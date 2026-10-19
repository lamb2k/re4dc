#!/usr/bin/env python3
"""cast_gc.py --not-drawn scope (lane garr18, coordinator 10-19): characters only (ids 10..3f) by default.
A door (em41 cEmDoor) or box (em43 cEmBox) alive and in view with no NMRS row must not fail; an in-view character
with no row still fails; --max-id 0xff restores the literal rule."""
from pathlib import Path
import subprocess
import sys
import tempfile

TOOL = Path(__file__).resolve().parents[1] / 'tools/d367/cast_gc.py'

LOG = '\n'.join([
    'NMRS f=331 room=0201 id=00 ot=7 parts=119 infos=9 plan=L native=150 crowd=0 declined=0 registry_declined=0 absent=0 would=0',
    'NMRS f=331 room=0201 id=1b ot=0 parts=38 infos=1 plan=R native=150 crowd=0 declined=0 registry_declined=0 absent=0 would=0',
] + ['warp: alivelist room 201 frame %d ids 1b*1@1362/v1 41*2@1768/v1 43*10@11400/v1%s' % (30 * k, EXTRA)
     for k in range(1, 5) for EXTRA in ('',)]) + '\n'


def run(text, *args):
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / 'run-output.txt'
        p.write_text(text)
        r = subprocess.run([sys.executable, str(TOOL), '--not-drawn', str(p), *args], capture_output=True, text=True)
        return r.returncode, r.stdout


def main():
    rc, out = run(LOG)
    assert rc == 0, out
    assert 'em41' not in out and 'em43' not in out, out
    rc, out = run(LOG, '--max-id', '0xff')
    assert rc == 1 and 'em41' in out and 'em43' in out, out
    # an in-view character (em1c) with no draw row still fails under the default scope
    rc, out = run(LOG.replace('1b*1@1362/v1', '1b*1@1362/v1 1c*1@900/v1'))
    assert rc == 1 and 'em1c' in out, out
    print('cast_gc NOT-DRAWN scope: PASS')


if __name__ == '__main__':
    main()
