"""Actual-edge union controls without private assets or renderer claims."""
import unittest
from fractions import Fraction as Q
from exact_shadow import prove
from exact_union import boundary,prove_union

class UnionTests(unittest.TestCase):
 vertices={0:(-20,-20,0),1:(20,-20,0),2:(20,20,0),3:(-20,20,0)}
 triangles=((0,1,2),(0,2,3))
 eye=((-1,-1,10),(1,1,12));target=((-5,-5,-12),(5,5,-10))
 def run_union(self,vertices=None,triangles=None,**kwargs):return prove_union(self.vertices if vertices is None else vertices,self.triangles if triangles is None else triangles,self.eye,self.target,**kwargs)
 def test_actual_square_union_covers_internal_diagonal(self):
  for t in self.triangles:self.assertFalse(prove(tuple(self.vertices[i] for i in t),self.eye,self.target)['proven'])
  p=self.run_union();self.assertTrue(p['proven']);self.assertEqual(set(p['shared_indices']),{0,2})
  reversed_ts=tuple(tuple(reversed(t)) for t in self.triangles);self.assertTrue(self.run_union(triangles=reversed_ts)['proven'])
 def test_nonplanar_real_pair(self):
  vertices=dict(self.vertices);vertices[3]=(-20,20,1)
  self.assertTrue(self.run_union(vertices=vertices)['proven'])
  for t in self.triangles:self.assertFalse(prove(tuple(vertices[i] for i in t),self.eye,self.target)['proven'])
 def test_missing_reversed_or_copied_edge(self):
  cases=(((0,1,2),(0,3,2)),((0,1,2),(0,4,3)),((0,1,2),(4,5,6)),((0,1,2),(0,1,2)))
  copied=dict(self.vertices,**{})
  copied.update({4:self.vertices[0],5:self.vertices[2],6:self.vertices[3]})
  for ts in cases:self.assertFalse(self.run_union(vertices=copied,triangles=ts)['proven'])
 def test_concave_folded_chart_and_planes(self):
  vertices=dict(self.vertices);vertices[3]=(0,0,0)
  self.assertFalse(self.run_union(vertices=vertices)['proven'])
  vertices[3]=(-20,20,12)
  self.assertEqual(self.run_union(vertices=vertices)['reason'],'chart_unknown')
  vertices[3]=(-30,-25,0)
  self.assertEqual(self.run_union(vertices=vertices)['reason'],'convexity_unknown')
  vertices[3]=(40,-20,0)
  self.assertFalse(self.run_union(vertices=vertices)['proven'])
  self.assertFalse(prove_union(self.vertices,self.triangles,((-1,-1,-1),(1,1,1)),self.target)['proven'])
  self.assertFalse(prove_union(self.vertices,self.triangles,self.eye,((-1,-1,-1),(1,1,1)))['proven'])
 def test_both_actual_planes_are_required(self):
  vertices=dict(self.vertices);vertices[3]=(-20,20,-15)
  eye=((0,0,10),)*2;target=((-10,10,-5),)*2
  result=prove_union(vertices,self.triangles,eye,target)
  self.assertFalse(result['proven']);self.assertEqual(result['reason'],'plane_unknown')
 def test_strict_outer_edge_and_hole_fill_refused(self):
  self.assertFalse(prove_union(self.vertices,self.triangles,((0,-20,10),)*2,((0,-20,-10),)*2)['proven'])
  # Four outer corners cannot justify filling an absent shared diagonal/source.
  self.assertFalse(self.run_union(triangles=((0,1,2),(4,5,6)))['proven'])
 def test_uncertainty_positive_and_ambiguity(self):
  vertices={i:tuple(x*1000 for x in p) for i,p in self.vertices.items()};eye=((-100,-100,10000),(100,100,12000));target=((-500,-500,-12000),(500,500,-10000))
  self.assertTrue(prove_union(vertices,self.triangles,eye,target,vertex_error=32,eye_error=32,target_error=32,eye_clearance=2000,target_clearance=32)['proven'])
  self.assertFalse(self.run_union(vertex_error=32)['proven'])
  self.assertFalse(self.run_union(eye_error=20)['proven'])
  with self.assertRaises(ValueError):self.run_union(vertex_error=-1)
 def test_correlated_shared_endpoint_choices(self):
  for delta in (Q(-1,10),Q(1,10)):
   vertices=dict(self.vertices);vertices[0]=tuple(Q(x)+delta for x in vertices[0]);vertices[2]=tuple(Q(x)-delta for x in vertices[2])
   self.assertTrue(self.run_union(vertices=vertices)['proven'])
  self.assertTrue(self.run_union(vertex_error=Q(1,10))['proven'])

if __name__=='__main__':unittest.main()
