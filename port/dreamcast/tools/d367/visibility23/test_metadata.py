import struct
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

from metadata import build, crc, write_metadata


def fixture(strips=((0, 1, 2), (2, 3, 4), (4, 5, 0)), indexed=False):
    mesh = bytearray(512)
    offsets = (5, 4, 3, 2, 1, 0) if indexed else ()
    stream = (struct.pack('<6H', *offsets) if indexed else b'') + b''.join(bytes([len(s), *s]) for s in strips)
    mesh[400:400+len(stream)] = stream
    struct.pack_into('<4s19I', mesh, 0, b'R4IM', 3, len(mesh), 0, 1, 1, 1, 6, len(stream), 1,
                     128, 196, 232, 260, 400, 500, 2, 0, 0, 0)
    struct.pack_into('<5I', mesh, 80, 0, 0, 332, 340, 340)
    struct.pack_into('<IIIHH6H', mesh, 232, 0, 0, len(stream)-(12 if indexed else 0), 6,
                     len(strips) | (0x8000 if indexed else 0), *([0]*6))
    for i in range(6):
        struct.pack_into('<6H', mesh, 260+12*i, i*10, i*20, i*30, 0, 0, 0)
    struct.pack_into('<I', mesh, 12, crc(mesh[80:]))
    side = bytearray(48)
    struct.pack_into('<4s7I', side, 0, b'R4PW', 1, 0, 1, 1, crc(side[32:]), 0, 0)
    return bytes(mesh), bytes(side)


class MetadataTests(unittest.TestCase):
    def test_indexed_original_ranges_and_bounds(self):
        mesh, side = fixture(indexed=True)
        result, stats = build(mesh, side, 4)
        # Corner 0 reads pool 5. Exact original corner numbers stay 0..2.
        self.assertEqual(struct.unpack_from('<6HHBB', result, 32), (30, 60, 90, 50, 100, 150, 4, 0, 2))
        self.assertEqual(stats['nonempty_groups'], 3)
        self.assertEqual(struct.unpack_from('<6HHBB', result, 80), (0, 0, 0, 0, 0, 0, 12, 1, 0))

    def test_empty_stream(self):
        mesh, side = fixture(strips=())
        result, stats = build(mesh, side)
        self.assertEqual(stats['nonempty_groups'], 0)
        self.assertEqual(result[32:], struct.pack('<6HHBB', 0, 0, 0, 0, 0, 0, 0, 1, 0)*4)

    def test_short_strip_rejected(self):
        mesh, side = fixture(strips=((0, 1),))
        with self.assertRaisesRegex(ValueError, 'short/truncated'):
            build(mesh, side)

    def test_bad_corner_rejected(self):
        mesh, side = fixture(strips=((0, 1, 6),))
        with self.assertRaisesRegex(ValueError, 'corner reference'):
            build(mesh, side)

    def test_crc_and_short_inputs_rejected(self):
        mesh, side = fixture()
        for bad_mesh, bad_side in ((mesh[:-1], side), (mesh, side[:-1]),
                                    (mesh[:450]+b'X'+mesh[451:], side),
                                    (mesh, side[:-1]+b'X')):
            with self.assertRaises(ValueError):
                build(bad_mesh, bad_side)

    def test_invalid_group_counts(self):
        for groups in (0, 9):
            with self.assertRaises(ValueError):
                build(*fixture(), groups)

    def test_no_mesh_output_or_input_alias(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            mesh, side = fixture()
            (root/'mesh').write_bytes(mesh)
            (root/'side').write_bytes(side)
            args = SimpleNamespace(mesh=str(root/'mesh'), sidecar=str(root/'side'),
                                   out_mesh='forbidden.mesh', out_groups=str(root/'out'), report=None, groups=4)
            with self.assertRaisesRegex(ValueError, 'no mesh output'):
                write_metadata(args)
            args.out_mesh = '-'
            args.out_groups = args.mesh
            with self.assertRaisesRegex(ValueError, 'aliases'):
                write_metadata(args)
            args.out_groups = str(root/'hardlink')
            (root/'hardlink').hardlink_to(root/'mesh')
            with self.assertRaisesRegex(ValueError, 'hard links'):
                write_metadata(args)
            self.assertEqual((root/'mesh').read_bytes(), mesh)


if __name__ == '__main__':
    unittest.main()
