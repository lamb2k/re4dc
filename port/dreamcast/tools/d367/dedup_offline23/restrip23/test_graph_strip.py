import unittest
from collections import Counter
from graph_strip import graph_partition,tie_risks,canonical,topology_bound
from ordered_strip import triangles
class GraphControls(unittest.TestCase):
 def setUp(self):self.c=[(i,i*i,0,i+100,i+200,65535) for i in range(256)]
 def test_reorder_without_rotation(self):
  old=[[0,1,2],[7,8,9],[2,1,3]]
  out=graph_partition(old,self.c)
  self.assertLess(sum(map(len,out)),sum(map(len,old)))
  self.assertEqual(Counter(triangles(old)),Counter(triangles(out)))
 def test_rotation_preserves_oriented_attributes(self):
  old=[[0,1,2],[3,2,1]];out=graph_partition(old,self.c,True)
  self.assertLess(sum(map(len,out)),sum(map(len,old)))
  self.assertEqual(Counter(canonical(t) for t in triangles(old)),Counter(canonical(t) for t in triangles(out)))
 def test_uv_seam_does_not_weld(self):
  self.c[4]=(2,4,0,999,202,65535);old=[[0,1,2],[4,1,3]]
  self.assertEqual(graph_partition(old,self.c,True),old)
  self.assertIn('attribute_seam',tie_risks(old,self.c))
 def test_duplicate_degenerate_overlap_guards(self):
  self.assertIn('duplicate_position_face',tie_risks([[0,1,2],[0,1,2]],self.c))
  self.assertIn('degenerate',tie_risks([[0,1,1]],self.c))
  c=[(0,0,0),(10,0,0),(0,10,0),(1,1,0),(2,1,0),(1,2,0)]
  self.assertIn('coplanar_positive_area_overlap',tie_risks([[0,1,2],[3,4,5]],c))
 def test_shared_edge_is_not_area_overlap(self):
  c=[(0,0,0),(10,0,0),(0,10,0),(10,10,0)]
  self.assertNotIn('coplanar_positive_area_overlap',tie_risks([[0,1,2],[2,1,3]],c))
 def test_optimistic_bound_disconnected_and_connected(self):
  c=self.c
  self.assertEqual(topology_bound([[0,1,2],[7,8,9]],c)['min_strips'],2)
  x=[[0,1,2],[2,1,3]]
  self.assertEqual(topology_bound(x,c)['min_corners'],4)
  self.assertLessEqual(topology_bound(x,c)['min_corners'],sum(map(len,graph_partition(x,c,True))))
 def test_optimistic_bound_seam_and_multiplicity(self):
  self.c[4]=(2,4,0,999,202,65535)
  self.assertEqual(topology_bound([[0,1,2],[4,1,3]],self.c)['min_strips'],2)
  self.assertEqual(topology_bound([[0,1,2],[0,1,2]],self.c)['triangles'],2)
 def test_maximum_strip_length_and_determinism(self):
  old=[[i,i+1,i+2] if not i&1 else [i+1,i,i+2] for i in range(254)]
  out=graph_partition(old,self.c,True)
  self.assertTrue(all(len(s)<=255 for s in out))
  self.assertEqual(out,graph_partition(old,self.c,True))
if __name__=='__main__':unittest.main()

