#!/usr/bin/env python3
"""Public structural gates for opt-in exact index placement; no private assets."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import struct
import tempfile
import unittest

import fixtures
import index_layout_fixtures as f
import package as p
import sidecars
from test_identity import patch


def decode(files, **kwargs):
    return p.decode(files[f.MESH], files[f.POLICY], **kwargs)


def check(files, **kwargs):
    doc = decode(files, **kwargs)
    return sidecars.rebuild(files, doc, p.serialize_mesh(doc), p.serialize_policy(doc))


def changed_mesh(files, table):
    result = dict(files)
    result[f.MESH] = f.append.serialize(table)
    return result


class IndexLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.appended = f.append_files()
        cls.canonical = fixtures.complete_files()

    def test_real_append_reproduces_original_refusal_and_roundtrips(self):
        self.assertEqual(len(f.append.parse(p.serialize_mesh(fixtures.document()))['index']), 66)
        table = f.append.parse(self.appended[f.MESH])
        self.assertEqual(table['meshlet'][6][1], 68)
        self.assertEqual(table['index'][66:68], bytes(2))
        errors = []
        for options in ({}, {'preserve_index_layout': False}, {'preserve_index_layout': 0}):
            with self.assertRaisesRegex(ValueError, 'noncanonical index placement') as error:
                decode(self.appended, **options)
            errors.append(str(error.exception))
        self.assertEqual(len(set(errors)), 1)
        self.assertEqual(check(self.appended, preserve_index_layout=True), self.appended)

    def test_canonical_absent_zero_and_one_complete_bundle_identity(self):
        before = sidecars.hashes(self.canonical)
        absent = decode(self.canonical)
        zero = decode(self.canonical, preserve_index_layout=0)
        self.assertEqual(absent, zero)
        self.assertNotIn('index_layout', absent)
        one = decode(self.canonical, preserve_index_layout=1)
        self.assertEqual(one.pop('index_layout'),
                         {'index_bytes': p.crb.HEADER.unpack_from(self.canonical[f.MESH])[8]})
        self.assertEqual(one['schema'], 're4dc.blender.identity-index-layout/1')
        one['schema'] = absent['schema']
        self.assertEqual(one, absent)
        for options in ({}, {'preserve_index_layout': 0}, {'preserve_index_layout': 1}):
            self.assertEqual(check(self.canonical, **options), self.canonical)
        self.assertEqual(sidecars.hashes(self.canonical), before)

    def test_four_byte_append_residues_plain_and_indexed(self):
        for residue in range(4):
            for indexed in (False, True):
                with self.subTest(residue=residue, appended_indexed=indexed):
                    files = f.append_files(residue, indexed)
                    source = p.serialize_mesh(f.document(residue))
                    size = p.crb.HEADER.unpack_from(source)[8]
                    self.assertEqual(size % 4, residue)
                    table = f.append.parse(files[f.MESH])
                    first = table['meshlet'][6]
                    self.assertEqual(first[1], (size + 3) // 4 * 4)
                    self.assertEqual(bool(first[4] & 0x8000), indexed)
                    self.assertEqual(table['index'][size:first[1]], bytes(-size % 4))
                    self.assertEqual(check(files, preserve_index_layout=1), files)

    def test_actual_append_then_strip_group_chain(self):
        files = f.strip_group_files()
        self.assertEqual(len(f.append.parse(files[f.MESH])['meshlet']), 18)
        self.assertEqual(check(files, preserve_index_layout=1), files)
        self.assertIn((66, 68), f.gaps(files[f.MESH]))
        self.assertIn((134, 136), f.gaps(files[f.MESH]))

    def test_reordered_disjoint_spans_preserve_commands_and_geometry(self):
        files = f.reordered_files()
        doc = decode(files, preserve_index_layout=1)
        original = f.document()
        original['commands'][2]['strips'][0] = [4, 3, 2, 2, 1, 0]
        self.assertEqual(doc['commands'], original['commands'])
        self.assertEqual(doc['vertices'], original['vertices'])
        for ji in range(len(doc['meshlets'])):
            self.assertEqual(p.triangles(doc, ji), p.triangles(original, ji))
        self.assertGreater(doc['meshlets'][0][1], doc['meshlets'][2][1])
        self.assertEqual(check(files, preserve_index_layout=1), files)
        with self.assertRaisesRegex(ValueError, 'noncanonical index placement'):
            decode(files)

    def test_zero_leading_and_trailing_gaps_retain_declared_extent(self):
        files = f.zero_gap_files()
        doc = decode(files, preserve_index_layout=1)
        self.assertEqual(doc['index_layout'], {'index_bytes': 77})
        self.assertEqual(f.gaps(files[f.MESH])[0], (0, 4))
        self.assertEqual(f.gaps(files[f.MESH])[-1], (70, 77))
        self.assertEqual(check(files, preserve_index_layout=1), files)

    def test_every_gap_byte_rejects_nonzero_payload_even_with_valid_crc(self):
        for label, files in [('append', self.appended), ('outer', f.zero_gap_files())]:
            h = p.crb.HEADER.unpack_from(files[f.MESH])
            for lo, hi in f.gaps(files[f.MESH]):
                for offset in range(lo, hi):
                    with self.subTest(fixture=label, offset=offset), self.assertRaises(ValueError):
                        decode(patch(files, f.MESH, h[14]+offset, '<B', 0x5a, 'mesh'),
                               preserve_index_layout=1)

    def test_exact_aliases_rejected_even_when_the_commands_agree(self):
        table = f.append.parse(self.canonical[f.MESH])
        self.assertEqual(table['meshlet'][0][2:], table['meshlet'][2][2:])
        table['meshlet'][2][1] = table['meshlet'][0][1]
        with self.assertRaisesRegex(ValueError, 'overlap'):
            decode(changed_mesh(self.canonical, table), preserve_index_layout=1)

    def test_partial_overlap_with_valid_inner_strip_rejected(self):
        table = f.append.parse(self.canonical[f.MESH])
        # The last four bytes of meshlet0 are a complete [3,1,4,2] strip.
        table['meshlet'][2][1:3] = [7, 4]
        table['meshlet'][2][4] = 1
        with self.assertRaisesRegex(ValueError, 'overlap'):
            decode(changed_mesh(self.canonical, table), preserve_index_layout=1)

    def test_serializer_rejects_conflicting_alias_commands(self):
        doc = decode(self.canonical, preserve_index_layout=1)
        doc['meshlets'][2][1] = doc['meshlets'][0][1]
        doc['commands'][2]['strips'][0] = [4, 3, 2, 2, 1, 0]
        with self.assertRaisesRegex(ValueError, 'overlap'):
            p.serialize_mesh(doc)

    def test_out_of_bounds_span_and_huge_offset_rejected(self):
        for start in (132, 0xffffffff):
            with self.subTest(start=start):
                table = f.append.parse(self.appended[f.MESH])
                table['meshlet'][0][1] = start
                with self.assertRaisesRegex(ValueError, 'extent|bounds|range'):
                    decode(changed_mesh(self.appended, table), preserve_index_layout=1)

    def test_indexed_pool_start_requires_u16_alignment(self):
        table = f.append.parse(self.appended[f.MESH])
        table['meshlet'][1][1] += 1
        with self.assertRaisesRegex(ValueError, 'alignment'):
            decode(changed_mesh(self.appended, table), preserve_index_layout=1)

    def test_bad_pool_reference_and_strip_fields_still_rejected(self):
        h = p.crb.HEADER.unpack_from(self.appended[f.MESH])
        table = f.append.parse(self.appended[f.MESH])
        indexed = table['meshlet'][1]
        for name, offset, fmt, value in [
                ('pool reference', h[14]+indexed[1], '<H', 65535),
                ('short strip', h[14], '<B', 2),
                ('local index', h[14]+1, '<B', 255),
                ('strip count', h[12]+14, '<H', 3)]:
            with self.subTest(name=name), self.assertRaises(ValueError):
                decode(patch(self.appended, f.MESH, offset, fmt, value, 'mesh'),
                       preserve_index_layout=1)

    def test_extra_outer_bytes_and_nonzero_section_padding_still_rejected(self):
        files = dict(self.appended)
        mesh = bytearray(files[f.MESH]) + bytes(32)
        struct.pack_into('<I', mesh, 8, len(mesh))
        struct.pack_into('<I', mesh, 12, p.crc(mesh[80:]))
        files[f.MESH] = bytes(mesh)
        with self.assertRaisesRegex(ValueError, 'layout|padding|trailing'):
            decode(files, preserve_index_layout=1)
        with self.assertRaisesRegex(ValueError, 'layout|padding|trailing'):
            decode(patch(self.appended, f.MESH, 112, '<B', 1, 'mesh'), preserve_index_layout=1)

    def test_extensions_and_bad_crc_remain_fail_closed(self):
        for offset, value, repair in [(4, 4, 'mesh'), (64, 1, 'mesh'),
                (68, 128, 'mesh'), (76, 0x334f4453, 'mesh'), (108, 128, 'mesh'),
                (12, 0, None)]:
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                decode(patch(self.appended, f.MESH, offset, '<I', value, repair),
                       preserve_index_layout=1)

    def test_truncated_tables_rejected(self):
        files = self.appended
        for cut in (0, 79, 111, len(files[f.MESH])-1):
            with self.subTest(cut=cut), self.assertRaises(ValueError):
                altered = dict(files)
                altered[f.MESH] = files[f.MESH][:cut]
                decode(altered, preserve_index_layout=1)

    def test_reserialization_uses_typed_records_not_a_saved_index_blob(self):
        files = self.appended
        doc = decode(files, preserve_index_layout=1)
        self.assertEqual(set(doc['index_layout']), {'index_bytes'})
        a = deepcopy(doc)
        a['commands'][0]['strips'][0][1] = 4
        mesh = p.serialize_mesh(a)
        self.assertNotEqual(mesh, files[f.MESH])
        self.assertEqual(decode({f.MESH: mesh, f.POLICY: files[f.POLICY]},
                                preserve_index_layout=1)['commands'][0], a['commands'][0])
        with self.assertRaisesRegex(ValueError, 'unchanged geometry'):
            sidecars.rebuild(files, a, mesh, p.serialize_policy(a))
        b = deepcopy(doc)
        b['vertices'][0][0] += 1
        self.assertNotEqual(p.serialize_mesh(b), files[f.MESH])

    def test_repeated_roundtrip_has_identical_layout_metadata_and_source_bytes(self):
        for name, make in f.suites():
            with self.subTest(fixture=name):
                files = make()
                original = deepcopy(files)
                first = decode(files, preserve_index_layout=1)
                for _ in range(3):
                    files = check(files, preserve_index_layout=1)
                    self.assertEqual(decode(files, preserve_index_layout=1), first)
                self.assertEqual(files, original)

    def test_stale_existing_companions_remain_rejected(self):
        for name, offset in [('ps2-world.ids', 12), ('ps2-world.r4tc', 16),
                ('ps2-world.r4sg', 16), ('ps2-world.r4sg', 20), ('ps2-world.r4sg', 24),
                ('ps2-world.pvs', 8), ('interior.cell', 8), ('ps2-world.occl', 8)]:
            with self.subTest(name=name, offset=offset), self.assertRaises(ValueError):
                check(patch(self.appended, name, offset, '<I', 0), preserve_index_layout=1)

    def test_stale_builder_report_remains_rejected(self):
        files = dict(self.appended)
        report = json.loads(files['ps2-world.json'])
        report['re4mesh_sha256'] = '0'*64
        files['ps2-world.json'] = json.dumps(report, indent=1).encode()
        with self.assertRaisesRegex(ValueError, 'stale builder report'):
            check(files, preserve_index_layout=1)

    def test_unknown_member_and_symlink_still_rejected(self):
        with tempfile.TemporaryDirectory(prefix='b11-index-inventory-') as td:
            folder = Path(td)/'bundle'
            fixtures.write(folder, self.appended)
            for name in ('unreviewed-proof.bin', 'ps2-world.re4mesh.dd3'):
                entry = folder/name
                entry.write_bytes(b'not an adapter')
                with self.subTest(name=name), self.assertRaises(ValueError):
                    sidecars.inventory(folder)
                entry.unlink()
            (folder/'alias').symlink_to(folder/f.MESH)
            with self.assertRaises(ValueError):
                sidecars.inventory(folder)


class CountedResult(unittest.TextTestResult):
    """Count actual unittest methods and subcases rather than a constant claim."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.subcases = 0

    def addSubTest(self, test, subtest, err):
        self.subcases += 1
        super().addSubTest(test, subtest, err)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(IndexLayoutTests)
    result = unittest.TextTestRunner(verbosity=2, resultclass=CountedResult).run(suite)
    report = dict(status='PASS_PUBLIC_HOST_ONLY' if result.wasSuccessful() else 'FAIL',
        test_methods=result.testsRun, subcases=result.subcases,
        failures=len(result.failures), errors=len(result.errors),
        private_r101_admission=False, runtime_timing_claim=False)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2, sort_keys=True)+'\n')
    print(json.dumps(report, sort_keys=True))
    raise SystemExit(0 if result.wasSuccessful() else 1)


if __name__ == '__main__':
    main()
