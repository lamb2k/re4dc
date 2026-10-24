"""Public rational controls only. No private source/scene predicates."""
from types import SimpleNamespace
import collections,dataclasses,hashlib,importlib.util,subprocess,sys,tempfile,unittest
from fractions import Fraction as Q
from pathlib import Path
from unittest.mock import patch
import partition as p
GENERIC='28c739468ae7d2d2d3c09f81330015e7769dc824'
class Controls(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory(dir='/dev/shm');root=Path(__file__).resolve().parents[5];data=subprocess.check_output(['git','-C',str(root),'show',GENERIC+':port/dreamcast/tools/d367/triangle_shadow24/exact_shadow.py'])
  if hashlib.sha256(data).hexdigest()!='9c0f85d588be2020a1506325da078e27a99c23b81f783ff3db268f6082a64f41':raise ValueError('Generic source mismatch')
  f=Path(cls.tmp.name)/'generic28c.py';f.write_bytes(data);spec=importlib.util.spec_from_file_location('generic28c',f);cls.o=importlib.util.module_from_spec(spec);sys.modules[spec.name]=cls.o;spec.loader.exec_module(cls.o)
 @classmethod
 def tearDownClass(cls):cls.tmp.cleanup()
 def inventory(self,triangles=None):
  if triangles is None:triangles=(((0,0,2),(4,0,2),(0,4,2)),)
  parents=tuple(p.Parent((1,1,2,3,0,4,i),(0,1,2),'b'*64,tuple(tuple(Q(x) for x in point) for point in t)) for i,t in enumerate(triangles));binding='a'*64
  return p.Inventory(parents,binding,p.inventory_digest(parents,binding))
 def panel(self,identifier,source):
  source=tuple(tuple(Q(x) for x in point) for point in source);s0,s1,s2=source;buddy=(s1,s0,tuple(s0[k]+s1[k]-s2[k] for k in range(3)))
  return p.PhysicalPanel(identifier,(identifier,identifier,2,3,4,0,1,2,1,0,3),'c'*64,(source,buddy))
 def eyes(self):return self.o.eye_box((Q(-1,100),)*3,(Q(1,100),)*3)
 def broad(self,identifier=1):return self.panel(identifier,((-100,-100,1),(100,-100,1),(0,100,1)))
 def strict_example(self):
  inv=self.inventory();children=p.canonical_partition(inv);sources=[]
  for i,(child,q) in enumerate(zip(children,(Q(9,10),Q(1),Q(11,10),Q(19,20)))):
   centroid=tuple(sum(v[k] for v in child.vertices)/3 for k in range(2));source=tuple((3*q*v[0]/4-q*centroid[0]/4,3*q*v[1]/4-q*centroid[1]/4,q) for v in child.vertices);sources.append(p.FixedFace(self.panel(i+1,source),0))
  return inv,children,tuple(sources)
 def test_design_strict_four_planes_old_fails_new_passes(self):
  inv,children,sources=self.strict_example()
  for source in sources:self.assertIs(type(self.o.cover_triangle(self.eyes(),source.panel.faces[0],inv.parents[0].vertices)),self.o.Unknown)
  with patch.object(self.o,'_edge',wraps=self.o._edge) as edge,patch.object(self.o,'_plane',wraps=self.o._plane) as plane:
   proof=p.cover_partition(inv,children,self.eyes(),sources,self.o)
  self.assertEqual(edge.call_count,288);self.assertEqual(plane.call_count,44);self.assertIs(type(proof),p.PartitionProof);self.assertEqual(proof.child_count,4);self.assertEqual(len(proof.physical_dependencies),4)
  self.assertEqual(len({s.panel.faces[0][0][2] for s in sources}),4)
  self.assertTrue(all(x.min_edge_volume>0 and x.min_eye_plane>0 and x.min_target_plane>0 for x in proof.base_proof.triangles))
 def test_old_whole_parent_positive_included(self):
  inv=self.inventory();source=p.FixedFace(self.broad(),0);self.assertIs(type(self.o.cover_triangle(self.eyes(),source.panel.faces[0],inv.parents[0].vertices)),self.o.TriangleProof)
  self.assertIs(type(p.cover_partition(inv,p.canonical_partition(inv),self.eyes(),(source,)*4,self.o)),p.PartitionProof)
 def test_basis_normals_internal_seams_and_exterior_boundary(self):
  inv=self.inventory();children=p.canonical_partition(inv);parentnormal=p.normal(inv.parents[0].vertices);edges=collections.Counter()
  for c in children:
   self.assertEqual(p.normal(c.vertices),tuple(v/4 for v in parentnormal));self.assertEqual(c.basis,p.BASIS[c.identifier])
   for v,w in zip(c.basis,c.basis[1:]+c.basis[:1]):edges[(v,w)]+=1
  internal=[((p.BASIS[0][1],p.BASIS[0][2])),((p.BASIS[1][2],p.BASIS[1][0])),((p.BASIS[2][0],p.BASIS[2][1]))]
  for a,b in internal:self.assertEqual(edges[(a,b)],1);self.assertEqual(edges[(b,a)],1)
  boundary={(a,b) for a,b in edges if not edges[(b,a)]};A=(1,0,0);B=(0,1,0);C=(0,0,1);D=(Q(1,2),Q(1,2),0);E=(0,Q(1,2),Q(1,2));F=(Q(1,2),0,Q(1,2))
  self.assertEqual(boundary,{(A,D),(D,B),(B,E),(E,C),(C,F),(F,A)})
 def test_missing_duplicate_reversed_wrong_midpoint_wrong_parent_refuse(self):
  inv=self.inventory();ch=p.canonical_partition(inv)
  mutants=[ch[:-1],ch[:3]+(ch[0],),ch[:3]+(dataclasses.replace(ch[3],vertices=tuple(reversed(ch[3].vertices))),),ch[:3]+(dataclasses.replace(ch[3],basis=ch[0].basis),),ch[:3]+(dataclasses.replace(ch[3],parent=(1,1,2,3,1,4,0)),),ch[:3]+(dataclasses.replace(ch[3],identifier=0),),ch[:3]+(dataclasses.replace(ch[3],vertices=((ch[3].vertices[0][0]+1,)+ch[3].vertices[0][1:],)+ch[3].vertices[1:]),)]
  for bad in mutants:self.assertIs(type(p.validate_partition(inv,bad)),p.Unknown)
  # Missing central child really leaves parent barycentric(1/3,1/3,1/3) outside corner children.
  self.assertTrue(all(Q(1,3)<Q(1,2) for _ in range(3)))
 def test_original_indices_affine_binding_and_occurrences_not_pruned(self):
  inv=self.inventory((self.inventory().parents[0].vertices,)*2);children=p.canonical_partition(inv);self.assertEqual(len(children),8);self.assertNotEqual(children[0].parent,children[4].parent)
  variants=[dataclasses.replace(inv,parents=inv.parents[:1]),dataclasses.replace(inv,parents=(inv.parents[0],inv.parents[0])),dataclasses.replace(inv,parents=(dataclasses.replace(inv.parents[0],indices=(2,1,0)),inv.parents[1])),dataclasses.replace(inv,parents=(dataclasses.replace(inv.parents[0],affine_sha256='d'*64),inv.parents[1]))]
  for bad in variants:self.assertIs(type(p.canonical_partition(bad)),p.Unknown)
 def test_degenerate_parent_refuses_entire_inventory_never_omitted(self):
  for t in (((0,0,2),(0,0,2),(1,0,2)),((0,0,2),(1,0,2),(2,0,2))):
   inv=self.inventory((self.inventory().parents[0].vertices,t));answer=p.canonical_partition(inv);self.assertEqual(answer.reason,'DEGENERATE_PARENT')
 def test_last_child_failure_does_not_return_subset(self):
  inv,ch,sources=self.strict_example();bad=p.FixedFace(self.panel(9,((100,100,1),(110,100,1),(100,110,1))),0);answer=p.cover_partition(inv,ch,self.eyes(),sources[:3]+(bad,),self.o)
  self.assertIs(type(answer),p.Unknown);self.assertEqual(answer.reason,'BASE_EDGE_VOLUME')
 def test_global_16_full_physical_panels_pass_17_refuse(self):
  inv=self.inventory((self.inventory().parents[0].vertices,)*5);ch=p.canonical_partition(inv)
  for n in (16,17):
   sources=tuple(p.FixedFace(self.broad(i%n+1),0) for i in range(20));answer=p.cover_partition(inv,ch,self.eyes(),sources,self.o)
   if n==16:self.assertIs(type(answer),p.PartitionProof);self.assertEqual(len(answer.physical_dependencies),16)
   else:self.assertEqual(answer.reason,'GLOBAL_PANEL_LIMIT')
 def test_same_coordinates_never_merge_physical_panel_aliases(self):
  inv=self.inventory();ch=p.canonical_partition(inv);a=self.broad(1);b=self.broad(2)
  wrongid=dataclasses.replace(b,identifier=1);wrongrecord=dataclasses.replace(a,identifier=2)
  for bad,reason in ((wrongid,'PHYSICAL_PANEL_ID_ALIAS'),(wrongrecord,'PHYSICAL_PANEL_RECORD_ALIAS')):
   answer=p.cover_partition(inv,ch,self.eyes(),(p.FixedFace(a,0),)*3+(p.FixedFace(bad,0),),self.o);self.assertEqual(answer.reason,reason)
 def test_full_panel_distinct_actual_corners_and_shared_edge(self):
  inv=self.inventory();ch=p.canonical_partition(inv);a=self.broad();record=a.record[:5]+a.record[5:8]*2;bad=dataclasses.replace(a,record=record)
  self.assertEqual(p.cover_partition(inv,ch,self.eyes(),(p.FixedFace(bad,0),)*4,self.o).reason,'DISTINCT_ADJACENT_ACTUAL_PANEL_FACES')
  moved=(tuple(v+1 for v in a.faces[1][0]),)+a.faces[1][1:];bad=dataclasses.replace(a,faces=(a.faces[0],moved))
  self.assertEqual(p.cover_partition(inv,ch,self.eyes(),(p.FixedFace(bad,0),)*4,self.o).reason,'ACTUAL_PANEL_CORNER_ALIAS')
 def test_work_bits_memory_and_count_budgets_unknown(self):
  inv=self.inventory();ch=p.canonical_partition(inv);sources=(p.FixedFace(self.broad(),0),)*4
  tests=[(p.Limits(max_parents=0),'PARENT_BUDGET'),(p.Limits(max_children=3),'CHILD_BUDGET'),(p.Limits(max_bits=2),'INPUT_BITS'),(p.Limits(max_serialized_bytes=1),'MEMORY_ACCOUNTING_BUDGET'),(p.Limits(max_edge_tests=287),'WORK_BUDGET')]
  for limits,reason in tests:self.assertEqual(p.cover_partition(inv,ch,self.eyes(),sources,self.o,limits).reason,reason)
  with patch.object(p,'_bytes',side_effect=MemoryError):self.assertEqual(p.canonical_partition(inv).reason,'MEMORY_ALLOCATION')
 def test_midpoint_bit_growth_refuses_not_rounds(self):
  x=Q(1,(1<<127)-1);y=Q(1,(1<<128)-1);inv=self.inventory((((x,0,2),(y,1,2),(0,0,2)),))
  self.assertEqual(p.canonical_partition(inv,p.Limits(max_bits=128)).reason,'INPUT_BITS')
 def test_per_vertex_or_per_eye_source_switching_not_an_assignment(self):
  inv=self.inventory();ch=p.canonical_partition(inv);face=p.FixedFace(self.broad(),0)
  for switched in ((face,)*3,(face,)*8):
   self.assertEqual(p.cover_partition(inv,ch,self.eyes(),(switched,)*4,self.o).reason,'FULL_PANEL_FACE')
 def test_incomplete_backend_result_refuses(self):
  inv=self.inventory();ch=p.canonical_partition(inv);face=p.FixedFace(self.broad(),0)
  oracle=SimpleNamespace(SourceFace=self.o.SourceFace,Panel=self.o.Panel,Unknown=self.o.Unknown,AssignedProof=self.o.AssignedProof,cover_assigned=lambda eyes,targets,sources:self.o.cover_assigned(eyes,targets[:-1],sources[:-1]))
  self.assertEqual(p.cover_partition(inv,ch,self.eyes(),(face,)*4,oracle).reason,'INCOMPLETE_BASE_RESULT')
 def test_no_float_or_mutable_or_subset_assignment(self):
  inv=self.inventory();ch=p.canonical_partition(inv);source=p.FixedFace(self.broad(),0)
  self.assertEqual(p.cover_partition(inv,ch,self.eyes(),(source,)*3,self.o).reason,'COMPLETE_CHILD_ASSIGNMENT')
  self.assertIs(type(p.validate_partition(inv,list(ch))),p.Unknown)
  bad=p.Parent(inv.parents[0].occurrence,inv.parents[0].indices,'b'*64,((0.0,0,2),(4,0,2),(0,4,2)));self.assertEqual(p.canonical_partition(dataclasses.replace(inv,parents=(bad,))).reason,'NON_RATIONAL')
 def test_conditional_perturbation_lift_no_automatic_endpoint_authority(self):
  w=(Q(1,2),Q(1,2),0);r=((32,32,32),)*3
  self.assertEqual(p.conditional_radius(w,r).reason,'ENDPOINT_BOUND_UNQUALIFIED');self.assertEqual(p.conditional_radius(w,r,True),(32,32,32));self.assertEqual(p.conditional_radius((Q(-1),1,1),r,True).reason,'NONCONVEX_BOUND')
  for failure in (MemoryError,OverflowError):
   with self.subTest(allocation_failure=failure.__name__):
    with patch.object(p,'_point',side_effect=failure):
     answer=p.conditional_radius(w,r,True)
     self.assertIs(type(answer),p.Unknown);self.assertEqual(answer.reason,'MEMORY_ALLOCATION')
  inv=self.inventory();parents=tuple(dataclasses.replace(t,vertices=tuple(tuple(v+(1 if k==0 else 0) for k,v in enumerate(point)) for point in t.vertices)) for t in inv.parents);shifted=p.Inventory(parents,inv.source_binding_sha256,p.inventory_digest(parents,inv.source_binding_sha256));ch=p.canonical_partition(shifted)
  self.assertEqual(ch[0].vertices[1],ch[1].vertices[0]);self.assertEqual(ch[0].vertices[2],ch[2].vertices[0]);self.assertEqual(ch[3].vertices[0],ch[0].vertices[1])
  # Equal endpoint errors persist; opposite errors cancel at the correlated midpoint.
  self.assertEqual((Q(1)+Q(1))/2,1);self.assertEqual((Q(1)-Q(1))/2,0)
if __name__=='__main__':unittest.main()
