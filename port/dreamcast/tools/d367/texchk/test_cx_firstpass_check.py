import unittest

from cx_firstpass_check import assess


GOOD = '''warp: room enter 117 (#1) vbl=12
PS2MESH room=117 open
PS2MESH open bytes=862816 placements=238 heap=5700000->4900000
native mesh: no-std room=117: scenery package not opened (PS2_WORLD_ROOMS=2) heap4=4900000
warp: placed room=117 pl=169,-1000,6073 ang=2922/1000
warp: act 0 buttons=0000 stick=100 hold=12 vbl=500
warp: frame 600 room=117 pl=250,-1037,6073 status1=00000200
PS2MESH frame=600 pass=0 placements=129 culled=56 parts=152 native=152 fallback=0 aborts=0
NMRS f=784 room=0117 id=00 ot=7 parts=119 infos=9 plan=L native=600 crowd=0 declined=0 registry_declined=0 absent=0 would=0
'''


class EvidenceGateTests(unittest.TestCase):
    def test_positive_log_requires_separate_asset_audit(self):
        result = assess(GOOD, 'r117')
        for key in ('entry', 'no_fatal', 'warp_directives', 'short_walk', 'ps2_world_draw', 'model_source_fallback'):
            self.assertEqual('PASS', result[key]['status'], key)
        self.assertEqual('UNPROVEN', result['model_ps2_asset_provenance']['status'])

    def test_empty_log_is_not_a_pass(self):
        for key, value in assess('', 'r117').items():
            if isinstance(value, dict):
                self.assertEqual('UNPROVEN', value['status'], key)

    def test_entry_without_motion_and_idle_jitter_do_not_prove_walk(self):
        idle = GOOD.replace('warp: act 0 buttons=0000 stick=100 hold=12 vbl=500\n', '').replace('pl=250,', 'pl=171,')
        self.assertEqual('UNPROVEN', assess(idle, 'r117')['short_walk']['status'])
        blocked_motion = GOOD.replace('pl=250,', 'pl=171,')
        self.assertEqual('UNPROVEN', assess(blocked_motion, 'r117')['short_walk']['status'])

    def test_unknown_warp_and_fatal_fail(self):
        result = assess(GOOD + "warp: unknown line 'status'\nFAULT pc=8c000000\n", 'r117')
        self.assertEqual('FAIL', result['warp_directives']['status'])
        self.assertEqual('FAIL', result['no_fatal']['status'])

    def test_source_fallback_cannot_hide_behind_native_counts(self):
        for token in ('declined=0', 'registry_declined=0', 'absent=0', 'would=0'):
            self.assertEqual('FAIL', assess(GOOD.replace(token, token[:-1]+'1'), 'r117')['model_source_fallback']['status'])
        self.assertEqual('FAIL', assess(GOOD.replace('fallback=0', 'fallback=1'), 'r117')['ps2_world_draw']['status'])

    def test_other_room_draws_and_census_do_not_count(self):
        wrong = GOOD.replace('PS2MESH room=117', 'PS2MESH room=112').replace('room=0117', 'room=0112')
        result = assess(wrong, 'r117')
        self.assertEqual('UNPROVEN', result['ps2_world_draw']['status'])
        self.assertEqual('UNPROVEN', result['model_source_fallback']['status'])

    def test_overflow_is_missing_coverage_and_generic_clip_is_not_gc(self):
        self.assertEqual('UNPROVEN', assess(GOOD+'NMRS f=800 overflow=1\n', 'r117')['model_source_fallback']['status'])
        result = assess(GOOD+'native clip fallback=27\n', 'r117')
        self.assertEqual('PASS', result['ps2_world_draw']['status'])
        self.assertEqual('PASS', result['model_source_fallback']['status'])

    def test_partial_and_zero_census_do_not_prove_coverage(self):
        start = GOOD.index('NMRS ')
        for row in ('NMRS f=784 room=0117 id=00\n', GOOD[start:].replace('native=600', 'native=0')):
            self.assertEqual('UNPROVEN', assess(GOOD[:start] + row, 'r117')['model_source_fallback']['status'])

    def test_motion_before_action_and_room_reentry_do_not_count(self):
        action = 'warp: act 0 buttons=0000 stick=100 hold=12 vbl=500\n'
        late = GOOD.replace(action, '') + action
        self.assertEqual('UNPROVEN', assess(late, 'r117')['short_walk']['status'])
        reentry = GOOD.replace('warp: frame 600', 'warp: room enter 117 (#2) vbl=600\nwarp: frame 600')
        self.assertEqual('UNPROVEN', assess(reentry, 'r117')['short_walk']['status'])

    def test_draw_after_other_room_entry_does_not_count(self):
        mixed = GOOD.replace('PS2MESH frame=600', 'warp: room enter 112 (#2) vbl=900\nPS2MESH frame=600')
        self.assertEqual('UNPROVEN', assess(mixed, 'r117')['ps2_world_draw']['status'])

    def test_missing_module_and_crash_screen_are_fatal(self):
        for line in ('RE4DC MISSING: DLL link/unlink failed called; halting',
                     'CRASH_SCREEN: no new frame for 30 s (ui frame 230)'):
            self.assertEqual('FAIL', assess(GOOD + line + '\n', 'r117')['no_fatal']['status'])

    def test_other_room_model_declines_are_scoped(self):
        other = 'warp: room enter 112 (#2) vbl=900\nNMRM decline t=800 why=shape\nNMRPACK refuse room=0112 why=shape\nNMRS f=900 overflow=2\n'
        self.assertEqual('PASS', assess(GOOD + other, 'r117')['model_source_fallback']['status'])


if __name__ == '__main__':
    unittest.main()
