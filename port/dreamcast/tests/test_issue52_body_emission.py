import sys, struct, tempfile, unittest
from pathlib import Path
T = Path(__file__).resolve().parents[1] / 'tools/d367/issue52_visuals'
sys.path.insert(0, str(T))
import emit_officer_body as emit
import verify_officer_body as verify
import transform_officer_body as body


class PrivateBodyEmission(unittest.TestCase):
    def test_disabled_before_reads_or_writes(self):
        old = sys.argv
        try:
            sys.argv = ['emit', '--sources', 'missing', '--plan', 'missing', '--out', 'missing']
            with self.assertRaisesRegex(ValueError, 'disabled'):
                emit.main()
        finally:
            sys.argv = old

    def test_floor_and_three_copy_budget(self):
        with self.assertRaisesRegex(ValueError, 'floor'):
            emit.check_capacity(1, emit.FLOOR)
        emit.check_capacity(1, emit.FLOOR + 1)
        with self.assertRaisesRegex(ValueError, 'budget'):
            emit.check_capacity(emit.TOTAL_BUDGET // 3, emit.FLOOR + emit.TOTAL_BUDGET)

    def test_no_overwrite_or_output_under_base(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / 'source'
            source.mkdir()
            sentinel = source / 'base'
            sentinel.write_bytes(b'preserve')
            with self.assertRaisesRegex(ValueError, 'overwrite'):
                emit.output_guard(source, source)
            with self.assertRaisesRegex(ValueError, 'outside'):
                emit.output_guard(source / 'new', source)
            self.assertEqual(sentinel.read_bytes(), b'preserve')

    def test_independent_rectangular_twiddle_decoder_and_CRC(self):
        pixels = []
        for y in range(8):
            for x in range(16):
                r, g, b = x * 2, y * 8, (x + y) % 32
                pixels.append(((r << 3) | (r >> 2), (g << 2) | (g >> 4), (b << 3) | (b >> 2), 255))
        blob, key = body.opaque_package(pixels, 16, 8, 'independent test')
        w, h, actual, parsed_key = verify.decode_native(blob)
        self.assertEqual((w, h, parsed_key), (16, 8, key))
        self.assertEqual(actual, bytes(v for p in pixels for v in p))
        corrupt = bytearray(blob)
        corrupt[-1] ^= 1
        with self.assertRaisesRegex(ValueError, 'CRC'):
            verify.decode_native(corrupt)

    def test_independent_TPL_parser_requires_coherent_dimensions(self):
        data = bytearray(256)
        struct.pack_into('<3I', data, 0, 0x20af30, 3, 12)
        for i in range(3):
            hdr, rec = 36 + 36 * i, 160 + 32 * i
            struct.pack_into('<II', data, 12 + 8 * i, hdr, 0)
            struct.pack_into('<2H4I', data, hdr, 8, 16, 14, rec, 1, 1)
            struct.pack_into('<8s6I', data, rec, b'R4NREF\0\0', 1, 2, 16, 8, 14, 32)
        self.assertEqual(len(verify.parse_tpl(data)), 3)
        struct.pack_into('<I', data, 160 + 16, 8)
        with self.assertRaisesRegex(ValueError, 'does not match'):
            verify.parse_tpl(data)


if __name__ == '__main__':
    unittest.main()