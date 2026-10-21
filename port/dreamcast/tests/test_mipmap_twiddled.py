"""Square native16-bit mip data, exact bases, and actual renderer admission."""
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
import convert_tpl as tpl
import mipmap_twiddled as mip
from test_pal4_alpha import mutate, FIXTURE
from test_mipmap_pal4 import stubs


def from_words(words, side, fmt=2, height=None, flags=None, rule="header"):
    height = height or side
    flags = (0 if fmt == 0 else 3 if fmt == 1 else 1) if flags is None else flags
    payload = struct.pack("<%dH" % len(words), *tpl.twiddle_16bpp(words, side, height))
    body = tpl.TEXTURE.pack(b"source material", side, height, fmt, 144, len(payload), flags, 1, 0) + payload
    crc = zlib.crc32(body if rule == "header" else payload) & 0xffffffff
    return tpl.HEADER.pack(tpl.MAGIC, 2, 48, 96, 1, 48, 144, len(payload), crc, 7, 29) + body


def native(side=8, fmt=0, height=None, rule="header"):
    height = height or side
    pack = (tpl._pack_565, tpl._pack_1555, tpl._pack_4444)[fmt]
    words = [pack(((x * 17 + y * 3) % 256, (x * 7 + y * 29) % 256,
                   (x * 31 + y * 11) % 256, (x * 37 + y * 21) % 256))
             for y in range(height) for x in range(side)]
    return from_words(words, side, fmt, height, rule=rule)


class TwiddledMipData(unittest.TestCase):
    def test_off_identity_all_formats_and_enabled_base_flags_header_crc_preservation(self):
        for fmt in range(3):
            for rule in ("header", "data"):
                source = native(16, fmt, rule=rule)
                self.assertEqual(mip.add_mipmaps(source)[0], source)
                result, report = mip.add_mipmaps(source, enabled=True)
                before, after = mip.read_native_twiddled(source), mip.read_native_twiddled(result)
                self.assertEqual(before.base_texels, after.base_texels)
                self.assertEqual(mip.decode_level(before, 16), mip.decode_level(after, 16))
                self.assertEqual(before.texture[:5], after.texture[:5])
                self.assertEqual(before.texture[6] | 4, after.texture[6])
                self.assertEqual(before.header[9:], after.header[9:])
                self.assertEqual(after.crc_rule, rule)
                self.assertEqual(after.payload[:6], bytes(6))
                self.assertEqual(len(after.payload), mip.chain_bytes(16))
                self.assertEqual(report["extra_payload_bytes"], 176)
                self.assertEqual(mip.add_mipmaps(result, enabled=True)[0], result)

    def test_alpha_filter_ignores_hidden_red_and_keeps_original_alpha_format(self):
        for fmt, hidden, blue in ((2, 0x0f00, 0xf00f), (1, 0x7c00, 0x801f)):
            words = [blue if x % 2 and y % 2 else hidden for y in range(8) for x in range(8)]
            source = from_words(words, 8, fmt)
            result, _ = mip.add_mipmaps(source, enabled=True)
            pixels = mip.decode_level(mip.read_native_twiddled(result), 4)
            self.assertTrue(all(p[0] == 0 and p[1] == 0 and p[2] == 255 for p in pixels))
            if fmt == 2:
                self.assertEqual({p[3] for p in pixels}, {68})
            else:
                self.assertTrue(all(p[3] in (0, 255) for p in pixels))

    def test_rectangles_linear_vq_and_bad_lengths_are_refused(self):
        source = native()
        for blob in (native(8, height=16), source[:-1], mutate(source, 7, 0),
                     mutate(source, 7, 2), mutate(source, 8, 1), mutate(source, 3, 4)):
            with self.assertRaises(ValueError):
                mip.add_mipmaps(blob, enabled=True)

    def test_exporter_dispatch_is_opt_in_and_preserves_native_payload_kind(self):
        with tempfile.TemporaryDirectory() as directory:
            d = pathlib.Path(directory)
            source = native()
            (d / "source").write_bytes(source)
            for enabled in (False, True):
                out = d / str(enabled)
                cmd = [sys.executable, str(ROOT / "tools/vq_export.py"),
                       "--native-package", str(d / "source"), "--package", str(out)]
                if enabled:
                    cmd.append("--add-mipmaps")
                subprocess.run(cmd, capture_output=True, check=True)
                result = mip.read_native_twiddled(out.read_bytes())
                self.assertEqual(result.texture[7], 1)
                self.assertEqual(result.mipmapped, enabled)
                if not enabled:
                    self.assertEqual(out.read_bytes(), source)

    @unittest.skipUnless(os.environ.get("MIPMAP_PVRTEX_ORACLE"), "independent decoder optional")
    def test_all_levels_all_formats_decode_with_actual_pvrtex(self):
        lib = ctypes.CDLL(os.environ["MIPMAP_PVRTEX_ORACLE"])
        fn = lib.mipmap_oracle_decode_twiddled
        fn.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_uint, ctypes.c_uint,
                       ctypes.c_int, ctypes.c_uint, ctypes.c_void_p, ctypes.c_size_t]
        fn.restype = ctypes.c_int
        for fmt in range(3):
            for side in (8, 32, 128):
                blob, _ = mip.add_mipmaps(native(side, fmt), enabled=True)
                n = mip.read_native_twiddled(blob)
                for at in range(side.bit_length()):
                    size = 1 << at
                    output = ctypes.create_string_buffer(size * size * 4)
                    got = fn(n.payload, len(n.payload), fmt, side, 1, at, output, len(output))
                    expected = bytes(c for p in mip.decode_level(n, size) for c in p)
                    self.assertEqual(got, len(expected))
                    self.assertEqual(output.raw, expected)


