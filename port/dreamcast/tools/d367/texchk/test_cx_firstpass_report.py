"""Input-integrity regressions using disk-backed evidence, not emulator runs."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import cx_firstpass_report as report


GOOD_LOG = '''warp: room enter 117 (#1) vbl=12
PS2MESH room=117 open
PS2MESH open bytes=862816 placements=238 heap=5700000->4900000
native mesh: no-std room=117: scenery package not opened (PS2_WORLD_ROOMS=2) heap4=4900000
warp: placed room=117 pl=169,-1000,6073 ang=2922/1000
warp: act 0 buttons=0000 stick=100 hold=12 vbl=500
warp: frame 600 room=117 pl=250,-1037,6073 status1=00000200
PS2MESH frame=600 pass=0 placements=129 culled=56 parts=152 native=152 fallback=0 aborts=0
NMRS f=784 room=0117 id=00 ot=7 parts=119 infos=9 plan=L native=600 crowd=0 declined=0 registry_declined=0 absent=0 would=0
native UI VRAM: used=6400000 free=1200000
native UI VRAM: used=6000000 free=1600000
'''
IDENTITY_KEYS = ('scenario', 'arm', 'elf_sha256', 'disc_sha256')


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n')


class FirstPassReportIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name)
        self.harness = self.root/'harness'
        self.textures = self.root/'textures'
        write_json(self.textures/'rooms/r117.json', {
            'standalone_world_payload_before': 619520,
            'standalone_world_payload_after': 619520,
            'runtime_parser': 'PASS',
        })
        self.readiness = {'rooms': {'r117': {
            'manifest': '/fixture/r117.json', 'views': ['entry', 'left', 'right', 'walk'],
            'blockers': [], 'texture_selection': {'fixture_selection': 'PASS'},
        }}}
        self.tex_check = patch.object(report.texchk, 'check', return_value=True).start()
        self.addCleanup(patch.stopall)

    def make_run(self, name='cx-r117-walk-01', log=GOOD_LOG):
        path = self.harness/'scenarios'/name
        identity = {'scenario': name, 'arm': 'cxfirstpassW',
                    'elf_sha256': '1'*64, 'disc_sha256': '2'*64}
        stage = dict(identity, status='STAGED_PAYLOAD_IDENTITY_PASS',
                     both_namespaces_verified=True, independent_raw_reader_verified=True,
                     boot_area_preserved=True,
                     fixture={'provenance': {'cx_room': {'room': 'r117'}},
                              'replace': {'dc/warp.txt': '/fixture/warp.txt'}})
        run = dict(identity, status='RUN_COMPLETE_AWAITING_REVIEW', reader_exit=0,
                   owned_emulator_exited=True, errors=[])
        write_json(path/'stage.json', stage)
        write_json(path/'payload-manifest.json', {
            'dc/warp.txt': {'sha256': '3'*64, 'size': 128},
            'dc/tex.pak': {'sha256': '4'*64, 'size': 4096},
        })
        write_json(path/'capture/run-result.json', run)
        (path/'capture/run-output.txt').write_bytes(log.encode('latin1'))
        return path, stage, run

    def build(self, names, walks=()):
        return report.build_report(self.harness, self.readiness, self.textures,
                                   {'r117': {'scenarios': list(names), 'walk_scenarios': list(walks)}})

    def test_complete_matching_evidence_passes_without_claiming_asset_provenance(self):
        path, stage, _ = self.make_run()
        result = report.inspect_run(path)
        for key in ('capture', 'evidence_identity', 'staged_payload', 'tex_check', 'short_walk'):
            self.assertEqual('PASS', result['checks'][key]['status'], key)
        self.assertEqual('UNPROVEN', result['checks']['model_ps2_asset_provenance']['status'])
        self.assertEqual(hashlib.sha256((path/'capture/run-output.txt').read_bytes()).hexdigest(),
                         result['log_sha256'])
        self.assertEqual(hashlib.sha256((path/'stage.json').read_bytes()).hexdigest(), result['stage_sha256'])
        self.assertEqual(stage['elf_sha256'], result['elf_sha256'])
        self.tex_check.assert_called_once_with(path/'capture/run-output.txt')

    def test_each_run_stage_identity_mismatch_fails(self):
        for key in IDENTITY_KEYS:
            with self.subTest(key=key):
                path, _, run = self.make_run()
                run[key] = 'different-' + run[key]
                write_json(path/'capture/run-result.json', run)
                check = report.inspect_run(path)['checks']['evidence_identity']
                self.assertEqual('FAIL', check['status'])
                self.assertIn(key, check['mismatched'])

    def test_each_missing_or_empty_identity_is_unproven_on_either_side(self):
        for source in ('stage.json', 'capture/run-result.json'):
            for key in IDENTITY_KEYS:
                for mode in ('missing', 'null', 'empty'):
                    with self.subTest(source=source, key=key, mode=mode):
                        path, stage, run = self.make_run()
                        value = stage if source == 'stage.json' else run
                        if mode == 'missing':
                            del value[key]
                        else:
                            value[key] = None if mode == 'null' else ''
                        write_json(path/source, value)
                        check = report.inspect_run(path)['checks']['evidence_identity']
                        self.assertEqual('UNPROVEN', check['status'])
                        self.assertIn(key, check['missing'])

    def test_matching_metadata_cannot_name_a_different_directory(self):
        path, stage, run = self.make_run()
        stage['scenario'] = run['scenario'] = 'cx-r117-foreign-01'
        write_json(path/'stage.json', stage)
        write_json(path/'capture/run-result.json', run)
        check = report.inspect_run(path)['checks']['evidence_identity']
        self.assertEqual('FAIL', check['status'])
        self.assertIn('directory_scenario', check['mismatched'])

    def test_capture_missing_completion_fields_is_unproven(self):
        for key in ('status', 'reader_exit', 'owned_emulator_exited', 'errors'):
            with self.subTest(key=key):
                path, _, run = self.make_run()
                del run[key]
                write_json(path/'capture/run-result.json', run)
                check = report.inspect_run(path)['checks']['capture']
                self.assertEqual('UNPROVEN', check['status'])
                self.assertIn(key, check['missing'])

    def test_explicit_capture_failure_cannot_pass_on_clean_error_list(self):
        failures = {'status': 'RUN_ABORTED', 'reader_exit': 1,
                    'owned_emulator_exited': False, 'errors': ['reader failed']}
        for key, value in failures.items():
            with self.subTest(key=key):
                path, _, run = self.make_run()
                run[key] = value
                write_json(path/'capture/run-result.json', run)
                check = report.inspect_run(path)['checks']['capture']
                self.assertEqual('FAIL', check['status'])
                self.assertIn(key, check['mismatched'])

    def test_staging_missing_verification_is_unproven_and_false_is_failure(self):
        for key in ('both_namespaces_verified', 'independent_raw_reader_verified', 'boot_area_preserved'):
            for mode in ('missing', 'false'):
                with self.subTest(key=key, mode=mode):
                    path, stage, _ = self.make_run()
                    if mode == 'missing':
                        del stage[key]
                    else:
                        stage[key] = False
                    write_json(path/'stage.json', stage)
                    check = report.inspect_run(path)['checks']['staged_payload']
                    self.assertEqual('UNPROVEN' if mode == 'missing' else 'FAIL', check['status'])

    def test_generic_texture_success_without_live_world_is_unproven(self):
        path, _, _ = self.make_run(log='native UI VRAM: used=128 free=512\n')
        result = report.inspect_run(path)
        self.assertEqual('UNPROVEN', result['checks']['ps2_world_draw']['status'])
        self.assertEqual('UNPROVEN', result['checks']['tex_check']['status'])
        self.tex_check.return_value = False
        self.assertEqual('FAIL', report.inspect_run(path)['checks']['tex_check']['status'])

    def test_periodic_vram_samples_are_not_reported_as_interval_peak(self):
        path, _, _ = self.make_run()
        value = report.inspect_run(path)['memory']
        self.assertEqual(6400000, value['vram_sampled_used_max'])
        self.assertEqual(1200000, value['vram_sampled_free_min'])
        self.assertEqual({'used': 6000000, 'free': 1600000}, value['vram_latest'])
        self.assertEqual(800000, value['world_opens'][0]['heap_consumed'])
        self.assertNotIn('vram_used_peak', value)
        self.assertNotIn('vram_free_min', value)
        empty = report.memory('')
        self.assertIsNone(empty['vram_sampled_used_max'])
        self.assertIsNone(empty['vram_sampled_free_min'])

    def test_selected_missing_scenario_is_preserved_as_unavailable(self):
        name = 'cx-r117-missing-01'
        result = self.build([name], [name])
        self.assertTrue(result['captures'][name]['unavailable'])
        self.assertEqual([name], result['rooms']['r117']['selected_scenarios'])
        self.assertEqual('UNPROVEN', result['rooms']['r117']['overall'])
        for key, status in result['rooms']['r117']['checks'].items():
            self.assertEqual('UNPROVEN', status, key)
        self.assertIn(name, report.markdown(result))

    def test_selected_partial_capture_is_unavailable_not_an_exception(self):
        for missing in ('stage.json', 'payload-manifest.json', 'capture/run-output.txt', 'capture/run-result.json'):
            with self.subTest(missing=missing):
                path, _, _ = self.make_run()
                (path/missing).unlink()
                result = self.build([path.name], [path.name])
                self.assertTrue(result['captures'][path.name]['unavailable'])
                self.assertEqual('UNPROVEN', result['rooms']['r117']['checks']['capture'])
                self.assertIn(path.name, report.markdown(result))

    def test_unavailable_selection_downgrades_success_and_history_stays_separate(self):
        current, _, _ = self.make_run()
        historical, _, run = self.make_run('cx-r117-walk-old')
        run['status'] = 'RUN_ABORTED'
        write_json(historical/'capture/run-result.json', run)
        value = self.build([current.name], [current.name])
        self.assertEqual('PASS', value['rooms']['r117']['checks']['capture'])
        self.assertEqual([historical.name], value['rooms']['r117']['historical_scenarios'])
        self.assertEqual('FAIL', value['captures'][historical.name]['checks']['capture']['status'])
        mixed = self.build([current.name, 'cx-r117-missing-01'], [current.name])
        self.assertEqual('UNPROVEN', mixed['rooms']['r117']['checks']['capture'])
        self.assertEqual('UNPROVEN', mixed['rooms']['r117']['checks']['evidence_identity'])
        self.assertEqual('PASS', mixed['rooms']['r117']['checks']['short_walk'])

    def test_empty_walk_selection_stays_unproven_and_nonselected_walk_is_rejected(self):
        path, _, _ = self.make_run()
        value = self.build([path.name])
        self.assertEqual('UNPROVEN', value['rooms']['r117']['checks']['short_walk'])
        with self.assertRaisesRegex(ValueError, 'walk selection must be a subset'):
            self.build([path.name], ['cx-r117-unselected-01'])


if __name__ == '__main__':
    unittest.main()