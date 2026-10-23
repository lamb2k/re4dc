import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('gc_judge', Path(__file__).with_name('judge.py'))
j = importlib.util.module_from_spec(spec)
spec.loader.exec_module(j)
DIGEST = 'a' * 64
ROW = dict(room='0111', kind='model', id='em2a/trap', sha256=DIGEST, provenance='gc',
           reason='Audited bear trap source geometry pending PS2 descriptor', owner='gc-port23',
           evidence='GC-ASSETS-INVENTORY-20261023.md row 3')
BEGIN = 'GC-ASSET-BEGIN v=1 room=0111 visit=1 wired=1ff required=1ff catalog=1 catalog_ok=1'
EVENT = f'GC-ASSET v=1 room=0111 visit=1 kind=model id=em2a/trap sha256={DIGEST} provenance=gc consumer=source_geometry action=emit'
END = ('GC-ASSET-END v=1 room=0111 visit=1 frame=2 wired=1ff checked=1ff required=1ff unique=1 overflow=0 errors=0 catalog_ok=1 '
       + ' '.join(f'{c}={1 if c == "source_geometry" else 0}' for c in j.CONSUMERS))


class JudgeTests(unittest.TestCase):
    def check(self, text, expected, required=('0111',), allow=None):
        result = j.judge([('fixture', text)], {j.identity(ROW): ROW} if allow is None else allow, required)
        self.assertEqual(result['pass'], expected, result)
        return result

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
        self.check('\n'.join((BEGIN.replace('wired=1ff', 'wired=1fe'), EVENT, END)), False)
        self.check('\n'.join((BEGIN, EVENT, END.replace('checked=1ff', 'checked=1fe'))), False)

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
