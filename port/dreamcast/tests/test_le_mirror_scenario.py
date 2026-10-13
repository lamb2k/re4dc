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


    def test_inert_normal_and_exec_union_keeps_authored_bytes(self):
        for kind in (0, 2):
            b, d = self.record(kind)
            payload = bytes(range(64))
            b[d:d+64] = payload
            self.convert(b)
            self.assertEqual(b[d:d+64], payload)

    def test_other_runtime_work_still_requires_zero(self):
        for kind in (6, 7, 20):
            b, d = self.record(kind)
            b[d] = 1
            self.assertEqual(LE.fmt_sce_at(LE.Swapper(b, 'test'), 0, len(b), 'test'),
                             ['scenario0 runtime work is nonzero'])

    def collision(self, value, slot=0):
        b, d = self.record(11)
        b[16+4] = 1  # authored quad
        b[16+52] = 3  # enabled
        struct.pack_into('>I', b, d + slot, value)
        return b, d

    def test_uncreated_collision_placeholder_rebuilt_by_source(self):
        for value, slot in ((1, 0), (0x44, 0), (0x45, 0), (0x23, 4)):
            b, d = self.collision(value, slot)
            struct.pack_into('>4I', b, d+12, 0x4000, 0x2000, 0, 0x10000)
            self.convert(b)
            self.assertEqual(struct.unpack_from('<I', b, d+slot)[0], value)
            self.assertEqual(struct.unpack_from('<4I', b, d+12),
                             (0x4000, 0x2000, 0, 0x10000))
            self.assertEqual(b[d+8], 0)  # conversion does not create collision

    def test_collision_rejects_live_or_unreplaced_pointer_slots(self):
        for condition in ('ppc', 'large', 'created', 'notquad', 'disabled',
                          'parentlink', 'nosat', 'noeat'):
            b, d = self.collision(0x44, 4 if condition == 'noeat' else 0)
            if condition in ('ppc', 'large'):
                struct.pack_into('>I', b, d, 0x80123456 if condition == 'ppc' else 0x100)
            elif condition == 'created': b[d+8] = 1
            elif condition == 'notquad': b[16+4] = 0
            elif condition == 'disabled': b[16+52] = 0
            elif condition == 'parentlink': b[16+70] = 1
            else: struct.pack_into('>I', b, d+20, 2 if condition == 'nosat' else 1)
            with self.subTest(condition=condition):
                with self.assertRaisesRegex(ValueError, 'placeholder is not rebuilt'):
                    LE.fmt_sce_at(LE.Swapper(b, 'test'), 0, len(b), 'test')

    def test_ignored_union_does_not_relax_shared_pointer_checks(self):
        for kind in (0, 2):
            for offset in (64, 76):
                b, d = self.record(kind)
                struct.pack_into('>I', b, 16+offset, 0x80123456)
                with self.assertRaisesRegex(ValueError, 'runtime/PPC pointer'):
                    LE.fmt_sce_at(LE.Swapper(b, 'test'), 0, len(b), 'test')


class EmptyItemModelPack(unittest.TestCase):
    def pack(self, count=0, offset=32, bin_offset=0, tpl_offset=0):
        b=bytearray(64)
        struct.pack_into('>4I',b,0,3,offset,bin_offset,tpl_offset)
        struct.pack_into('>I',b,32,count)
        b[36:]=bytes(range(28))
        return b

    def test_source_zero_count_null_tables_preserves_unused_bytes(self):
        b=self.pack()
        original=bytes(b)
        LE.fmt_itm(LE.Swapper(b,'empty-itm'),0,len(b),'test')
        self.assertEqual(struct.unpack_from('<4I',b),(3,32,0,0))
        self.assertEqual(struct.unpack_from('<I',b,32)[0],0)
        self.assertEqual(b[16:32],original[16:32])
        self.assertEqual(b[36:],original[36:])

    def test_nonempty_null_tables_rejected(self):
        b=self.pack(count=1)
        with self.assertRaisesRegex(ValueError,'nonempty'):
            LE.fmt_itm(LE.Swapper(b,'empty-itm'),0,len(b),'test')

    def test_invalid_id_offsets_rejected(self):
        for offset in (0,4,12,62,64,65,0xfffffff0):
            b=self.pack(offset=offset)
            with self.subTest(offset=offset):
                with self.assertRaises(ValueError):
                    LE.fmt_itm(LE.Swapper(b,'empty-itm'),0,len(b),'test')

    def test_one_null_or_aliased_nonnull_table_still_rejected(self):
        for bin_offset,tpl_offset in ((0,48),(48,0),(32,48),(48,48)):
            b=self.pack(bin_offset=bin_offset,tpl_offset=tpl_offset)
            with self.subTest(bin_offset=bin_offset,tpl_offset=tpl_offset):
                with self.assertRaisesRegex(ValueError,'invalid item model tables'):
                    LE.fmt_itm(LE.Swapper(b,'empty-itm'),0,len(b),'test')


if __name__ == '__main__':
    unittest.main()