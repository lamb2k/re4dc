import unittest
from lod_alias_audit import minimum_alias_cover
class CoverTests(unittest.TestCase):
 def test_exact_alias_level_cover(self):
  self.assertEqual(minimum_alias_cover([1,2,4],3),(0,1,2))
  self.assertEqual(minimum_alias_cover([1,2,3],2),(2,))
  self.assertEqual(minimum_alias_cover([3,6,1],3),(0,1))
  self.assertIsNone(minimum_alias_cover([1,2],3))
 def test_invalid_masks(self):
  for args in (([],0),([0],1),([4],2),([-1],2)):
   with self.assertRaises(ValueError):minimum_alias_cover(*args)
if __name__=='__main__':unittest.main()
