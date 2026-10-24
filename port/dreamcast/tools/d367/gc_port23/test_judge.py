import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import subprocess
import unittest

spec = importlib.util.spec_from_file_location('gc_judge', Path(__file__).with_name('judge.py'))
j = importlib.util.module_from_spec(spec)
spec.loader.exec_module(j)
DIGEST = 'a' * 64
ROW = dict(room='0111', kind='model', id='em2a/trap', sha256=DIGEST, provenance='gc',
           reason='Audited bear trap source geometry pending PS2 descriptor', owner='gc-port23',
           evidence='GC-ASSETS-INVENTORY-20261023.md row 3')
BEGIN = 'GC-ASSET-BEGIN v=2 room=0111 visit=1 wired=3ff required=3ff catalog=1 catalog_ok=1'
EVENT = f'GC-ASSET v=2 room=0111 visit=1 kind=model id=em2a/trap sha256={DIGEST} provenance=gc consumer=source_geometry action=emit'
END = ('GC-ASSET-COUNTS v=2 room=0111 visit=1 '
       + ' '.join(f'{c}={1 if c == "source_geometry" else 0}' for c in j.CONSUMERS)
       + '\nGC-ASSET-END v=2 room=0111 visit=1 frame=2 wired=3ff checked=3ff required=3ff unique=1 overflow=0 errors=0 catalog_ok=1')
STARTUP = '\n'.join((BEGIN, END.replace('unique=1', 'unique=0'))).replace('room=0111', 'phase=startup')
INITIAL = (BEGIN.replace('room=0111', 'phase=transition from_phase=startup transition_reason=initial-room')+'\n'+END.replace('unique=1', 'unique=0').replace('room=0111', 'phase=transition')).replace('visit=1', 'visit=2')


