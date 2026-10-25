"""Private-pack-free converter tests.

Set TEXSRC22_TEST_QUALITY_GATE to the reviewed mipfix22 mip_quality.py to run
the real final-level gate cases. The parked texsrc22 branch does not contain
that integration dependency. Fixtures are generated in memory, never game data.
"""
import importlib.util
import json
import os
import py_compile
import sys
from pathlib import Path
import struct
import tempfile
import unittest
import zlib

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('texsrc22_convert', HERE / 'convert.py')
convert = importlib.util.module_from_spec(spec)
spec.loader.exec_module(convert)
tpl = convert.tpl
GATE = Path(os.environ.get('TEXSRC22_TEST_QUALITY_GATE', str(HERE.parent / 'mipmap21/mip_quality.py')))


def package(kind='vq', side=32, height=None, cutout=False, bad_colour=False, legacy=False):
    height = height or side
    fmt = 1 if cutout else 0
    flags = 3 if cutout else 0
    if kind == 'vq':
        if cutout:
            vector = (0xffff, 0, 0, 0)
        elif bad_colour:
            vector = (0xffff, 0, 0xffff, 0)
        else:
            vector = (0xffff,) * 4
        payload = struct.pack('<4H', *vector) + bytes(2040) + bytes(side * height // 4)
        layout = 2
    elif kind == 'twiddled':
        payload = struct.pack('<%dH' % (side * height), *([0xffff] * (side * height)))
        layout = 1
    elif kind == 'pal4':
        payload = bytes(side * height // 2) + struct.pack('<16H', *([0xffff] + [0] * 15))
        fmt, flags, layout = 4, 1, 1
    else:
        raise ValueError(kind)
    body = tpl.TEXTURE.pack(b'public synthetic fixture', side, height, fmt, 144,
                            len(payload), flags, layout, 0) + payload
    crc = zlib.crc32(payload if legacy else body) & 0xffffffff
    return tpl.HEADER.pack(tpl.MAGIC, 2, 48, 96, 1, 48, 144, len(payload), crc, 7, 29) + body


def source_pack(*blobs):
    return convert.texpack.build({(i, i + 100): b for i, b in enumerate(blobs, 1)})[0]


def name(i):
    return '%08x-%08x' % (i, i + 100)


def selection(source, names, hold=b'# explicit empty policy for synthetic tests\n'):
    return dict(schema=convert.SCHEMA, base_pack_sha256=convert.digest(source),
                quality_gate_sha256=convert.digest(GATE.read_bytes()),
                hold_keys_sha256=convert.digest(hold), approved_keys=names)


class ConverterInputContract(unittest.TestCase):
    def test_off_preserves_whole_archive_without_profile_or_external_gate(self):
        source = bytearray(source_pack(package(legacy=True), package('twiddled')))
        source[-1] = 0xab  # legal archive padding must also remain exact OFF
        result, report = convert.build_candidate(bytes(source))
        self.assertEqual(result, bytes(source))
        self.assertEqual(report['changed'], 0)
        self.assertEqual(report['unselected_exact'], 2)

    def test_enabled_requires_gate_and_hold_manifest(self):
        with self.assertRaisesRegex(ValueError, 'explicit gate'):
            convert.build_candidate(source_pack(package()), enabled=True)

    def test_manifest_binds_all_three_inputs_and_rejects_duplicate_keys(self):
        source, gate, hold = b'pack', b'gate', b'hold'
        manifest = dict(schema=convert.SCHEMA, approved_keys=[name(1)],
                        base_pack_sha256=convert.digest(source),
                        quality_gate_sha256=convert.digest(gate), hold_keys_sha256=convert.digest(hold))
        self.assertEqual(convert.validate_selection(manifest, source, gate, hold), [name(1)])
        for field in ('base_pack_sha256', 'quality_gate_sha256', 'hold_keys_sha256'):
            with self.subTest(field=field):
                changed = dict(manifest, **{field: '0' * 64})
                with self.assertRaisesRegex(ValueError, 'identity mismatch'):
                    convert.validate_selection(changed, source, gate, hold)
        for invalid in ({}, dict(manifest, approved_keys=[]),
                        dict(manifest, approved_keys=[name(1), name(1)]),
                        dict(manifest, approved_keys=['not-a-key'])):
            with self.assertRaises(ValueError):
                convert.validate_selection(invalid, source, gate, hold)

    def test_room_policy_rejects_bad_key_syntax(self):
        with self.assertRaises(ValueError):
            convert.hold_keys(b'key\troom\nwrong\tr101\n')

    def test_cli_refuses_in_place_output_before_writing(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'source.pak'
            source = source_pack(package())
            path.write_bytes(source)
            with self.assertRaises(SystemExit):
                convert.main(['--pack', str(path), '--out', str(path), '--report', str(Path(td) / 'report.json')])
            self.assertEqual(path.read_bytes(), source)


    def test_pinned_gate_executes_source_even_with_unchecked_cached_bytecode(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'gate.py'
            raw = b"def audit(item): return item[0], {'source': True}, None\n"
            poison = "def audit(item): return item[0], {'source': False}, None\n"
            path.write_text(poison)
            cached = Path(py_compile.compile(str(path), doraise=True,
                invalidation_mode=py_compile.PycInvalidationMode.UNCHECKED_HASH))
            path.write_bytes(raw)
            cached_before = cached.read_bytes()
            gate = convert.load_gate(path, convert.digest(raw))
            self.assertTrue(gate.audit(((1, 2), b''))[1]['source'])
            self.assertEqual(cached.read_bytes(), cached_before)
            path.write_bytes(raw + b'# changed source\n')
            with self.assertRaisesRegex(ValueError, 'identity changed'):
                convert.load_gate(path, convert.digest(raw))
            self.assertEqual(cached.read_bytes(), cached_before)

    def test_bad_pack_identity_and_index_extent_refuse_even_off(self):
        source = source_pack(package())
        bad_magic = b'WRONGPAK' + source[8:]
        bad_index = bytearray(source)
        struct.pack_into('<I', bad_index, 16, 123)
        for blob in (b'', bad_magic, bytes(bad_index), source[:4096]):
            with self.subTest(length=len(blob)):
                with self.assertRaises(SystemExit):
                    convert.build_candidate(blob)

    def test_cli_enable_without_selection_never_creates_outputs(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with self.assertRaises(SystemExit):
                convert.main(['--pack', str(root / 'missing.pak'), '--enable',
                              '--out', str(root / 'out.pak'), '--report', str(root / 'report.json')])
            self.assertEqual(list(root.iterdir()), [])

    def test_cli_off_exact_output_and_no_clobber(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = source_pack(package(legacy=True))
            (root / 'in.pak').write_bytes(source)
            argv = ['--pack', str(root / 'in.pak'), '--out', str(root / 'out.pak'),
                    '--report', str(root / 'report.json')]
            convert.main(argv)
            self.assertEqual((root / 'out.pak').read_bytes(), source)
            report = json.loads((root / 'report.json').read_text())
            self.assertFalse(report['enabled'])
            self.assertEqual(report['source_pack_sha256'], report['output_pack_sha256'])
            before = (root / 'report.json').read_bytes()
            with self.assertRaises(SystemExit):
                convert.main(argv)
            self.assertEqual((root / 'report.json').read_bytes(), before)
            self.assertEqual((root / 'in.pak').read_bytes(), source)

    def test_gate_missing_final_level_refuses_complete_candidate(self):
        with tempfile.TemporaryDirectory() as td:
            gate = Path(td) / 'gate.py'
            gate.write_text("def audit(item): return item[0], {'verdict': 'pass', 'levels': "
                            "[{'side': n} for n in (16, 8, 4, 2)]}, None\n")
            source = source_pack(package())
            hold = b'# none\n'
            manifest = dict(schema=convert.SCHEMA, approved_keys=[name(1)],
                base_pack_sha256=convert.digest(source),
                quality_gate_sha256=convert.digest(gate.read_bytes()),
                hold_keys_sha256=convert.digest(hold))
            with self.assertRaisesRegex(ValueError, 'every level through 1x1'):
                convert.build_candidate(source, enabled=True, selection=manifest,
                    gate_path=gate, hold_bytes=hold, engine='python')


@unittest.skipUnless(GATE.is_file(), 'set TEXSRC22_TEST_QUALITY_GATE to the reviewed mipfix22 gate')
class ConverterRealGate(unittest.TestCase):
    def run_candidate(self, source, names, hold=b'# explicit empty policy for synthetic tests\n'):
        return convert.build_candidate(source, enabled=True, selection=selection(source, names, hold),
                                       gate_path=GATE, hold_bytes=hold, engine='python')

    def test_supported_formats_preserve_base_and_unselected_packages(self):
        for kind in ('vq', 'twiddled', 'pal4'):
            with self.subTest(kind=kind):
                original = package(kind, legacy=True)
                unselected = package('vq', bad_colour=True, legacy=True)
                source = source_pack(original, unselected)
                output, report = self.run_candidate(source, [name(1)])
                result = convert.read_pak(output)
                self.assertNotEqual(result[(1, 101)], original)
                self.assertEqual(result[(2, 102)], unselected)
                self.assertEqual(report['changed_keys'], [name(1)])
                self.assertEqual(report['unselected_exact'], 1)
                before = convert.identify(original)
                after = convert.identify(result[(1, 101)])
                self.assertEqual(before[4](before[1]), after[4](after[1]))
                self.assertEqual(before[2](before[1], 32), after[2](after[1], 32))
                self.assertEqual(tpl.HEADER.unpack_from(result[(1, 101)])[8],
                                 zlib.crc32(result[(1, 101)][48:]) & 0xffffffff)
                self.assertEqual(report['rows'][0]['quality']['verdict'], 'pass')
                self.assertEqual(report['rows'][0]['quality']['levels'][-1]['side'], 1)
                self.assertEqual(report['quality_gate_dependencies_sha256']['compact_native_pal8'],
                                 convert.digest(Path(__import__('compact_native_pal8').__file__).read_bytes()))
                self.assertIn('vram.vq_pak', report['quality_gate_dependencies_sha256'])

    def test_colour_and_coverage_failures_keep_exact_original_bytes(self):
        for kwargs, reason in ((dict(bad_colour=True), 'vq-colour'), (dict(cutout=True), 'coverage')):
            with self.subTest(reason=reason):
                source = source_pack(package(legacy=True, **kwargs))
                output, report = self.run_candidate(source, [name(1)])
                self.assertEqual(output, source)
                self.assertIn(reason, report['rows'][0]['reasons'])
                self.assertEqual(report['rows'][0]['verdict'], 'held')
                self.assertEqual(report['extra_alloc32_bytes'], 0)

    def test_room_selected_key_stays_exact_and_other_key_converts(self):
        source = source_pack(package(legacy=True), package('twiddled'))
        hold = ('key\trooms\treason\n%s\tr101\tsmall-chain\n' % name(1)).encode()
        output, report = self.run_candidate(source, [name(1), name(2)], hold)
        before, after = convert.read_pak(source), convert.read_pak(output)
        self.assertEqual(before[(1, 101)], after[(1, 101)])
        self.assertNotEqual(before[(2, 102)], after[(2, 102)])
        self.assertEqual(report['rows'][0]['reasons'], ['room-select'])

    def test_already_mipped_member_stays_byte_identical(self):
        mip, _ = convert.vq.add_mipmaps(package(), enabled=True, engine='python')
        source = source_pack(mip)
        output, report = self.run_candidate(source, [name(1)])
        self.assertEqual(output, source)
        self.assertEqual(report['rows'][0]['reasons'], ['already-mipped'])

    def test_missing_rectangle_and_multiple_images_fail_before_candidate(self):
        source = source_pack(package())
        with self.assertRaisesRegex(ValueError, 'absent'):
            self.run_candidate(source, [name(2)])
        rectangle = package(side=32, height=64)
        with self.assertRaisesRegex(ValueError, 'unsupported'):
            self.run_candidate(source_pack(package(), rectangle), [name(1), name(2)])
        multiple = bytearray(package())
        struct.pack_into('<I', multiple, 20, 2)  # number of textures
        with self.assertRaisesRegex(ValueError, 'exactly one'):
            self.run_candidate(source_pack(bytes(multiple)), [name(1)])

    def test_cli_dry_run_writes_report_without_pack(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = source_pack(package())
            hold = b'# no holds in this synthetic test\n'
            (root / 'source.pak').write_bytes(source)
            (root / 'holds.tsv').write_bytes(hold)
            (root / 'selection.json').write_text(json.dumps(selection(source, [name(1)], hold)))
            out, report = root / 'out.pak', root / 'report.json'
            convert.main(['--pack', str(root / 'source.pak'), '--selection', str(root / 'selection.json'),
                          '--quality-gate', str(GATE), '--hold-keys', str(root / 'holds.tsv'),
                          '--enable', '--dry-run', '--out', str(out), '--report', str(report), '--engine', 'python'])
            self.assertFalse(out.exists())
            result = json.loads(report.read_text())
            self.assertEqual(result['changed'], 1)
            self.assertTrue(result['dry_run'])


if __name__ == '__main__':
    unittest.main()
