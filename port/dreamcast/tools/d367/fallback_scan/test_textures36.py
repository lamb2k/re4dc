"""Public Build 36 selection fixtures using the existing physical pack writer."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import struct
import unittest

import formats
from textures36 import Resolver


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("textures36_existing_texpack", HERE.parent / "texpack.py")
PACK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PACK)
KNOBS = dict(TEX_PACK="1", TEX_RESIDENT="1", QUALITY_ASSETS="0")
A, B, C = "10000001-00000002", "20000003-00000004", "a0000005-00000006"


def texture(palette=False, tag=0):
    payload = bytes([tag]) * (64 if palette else 128)
    descriptor = struct.pack("<64s8I", b"synthetic36", 8, 8, 4 if palette else 1,
                             144, len(payload), 0, 1, 0)
    body = descriptor + payload
    return struct.pack("<8s10I", b"RE4DCTX\0", 2, 48, 96, 1, 48, 144,
                       len(payload), formats.crc(body), 1, 0) + body


def pack(entries):
    return PACK.build({tuple(int(v, 16) for v in key.split("-")): data for key, data in entries.items()})[0]


def loose(key, *, flat=False, low=False):
    return "dc/" + ("texlow" if low else "tex") + "/" + ("" if flat else key[0] + "/") + key + ".re4tex"


def index_crc(blob):
    n = struct.unpack_from("<I", blob, 12)[0]
    size = (n * 16 + 2047) // 2048 * 2048
    struct.pack_into("<I", blob, 24, formats.crc(blob[2048:2048 + size]))
    return bytes(blob)


class Selection(unittest.TestCase):
    def resolver(self, **changes):
        return Resolver(dict(KNOBS, **changes))

    def test_pack_precedes_different_loose_in_either_discovery_order(self):
        for reverse in (False, True):
            with self.subTest(reverse=reverse):
                resolver = self.resolver()
                actions = [(resolver.add_pack, "dc/tex.pak", pack({A: texture(True)})),
                           (resolver.add_loose, loose(A), texture(False))]
                for action, path, data in actions[::(-1 if reverse else 1)]:
                    self.assertEqual(action(path, data)["status"], "scanned")
                row = resolver.predicate(A)
                self.assertIs(row["present"], True)
                self.assertIs(row["palette"], True)
                self.assertEqual(row["selected_source"], "dc/tex.pak")
                self.assertEqual(row["shadowed"][0]["source"], loose(A))
                self.assertEqual(resolver.finish()["summary"], dict(definite_keys=1, conditional_keys=0,
                    absent_keys=0, physical_variants=2, possible_variants=1, shadowed_variants=1))

    def test_identical_copies_are_one_effective_key(self):
        resolver = self.resolver()
        payload = texture()
        resolver.add_pack("dc/tex.pak", pack({A: payload}))
        resolver.add_loose(loose(A), payload)
        result = resolver.finish()
        self.assertEqual(len(result["textures"]), 1)
        self.assertEqual(result["summary"]["definite_keys"], 1)
        self.assertEqual(result["summary"]["physical_variants"], 2)

    def test_pack_miss_uses_canonical_loose(self):
        resolver = self.resolver()
        resolver.add_pack("dc/tex.pak", pack({A: texture()}))
        resolver.add_loose(loose(B), texture(True))
        self.assertEqual(resolver.predicate(B)["selected_source"], loose(B))
        self.assertIs(resolver.predicate(B)["palette"], True)
        self.assertIs(resolver.predicate(C)["present"], False)

    def test_absent_pack_uses_loose(self):
        resolver = self.resolver()
        resolver.add_loose(loose(A), texture())
        self.assertEqual(resolver.predicate(A)["selected_source"], loose(A))

    def test_final_layer_is_whole_file_replacement(self):
        resolver = self.resolver()
        resolver.add_pack("dc/tex.pak", pack({A: texture(), B: texture(True)}))
        resolver.add_pack("@texpak-layer/0001/later.pak", pack({A: texture(True), C: texture()}), layer=1)
        result = resolver.finish()
        self.assertIs(resolver.predicate(A)["palette"], True)
        self.assertIs(resolver.predicate(B)["present"], False)
        self.assertIs(resolver.predicate(C)["present"], True)
        self.assertNotIn(B, result["textures"])
        self.assertEqual(result["summary"]["definite_keys"], 2)
        self.assertEqual(result["summary"]["absent_keys"], 1)
        self.assertTrue(result["sources"][0]["shadowed_file"])
        self.assertTrue(result["sources"][1]["selected_file"])

    def test_replaced_pack_key_can_still_use_loose(self):
        resolver = self.resolver()
        resolver.add_pack("dc/tex.pak", pack({A: texture(True)}))
        resolver.add_pack("@texpak-layer/0001/new.pak", pack({B: texture()}), layer=1)
        resolver.add_loose(loose(A), texture(False))
        self.assertEqual(resolver.predicate(A)["selected_source"], loose(A))
        self.assertIs(resolver.predicate(A)["palette"], False)

    def test_layer_ordinal_not_walk_order_selects_final_file(self):
        for sequence in ((0, 1, 2), (2, 0, 1), (1, 2, 0)):
            with self.subTest(sequence=sequence):
                resolver = self.resolver()
                for ordinal in sequence:
                    resolver.add_pack("dc/tex.pak" if ordinal == 0 else f"@texpak-layer/{ordinal:04d}/x.pak",
                                      pack({A: texture(ordinal == 2, ordinal)}), layer=ordinal or None)
                self.assertEqual(resolver.predicate(A)["selected_source"], "@texpak-layer/0002/x.pak")
                self.assertIs(resolver.predicate(A)["palette"], True)

    def test_reversing_declared_layers_changes_winner(self):
        for values in ((False, True), (True, False)):
            resolver = self.resolver()
            for ordinal, palette in enumerate(values, 1):
                resolver.add_pack(f"@texpak-layer/{ordinal:04d}/x.pak", pack({A: texture(palette)}), layer=ordinal)
            self.assertIs(resolver.predicate(A)["palette"], values[-1])

    def test_undeclared_pack_is_visible_but_never_a_layer(self):
        for path in ("other/tex.pak", "@input/extra.pak", "@input/tex.pak"):
            with self.subTest(path=path):
                resolver = self.resolver()
                row = resolver.add_pack(path, pack({A: texture(True)}))
                self.assertEqual(row["status"], "unsupported")
                self.assertIs(resolver.predicate(A)["present"], False)
                self.assertFalse(resolver.finish()["sources"][0]["selected_file"])
                self.assertEqual(resolver.finish()["summary"]["shadowed_variants"], 1)

    def test_undeclared_pack_cannot_override_canonical_pack(self):
        resolver = self.resolver()
        resolver.add_pack("dc/tex.pak", pack({A: texture(False)}))
        resolver.add_pack("zzz/tex.pak", pack({A: texture(True)}))
        self.assertIs(resolver.predicate(A)["palette"], False)

    def test_pack_disabled_uses_loose(self):
        resolver = self.resolver(TEX_PACK="0")
        resolver.add_pack("dc/tex.pak", pack({A: texture(True)}))
        resolver.add_loose(loose(A), texture(False))
        self.assertEqual(resolver.predicate(A)["selected_source"], loose(A))
        self.assertIs(resolver.predicate(A)["palette"], False)

    def test_flat_and_bucket_paths_follow_resident_recipe(self):
        for resident in (0, 1):
            resolver = self.resolver(TEX_PACK="0", TEX_RESIDENT=str(resident))
            resolver.add_loose(loose(A), texture(True))
            resolver.add_loose(loose(A, flat=True), texture(False))
            self.assertEqual(resolver.predicate(A)["selected_source"], loose(A, flat=not resident))
            self.assertIs(resolver.predicate(A)["palette"], bool(resident))

    def test_wrong_bucket_and_arbitrary_loose_path_are_unselected(self):
        for path in ("dc/tex/2/" + A + ".re4tex", "objects/" + A + ".re4tex",
                     "dc/texlow/" + A + ".re4tex"):
            resolver = self.resolver()
            self.assertEqual(resolver.add_loose(path, texture())["status"], "unsupported")
            self.assertIs(resolver.predicate(A)["present"], False)

    def test_quality_off_does_not_use_texlow(self):
        resolver = self.resolver()
        resolver.add_pack("dc/tex.pak", pack({A: texture(False)}))
        resolver.add_loose(loose(A, low=True), texture(True))
        self.assertIs(resolver.predicate(A)["palette"], False)
        self.assertEqual(resolver.predicate(A)["selected_source"], "dc/tex.pak")

    def test_quality_on_keeps_room_selection_conditional(self):
        resolver = self.resolver(QUALITY_ASSETS="1")
        resolver.add_pack("dc/tex.pak", pack({A: texture(False)}))
        resolver.add_loose(loose(A, low=True), texture(True))
        row = resolver.predicate(A)
        self.assertIs(row["present"], True)
        self.assertIsNone(row["palette"])
        self.assertIsNone(row["selected_source"])
        self.assertIsNone(row["selected_sha256"])
        self.assertEqual(len(row["possible_sources"]), 2)
        self.assertEqual(resolver.finish()["summary"]["definite_keys"], 1)
        self.assertEqual(resolver.finish()["textures"], {})

    def test_quality_on_can_make_presence_unknown(self):
        resolver = self.resolver(QUALITY_ASSETS="1")
        resolver.add_pack("dc/tex.pak", pack({A: texture()}))
        row = resolver.predicate(A)
        self.assertIsNone(row["present"])
        self.assertTrue(row["possible_absent"])
        self.assertFalse(row["unresolved"])
        self.assertEqual(resolver.finish()["summary"]["conditional_keys"], 1)

    def test_quality_off_is_not_assumed_when_recipe_omits_it(self):
        knobs = dict(KNOBS)
        knobs.pop("QUALITY_ASSETS")
        resolver = Resolver(knobs)
        resolver.add_pack("dc/tex.pak", pack({A: texture()}))
        self.assertIsNone(resolver.predicate(A)["present"])
        self.assertTrue(any("QUALITY_ASSETS" in warning for warning in resolver.finish()["warnings"]))

    def test_identical_conditional_sources_can_prove_payload(self):
        resolver = self.resolver(QUALITY_ASSETS="1")
        payload = texture()
        resolver.add_pack("dc/tex.pak", pack({A: payload}))
        resolver.add_loose(loose(A, low=True), payload)
        row = resolver.predicate(A)
        self.assertIs(row["present"], True)
        self.assertIs(row["palette"], False)
        self.assertIsNone(row["selected_source"])
        self.assertEqual(row["selected_sha256"], formats.sha(payload))
        self.assertEqual(resolver.finish()["textures"][A], formats.parse_texture(payload))

    def test_unknown_recipe_can_prove_presence_if_every_path_exists(self):
        resolver = Resolver()
        payload = texture()
        resolver.add_pack("dc/tex.pak", pack({A: payload}))
        for path in (loose(A), loose(A, flat=True), loose(A, low=True)):
            resolver.add_loose(path, payload)
        row = resolver.predicate(A)
        self.assertIs(row["present"], True)
        self.assertIs(row["palette"], False)
        self.assertEqual(len(row["possible_sources"]), 4)
        self.assertEqual(resolver.finish()["summary"]["definite_keys"], 1)

    def test_unknown_pack_does_not_claim_pack_only_key_present(self):
        knobs = dict(KNOBS)
        knobs.pop("TEX_PACK")
        resolver = Resolver(knobs)
        resolver.add_pack("dc/tex.pak", pack({A: texture()}))
        self.assertIsNone(resolver.predicate(A)["present"])

    def test_pack_prerequisite_can_constrain_missing_resident_knob(self):
        knobs = dict(KNOBS)
        knobs.pop("TEX_RESIDENT")
        resolver = Resolver(knobs)
        resolver.add_pack("dc/tex.pak", pack({A: texture()}))
        self.assertIs(resolver.predicate(A)["present"], True)

    def test_impossible_recipe_is_unknown(self):
        resolver = self.resolver(TEX_RESIDENT="0")
        resolver.add_pack("dc/tex.pak", pack({A: texture()}))
        self.assertIsNone(resolver.predicate(A)["present"])
        self.assertTrue(resolver.predicate(A)["unresolved"])
        self.assertTrue(any("not an admitted recipe" in w for w in resolver.finish()["warnings"]))

    def test_noninteger_recipe_is_unknown(self):
        resolver = self.resolver(TEX_PACK="$(UNTRUSTED)")
        resolver.add_pack("dc/tex.pak", pack({A: texture()}))
        self.assertIsNone(resolver.predicate(A)["present"])

    def test_missing_reference_does_not_create_an_inventory_key(self):
        resolver = self.resolver()
        self.assertIs(resolver.predicate(A)["present"], False)
        self.assertEqual(resolver.finish()["keys"], {})
        self.assertEqual(resolver.finish()["summary"]["absent_keys"], 0)

    def test_predicate_cache_is_invalidated_by_later_inputs(self):
        resolver = self.resolver()
        self.assertEqual(resolver.finish()["textures"], {})
        resolver.add_loose(loose(A), texture())
        self.assertIs(resolver.predicate(A)["present"], True)
        resolver.add_pack("dc/tex.pak", pack({A: texture(True)}))
        self.assertIs(resolver.predicate(A)["palette"], True)
        self.assertEqual(resolver.finish()["summary"]["definite_keys"], 1)

    def test_json_provenance_preserves_offsets_and_hashes_without_bytes(self):
        resolver = self.resolver()
        payload = texture(True)
        blob = pack({A: payload})
        before = bytes(blob)
        coverage = resolver.add_pack("dc/tex.pak", blob)
        result = resolver.finish()
        self.assertEqual(blob, before)
        decoded = json.loads(json.dumps(result, sort_keys=True))
        self.assertEqual(decoded, result)
        variant = result["keys"][A]["possible_sources"][0]
        self.assertEqual(variant["source_sha256"], formats.sha(blob))
        self.assertEqual(variant["sha256"], formats.sha(payload))
        self.assertEqual(blob[variant["offset"]:variant["offset"] + variant["bytes"]], payload)
        self.assertEqual(coverage, result["coverage"][0])

    def test_duplicate_api_identity_layer_and_invalid_layer_refused(self):
        blob = pack({A: texture()})
        resolver = self.resolver()
        resolver.add_pack("dc/tex.pak", blob)
        with self.assertRaises(formats.Invalid):
            resolver.add_pack("dc/tex.pak", blob)
        resolver.add_pack("@texpak-layer/0001/a", blob, layer=1)
        with self.assertRaises(formats.Invalid):
            resolver.add_pack("@texpak-layer/0001/b", blob, layer=1)
        for layer in (0, -1, 1.0, True):
            with self.assertRaises(formats.Invalid):
                resolver.add_pack("@invalid", blob, layer=layer)
        resolver.add_loose(loose(A), texture())
        with self.assertRaises(formats.Invalid):
            resolver.add_loose(loose(A), texture())

    def test_same_external_file_can_be_explicitly_repeated_at_new_layer(self):
        resolver = self.resolver()
        blob = pack({A: texture()})
        resolver.add_pack("external.pak", blob, layer=1)
        resolver.add_pack("external.pak", blob, layer=2)
        self.assertEqual(resolver.predicate(A)["possible_sources"][0]["layer"], 2)


class Failures(unittest.TestCase):
    def resolver(self, **changes):
        return Resolver(dict(KNOBS, **changes))

    def test_malformed_final_layer_never_uncovers_previous_pack(self):
        resolver = self.resolver()
        resolver.add_pack("dc/tex.pak", pack({A: texture(True)}))
        resolver.add_loose(loose(A), texture(False))
        row = resolver.add_pack("@texpak-layer/0001/bad.pak", b"RE4PAK1\0", layer=1)
        self.assertEqual(row["status"], "rejected")
        self.assertIsNone(resolver.predicate(A)["present"])
        self.assertEqual(resolver.predicate(A)["possible_sources"], [])
        self.assertIsNone(resolver.predicate(C)["present"])
        self.assertEqual(resolver.finish()["textures"], {})

    def test_unreadable_final_layer_retains_uncertainty(self):
        resolver = self.resolver()
        resolver.add_pack("dc/tex.pak", pack({A: texture()}))
        row = resolver.failed_pack("@texpak-layer/0001/missing.pak", "missing input", layer=1)
        self.assertEqual(row["status"], "rejected")
        self.assertIsNone(resolver.predicate(A)["present"])
        self.assertIsNone(resolver.predicate(B)["present"])
        source = resolver.finish()["sources"][-1]
        self.assertIsNone(source["sha256"])
        self.assertTrue(source["selected_file"])

    def test_later_valid_layer_can_replace_a_failed_earlier_layer(self):
        resolver = self.resolver()
        resolver.failed_pack("dc/tex.pak", "read failed")
        resolver.add_pack("@texpak-layer/0001/good.pak", pack({A: texture()}), layer=1)
        self.assertIs(resolver.predicate(A)["present"], True)
        self.assertIs(resolver.predicate(B)["present"], False)
        self.assertEqual(resolver.finish()["coverage"][0]["status"], "rejected")

    def test_pack_failure_is_irrelevant_to_known_pack_off_selection(self):
        resolver = self.resolver(TEX_PACK="0")
        resolver.failed_pack("dc/tex.pak", "read failed")
        resolver.add_loose(loose(A), texture())
        self.assertIs(resolver.predicate(A)["present"], True)
        self.assertEqual(resolver.predicate(A)["selected_source"], loose(A))

    def test_malformed_loose_is_unknown_unless_shadowed_by_pack(self):
        resolver = self.resolver()
        row = resolver.add_loose(loose(A), b"bad")
        self.assertEqual(row["status"], "rejected")
        self.assertIsNone(resolver.predicate(A)["present"])
        self.assertEqual(resolver.finish()["summary"]["conditional_keys"], 1)
        resolver.add_pack("dc/tex.pak", pack({A: texture()}))
        self.assertIs(resolver.predicate(A)["present"], True)

    def test_nested_payload_crc_failure_does_not_fall_back_to_loose(self):
        blob = bytearray(pack({A: texture()}))
        offset, size = struct.unpack_from("<2I", blob, 2048 + 8)
        blob[offset + size - 1] ^= 1
        self.assertEqual(PACK.verify(blob)[0], 1)  # Physical index is still valid.
        resolver = self.resolver()
        resolver.add_loose(loose(A), texture(True))
        self.assertEqual(resolver.add_pack("dc/tex.pak", bytes(blob))["status"], "rejected")
        self.assertIsNone(resolver.predicate(A)["present"])
        self.assertEqual(resolver.predicate(A)["possible_sources"], [])

    def test_duplicate_on_disk_keys_remain_invalid_even_with_recomputed_crc(self):
        blob = bytearray(pack({A: texture(), B: texture(True)}))
        blob[2064:2072] = blob[2048:2056]
        blob = index_crc(blob)
        with self.assertRaises(SystemExit):
            PACK.verify(blob)
        resolver = self.resolver()
        self.assertEqual(resolver.add_pack("dc/tex.pak", blob)["status"], "rejected")
        self.assertIsNone(resolver.predicate(A)["present"])

    def test_sector_boundary_duplicate_remains_invalid(self):
        entries = {f"{i:08x}-00000000": texture(tag=i % 256) for i in range(129)}
        blob = bytearray(pack(entries))
        blob[4096:4104] = blob[4080:4088]
        resolver = self.resolver()
        self.assertEqual(resolver.add_pack("dc/tex.pak", index_crc(blob))["status"], "rejected")

    def test_unsigned_crc_fnv_order_across_index_sector_is_accepted(self):
        entries = {f"{0x80000000 + i // 2:08x}-{0xffffffff if i % 2 else 0:08x}": texture(tag=i % 256)
                   for i in range(129)}
        resolver = self.resolver()
        self.assertEqual(resolver.add_pack("dc/tex.pak", pack(entries))["status"], "scanned")
        self.assertEqual(resolver.finish()["summary"]["definite_keys"], 129)
        for key in entries:
            self.assertIs(resolver.predicate(key)["present"], True)

    def test_existing_format_refusals_are_preserved(self):
        original = pack({A: texture(), B: texture(True)})
        cases = []
        for offset, value, fix_crc in ((8, 2, False), (12, 0, False), (12, 8193, False),
                                       (16, 4096, False), (20, 4097, False),
                                       (2056, 4097, True), (2056, 2048, True),
                                       (2060, 0, True), (2060, len(original), True)):
            blob = bytearray(original)
            struct.pack_into("<I", blob, offset, value)
            cases.append(index_crc(blob) if fix_crc else bytes(blob))
        bad_crc = bytearray(original)
        bad_crc[24] ^= 1
        cases.append(bytes(bad_crc))
        cases.append(original[:2047])
        for index, blob in enumerate(cases):
            with self.subTest(case=index):
                resolver = self.resolver()
                self.assertEqual(resolver.add_pack("dc/tex.pak", blob)["status"], "rejected")
                self.assertIsNone(resolver.predicate(A)["present"])

    def test_existing_scanner_overlap_refusal_is_not_relaxed(self):
        blob = bytearray(pack({A: texture(), B: texture()}))
        blob[2072:2080] = blob[2056:2064]
        blob = index_crc(blob)
        self.assertEqual(PACK.verify(blob)[0], 2)  # Existing scanner is stricter.
        resolver = self.resolver()
        row = resolver.add_pack("dc/tex.pak", blob)
        self.assertEqual(row["status"], "rejected")
        self.assertIn("aliases/overlaps", row["message"])

    def test_builder_still_refuses_different_bytes_for_one_key(self):
        out = {}
        PACK.add(out, (1, 2), texture(), "first")
        snapshot = deepcopy(out)
        with self.assertRaises(SystemExit):
            PACK.add(out, (1, 2), texture(True), "second")
        self.assertEqual(out, snapshot)


if __name__ == "__main__":
    unittest.main()
