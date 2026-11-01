#!/usr/bin/env python3
"""Synthetic closed barns, doors, cracks, LODs, dynamic walls and corrupt cells."""
from copy import deepcopy
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

import barn_portals29 as B
import graft_portals29 as G


def fixture(directory, openings=None, second_lod=None, dynamic=False, cull=0, room=0x103):
    """Only deliberately authored synthetic cuboids. No private source inputs."""
    module = B.codec()
    d = dict(schema=module.SCHEMA, meshes=[], parts=[], meshlets=[], vertices=[], commands=[],
             palette=[0xffffffff], part_lods=[], clusters=[], levels=[], classes=None, rules=None,
             materials=[], placements=[])
    openings = openings or {5: [(800, 1200, 0, 1200)], 0: [(1000, 1400, 800, 1200)]}
    index_bytes = 0
    for face in range(6):
        first = len(d["meshlets"])
        first_level = len(d["levels"])
        extent_min, extent_max = [65535] * 3, [0] * 3
        for li, holes in enumerate([openings] + ([] if second_lod is None else [second_lod])):
            plane = 2000 if face & 1 else 0
            axis = face // 2
            u, v = (axis + 1) % 3, (axis + 2) % 3
            cuts_u = sorted({0, 2000} | {p for h in holes.get(face, []) for p in h[:2]})
            cuts_v = sorted({0, 2000} | {p for h in holes.get(face, []) for p in h[2:]})
            vertices, strips = [], []
            for u0, u1 in zip(cuts_u, cuts_u[1:]):
                for v0, v1 in zip(cuts_v, cuts_v[1:]):
                    cu, cv = (u0 + u1) / 2, (v0 + v1) / 2
                    if any(h[0] < cu < h[1] and h[2] < cv < h[3] for h in holes.get(face, [])):
                        continue
                    first_corner = len(vertices)
                    for x, y in ((u0, v0), (u1, v0), (u1, v1), (u0, v1)):
                        q = [0, 0, 0]
                        q[axis], q[u], q[v] = int(plane * 8), int(x * 8), int(y * 8)
                        vertices.append(q + [0, 0, 0xffff])
                    strips.append([first_corner + k for k in (0, 1, 3, 2)])
            base = len(d["vertices"])
            d["vertices"].extend(vertices)
            low = [min(q[a] for q in vertices) for a in range(3)]
            high = [max(q[a] for q in vertices) for a in range(3)]
            extent_min = [min(a, b) for a, b in zip(extent_min, low)]
            extent_max = [max(a, b) for a, b in zip(extent_max, high)]
            sb = sum(len(s) + 1 for s in strips)
            ji = len(d["meshlets"])
            d["meshlets"].append([base, index_bytes, sb, len(vertices), len(strips), *low, *high])
            d["commands"].append(dict(pool=list(range(len(vertices))), strips=strips))
            d["levels"].append([ji, 1, float(li)])
            index_bytes += sb
        count = len(d["meshlets"]) - first
        d["parts"].append([0, 64, 0, 0, 0, 0, first, count, 0., 0., 1., 1.])
        d["part_lods"].append([face, 1])
        d["clusters"].append(extent_min + extent_max + [first_level, count])
        d["materials"].append([1 + face, 2 + face, 64, 64, 0, cull, 0, 0])
    d["meshes"].append([1, 0, 0, 0, 6, 0, 0, 6, 0., 0., 0., .125, .125, .125, 0., 0., 0., 2000., 2000., 2000.])
    d["placements"].append([0, 0, 1., 0., 0., 0., 0., 1., 0., 0., 0., 0., 1., 0.])
    mesh, policy = module.serialize_mesh(d), module.serialize_policy(d)
    module.decode(mesh, policy)
    ids = struct.pack("<4s3I", b"R4ID", 1, 1, struct.unpack_from("<I", policy, 20)[0]) + bytes([1 if dynamic else 255])
    ids += bytes(-len(ids) % 32)
    files = dict(mesh=("ps2-world.re4mesh", mesh), policy=("ps2-world.r4pw", policy), ids=("ps2-world.ids", ids))
    package = {}
    for kind, (name, data) in files.items():
        (directory / name).write_bytes(data)
        package[kind], package[kind + "_sha256"] = name, B.sha(data)
    return dict(schema=B.SCHEMA, room=hex(room), package=package, near_max=100, aperture_margin=64,
                houses=[dict(name="synthetic barn", hull=[[0, 0, 0], [2000, 2000, 2000]],
                             eye_boxes=[[[500, 500, 500], [1500, 1500, 1500]]])]), d


def portals(cell):
    w = struct.unpack_from("<16I", cell)
    start = 64 + 32 * w[9] + 28 * w[5]
    return [struct.unpack_from("<I5f", cell, start + i * 24) for i in range(w[6])]


def covers_exit(cell, axis, plane, u, v):
    return any(p[0] == axis and p[1] == plane and p[2] <= u <= p[3] and p[4] <= v <= p[5] for p in portals(cell))


