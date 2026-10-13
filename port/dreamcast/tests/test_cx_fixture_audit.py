"""Selected archive errors must not inherit failures from retained old outputs."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location(
    'cx_fixture_audit', Path(__file__).parents[1] / 'tools/d367/cx_fixture_audit.py')
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


class ArchiveErrorHistory(unittest.TestCase):
    def report(self, room, suffix, errors):
        folder=room / suffix
        path=folder / 'tex/native-ui-report.json'
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({'errors': errors}))
        return folder

    def test_successful_selected_archive_has_no_historical_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            room=Path(tmp) / 'r203'
            old=self.report(room,'ancillary-aaaa',[{'error':'old failure'}])
            active=self.report(room,'ancillary-bbbb',[])
            manifest={'dependencies':[{'destination':'st2/r203.arc',
                'source':str(active/'mirror/st2/r203.arc')}],
                'blockers':['New ancillary DAR has no qualified AICA bank.']}
            current, historical, selected=AUDIT.archive_error_history(room,manifest)
            self.assertEqual(current,[])
            self.assertEqual([r['error'] for r in historical],['old failure'])
            self.assertEqual(selected,[str(active)])

    def test_current_failed_preparation_uses_exact_manifest_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            room=Path(tmp) / 'r208'
            old=self.report(room,'ancillary',[{'error':'old failure'}])
            active=self.report(room,'ancillary-cdef',[{'error':'current failure'}])
            manifest={'dependencies':[], 'blockers':[
                'Ancillary preparation: command exited 2; '+str(active/'textures.log')]}
            current, historical, selected=AUDIT.archive_error_history(room,manifest)
            self.assertEqual([r['error'] for r in current],['current failure'])
            self.assertEqual([r['error'] for r in historical],['old failure'])
            self.assertEqual(selected,[str(active)])

    def test_external_reviewed_archive_does_not_select_local_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            room=Path(tmp) / 'r117'
            self.report(room,'ancillary-aaaa',[{'error':'abandoned attempt'}])
            manifest={'dependencies':[{'destination':'st1/r117.arc',
                'source':'/reviewed/r117.arc'}]}
            current, historical, selected=AUDIT.archive_error_history(room,manifest)
            self.assertEqual(current,[])
            self.assertEqual(selected,[])
            self.assertEqual(len(historical),1)


if __name__ == '__main__':
    unittest.main()
