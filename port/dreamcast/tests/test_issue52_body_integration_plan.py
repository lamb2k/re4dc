"""Integration planning tests use in-memory synthetic packs; write no binaries."""
import importlib.util
import io
from pathlib import Path
import struct
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parents[1] / 'tools'
sys.path[:0] = [str(TOOLS / 'd367/issue52_visuals'), str(TOOLS / 'd367')]
import plan_officer_body_integration as p
import texpack


class MemoryPack:
    def __init__(self, data):
        self.data = data
    def open(self, mode):
        if mode != 'rb':
            raise AssertionError('plan tried binary mutation')
        return io.BytesIO(self.data)
    def stat(self):
        return SimpleNamespace(st_size=len(self.data))


class IntegrationPlanTests(unittest.TestCase):
    def test_virtual_hash_matches_independent_existing_canonical_builder(self):
        old = {(1, 2): b'RE4DCTX\0' + bytes(range(256)) * 9,
               (9, 3): b'RE4DCTX\0' + bytes(95)}
        added = {(4, 7): b'RE4DCTX\0' + bytes(range(255)) * 400,
                 (10, 8): b'RE4DCTX\0' + bytes(4001)}
        baseline, _ = texpack.build(old)
        reference, count = texpack.build(dict(old, **{}) | added)
        report = p.expected_pack(MemoryPack(baseline), added)
        self.assertEqual(report['expected_sha256'], p.sha(reference))
        self.assertEqual(report['independent_virtual_reader_sha256'], p.sha(reference))
        self.assertEqual(report['expected_bytes'], len(reference))
        self.assertEqual(report['expected_count'], count)
        self.assertEqual(report['preserved_member_count'], 2)
    def test_collision_and_corrupt_index_refused(self):
        baseline, _ = texpack.build({(1, 2): b'RE4DCTX\0' + bytes(32)})
        with self.assertRaisesRegex(ValueError, 'collides'):
            p.expected_pack(MemoryPack(baseline), {(1, 2): b'RE4DCTX\0'})
        bad = bytearray(baseline)
        bad[2048] ^= 1
        with self.assertRaisesRegex(ValueError, 'CRC'):
            p.expected_pack(MemoryPack(bytes(bad)), {})
    def test_metadata_only_and_frozen_bundle_output_guard(self):
        with self.assertRaisesRegex(ValueError, 'JSON'):
            p.output_guard(Path('hypothetical-output.pak'), Path('frozen-bundle'))
        with self.assertRaisesRegex(ValueError, 'preserve'):
            p.output_guard(Path('frozen-bundle/new.json'), Path('frozen-bundle'))
    def test_default_cli_does_not_read_sources(self):
        argv = ['plan', '--dar', 'missing', '--pack', 'missing', '--bundle', 'missing',
                '--source-plan', 'missing', '--flags', 'missing', '--binding', 'missing',
                '--report', 'missing-new-report']
        with patch.object(sys, 'argv', argv), patch.object(p, 'plan', side_effect=AssertionError('unexpected read')):
            with self.assertRaisesRegex(ValueError, 'disabled'):
                p.main()


if __name__ == '__main__':
    unittest.main()
