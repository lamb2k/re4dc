import unittest
from ordered_strip import triangles,ordered_partition,grouped_partition
class ExactOrder(unittest.TestCase):
 def setUp(self):self.c=[(i,0,0,100+i,200+i,65535) for i in range(256)]
 def exact(self,old,new):
  f=lambda ss:[tuple(self.c[q] for q in t) for t in triangles(ss)]
  self.assertEqual(f(old),f(new))
 def test_packet_join_and_provoking(self):
  old=[[0,1,2],[2,1,3]];new=ordered_partition(old,self.c)
  self.assertEqual(new,[[0,1,2,3]]);self.exact(old,new)
 def test_longer_packet_join(self):
  old=[[0,1,2,3],[2,3,4,5]];new=ordered_partition(old,self.c)
  self.assertEqual(new,[[0,1,2,3,4,5]]);self.exact(old,new)
 def test_cyclic_rotation_not_admitted(self):
  old=[[0,1,2],[1,3,2]]
  self.assertEqual(ordered_partition(old,self.c),old)
 def test_uv_and_colour_seams(self):
  old=[[0,1,2],[4,1,3]]
  self.c[4]=(2,0,0,999,202,65535)
  self.assertEqual(ordered_partition(old,self.c),old)
  self.c[4]=(2,0,0,102,202,12345)
  self.assertEqual(ordered_partition(old,self.c),old)
 def test_exact_alias_can_join(self):
  self.c[4]=self.c[2];old=[[0,1,2],[4,1,3]]
  new=ordered_partition(old,self.c);self.assertEqual(len(new),1);self.exact(old,new)
 def test_group_and_transparent_boundaries(self):
  old=[[0,1,2],[2,1,3]]
  self.assertEqual(grouped_partition(old,self.c,[1,2])[0],old)
  self.assertEqual(ordered_partition(old,self.c,allow=False),old)
 def test_no_degenerate_removal(self):
  old=[[0,1,2,2],[2,2,3]]
  new=ordered_partition(old,self.c);self.exact(old,new)
  self.assertEqual(len(triangles(old)),len(triangles(new)))
 def test_length_and_local_index_limits(self):
  old=[list(range(254)),[252,253,254,255]]
  new=ordered_partition(old,self.c)
  self.assertTrue(all(3<=len(s)<=255 for s in new));self.exact(old,new)
  with self.assertRaises(ValueError):ordered_partition([[0,1,256]],self.c)
 def test_deterministic_and_never_grows(self):
  old=[[0,1,2],[2,1,3],[2,3,4],[4,3,5],[9,8,7]]
  a=ordered_partition(old,self.c);self.assertEqual(a,ordered_partition(old,self.c))
  self.assertLessEqual(sum(map(len,a)),sum(map(len,old)));self.exact(old,a)
if __name__=='__main__':unittest.main()

