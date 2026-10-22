"""Generated mip data against the actual native Package reader, off and on."""
import pathlib
import shutil
import subprocess
import unittest

import test_mipmap_vq as data
import test_ps2_room_r4im_texcrc as host


@unittest.skipUnless(shutil.which("g++"), "host compiler required")
class RuntimeMipmapAdmission(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        host.Ps2TextureCrcTests.setUpClass()
        cls.owner = host.Ps2TextureCrcTests
        root = cls.owner.root
        scene = host.ROOT / "room"
        reader = host.READER.replace(
            "a.close();s.close();",
            'if(streamed)std::printf("format:%08x\\n",re4dc::texture::pvr_format(*s.textures()));'
            "a.close();s.close();")
        (root / "reader-mip.cpp").write_text("#include <cstring>\n" + reader)
        cls.exe = root / "reader-mip"
        subprocess.run([
            "g++", "-std=c++17", "-DRE4DC_CAST_MIPMAP=1", "-DRE4DC_TEX_RESIDENT=1",
            "-DRE4DC_STORAGE_BOUNCE_BYTES=16384", "-I" + str(root), "-I" + str(scene),
            str(root / "reader-mip.cpp"), str(scene / "texture_package.cpp"),
            str(scene / "room_storage.cpp"), "-o", str(cls.exe)], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.owner.tearDownClass()

    def read(self, blob, enabled=True):
        path = self.owner.root / "mip-input.re4tex"
        path.write_bytes(blob)
        exe = self.exe if enabled else self.owner.exe["1"]
        return subprocess.run([str(exe), str(path)], capture_output=True, text=True,
                              check=True).stdout.splitlines()

    def test_enabled_reader_admits_each_generated_native_format_and_forwards_mip_flag(self):
        for fmt in range(3):
            blob, _ = data.mip.add_mipmaps(data.native(size=16, fmt=fmt),
                                          enabled=True, engine="python")
            lines = self.read(blob)
            self.assertEqual(lines[0], "ok|ok")
            word = int(lines[1].split(":")[1], 16)
            self.assertTrue(word & 0x80000000)
            self.assertTrue(word & 0x40000000)
            self.assertNotEqual(self.read(blob, enabled=False)[0], "ok|ok")

    def test_existing_base_remains_admitted_and_has_no_mip_flag(self):
        for fmt in range(3):
            lines = self.read(data.native(fmt=fmt))
            self.assertEqual(lines[0], "ok|ok")
            self.assertFalse(int(lines[1].split(":")[1], 16) & 0x80000000)

    def test_legacy_input_generates_canonical_output_admitted_strict_and_streamed(self):
        source = data.native(rule="data")
        self.assertEqual(data.mip.read_native_vq(source).crc_rule, "data")   # supported legacy input
        self.assertEqual(data.mip.add_mipmaps(source)[0], source)            # disabled: exact input
        blob, _ = data.mip.add_mipmaps(source, enabled=True, engine="python")
        self.assertEqual(data.mip.read_native_vq(blob).crc_rule, "header")   # canonical output checksum
        self.assertEqual(self.read(blob)[0], "ok|ok")                        # strict memory and streamed paths

    def test_truncated_chain_is_refused_by_actual_reader(self):
        blob, _ = data.mip.add_mipmaps(data.native(), enabled=True, engine="python")
        self.assertNotEqual(self.read(blob[:-1])[0], "ok|ok")


if __name__ == "__main__":
    unittest.main()
