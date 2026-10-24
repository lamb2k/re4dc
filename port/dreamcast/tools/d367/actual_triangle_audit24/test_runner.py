"""Public synthetic runner controls; never execute private geometry predicates."""
import dataclasses,json,tempfile,unittest
from fractions import Fraction as Q
from pathlib import Path
from types import SimpleNamespace
import runner as r
class Clock:
 def __init__(self):self.now=0
 def __call__(self):return self.now
class Controls(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.temp=tempfile.TemporaryDirectory(dir='/dev/shm');cls.oracle=r.frozen_oracle(Path(__file__).resolve().parents[5],Path(cls.temp.name))
 @classmethod
 def tearDownClass(cls):cls.temp.cleanup()
 def case(self,n=2,sources=None):
  t=((Q(-1),Q(-1),Q(0)),(Q(1),Q(-1),Q(0)),(Q(0),Q(1),Q(0)))
  source=((Q(-10),Q(-10),Q(2)),(Q(10),Q(-10),Q(2)),(Q(0),Q(10),Q(2)))
  buddy=(source[1],source[0],(Q(0),Q(-20),Q(2)))
  c=r.Candidate((1,1,1,1,0,1,0),1,(1,1,1,1,1,0,1,2,1,0,3),(source,buddy),0)
  ts=tuple(t for _ in range(n));return r.Case((0,),ts,n,r.inventory_sha(ts),(c,) if sources is None else sources,((Q(-1),Q(-1),Q(4)),(Q(1),Q(1),Q(6))))
 def budget(self,**kw):return r.Budget(clock=Clock(),**kw)
 def proxy(self,cover=None,assigned=None):
  o=self.oracle;return SimpleNamespace(Unknown=o.Unknown,TriangleProof=o.TriangleProof,AssignedProof=o.AssignedProof,Panel=o.Panel,SourceFace=o.SourceFace,eye_box=o.eye_box,cover_triangle=cover or o.cover_triangle,cover_assigned=assigned or o.cover_assigned)
 def test_real_generic_complete_positive(self):
  b=self.budget();answer=r.solve(self.case(),b,self.oracle)
  self.assertEqual(answer['status'],'NOMINAL_EXACT_REAL_CANDIDATE_ONLY');self.assertEqual(answer['complete_target_triangles'],2);self.assertEqual(len(answer['assignments']),2);self.assertEqual(answer['dependencies'],(1,));self.assertEqual((b.candidate_used,b.final_used,b.final_invocations),(2,2,1))
 def test_wholecase_pre_reservation_not_early_exit_guess(self):
  case=self.case(sources=self.case().sources*2);seen=[]
  oracle=self.proxy(cover=lambda *a:seen.append(a))
  b=self.budget(candidate=3);answer=r.solve(case,b,oracle)
  self.assertEqual(answer['status'],'UNTESTED_UNKNOWN_BUDGET');self.assertEqual(seen,[]);self.assertEqual(b.candidate_used,0)
 def test_target_degenerate_retained_as_complete_geometry(self):
  case=self.case();point=(Q(0),Q(0),Q(0));tris=(case.triangles[0],(point,point,point));case=dataclasses.replace(case,triangles=tris,expected_inventory=r.inventory_sha(tris))
  answer=r.solve(case,self.budget(),self.oracle);self.assertEqual(answer['status'],'NOMINAL_EXACT_REAL_CANDIDATE_ONLY');self.assertEqual(len(answer['assignments']),2)
 def test_float_source_cannot_grant_positive(self):
  case=self.case();source=case.sources[0];faces=tuple(tuple(tuple(float(v) for v in p) for p in t) for t in source.panel_faces);bad=dataclasses.replace(source,panel_faces=faces)
  answer=r.solve(dataclasses.replace(case,sources=(bad,)),self.budget(),self.oracle);self.assertEqual(answer['status'],'UNKNOWN_NO_FIXED_SOURCE');self.assertIn('NON_RATIONAL',answer['refusals'])
 def test_full_final_reserve_before_candidates(self):
  b=self.budget(final=1);answer=r.solve(self.case(),b,self.oracle)
  self.assertEqual(answer['status'],'UNTESTED_UNKNOWN_BUDGET');self.assertEqual(b.candidate_used,0)
 def test_complete_inventory_mutations_before_predicate(self):
  case=self.case();seen=[];oracle=self.proxy(cover=lambda *a:seen.append(a))
  altered=(dataclasses.replace(case,triangles=case.triangles[:-1]),dataclasses.replace(case,triangles=case.triangles+(case.triangles[0],)),dataclasses.replace(case,triangles=(case.triangles[0],tuple(reversed(case.triangles[1])))))
  for bad in altered:
   with self.assertRaises(ValueError):r.solve(bad,self.budget(),oracle)
  self.assertEqual(seen,[])
 def test_failure_after_earlier_triangle_success_no_partial_positive(self):
  n=[0]
  def cover(*args):
   n[0]+=1
   return self.oracle.cover_triangle(*args) if n[0]==1 else self.oracle.Unknown('EDGE_VOLUME')
  answer=r.solve(self.case(),self.budget(),self.proxy(cover=cover))
  self.assertEqual(answer['status'],'UNKNOWN_NO_FIXED_SOURCE');self.assertEqual(answer['first_uncovered_target_ordinal'],1);self.assertNotIn('assignments',answer)
 def test_final_helper_refusal_not_positive(self):
  answer=r.solve(self.case(),self.budget(),self.proxy(assigned=lambda *a:self.oracle.Unknown('PANEL_LIMIT')))
  self.assertEqual(answer['status'],'UNKNOWN_FINAL_PANEL_LIMIT');self.assertNotIn('assignments',answer)
 def test_interruption_discards_current_case_and_stops_remaining(self):
  clock=Clock();b=r.Budget(clock=clock,deadline=10);n=[0]
  def cover(*args):
   n[0]+=1
   if n[0]==3:clock.now=10
   return self.oracle.cover_triangle(*args)
  rows=r.execute((self.case(),self.case(),self.case()),b,self.proxy(cover=cover))
  self.assertEqual([x['status'] for x in rows],['NOMINAL_EXACT_REAL_CANDIDATE_ONLY','UNKNOWN_WALL_BUDGET','UNKNOWN_WALL_BUDGET']);self.assertTrue(rows[1]['partial_assignment_discarded']);self.assertFalse(rows[2]['started']);self.assertNotIn('assignments',rows[1]);self.assertEqual(b.final_used,2)
 def test_budget_halt_no_later_small_case_packing(self):
  b=self.budget(candidate=1);rows=r.execute((self.case(),self.case(n=1)),b,self.oracle)
  self.assertEqual([x['status'] for x in rows],['UNTESTED_UNKNOWN_BUDGET']*2);self.assertEqual(b.candidate_used,0)
 def test_unused_reservation_released_only_after_whole_case(self):
  case=self.case(sources=self.case().sources*2);b=self.budget(candidate=4)
  answer=r.solve(case,b,self.proxy(cover=lambda *a:self.oracle.Unknown('TARGET_DEPTH')))
  self.assertEqual(answer['status'],'UNKNOWN_NO_FIXED_SOURCE');self.assertEqual(b.candidate_used,2);self.assertIsNone(b.active)
  answer=r.solve(self.case(n=1),b,self.oracle);self.assertEqual(answer['status'],'NOMINAL_EXACT_REAL_CANDIDATE_ONLY')
 def test_unrepresentable_source_is_explicit_unknown(self):
  source=r.Candidate((1,1,1,1,0,1,0),None,None,None,None,'UNKNOWN_UNREPRESENTABLE_PANEL');b=self.budget();answer=r.solve(self.case(sources=(source,)),b,self.oracle)
  self.assertEqual(answer['status'],'UNKNOWN_NO_FIXED_SOURCE');self.assertEqual(answer['refusals'],{'UNKNOWN_UNREPRESENTABLE_PANEL':1});self.assertEqual(b.candidate_used,0)
 def test_seventeen_actual_dependencies_refused_no_backtracking(self):
  ts=tuple(((Q(i),Q(0),Q(0)),(Q(i+1),Q(0),Q(0)),(Q(i),Q(1),Q(0))) for i in range(17));cs=[]
  for i,t in enumerate(ts):cs.append(r.Candidate((i,),i+1,(i,), (t,t),0))
  c=dataclasses.replace(self.case(),triangles=ts,expected_count=17,expected_inventory=r.inventory_sha(ts),sources=tuple(cs))
  def cover(eyes,source,target):return self.oracle.TriangleProof(1,24,Q(1),Q(1),Q(1)) if source==target else self.oracle.Unknown('EDGE_VOLUME')
  answer=r.solve(c,self.budget(),self.proxy(cover=cover));self.assertEqual(answer['status'],'UNKNOWN_PANEL_CAP');self.assertEqual(answer['first_excess_target_ordinal'],16);self.assertNotIn('assignments',answer)
 def test_mutated_prepared_pin_refused_before_binding(self):
  with tempfile.TemporaryDirectory(dir='/dev/shm') as tmp:
   p=Path(tmp)/'report.json';p.write_text('{}');s=Path(tmp)/'SEAL.json';s.write_text('{}')
   with self.assertRaises(ValueError):r.bind(p,s)
 def test_candidate_and_final_accounting_caps(self):
  b=self.budget(candidate=1,final=1);self.assertTrue(b.reserve(1,1));b.candidate();b.final(1)
  with self.assertRaises(ValueError):b.candidate()
  with self.assertRaises(ValueError):b.final(1)
  self.assertEqual(b.receipt()['candidate_edge_upper'],72);self.assertEqual(b.receipt()['final_edge_upper'],72)
if __name__=='__main__':unittest.main()
