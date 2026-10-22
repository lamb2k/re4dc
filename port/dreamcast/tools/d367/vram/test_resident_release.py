#!/usr/bin/env python3
"""test_resident_release.py (lane residentbin22, 10-22): the release dc/resident.bin rebuilds byte for byte.

1. The shipped res18f (/root/re4data/private/fix18-20261018/resident.bin, sha256 a9dca43b..., Test 18 to Test 21)
   from lane/fix18's lists (commit d6e73099d, git archive of vram/resident + water/resident) via
   resident_keys.py release. Skipped when that commit is not in the checkout (public kit).
2. The current lists give the sha in vram/resident/RELEASE.sha256 (the release data set named there): a list edit
   without a rebuilt resident.bin and an updated RELEASE.sha256 fails here.
Run: python3 port/dreamcast/tools/d367/vram/test_resident_release.py
"""
import hashlib
import io
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
D367 = HERE.parent
sys.path.insert(0, str(HERE))
import resident_keys as RK  # noqa: E402

FIX18_COMMIT = 'd6e73099d'
FIX18_SHA = 'a9dca43b2b62e75235c6ae1cba0a1880fd18b0df6df61b3001a0441a724ce76d'
REL = 'port/dreamcast/tools/d367'


class ResidentRelease(unittest.TestCase):
    def test_fix18_rebuilds(self):
        top = subprocess.run(['git', '-C', str(D367), 'rev-parse', '--show-toplevel'], capture_output=True, text=True)
        if top.returncode:
            self.skipTest('not a git checkout')
        ar = subprocess.run(['git', '-C', top.stdout.strip(), 'archive', FIX18_COMMIT, REL + '/vram/resident',
                             REL + '/water/resident'], capture_output=True)
        if ar.returncode:
            self.skipTest('commit %s not in this checkout' % FIX18_COMMIT)
        with tempfile.TemporaryDirectory() as td:
            tarfile.open(fileobj=io.BytesIO(ar.stdout)).extractall(td)
            b, n = RK.release_bytes(Path(td) / REL)
        self.assertEqual(hashlib.sha256(b).hexdigest(), FIX18_SHA)
        self.assertEqual(len(b), 86528)

    def test_current_matches_pin(self):
        pin = (D367 / 'vram' / 'resident' / 'RELEASE.sha256').read_text().split()
        b, n = RK.release_bytes(D367)
        self.assertEqual(hashlib.sha256(b).hexdigest(), pin[0],
                         'vram/resident lists changed: rebuild resident.bin (resident_keys.py release) and update RELEASE.sha256')


if __name__ == '__main__':
    unittest.main()
