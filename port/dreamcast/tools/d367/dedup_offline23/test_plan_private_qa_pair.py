import unittest
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
