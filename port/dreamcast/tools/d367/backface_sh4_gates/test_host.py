import pathlib,unittest
from compare import diff_rgb,Refusal,evidence,ganado_burst,memory_gate
from model import model
P=pathlib.Path(__file__).parent
class Tests(unittest.TestCase):
 def test_ganado_window(self):
  log='bfc: frame=301..360 scenes=60 cls=4 v=100 cv=100'
  self.assertTrue(ganado_burst(log,[300,420]));self.assertFalse(ganado_burst(log,[361,420]));self.assertFalse(ganado_burst(log.replace('v=100','v=0'),[300,420]))
 def test_no_standin_ganado(self):self.assertFalse(ganado_burst('bfc: frame=301..360 scenes=60 cls=3 v=100',[300,420]))
 def test_memory_gate(self):self.assertTrue(memory_gate(dict(squeeze_bytes=49152,minimum_KOS_headroom=4096,s30_frames=340,s30_expected=340,heap4_refusals=0,heap4_before=39616,missing_symbols=0)))
 def test_incomplete_s30_refuses(self):
  with self.assertRaises(Refusal):memory_gate(dict(squeeze_bytes=49152,minimum_KOS_headroom=4096,s30_frames=339,s30_expected=340,heap4_refusals=0,heap4_before=39616,missing_symbols=0))
 def test_identical(self):self.assertEqual(diff_rgb(bytes(6),bytes(6),(2,1),(2,1))['different_pixels'],0)
 def test_one_pixel(self):self.assertEqual(diff_rgb(bytes(6),bytes([0,0,0,0,1,0]),(2,1),(2,1))['different_pixels'],1)
 def test_missing_pixel(self):
  with self.assertRaises(Refusal):diff_rgb(bytes(5),bytes(6),(2,1),(2,1))
 def test_dimension_mismatch(self):
  with self.assertRaises(Refusal):diff_rgb(bytes(6),bytes(6),(1,2),(2,1))
 def test_wrong_emu_refuses_before_reads(self):
  with self.assertRaises(Refusal):evidence({'emu':'harness'})
 def test_complete_guard(self):
  with self.assertRaises(Refusal):evidence({'emu':'console','run_complete':False,'errors':[]})
 def test_hang_guard(self):
  with self.assertRaises(Refusal):evidence({'emu':'console','run_complete':True,'errors':[],'hang_or_fault':True})
 def test_capture_guard(self):
  with self.assertRaises(Refusal):evidence({'emu':'console','run_complete':True,'errors':[],'hang_or_fault':False,'capture_seconds_after_freeze':31})
 def test_model_denominators(self):
  with self.assertRaises(ValueError):model(P/'handcount-edge.schedule',0,1,'illustrative')
 def test_model_scope(self):self.assertEqual(model(P/'handcount-edge.schedule',1,1,'illustrative')['source_kind'],'illustrative')
if __name__=='__main__':unittest.main()
