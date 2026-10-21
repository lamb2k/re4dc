"""Compact palette mip data and actual Package admission/upload contracts."""
import ctypes
import os
import pathlib
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import convert_tpl as tpl
import mipmap_pal4 as mip
from test_pal4_alpha import native, mutate, PVR_H, FIXTURE


def package(side=8, height=None):
    palette = [0x0000, 0x0f00, 0x1000, 0x2456, 0x4abc, 0x6def, 0x8ace, 0x9bdf,
               0xafed, 0xbcba, 0xccbb, 0xd123, 0xeeee, 0xf00f, 0xffff, 0xfedc]
    height = height or side
    pixels = [palette[(x * 7 + y * 3 + x * y) % 16]
              for y in range(height) for x in range(side)]
    return tpl.package_exact_pal4_argb4444(native(pixels, side, height, 1))[0]


class PaletteMipData(unittest.TestCase):
    def test_disabled_exact_and_enabled_preserves_palette_base_flags_identity(self):
        for side in (8, 16, 64):
            source = package(side)
            self.assertEqual(mip.add_mipmaps(source)[0], source)
            result, report = mip.add_mipmaps(source, enabled=True, engine="python")
            before, after = mip.read_native_pal4(source), mip.read_native_pal4(result)
            self.assertEqual(before.palette, after.palette)
            self.assertEqual(before.base_indices, after.base_indices)
            self.assertEqual(mip.decode_level(before, side), mip.decode_level(after, side))
            self.assertEqual(before.texture[:5], after.texture[:5])
            self.assertEqual(before.texture[6] | 4, after.texture[6])
            self.assertEqual(before.header[9:], after.header[9:])
            self.assertEqual(len(after.payload), mip.chain_bytes(side) + 32)
            self.assertEqual(report["extra_payload_bytes"], mip.chain_bytes(side) - side * side // 2)
            self.assertEqual(after.payload[0], 0)
            self.assertEqual(after.payload[1] & 15, after.payload[1] >> 4)
            self.assertEqual(mip.add_mipmaps(result, enabled=True)[0], result)

    def test_legacy_crc_convention_and_base_stay_exact(self):
        import zlib
        source = bytearray(package())
        struct.pack_into("<I", source, 36, zlib.crc32(source[144:]) & 0xffffffff)
        result, _ = mip.add_mipmaps(source, enabled=True, engine="python")
        after = mip.read_native_pal4(result)
        self.assertEqual(after.crc_rule, "data")
        self.assertEqual(after.base_indices, bytes(source[144:-32]))

    def test_invalid_layouts_and_palette_tail_are_refused(self):
        source = package()
        for blob in (source[:-1], package(8, 16), mutate(source, 7, 2),
                     mutate(source, 8, 1), mutate(source, 3, 3)):
            with self.assertRaises(ValueError):
                mip.add_mipmaps(blob, enabled=True)

    def test_numpy_and_python_are_byte_identical(self):
        try:
            import numpy
        except ImportError:
            self.skipTest("NumPy optional")
        a, _ = mip.add_mipmaps(package(16), enabled=True, engine="python")
        b, _ = mip.add_mipmaps(package(16), enabled=True, engine="numpy")
        self.assertEqual(a, b)

    def test_exporter_dispatch_default_off_and_opt_in(self):
        with tempfile.TemporaryDirectory() as directory:
            d = pathlib.Path(directory)
            (d / "src").write_bytes(package())
            for enabled in (False, True):
                out = d / ("on" if enabled else "off")
                cmd = [sys.executable, str(ROOT / "tools/vq_export.py"),
                       "--native-package", str(d / "src"), "--package", str(out)]
                if enabled:
                    cmd.append("--add-mipmaps")
                subprocess.run(cmd, capture_output=True, check=True)
                if not enabled:
                    self.assertEqual(out.read_bytes(), (d / "src").read_bytes())
                self.assertEqual(mip.read_native_pal4(out.read_bytes()).mipmapped, enabled)

    @unittest.skipUnless(os.environ.get("MIPMAP_PVRTEX_ORACLE"), "independent decoder optional")
    def test_actual_pvrtex_decodes_all_generated_levels_and_exact_alpha(self):
        lib = ctypes.CDLL(os.environ["MIPMAP_PVRTEX_ORACLE"])
        fn = lib.mipmap_oracle_decode_pal4
        fn.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_uint, ctypes.c_int,
                       ctypes.c_uint, ctypes.c_void_p, ctypes.c_size_t]
        fn.restype = ctypes.c_int
        for side in (8, 16, 64):
            for enabled in (False, True):
                blob, _ = mip.add_mipmaps(package(side), enabled=enabled, engine="python")
                n = mip.read_native_pal4(blob)
                levels = range(side.bit_length()) if enabled else [side.bit_length() - 1]
                for at in levels:
                    s = 1 << at
                    out = ctypes.create_string_buffer(s * s * 4)
                    got = fn(n.payload, len(n.payload), side, enabled, at, out, len(out))
                    expected = bytes(c for p in mip.decode_level(n, s) for c in p)
                    self.assertEqual(got, len(expected))
                    self.assertEqual(out.raw, expected)


