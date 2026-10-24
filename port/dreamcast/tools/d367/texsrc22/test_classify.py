#!/usr/bin/env python3
"""Host regressions for provenance versus selected-consumer decisions."""
import importlib.util
import csv
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('texsrc22_classify', HERE / 'classify.py')
C = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(C)
KEY = 'dc363980-b5147ee2'
OTHER = '279052e0-b695f91f'
SCOPED = '12345678-90abcdef'


def image(name='source', width=128, height=128, fmt='RGB565', layout='vq', mip=False):
    return dict(name=name, w=width, h=height, fmt=fmt, layout=layout, mip=mip)


def world(materials, placement_key=None):
    body = b''.join(struct.pack('<IIHH4B', *(int(w, 16) for w in key.split('-')), 128, 128, 0, 0, 1, 0)
                    for key in materials)
    if placement_key:
        body += struct.pack('<II', *(int(w, 16) for w in placement_key.split('-'))) + bytes(44)
    return struct.pack('<4s7I', b'R4PW', 1, bool(placement_key), len(materials), 1,
                       zlib.crc32(body), 0, 0) + body


class Classification(unittest.TestCase):
    def test_route_requires_an_exact_room_identity(self):
        for room in ('r100', 'r120', 'r200', 'r22f'):
            self.assertTrue(C.route_room(room))
        for room in ('x100', 'r100junk', 'r121', 'r230', 'archive:em/em10.drs', 'global', ''):
            self.assertFalse(C.route_room(room))

    def test_world_materials_ignore_incidental_placement_words(self):
        self.assertEqual(C.world_material_keys(world([KEY], OTHER)), {KEY})

    def test_invalid_world_does_not_silently_become_missing_binding(self):
        for blob in (b'R4PW', world([KEY])[:-1], world([KEY]) + b'\0',
                     world([KEY])[:32] + bytes(16)):
            with self.assertRaises(ValueError):
                C.world_material_keys(blob)

    def test_native_scoped_binding_and_unknown_format_hint_stay_distinct(self):
        with tempfile.TemporaryDirectory() as tmp:
            room = Path(tmp) / 'r101'
            room.mkdir()
            (room / 'ps2-world.r4pw').write_bytes(world([SCOPED], OTHER))
            (room / 'unknown.bin').write_bytes(struct.pack('<II', *(int(w, 16) for w in OTHER.split('-'))))
            bindings, hints = C.native_refs(tmp, {KEY: KEY, OTHER: OTHER, SCOPED: KEY})
        self.assertEqual(bindings, {KEY: {'r101/ps2-world.r4pw'}})
        self.assertEqual(hints, {OTHER: {'r101/unknown.bin'}})

    def test_ambiguous_scoped_origin_is_rejected(self):
        origins = '{0x12345678U,0x90abcdefU,0xdc363980U,0xb5147ee2U},\n'
        origins += '{0x12345678U,0x90abcdefU,0x279052e0U,0xb695f91fU},\n'
        with self.assertRaisesRegex(ValueError, 'ambiguous scoped origin'):
            C.source_aliases({KEY, OTHER}, origins)

    def test_shared_enemy_archive_alone_does_not_prove_live_or_dead(self):
        row = C.classify_key(KEY, [image()], [{'file': 'em/em10.drs', 'context': '#542'},
                                               {'file': 'em/em4c.drs', 'context': '#542'}])
        self.assertEqual(row['decision'], 'consumer-unresolved')
        self.assertEqual(row['consumer_status'], 'consumer-unresolved')

    def test_shared_enemy_resident_consumer_is_preserved(self):
        row = C.classify_key(KEY, [image()], [{'file': 'em/em10.drs', 'context': '#542'}],
                             resident_refs=['r201'])
        self.assertEqual(row['decision'], 'mip-chain')
        self.assertEqual(row['consumer_status'], 'bound-on-route')
        self.assertEqual(row['minification'], 'unmeasured')

    def test_unknown_role_with_positive_resident_evidence_is_never_unreachable(self):
        for key, room, height in ((KEY, 'r100', 128), (OTHER, 'r207', 256)):
            row = C.classify_key(key, [image(height=height)], resident_refs=[room], old_decision='not-worth')
            self.assertEqual(row['decision'], 'consumer-unresolved')
            self.assertEqual(row['consumer_status'], 'bound-consumer-unresolved')
            self.assertEqual(row['binding_rooms'], room)

    def test_hud_alias_excludes_all_source_orders(self):
        sources = [{'file': 'em/em10.drs', 'context': 'body'},
                   {'file': 'ss/inventory.tpl', 'context': 'screen'}]
        for ordered in (sources, list(reversed(sources))):
            row = C.classify_key(KEY, [image('PS2 r101 texture 3')], ordered, resident_refs=['r101'])
            self.assertEqual(row['decision'], 'exclude')
            self.assertIn('hud', row['classes'].split(','))

    def test_complete_provenance_does_not_truncate_late_shared_consumer(self):
        sources = [{'file': 'em/em%02x.drs' % index, 'context': 'texture-index-%d' % index}
                   for index in range(12)]
        sources.append({'file': 'ss/late-ui.tpl', 'context': 'late ' + 'x' * 80})
        refs = ['evidence%d.json' % index for index in range(7)]
        row = C.classify_key(KEY, [image()], sources, text_refs=refs)
        self.assertEqual(row['source_count'], 21)
        self.assertIn('ss/late-ui.tpl', row['sources'])
        self.assertIn('x' * 80, row['sources'])
        self.assertIn('evidence6.json', row['sources'])
        self.assertEqual(row['decision'], 'exclude')

    def test_raw_and_text_mentions_do_not_admit_conversion(self):
        for kwargs in ({'raw_refs': ['r100/geometry.bin']}, {'text_refs': ['historic-report.md']}):
            row = C.classify_key(KEY, [image('PS2 r100 texture 1')], **kwargs)
            self.assertEqual(row['decision'], 'consumer-unresolved')

    def test_positive_drawing_is_not_overruled_by_missing_static_binding(self):
        row = C.classify_key(KEY, [image('PS2 r100 texture 1')], old_decision='not-worth')
        self.assertEqual(row['decision'], 'consumer-unresolved')
        self.assertIn('observed drawing', row['contradiction'])

    def test_origin_room_name_alone_is_not_a_material_binding(self):
        row = C.classify_key(KEY, [image('PS2 r100 texture 1')])
        self.assertEqual(row['decision'], 'not-reachable')
        self.assertEqual(row['consumer_status'], 'no-static-binding')
        self.assertIn('not a pruning proof', row['reason'])

    def test_route_cutscene_is_a_static_candidate_not_measured_minification(self):
        row = C.classify_key(KEY, [image()], [{'file': 'evd/r101s30.evd', 'context': '#1'}],
                             old_decision='not-on-route')
        self.assertEqual(row['decision'], 'mip-chain')
        self.assertEqual(row['consumer_status'], 'archive-on-route')
        self.assertEqual(row['minification'], 'unmeasured')
        self.assertIn('static route reference', row['contradiction'])

    def test_bound_rectangle_stays_blocked_and_existing_chain_stays_exact(self):
        row = C.classify_key(KEY, [image('PS2 r101 texture 1', height=256)], resident_refs=['r101'])
        self.assertEqual(row['decision'], 'convert-blocked')
        row = C.classify_key(KEY, [image('PS2 r101 texture 1', mip=True)], resident_refs=['r101'])
        self.assertEqual(row['decision'], 'already-mipped')

    def test_bad_texture_extent_is_rejected(self):
        for blob in (b'RE4DCTX\0', struct.pack('<8s10I', b'RE4DCTX\0', 2, 48, 96, 1, 48, 144, 32, 0, 1, 0)):
            with self.assertRaises(ValueError):
                C.desc(blob)

    def test_cli_rejects_missing_resident_evidence_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            command = [sys.executable, str(HERE / 'classify.py')]
            for name in ('keys', 'pack', 'gc', 'data', 'origins', 'resident', 'texclass', 'out-tsv', 'out-json'):
                command.extend(['--' + name, str(Path(tmp) / name)])
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertFalse((Path(tmp) / 'out-tsv').exists())
        self.assertEqual(result.returncode, 2)
        self.assertIn('--resident must identify an existing directory', result.stderr)

    def test_cli_rejects_existing_or_aliased_outputs_before_input_reads(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / 'retained.tsv'
            source.write_bytes(b'retained evidence')
            for out_tsv, out_json in ((source, root / 'new.json'),
                                       (root / 'same', root / 'same')):
                command = [sys.executable, '-B', str(HERE / 'classify.py')]
                for name in ('keys', 'pack', 'gc', 'data', 'origins', 'resident', 'texclass'):
                    command += ['--' + name, str(root / 'missing')]
                command += ['--out-tsv', str(out_tsv), '--out-json', str(out_json)]
                result = subprocess.run(command, capture_output=True, text=True)
                self.assertEqual(result.returncode, 2)
                self.assertIn('output', result.stderr)
                self.assertEqual(source.read_bytes(), b'retained evidence')
                self.assertFalse((root / 'new.json').exists())

    def test_cli_retains_scoped_material_and_unknown_resident_evidence(self):
        spec = importlib.util.spec_from_file_location('texpack', HERE.parent / 'texpack.py')
        texpack = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(texpack)

        def package(name):
            payload = bytes(32 * 32 * 2)
            header = struct.pack('<8s10I', b'RE4DCTX\0', 2, 48, 96, 1, 48, 160,
                                 len(payload), 0, zlib.crc32(payload), 0)
            descriptor = struct.pack('<64s8I', name.encode(), 32, 32, 0, 160,
                                     len(payload), 0, 1, 0)
            return header + descriptor + bytes(16) + payload

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            packages = {tuple(int(word, 16) for word in key.split('-')): package(name)
                        for key, name in ((KEY, 'source'), (OTHER, 'PS2 r101 texture 1'))}
            (root / 'tex.pak').write_bytes(texpack.build(packages)[0])
            (root / 'keys.txt').write_text(KEY + '\n' + OTHER + '\n')
            (root / 'gc.json').write_text('{}')
            (root / 'origins.inc').write_text('{0x12345678U,0x90abcdefU,0x279052e0U,0xb695f91fU},\n')
            (root / 'old.tsv').write_text('key\tdecision\n' + KEY + '\tnot-worth\n' + OTHER + '\tnot-on-route\n')
            resident = root / 'resident'
            resident.mkdir()
            (resident / 'r100.tsv').write_text(KEY + '\n')
            room = root / 'data' / 'native' / 'r101'
            room.mkdir(parents=True)
            (room / 'ps2-world.r4pw').write_bytes(world([SCOPED]))
            command = [sys.executable, str(HERE / 'classify.py')]
            options = {'keys': root / 'keys.txt', 'pack': root / 'tex.pak',
                       'gc': root / 'gc.json', 'data': root / 'data',
                       'origins': root / 'origins.inc', 'resident': resident,
                       'texclass': root / 'old.tsv', 'out-tsv': root / 'out.tsv',
                       'out-json': root / 'out.json'}
            for name, path in options.items():
                command.extend(['--' + name, str(path)])
            subprocess.run(command, check=True, capture_output=True, text=True)
            with (root / 'out.tsv').open(newline='') as handle:
                rows = {row['key']: row for row in csv.DictReader(handle, delimiter='\t')}
            summary = json.loads((root / 'out.json').read_text())
        self.assertEqual(rows[KEY]['consumer_status'], 'bound-consumer-unresolved')
        self.assertEqual(rows[KEY]['decision'], 'consumer-unresolved')
        self.assertEqual(rows[OTHER]['decision'], 'mip-chain')
        self.assertEqual(rows[OTHER]['binding_rooms'], 'r101')
        self.assertIn('pkg:r101/ps2-world.r4pw', rows[OTHER]['sources'])
        self.assertEqual(summary['consumer_status'], {'bound-consumer-unresolved': 1, 'bound-on-route': 1})
        import hashlib
        self.assertEqual(set(summary['input_sha256']),
                         {'keys', 'pack', 'gc', 'origins', 'texclass',
                          'resident/r100.tsv', 'native/r101/ps2-world.r4pw'})
        self.assertEqual(summary['input_sha256']['native/r101/ps2-world.r4pw'],
                         hashlib.sha256(world([SCOPED])).hexdigest())
        self.assertEqual(summary['input_sha256']['resident/r100.tsv'],
                         hashlib.sha256((KEY + '\n').encode()).hexdigest())


if __name__ == '__main__':
    unittest.main()
