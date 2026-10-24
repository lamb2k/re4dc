import importlib.util,pathlib,unittest
p=pathlib.Path(__file__).with_name('freeze_capture.py');s=importlib.util.spec_from_file_location('capture',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Controls(unittest.TestCase):
 def test_exact_marker_requires_placed_room(self):
  self.assertEqual(m.marker('warp: frozen at tick 330','101','101')['tick'],330)
  for line,placed in [('warp: frozen at tick 331','101'),('warp: frozen at tick 330',None),('warp: frozen at tick 330','100')]:
   with self.assertRaises(ValueError):m.marker(line,placed,'101')
 def test_other_log_not_capture(self):self.assertIsNone(m.marker('warp: frame 330 room=101','101','101'))
 def test_bad_frame_extent_refused(self):
  class Mod:VRAM_SIZE=8*1024*1024
  with self.assertRaises(ValueError):m.frame_bytes(b'short',0,Mod)
if __name__=='__main__':unittest.main(verbosity=2)