RAW_MAIN = r"""
int main(int argc,char** argv) {
    auto bytes=read_bytes(argv[1]);
    const bool accepted=atoi(argv[2])!=0;
    Package p;
    assert(p.adopt(bytes.data(),bytes.size())==accepted);
    if(!accepted) {
        assert(!p.open_streamed(argv[1]));assert(!allocs && !open_files);return 0;
    }
    for(unsigned arm=0;arm<2;++arm) {
        if(arm)assert(p.open_streamed(argv[1]));
        inflight=true;assert(p.upload());
        const auto t=p.textures()[0];
        assert(!memcmp(p.pvr_texture(0),bytes.data()+t.data_offset,t.data_size));
        const unsigned tcw=pvr_format(t);
        assert(bool(tcw&0x80000000U)==bool(t.flags&kMipmap));
        assert(!(tcw&PVR_TXRFMT_VQ_ENABLE));
        assert((tcw&(7U<<27))==unsigned(t.format==0?1U:t.format==1?0U:2U)<<27);
        assert(p.vram_bytes()==t.data_size);
        assert(p.release_payload());close_checked(p);
        assert(!allocs && !open_files);
    }
    assert(!palette_writes);
    return 0;
}
"""


@unittest.skipUnless(shutil.which("g++"), "host compiler required")
class TwiddledMipRuntime(unittest.TestCase):
    def test_actual_reader_native_copy_flags_fences_and_invalid_layouts(self):
        with tempfile.TemporaryDirectory() as directory:
            d = pathlib.Path(directory)
            stubs(d)
            prefix = FIXTURE[:FIXTURE.index("int main(")]
            old = "assert(!inflight);memcpy(q,p,w*h*2);"
            self.assertIn(old, prefix)
            prefix = prefix.replace(old, 'assert(false && "twiddled mips must not be retwiddled");')
            (d / "reader.cpp").write_text(prefix + RAW_MAIN)
            cases = {}
            for fmt in range(3):
                base = native(fmt=fmt)
                chain, _ = mip.add_mipmaps(base, enabled=True)
                cases["base%d" % fmt] = base
                cases["chain%d" % fmt] = chain
            chain = cases["chain2"]
            cases.update(truncated=chain[:-1], rectangle=mutate(chain, 2, 16),
                         linear=mutate(chain, 7, 0), reserved=mutate(chain, 8, 1),
                         giant=mutate(mutate(chain, 1, 1 << 31), 2, 1 << 31))
            for name, blob in cases.items():
                (d / name).write_bytes(blob)
            for knob in (0, 1):
                for palette in (0, 1):
                    exe = d / "reader"
                    flags = ["-DRE4DC_TEX_TWIDDLED_MIPMAP=" + str(knob),
                             "-DRE4DC_TEX_PAL4_MIPMAP=" + str(palette),
                             "-DRE4DC_TEX_PAL4_ALPHA=1",
                             "-DRE4DC_UI_VRAM=" + str(palette)]
                    subprocess.run(["g++", "-std=c++17", "-DRE4DC_CAST_MIPMAP=1",
                        "-DRE4DC_PVR_PIPELINE=1", "-DRE4DC_STORAGE_BOUNCE_BYTES=16384",
                        "-fsanitize=address,undefined", "-fno-omit-frame-pointer",
                        "-I" + str(d), "-I" + str(ROOT / "room")] + flags +
                        [str(d / "reader.cpp"), str(ROOT / "room/texture_package.cpp"),
                         str(ROOT / "room/room_storage.cpp"), "-o", str(exe)],
                        capture_output=True, check=True)
                    for name in cases:
                        accepted = name.startswith("base") or name.startswith("chain") and knob == 1
                        subprocess.run([str(exe), str(d / name), str(int(accepted))],
                                       capture_output=True, check=True, timeout=5)

    def test_build_flag_and_parent_guard(self):
        make = shutil.which("make")
        if not make:
            self.skipTest("make optional")
        text = (ROOT / "game/game30.mk").read_text()
        block = text[text.index("# Native square 16-bit twiddled mip chains"):
                     text.index("# Exact private r11f Mendez/Luis")]
        with tempfile.TemporaryDirectory() as directory:
            d = pathlib.Path(directory)
            (d / "guard.mk").write_text(block +
                "\nobj/native-reuse/texture_package.o:\n\t@echo FLAGS=$(PLATFORM_CPPFLAGS)\n")
            for args, allowed in (([], True), (["TEX_TWIDDLED_MIPMAP=2"], False),
                                  (["TEX_TWIDDLED_MIPMAP=1"], False),
                                  (["TEX_TWIDDLED_MIPMAP=1", "CAST_MIPMAP=1"], True)):
                result = subprocess.run([make, "--no-print-directory", "-f", str(d / "guard.mk"),
                    "OBJDIR=obj", "obj/native-reuse/texture_package.o"] + args,
                    capture_output=True, text=True)
                self.assertEqual(result.returncode == 0, allowed, result.stderr)
                if not args:
                    self.assertNotIn("RE4DC_TEX_TWIDDLED_MIPMAP", result.stdout)
                elif allowed:
                    self.assertIn("-DRE4DC_TEX_TWIDDLED_MIPMAP=1", result.stdout)


if __name__ == "__main__":
    unittest.main()
