#!/usr/bin/env python3
"""End-to-end Build36 reports from public writers and bounded refusal cases."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import formats
import scan
import test_scan as fixtures
from test_world36 import legacy_fixtures


HERE = Path(__file__).resolve().parent
KEY = "11223344-99aabbcc"
OTHER = "11223345-99aabbcb"
KNOBS = {"TEX_PACK": "1", "TEX_RESIDENT": "1", "QUALITY_ASSETS": "0"}
REPORTS = {"details.tsv", "by-model.tsv", "by-room.tsv", "barn.tsv", "spawns.tsv",
           "coverage.tsv", "report.json", "context-template.json", "REPORT.md"}


def hashes(tree):
    return {p.relative_to(tree).as_posix(): formats.sha(p.read_bytes())
            for p in sorted(tree.rglob("*")) if p.is_file()}


class Scan36Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.legacy = legacy_fixtures()["v3-oct"]
        cls.pack = fixtures.module("scan36_existing_pack", HERE.parent / "texpack.py")

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.tree = fixtures.make_tree(self.root)

    def put(self, name, data):
        path = self.tree / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def run_scan(self, **kwargs):
        kwargs.setdefault("knobs", KNOBS)
        kwargs.setdefault("scan36", 1)
        return scan.scan_tree(self.tree, ["r103"], **kwargs)

    def global_archive(self):
        archive = fixtures.dar(fixtures.model_bin())
        self.put("em/em12.drs", formats.DRS_MAGIC + archive[32:])
        self.put("etc/emleon00.esl", fixtures.esl())

    def model(self, result, source):
        return next(m for m in result["model_inventory"] if m["source"] == source)

    def row(self, result, reason, key=KEY):
        return next(r for r in result["rows"] if r["reason"] == reason and r["material"] == key)

    def layer(self, name, keys):
        path = self.root / name
        payload = {tuple(int(x, 16) for x in key.split("-")): fixtures.texture(palette)
                   for key, palette in keys.items()}
        path.write_bytes(self.pack.build(payload)[0])
        return path

    def test_pack_over_loose_repairs_cross_file_collision_only_when_enabled(self):
        self.put("dc/tex/1/" + KEY + ".re4tex", fixtures.texture(False))
        old = self.run_scan(scan36=0)
        self.assertTrue(any("duplicate texture key" in c["message"] for c in old["coverage"]))
        new = self.run_scan()
        self.assertFalse(any("duplicate texture key" in c["message"] for c in new["coverage"]))
        selected = new["texture_selection"]["keys"][KEY]
        self.assertEqual(selected["selected_source"], "dc/tex.pak")
        self.assertEqual(len(selected["shadowed"]), 1)
        self.assertEqual(self.row(new, "tex_palette")["status"], "static")
        self.assertEqual(self.row(new, "resident_key_missing")["status"], "clear")
        self.assertEqual(new["textures"], 3)

    def test_known_pack_disabled_selects_canonical_loose(self):
        self.put("dc/tex/1/" + KEY + ".re4tex", fixtures.texture(False))
        result = self.run_scan(knobs=dict(KNOBS, TEX_PACK="0"))
        self.assertEqual(self.row(result, "tex_palette")["status"], "clear")
        self.assertEqual(result["texture_selection"]["keys"][KEY]["selected_source"],
                         "dc/tex/1/" + KEY + ".re4tex")
        self.assertEqual(self.row(result, "tex_missing", OTHER)["status"], "static")

    def test_unknown_pack_and_quality_keep_presence_and_palette_unknowns(self):
        self.put("dc/tex/1/" + KEY + ".re4tex", fixtures.texture(False))
        result = self.run_scan(knobs={"TEX_RESIDENT": "1", "QUALITY_ASSETS": "0"})
        self.assertIs(result["texture_selection"]["keys"][KEY]["present"], True)
        self.assertEqual(self.row(result, "tex_palette")["status"], "unknown")
        result = self.run_scan(knobs=dict(KNOBS, QUALITY_ASSETS="1"))
        self.assertEqual(self.row(result, "tex_missing")["status"], "unknown")
        self.assertEqual(self.row(result, "resident_key_missing")["status"], "unknown")

    def test_explicit_layers_replace_whole_pack_in_declared_order(self):
        first = self.layer("first.pak", {KEY: False})
        second = self.layer("second.pak", {OTHER: True})
        result = self.run_scan(texpak_layers=[first, second])
        self.assertEqual(result["textures"], 1)
        self.assertEqual(self.row(result, "tex_missing")["status"], "static")
        self.assertEqual(self.row(result, "resident_key_missing")["status"], "static")
        self.assertEqual(result["texture_selection"]["keys"][OTHER]["selected_source"],
                         "@texpak-layer/0002/second.pak")
        reverse = self.run_scan(texpak_layers=[second, first])
        self.assertEqual(self.row(reverse, "tex_missing")["status"], "clear")
        self.assertEqual(self.row(reverse, "tex_missing", OTHER)["status"], "static")

    def test_unordered_additional_pack_is_reported_not_selected(self):
        extra = self.layer("extra.pak", {KEY: False})
        result = self.run_scan(extra_inputs=[extra])
        self.assertEqual(result["texture_selection"]["keys"][KEY]["selected_source"], "dc/tex.pak")
        self.assertTrue(any(c["source"] == "@input/extra.pak" and c["status"] == "unsupported"
                            for c in result["coverage"]))

    def test_missing_and_malformed_last_layer_never_restore_old_pack(self):
        for path in (self.root / "missing.pak", self.root / "broken.pak"):
            if path.name == "broken.pak":
                path.write_bytes(b"bad pack")
            result = self.run_scan(texpak_layers=[path])
            self.assertEqual(result["status"], "INCOMPLETE")
            self.assertEqual(self.row(result, "tex_missing")["status"], "unknown")
            self.assertEqual(self.row(result, "resident_key_missing")["status"], "unknown")
            self.assertIsNone(result["texture_selection"]["referenced_keys"][KEY]["selected_source"])
            self.assertTrue(any(c["source"].startswith("@texpak-layer/") and c["status"] == "rejected"
                                for c in result["coverage"]))

    def test_bad_canonical_pack_path_produces_incomplete_unknowns(self):
        pack = self.tree / "dc/tex.pak"
        pack.unlink()
        pack.mkdir()
        result = self.run_scan()
        self.assertEqual(self.row(result, "tex_missing")["status"], "unknown")
        self.assertTrue(any(c["source"] == "dc/tex.pak" and c["status"] == "rejected" for c in result["coverage"]))

    def test_wrong_content_magic_in_loose_path_stays_a_rejected_texture(self):
        self.put("dc/tex/1/" + KEY + ".re4tex", (self.tree / "dc/tex.pak").read_bytes())
        result = self.run_scan(knobs=dict(KNOBS, TEX_PACK="0"))
        self.assertEqual(self.row(result, "tex_missing")["status"], "unknown")
        self.assertTrue(any(c["source"].endswith(".re4tex") and c["format"] == "texture"
                            and c["status"] == "rejected" for c in result["coverage"]))

    def test_native_list_binds_exact_global_archive_with_conditional_provenance(self):
        self.global_archive()
        result = self.run_scan()
        model = self.model(result, "em/em12.drs")
        self.assertEqual([m["room"] for m in model["memberships"]], ["r103"])
        member = model["memberships"][0]
        self.assertEqual(member["status"], "candidate")
        self.assertIsNone(member["instances"])
        evidence = result["room_membership"]["inventory"][member["evidence"][0]]
        self.assertEqual(evidence["source_sha256"], formats.sha((self.tree / "em/em12.drs").read_bytes()))
        self.assertIn(model["key"], evidence["model_keys"])
        self.assertEqual(len(evidence["loader_alternatives"]), 4)
        rows = [r for r in result["rows"] if r["source"] == "em/em12.drs"]
        self.assertTrue(rows)
        self.assertTrue(all(r["room"] == "r103" and r["membership"]["status"] == "candidate" for r in rows))
        old = self.run_scan(scan36=0)
        self.assertEqual(self.model(old, "em/em12.drs")["memberships"][0]["room"], "unassigned")

    def test_explicit_source_bound_room_entry_overrides_auto_count_and_label(self):
        self.global_archive()
        model = self.model(self.run_scan(), "em/em12.drs")
        room_list = dict(schema=scan.ROOM_LIST_SCHEMA, rooms={"r103": [dict(
            path=model["source"], model=model["key"], sha256=model["file_sha256"], instances=7, label="owner-verified") ]})
        result = self.run_scan(room_list=room_list)
        changed = self.model(result, "em/em12.drs")
        self.assertEqual(changed["label"], "owner-verified")
        self.assertEqual(changed["memberships"], [dict(room="r103", instances=7, origin="explicit room list")])
        self.assertTrue(result["room_membership"]["inventory"])

    def test_untouched_template_does_not_promote_or_retain_list_candidates(self):
        self.global_archive()
        first = self.run_scan()
        context = deepcopy(first["context_template"])
        entry = next(s for s in context["sources"] if s["path"] == "em/em12.drs")["models"][0]
        self.assertEqual(entry["rooms"], [])
        self.assertTrue(entry["room_candidates"])
        second = self.run_scan(context=context)
        self.assertEqual(self.model(first, "em/em12.drs")["memberships"], self.model(second, "em/em12.drs")["memberships"])
        (self.tree / "etc/emleon00.esl").unlink()
        third = self.run_scan(context=context)
        self.assertEqual(self.model(third, "em/em12.drs")["memberships"],
                         [dict(room="unassigned", instances=None, origin="unknown")])

    def test_missing_global_archive_stays_visible_in_membership_coverage(self):
        self.put("etc/emleon00.esl", fixtures.esl())
        result = self.run_scan()
        self.assertTrue(any(c["source"] == "em/em12.drs" and c["format"] == "room-membership"
                            and c["status"] == "missing" for c in result["coverage"]))

    def test_legacy_world_is_partial_geometry_not_actor_or_policy_prediction(self):
        self.put("dc/native/r103/old-world.re4mesh", self.legacy)
        result = self.run_scan()
        model = self.model(result, "dc/native/r103/old-world.re4mesh")
        self.assertEqual(model["kind"], "R4IM-legacy")
        self.assertIsNone(model["placements"])
        rows = [r for r in result["rows"] if r["source"] == model["source"]]
        self.assertTrue(rows)
        self.assertEqual({r["reason"] for r in rows}, {"legacy_world_geometry", "meshlet_inventory"})
        self.assertTrue(all(r["status"] == "inventory" for r in rows))
        self.assertTrue(any(c["source"] == model["source"] and c["status"] == "partial" for c in result["coverage"]))
        self.assertFalse(any(r["source"] == model["source"] for r in self.run_scan(scan36=0)["rows"]))

    def test_present_bad_policy_is_not_legacy_absence(self):
        self.put("dc/native/r103/old-world.re4mesh", self.legacy)
        policy = self.put("dc/native/r103/old-world.r4pw", b"")
        for kind in ("empty", "directory", "dangling"):
            if kind == "directory":
                policy.unlink()
                policy.mkdir()
            elif kind == "dangling":
                policy.rmdir()
                policy.symlink_to("missing.r4pw")
            result = self.run_scan()
            self.assertFalse(any(m["kind"] == "R4IM-legacy" for m in result["model_inventory"]))
            self.assertTrue(any(c["source"].endswith("old-world.re4mesh") and c["status"] == "rejected"
                                for c in result["coverage"]), kind)

    def test_modern_world_still_requires_policy(self):
        (self.tree / "dc/native/r103/ps2-world.r4pw").unlink()
        result = self.run_scan()
        self.assertFalse(any(m["kind"].startswith("R4IM") for m in result["model_inventory"]))
        self.assertTrue(any(c["source"].endswith("ps2-world.re4mesh") and c["status"] == "rejected"
                            for c in result["coverage"]))

    def test_enabled_report_is_deterministic_json_and_inputs_are_unchanged(self):
        self.global_archive()
        self.put("dc/native/r103/old-world.re4mesh", self.legacy)
        before = hashes(self.tree)
        first = self.run_scan()
        second = self.run_scan()
        self.assertEqual(first, second)
        json.dumps(first, sort_keys=True)
        self.assertEqual(hashes(self.tree), before)
        self.assertIn("Build 36", scan.render_report(first))
        self.assertIn("archive-load candidates", scan.render_report(first))

    def cli(self, *args, output="report"):
        out = self.root / output
        process = subprocess.run([sys.executable, "-B", str(HERE / "scan.py"), str(self.tree),
            "--out", str(out), "--rooms", "r103", *args], capture_output=True, text=True)
        return process, out

    def test_cli_enabled_outputs_and_partial_strict_exit(self):
        self.put("dc/native/r103/old-world.re4mesh", self.legacy)
        process, out = self.cli("--scan36=1", "--strict")
        self.assertEqual(process.returncode, 1, process.stderr)
        self.assertEqual({p.name for p in out.iterdir()}, REPORTS)
        report = json.loads((out / "report.json").read_text())
        self.assertEqual(report["scan36"], 1)
        self.assertIn("membership", (out / "details.tsv").read_text().splitlines()[0])
        self.assertIn("room_membership", report)

    def test_cli_layer_requires_mode_and_invalid_mode_has_no_output(self):
        layer = self.layer("layer.pak", {KEY: False})
        for args in (("--texpak-layer", str(layer)), ("--scan36=0", "--texpak-layer", str(layer)), ("--scan36=2",)):
            process, out = self.cli(*args)
            self.assertEqual(process.returncode, 2)
            self.assertFalse(out.exists())

    def test_cli_missing_layer_reports_unknown_without_old_pack_authority(self):
        process, out = self.cli("--scan36=1", "--texpak-layer", str(self.root / "missing.pak"), "--strict")
        self.assertEqual(process.returncode, 1, process.stderr)
        report = json.loads((out / "report.json").read_text())
        self.assertIsNone(report["texture_selection"]["referenced_keys"][KEY]["present"])

    def test_readable_input_and_policy_symlink_escape_still_refuse(self):
        outside = self.root / "outside.bin"
        outside.write_bytes(fixtures.model_bin())
        (self.tree / "escape.bin").symlink_to(outside)
        with self.assertRaisesRegex(formats.Invalid, "symlink escapes"):
            self.run_scan()
        (self.tree / "escape.bin").unlink()
        side = self.tree / "dc/native/r103/ps2-world.r4pw"
        outside.write_bytes(side.read_bytes())
        side.unlink()
        side.symlink_to(outside)
        result = self.run_scan()
        self.assertTrue(any(c["status"] == "rejected" and "symlink escapes" in c["message"] for c in result["coverage"]))


if __name__ == "__main__":
    unittest.main()
