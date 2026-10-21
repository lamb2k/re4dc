import sys, struct, unittest
from pathlib import Path
T = Path(__file__).resolve().parents[1] / 'tools/d367/issue52_visuals'
sys.path.insert(0, str(T))
import transform_officer_body as body


class OfficerBodyTransformer(unittest.TestCase):
    def test_disabled_before_input_reads(self):
        old = sys.argv
        try:
            sys.argv = ['tool', '--sources', 'missing', '--report', 'missing']
            with self.assertRaisesRegex(ValueError, 'disabled'):
                body.main()
        finally:
            sys.argv = old

    def test_opaque_material_does_not_silently_drop_alpha(self):
        with self.assertRaisesRegex(ValueError, 'source alpha'):
            body.opaque_package([(20, 30, 40, 254)] * 64, 8, 8, 'test')

    def test_native_package_keeps_source_size_and_opaque_contract(self):
        blob, key = body.opaque_package([(20, 30, 40, 255)] * 128, 16, 8, 'test')
        h = body.ct.HEADER.unpack_from(blob)
        t = body.ct.TEXTURE.unpack_from(blob, h[5])
        self.assertEqual(t[1:4], (16, 8, body.ct.FORMAT_RGB565))
        self.assertEqual(t[6:8], (0, body.ct.PAYLOAD_TWIDDLED))
        self.assertEqual(key, body.key_for(blob[t[4]:t[4] + t[5]]))

    def test_nearest_RGB565_bounds_each_source_channel(self):
        for value in range(256):
            q = body.expand565(body.quantize565((value, value, value, 255)))
            for actual, limit in zip(q, [4, 2, 4]):
                self.assertLessEqual(abs(value - actual), limit)

    def test_changed_native_dimensions_must_match_header(self):
        data = bytearray(256)
        struct.pack_into('<3I', data, 0, body.ct.TPL_MAGIC, 3, 12)
        for i in range(3):
            hdr, rec = 36 + 36 * i, 160 + 32 * i
            struct.pack_into('<II', data, 12 + 8 * i, hdr, 0)
            struct.pack_into('<2H4I', data, hdr, 8, 16, 14, rec, 1, 1)
            struct.pack_into('<8s6I', data, rec, b'R4NREF\0\0', 1, 2, 16, 8, 14, 32)
        self.assertEqual(len(body.records(data)), 3)
        struct.pack_into('<I', data, 160 + 16, 8)
        with self.assertRaisesRegex(ValueError, 'mismatch'):
            body.records(data)


if __name__ == '__main__':
    unittest.main()