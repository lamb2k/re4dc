import tempfile,unittest
from pathlib import Path
from PIL import Image
from compare_four import compare,sha
class Tests(unittest.TestCase):
 def fixture(self,base,colours):
  events=[]
  for arm in range(2):
   directory=base/str(arm);directory.mkdir();pins={}
   for index in range(2):
    path=directory/f'fb{index}.png';Image.new('RGB',(2,2),colours[arm*2+index]).save(path);pins[path.name]=sha(path)
   events.append(dict(qualified=True,framebuffer_source_offsets=[0,614400],freeze_observed_monotonic=1,
                      stock_grace_seconds=8,stock_stop_deadline_monotonic=9,capture_start_monotonic=1,
                      capture_end_monotonic=2,path=str(directory),images=pins))
  return events
 def test_all_four_identical(self):
  with tempfile.TemporaryDirectory() as tmp:self.assertTrue(compare(*self.fixture(Path(tmp),[(1,2,3)]*4))['pixel_equivalent_without_selector'])
 def test_pairwise_only_refuses(self):
  with tempfile.TemporaryDirectory() as tmp:self.assertFalse(compare(*self.fixture(Path(tmp),[(1,2,3),(3,2,1)]*2))['pixel_equivalent_without_selector'])
 def test_changed_retained_image_refuses(self):
  with tempfile.TemporaryDirectory() as tmp:
   events=self.fixture(Path(tmp),[(1,2,3)]*4);(Path(tmp)/'0/fb0.png').write_bytes(b'changed')
   with self.assertRaises(ValueError):compare(*events)
 def test_late_event_refuses(self):
  with tempfile.TemporaryDirectory() as tmp:
   events=self.fixture(Path(tmp),[(1,2,3)]*4);events[0]['capture_end_monotonic']=30
   with self.assertRaises(ValueError):compare(*events)
if __name__=='__main__':unittest.main()
