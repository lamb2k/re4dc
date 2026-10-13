"""Converter roundtrip and hostile-package tests; generated fixtures are synthetic."""
import argparse
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fit_ps2_world_textures as fit


def package(width, height, fmt, flags, kind, payload):
    desc = fit.tpl.TEXTURE.pack(b'synthetic', width, height, fmt, 144, len(payload), flags, kind, 0)
    body = desc + payload
    return fit.tpl.HEADER.pack(fit.tpl.MAGIC, 2, 48, 96, 1, 48, 144,
                               len(payload), zlib.crc32(body), 1, 0) + body


def build_runtime_checker(root):
    """Compile the actual Package::adopt/validate body; never call PVR upload."""
    include = root / 'include'
    (include / 'dc' / 'pvr').mkdir(parents=True, exist_ok=True)
    (include / 'kos').mkdir(parents=True, exist_ok=True)
    (include / 'kos' / 'fs.h').write_text('''#pragma once
#include <sys/types.h>
#include <cstddef>
using file_t = int;
constexpr int FILEHND_INVALID = -1;
inline int fs_open(const char*, int) { return -1; }
inline ssize_t fs_total(int) { return -1; }
inline void* fs_mmap(int) { return nullptr; }
inline int fs_close(int) { return 0; }
inline int fs_seek(int, off_t, int) { return -1; }
inline ssize_t fs_read(int, void*, std::size_t) { return -1; }
''')
    (include / 'dc' / 'pvr.h').write_text('''#pragma once
#include <cstddef>
using pvr_ptr_t = void*;
constexpr unsigned PVR_TXRFMT_RGB565=1, PVR_TXRFMT_ARGB1555=2, PVR_TXRFMT_ARGB4444=3;
constexpr unsigned PVR_TXRFMT_VQ_ENABLE=4, PVR_TXRLOAD_16BPP=16;
inline void* pvr_mem_malloc(std::size_t) { return nullptr; }
inline void pvr_mem_free(void*) {}
inline void pvr_txr_load(const void*, void*, std::size_t) {}
inline void pvr_txr_load_ex(const void*, void*, unsigned, unsigned, unsigned) {}
''')
    for name in ('pvr_mem.h', 'pvr_txr.h'):
        (include / 'dc' / 'pvr' / name).write_text('#include <dc/pvr.h>\n')
    source = root / 'texture-check.cpp'
    source.write_text('''#include "texture_package.hpp"
#include <fstream>
#include <iostream>
#include <iterator>
#include <string>
#include <vector>
int main() {
    std::string path; unsigned total=0, rejected=0;
    while(std::getline(std::cin,path)) {
        std::ifstream f(path,std::ios::binary);
        std::vector<std::uint8_t> bytes((std::istreambuf_iterator<char>(f)), {});
        re4dc::texture::Package package;
        if(!package.adopt(bytes.data(),bytes.size())) {
            ++rejected; std::cerr << path << ": " << package.error() << "\\n";
        }
        ++total;
    }
    std::cout << "runtime Package::adopt: " << total << " checked, " << rejected << " rejected\\n";
    return rejected?1:0;
}
''')
    room = Path(fit.__file__).resolve().parents[1] / 'room'
    binary = root / 'texture-check'
    subprocess.run(['g++', '-std=c++17', '-O1', '-ffunction-sections', '-fdata-sections',
                    '-Wl,--gc-sections', '-I', str(include), '-I', str(room), str(source),
                    str(room / 'texture_package.cpp'), '-o', str(binary)], check=True)
    return binary


class TextureFitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.TemporaryDirectory()
        cls.root = Path(cls.work.name)
        cls.checker = build_runtime_checker(cls.root / 'host')

    @classmethod
    def tearDownClass(cls):
        cls.work.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=self.root)
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)

    def runtime(self, paths):
        return subprocess.run([str(self.checker)], input=''.join(str(p) + '\n' for p in paths),
                              capture_output=True, text=True)

    def test_known_vq_codebook_expands_in_twiddle_order(self):
        words = [0] * 1024
        words[0:4] = [0xf800, 0x07e0, 0x001f, 0xffff]
        blob = package(8, 8, 0, 0, 2, struct.pack('<1024H', *words) + bytes(16))
        path = self.path / 'known.re4tex'
        path.write_bytes(blob)
        decoded = fit.decode(path)
        self.assertEqual(decoded[0], (255, 0, 0, 255))
        self.assertEqual(decoded[8], (0, 255, 0, 255))
        self.assertEqual(decoded[1], (0, 0, 255, 255))
        self.assertEqual(decoded[9], (255, 255, 255, 255))
        self.assertEqual(self.runtime([path]).returncode, 0)

    def test_valid_crc_cannot_hide_invalid_payload_size(self):
        path = self.path / 'wrong-size.re4tex'
        path.write_bytes(package(8, 8, 0, 0, 2, bytes(2048)))
        with self.assertRaisesRegex(ValueError, 'runtime parser rejected'):
            fit.metadata(path)
        self.assertEqual(self.runtime([path]).returncode, 1)

    def test_corrupt_payload_is_rejected_by_actual_runtime(self):
        path = self.path / 'corrupt.re4tex'
        data = bytearray(package(8, 8, 0, 0, 1, bytes(128)))
        data[-1] ^= 1
        path.write_bytes(data)
        with self.assertRaisesRegex(ValueError, 'corrupt RE4DCTX'):
            fit.metadata(path)
        result = self.runtime([path])
        self.assertEqual(result.returncode, 1)
        self.assertIn('payload CRC mismatch', result.stderr)

    def test_alpha_change_without_coverage_change_is_rejected(self):
        result = fit.compare([(128, 128, 128, 136)], [(128, 128, 128, 153)])
        self.assertFalse(result['alpha_exact'])
        self.assertEqual(result['coverage_changed_pixels'], 0)
        self.assertEqual(result['rgb_psnr_db'], 99)

    def test_fixture_missing_pack_key_selects_exact_loose(self):
        import audit_ps2_texture_winners as audit
        selected = package(8, 8, 0, 0, 1, bytes(128))
        unrelated = package(8, 8, 0, 0, 1, bytes([255]) * 128)
        source = self.path / '12345678-90abcdef.re4tex'
        source.write_bytes(selected)
        pack_path = self.path / 'synthetic.pak'
        pack_path.write_bytes(audit.texpack.build({(1, 2): unrelated})[0])
        staging = self.path / 'room.json'
        fit.write_json(staging, dict(room='r000', textures=[dict(key=source.stem, chosen=fit.metadata(source), reason='test')]))
        fixture = self.path / 'fixture.json'
        fit.write_json(fixture, dict(replace={'dc/tex.pak': str(pack_path),
            'dc/tex/1/' + source.name: str(source)}, remove=[]))
        result = audit.audit(pack_path, [staging], self.path / 'audit.json', {'r000': fixture})['rooms']['r000']
        self.assertEqual(result['fixture_selection'], 'PASS_SELECTED_RENDER_BYTES')
        self.assertEqual(result['textures'][0]['selected_origin'], 'fixture_loose')
        # A present but stale member shadows the otherwise correct loose file.
        pack_path.write_bytes(audit.texpack.build({(0x12345678, 0x90abcdef): unrelated})[0])
        result = audit.audit(pack_path, [staging], self.path / 'audit.json', {'r000': fixture})['rooms']['r000']
        self.assertEqual(result['fixture_selection'], 'FAIL_SELECTED_RENDER_BYTES')
        self.assertEqual(result['textures'][0]['status'], 'STALE_PACK_SHADOWS_CHOICE')
        # A removal invalidates the loose replacement's first-pass availability.
        pack_path.write_bytes(audit.texpack.build({(1, 2): unrelated})[0])
        fit.write_json(fixture, dict(replace={'dc/tex.pak': str(pack_path),
            'dc/tex/1/' + source.name: str(source)}, remove=['dc/tex/1/' + source.name]))
        result = audit.audit(pack_path, [staging], self.path / 'audit.json', {'r000': fixture})['rooms']['r000']
        self.assertEqual(result['fixture_selection'], 'FAIL_SELECTED_RENDER_BYTES')
    def test_actual_encoder_roundtrip_and_determinism_preserve_flags(self):
        if not Path(fit.vq.PVRTEX).is_file():
            self.skipTest('pinned KOS pvrtex is unavailable')
        width = height = 128
        # Four native colors and a binary cutout boundary fit in the codebook.
        linear = [0 if x < 32 else (0xfc00 if x < 64 else 0x83e0 if y < 64 else 0x801f)
                  for y in range(height) for x in range(width)]
        payload = struct.pack('<%dH' % len(linear), *fit.tpl.twiddle_16bpp(linear, width, height))
        source = self.path / '12345678-90abcdef.re4tex'
        source.write_bytes(package(width, height, 1, 0, 1, payload))
        baseline = fit.metadata(source)
        options = dict(min_bytes=32768, min_side=32, min_rgb_psnr=30.0, pvrtex=fit.vq.PVRTEX)
        results = []
        for name in ('first', 'second'):
            args = argparse.Namespace(output=self.path / name, **options)
            results.append(fit.fit_key(source.stem, [dict(baseline=baseline)], args, {'test': 1}))
        first, second = results
        self.assertEqual(first['reason'], 'vq_alpha_exact_rgb_quality_pass')
        self.assertEqual(first['chosen']['sha256'], second['chosen']['sha256'])
        self.assertEqual(first['chosen']['flags'], 0)
        self.assertEqual(first['candidate']['quality']['alpha_changed_pixels'], 0)
        self.assertEqual(first['candidate']['quality']['rgb_psnr_db'], 99.0)
        self.assertEqual(fit.sha(source), baseline['sha256'])
        self.assertEqual(self.runtime([source, first['chosen']['path']]).returncode, 0)


if __name__ == '__main__':
    unittest.main()