"""Regression checks for fixtures that override the staging program selection."""
from pathlib import Path
import importlib.util
import json
import tempfile
import unittest

TOOL = Path(__file__).resolve().parents[1] / 'tools/d367/texchk/fixture_arm.py'
spec = importlib.util.spec_from_file_location('fixture_arm', TOOL)
arm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(arm)

class FixtureBootTest(unittest.TestCase):
    def test_explicit_stale_boot_and_overlay_are_retargeted(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); candidate = root / 'candidate'; candidate.mkdir()
            for name in ['1ST_READ.BIN', 'pl11.ovl']:
                (candidate / name).write_bytes(b'candidate')
            src, dst = root / 'in.json', root / 'out.json'
            src.write_text(json.dumps({'replace': {'1ST_READ.BIN': '/old/image', 'dc/pl11.ovl': '/old/overlay'}}))
            self.assertEqual(arm.main(['fixture_arm', str(src), str(dst), 'new', '--candidate-dir', str(candidate)]), 0)
            self.assertEqual(json.loads(dst.read_text())['replace'], {'1ST_READ.BIN': str(candidate / '1ST_READ.BIN'), 'dc/pl11.ovl': str(candidate / 'pl11.ovl')})

    def test_missing_explicit_boot_fails_without_output(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); src, dst = root / 'in.json', root / 'out.json'
            src.write_text(json.dumps({'replace': {'1ST_READ.BIN': '/old/image'}}))
            self.assertEqual(arm.main(['fixture_arm', str(src), str(dst), 'new', '--candidate-dir', str(root)]), 1)
            self.assertFalse(dst.exists())

    def test_absent_boot_keeps_staging_program_selection(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); src, dst = root / 'in.json', root / 'out.json'
            src.write_text(json.dumps({'replace': {'dc/warp.txt': '/warp'}}))
            self.assertEqual(arm.main(['fixture_arm', str(src), str(dst), 'new', '--candidate-dir', str(root)]), 0)
            self.assertNotIn('1ST_READ.BIN', json.loads(dst.read_text())['replace'])

if __name__ == '__main__':
    unittest.main()