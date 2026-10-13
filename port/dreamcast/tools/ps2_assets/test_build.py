"""Boundary tests for source/tool/output rejection; no original game data."""
import argparse
import contextlib
import io
import json
from pathlib import Path
import shutil
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build_ps2_assets as build
import convert_room_bins


def fixture(root):
    """One prelit triangle, one placement, and one loadable 8x8 texture."""
    (root / 'tex').mkdir()
    payload = b'\x00\x00' * 64
    fnv = 2166136261
    for b in payload:
        fnv = ((fnv ^ b) * 16777619) & 0xffffffff
    crc = zlib.crc32(payload)
    name = f'{crc:08x}-{fnv:08x}.re4tex'
    desc = struct.pack('<64s8I', b'synthetic test', 8, 8, 0, 144, len(payload), 0, 1, 0)
    head = struct.pack('<8s10I', b'RE4DCTX\0', 2, 48, 96, 1, 48, 144, len(payload),
                       zlib.crc32(desc + payload), 1, 0)
    (root / 'tex' / name).write_bytes(head + desc + payload)
    body = struct.pack('<IIHHBBBB', crc, fnv, 8, 8, 0, 0, 0, 0)
    body += struct.pack('<HH12f', 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0)
    crc = zlib.crc32(body)
    (root / 'ps2-world.r4pw').write_bytes(struct.pack('<4s7I', b'R4PW', 1, 1, 1, 1, crc, 0, 0) + body)
    (root / 'ps2-world.ids').write_bytes(struct.pack('<4s3I', b'R4ID', 1, 1, crc) + b'\x05' + b'\x00' * 15)
    corners = [(i, (255, 255, 255, 255), uv, (0, 1, 0))
               for i, uv in enumerate(((0, 0), (0, 1), (1, 0)))]
    part = dict(offset=0, size=0, flags=0, texture=0, alpha=255, strips=[], loose=[corners])
    source = dict(flags=0, nvtx=3, nparts=1, positions=[(0, 0, 0), (0, 0, 100), (100, 0, 0)],
                  parts=[part], uv=lambda x: x, normal=lambda x: x, color=lambda x: x)
    mesh, _ = convert_room_bins.convert_lod([(0x50, 0, 0, Path('synthetic.BIN'))], 1.0,
                                            eps_world=(), max_levels=1, share=True,
                                            source=lambda _: source, color_mode='prelit')
    (root / 'ps2-world.re4mesh').write_bytes(mesh)
    return name


def change_sidecar(root, offset, fmt, value):
    """Change a record while keeping the sidecar CRC and ID binding consistent."""
    path = root / 'ps2-world.r4pw'
    data = bytearray(path.read_bytes())
    struct.pack_into(fmt, data, offset, value)
    crc = zlib.crc32(data[32:])
    struct.pack_into('<I', data, 20, crc)
    path.write_bytes(data)
    path = root / 'ps2-world.ids'
    data = bytearray(path.read_bytes())
    struct.pack_into('<I', data, 12, crc)
    path.write_bytes(data)


def overlay(out):
    room = out / 'rooms/r102'
    room.mkdir(parents=True)
    fixture(room)
    for path in build.runtime_files(room):
        destination = out / 'stage' / ('tex' if path.suffix == '.re4tex' else 'rooms/r102') / path.name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination)


