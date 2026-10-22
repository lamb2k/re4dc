"""Explicit source-bound key selection, disabled pack identity and isolation."""
import copy
import pathlib
import json
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools/d367"))
sys.path.insert(0, str(ROOT / "tools/d367/mipmap21"))
import texpack
import compact_candidate as candidate
from test_compact_native_vq import raw


class SelectedCompactPack(unittest.TestCase):
    def setUp(self):
        self.inputs = {(1, 2): raw(), (3, 4): raw(1)}
        self.pack = texpack.build(self.inputs)[0]
        self.selection = dict(schema="re4dc-lossless-vq-selection-1",
            source_pack_sha256=candidate.sha(self.pack), scope="generated source-owned fixture",
            keys=[dict(key="00000001-00000002", package_sha256=candidate.sha(self.inputs[(1, 2)]),
                       owner_evidence=[dict(kind="generated fixture")])])

    def test_off_pack_exact_on_selected_key_only_and_complete_costs(self):
        control, off, before, after = candidate.build_candidate(self.pack, self.selection)
        self.assertEqual(control, self.pack)
        self.assertEqual(before, after)
        result, report, before, after = candidate.build_candidate(self.pack, self.selection, enabled=True)
        self.assertEqual(report["changed_keys"], 1)
        self.assertEqual(report["unchanged_keys"], 1)
        self.assertEqual(after[(3, 4)], before[(3, 4)])
        self.assertEqual(report["saved_payload_bytes"], 8192 - 3072)
        self.assertEqual(report["saved_archive_bytes"], len(self.pack) - len(result))
        texpack.verify(result)

    def test_mismatched_source_or_key_hash_missing_owner_duplicate_and_absent_refused(self):
        for kind in ("pack", "key", "owner", "duplicate", "missing", "empty"):
            selected = copy.deepcopy(self.selection)
            if kind == "pack":
                selected["source_pack_sha256"] = "bad"
            elif kind == "key":
                selected["keys"][0]["package_sha256"] = "bad"
            elif kind == "owner":
                selected["keys"][0].pop("owner_evidence")
            elif kind == "duplicate":
                selected["keys"] *= 2
            elif kind == "missing":
                selected["keys"][0]["key"] = "00000005-00000006"
            else:
                selected["keys"] = []
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                candidate.build_candidate(self.pack, selected, enabled=True)

    def test_pack_file_cli_is_receipt_bound_default_off_and_exclusive(self):
        with tempfile.TemporaryDirectory() as directory:
            d = pathlib.Path(directory)
            (d / "tex.pak").write_bytes(self.pack)
            (d / "selection.json").write_text(json.dumps(self.selection))
            receipt = {"dc/tex.pak": dict(size=len(self.pack), sha256=candidate.sha(self.pack))}
            (d / "manifest.json").write_text(json.dumps(receipt))
            command = [sys.executable, str(ROOT / "tools/d367/mipmap21/compact_candidate.py"),
                "--source-pack", str(d / "tex.pak"), "--release-manifest", str(d / "manifest.json"),
                "--selection", str(d / "selection.json"), "--output", str(d / "control")]
            subprocess.run(command, capture_output=True, check=True)
            self.assertEqual((d / "control/tex.pak").read_bytes(), self.pack)
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
            receipt["dc/tex.pak"]["sha256"] = "bad"
            (d / "manifest.json").write_text(json.dumps(receipt))
            command[-1] = str(d / "bad")
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
            self.assertFalse((d / "bad").exists())


if __name__ == "__main__":
    unittest.main()
