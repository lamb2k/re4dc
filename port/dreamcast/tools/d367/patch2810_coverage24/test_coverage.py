import unittest
from fractions import Fraction as Q
from coverage import independent_disk,plane_audit,normal,det3,boxcorners,scalar
class IndependentControls(unittest.TestCase):
 def test_shared_edge_disk_and_winding(self):
  self.assertEqual(independent_disk(((0,1,2),(2,1,3)))['boundary'],[0,1,3,2])
  with self.assertRaisesRegex(ValueError,'winding'):independent_disk(((0,1,2),(1,2,3)))
 def test_disconnected_and_duplicate_refuse(self):
  for faces in (((0,1,2),(3,4,5)),((0,1,2),(0,1,2))):
   with self.assertRaises(ValueError):independent_disk(faces)
 def test_plane_support_equals_all_exact_corners(self):
  v={0:(Q(0),Q(-1),Q(-1)),1:(Q(0),Q(1),Q(-1)),2:(Q(0),Q(-1),Q(1))};eye=((-4,-2,-2),(-3,2,2));target=((3,-1,-1),(4,1,1));planes,signs=plane_audit(v,((0,1,2),),eye,target)
  self.assertEqual(signs,[-1]);n=normal(*(v[i] for i in (0,1,2)));d=-scalar(n,v[0])
  for box,key in ((eye,'eye_range'),(target,'target_range')):
   vals=[scalar(n,p)+d for p in boxcorners(box)];self.assertEqual(planes[0][key],[str(min(vals)),str(max(vals))])
 def test_touching_plane_refuses(self):
  v={0:(0,-1,-1),1:(0,1,-1),2:(0,-1,1)};_,signs=plane_audit(v,((0,1,2),),((-1,-1,-1),(0,1,1)),((1,-1,-1),(2,1,1)));self.assertEqual(signs,[])
 def test_native_odd_rotation_preserves_exact_normal(self):
  a=(Q(1,3),Q(2,5),Q(3,7));b=(Q(4,9),Q(5,11),Q(6,13));c=(Q(7,15),Q(8,17),Q(9,19))
  self.assertEqual(normal(b,a,c),normal(c,b,a));self.assertNotEqual(normal(a,b,c),normal(c,b,a))
 def test_determinant_known_and_singular(self):
  self.assertEqual(det3((1,0,0),(0,2,0),(0,0,3)),6);self.assertEqual(det3((1,2,3),(1,2,3),(0,0,1)),0)
if __name__=='__main__':unittest.main()