def fix_crc(data):
    struct.pack_into("<I", data, 60, 0)
    struct.pack_into("<I", data, 60, B.crc(data))


class PortalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="portal29-synthetic-")
        self.directory = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_default_and_explicit_zero_write_nothing(self):
        for extra in ([], ["--barn-portals29=0"]):
            out = self.directory / "missing" / "cell"
            p = subprocess.run([sys.executable, str(Path(B.__file__)), *extra, "--config", "/does-not-exist",
                                "--out", str(out)], capture_output=True, text=True)
            self.assertEqual(p.returncode, 0)
            self.assertFalse(out.exists())

    def test_two_triangle_union_exactly_closes_face(self):
        q = B.Q
        outer = B.rectangle(q(0), q(10), q(0), q(10))
        a = [(q(0), q(0)), (q(10), q(0)), (q(0), q(10))]
        b = [(q(10), q(0)), (q(10), q(10)), (q(0), q(10))]
        self.assertEqual(B.subtract_all([outer], [a, b]), [])

    def test_exact_subtraction_preserves_submillimetre_slit(self):
        q = B.Q
        outer = B.rectangle(q(0), q(2000), q(0), q(2000))
        covers = [B.rectangle(q(0), q(1000), q(0), q(2000)),
                  B.rectangle(q(8001, 8), q(2000), q(0), q(2000))]
        holes = B.subtract_all([outer], covers)
        self.assertEqual(sum(B.area(h) for h in holes) / 2, q(250))

    def test_barn_door_and_window_have_outward_margin(self):
        config, _ = fixture(self.directory)
        cell, report = B.build(config, self.directory)
        self.assertEqual(report["summary"]["witnesses"], [(0, i) for i in range(6)])
        self.assertTrue(covers_exit(cell, 2, 2000, 736, 500))
        self.assertTrue(covers_exit(cell, 2, 2000, 1264, 1264))
        self.assertFalse(covers_exit(cell, 2, 2000, 1500, 500))
        self.assertTrue(covers_exit(cell, 0, 0, 1000, 800))
        self.assertEqual(cell, B.build(config, self.directory)[0])

    def test_small_crack_not_missed(self):
        config, _ = fixture(self.directory, openings={5: [(900, 900.125, 0, 2000)]})
        cell, _ = B.build(config, self.directory)
        self.assertTrue(covers_exit(cell, 2, 2000, 900.0625, 1000))
        self.assertFalse(covers_exit(cell, 2, 2000, 1200, 1000))

    def test_lod_opening_union_is_required(self):
        config, _ = fixture(self.directory, openings={5: [(900, 1100, 0, 800)]},
                            second_lod={5: [(700, 1300, 0, 1400)]})
        cell, _ = B.build(config, self.directory)
        self.assertTrue(covers_exit(cell, 2, 2000, 700, 1300))
        self.assertFalse(covers_exit(cell, 2, 2000, 1500, 1000))

    def test_wrong_side_faces_open(self):
        config, _ = fixture(self.directory, cull=2)
        cell, _ = B.build(config, self.directory)
        # Synthetic strips have +axis winding; high walls face outside.
        self.assertTrue(covers_exit(cell, 2, 2000, 10, 1900))

    def test_dynamic_walls_cannot_be_witnesses(self):
        config, _ = fixture(self.directory, dynamic=True)
        with self.assertRaisesRegex(ValueError, "witness"):
            B.build(config, self.directory)

    def test_cutout_wall_remains_wholly_open(self):
        config, doc = fixture(self.directory)
        doc["materials"][5][4] = 1
        policy = B.codec().serialize_policy(doc)
        (self.directory / "ps2-world.r4pw").write_bytes(policy)
        config["package"]["policy_sha256"] = B.sha(policy)
        ids = bytearray((self.directory / "ps2-world.ids").read_bytes())
        struct.pack_into("<I", ids, 12, struct.unpack_from("<I", policy, 20)[0])
        (self.directory / "ps2-world.ids").write_bytes(ids)
        config["package"]["ids_sha256"] = B.sha(ids)
        cell, report = B.build(config, self.directory)
        self.assertTrue(covers_exit(cell, 2, 2000, 10, 1900))
        self.assertNotIn((0, 5), report["summary"]["witnesses"])

    def test_non_coplanar_wall_is_open(self):
        config, _ = fixture(self.directory)
        config["houses"][0]["hull"][1][2] = 2001
        cell, _ = B.build(config, self.directory)
        self.assertTrue(covers_exit(cell, 2, 2001, 10, 1900))

    def test_doorway_or_near_plane_eye_refused(self):
        config, _ = fixture(self.directory)
        config["houses"][0]["eye_boxes"][0][0][2] = 163
        with self.assertRaisesRegex(ValueError, "inset"):
            B.build(config, self.directory)

    def test_package_hash_and_ids_crc_refusals(self):
        config, _ = fixture(self.directory)
        stale = deepcopy(config)
        stale["package"]["mesh_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "sha256"):
            B.build(stale, self.directory)
        ids = bytearray((self.directory / "ps2-world.ids").read_bytes())
        ids[12] ^= 1
        (self.directory / "ps2-world.ids").write_bytes(ids)
        config["package"]["ids_sha256"] = B.sha(ids)
        with self.assertRaisesRegex(ValueError, "CRC"):
            B.build(config, self.directory)

    def test_missing_ids_and_path_traversal_refused(self):
        config, _ = fixture(self.directory)
        config["package"]["ids"] = "../outside.ids"
        with self.assertRaisesRegex(ValueError, "within"):
            B.build(config, self.directory)

    def test_whole_file_checksum_covers_portal_and_boxes(self):
        config, _ = fixture(self.directory)
        cell, _ = B.build(config, self.directory)
        for offset in (64, 100, len(cell) - 1):
            bad = bytearray(cell)
            bad[offset] ^= 1
            with self.assertRaisesRegex(ValueError, "checksum"):
                B.verify_cell(bytes(bad))

    def test_structural_validation_even_with_recomputed_checksum(self):
        config, _ = fixture(self.directory)
        cell, _ = B.build(config, self.directory)
        w = struct.unpack_from("<16I", cell)
        portal_start = 64 + 32 * w[9] + 28 * w[5]
        bad = bytearray(cell)
        struct.pack_into("<I", bad, portal_start, 3)
        fix_crc(bad)
        with self.assertRaisesRegex(ValueError, "portal"):
            B.verify_cell(bytes(bad))
        bad = bytearray(cell)
        struct.pack_into("<f", bad, 64, float("nan"))
        fix_crc(bad)
        with self.assertRaisesRegex(ValueError, "house"):
            B.verify_cell(bytes(bad))

    def test_legacy_pcl2_size_gate_rejects_witness_extension(self):
        config, _ = fixture(self.directory)
        cell, _ = B.build(config, self.directory)
        w = struct.unpack_from("<16I", cell)
        self.assertNotEqual(len(cell), 64 + 32 * w[9] + 28 * w[5] + 24 * w[6])

    def test_other_room_and_multiple_houses(self):
        config, _ = fixture(self.directory, room=0x200)
        config["houses"] += deepcopy(config["houses"])
        cell, report = B.build(config, self.directory)
        self.assertEqual(report["summary"]["room"], 0x200)
        self.assertEqual(report["summary"]["houses"], 2)
        self.assertEqual(B.verify_cell(cell)["cells"], 2)

    def test_output_cli_and_no_overwrite(self):
        config, _ = fixture(self.directory)
        source = self.directory / "config.json"
        source.write_text(json.dumps(config))
        command = [sys.executable, str(Path(B.__file__)), "--barn-portals29=1", "--config", str(source),
                   "--package", str(self.directory), "--out", str(self.directory / "candidate.cell"),
                   "--report", str(self.directory / "report.json")]
        first = subprocess.run(command, text=True, capture_output=True)
        self.assertEqual(first.returncode, 0, first.stderr)
        second = subprocess.run(command, text=True, capture_output=True)
        self.assertEqual(second.returncode, 2)
        self.assertIn("already exist", second.stderr)

    def test_rounding_always_expands(self):
        for value in (B.Q(1, 3), B.Q(-1, 3), B.Q(1, 10**50), B.Q(-1, 10**50), B.Q(1000001, 7)):
            self.assertLessEqual(B.Q(B.outward(value, False)), value)
            self.assertGreaterEqual(B.Q(B.outward(value, True)), value)

    def test_graft_checks_matching_package_and_resolves_paths(self):
        config, _ = fixture(self.directory)
        cell, _ = B.build(config, self.directory)
        cell_path = self.directory / "candidate.cell"
        cell_path.write_bytes(cell)
        fix = dict(replace={"dc/native/r103/ps2-world.re4mesh": "ps2-world.re4mesh",
                            "dc/native/r103/ps2-world.r4pw": "ps2-world.r4pw",
                            "other/file": "other.bin"}, remove=["dc/native/r103/interior.cell", "old/file"],
                   preserved={"mode": 7})
        result = G.graft(fix, self.directory, cell_path)
        self.assertEqual(result["replace"]["dc/native/r103/interior.cell"], str(cell_path))
        self.assertEqual(result["remove"], ["old/file"])
        self.assertEqual(result["preserved"], {"mode": 7})
        self.assertTrue(Path(result["replace"]["other/file"]).is_absolute())
        missing = deepcopy(fix)
        del missing["replace"]["dc/native/r103/ps2-world.r4pw"]
        with self.assertRaisesRegex(ValueError, "explicitly stage"):
            G.graft(missing, self.directory, cell_path)

    def test_graft_default_disabled(self):
        out = self.directory / "absent.json"
        run = subprocess.run([sys.executable, str(Path(G.__file__)), "--fixture", "/absent", "--out", str(out)],
                             capture_output=True, text=True)
        self.assertEqual(run.returncode, 0)
        self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
