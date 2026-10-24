"""Canonical target proof decomposition. Never generates rendered geometry.
Original occurrence/indices/affine/package authentication is a CALLER obligation.
"""
from dataclasses import dataclass
from fractions import Fraction as Q
import hashlib,json
MAX_BITS=256;MAX_PARENTS=256;MAX_CHILDREN=1024;MAX_EDGE_TESTS=73728
BASIS=(((1,0,0),(Q(1,2),Q(1,2),0),(Q(1,2),0,Q(1,2))),((Q(1,2),Q(1,2),0),(0,1,0),(0,Q(1,2),Q(1,2))),((Q(1,2),0,Q(1,2)),(0,Q(1,2),Q(1,2)),(0,0,1)),((Q(1,2),Q(1,2),0),(0,Q(1,2),Q(1,2)),(Q(1,2),0,Q(1,2))))
@dataclass(frozen=True)
class Unknown:
 reason:str
 def __bool__(self):raise TypeError('UNKNOWN is not a visibility decision')
@dataclass(frozen=True)
class Parent:
 occurrence:tuple # placement,field,part,cluster,effectiveLOD,globallet,ordinal
 indices:tuple # unchanged original oriented local corner indices
 affine_sha256:str # external exact serialized affine/dequantization operands
 vertices:tuple
@dataclass(frozen=True)
class Inventory:
 parents:tuple
 source_binding_sha256:str # external authenticated source/input/provenance binding
 expected_inventory_sha256:str
@dataclass(frozen=True)
class Child:
 parent:tuple
 identifier:int
 basis:tuple
 vertices:tuple
@dataclass(frozen=True)
class PhysicalPanel:
 identifier:int
 record:tuple # actual production placement,field,part,cluster,let,corners[6]
 source_binding_sha256:str
 faces:tuple # both DISTINCT actual oriented adjacent source triangles
@dataclass(frozen=True)
class FixedFace:
 panel:PhysicalPanel
 face:int
@dataclass(frozen=True)
class Limits:
 max_parents:int=MAX_PARENTS
 max_children:int=MAX_CHILDREN
 max_bits:int=MAX_BITS
 max_edge_tests:int=MAX_EDGE_TESTS
 max_serialized_bytes:int=4*1024*1024 # accounting envelope, NOT a Python RSS bound
@dataclass(frozen=True)
class PartitionProof:
 inventory_sha256:str
 original_occurrences:tuple
 child_count:int
 physical_dependencies:tuple
 dependencies:tuple
 assignments:tuple
 base_proof:object
class _Refuse(Exception):pass

def _tuple(x,n,m,why):
 if type(x)is not tuple or not n<=len(x)<=m:raise _Refuse(why)
 return x
def _uint(x,maximum=0xffffffff):
 if type(x)is not int or not 0<=x<=maximum:raise _Refuse('IDENTITY_INTEGER')
 return x
def _hash(s):
 if type(s)is not str or len(s)!=64 or any(c not in '0123456789abcdef' for c in s):raise _Refuse('PROVENANCE_HASH')
 return s
def _limits(l):
 if type(l)is not Limits or any(type(v)is not int or v<0 for v in (l.max_parents,l.max_children,l.max_bits,l.max_edge_tests,l.max_serialized_bytes)):raise _Refuse('LIMITS')
 if l.max_parents>MAX_PARENTS or l.max_children>MAX_CHILDREN or l.max_bits>MAX_BITS or l.max_edge_tests>MAX_EDGE_TESTS or l.max_serialized_bytes>4*1024*1024:raise _Refuse('LIMITS')
 return l
def _scalar(x,l):
 if type(x)not in (int,Q):raise _Refuse('NON_RATIONAL')
 q=Q(x)
 if max(abs(q.numerator).bit_length(),q.denominator.bit_length())>l.max_bits:raise _Refuse('INPUT_BITS')
 return q
def _point(p,l):return tuple(_scalar(v,l) for v in _tuple(p,3,3,'POINT_ARITY'))
def _triangle(t,l):return tuple(_point(p,l) for p in _tuple(t,3,3,'TRIANGLE_ARITY'))
def _sub(a,b):return tuple(a[i]-b[i] for i in range(3))
def normal(t):
 a,b,c=t;u=_sub(b,a);v=_sub(c,a);return (u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0])
def _serialized(value):
 if type(value)in (int,str):return value
 if type(value)is Q:return str(value)
 if type(value)is tuple:return [_serialized(x) for x in value]
 raise _Refuse('SERIALIZATION_TYPE')
