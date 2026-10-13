"""Source-layout checks for castle and later-village authored AEV payloads."""
import importlib.util
from pathlib import Path
import struct
import unittest

SPEC = importlib.util.spec_from_file_location('le_mirror', Path(__file__).parents[1] / 'tools' / 'le_mirror.py')
LE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LE)


class ScenarioPayloads(unittest.TestCase):
    def record(self, kind):
        b = bytearray(16 + 156)
        b[:8] = struct.pack('>4sHH', b'AEV\0', 0x104, 1)
        b[16 + 53] = kind
        return b, 16 + 92

    def convert(self, b):
        self.assertEqual(LE.fmt_sce_at(LE.Swapper(b, 'test'), 0, len(b), 'test'), [])

    def test_damage_fields_and_byte_flags(self):
        b, d = self.record(10)
        struct.pack_into('>iBB2sif', b, d, 0x1020304, 9, 3, b'xy', -123456, 12.5)
        self.convert(b)
        self.assertEqual(struct.unpack_from('<iBB2sif', b, d), (0x1020304, 9, 3, b'xy', -123456, 12.5))

    def test_hide_position_preserves_state(self):
        b, d = self.record(18)
        b[d:d+4] = bytes([2, 0xa1, 0xb2, 7])
        struct.pack_into('>3f', b, d+36, 123.25, -432.5, 19.75)
        b[d+52] = 9
        self.convert(b)
        self.assertEqual(struct.unpack_from('<3f', b, d+36), (123.25, -432.5, 19.75))
        self.assertEqual(b[d:d+4], bytes([2, 0xa1, 0xb2, 7]))
        self.assertEqual(b[d+52], 9)

    def test_camera_and_jump(self):
        b, d = self.record(12)
        struct.pack_into('>4f', b, d, 1.25, -2.5, 3.75, 0.125)
        b[d+17] = 1
        struct.pack_into('>2f', b, d+20, 120.5, 30.25)
        self.convert(b)
        self.assertEqual(struct.unpack_from('<4f', b, d), (1.25, -2.5, 3.75, 0.125))
        self.assertEqual(struct.unpack_from('<2f', b, d+20), (120.5, 30.25))
        self.assertEqual(b[d+17], 1)
        b, d = self.record(19)
        struct.pack_into('>3f', b, d, -10.5, 12.25, 8.75)
        self.convert(b)
        self.assertEqual(struct.unpack_from('<3f', b, d), (-10.5, 12.25, 8.75))

    def test_shadow_and_null_special_key(self):
        b, d = self.record(9)
        struct.pack_into('>HBB', b, d, 0x1234, 1, 2)
        self.convert(b)
        self.assertEqual(struct.unpack_from('<HBB', b, d), (0x1234, 1, 2))
        b, d = self.record(15)
        b[d+8:d+10] = bytes([7, 5])
        self.convert(b)
        self.assertEqual(b[d+8:d+10], bytes([7, 5]))

    def test_reject_ppc_runtime_pointers(self):
        for kind, offset in ((15, 0), (15, 4), (18, 48)):
            b, d = self.record(kind)
            struct.pack_into('>I', b, d+offset, 0x80123456)
            with self.assertRaisesRegex(ValueError, 'runtime/PPC pointer'):
                LE.fmt_sce_at(LE.Swapper(b, 'test'), 0, len(b), 'test')


if __name__ == '__main__':
    unittest.main()