def stubs(root):
    (root / "dc/pvr").mkdir(parents=True)
    (root / "kos").mkdir()
    (root / "dc/pvr.h").write_text(PVR_H)
    (root / "dc/pvr/pvr_mem.h").write_text(
        "#include <cstddef>\nvoid* pvr_mem_malloc(std::size_t);void pvr_mem_free(void*);\n")
    (root / "dc/pvr/pvr_txr.h").write_text(
        "#include <cstddef>\n#define PVR_TXRLOAD_16BPP 0\n"
        "void pvr_txr_load_ex(const void*,void*,unsigned,unsigned,unsigned);"
        "void pvr_txr_load(const void*,void*,std::size_t);\n")
    (root / "kos/fs.h").write_text(
        "#pragma once\n#include <sys/types.h>\nusing file_t=int;\n#define FILEHND_INVALID -1\n"
        "int fs_open(const char*,int);int fs_close(int);ssize_t fs_total(int);"
        "void* fs_mmap(int);ssize_t fs_read(int,void*,size_t);off_t fs_seek(int,off_t,int);\n")
    (root / "kos.h").write_text(
        "#include <kos/fs.h>\n#include <fcntl.h>\n#include <cstdint>\nstd::uint64_t timer_us_gettime64();\n")


PALETTE_MAIN = r"""
int main(int argc,char** argv) {
    const auto path=std::string(argv[1]);
    const bool accepted=atoi(argv[2])!=0;
    reserved_count=8;
    for(unsigned i=0;i<1024;++i)palette[i]=0x12345678U+i;
    assert(initialize_palettes(0xff));
    auto bytes=read_bytes(path);
    Package p;
    const bool adopted=p.adopt(bytes.data(),bytes.size());
    assert(adopted==accepted);
    if(!adopted) {
        assert(!p.open_streamed(path.c_str()));
        assert(!allocs && !open_files && !palette_writes);
        return 0;
    }
    inflight=true;assert(p.upload());check_palette(p);
    assert(!memcmp(p.pvr_texture(0),bytes.data()+p.textures()[0].data_offset,p.textures()[0].data_size));
    assert(p.vram_bytes()==p.textures()[0].data_size);
    assert(p.release_payload());memset(bytes.data(),0xcc,bytes.size());check_palette(p);
    close_checked(p);
    assert(p.open_streamed(path.c_str()));
    inflight=true;assert(p.upload());check_palette(p);
    assert(p.release_payload());close_checked(p);
    assert(!allocs && !open_files);
    return 0;
}
"""


