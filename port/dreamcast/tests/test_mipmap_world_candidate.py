import importlib.util
import pathlib
import struct
import sys
import unittest

HERE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "tools"))
sys.path.insert(0, str(HERE / "tools" / "d367"))
sys.path.insert(0, str(HERE / "tools" / "d367" / "mipmap21"))
import mipmap_vq as mip
import texpack
import world_candidate as candidate
from test_mipmap_vq import native, replace_texture


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
