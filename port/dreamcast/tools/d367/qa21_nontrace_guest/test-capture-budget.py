import importlib.util,pathlib,unittest
s=importlib.util.spec_from_file_location('broker',pathlib.Path(__file__).with_name('capture-budget.py'));b=importlib.util.module_from_spec(s);s.loader.exec_module(b)
class Broker(unittest.TestCase):
 def test_reserves_final_two_and_blocks_duplicate(self):
  x=b.Budget()
  for i in range(3):self.assertTrue(x.request(str(i),i*2,100))
  self.assertFalse(x.request('more',6,100));self.assertFalse(x.request('0',6,100));self.assertTrue(x.request('final',6,100,True));x.validate(8)
 def test_no_screenshot_traffic_near_evidence_cap(self):self.assertFalse(b.Budget().request('early',0,55000000))
 def test_unexpected_external_periodic_capture_disqualifies(self):
  with self.assertRaises(RuntimeError):b.Budget().request('early',2,100)
 def test_actual_png_count_mismatch_disqualifies(self):
  with self.assertRaises(RuntimeError):b.Budget().validate(1)
if __name__=='__main__':unittest.main(verbosity=2)