class BuildBoundaries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.checker_temp = tempfile.TemporaryDirectory(prefix='re4dc-assets-checker-test-')
        cls.addClassCleanup(cls.checker_temp.cleanup)
        with patch.object(build.world_registry, 'CACHE', Path(cls.checker_temp.name)):
            cls.checker = build.runtime_checker(Path(cls.checker_temp.name))

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_valid_bindings(self):
        fixture(self.root)
        result = build.validate_runtime(self.root, self.checker)
        self.assertEqual(result['textures'], 1)
        self.assertEqual(result['runtime_open'], 'accepted')

    def test_missing_bound_texture(self):
        name = fixture(self.root)
        (self.root / 'tex' / name).unlink()
        with self.assertRaisesRegex(ValueError, 'texture bindings'):
            build.validate_runtime(self.root, self.checker)

    def test_changed_mesh_crc(self):
        fixture(self.root)
        p = self.root / 'ps2-world.re4mesh'
        data = bytearray(p.read_bytes()); data[-1] ^= 1; p.write_bytes(data)
        with self.assertRaisesRegex(ValueError, 'R4IM CRC'):
            build.validate_runtime(self.root, self.checker)

    def test_invalid_mesh_structure_with_valid_crc(self):
        fixture(self.root)
        p = self.root / 'ps2-world.re4mesh'
        data = bytearray(p.read_bytes())
        struct.pack_into('<I', data, 40, len(data) + 4)  # MeshHeader::mesh_offset outside the file.
        struct.pack_into('<I', data, 12, zlib.crc32(data[80:]))
        p.write_bytes(data)
        with self.assertRaisesRegex(ValueError, 'runtime world open rejected: section'):
            build.validate_runtime(self.root, self.checker)

    def test_invalid_sidecar_mesh_reference(self):
        fixture(self.root)
        change_sidecar(self.root, 48, '<H', 1)  # Only mesh zero exists.
        with self.assertRaisesRegex(ValueError, 'runtime world open rejected: sidecar records'):
            build.validate_runtime(self.root, self.checker)

    def test_invalid_sidecar_part_dimensions(self):
        fixture(self.root)
        change_sidecar(self.root, 40, '<H', 0)
        with self.assertRaisesRegex(ValueError, 'runtime world open rejected: sidecar records'):
            build.validate_runtime(self.root, self.checker)

    def test_texture_dimensions_must_match_part(self):
        fixture(self.root)
        change_sidecar(self.root, 40, '<H', 16)  # Legal dimensions, but the bound texture is 8x8.
        with self.assertRaisesRegex(ValueError, 'runtime texture rejected: .*part samples 16x8'):
            build.validate_runtime(self.root, self.checker)

    def test_ids_from_another_sidecar(self):
        fixture(self.root)
        p = self.root / 'ps2-world.ids'
        data = bytearray(p.read_bytes()); data[12] ^= 1; p.write_bytes(data)
        with self.assertRaisesRegex(ValueError, 'R4ID'):
            build.validate_runtime(self.root, self.checker)

    def test_changed_texture_crc(self):
        name = fixture(self.root)
        p = self.root / 'tex' / name
        data = bytearray(p.read_bytes()); data[-1] ^= 1; p.write_bytes(data)
        with self.assertRaisesRegex(ValueError, 'RE4DCTX'):
            build.validate_runtime(self.root, self.checker)

    def completed_overlay(self):
        overlay(self.root)
        fingerprint = dict(rooms=['r102'])
        manifest = dict(fingerprint=fingerprint,
                        runtime_files=build.verify_overlay(self.root, ['r102'], self.checker))
        (self.root / 'manifest.json').write_text(json.dumps(manifest))
        return manifest

    def reuse(self, fingerprint):
        args = argparse.Namespace(out=self.root)
        sources = dict(ps2=dict(path='unused-ps2.iso'), gc=dict(path='unused-gc.iso'))
        with patch.object(build, 'fetch_tool', side_effect=AssertionError('reuse must not fetch tools')):
            build.build(args, {}, sources, fingerprint, self.checker)

    def test_unchanged_overlay_reused_without_writes(self):
        manifest = self.completed_overlay()
        before = {str(p.relative_to(self.root)): (build.record(p), p.stat().st_mtime_ns)
                  for p in self.root.rglob('*') if p.is_file()}
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.reuse(manifest['fingerprint'])
        self.assertIn('Verified existing build', output.getvalue())
        after = {str(p.relative_to(self.root)): (build.record(p), p.stat().st_mtime_ns)
                 for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(before, after)

    def test_staged_extra_room_rejected(self):
        manifest = self.completed_overlay()
        extra = self.root / 'stage/rooms/r106/ps2-world.r4pw'
        extra.parent.mkdir()
        extra.write_bytes(b'stale room')
        with self.assertRaisesRegex(ValueError, 'staged inventory differs'):
            self.reuse(manifest['fingerprint'])

    def test_incomplete_manifest_rejected(self):
        manifest = self.completed_overlay()
        del manifest['runtime_files']['stage/rooms/r102/ps2-world.r4pw']
        (self.root / 'manifest.json').write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, 'completed output inventory or bytes changed'):
            self.reuse(manifest['fingerprint'])

    def test_changed_stage_not_hidden_by_manifest_omission(self):
        manifest = self.completed_overlay()
        relative = 'stage/rooms/r102/ps2-world.r4pw'
        del manifest['runtime_files'][relative]
        (self.root / 'manifest.json').write_text(json.dumps(manifest))
        (self.root / relative).write_bytes(b'changed staged room')
        with self.assertRaisesRegex(ValueError, 'staged bytes differ from room output'):
            self.reuse(manifest['fingerprint'])

    def test_missing_host_tools(self):
        tool = self.root / 'tool'
        tool.write_bytes(b'synthetic executable')
        for missing in ('mono', 'powerpc-linux-gnu-gcc', 'qemu-ppc', 'g++'):
            with self.subTest(missing=missing), \
                 patch.object(build.shutil, 'which', side_effect=lambda name: None if name == missing else str(tool)), \
                 patch.object(build.subprocess, 'run') as run:
                run.return_value.stdout = 'synthetic version\n'
                with self.assertRaises(ValueError) as error:
                    build.host_tools()
                self.assertIn('missing ' + missing, str(error.exception))

    def test_yz2_dependencies_invalidate_fingerprint(self):
        scratch = self.root / 'repo/port/dreamcast/tools'
        for relative in build.source_hashes():
            destination = scratch / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(build.HERE / relative, destination)
        with patch.object(build, 'HERE', scratch), patch.object(build, 'PROFILE', scratch / 'ps2_assets/worlds.json'):
            original = build.source_hashes()
            for relative in ('decode_yz2.py', '../../../src/game/yz2asm.cpp', '../../../src/game/yz2code.cpp'):
                with self.subTest(source=relative):
                    path = scratch / relative
                    saved = path.read_bytes()
                    path.write_bytes(saved + b'\n// changed decoder input\n')
                    changed = build.source_hashes()
                    self.assertNotEqual(original, changed)
                    self.assertEqual({key for key in original if original[key] != changed[key]}, {relative})
                    path.write_bytes(saved)

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