class JudgeTests(unittest.TestCase):
    def test_protocol_v2_manifest_and_preserved_ordinals(self):
        root = Path(__file__).resolve().parent
        protocol = json.loads((root / 'protocol.json').read_text())
        self.assertEqual(protocol['schema'], 2)
        self.assertEqual(protocol['diagnostic_version'], j.PROTOCOL_VERSION)
        self.assertEqual(protocol['consumers'], list(j.CONSUMERS))
        self.assertEqual(protocol['required'], f'{j.REQUIRED:03x}')
        self.assertEqual(protocol['required'], '3ff')
        self.assertEqual(protocol['consumers'][8:], ['movie','motion'])
        self.assertEqual(protocol['legacy_diagnostic_versions_rejected'], [1])
        self.assertEqual(protocol['motion_identity_kind'], 'motion')
        game = root.parents[2] / 'game'
        source = (game / 'platform/gc_asset_gate.cpp').read_text()
        names = source.split('const char* names[] = {',1)[1].split('};',1)[0]
        self.assertEqual(j.re.findall(r'"([a-z_]+)"',names), list(j.CONSUMERS))
        # Exact UI delta: version literal and explicit exclusion of Motion
        # from a mask derived from Required. Actual wired value stays1f6.
        old = subprocess.check_output(['git','-C',str(game.parents[2]),'show',
            '01b967d0e:port/dreamcast/game/platform/native_ui.cpp'],text=True)
        expected = old.replace('GC-ASSET-ERROR v=1 why=texture-fingerprint',
                               'GC-ASSET-ERROR v=2 why=texture-fingerprint')
        mask='unsigned mask=re4dc_gcasset::Required&~((1U<<re4dc_gcasset::SourceGeometry)|(1U<<re4dc_gcasset::Weapon));'
        self.assertEqual(old.count(mask),1)
        expected=expected.replace(mask,mask.replace('Weapon));','Weapon)|(1U<<re4dc_gcasset::Motion));'))
        current=(game/'platform/native_ui.cpp').read_text()
        # New standalone Motion diagnostics do not alter this historical v2
        # protocol boundary. Strip ONLY exact approved guarded insertions;
        # ungated/bad-guard/dropped-mask mutants are tested separately.
        from test_motion_unknown import project_ui_motion0
        self.assertEqual(project_ui_motion0(current),expected)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'protocol.json'
            for key,value in [('schema',1),('required','1ff'),('diagnostic_version',1),
                              ('consumers',list(j.CONSUMERS[:-1])),('motion_identity_kind','geometry')]:
                changed=dict(protocol);changed[key]=value;path.write_text(json.dumps(changed))
                with self.assertRaises(ValueError):j.read_protocol(path)

    def test_legacy_and_missing_motion_are_not_current_coverage(self):
        full = '\n'.join((STARTUP, INITIAL, '\n'.join((BEGIN,EVENT,END)).replace('visit=1','visit=3')))
        allow = {j.identity(ROW):ROW}
        legacy = full.replace('v=2','v=1').replace('3ff','1ff').replace(' motion=0','')
        result = j.judge([('legacy',legacy)],allow,['0111'])
        self.assertFalse(result['pass']);self.assertEqual(result['schema'],2)
        self.assertTrue(any('historical' in failure for failure in result['failures']))
        for missing in (full.replace('wired=3ff','wired=1ff').replace('checked=3ff','checked=1ff'),
                        full.replace(' motion=0',''),
                        full.replace('motion=0','motion=4294967296')):
            self.assertFalse(j.judge([('missing-motion',missing)],allow,['0111'])['pass'])

    def test_motion_cannot_borrow_geometry_identity_or_allowance(self):
        motion_end = END.replace('source_geometry=1','source_geometry=0').replace('motion=0','motion=1')
        event = EVENT.replace('consumer=source_geometry','consumer=motion')
        self.check('\n'.join((BEGIN,event,motion_end)),False) # old model allowance cannot certify Motion
        motion_event = event.replace('kind=model','kind=motion')
        self.check('\n'.join((BEGIN,motion_event,motion_end)),False)
        motion_row = dict(ROW,kind='motion',reason='Synthetic separately reviewed motion source')
        self.check('\n'.join((BEGIN,motion_event,motion_end)),True,allow={j.identity(motion_row):motion_row})
        with tempfile.TemporaryDirectory() as folder:
            current,accepted=(Path(folder)/name for name in ('current.json','accepted.json'))
            accepted.write_text(json.dumps(dict(schema=1,entries=[ROW])))
            current.write_text(json.dumps(dict(schema=1,entries=[ROW,motion_row])))
            with self.assertRaises(ValueError):j.read_allowlist(current,accepted)

    def check(self, text, expected, required=('0111',), allow=None):
        text = STARTUP + '\n' + INITIAL + '\n' + text.replace('visit=1', 'visit=3')
        result = j.judge([('fixture', text)], {j.identity(ROW): ROW} if allow is None else allow, required)
        self.assertEqual(result['pass'], expected, result)
        return result

    def test_startup_is_named_required_and_has_independent_exceptions(self):
        room = '\n'.join((BEGIN, EVENT, END)).replace('visit=1', 'visit=3')
        self.assertFalse(j.judge([('fixture', room)], {j.identity(ROW): ROW}, ['0111'])['pass'])
        startup_row = dict(ROW);del startup_row['room'];startup_row['phase'] = 'startup'
        startup = '\n'.join((BEGIN, EVENT, END)).replace('room=0111', 'phase=startup')
        allow = {j.identity(ROW): ROW}
        self.assertFalse(j.judge([('fixture', startup+'\n'+INITIAL+'\n'+room)], allow, ['0111'])['pass'])
        allow[j.identity(startup_row)] = startup_row
        self.assertTrue(j.judge([('fixture', startup+'\n'+INITIAL+'\n'+room)], allow, ['0111'])['pass'])
        self.assertFalse(j.judge([('fixture', startup)], allow, [])['pass'])
        for bad in (startup.replace('phase=startup', 'room=0000'),
                    startup.replace('phase=startup', 'phase=startup room=0000'),
                    startup.replace('phase=startup', 'phase=menu'),
                    startup.replace('visit=1', 'visit=2')):
            self.assertFalse(j.judge([('fixture', bad+'\n'+INITIAL+'\n'+room)], allow, ['0111'])['pass'])

    def test_transition_origin_order_and_separate_allowance(self):
        room = '\n'.join((BEGIN, EVENT, END)).replace('visit=1', 'visit=3')
        transition = (BEGIN.replace('room=0111', 'phase=transition from_room=0111 transition_reason=room-retire')+'\n'+EVENT.replace('room=0111', 'phase=transition')+'\n'+END.replace('room=0111', 'phase=transition')).replace('visit=1', 'visit=4')
        next_room = room.replace('0111', '0113').replace('visit=3', 'visit=5')
        allow = {j.identity(ROW): ROW}
        next_row = dict(ROW, room='0113');allow[j.identity(next_row)] = next_row
        reviewed = dict(ROW);del reviewed['room'];reviewed.update(phase='transition', from_room='0111', transition_reason='room-retire')
        full = '\n'.join((STARTUP, INITIAL, room, transition, next_room))
        self.assertFalse(j.judge([('fixture', full)], allow, ['0111', '0113'])['pass'])
        allow[j.identity(reviewed)] = reviewed
        self.assertTrue(j.judge([('fixture', full)], allow, ['0111', '0113'])['pass'])
        for bad in (transition.replace('from_room=0111', 'from_room=0113'),
                    transition.replace('from_room=0111', 'from_phase=startup'),
                    transition.replace('transition_reason=room-retire', 'transition_reason=other'),
                    transition.replace('visit=4', 'visit=3')):
            self.assertFalse(j.judge([('fixture', '\n'.join((STARTUP, INITIAL, room, bad, next_room)))], allow, ['0111'])['pass'])
        self.assertFalse(j.judge([('fixture', '\n'.join((STARTUP, room)))], allow, ['0111'])['pass'])
        self.assertFalse(j.judge([('fixture', '\n'.join((STARTUP, INITIAL, room, next_room)))], allow, ['0111'])['pass'])
        with tempfile.TemporaryDirectory() as folder:
            current, accepted = (Path(folder)/n for n in ('current.json', 'accepted.json'))
            accepted.write_text(json.dumps(dict(schema=1, entries=[reviewed])))
            current.write_text(accepted.read_text());self.assertEqual(len(j.read_allowlist(current, accepted)), 1)
            reviewed['from_room'] = '0113';current.write_text(json.dumps(dict(schema=1, entries=[reviewed])))
            with self.assertRaises(ValueError):j.read_allowlist(current, accepted)

    def test_startup_allowlist_cannot_borrow_room_or_grow(self):
        startup = dict(ROW);del startup['room'];startup['phase'] = 'startup'
        with tempfile.TemporaryDirectory() as folder:
            current, accepted = (Path(folder)/n for n in ('current.json', 'accepted.json'))
            accepted.write_text(json.dumps(dict(schema=1, entries=[ROW])))
            current.write_text(json.dumps(dict(schema=1, entries=[startup])))
            with self.assertRaises(ValueError):j.read_allowlist(current, accepted)
            accepted.write_text(current.read_text())
            self.assertEqual(len(j.read_allowlist(current, accepted)), 1)
            startup['room'] = '0000';current.write_text(json.dumps(dict(schema=1, entries=[startup])))
            with self.assertRaises(ValueError):j.read_allowlist(current, accepted)

    def test_exact_reviewed_gc_pass(self):
        self.check('\n'.join((BEGIN, EVENT, END)), True)

    def test_empty_and_load_only_fail(self):
        self.check('', False)
        self.check('load /cd/em/em2a.drs ready=1', False)

    def test_unreviewed_same_class_new_id_fails(self):
        self.check('\n'.join((BEGIN, EVENT.replace('em2a/trap', 'em2a/new-trap'), END)), False)

    def test_changed_payload_same_name_fails(self):
        self.check('\n'.join((BEGIN, EVENT.replace(DIGEST, 'b' * 64), END)), False)

    def test_unknown_cannot_inherit_gc_exception_or_ps2_claim(self):
        self.check('\n'.join((BEGIN, EVENT.replace('provenance=gc', 'provenance=unknown'), END)), False)
        self.check('\n'.join((BEGIN, EVENT.replace('provenance=gc', 'provenance=ps2'), END)), False)

    def test_missing_end_or_begin_fail(self):
        self.check('\n'.join((BEGIN, EVENT)), False)
        self.check('\n'.join((EVENT, END)), False)

    def test_incomplete_wiring_and_runtime_coverage_fail(self):
        self.check('\n'.join((BEGIN.replace('wired=3ff', 'wired=1fe'), EVENT, END)), False)
        self.check('\n'.join((BEGIN, EVENT, END.replace('checked=3ff', 'checked=1fe'))), False)

    def test_missing_requested_room_fails(self):
        self.check('\n'.join((BEGIN, EVENT, END)), False, ('0111', '0113'))

    def test_overflow_errors_bad_catalog_fail(self):
        for field in ('overflow', 'errors'):
            self.check('\n'.join((BEGIN, EVENT, END.replace(field+'=0', field+'=1'))), False)
        self.check('\n'.join((BEGIN, EVENT, END.replace('catalog_ok=1', 'catalog_ok=0'))), False)

    def test_duplicate_row_and_count_mismatch_fail(self):
        self.check('\n'.join((BEGIN, EVENT, EVENT, END)), False)
        self.check('\n'.join((BEGIN, EVENT, END.replace('unique=1', 'unique=0'))), False)

    def test_wrong_consumer_counter_cannot_explain_first_use(self):
        self.check('\n'.join((BEGIN, EVENT.replace('consumer=source_geometry', 'consumer=weapon'), END)), False)

    def test_load_ready_is_not_an_emission(self):
        for action in ('load', 'ready', 'reserve', 'culled'):
            self.check('\n'.join((BEGIN, EVENT.replace('action=emit', 'action='+action), END)), False)

    def test_explicit_empty_room_passes_only_with_complete_coverage(self):
        self.check('\n'.join((BEGIN, END.replace('unique=1', 'unique=0'))), True)

    def test_allowlist_only_shrinks(self):
        with tempfile.TemporaryDirectory() as folder:
            current, ceiling = (Path(folder)/n for n in ('current.json', 'ceiling.json'))
            base = dict(schema=1, entries=[ROW])
            ceiling.write_text(json.dumps(base))
            current.write_text(json.dumps(dict(schema=1, entries=[])))
            self.assertEqual(j.read_allowlist(current, ceiling), {})
            for change in ({'id': '*'}, {'sha256': '*'}, {'provenance': 'ps2'}, {'owner': ''}, {'id': 'em2a/new'}):
                bad = copy.deepcopy(base)
                bad['entries'][0].update(change)
                current.write_text(json.dumps(bad))
                with self.assertRaises(ValueError):
                    j.read_allowlist(current, ceiling)


if __name__ == '__main__':
    unittest.main()
