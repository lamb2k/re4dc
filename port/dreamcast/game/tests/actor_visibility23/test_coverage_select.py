"""Exact geometric controls with synthetic authored panels; no game data."""
from fractions import Fraction as F
import copy,unittest
from coverage_select import exact_sources,protected_rect,certify,select_dependencies,check_frontside_and_slab,bind_quantized_identity,validate_lod_coverage

def tri(a,b,c):return[(a[0],a[1],0),(b[0],b[1],0),(c[0],c[1],0)]
def rectangle(l,b,rr,t):return[tri((l,b),(rr,b),(rr,t)),tri((l,b),(rr,t),(l,t))]
def panel(l=2,b=2,rr=8,t=8):return dict(corners=[[l,b,0],[rr,b,0],[rr,t,0],[l,t,0]],half=1,frontside_eye_box=[-20,20,-20,20,101,200])

class SelectionTests(unittest.TestCase):
 def test_removes_extras_without_changing_original_ids_or_panel(self):
  outside=rectangle(40,40,50,50);wall=[tri((0,0),(10,0),(5,5)),tri((10,0),(10,10),(5,5)),tri((10,10),(0,10),(5,5)),tri((0,10),(0,0),(5,5))]
  sources=outside[:1]+wall+outside[1:];panels=[panel()];before=copy.deepcopy((sources,panels));proof=select_dependencies(sources,panels,1)
  self.assertEqual(proof['selected_dependency_ids'],[1,2,3,4]);self.assertEqual(proof['required_coverage_mask'],0x1e);self.assertEqual((sources,panels),before)
  self.assertTrue(proof['valid']);self.assertTrue(proof['deletion_irredundant_under_validator']);self.assertTrue(all(not p['exact_remaining_polygons']and not p['unmatched_edges_touching_expanded_panel']for p in proof['panels']))
 def test_selection_is_stable_and_retained_triangles_are_indispensable(self):
  wall=rectangle(0,0,10,10);sources=wall+wall;panels=[panel()];a=select_dependencies(sources,panels,1);self.assertEqual(a,select_dependencies(sources,panels,1));self.assertEqual(a['selected_dependency_ids'],[0,1,2,3]);self.assertTrue(certify(exact_sources(sources),[2,3],panels,1)['valid'])
  exact=exact_sources(sources)
  for index in a['selected_dependency_ids']:self.assertFalse(certify(exact,[i for i in a['selected_dependency_ids']if i!=index],panels,1)['valid'])
 def test_whole_expanded_panel_required_not_only_inset_or_samples(self):
  sources=rectangle(2,2,8,8)
  with self.assertRaises(ValueError):select_dependencies(sources,[panel()],1)
  # A rational slit far thinner than a sampling grid still leaves uncovered area.
  sources=rectangle(0,0,F(5),10)+rectangle(F(5)+F(1,10**9),0,10,10)
  with self.assertRaises(ValueError):select_dependencies(sources,[panel()],1)
 def test_every_panel_must_remain_covered(self):
  sources=rectangle(0,0,10,10)+rectangle(20,20,30,30);panels=[panel(),panel(22,22,28,28)]
  self.assertEqual(select_dependencies(sources,panels,1)['selected_dependency_ids'],[0,1,2,3])
  with self.assertRaises(ValueError):select_dependencies(sources[:2],panels,1)
 def test_t_junction_unmatched_boundary_refuses_even_with_complete_union(self):
  sources=rectangle(0,0,5,10)+rectangle(5,0,10,5)+rectangle(5,5,10,10)
  proof=certify(exact_sources(sources),list(range(len(sources))),[panel()],1)
  self.assertEqual(proof['panels'][0]['exact_remaining_polygons'],0);self.assertGreater(proof['panels'][0]['unmatched_edges_touching_expanded_panel'],0);self.assertFalse(proof['valid'])
  with self.assertRaises(ValueError):select_dependencies(sources,[panel()],1)
 def test_exact_frontside_all_eight_corners_and_unchanged_slab(self):
  sources=rectangle(0,0,10,10);panels=[panel()];proof=check_frontside_and_slab(sources,[0,1],panels,100);self.assertEqual(proof['exact_frontside_checks'],16)
  for kind in('back','distance','slab'):
   s=copy.deepcopy(sources);p=copy.deepcopy(panels)
   if kind=='back':s[0].reverse()
   elif kind=='distance':p[0]['frontside_eye_box'][4]=100
   else:s[0][0]=(0,0,2)
   with self.subTest(kind=kind),self.assertRaises(ValueError):check_frontside_and_slab(s,[0,1],p,100)
 def test_invalid_or_unsupported_geometric_inputs_fail_closed(self):
  for sources,panels,margin in(([],[panel()],1),(rectangle(0,0,10,10),[],1),(rectangle(0,0,10,10),[panel()],-1),([[(0,0),(1,0),(0,1)]],[panel()],1)):
   with self.assertRaises(ValueError):select_dependencies(sources,panels,margin)
  p=panel();p['corners'][1][2]=1
  with self.assertRaises(ValueError):protected_rect(p,1)
 def test_actual_dependency_contract_requires_shared_identity_and_every_lod(self):
  bindings={};point=(F(1),F(2),F(3));identity=(4,(5,6,7));bind_quantized_identity(bindings,point,identity);bind_quantized_identity(bindings,point,identity)
  for changed in((9,(5,6,7)),(4,(5,6,8))):
   with self.assertRaises(ValueError):bind_quantized_identity(bindings,point,changed)
  records=[dict(level=l,coverage_bit=b)for l in range(3)for b in(1,4)];self.assertEqual(validate_lod_coverage(records,0x12),[0x12]*3)
  for bad in(records[:-1],records+[dict(level=3,coverage_bit=1)],records+[dict(level=0,coverage_bit=2)]):
   with self.assertRaises(ValueError):validate_lod_coverage(bad,0x12)
if __name__=='__main__':unittest.main()
