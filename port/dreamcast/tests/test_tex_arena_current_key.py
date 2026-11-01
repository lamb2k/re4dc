"""Actual texture classifier/allocator/load controls; no game data required."""
import importlib.util
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
TOOL = ROOT / "port/dreamcast/tools/d367/tex_arena_current_key/host_checks.py"
spec = importlib.util.spec_from_file_location("tex_arena_host_checks", TOOL)
checks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)


@unittest.skipUnless(shutil.which("g++"), "host C++ compiler required")
class TextureArenaAndFinalRefusal(unittest.TestCase):
    def test_actual_classifier_allocator_and_load(self):
        with tempfile.TemporaryDirectory(prefix="test-tex-arena-") as temporary:
            result = checks.run(Path(temporary), ROOT)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(len(result["variants"]), 10)
        for row in result["variants"]:
            self.assertEqual(row["stderr"], "")
            if row["kind"] == "arena":
                self.assertEqual(len(row["cases"]), 4)
            else:
                self.assertEqual(len(row["cases"]), 21)
                logged = [line for line in row["stdout"].splitlines() if line.startswith("REFUSAL TEX-REFUSE ")]
                self.assertEqual(len(logged), 17 if row["log"] else 0)


if __name__ == "__main__":
    unittest.main()
