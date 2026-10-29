"""Build36 synthetic world cases from the existing public scenery writers."""
import contextlib
import importlib.util
import io
from pathlib import Path
import struct
import sys
import unittest
from unittest import mock

import formats
import world36


HERE = Path(__file__).resolve().parent
DC = HERE.parents[2]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def modern_bundle():
    folder = HERE.parent / "world_blender_roundtrip"
    previous = sys.modules.get("package")
    sys.path.insert(0, str(folder))
    try:
        codec = module("world36_fixture_codec", folder / "package.py")
        sys.modules["package"] = codec
        fixture = module("world36_modern_fixture", folder / "fixtures.py")
        document = fixture.document()
        return codec.serialize_mesh(document), codec.serialize_policy(document)
    finally:
        sys.path.remove(str(folder))
        if previous is None:
            sys.modules.pop("package", None)
        else:
            sys.modules["package"] = previous


def legacy_fixtures():
    """Actual convert()/convert_lod() output, no hand-authored R4IM packages."""
    fixtures = module("world36_bin_fixture", DC / "tests/test_room_bins.py")
    writer = fixtures.C
    results = {"v1": fixtures.package([fixtures.fixture(), fixtures.fixture()])}
    positions = [(x * 100., 0., z * 100.) for z in range(5) for x in range(5)]
    triangles = []
    for z in range(4):
        for x in range(4):
            a = z * 5 + x
            triangles += [tuple((i, 0, i, 0) for i in tri)
                          for tri in ((a, a + 5, a + 1), (a + 1, a + 5, a + 6))]
    source = dict(flags=0, nvtx=len(positions), nparts=1, positions=positions,
        parts=[dict(offset=0, size=0, flags=0, texture=7, alpha=123, strips=[], loose=triangles)],
        uv=lambda i: (positions[i][0] / 400., positions[i][2] / 400.),
        normal=lambda i: (0., 1., 0.), color=lambda i: (255, 255, 255, 255), bytes=0)
    with contextlib.redirect_stdout(io.StringIO()):
        for share in (False, True):
            for color in ("oct", "prelit", "oct-vertex"):
                data, report = writer.convert_lod([(1, False, 0, None), (0xff, True, 7, None)], 1.,
                    source=lambda _: source, color_mode=color, share=share,
                    eps_world=(100., 1000.), min_gain=.99, max_levels=3,
                    classes={(1, 0): 2}, class_rules={2: (10, 50)})
                expected_version = 3 if share else 2
                assert report["version"] == expected_version
                results[f"v{expected_version}-{color}"] = data
    return results


def patched(data, offset, fmt, value, *, repair_crc=True):
    result = bytearray(data)
    struct.pack_into(fmt, result, offset, value)
    if repair_crc:
        struct.pack_into("<I", result, 12, formats.crc(result[80:]))
    return bytes(result)


