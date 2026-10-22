import importlib.util
import pathlib
import struct
import sys
import unittest
import zlib

HERE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "tools"))
sys.path.insert(0, str(HERE / "tools" / "d367"))
sys.path.insert(0, str(HERE / "tools" / "d367" / "mipmap21"))
import mipmap_vq as mip
import texpack
import world_candidate as candidate
from test_mipmap_vq import native, replace_texture


def legacy_crc(blob):
    """Restamp a native package with the legacy data-only CRC convention."""
    h = list(mip.tpl.HEADER.unpack_from(blob))
    h[8] = zlib.crc32(blob[h[6]:]) & 0xffffffff
    return mip.tpl.HEADER.pack(*h) + blob[mip.tpl.HEADER.size:]


def world(keys):
    return struct.pack("<4s7I", b"R4PW", 1, 0, len(keys), 0, 0, 0, 0) + b"".join(
        struct.pack("<IIHH4B", *key, 8, 8, 0, 0, 0, 0) for key in keys)


class RoomSelection(unittest.TestCase):
    def test_disabled_pack_is_byte_exact_and_other_formats_are_reported(self):
        source = {(1, 2): native(), (3, 4): replace_texture(native(), 7, 1)}
        pack, _ = texpack.build(source)
        out, report, _, _ = candidate.build_candidate(pack, world(list(source)))
        self.assertEqual(out, pack)
        self.assertEqual(report["changed_keys"], 0)
        self.assertEqual(report["compatible_keys"], 1)
        self.assertEqual(len(report["other_formats"]), 1)
        self.assertEqual(report["extra_payload_bytes"], 0)

    def test_enabled_only_changes_selected_compatible_key(self):
        source = {(1, 2): native(), (3, 4): native(fmt=2), (5, 6): native()}
        pack, _ = texpack.build(source)
        out, report, before, after = candidate.build_candidate(
            pack, world([(1, 2), (3, 4)]), enabled=True, engine="python")
        self.assertNotEqual(out, pack)
        self.assertEqual(report["changed_keys"], 2)
        self.assertEqual(report["unchanged_keys"], 1)
        self.assertEqual(before[(5, 6)], after[(5, 6)])
        for key in ((1, 2), (3, 4)):
            old, new = mip.read_native_vq(before[key]), mip.read_native_vq(after[key])
            self.assertEqual(old.codebook, new.codebook)
            self.assertEqual(old.base_indices, new.base_indices)
        self.assertEqual(report["extra_payload_bytes"], 2 * 6)

    def test_all_world_keys_are_deduplicated_and_per_room_sums_keep_overlap(self):
        source = {(1, 2): native(), (3, 4): native(), (5, 6): native()}
        pack, _ = texpack.build(source)
        worlds = {"r100": world([(1, 2), (3, 4)]), "r103": world([(3, 4), (5, 6)])}
        progress = []
        _, report, _, _ = candidate.build_candidate(
            pack, worlds, enabled=True, engine="python",
            progress=lambda done, total: progress.append((done, total)))
        self.assertEqual(report["changed_keys"], 3)
        self.assertEqual(report["extra_payload_bytes"], 18)
        self.assertEqual(report["per_room"]["r100"]["changed_keys"], 2)
        self.assertEqual(report["per_room"]["r103"]["changed_keys"], 2)
        self.assertEqual(sum(r["extra_payload_bytes"] for r in report["per_room"].values()), 24)
        self.assertEqual(progress, [(3, 3)])
        self.assertIn("not simultaneous", report["per_room_sum_caution"])

    def test_all_world_selector_is_limited_to_named_sidecars_in_manifest(self):
        names = ["dc/native/r100/ps2-world.r4pw", "dc/native/r103/ps2-world.r4pw"]
        manifest = dict.fromkeys(names + ["dc/native/r100/other.r4pw", "dc/tex.pak",
            "dc/native/r1234/ps2-world.r4pw", "dc/native/r100/ps2-worldXr4pw"])
        self.assertEqual(candidate.world_paths(manifest), names)
        self.assertEqual(candidate.world_paths(manifest, 0x103), [names[1]])

    def test_square_twiddled_selection_is_explicit_and_retains_exact_base(self):
        from test_mipmap_twiddled import native as raw
        import mipmap_twiddled as twiddled
        source = {(1, 2): native(), (3, 4): raw(fmt=2)}
        pack, _ = texpack.build(source)
        worlds = world(list(source))
        _, report, _, _ = candidate.build_candidate(pack, worlds, enabled=True, engine="python")
        self.assertEqual(report["changed_keys"], 1)
        control, _, _, _ = candidate.build_candidate(pack, worlds, include_twiddled=True)
        self.assertEqual(control, pack)
        _, report, before, after = candidate.build_candidate(
            pack, worlds, enabled=True, include_twiddled=True, engine="python")
        self.assertEqual(report["changed_keys"], 2)
        self.assertIn("TEX_TWIDDLED_MIPMAP=1", report["required_build_knobs"])
        self.assertEqual(twiddled.read_native_twiddled(before[(3, 4)]).base_texels,
                         twiddled.read_native_twiddled(after[(3, 4)]).base_texels)

    def test_already_mipmapped_legacy_input_is_checksum_normalized_only(self):
        mipped, _ = mip.add_mipmaps(native(), enabled=True, engine="python")
        legacy = legacy_crc(mipped)
        self.assertEqual(mip.read_native_vq(legacy).crc_rule, "data")
        source = {(1, 2): legacy, (3, 4): native(rule="data"), (5, 6): legacy_crc(mipped)}
        pack, _ = texpack.build(source)
        worlds = world([(1, 2), (3, 4)])
        off, report, _, _ = candidate.build_candidate(pack, worlds)
        self.assertEqual(off, pack)
        self.assertEqual(report["changed_keys"], 0)
        out, report, before, after = candidate.build_candidate(pack, worlds, enabled=True, engine="python")
        self.assertEqual(report["changed_keys"], 2)
        self.assertEqual(report["checksum_normalized_keys"], 1)
        self.assertEqual(after[(5, 6)], before[(5, 6)])  # unselected legacy key untouched
        old, new = mip.read_native_vq(before[(1, 2)]), mip.read_native_vq(after[(1, 2)])
        self.assertEqual((new.crc_rule, new.payload, new.texture), ("header", old.payload, old.texture))
        self.assertEqual(after[(1, 2)][40:], before[(1, 2)][40:])
        self.assertEqual(mip.read_native_vq(after[(3, 4)]).crc_rule, "header")

    def test_payload_change_on_already_mipmapped_key_is_refused(self):
        mipped, _ = mip.add_mipmaps(native(), enabled=True, engine="python")
        pack, _ = texpack.build({(1, 2): legacy_crc(mipped)})
        real = mip.tpl.canonical_native_crc
        try:
            def tamper(b):
                c = real(b)
                c = c[:-1] + bytes([c[-1] ^ 1])
                h = list(mip.tpl.HEADER.unpack_from(c))
                h[8] = zlib.crc32(c[h[2]:]) & 0xffffffff
                return mip.tpl.HEADER.pack(*h) + c[mip.tpl.HEADER.size:]
            mip.tpl.canonical_native_crc = tamper
            # refused either by the exact-base check or the checksum-only rule
            with self.assertRaisesRegex(ValueError, "changed"):
                candidate.build_candidate(pack, world([(1, 2)]), enabled=True, engine="python")
        finally:
            mip.tpl.canonical_native_crc = real

    def test_missing_world_key_is_refused(self):
        pack, _ = texpack.build({(1, 2): native()})
        with self.assertRaisesRegex(ValueError, "absent"):
            candidate.build_candidate(pack, world([(9, 9)]))

    def test_noncanonical_source_pack_is_refused_even_when_disabled(self):
        pack, _ = texpack.build({(1, 2): native()})
        with self.assertRaisesRegex(ValueError, "canonical"):
            candidate.build_candidate(pack + bytes(2048), world([(1, 2)]))

    def test_world_header_and_part_extents_are_bounded(self):
        for bad in (b"", world([(1, 2)])[:-1], world([(1, 2)]).replace(b"R4PW", b"BAD!")):
            with self.assertRaises(ValueError):
                candidate.world_keys(bad)


if __name__ == "__main__":
    unittest.main()