def _bytes(value):return json.dumps(_serialized(value),separators=(',',':')).encode()
def _account(value,l):
 b=_bytes(value)
 if len(b)>l.max_serialized_bytes:raise _Refuse('MEMORY_ACCOUNTING_BUDGET')
 return b
def inventory_digest(parents,source_binding_sha256):
 """Digest for an EXTERNALLY authenticated original manifest; not asset proof."""
 payload=(source_binding_sha256,tuple((p.occurrence,p.indices,p.affine_sha256,p.vertices) for p in parents))
 return hashlib.sha256(_bytes(payload)).hexdigest()
def _inventory(inv,l):
 if type(inv)is not Inventory:raise _Refuse('INVENTORY_TYPE')
 parents=_tuple(inv.parents,1,min(MAX_PARENTS,l.max_parents),'PARENT_BUDGET');_hash(inv.source_binding_sha256);_hash(inv.expected_inventory_sha256)
 if 4*len(parents)>min(MAX_CHILDREN,l.max_children):raise _Refuse('CHILD_BUDGET')
 physical=None
 for ordinal,p in enumerate(parents):
  if type(p)is not Parent:raise _Refuse('PARENT_TYPE')
  _tuple(p.occurrence,7,7,'ORIGINAL_IDENTITY')
  for v in p.occurrence:_uint(v)
  if p.occurrence[-1]!=ordinal:raise _Refuse('ORIGINAL_OCCURRENCE_ORDER')
  if physical is None:physical=p.occurrence[:6]
  if physical!=p.occurrence[:6]:raise _Refuse('WRONG_ORIGINAL_PARENT')
  for v in _tuple(p.indices,3,3,'ORIGINAL_INDICES'):_uint(v,255)
  _hash(p.affine_sha256);t=_triangle(p.vertices,l)
  if not any(normal(t)):raise _Refuse('DEGENERATE_PARENT') # conservative user scope; NEVER omit
 _account((inv.source_binding_sha256,tuple((p.occurrence,p.indices,p.affine_sha256,p.vertices) for p in parents)),l)
 if inventory_digest(parents,inv.source_binding_sha256)!=inv.expected_inventory_sha256:raise _Refuse('ORIGINAL_INVENTORY_BINDING')
 return parents

def _canonical(inv,l):
 parents=_inventory(inv,l);out=[]
 for p in parents:
  # One correlated midpoint construction from these SAME authenticated endpoints.
  a,b,c=p.vertices;ab=tuple((Q(x)+Q(y))/2 for x,y in zip(a,b));bc=tuple((Q(x)+Q(y))/2 for x,y in zip(b,c));ac=tuple((Q(x)+Q(y))/2 for x,y in zip(a,c))
  vertices=((a,ab,ac),(ab,b,bc),(ac,bc,c),(ab,bc,ac))
  for i,v in enumerate(vertices):out.append(Child(p.occurrence,i,BASIS[i],_triangle(v,l)))
 _account((inv.source_binding_sha256,tuple((p.occurrence,p.indices,p.affine_sha256,p.vertices) for p in parents),tuple((c.parent,c.identifier,c.basis,c.vertices) for c in out)),l)
 return tuple(out)
def canonical_partition(inv,limits=Limits()):
 try:return _canonical(inv,_limits(limits))
 except _Refuse as e:return Unknown(str(e))
 except (MemoryError,OverflowError):return Unknown('MEMORY_ALLOCATION')
def _validate(inv,children,l):
 expected=_canonical(inv,l);_tuple(children,len(expected),len(expected),'COMPLETE_CANONICAL_PARTITION')
 for actual,wanted in zip(children,expected):
  if type(actual)is not Child:raise _Refuse('CHILD_TYPE')
  _tuple(actual.parent,7,7,'CHILD_PARENT')
  for v in actual.parent:_uint(v)
  _uint(actual.identifier,3)
  for v in _tuple(actual.basis,3,3,'CHILD_BASIS'):_point(v,l)
  _triangle(actual.vertices,l)
  if actual!=wanted:raise _Refuse('NONCANONICAL_CHILD_OR_PARENT')
 return expected
def validate_partition(inv,children,limits=Limits()):
 try:return _validate(inv,children,_limits(limits))
 except _Refuse as e:return Unknown(str(e))
 except (MemoryError,OverflowError):return Unknown('MEMORY_ALLOCATION')
