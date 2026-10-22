import ctypes
import importlib.util
import os
import pathlib
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib

TOOLS = pathlib.Path(__file__).parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
import convert_tpl as tpl
import mipmap_vq as mip


def native(size=8, fmt=0, rule="header", height=None):
    height = height or size
    words = []
    for i in range(256):
        for j in range(4):
            if fmt == 0:
                words.append(((i + j) & 31) << 11 | ((i * 3 + j) & 63) << 5 | ((i * 7 + j) & 31))
            elif fmt == 1:
                words.append((0x8000 if i & 1 else 0) | ((i + j) & 31) << 10 |
                             ((i * 3 + j) & 31) << 5 | ((i * 7 + j) & 31))
            else:
                words.append(((i + j) & 15) << 12 | ((i * 3 + j) & 15) << 8 |
                             ((i * 5 + j) & 15) << 4 | ((i * 7 + j) & 15))
    payload = struct.pack("<1024H", *words) + bytes((i * 7 + 13) % 256 for i in range(size * height // 4))
    flags = 0 if fmt == 0 else (3 if fmt == 1 else 1)
    t = tpl.TEXTURE.pack(b"fixture", size, height, fmt, 144, len(payload), flags, 2, 0)
    body = t + payload
    crc = zlib.crc32(body if rule == "header" else payload) & 0xffffffff
    h = tpl.HEADER.pack(tpl.MAGIC, 2, 48, 96, 1, 48, 144, len(payload), crc, 1, 0x40000000)
    return h + body


def replace_texture(blob, field, value):
    h = list(tpl.HEADER.unpack_from(blob))
    t = list(tpl.TEXTURE.unpack_from(blob, 48))
    t[field] = value
    body = tpl.TEXTURE.pack(*t) + blob[144:]
    h[8] = zlib.crc32(body) & 0xffffffff
    return tpl.HEADER.pack(*h) + body


class Mipmaps(unittest.TestCase):
    def test_disabled_returns_identical_bytes_for_all_formats_and_crc_rules(self):
        for fmt in range(3):
            for rule in ("header", "data"):
                with self.subTest(fmt=fmt, rule=rule):
                    src = native(fmt=fmt, rule=rule)
                    result, report = mip.add_mipmaps(src)
                    self.assertEqual(result, src)
                    self.assertFalse(report["changed"])
                    self.assertEqual(report["extra_payload_bytes"], 0)

    def test_added_chain_preserves_source_material_flags_base_codebook_and_crc_rule(self):
        for fmt in range(3):
            for rule in ("header", "data"):
                with self.subTest(fmt=fmt, rule=rule):
                    before = mip.read_native_vq(native(fmt=fmt, rule=rule))
                    result, report = mip.add_mipmaps(native(fmt=fmt, rule=rule), enabled=True, engine="python")
                    after = mip.read_native_vq(result)
                    self.assertEqual(after.codebook, before.codebook)
                    self.assertEqual(after.base_indices, before.base_indices)
                    self.assertEqual(mip.decode_level(after, 8), mip.decode_level(before, 8))
                    self.assertEqual(before.crc_rule, rule)
                    self.assertEqual(after.crc_rule, "header")  # legacy input accepted; enabled output carries the canonical checksum
                    self.assertEqual(after.header[9:], before.header[9:])
                    self.assertEqual(after.texture[:5], before.texture[:5])
                    self.assertEqual(after.texture[6], before.texture[6] | tpl.FLAG_MIPMAP)
                    self.assertEqual(len(after.payload), 2048 + tpl.vq_mip_index_bytes(8))
                    self.assertTrue(report["base_level_exact"])

    def test_idempotent_for_existing_mips(self):
        once, _ = mip.add_mipmaps(native(), enabled=True, engine="python")
        twice, report = mip.add_mipmaps(once, enabled=True, engine="python")
        self.assertEqual(once, twice)
        self.assertFalse(report["changed"])

    def test_bad_crc_and_truncated_input_refuse(self):
        blob = native()
        for bad in (blob[:-1], blob[:100], blob[:-1] + bytes([blob[-1] ^ 1])):
            with self.subTest(size=len(bad)):
                with self.assertRaises(ValueError):
                    mip.add_mipmaps(bad, enabled=True)

    def test_rejects_rectangles_palette_payload_and_runtime_top_drop(self):
        for src in (native(height=16), replace_texture(native(), 3, 4),
                    replace_texture(native(), 7, 1),
                    replace_texture(native(), 6, 1 << 30)):
            with self.assertRaises(ValueError):
                mip.add_mipmaps(src, enabled=True)

    def test_nearest_ties_choose_lowest_index(self):
        out, engine = mip._nearest([(3, 7), (5, 5)], [(3, 7), (3, 7), (7, 3)], "python")
        self.assertEqual(out, [0, 0])
        self.assertEqual(engine, "python")

    def test_transparent_colour_does_not_bleed_into_lower_level_target(self):
        p = [mip._feature((255, 0, 255, 0)), mip._feature((0, 255, 0, 255)),
             mip._feature((255, 0, 255, 0)), mip._feature((0, 255, 0, 255))]
        self.assertEqual(mip._halve(p, 2), [(0, 32513, 0, 32513)])

    def test_one_pixel_level_scores_the_fourth_codebook_pixel(self):
        black, white, grey = mip._feature((0, 0, 0, 255)), mip._feature((255, 255, 255, 255)), mip._feature((128, 128, 128, 255))
        book = [black + black + black + white, white + white + white + grey]
        result, _ = mip._encode_level([white], 1, book, "python")
        self.assertEqual(result, b"\0")

    @unittest.skipUnless(importlib.util.find_spec("numpy"), "optional NumPy is unavailable")
    def test_numpy_and_standard_library_generate_exact_same_bytes(self):
        for fmt in range(3):
            src = native(size=16, fmt=fmt)
            a, _ = mip.add_mipmaps(src, enabled=True, engine="python")
            b, _ = mip.add_mipmaps(src, enabled=True, engine="numpy")
            self.assertEqual(a, b)

    def test_cli_native_default_off_is_identity_and_existing_output_refuses(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = pathlib.Path(tmp)
            src, out = d / "src.re4tex", d / "out.re4tex"
            src.write_bytes(native())
            cmd = [sys.executable, str(TOOLS / "vq_export.py"), "--native-package", str(src), "--package", str(out)]
            subprocess.run(cmd, check=True, capture_output=True)
            self.assertEqual(out.read_bytes(), src.read_bytes())
            self.assertNotEqual(subprocess.run(cmd, capture_output=True).returncode, 0)
            self.assertEqual(out.read_bytes(), src.read_bytes())


@unittest.skipUnless(os.environ.get("MIPMAP_PVRTEX_ORACLE"), "pinned pvrtex decoder oracle not configured")
class DecoderOracle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib = ctypes.CDLL(os.environ["MIPMAP_PVRTEX_ORACLE"])
        cls.call = cls.lib.mipmap_oracle_decode
        cls.call.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_uint, ctypes.c_uint,
                             ctypes.c_int, ctypes.c_uint, ctypes.c_void_p, ctypes.c_size_t]
        cls.call.restype = ctypes.c_int

    def test_all_generated_levels_match_independent_pvrtex_decoder(self):
        for fmt in range(3):
            result, _ = mip.add_mipmaps(native(size=16, fmt=fmt), enabled=True, engine="python")
            n = mip.read_native_vq(result)
            source = ctypes.create_string_buffer(n.payload)
            for power in range(5):
                side = 1 << power
                output = ctypes.create_string_buffer(side * side * 4)
                got = self.call(source, len(n.payload), fmt, 16, 1, power, output, len(output))
                self.assertEqual(got, len(output))
                expected = bytes(c for p in mip.decode_level(n, side) for c in p)
                self.assertEqual(output.raw, expected, (fmt, side))


if __name__ == "__main__":
    unittest.main()
