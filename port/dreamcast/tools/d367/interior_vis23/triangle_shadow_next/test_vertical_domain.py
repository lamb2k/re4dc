import unittest
from fractions import Fraction as Q
from vertical_domain import affine_row,intersect,quantized_band,solve,constraints
class VerticalTests(unittest.TestCase):
 def test_exact_open_linear_bounds(self):
  rows=[affine_row('lo',lambda y:3*y+2),affine_row('hi',lambda y:7-2*y),affine_row('constant',lambda y:Q(1))];r=intersect(rows)
  self.assertTrue(r['nonempty']);self.assertEqual((r['lower'],r['upper']),(Q(-2,3),Q(7,2)))
  self.assertFalse(intersect(rows+[affine_row('empty',lambda y:-y-5)])['nonempty'])
  self.assertFalse(intersect([affine_row('zero',lambda y:0)])['nonempty'])
 def test_signed_quantization_strict_endpoints(self):
  def interval(lo,hi):return dict(nonempty=True,lower=Q(lo),upper=Q(hi))
  r=quantized_band(interval(-200,400),61);self.assertEqual((r['ylo_units'],r['yhi_units']),(-1,3))
  self.assertFalse(quantized_band(interval(0,100),61)['representable'])
  self.assertFalse(quantized_band(interval(0,201),61)['representable'])
  r=quantized_band(interval(-201,401),61);self.assertEqual((r['ylo_units'],r['yhi_units']),(-2,4))
  self.assertFalse(quantized_band(dict(nonempty=False),0)['representable'])
 def test_public_square_continuous_band_oracle(self):
  v={0:(-20000,-20000,0),1:(20000,-20000,0),2:(20000,20000,0),3:(-20000,20000,0)};t=((0,1,2),(0,2,3));xz=((-1000,10000),(1000,12000));target=((-1000,-1000,-12000),(1000,1000,-10000))
  results=solve(v,t,xz,target,Q(61));positive=[r for r in results if r['quantized_band']['representable']]
  self.assertEqual(len(positive),1);self.assertTrue(positive[0]['nominal_band_oracle']['proven']);self.assertGreater(positive[0]['strict_minimum_at_band_endpoints'],0)
 def test_all_outer_halfspaces_define_exact_square_bound(self):
  v={0:(-20000,-20000,0),1:(20000,-20000,0),2:(20000,20000,0),3:(-20000,20000,0)};t=((0,1,2),(0,2,3))
  branches=[intersect(constraints(v,t,((-1000,10000),(1000,12000)),((-1000,-1000,-12000),(1000,1000,-10000)),sigma,sign)) for sigma in (1,-1) for sign in (1,-1)]
  good=[r for r in branches if r['nonempty']];self.assertEqual(len(good),1);self.assertEqual((good[0]['lower'],good[0]['upper']),(Q(-107500,3),Q(107500,3)))
 def test_nonaffine_refused(self):
  with self.assertRaises(ValueError):affine_row('square',lambda y:y*y)
if __name__=='__main__':unittest.main()
