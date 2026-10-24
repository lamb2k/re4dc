import unittest
import json
from pathlib import Path
import tempfile
from unittest.mock import patch
import plan_private_qa_pair as q


class PrivateQaPlanTests(unittest.TestCase):
    def test_standard_qa_both_modes(self):
        for mode in (0,3):
            knobs={**q.QA,'SCENERY_DEDUP':str(mode),**{k:'0' for k in q.DIAGNOSTIC_ZERO}}
            self.assertTrue(q.resolved_qa(knobs,mode))

    def test_diagnostic_contamination_and_absence_refused(self):
        good={**q.QA,'SCENERY_DEDUP':'3',**{k:'0' for k in q.DIAGNOSTIC_ZERO}}
        for key in q.DIAGNOSTIC_ZERO:
            with self.subTest(key=key):
                with self.assertRaises(ValueError):q.resolved_qa({**good,key:'1'},3)
                missing=dict(good);del missing[key]
                with self.assertRaises(ValueError):q.resolved_qa(missing,3)

    def test_path_remap_preserves_data_names(self):
        before={'argv':['/live/tools/ch2.sh','dc/native/r101/ps2-dd3.re4mesh'],'env':{'T':'/live'}}
        self.assertEqual(q.remap(before,'/live','/private'),
                         {'argv':['/private/tools/ch2.sh','dc/native/r101/ps2-dd3.re4mesh'],'env':{'T':'/private'}})

    def test_current_source_mismatch_refused_before_file_io(self):
        source='a'*40
        with self.assertRaisesRegex(ValueError,'exact frozen source'):
            q.validate_plan({'source':'b'*40},source)
        with self.assertRaisesRegex(ValueError,'exact frozen source'):
            q.validate_plan({'source':source},'a'*39)

    def test_current_qa_src_must_match_frozen_programme(self):
        source='a'*40
        good={**q.QA,'QA_SRC':source[:8],'SCENERY_DEDUP':'3',**{k:'0' for k in q.DIAGNOSTIC_ZERO}}
        self.assertTrue(q.resolved_qa(good,3,source))
        with self.assertRaisesRegex(ValueError,'QA_SRC'):
            q.resolved_qa({**good,'QA_SRC':q.SOURCE[:8]},3,source)

    def test_private_programs_match_actual_payload_overlay_lookup(self):
        # Execute the actual t11 payload_base body with controlled files; the
        # private stage must choose this programme rather than baseline ovl.
        import importlib.util
        src=Path(q.__file__).resolve().parents[1]/'test11/t11-fix.py'
        spec=importlib.util.spec_from_file_location('private_t11',src)
        t11=importlib.util.module_from_spec(spec);spec.loader.exec_module(t11)
        with tempfile.TemporaryDirectory(dir='/dev/shm') as tmp:
            root=Path(tmp);work=root/'private';payload=root/'payload';payload.mkdir()
            label='new-current-on';private=work/'programs'/('candidate-route'+label);private.mkdir(parents=True)
            (private/'sscrn.ovl').write_bytes(b'current programme')
            (payload/'tree/dc').mkdir(parents=True);(payload/'tree/dc/sscrn.ovl').write_bytes(b'old baseline')
            (payload/'MANIFEST-disc.json').write_text(json.dumps({'dc/sscrn.ovl':dict(sha256='baseline',size=12)}))
            p=dict(source=q.SOURCE,tree='/frozen',recipe=dict(sha256=q.sha(b'recipe')),data_sets='unchanged',
                alternates=[],baseline_packages={},qa=dict(arms={}))
            for arm in ('off','on'):
                p['qa']['arms'][arm]=dict(label=label,pkgtree=dict(environment={'PKG_K':'/oldwork'}),
                    build=dict(environment={},argv=['build']),stage=dict(environment={}))
            with patch.object(q,'validate_plan'),patch.object(q,'git',return_value=b'recipe'):
                planned=q.make_plan(p,root,root/'buildtree',work)
            stage=planned['arms']['on']['stage']['environment']
            self.assertEqual(stage['RE4DC_HARNESS']+'/programs',
                planned['arms']['on']['build']['environment']['ROUTE_PROGRAMS_DIR'])
            t11.PAYLOAD_ROOT=str(payload);t11.STAGE_BASE=str(root/'absent')
            t11.HARNESS=stage['RE4DC_HARNESS']
            current=t11.payload_base(label)['replace']['dc/sscrn.ovl']
            self.assertEqual(Path(current),private/'sscrn.ovl')
            t11.HARNESS=str(root/'wrong-harness')
            wrong=t11.payload_base(label)['replace']['dc/sscrn.ovl']
            self.assertEqual(Path(wrong),payload/'tree/dc/sscrn.ovl')
            self.assertNotEqual(Path(current).read_bytes(),Path(wrong).read_bytes())
