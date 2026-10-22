"""Lossless dictionary coding, complete byte costs and native reader contract."""
import ctypes
import os
import pathlib
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import compact_native_vq as compact
import mipmap_pal4 as pal4
import mipmap_twiddled as twiddled
import mipmap_vq as vq
from test_mipmap_pal4 import package, stubs
from test_mipmap_twiddled import from_words, RAW_MAIN
from test_pal4_alpha import FIXTURE, mutate


def raw(fmt=0, side=64, rule="header"):
    words = [(x // 2 + y // 2 * 19) % 128 * 509 & 65535
             for y in range(side) for x in range(side)]
    return from_words(words, side, fmt, rule=rule)


class LosslessNativeVq(unittest.TestCase):
    def test_raw_all_formats_preserve_words_rgba_flags_material_crc_and_off_bytes(self):
        for fmt in range(3):
            for rule in ("header", "data"):
                source = raw(fmt, rule=rule)
                self.assertEqual(compact.compact(source)[0], source)
                result, report = compact.compact(source, enabled=True)
                self.assertTrue(report["changed"])
                before, after = twiddled.read_native_twiddled(source), vq.read_native_vq(result)
                self.assertEqual(after.crc_rule, rule)
                self.assertEqual(before.texture[:5], after.texture[:5])
                self.assertEqual(before.texture[6], after.texture[6])
                self.assertEqual(before.header[9:], after.header[9:])
                self.assertEqual(twiddled.decode_level(before, 64), vq.decode_level(after, 64))
                self.assertEqual(len(after.payload), 2048 + 64 * 64 // 4)
                self.assertEqual(compact.compact(result, enabled=True)[0], result)

    def test_palette_exact_alpha_and_covered_uv_marker(self):
        source = bytearray(package(128))
        struct.pack_into("<I", source, 44, 0x80000000 | 100 | 93 << 11)
        result, report = compact.compact(source, enabled=True)
        self.assertTrue(report["changed"])
        before, after = pal4.read_native_pal4(source), vq.read_native_vq(result)
        self.assertEqual(after.texture[3], 2)
        self.assertEqual(before.texture[0:3], after.texture[0:3])
        self.assertEqual(before.texture[6], after.texture[6])
        self.assertEqual(before.header[9:], after.header[9:])
        self.assertEqual(pal4.decode_level(before, 128), vq.decode_level(after, 128))
        self.assertEqual(report["saved_payload_bytes"], 2080)

    def test_more_than256_vectors_and_unprofitable_small_palettes_are_unchanged(self):
        source = from_words(list(range(4096)), 64)
        result, report = compact.compact(source, enabled=True)
        self.assertEqual(result, source)
        self.assertEqual(report["reason"], "requires-lossy-vector-quantization")
        for side in (8, 16, 32, 64):
            source = package(side)
            result, report = compact.compact(source, enabled=True)
            self.assertEqual(result, source)
            self.assertEqual(report["reason"], "vq-codebook-overhead-does-not-win")

    def test_existing_mips_are_preserved_and_invalid_layouts_are_refused(self):
        source, _ = twiddled.add_mipmaps(raw(), enabled=True)
        self.assertEqual(compact.compact(source, enabled=True)[0], source)
        source = raw()
        for invalid in (source[:-1], mutate(source, 2, 32), mutate(source, 7, 0),
                        mutate(source, 8, 1), mutate(source, 3, 3)):
            with self.assertRaises(ValueError):
                compact.compact(invalid, enabled=True)

    @unittest.skipUnless(os.environ.get("MIPMAP_PVRTEX_ORACLE"), "independent decoder optional")
    def test_actual_pvrtex_independent_decoders_match_all_base_pixels_and_alpha(self):
        lib = ctypes.CDLL(os.environ["MIPMAP_PVRTEX_ORACLE"])
        outfn = lib.mipmap_oracle_decode
        outfn.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_uint, ctypes.c_uint,
                         ctypes.c_int, ctypes.c_uint, ctypes.c_void_p, ctypes.c_size_t]
        outfn.restype = ctypes.c_int
        for source in [raw(f) for f in range(3)] + [package(128)]:
            result, report = compact.compact(source, enabled=True)
            n = vq.read_native_vq(result)
            size = n.size
            output = ctypes.create_string_buffer(size * size * 4)
            self.assertEqual(outfn(n.payload, len(n.payload), n.texture[3], size, 0,
                                  size.bit_length()-1, output, len(output)), len(output))
            if report["source_format"] == 4:
                before = pal4.read_native_pal4(source)
                expected = pal4.decode_level(before, size)
            else:
                before = twiddled.read_native_twiddled(source)
                expected = twiddled.decode_level(before, size)
            self.assertEqual(output.raw, bytes(c for p in expected for c in p))


@unittest.skipUnless(shutil.which("g++"), "host compiler required")
class NativeVqReader(unittest.TestCase):
    def test_actual_reader_uploads_exact_vq_bytes_without_new_runtime_flags(self):
        with tempfile.TemporaryDirectory() as directory:
            d = pathlib.Path(directory)
            stubs(d)
            prefix = FIXTURE[:FIXTURE.index("int main(")]
            prefix = prefix.replace("assert(!inflight);memcpy(q,p,w*h*2);",
                                    'assert(false && "native VQ must not be retwiddled");')
            main = RAW_MAIN.replace("assert(!(tcw&PVR_TXRFMT_VQ_ENABLE));",
                                    "assert(tcw&PVR_TXRFMT_VQ_ENABLE);")
            (d / "reader.cpp").write_text(prefix + main)
            for fmt in range(3):
                result, _ = compact.compact(raw(fmt), enabled=True)
                (d / str(fmt)).write_bytes(result)
            result, _ = compact.compact(package(128), enabled=True)
            (d / "pal4").write_bytes(result)
            for allocator in (0, 1):
                exe = d / "reader"
                subprocess.run(["g++", "-std=c++17", "-DRE4DC_PVR_PIPELINE=1",
                    "-DRE4DC_STORAGE_BOUNCE_BYTES=16384", "-DRE4DC_UI_VRAM=" + str(allocator),
                    "-fsanitize=address,undefined", "-fno-omit-frame-pointer",
                    "-I" + str(d), "-I" + str(ROOT / "room"), str(d / "reader.cpp"),
                    str(ROOT / "room/texture_package.cpp"), str(ROOT / "room/room_storage.cpp"),
                    "-o", str(exe)], capture_output=True, check=True)
                for filename in ("0", "1", "2", "pal4"):
                    subprocess.run([str(exe), str(d / filename), "1"],
                                   capture_output=True, check=True, timeout=5)


if __name__ == "__main__":
    unittest.main()
