"""Boundary tests for source/tool/output rejection; no original game data."""
import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import zipfile
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build_ps2_assets as build


def fixture(root):
    (root / 'tex').mkdir()
    payload = b'\x00\x00' * 4
    fnv = 2166136261
    for b in payload:
        fnv = ((fnv ^ b) * 16777619) & 0xffffffff
    crc = zlib.crc32(payload)
    name = f'{crc:08x}-{fnv:08x}.re4tex'
    desc = struct.pack('<64s8I', b'synthetic test', 2, 2, 0, 144, 8, 0, 1, 0)
    head = struct.pack('<8s10I', b'RE4DCTX\0', 2, 48, 96, 1, 48, 144, 8, zlib.crc32(desc + payload), 1, 0)
    (root / 'tex' / name).write_bytes(head + desc + payload)
    body = struct.pack('<IIHHBBBB', crc, fnv, 0, 0, 0, 0, 0, 0)
    body += struct.pack('<HH12f', 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0)
    crc = zlib.crc32(body)
    (root / 'ps2-world.r4pw').write_bytes(struct.pack('<4s7I', b'R4PW', 1, 1, 1, 1, crc, 0, 0) + body)
    (root / 'ps2-world.ids').write_bytes(struct.pack('<4s3I', b'R4ID', 1, 1, crc) + b'\x05' + b'\x00' * 15)
    # Only the mesh header/CRC is inspected by this boundary check.
    mesh = [b'R4IM', 3, 112, zlib.crc32(b'\x00' * 32), 1, 1] + [0] * 14
    (root / 'ps2-world.re4mesh').write_bytes(struct.pack('<4s19I', *mesh) + b'\x00' * 32)
    return name


class BuildBoundaries(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_valid_bindings(self):
        fixture(self.root)
        self.assertEqual(build.validate_runtime(self.root)['textures'], 1)

    def test_missing_bound_texture(self):
        name = fixture(self.root)
        (self.root / 'tex' / name).unlink()
        with self.assertRaisesRegex(ValueError, 'texture bindings'):
            build.validate_runtime(self.root)

    def test_changed_mesh_crc(self):
        fixture(self.root)
        p = self.root / 'ps2-world.re4mesh'
        data = bytearray(p.read_bytes()); data[-1] = 1; p.write_bytes(data)
        with self.assertRaisesRegex(ValueError, 'R4IM CRC'):
            build.validate_runtime(self.root)

    def test_ids_from_another_sidecar(self):
        fixture(self.root)
        p = self.root / 'ps2-world.ids'
        data = bytearray(p.read_bytes()); data[12] ^= 1; p.write_bytes(data)
        with self.assertRaisesRegex(ValueError, 'R4ID'):
            build.validate_runtime(self.root)

    def test_changed_texture_crc(self):
        name = fixture(self.root)
        p = self.root / 'tex' / name
        data = bytearray(p.read_bytes()); data[-1] ^= 1; p.write_bytes(data)
        with self.assertRaisesRegex(ValueError, 'RE4DCTX'):
            build.validate_runtime(self.root)

    def test_wrong_ps2_disc_rejected_before_hashing(self):
        p = self.root / 'wrong.iso'; p.write_bytes(b'wrong')
        pin = json.loads(build.PROFILE.read_text())['source']
        with self.assertRaisesRegex(ValueError, 'ISO size'):
            build.check_ps2(p, pin)

    def test_wrong_gc_disc(self):
        p = self.root / 'wrong.iso'; p.write_bytes(b'wrong')
        with self.assertRaisesRegex(ValueError, 'G4BE08'):
            build.check_gc(p, {})

    def test_cached_tool_hash_mismatch(self):
        root = self.root / ('dat-' + 'a' * 12); root.mkdir()
        (root / 'tool.exe').write_bytes(b'wrong')
        pin = dict(archive_sha256='a' * 64, exe='tool.exe', exe_sha256='b' * 64)
        with self.assertRaisesRegex(ValueError, 'changed tool cache'):
            build.fetch_tool(self.root, 'dat', pin)

    def test_zip_path_traversal(self):
        archive = self.root / 'bad.zip'
        with zipfile.ZipFile(archive, 'w') as z:
            z.writestr('../escape.exe', b'no')
        digest = build.sha(archive)
        archive.rename(self.root / (digest + '.zip'))
        pin = dict(archive_sha256=digest, exe='tool.exe', exe_sha256='b' * 64)
        with self.assertRaisesRegex(ValueError, 'unsafe tool ZIP'):
            build.fetch_tool(self.root, 'dat', pin)
        self.assertFalse((self.root / ('dat-' + digest[:12])).exists())


if __name__ == '__main__':
    unittest.main()
