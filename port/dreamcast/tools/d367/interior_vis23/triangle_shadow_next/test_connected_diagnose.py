import unittest
from fractions import Fraction as Q
from connected_diagnose import closed_ray_hit
class RayTests(unittest.TestCase):
 def test_exact_closed_hit_and_negatives(self):
  t=((Q(-2),Q(-2),Q(0)),(Q(2),Q(-2),Q(0)),(Q(0),Q(2),Q(0)))
  self.assertIsNotNone(closed_ray_hit((0,0,10),(0,0,-10),t))
  self.assertIsNotNone(closed_ray_hit((0,0,10),(0,0,-10),t[::-1]))
  self.assertIsNone(closed_ray_hit((0,0,10),(0,0,1),t))
  self.assertIsNone(closed_ray_hit((0,0,10),(20,0,-10),t))
  self.assertIsNone(closed_ray_hit((0,0,10),(1,0,10),t))
  hit=closed_ray_hit((0,-2,10),(0,-2,-10),t);self.assertIsNotNone(hit);self.assertEqual(hit['ray_fraction'],'1/2')
if __name__=='__main__':unittest.main()