class World36Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.legacy = legacy_fixtures()
        cls.modern, cls.policy = modern_bundle()

    def test_real_legacy_writers_all_versions_and_encodings(self):
        for name, data in self.legacy.items():
            with self.subTest(layout=name):
                result = world36.parse_world(data)
                h = world36.HEADER.unpack_from(data)
                self.assertEqual((len(result["models"]), result["parts"], result["meshlets"], result["stored_vertices"]),
                                 (h[4], h[5], h[6], h[7]))
                self.assertEqual(result["layout"], f"R4IM-v{h[1]}-legacy")
                self.assertEqual(result["color_encoding"], world36.COLOR_NAMES[h[16]])
                self.assertEqual(result["lod"], h[1] >= 2)
                self.assertEqual(result["metadata_status"], "incomplete")
                self.assertEqual(result["policy_status"], "not-stored-in-legacy-format")
                self.assertIsNone(result["placements"])
                self.assertTrue(result["limitations"])
                self.assertEqual(sum(len(p["meshlets"]) for m in result["models"] for p in m["parts"]), h[6])

    def test_geometry_and_material_unknowns_are_not_guessed(self):
        for name, data in self.legacy.items():
            with self.subTest(layout=name):
                result = world36.parse_world(data)
                for model in result["models"]:
                    self.assertEqual(model["kind"], world36.LEGACY_KIND)
                    self.assertIsNone(model["placements"])
                    self.assertIsNone(model["policy_sha256"])
                    self.assertNotIn("room", model)
                    self.assertEqual(model["source_sha256"], formats.sha(data))
                    self.assertEqual(model["source_bytes"], len(data))
                    for part in model["parts"]:
                        for field in ("texture_key", "texture_width", "texture_height", "pass_id", "cull", "vertex_alpha"):
                            self.assertIsNone(part[field], (name, field))
                        self.assertGreaterEqual(part["texture_index"], 0)
                        self.assertGreater(part["vertices"], 0)
                        level0 = [row for row in part["meshlets"] if row["level"] == 0]
                        self.assertEqual(part["vertices"], sum(row["vertices"] for row in level0))
                        self.assertEqual(part["corners"], sum(row["corners"] for row in level0))

    def test_indexed_and_empty_coarse_levels_keep_explicit_ownership(self):
        data = self.legacy["v3-oct"]
        result = world36.parse_world(data)
        lets = [row for model in result["models"] for part in model["parts"] for row in part["meshlets"]]
        self.assertTrue(any(row["indexed"] for row in lets))
        self.assertTrue(any(row["level"] > 0 for row in lets))
        h = world36.HEADER.unpack_from(data)
        lod = world36.LOD_HEADER.unpack_from(data, 80)
        levels = [world36.LEVEL.unpack_from(data, lod[4] + i * world36.LEVEL.size) for i in range(lod[1])]
        self.assertTrue(any(level[1] == 0 for level in levels))
        self.assertEqual(sorted(row["index"] for row in lets), list(range(h[6])))

    def test_legacy_read_is_pure_and_does_not_open_files(self):
        raw = bytearray(self.legacy["v1"])
        before = bytes(raw)
        with mock.patch.object(Path, "read_bytes", side_effect=AssertionError("unexpected file read")):
            result = world36.parse_world(raw)
        self.assertEqual(raw, before)
        self.assertEqual(result, world36.parse_world(before))

    def test_present_valid_policy_preserves_all_existing_result_fields(self):
        old = formats.parse_world(self.modern, self.policy)
        result = world36.parse_world(self.modern, self.policy)
        self.assertEqual({key: result[key] for key in old}, old)
        self.assertEqual(result["metadata_status"], "complete")
        self.assertEqual(result["policy_status"], "present-validated")

    def test_present_bad_policy_is_never_legacy_fallback(self):
        malformed = (b"", self.policy[:31], self.policy[:-1], b"BAD!" + self.policy[4:],
                     patched(self.policy, 20, "<I", 0, repair_crc=False))
        for data in (self.modern, self.legacy["v1"], self.legacy["v3-prelit"]):
            for policy in malformed:
                with self.subTest(mesh=formats.sha(data)[:8], policy_bytes=len(policy)):
                    with self.assertRaises(formats.Invalid):
                        world36.parse_world(data, policy)
        with mock.patch.object(formats, "parse_world", side_effect=formats.Invalid("strict refusal")) as parser:
            with self.assertRaisesRegex(formats.Invalid, "strict refusal"):
                world36.parse_world(self.legacy["v1"], b"present")
            parser.assert_called_once_with(self.legacy["v1"], b"present")

    def test_modern_missing_policy_is_not_accepted_as_legacy(self):
        with self.assertRaisesRegex(formats.Invalid, "PS2 world source owner"):
            world36.parse_world(self.modern)
        for marker in (b"SLI1", b"SDS1", b"SDO3"):
            with self.subTest(marker=marker):
                data = patched(self.modern, 76, "<I", int.from_bytes(marker, "little"))
                with self.assertRaisesRegex(formats.Invalid, "physical variant"):
                    world36.parse_world(data)
        with self.assertRaisesRegex(formats.Invalid, "not a supported ordinary legacy"):
            world36.parse_world(patched(self.modern, 4, "<I", 4))

    def test_short_size_and_crc_failures(self):
        for name, data in self.legacy.items():
            for size in (0, 4, 79, 80, 111, len(data) - 1):
                with self.subTest(layout=name, truncated=size), self.assertRaises(formats.Invalid):
                    world36.parse_world(data[:size])
            with self.subTest(layout=name, field="crc"), self.assertRaisesRegex(formats.Invalid, "CRC"):
                world36.parse_world(patched(data, 12, "<I", 0, repair_crc=False))
            with self.subTest(layout=name, field="size"), self.assertRaisesRegex(formats.Invalid, "size"):
                world36.parse_world(patched(data, 8, "<I", len(data) + 32))

    def test_offsets_counts_padding_and_extensions_fail_closed(self):
        data = self.legacy["v3-oct"]
        h = world36.HEADER.unpack_from(data)
        probes = [(40, "<I", h[10] + 1), (44, "<I", h[10]), (48, "<I", 80),
                  (16, "<I", 0xffffffff), (20, "<I", 0), (36, "<I", 17),
                  (64, "<I", 99), (68, "<I", h[13]), (72, "<I", 1), (108, "<I", h[15]),
                  (112, "<B", 1)]
        for at, fmt, value in probes:
            with self.subTest(at=at), self.assertRaises(formats.Invalid):
                world36.parse_world(patched(data, at, fmt, value))
        extended = bytearray(data + bytes(32))
        struct.pack_into("<I", extended, 8, len(extended))
        struct.pack_into("<I", extended, 12, formats.crc(extended[80:]))
        with self.assertRaisesRegex(formats.Invalid, "trailing"):
            world36.parse_world(bytes(extended))

    def test_mesh_part_grid_and_state_validation(self):
        data = self.legacy["v1"]
        h = world36.HEADER.unpack_from(data)
        probes = [(h[10] + 2, "<B", 2), (h[10] + 3, "<B", 0x50),
                  (h[10] + 12, "<I", 1), (h[10] + 16, "<I", h[5] + 1),
                  (h[10] + 20, "<f", float("nan")), (h[10] + 32, "<f", 0.),
                  (h[10] + 44, "<f", 1.e20), (h[11] + 11, "<B", 1),
                  (h[11] + 12, "<I", 1), (h[11] + 16, "<I", h[6] + 1),
                  (h[11] + 20, "<f", float("inf")), (h[11] + 28, "<f", 0.)]
        for at, fmt, value in probes:
            with self.subTest(at=at), self.assertRaises(formats.Invalid):
                world36.parse_world(patched(data, at, fmt, value))

    def test_meshlet_references_strips_palette_and_bounds_validation(self):
        data = self.legacy["v1"]
        h = world36.HEADER.unpack_from(data)
        probes = [(h[12], "<I", h[7]), (h[12] + 4, "<I", h[8]),
                  (h[12] + 8, "<I", h[8] + 1), (h[12] + 12, "<H", 257),
                  (h[12] + 14, "<H", 0), (h[12] + 14, "<H", 0x8001),
                  (h[12] + 16, "<H", 65535), (h[14], "<B", 2),
                  (h[14] + 1, "<B", 255), (h[13] + 10, "<H", 0xffff)]
        for at, fmt, value in probes:
            with self.subTest(at=at), self.assertRaises(formats.Invalid):
                world36.parse_world(patched(data, at, fmt, value))

    def test_lod_hierarchy_errors_and_indexed_pools_are_validated(self):
        data = self.legacy["v3-oct"]
        h = world36.HEADER.unpack_from(data)
        lod = world36.LOD_HEADER.unpack_from(data, 80)
        probes = [(lod[2], "<I", 1), (lod[2] + 4, "<I", lod[0] + 1),
                  (lod[3] + 12, "<I", 1), (lod[3] + 16, "<I", 0),
                  (lod[4], "<I", 1), (lod[4] + 4, "<I", h[6] + 1),
                  (lod[4] + 8, "<f", -1.), (lod[4] + 8, "<f", float("nan")),
                  (lod[5], "<B", 8)]
        for i in range(h[6]):
            row = world36.MESHLET.unpack_from(data, h[12] + i * world36.MESHLET.size)
            if row[4] & world36.INDEXED:
                probes += [(h[12] + i * world36.MESHLET.size + 4, "<I", row[1] + 1),
                           (h[14] + row[1], "<H", 65535)]
                break
        for at, fmt, value in probes:
            with self.subTest(at=at), self.assertRaises(formats.Invalid):
                world36.parse_world(patched(data, at, fmt, value))

    def test_oct_vertex_table_is_required_bounded_and_palette_zero(self):
        data = self.legacy["v3-oct-vertex"]
        h = world36.HEADER.unpack_from(data)
        for at, fmt, value in ((68, "<I", 0), (68, "<I", h[17] + 4),
                               (36, "<I", 2), (h[13] + 10, "<H", 0x1000)):
            with self.subTest(at=at), self.assertRaises(formats.Invalid):
                world36.parse_world(patched(data, at, fmt, value))


if __name__ == "__main__":
    unittest.main()
