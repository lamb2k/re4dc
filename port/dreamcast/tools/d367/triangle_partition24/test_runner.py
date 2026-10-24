"""Public-only runner controls; no actual private coverage predicates."""
import contextlib,dataclasses,hashlib,io,json,subprocess,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import partition as p
import prepare_private as prep
import runner as r
import test_partition as public
class RunnerControls(unittest.TestCase):
 @classmethod
 def setUpClass(cls):public.Controls.setUpClass();cls.helper=public.Controls();cls.base=public.Controls.o
 @classmethod
 def tearDownClass(cls):public.Controls.tearDownClass()
 def case(self,parents=1,sources=None):
  inv=self.helper.inventory((self.helper.inventory().parents[0].vertices,)*parents);children=p.canonical_partition(inv)
  if sources is None:sources=(r.Source((1,0),p.FixedFace(self.helper.broad(),0)),)
  c=r.Case((0,'PUBLIC'),inv,children,tuple(sources),((0,0,0),(0,0,0)),'');return dataclasses.replace(c,expected_fingerprint=prep.token(r.record(c)))
 def budget(self,caps=prep.CAPS,clock=lambda:0):return r.Budget(caps,clock,100)
 def test_actual_public_generic_all_parents_children_final_pass(self):
  case=self.case(2);oracle=r.Oracle(self.base);budget=self.budget();rows=r.execute((case,),budget,p,oracle)
  self.assertEqual(rows[0]['status'],'NOMINAL_EXACT_REAL_OPPORTUNITY_ONLY');self.assertEqual(rows[0]['original_parent_occurrences'],2);self.assertEqual(rows[0]['complete_children'],8);self.assertEqual(len(rows[0]['assignments']),8);self.assertEqual(oracle.triangle_calls,8);self.assertEqual(oracle.assigned_calls,1);self.assertEqual(budget.used,(8,576,8,576));self.assertIsNone(budget.active)
 def test_atomic_caps_and_refund_only_after_case(self):
  row=dict(original_parents=2,canonical_children=8,source_faces=3,whole_case_candidate_calls_reserve=24,candidate_edge_upper_reserve=1728,whole_case_final_child_calls_reserve=8,final_edge_upper_reserve=576)
  values=prep.reservation(row)
  for i in range(4):
   budget=self.budget(tuple(v-(j==i) for j,v in enumerate(values)));self.assertFalse(budget.reserve(row));self.assertIsNone(budget.active);self.assertEqual(budget.used,(0,0,0,0))
  budget=self.budget(values);self.assertTrue(budget.reserve(row));budget.candidate()
  with self.assertRaisesRegex(ValueError,'refund only after case'):budget.reserve(row)
  self.assertEqual(budget.active[0],values);self.assertEqual(budget.active[1],(1,72,0,0));budget.close();self.assertEqual(budget.used,(1,72,0,0));self.assertFalse(budget.reserve(row))
  smaller=dict(original_parents=1,canonical_children=4,source_faces=3,whole_case_candidate_calls_reserve=12,candidate_edge_upper_reserve=864,whole_case_final_child_calls_reserve=4,final_edge_upper_reserve=288)
  self.assertTrue(budget.reserve(smaller));budget.close()
 def test_budget_refuses_whole_case_before_any_child(self):
  case=self.case();oracle=r.Oracle(self.base);budget=self.budget((3,288,4,288));row=r.execute((case,case),budget,p,oracle)
  self.assertTrue(all(x['status']=='UNTESTED_UNKNOWN_BUDGET' and not x['started'] for x in row));self.assertEqual(oracle.triangle_calls,0);self.assertEqual(oracle.assigned_calls,0)
 def test_last_child_failure_discards_whole_parent_and_no_final(self):
  case=self.case();calls=[0]
  def primitive(*args):
   calls[0]+=1
   return self.base.Unknown('PUBLIC_LAST_CHILD') if calls[0]==4 else self.base.cover_triangle(*args)
  oracle=SimpleNamespace(eye_box=self.base.eye_box,Unknown=self.base.Unknown,TriangleProof=self.base.TriangleProof,cover_triangle=primitive)
  budget=self.budget();row=r.execute((case,),budget,p,oracle)[0]
  self.assertEqual(row['status'],'UNKNOWN_NO_FIXED_SOURCE');self.assertEqual(row['first_uncovered_child'],3);self.assertTrue(row['partial_assignment_discarded']);self.assertNotIn('assignments',row);self.assertEqual(budget.used[2],0);self.assertIsNone(budget.active)
 def test_missing_child_or_parent_never_enters_predicates(self):
  case=self.case(2);oracle=r.Oracle(self.base)
  mutants=[dataclasses.replace(case,children=case.children[:-1]),dataclasses.replace(case,inventory=dataclasses.replace(case.inventory,parents=case.inventory.parents[:-1]))]
  for mutant in mutants:
   mutant=dataclasses.replace(mutant,expected_fingerprint=prep.token(r.record(mutant)))
   with self.assertRaises(ValueError):r.execute((mutant,),self.budget(),p,oracle)
  self.assertEqual(oracle.triangle_calls,0)
 def test_global17_panels_across_parents_never_finalizes(self):
  sources=tuple(r.Source((i,0),p.FixedFace(self.helper.broad(i),0)) for i in range(1,18));case=self.case(5,sources);cursor=[0,0]
  def choose(*args):
   cursor[1]+=1
   if cursor[1]!=cursor[0]+1:return self.base.Unknown('PUBLIC_GREEDY_CHOICE')
   cursor[0]+=1;cursor[1]=0;return self.base.cover_triangle(*args)
  oracle=SimpleNamespace(eye_box=self.base.eye_box,Unknown=self.base.Unknown,TriangleProof=self.base.TriangleProof,cover_triangle=choose)
  budget=self.budget();row=r.execute((case,),budget,p,oracle)[0]
  self.assertEqual(row['status'],'UNKNOWN_GLOBAL_PANEL_CAP');self.assertEqual(row['first_excess_child'],16);self.assertEqual(budget.used[2],0);self.assertNotIn('assignments',row)
 def test_incomplete_final_backend_and_wrapper_cannot_be_positive(self):
  case=self.case()
  def incomplete(*args):
   answer=self.base.cover_assigned(*args);return dataclasses.replace(answer,assignments=answer.assignments[:-1])
  base=SimpleNamespace(eye_box=self.base.eye_box,Unknown=self.base.Unknown,TriangleProof=self.base.TriangleProof,AssignedProof=self.base.AssignedProof,SourceFace=self.base.SourceFace,Panel=self.base.Panel,cover_triangle=self.base.cover_triangle,cover_assigned=incomplete)
  row=r.execute((case,),self.budget(),p,r.Oracle(base))[0];self.assertEqual(row['status'],'UNKNOWN_FINAL_INCOMPLETE_BASE_RESULT')
  real=p.cover_partition
  def corrupt(*args):return dataclasses.replace(real(*args),child_count=3)
  with patch.object(p,'cover_partition',side_effect=corrupt):self.assertEqual(r.execute((case,),self.budget(),p,r.Oracle(self.base))[0]['status'],'UNKNOWN_FINAL_INCOMPLETE_RESULT')
 def test_interruption_and_allocation_preserve_no_partial_positive(self):
  case=self.case();clock=[0];budget=self.budget(clock=lambda:clock[0])
  def interrupt(*args):clock[0]=100;return self.base.cover_triangle(*args)
  base=SimpleNamespace(eye_box=self.base.eye_box,Unknown=self.base.Unknown,TriangleProof=self.base.TriangleProof,cover_triangle=interrupt)
  rows=r.execute((case,case),budget,p,base);self.assertEqual(rows[0]['status'],'UNKNOWN_WALL_BUDGET');self.assertFalse(rows[1]['started']);self.assertEqual(budget.used[0],1);self.assertIsNone(budget.active)
  for error in (MemoryError,OverflowError):
   with patch.object(self.base,'cover_triangle',side_effect=error):
    row=r.execute((case,),self.budget(),p,r.Oracle(self.base))[0];self.assertEqual(row['status'],'UNKNOWN_MEMORY_ALLOCATION');self.assertNotIn('assignments',row)
 def test_source_eye_and_original_input_drift_refused_before_calls(self):
  case=self.case();oracle=r.Oracle(self.base)
  for mutant in (dataclasses.replace(case,eye_box=((0,0,0),(1,1,1))),dataclasses.replace(case,sources=(dataclasses.replace(case.sources[0],key=(99,0)),))):
   with self.assertRaisesRegex(ValueError,'drift'):r.execute((mutant,),self.budget(),p,oracle)
  self.assertEqual(oracle.triangle_calls,0)
  with tempfile.TemporaryDirectory(dir='/dev/shm') as temp:
   path=Path(temp)/'input';path.write_text('public source/profile/camera');sha=r.pin(path)['sha256'];r.require(path,sha);path.write_text('changed')
   with self.assertRaisesRegex(ValueError,'Frozen input changed'):r.require(path,sha)
 def test_grant_binds_root_source_review_plan_cases_caps_and_output(self):
  cases=(self.case(),);source='a'*40
  with tempfile.TemporaryDirectory(dir='/dev/shm') as temp:
   folder=Path(temp);review=folder/'review';review.write_text('Public independent review');reviewsha=r.pin(review)['sha256'];out=folder/'output';grant=folder/'grant'
   valid=r.grant_binding(source,reviewsha,cases,out)
   def write(d):grant.write_text(json.dumps(d));return r.pin(grant)['sha256']
   sha=write(valid);self.assertEqual(r.authorize(grant,sha,review,reviewsha,source,cases,out)['grant']['sha256'],sha)
   with self.assertRaises(ValueError):r.authorize(None,None,review,reviewsha,source,cases,out)
   for key,value in (('issuer','/author'),('approved',False),('runner_source','b'*40),('review_sha256','0'*64),('plan_sha256','0'*64),('cases_sha256','0'*64),('output',str(folder/'different')),('limits',dict(r.LIMITS,candidate_calls=100001))):
    mutant=dict(valid);mutant[key]=value;sha=write(mutant)
    with self.subTest(key=key),self.assertRaises(ValueError):r.authorize(grant,sha,review,reviewsha,source,cases,out)
 def test_default_cli_and_missing_grant_make_zero_oracle_calls(self):
  case=self.case()
  with tempfile.TemporaryDirectory(dir='/dev/shm') as temp:
   folder=Path(temp);preserved=folder/'preserved';preserved.mkdir();(preserved/'report.json').write_text('Public synthetic preparation');(preserved/'PREPARATION-SEAL.json').write_text('Public synthetic seal');common=['runner.py','--repo',str(folder/'repo'),'--prepared-directory',str(folder/'preserved'),'--expected-source','a'*40]
   with patch.object(r,'own_sources',return_value={}),patch.object(r,'bind',return_value=({},(case,),p,{})),patch.object(prep,'load',side_effect=AssertionError('No oracle load authorized')),contextlib.redirect_stdout(io.StringIO()):
    out=folder/'default'
    with patch.object(sys,'argv',common+['--out',str(out)]):r.main()
    result=json.loads((out/'report.json').read_text());self.assertEqual(result['private_candidate_triangle_calls'],0);self.assertEqual(result['private_final_assigned_batch_calls'],0);self.assertEqual(result['results'][0]['status'],'UNTESTED_UNKNOWN')
    denied=folder/'denied'
    with patch.object(sys,'argv',common+['--out',str(denied),'--execute']),self.assertRaisesRegex(ValueError,'separately pinned root grant'):r.main()
    self.assertFalse(denied.exists())
 def test_default_branch_cannot_load_oracle_without_authorization(self):
  import ast
  tree=ast.parse(Path(r.__file__).read_text());main=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='main');branch=next(x for x in ast.walk(main) if isinstance(x,ast.If) and isinstance(x.test,ast.Attribute) and x.test.attr=='execute')
  calls=[x for x in branch.body if isinstance(x,ast.Assign)];self.assertTrue(calls)
  self.assertIsInstance(branch.body[0],ast.Assign);self.assertEqual(branch.body[0].value.func.id,'authorize')
  self.assertTrue(any(isinstance(x,ast.Call) and isinstance(x.func,ast.Name) and x.func.id=='execute' for x in ast.walk(branch)))
if __name__=='__main__':unittest.main()
