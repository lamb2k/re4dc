import unittest,tempfile
from pathlib import Path
import prepare as p
class Controls(unittest.TestCase):
 def test_target_completeness_and_order(self):
  actual=[(0,(0,1,2)),(1,(2,1,3)),(2,(3,3,3))]
  p.check_inventory(actual,list(actual))
  for bad in (actual[:-1],actual[::-1],actual+actual[:1]):
   with self.assertRaises(ValueError):p.check_inventory(actual,bad)
 def test_distinct_actual_adjacent_panel(self):
  fs={8:(18,19,20),12:(20,19,24),13:(25,24,19),14:(24,25,26)}
  out,miss=p.panels(fs,dict.fromkeys(fs,True));self.assertEqual(miss,[])
  self.assertEqual(out[8],(8,12,(18,19,20,20,19,24)))
  self.assertEqual(out[12][0:2],(8,12))
  self.assertEqual(p.panels({8:fs[8]}, {8:True}),({},[8]))
  self.assertEqual(p.panels({8:fs[8],9:fs[8]},{8:True,9:True}),({},[8,9]))
  self.assertEqual(p.panels({8:fs[8],12:(19,20,24)},{8:True,12:True}),({},[8,12]))
 def test_degenerate_buddy_refused(self):
  self.assertEqual(p.panels({1:(0,1,2),2:(2,1,3)},{1:True,2:False}),({},[1,2]))
 def test_physical_id_not_coordinate_alias(self):
  a=(1,1,2,3,4,0,1,2,2,1,3);b=(2,2,2,3,4,0,1,2,2,1,3)
  ids=p.id_atlas([b,a,a]);self.assertEqual(len(ids),2);self.assertNotEqual(ids[a],ids[b]);self.assertEqual(ids,p.id_atlas([a,b]))
 def test_complete_component_not_hit_subset(self):
  xyz=((0,0,0),(1,0,0),(0,1,0),(1,1,0),(10,0,0),(11,0,0),(10,1,0))
  actual=[(0,1,2),(2,1,3),(4,5,6)]
  rows=[[0,0,1,2],[1,2,1,3]]
  self.assertEqual(len(p.validate_component(actual,xyz,rows)),2)
  for bad in (rows[:1],rows+[[2,4,5,6]],[[0,0,2,1],rows[1]],rows+rows[:1]):
   with self.assertRaises(ValueError):p.validate_component(actual,xyz,bad)
 def test_prefix_and_self_refuse(self):
  t=dict(placement=10,cluster=5)
  p.prefix_guard(dict(placement=9,cluster=5),t)
  for source in (dict(placement=10,cluster=4),dict(placement=11,cluster=4),dict(placement=10,cluster=5)):
   with self.assertRaises(ValueError):p.prefix_guard(source,t)
 def test_pinned_input_mutation_refused(self):
  with tempfile.TemporaryDirectory(dir='/dev/shm') as temp:
   f=Path(temp)/'copied-header';f.write_bytes(b'authenticated copied header')
   expected=p.pin(f);p.require(f,expected);f.write_bytes(b'authenticated copied headeR')
   with self.assertRaises(ValueError):p.require(f,expected)
   f.write_bytes(b'authenticated copied header'+b'X')
   with self.assertRaises(ValueError):p.require(f,expected)
 def test_actual_level_identity(self):
  a=dict(placement=1,field=1,part=2,cluster=3,level=0,meshlet=4);b=dict(a,level=1)
  self.assertNotEqual(p.physical(a),p.physical(b))
 def test_finite_work_no_short_zip(self):
  q=p.precount(44,27);self.assertEqual(q['edge_determinants_upper'],72*44*27*129*3);self.assertEqual(q['primitive_calls_upper'],44*27*387)
if __name__=='__main__':unittest.main()
