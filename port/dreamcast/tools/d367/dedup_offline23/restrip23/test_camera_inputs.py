import unittest,tempfile
from pathlib import Path
from camera_selection import cameras,legacy_viewport_audit
class CameraInputs(unittest.TestCase):
 def row(self,vp):return 'PS2CAM f=500 cf=46c35000 c='+'00000000 '*12+'p='+'00000000 '*7+'vp='+vp
 def runrow(self,row):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'camera';p.write_text(row);return cameras(p,500,500),legacy_viewport_audit(p,500,500)
 def test_missing_unused_tail_is_not_repaired(self):
  cam,a=self.runrow(self.row('00000000 00000000 44200000 43f00000 00000000 3f80000'))
  self.assertEqual(a['truncated_rows'],1);self.assertEqual(a['frames'][500]['remaining_words'][-1],'3f80000');self.assertEqual(len(cam[0][1]),20)
 def test_offsets_bad_extent_and_missing_used_word_rejected(self):
  for vp in ('3f800000 00000000 44200000 43f00000','00000000 00000000 00000000 43f00000','00000000 00000000 44200000 43f0000'):
   with self.assertRaises(ValueError):self.runrow(self.row(vp))
 def test_unused_tail_cannot_change_model_camera(self):
  a,_=self.runrow(self.row('00000000 00000000 44200000 43f00000 deadbeef fffffff'))
  b,_=self.runrow(self.row('00000000 00000000 44200000 43f00000 00000000 3f800000'))
  self.assertEqual(a,b)
if __name__=='__main__':unittest.main()
