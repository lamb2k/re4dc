#!/usr/bin/env python3
"""Selection, source-owner, atlas-boundary and preservation regression gates."""
import copy
import json
from pathlib import Path
import struct
import sys
import unittest

import actor_candidate as actor
sys.path.insert(0, str(actor.TOOLS.parent / "tests"))
from test_mipmap_vq import native


def registry(key=(1, 2), size=8):
    uv = struct.pack("<8H", 0, 0, 32768, 0, 32768, 32768, 0, 32768)
    bodies = [b"actor\0".ljust(16, b"\0") + struct.pack("<8I", 512, 1, 4, 1, 0, 0, 0, 0),
              struct.pack("<4I", 0, 0, 0, 0),
              struct.pack("<16I", 4, 4, 1, 2, 16, len(uv), 16, 4, 0, 0, 0, 0, 0, 0, 0, 0),
              uv, struct.pack("<4I", *key, size, size)] + [b""] * 7
    counts = [1, 1, 1, len(uv), 1] + [0] * 7
    table, tail, at = [], bytearray(), 256
    for i, (b, n) in enumerate(zip(bodies, counts), 1):
        table.append(struct.pack("<4I", i, at, len(b), n))
        tail += b + bytes(actor.rounded(len(b), 32) - len(b))
        at += actor.rounded(len(b), 32)
    header = b"RE4NMR1\0" + struct.pack("<14I", 1, 64, at, 12, 64, 0, 0x100, 0, 0, 0, 512, 4, 0, 0)
    return header + b"".join(table) + tail


def fixture():
    package = native()
    protected = actor.parse_key(sorted(actor.PROTECTED_GANADO)[0])
    pack = actor.texpack.build({(1, 2): package, (3, 4): native(fmt=1), protected: native()})[0]
    proof = registry()
    contract = dict(schema=actor.SCHEMA, source_pack_sha256=actor.sha(pack),
                    proofs=[dict(id="registry", sha256=actor.sha(proof), path="unused")],
                    textures=[dict(key="00000001-00000002", source_package_sha256=actor.sha(package),
                                   dimensions=[8, 8], binding=dict(kind="native-registry", proof="registry"),
                                   sampling=dict(kind="owned-native-atlas"))])
    return pack, contract, {"registry": proof}


class ActorCandidates(unittest.TestCase):
    def test_disabled_is_exact_and_only_explicit_actor_is_selected(self):
        pack, contract, proofs = fixture()
        replacements, report = actor.build_candidate(pack, contract, proofs)
        self.assertEqual(replacements[(1, 2)], actor.read_pak(pack)[(1, 2)])
        self.assertEqual(report["changed_keys"], 0)
        self.assertEqual(report["extra_allocation_request_bytes"], 0)
        self.assertEqual(report["unselected_packages"], 2)
        self.assertEqual(len(report["protected_existing_ganado"]), 1)

    def test_enabled_preserves_vq_base_and_takes_no_alpha_or_other_owner(self):
        pack, contract, proofs = fixture()
        replacements, report = actor.build_candidate(pack, contract, proofs, enabled=True, engine="python")
        before = actor.mip.read_native_vq(actor.read_pak(pack)[(1, 2)])
        after = actor.mip.read_native_vq(replacements[(1, 2)])
        self.assertEqual(before.codebook, after.codebook)
        self.assertEqual(before.base_indices, after.base_indices)
        self.assertEqual(len(replacements), 1)
        self.assertEqual(report["changed_keys"], 1)
        self.assertEqual(report["textures"][0]["owner"]["descriptors"][0]["name"], "actor")
        self.assertFalse(report["textures"][0]["sampling"]["runtime_mip_adoption_accepted"])

    def test_changed_pack_package_or_consumer_proof_refuses(self):
        pack, contract, proofs = fixture()
        for change in ("pack", "package", "proof", "dimensions", "duplicate", "owner"):
            c, p = copy.deepcopy(contract), dict(proofs)
            if change == "pack": c["source_pack_sha256"] = "0" * 64
            elif change == "package": c["textures"][0]["source_package_sha256"] = "0" * 64
            elif change == "proof": p["registry"] += b"x"
            elif change == "dimensions": c["textures"][0]["dimensions"] = [16, 16]
            elif change == "duplicate": c["textures"] *= 2
            else:
                p["registry"] = registry((5, 6))
                c["proofs"][0]["sha256"] = actor.sha(p["registry"])
            with self.subTest(change=change), self.assertRaises(ValueError):
                actor.build_candidate(pack, c, p)

    def test_protected_ganado_key_refuses_even_when_declared(self):
        pack, contract, proofs = fixture()
        contract["textures"][0]["key"] = sorted(actor.PROTECTED_GANADO)[0]
        with self.assertRaisesRegex(ValueError, "protected"):
            actor.build_candidate(pack, contract, proofs)

    def test_registry_requires_actual_geometry_use(self):
        b = bytearray(registry())
        refs_at = struct.unpack_from("<I", b, 64 + 16 + 4)[0]
        struct.pack_into("<I", b, refs_at + 4, 1)
        with self.assertRaisesRegex(ValueError, "no primary geometry"):
            actor.registry_binding(bytes(b), "00000001-00000002", [8, 8])

    def test_atlas_audit_identifies_coarse_cross_tile_sampling_and_excludes_hair(self):
        tiles = {"left": dict(x=0, y=0, width=8, height=16, inner_width=4, inner_height=12),
                 "right": dict(x=8, y=0, width=8, height=16, inner_width=4, inner_height=12)}
        mesh = dict(triangles=[dict(source_info=0, corners=[dict(uv=[.25, .5])] * 3),
                               dict(source_info=7, corners=[dict(uv=[1.5, 1.5])] * 3)])
        result = actor.atlas_boundaries(tiles, mesh, 16)
        self.assertEqual(result["triangles"], 1)
        self.assertEqual(result["sampled_corners"], 3)
        self.assertEqual(result["levels"][-1]["corner_footprints_crossing_tile"], 0)
        self.assertGreater(result["levels"][0]["corner_footprints_crossing_tile"], 0)
        self.assertGreater(result["levels"][0]["box_cells_mixing_tile_owners"], 0)

    def test_atlas_unknown_corner_and_cross_tile_triangle_refuse(self):
        tiles = {"left": dict(x=0, y=0, width=8, height=16, inner_width=4, inner_height=12),
                 "right": dict(x=8, y=0, width=8, height=16, inner_width=4, inner_height=12)}
        for uv in ([1.5, .5], [.75, .5]):
            mesh = dict(triangles=[dict(source_info=0, corners=[dict(uv=[.25, .5]), dict(uv=uv), dict(uv=[.25, .5])])])
            with self.assertRaises(ValueError):
                actor.atlas_boundaries(tiles, mesh, 16)

    def test_leon_source_uvs_must_match_selected_runtime_for_every_role(self):
        mesh = dict(triangles=[dict(source_info=i, corners=[dict(uv=[.25, .5])] * 3) for i in range(8)])
        values = ",".join(str(x) for x in struct.pack("<2H", 8192, 16384))
        header = "\n".join(f"unsigned char i{i}_uv[] = {{{values}}};" for i in range(8)).encode()
        self.assertTrue(actor.leon_runtime_uv(header, mesh)["source_mesh_uvs_match_selected_runtime"])
        mesh["triangles"][4]["corners"][0]["uv"] = [.1, .5]
        with self.assertRaisesRegex(ValueError, "role 4"):
            actor.leon_runtime_uv(header, mesh)


if __name__ == "__main__":
    unittest.main()