@unittest.skipUnless(shutil.which("g++"), "host compiler required")
class PaletteMipRuntime(unittest.TestCase):
    def test_actual_reader_flag_upload_palette_tail_fences_and_refusals(self):
        with tempfile.TemporaryDirectory() as directory:
            d = pathlib.Path(directory)
            stubs(d)
            prefix = FIXTURE[:FIXTURE.index("int main(")].replace(
                "assert(!(tcw&0x80000000U));",
                "assert(bool(tcw&0x80000000U)==bool(t.flags&kMipmap));")
            (d / "reader.cpp").write_text(prefix + PALETTE_MAIN)
            base = package()
            chain, _ = mip.add_mipmaps(base, enabled=True, engine="python")
            cases = dict(base=base, chain=chain, truncated=chain[:-1],
                         rectangular=mutate(chain, 2, 16), wrong_layout=mutate(chain, 7, 2),
                         reserved=mutate(chain, 8, 1))
            for name, blob in cases.items():
                (d / name).write_bytes(blob)
            for knob in (0, 1):
                for vram in (0, 1):
                    exe = d / "reader"
                    command = ["g++", "-std=c++17", "-DRE4DC_STORAGE_BOUNCE_BYTES=16384",
                        "-DRE4DC_PVR_PIPELINE=1", "-DRE4DC_TEX_PAL4_ALPHA=1",
                        "-DRE4DC_CAST_MIPMAP=1", "-DRE4DC_TEX_PAL4_MIPMAP=" + str(knob),
                        "-DRE4DC_UI_VRAM=" + str(vram),
                        "-fsanitize=address,undefined", "-fno-omit-frame-pointer",
                        "-I" + str(d), "-I" + str(ROOT / "room"),
                        str(d / "reader.cpp"), str(ROOT / "room/texture_package.cpp"),
                        str(ROOT / "room/room_storage.cpp"), "-o", str(exe)]
                    subprocess.run(command, capture_output=True, check=True)
                    for name in cases:
                        accepted = name == "base" or name == "chain" and knob == 1
                        subprocess.run([str(exe), str(d / name), str(int(accepted))],
                                       capture_output=True, check=True)

    def test_build_knob_defaults_off_and_requires_both_parent_paths(self):
        make = shutil.which("make")
        if not make:
            self.skipTest("make optional")
        text = (ROOT / "game/game30.mk").read_text()
        block = text[text.index("# Compact square twiddled PAL4"):text.index("# Exact private r11f Mendez/Luis")]
        with tempfile.TemporaryDirectory() as directory:
            d = pathlib.Path(directory)
            (d / "guard.mk").write_text(block + "\nobj/native-reuse/texture_package.o:\n\t@echo FLAGS=$(PLATFORM_CPPFLAGS)\n")
            for args, allowed in (([], True), (["TEX_PAL4_MIPMAP=2"], False),
                                  (["TEX_PAL4_MIPMAP=1"], False),
                                  (["TEX_PAL4_MIPMAP=1", "TEX_PAL4_ALPHA=1"], False),
                                  (["TEX_PAL4_MIPMAP=1", "TEX_PAL4_ALPHA=1", "CAST_MIPMAP=1"], True)):
                result = subprocess.run([make, "--no-print-directory", "-f", str(d / "guard.mk"),
                                         "OBJDIR=obj", "obj/native-reuse/texture_package.o"] + args, capture_output=True, text=True)
                self.assertEqual(result.returncode == 0, allowed, result.stderr)
                if not args:
                    self.assertNotIn("RE4DC_TEX_PAL4_MIPMAP", result.stdout)
                elif allowed:
                    self.assertIn("-DRE4DC_TEX_PAL4_MIPMAP=1", result.stdout)

    def test_off_host_object_exact_to_integration_source(self):
        with tempfile.TemporaryDirectory() as directory:
            d = pathlib.Path(directory)
            stubs(d)
            original = subprocess.run(
                ["git", "-C", str(ROOT), "show", "54cef5d1:port/dreamcast/room/texture_package.cpp"],
                capture_output=True, check=True).stdout
            objects = []
            for label, source in (("control", original),
                                  ("current", (ROOT / "room/texture_package.cpp").read_bytes())):
                (d / label).mkdir()
                cpp = d / label / "texture_package.cpp"
                cpp.write_bytes(source)
                obj = d / label / "package.o"
                command = ["g++", "-std=c++17", "-O2", "-g0", "-frandom-seed=mipmap21",
                    "-DRE4DC_TEX_PAL4_ALPHA=1", "-DRE4DC_CAST_MIPMAP=1",
                    "-DRE4DC_STORAGE_BOUNCE_BYTES=16384", "-I" + str(d),
                    "-I" + str(ROOT / "room"), "-c", str(cpp), "-o", str(obj)]
                subprocess.run(command, capture_output=True, check=True)
                objects.append(obj.read_bytes())
            self.assertEqual(*objects)


if __name__ == "__main__":
    unittest.main()
