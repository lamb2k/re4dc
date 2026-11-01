#!/usr/bin/env python3
"""Analytic, byte-identity, BVH/reference, mapping and refusal controls."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest

import character_light_bake as B
from bake_examples import fixture

HERE = Path(__file__).resolve().parent


class CharacterBakeTests(unittest.TestCase):
    def setUp(self):
        self.mesh_raw, self.source_raw, self.settings_raw = fixture("em12")
        self.mesh, self.settings = B.decode(self.mesh_raw), B.decode(self.settings_raw)

    def write_dataset(self, directory, files):
        for name, data in files.items():
            (directory / name).write_bytes(data)

    def test_absent_and_zero_preserve_all_input_bytes(self):
        # Even whitespace, CRLF, unknown fields and invalid JSON are copied in
        # the off arm: the tool is not silently canonicalizing legacy files.
        data = b'  {"untouched":"opaque source bytes"}\r\n\x00'
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "mesh").write_bytes(data)
            for name, flags in (("absent", []), ("zero", ["--bake-static-light", "0"])):
                result = subprocess.run([sys.executable, str(HERE / "character_light_bake.py"),
                    "bake", str(root / "mesh"), str(root / name), *flags], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual((root / name / "mesh.json").read_bytes(), data)
                self.assertFalse(B.verify_dataset(root / name)["enabled"])
            self.assertEqual((root / "absent/manifest.json").read_bytes(), (root / "zero/manifest.json").read_bytes())

    def test_source_rig_mesh_order_and_alpha_are_byte_identical(self):
        files = B.bake(self.mesh_raw, self.source_raw, self.settings_raw)
        self.assertEqual(files["mesh.json"], self.mesh_raw)
        self.assertEqual(files["source.json"], self.source_raw)
        table = B.decode(files["light-colours.json"])
        for index, (row, tri) in enumerate(zip(table["triangles"], self.mesh["triangles"])):
            self.assertEqual(row["triangle"], index)
            self.assertEqual(row["source_info"], tri["source_info"])
            self.assertEqual([c["vertex"] for c in row["corners"]], [c["vertex"] for c in tri["corners"]])
        self.assertEqual(B.decode(files["mesh.json"])["triangles"][0]["corners"][0]["colour_rgba8"][3], 93)
        with tempfile.TemporaryDirectory() as tmp:
            self.write_dataset(Path(tmp), files)
            self.assertEqual(B.verify_dataset(Path(tmp)), B.decode(files["manifest.json"]))

    def test_repeat_bake_is_deterministic(self):
        self.assertEqual(B.bake(self.mesh_raw, self.source_raw, self.settings_raw),
                         B.bake(self.mesh_raw, self.source_raw, self.settings_raw))

    def test_unoccluded_known_static_colour(self):
        self.settings.update(ambient_rgb=[0.25, 0.25, 0.25],
            directional_lights=[{"toward_light": [0, 2, 0], "rgb": [0.5, 0.25, 0.0]}],
            exclude_occluder_infos=[1], ao_strength=1.0, ao_floor=0.0)
        table = B.decode(B.bake(self.mesh_raw, self.source_raw, B.encoded(self.settings))["light-colours.json"])
        corner = table["triangles"][0]["corners"][1]
        self.assertEqual(table["palette_rgb8"][corner["colour_index"]], [191, 128, 64])
        authored = table["triangles"][0]["corners"][0]
        self.assertEqual(table["palette_rgb8"][authored["colour_index"]], [150, 75, 25])

    def test_occluder_reduces_ao_and_exclusion_restores_it(self):
        self.settings.update(ambient_rgb=[1, 1, 1], directional_lights=[], ao_strength=1.0, ao_floor=0.2)
        covered = B.bake(self.mesh_raw, self.source_raw, B.encoded(self.settings))
        covered_table = B.decode(covered["light-colours.json"])
        index = covered_table["triangles"][0]["corners"][1]["colour_index"]
        self.assertEqual(covered_table["palette_rgb8"][index], [51, 51, 51])
        self.settings["exclude_occluder_infos"] = [1]
        open_table = B.decode(B.bake(self.mesh_raw, self.source_raw, B.encoded(self.settings))["light-colours.json"])
        index = open_table["triangles"][0]["corners"][1]["colour_index"]
        self.assertEqual(open_table["palette_rgb8"][index], [255, 255, 255])

    def test_normal_seams_do_not_average(self):
        tri = deepcopy(self.mesh["triangles"][0])
        for corner in tri["corners"]:
            corner["normal"] = [0, -1, 0]
        self.mesh["triangles"].append(tri)
        self.settings.update(ambient_rgb=[0, 0, 0], ao_strength=0,
            directional_lights=[{"toward_light": [0, 1, 0], "rgb": [1, 1, 1]}])
        table = B.decode(B.bake(B.encoded(self.mesh), self.source_raw, B.encoded(self.settings))["light-colours.json"])
        top = table["triangles"][0]["corners"][1]["colour_index"]
        bottom = table["triangles"][-1]["corners"][1]["colour_index"]
        self.assertEqual(table["palette_rgb8"][top], [255, 255, 255])
        self.assertEqual(table["palette_rgb8"][bottom], [0, 0, 0])

    def test_bvh_matches_independent_full_scan(self):
        rng = random.Random(25)
        triangles = [tuple(tuple(rng.uniform(-20, 20) for _ in range(3)) for _ in range(3)) for _ in range(60)]
        triangles.append(((0, 0, 0), (0, 0, 0), (0, 0, 0)))
        bvh = B.Occluders(triangles)
        for _ in range(250):
            origin = tuple(rng.uniform(-25, 25) for _ in range(3))
            direction = B.unit(tuple(rng.uniform(-1, 1) for _ in range(3)))
            distance = rng.uniform(0.01, 80)
            reference = any(B.hits_triangle(origin, direction, tri, distance) for tri in triangles)
            self.assertEqual(bvh.hits(origin, direction, distance), reference)
        self.assertLess(bvh.triangle_tests, 250 * len(triangles))

    def test_synthetic_leon_and_em12_examples(self):
        for name in ("leon", "em12"):
            with self.subTest(name=name):
                files = B.bake(*fixture(name))
                table = B.decode(files["light-colours.json"])
                report = B.decode(files["manifest.json"])
                self.assertTrue(table["synthetic_fixture"])
                self.assertEqual(report["corners"], 9)
                self.assertEqual(report["unique_light_samples"], 7)
                self.assertEqual(table["runtime_contract"]["normal_light_evaluations_per_vertex"], 0)

    def test_reject_invalid_mesh_and_rig(self):
        mutations = [
            lambda m: m.update(source_sha256="0" * 64),
            lambda m: m["positions_mm"][0].__setitem__(0, float("nan")),
            lambda m: m["weights"][0].__setitem__(0, [99, 1.0]),
            lambda m: m["weights"][0].__setitem__(0, [0, -1.0]),
            lambda m: m["weights"][0].__setitem__(0, [0, 0.25]),
            lambda m: m["weights"][0].append([0, 0.5]),
            lambda m: m["bones"][1].update(id=0),
            lambda m: m["bones"][0].update(parent=1),
            lambda m: m["bones"][0].update(parent=99),
            lambda m: m["bones"][0].update(rest=[]),
            lambda m: m["triangles"][0]["corners"][0].update(vertex=99),
            lambda m: m["triangles"][0]["corners"][0].update(normal=[0, 0, 0]),
            lambda m: m["triangles"][0]["corners"][0].update(colour_rgba8=[255, 256, 0, 255]),
            lambda m: m["triangles"][0].update(source_info=-1),
            lambda m: m["triangles"][0]["corners"].pop(),
        ]
        for index, mutation in enumerate(mutations):
            with self.subTest(index=index):
                mesh = deepcopy(self.mesh)
                mutation(mesh)
                with self.assertRaises(ValueError):
                    B.bake(json.dumps(mesh).encode(), self.source_raw, self.settings_raw)

    def test_reject_invalid_settings(self):
        mutations = [{"ao_samples": 0}, {"ao_samples": 1025}, {"ao_samples": True},
                     {"ao_floor": -0.01}, {"ao_strength": 1.01}, {"ray_bias_mm": 400.0},
                     {"ao_distance_mm": 0.0}, {"ambient_rgb": [-1, 0, 0]}, {"unexpected": 1},
                     {"directional_lights": [{"toward_light": [0, 0, 0], "rgb": [1, 1, 1]}]},
                     {"exclude_occluder_infos": [100]}]
        for value in mutations:
            with self.subTest(value=value), self.assertRaises(ValueError):
                B.bake(self.mesh_raw, self.source_raw, B.encoded(value))

    def test_reject_duplicate_json_keys(self):
        with self.assertRaises(ValueError):
            B.settings_of(b'{"ao_samples":4,"ao_samples":8}')

    def test_verify_rejects_tampered_palette(self):
        files = B.bake(self.mesh_raw, self.source_raw, self.settings_raw)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_dataset(root, files)
            (root / "palette.rgb8").write_bytes(b"tamper")
            with self.assertRaisesRegex(ValueError, "dataset file changed"):
                B.verify_dataset(root)

    def test_verify_rejects_rebound_bad_mapping(self):
        files = B.bake(self.mesh_raw, self.source_raw, self.settings_raw)
        table = B.decode(files["light-colours.json"])
        table["triangles"][0]["corners"][0]["vertex"] = 5
        files["light-colours.json"] = B.encoded(table)
        manifest = B.decode(files["manifest.json"])
        manifest["files"]["light-colours.json"] = {"sha256": B.digest(files["light-colours.json"]),
                                                   "bytes": len(files["light-colours.json"])}
        files["manifest.json"] = B.encoded(manifest)
        with tempfile.TemporaryDirectory() as tmp:
            self.write_dataset(Path(tmp), files)
            with self.assertRaisesRegex(ValueError, "corner mapping"):
                B.verify_dataset(Path(tmp))

    def test_cli_refuses_existing_destination(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "mesh").write_bytes(self.mesh_raw)
            dest = root / "existing"
            dest.mkdir()
            (dest / "keep").write_bytes(b"unchanged")
            run = subprocess.run([sys.executable, str(HERE / "character_light_bake.py"), "bake",
                str(root / "mesh"), str(dest)], capture_output=True)
            self.assertEqual(run.returncode, 2)
            self.assertEqual((dest / "keep").read_bytes(), b"unchanged")
            self.assertFalse((dest / "mesh.json").exists())


if __name__ == "__main__":
    unittest.main()