def _panel(face,l):
 if type(face)is not FixedFace or type(face.face)is not int or face.face not in (0,1) or type(face.panel)is not PhysicalPanel:raise _Refuse('FULL_PANEL_FACE')
 p=face.panel;_uint(p.identifier);_hash(p.source_binding_sha256);_tuple(p.record,11,11,'PHYSICAL_PANEL_RECORD')
 for v in p.record[:5]:_uint(v)
 for v in p.record[5:]:_uint(v,255)
 a,b=p.record[5:8],p.record[8:11]
 if a==b or not any((u,v)==(y,x) for u,v in zip(a,a[1:]+a[:1]) for x,y in zip(b,b[1:]+b[:1])):raise _Refuse('DISTINCT_ADJACENT_ACTUAL_PANEL_FACES')
 faces=tuple(_triangle(t,l) for t in _tuple(p.faces,2,2,'FULL_PANEL_FACES'))
 if not all(any(normal(t)) for t in faces):raise _Refuse('DEGENERATE_SOURCE')
 points={}
 for index,point in zip(p.record[5:],faces[0]+faces[1]):
  if index in points and points[index]!=point:raise _Refuse('ACTUAL_PANEL_CORNER_ALIAS')
  points[index]=point
 return p,faces

def cover_partition(inv,children,eyes,fixed_sources,oracle,limits=Limits()):
 """ALL original occurrences, ALL four children, ONE fixed face/child over ALL E.
 Full Panel source authentication and actual rendered receipts remain external.
 """
 try:
  l=_limits(limits);validated=_validate(inv,children,l);_tuple(eyes,1,64,'EYE_BUDGET')
  for e in eyes:_point(e,l)
  if len(validated)*len(eyes)*9>l.max_edge_tests:raise _Refuse('WORK_BUDGET')
  _tuple(fixed_sources,len(validated),len(validated),'COMPLETE_CHILD_ASSIGNMENT');by_id={};by_record={};sources=[]
  for f in fixed_sources:
   p,faces=_panel(f,l);definition=(p.record,p.source_binding_sha256,faces)
   if p.identifier in by_id and by_id[p.identifier]!=definition:raise _Refuse('PHYSICAL_PANEL_ID_ALIAS')
   if p.record in by_record and by_record[p.record]!=p.identifier:raise _Refuse('PHYSICAL_PANEL_RECORD_ALIAS')
   by_id[p.identifier]=definition;by_record[p.record]=p.identifier
   if len(by_record)>16:raise _Refuse('GLOBAL_PANEL_LIMIT')
   sources.append(oracle.SourceFace(oracle.Panel(p.identifier,faces),f.face))
  _account((inv.source_binding_sha256,tuple((p.occurrence,p.indices,p.affine_sha256,p.vertices) for p in inv.parents),tuple((c.parent,c.identifier,c.basis,c.vertices) for c in validated),eyes,tuple((f.panel.identifier,f.panel.record,f.panel.source_binding_sha256,f.panel.faces,f.face) for f in fixed_sources)),l)
  proof=oracle.cover_assigned(eyes,tuple(c.vertices for c in validated),tuple(sources))
  if type(proof)is oracle.Unknown:return Unknown('BASE_'+proof.reason)
  if type(proof)is not oracle.AssignedProof or len(proof.assignments)!=len(validated) or len(proof.triangles)!=len(validated) or proof.dependencies!=tuple(sorted(by_id)):raise _Refuse('INCOMPLETE_BASE_RESULT')
  return PartitionProof(inv.expected_inventory_sha256,tuple(p.occurrence for p in inv.parents),len(validated),tuple(sorted(by_record)),proof.dependencies,proof.assignments,proof)
 except _Refuse as e:return Unknown(str(e))
 except (MemoryError,OverflowError):return Unknown('MEMORY_ALLOCATION')

def conditional_radius(weights,radii,endpoint_bounds_valid=False,limits=Limits()):
 """Algebra ONLY: caller-valid endpoint component radii lift by convex weights.
 No actual SH4, raster, clipping or endpoint-bound validity is established here.
 """
 try:
  if endpoint_bounds_valid is not True:raise _Refuse('ENDPOINT_BOUND_UNQUALIFIED')
  l=_limits(limits);w=tuple(_scalar(v,l) for v in _tuple(weights,3,3,'WEIGHTS'));rr=tuple(_point(p,l) for p in _tuple(radii,3,3,'RADII'))
  if any(x<0 for x in w) or sum(w)!=1 or any(x<0 for p in rr for x in p):raise _Refuse('NONCONVEX_BOUND')
  return _point(tuple(sum(w[i]*rr[i][k] for i in range(3)) for k in range(3)),l)
 except _Refuse as e:return Unknown(str(e))
 except (MemoryError,OverflowError):return Unknown('MEMORY_ALLOCATION')
