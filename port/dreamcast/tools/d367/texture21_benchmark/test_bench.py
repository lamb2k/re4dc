import copy
import tempfile
import unittest
from pathlib import Path
import bench

D = {'size': 4, 'sha256': 'same'}

class BenchmarkAdmissionTests(unittest.TestCase):
    def fixtures(self):
        arm = {'scene': {'window': [300,419]}, 'knobs': {'ANIMALS_OFF': '1'},
               'source': {'head': 'source', 'dirty': ''},
               'build': {'program.bin': D, 'st1_0.ovl': D}, 'objects': {'native_static.o': D},
               'preprocessing': {'one.i': D}, 'admission_errors': []}
        image = {'files': {'1ST_READ.BIN': D, 'dc/st1_0.ovl': D, 'dc/tex.pak': D, 'dc/world103.re4world': D}}
        return arm, copy.deepcopy(arm), image, copy.deepcopy(image)

    def evaluate(self, items, allowed=('dc/tex.pak',)):
        return bench.compare(*items, allowed)

    def test_matched_texture_pair_and_no_fps_claim(self):
        a,b,ia,ib=self.fixtures();ib['files']['dc/tex.pak']={'size':8,'sha256':'new'}
        r=self.evaluate((a,b,ia,ib))
        self.assertTrue(r['asset_pair_admissible'])
        self.assertFalse(r['performance_improvement_claimed'])

    def test_same_label_cannot_hide_animals_or_geometry(self):
        a,b,ia,ib=self.fixtures();b['knobs']['ANIMALS_OFF']='0'
        self.assertFalse(self.evaluate((a,b,ia,ib))['asset_pair_admissible'])
        a,b,ia,ib=self.fixtures();ib['files']['dc/world103.re4world']={'size':5,'sha256':'other'}
        self.assertFalse(self.evaluate((a,b,ia,ib))['asset_pair_admissible'])

    def test_staged_program_and_overlay_must_bind_build(self):
        for path in ['1ST_READ.BIN','dc/st1_0.ovl']:
            a,b,ia,ib=self.fixtures();ib['files'][path]={'size':4,'sha256':'old'}
            self.assertFalse(self.evaluate((a,b,ia,ib),tuple(ib['files']))['asset_pair_admissible'])

    def test_object_source_frame_and_preprocessor_mismatch(self):
        for key in ['objects','source','scene','preprocessing']:
            a,b,ia,ib=self.fixtures();b[key]={'changed': {'size': 4, 'sha256': 'different'}} if key!='source' else {'head':'other','dirty':''}
            self.assertFalse(self.evaluate((a,b,ia,ib))['asset_pair_admissible'],key)
        a,b,ia,ib=self.fixtures();b['preprocessing']={}
        self.assertFalse(self.evaluate((a,b,ia,ib))['asset_pair_admissible'])

    def test_scene_preserves_kill_schedule_and_rejects_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'farm'; plan=bench.scene('farm-midfight',out)
            self.assertIn('kill 0x12 150 0x103',(out/'warp.txt').read_text())
            self.assertEqual(plan['window']['inclusive_frames'],120)
            self.assertEqual(plan['required_actual_knobs']['SS_WINDOW_HOLD_RESTORE'],'0')
            with self.assertRaises(FileExistsError):bench.scene('farm-midfight',out)

    def test_seal_refuses_incomplete_build(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):bench.seal(tmp,tmp,'missing',Path(tmp)/'out')

if __name__=='__main__':unittest.main()
