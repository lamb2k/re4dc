#!/usr/bin/env python3
"""Synthetic metadata preservation, malformed input and default-off gates."""
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

import scps_only as S


def mesh(parts=5, version=3):
    head = 80 if version == 1 else 112
    out = bytearray(head + parts * 36)
    struct.pack_into('<4s19I', out, 0, b'R4IM', version, len(out), 0,
                     0, parts, 0, 0, 0, 0, head, head, head, head, head, head, 2, 0, 0, 0)
    struct.pack_into('<I', out, 12, S.crc(out[80:]))
    return bytes(out)


def room(count=2):
    out = bytearray(64 + count * 32)
    struct.pack_into('<4sHHIII', out, 0, b'R4RC', 1, 64, 0x103, count, 0)
    for i in range(count):
        body = bytes([i + 1]) * (13 + i)
        tag = f'T{i:03}'.encode()
        out.extend(bytes(-len(out) % 16))
        struct.pack_into('<4sHH6I', out, 64 + i * 32, tag, 3, i & 1,
                         len(out), len(body), 7 + i, 9 + i, 16, 0x1200 + i)
        out.extend(body)
    out.extend(bytes(-len(out) % 16))
    struct.pack_into('<I', out, 16, len(out))
    struct.pack_into('<I', out, 48, S.crc(out[64:]))
    return bytes(out)


def patch(data, offset, value, fmt='<I', fix_crc=True):
    out = bytearray(data)
    struct.pack_into(fmt, out, offset, value)
    if fix_crc:
        struct.pack_into('<I', out, 48, S.crc(out[64:]))
    return bytes(out)


class ScpsOnly(unittest.TestCase):
    def test_all_mesh_versions_and_counts(self):
        for version in (1, 2, 3):
            for n in (0, 1, 5, 257):
                with self.subTest(version=version, parts=n):
                    source = mesh(n, version)
                    original = room()
                    out, report = S.convert(source, original)
                    self.assertEqual(report['mesh']['sha256'], S.sha(source))
                    self.assertEqual(report['mesh']['parts'], n)
                    self.assertEqual(report['runtime_scps_block_contribution'], (16 + 4*n + 31) & ~31)
                    _, rows = S.read_room(out)
                    hdr = struct.unpack_from('<4I', rows[-1][1])
                    self.assertEqual(hdr, (S.crc(source[80:]), len(source), n, 0))
                    self.assertFalse(any(rows[-1][1][16:]))
                    self.assertEqual(source, mesh(n, version))

    def test_deterministic_replace_preserves_other_metadata(self):
        old = room()
        once, _ = S.convert(mesh(), old)
        twice, report = S.convert(mesh(), once)
        self.assertEqual(once, twice)
        self.assertTrue(report['replaced'])
        before = S.read_room(old)[1]
        after = S.read_room(twice)[1][:-1]
        for (a, ad), (b, bd) in zip(before, after):
            self.assertEqual(a[:3] + a[4:], b[:3] + b[4:])
            self.assertEqual(ad, bd)

    def test_room_rejections(self):
        valid = room()
        samples = [valid[:63], valid[:-1], patch(valid, 4, 2, '<H'),
                   patch(valid, 8, 0x1000), patch(valid, 12, 9),
                   patch(valid, 48, 0, fix_crc=False),
                   patch(valid, 72, 65), patch(valid, 76, 0xffffffff),
                   patch(valid, 88, 32), patch(valid, 104, 128)]
        duplicate = bytearray(valid)
        duplicate[96:100] = duplicate[64:68]
        struct.pack_into('<I', duplicate, 48, S.crc(duplicate[64:]))
        samples.append(bytes(duplicate))
        for n, bad in enumerate(samples):
            with self.subTest(case=n), self.assertRaises(ValueError):
                S.convert(mesh(), bad)
        with self.assertRaisesRegex(ValueError, 'MAXSEC'):
            S.convert(mesh(), room(8))

    def test_mesh_rejections(self):
        good = mesh()
        cases = [good[:79], good[:-1]]
        for offset, value in ((4, 4), (8, 1), (12, 0), (20, 0xffffffff), (44, 113)):
            bad = bytearray(good)
            struct.pack_into('<I', bad, offset, value)
            cases.append(bytes(bad))
        for n, bad in enumerate(cases):
            with self.subTest(case=n), self.assertRaises(ValueError):
                S.convert(bad, room())

    def test_cli_default_no_io_and_no_overwrite(self):
        script = Path(S.__file__)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            args = [sys.executable, str(script), '--mesh', str(root/'missing'),
                    '--room-file', str(root/'absent'), '--out', str(root/'out'), '--report', str(root/'report')]
            self.assertEqual(subprocess.run(args, capture_output=True).returncode, 0)
            self.assertFalse(list(root.iterdir()))
            (root/'mesh').write_bytes(mesh())
            (root/'room').write_bytes(room())
            args = [sys.executable, str(script), '--scps-only34=1', '--mesh', str(root/'mesh'),
                    '--room-file', str(root/'room'), '--out', str(root/'out'), '--report', str(root/'report')]
            self.assertEqual(subprocess.run(args, capture_output=True).returncode, 0)
            before = (root/'out').read_bytes()
            self.assertEqual(json.loads((root/'report').read_text())['status'], 'PASS')
            self.assertEqual(subprocess.run(args, capture_output=True).returncode, 2)
            self.assertEqual((root/'out').read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
