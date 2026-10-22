import math,unittest
from active_gate import camera_valid,phases
class ActiveGateTests(unittest.TestCase):
 def test_active_projection_and_lookat_required(self):
  cot=1/math.tan(math.radians(25));q=[0.0]*16;q[0]=cot/1.3333334;q[5]=cot;q[14]=-1
  row={'camera_scope':'active pG->Cam','pose':{'camera_param':[0,0,0,0,0,-1,0,50],'camera_view':[1,0,0,0,0,1,0,0,0,0,1,0],'camera_projection':q}}
  self.assertTrue(camera_valid(row)[0]);row['pose']['camera_projection']=[0.0]*16;self.assertFalse(camera_valid(row)[0])
 def test_partial_loop_count_and_cache_units(self):
  full='PT f=241-300 n=60 Player=5/9 ObjMgr.move=4/7 CameraMove=6/8 cpu=20/30 rotcache=99/2'
  r=phases(full)[0];self.assertTrue(r['freeplay_loop_complete']);self.assertEqual(r['fields']['rotcache']['hits'],99);self.assertNotIn('mean_us',r['fields']['rotcache'])
  self.assertFalse(phases(full.replace('CameraMove=6/8','CameraMove=6/8/59'))[0]['freeplay_loop_complete'])
if __name__=='__main__':unittest.main()
