"""Bounded hut647 actual-triangle runner. Default command ONLY prepares a plan.
Private execution is held for independent review and a separate root grant.
"""
import argparse,collections,dataclasses,hashlib,importlib.util,itertools,json,resource,subprocess,sys,tempfile,time
from fractions import Fraction as Q
from pathlib import Path
PREP_SOURCE='d8620e8b6a13706d89aa8415d3397f5f4d06c589'
PREP_SHA='22b2fe4dc83c0a0ba846eefb822fe1dead4bbbaa850b1e838dc5eaaadc56d57c'
SEAL_SHA='ef328388f80574e2fc41bf4f01a9b983822c6b20a28c8844a72eafdc7c17e265'
GENERIC='28c739468ae7d2d2d3c09f81330015e7769dc824'
GENERIC_SHA='9c0f85d588be2020a1506325da078e27a99c23b81f783ff3db268f6082a64f41'
CANDIDATE_CALLS=100000;FINAL_CALLS=889*3;EDGE_PER_CALL=72
RAM=256*1024*1024;OUTPUT=16*1024*1024;WALL=120;COMPUTE_SECONDS=115
SIZES=(2000,500,250)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def require(p,expected):
 p=Path(p)
 if p.stat().st_size!=expected['bytes'] or sha(p)!=expected['sha256']:raise ValueError('Pinned input changed '+str(p))
def pin(p):return dict(path=str(p),bytes=Path(p).stat().st_size,sha256=sha(p))
def encoded(x):return json.dumps(x,separators=(',',':'),sort_keys=True).encode()
def inventory_sha(triangles):return hashlib.sha256(encoded([[[str(v) for v in p] for p in t] for t in triangles])).hexdigest()
def point(p):
 if type(p) not in (tuple,list) or len(p)!=3 or any(type(v) is not str for v in p):raise ValueError('Exact serialized point required')
 out=tuple(Q(v) for v in p)
 if any(max(abs(v.numerator).bit_length(),v.denominator.bit_length())>256 for v in out):raise ValueError('Exact scalar bound')
 return out
def triangle(t):
 if len(t)!=3:raise ValueError('Whole actual triangle required')
 return tuple(point(p) for p in t)
def nondeg(t):
 a,b,c=t;u=tuple(b[i]-a[i] for i in range(3));v=tuple(c[i]-a[i] for i in range(3))
 return any((u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]))
def adjacent(a,b):return a!=b and any((u,v)==(y,x) for u,v in zip(a,a[1:]+a[:1]) for x,y in zip(b,b[1:]+b[:1]))
@dataclasses.dataclass(frozen=True)
class Candidate:
 key:tuple
 panel_id:int|None
 panel_record:tuple|None
 panel_faces:tuple|None
 face:int|None
 reason:str|None=None
@dataclasses.dataclass(frozen=True)
class Case:
 identifier:tuple
 triangles:tuple
 expected_count:int
 expected_inventory:str
 sources:tuple
 eye_box:tuple
 source_unrepresentable:tuple=()
class Interrupted(Exception):pass
class Budget:
 def __init__(self,candidate=CANDIDATE_CALLS,final=FINAL_CALLS,clock=time.monotonic,deadline=None):
  self.candidate_limit=candidate;self.final_limit=final;self.candidate_used=0;self.final_used=0;self.final_invocations=0;self.active=None;self.clock=clock;self.deadline=clock()+COMPUTE_SECONDS if deadline is None else deadline
 def check_time(self):
  if self.clock()>=self.deadline:raise Interrupted('UNKNOWN_WALL_BUDGET')
 def reserve(self,candidate,final):
  if self.active is not None:raise ValueError('Nested reservation')
  self.check_time()
  if candidate>self.candidate_limit-self.candidate_used or final>self.final_limit-self.final_used:return False
  self.active=[candidate,final,0,0];return True
 def candidate(self):
  self.check_time()
  if self.active is None or self.active[2]>=self.active[0]:raise ValueError('Candidate reservation exceeded')
  self.active[2]+=1;self.candidate_used+=1
 def final(self,n):
  self.check_time()
  if self.active is None or self.active[3]+n>self.active[1]:raise ValueError('Final reservation exceeded')
  self.active[3]+=n;self.final_used+=n;self.final_invocations+=1
 def close(self):self.active=None
 def receipt(self):return dict(candidate_call_cap=self.candidate_limit,candidate_calls=self.candidate_used,candidate_edge_upper=72*self.candidate_used,final_call_cap=self.final_limit,final_triangle_calls_upper=self.final_used,final_batch_invocations=self.final_invocations,final_edge_upper=72*self.final_used,unused_reservations_returned_only_after_case=True)
def frozen_oracle(repo,ram):
 data=subprocess.check_output(['git','-C',str(repo),'show',GENERIC+':port/dreamcast/tools/d367/triangle_shadow24/exact_shadow.py'])
 if hashlib.sha256(data).hexdigest()!=GENERIC_SHA:raise ValueError('Generic source drift')
 path=ram/'reviewed_triangle_shadow.py';path.write_bytes(data);spec=importlib.util.spec_from_file_location('reviewed_triangle_shadow',path);m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m);return m

def bind(report_path,seal_path):
 if sha(report_path)!=PREP_SHA or sha(seal_path)!=SEAL_SHA:raise ValueError('Frozen preparation report/seal required')
 d=json.loads(report_path.read_text());seal=json.loads(seal_path.read_text())
 if seal['source']!=PREP_SOURCE or d['actual_shadow_predicate_calls']!=0 or d['runtime_admitted'] is not False:raise ValueError('Wrong preparation provenance')
 # Fresh byte readback of copied source data, profile, descriptors, cameras and capability.
 for p in d['inputs'].values():require(p['path'],p)
 require(d['source']['profile']['path'],d['source']['profile'])
 for rel,p in d['source']['files'].items():
  path=Path('/root/probe/interior-discovery24')/rel
  if sha(path)!=p['owned_tree_sha256']:raise ValueError('Frozen source file changed '+rel)
 for k,p in d['material_pins'].items():
  if type(p)is dict and set(('path','bytes','sha256'))<=set(p):require(p['path'],p)
 require(d['production_panel_source']['path'],d['production_panel_source']);require(d['capability']['path'],d['capability'])
 cap=json.loads(Path(d['capability']['path']).read_text())
 for k in ('helper','nonempty','helper_block','compiler','binary','harness','actual_audit','actual_mesh'):require(cap[k]['path'],cap[k])
 logs=d['authentic_camera_logs']
 for entry in logs:
  for p in (entry['log'],entry['weights']):require(p['path'],p)
 return d

def cases_from_report(d):
 if len(d['targets'])!=25 or len(d['domains'])!=387 or sum(len(t['complete_target_faces']) for t in d['targets'])!=889:raise ValueError('Complete fixed inventory required')
 domains=[x for x in d['domains'] if x['label']=='hut' and x['frame']==647]
 if tuple(x['size_mm'] for x in domains)!=SIZES:raise ValueError('Authentic hut647 declared domain order required')
 atlas={x['identifier']:x for x in d['panel_atlas']}
 if len(atlas)!=len(d['panel_atlas']) or len({tuple(x['record']) for x in atlas.values()})!=len(atlas):raise ValueError('Full Panel ID bijection')
 cases=[]
 for rank,t in enumerate(d['targets']):
  if t['rank']!=rank:raise ValueError('Saved target order changed')
  raw=t['complete_target_faces']
  if [x['ordinal'] for x in raw]!=list(range(len(raw))) or not raw:raise ValueError('Complete ordered triangle inventory')
  tris=tuple(triangle(x['positions_exact']) for x in raw);sources=[];bykey={tuple(x['key']):x for x in t['source_faces']}
  if len(bykey)!=len(t['source_faces']):raise ValueError('Duplicate actual source key')
  for r in t['source_faces']:
   key=tuple(r['key'])
   if 'panel_id' not in r:sources.append(Candidate(key,None,None,None,None,'UNKNOWN_UNREPRESENTABLE_PANEL'));continue
   a,b=r['panel_face_ordinals'];ka=(*key[:6],a);kb=(*key[:6],b)
   if a==b or ka not in bykey or kb not in bykey:raise ValueError('Both distinct retained Panel faces required')
   ra,rb=bykey[ka],bykey[kb];ia,ib=tuple(ra['corners']),tuple(rb['corners']);record=(*key[:4],key[5],*ia,*ib)
   if not adjacent(ia,ib) or record!=tuple(r['panel_record']) or atlas[r['panel_id']]['record']!=list(record) or atlas[r['panel_id']]['actual_face_definition']!=list((*key[:6],a,b)):raise ValueError('Full actual Panel binding')
   faces=(triangle(ra['positions_exact']),triangle(rb['positions_exact']))
   if not all(nondeg(f) for f in faces) or r['panel_face']!=int(key[6]==b) or key[6] not in (a,b):raise ValueError('Panel face/degeneracy mismatch')
   sources.append(Candidate(key,r['panel_id'],record,faces,r['panel_face']))
  for domain in domains:
   box=tuple(point(x) for x in domain['box_exact'])
   if any(box[0][i]>box[1][i] for i in range(3)):raise ValueError('Domain bounds')
   cases.append(Case((rank,*t['physical'],'hut',647,domain['size_mm']),tris,len(tris),inventory_sha(tris),tuple(sources),box,tuple(tuple(x) for x in t['unrepresentable_source_faces'])))
 if len(cases)!=75:raise ValueError('Fixed75 case census')
 return tuple(cases)

def _solve(case,budget,oracle):
 # This comparison precedes every predicate and never canonicalizes/prunes faces.
 if len(case.triangles)!=case.expected_count or inventory_sha(case.triangles)!=case.expected_inventory:raise ValueError('Incomplete or changed actual target triangles')
 calls=len(case.triangles)*len(case.sources);final=len(case.triangles)
 if not budget.reserve(calls,final):return dict(status='UNTESTED_UNKNOWN_BUDGET',started=False)
 assignments=[];failures=collections.Counter();panels=set();started_candidate=budget.candidate_used;started_final=budget.final_used
 try:
  eyes=oracle.eye_box(*case.eye_box)
  if type(eyes)is oracle.Unknown:return dict(status='UNKNOWN_EYE_DOMAIN',started=True)
  for ti,target in enumerate(case.triangles):
   chosen=None
   for source in case.sources:
    if source.reason:failures[source.reason]+=1;continue
    budget.candidate();answer=oracle.cover_triangle(eyes,source.panel_faces[source.face],target);budget.check_time()
    if type(answer)is oracle.Unknown:failures[answer.reason]+=1;continue
    if type(answer)is not oracle.TriangleProof:raise ValueError('Unrecognized primitive result')
    chosen=source;break
   if chosen is None:return dict(status='UNKNOWN_NO_FIXED_SOURCE',started=True,first_uncovered_target_ordinal=ti,refusals=dict(failures))
   panels.add(chosen.panel_id)
   if len(panels)>16:return dict(status='UNKNOWN_PANEL_CAP',started=True,first_excess_target_ordinal=ti)
   assignments.append(oracle.SourceFace(oracle.Panel(chosen.panel_id,chosen.panel_faces),chosen.face))
  if len(assignments)!=case.expected_count:raise ValueError('Incomplete final assignment')
  budget.final(final);proof=oracle.cover_assigned(eyes,case.triangles,tuple(assignments));budget.check_time()
  if type(proof)is oracle.Unknown:return dict(status='UNKNOWN_FINAL_'+proof.reason,started=True)
  if type(proof)is not oracle.AssignedProof or len(proof.assignments)!=case.expected_count or len(proof.triangles)!=case.expected_count or tuple(sorted(panels))!=proof.dependencies:raise ValueError('Incomplete full assigned proof')
  return dict(status='NOMINAL_EXACT_REAL_CANDIDATE_ONLY',started=True,complete_target_triangles=case.expected_count,dependencies=proof.dependencies,assignments=proof.assignments,margins=[dict(sign=p.sign,eye_plane=str(p.min_eye_plane),target_plane=str(p.min_target_plane),edge_volume=str(p.min_edge_volume)) for p in proof.triangles],refusals=dict(failures),runtime_admitted=False)
 except Interrupted as e:return dict(status=str(e),started=True,partial_assignment_discarded=True)
 finally:budget.close()

def solve(case,budget,oracle):
 before=budget.candidate_used;fbefore=budget.final_used
 answer=_solve(case,budget,oracle)
 return dict(answer,candidate_calls=budget.candidate_used-before,final_triangle_calls_upper=budget.final_used-fbefore)

def execute(cases,budget,oracle):
 rows=[];halt=None
 for case in cases:
  if halt:answer=dict(status=halt,started=False)
  else:
   try:answer=solve(case,budget,oracle)
   except Interrupted as e:answer=dict(status=str(e),started=False)
   if answer['status'] in ('UNTESTED_UNKNOWN_BUDGET','UNKNOWN_WALL_BUDGET'):halt=answer['status']
  rows.append(dict(case=case.identifier,source_unrepresentable=case.source_unrepresentable,**answer))
 return rows

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--repo',type=Path,required=True);ap.add_argument('--prepared',type=Path,required=True);ap.add_argument('--seal',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--execute',action='store_true',help='HELD: run only after independent review and separate root grant');a=ap.parse_args()
 start=time.monotonic();resource.setrlimit(resource.RLIMIT_AS,(RAM,RAM))
 if a.out.exists() or a.out.is_relative_to(a.repo):raise ValueError('Fresh private external output required')
 d=bind(a.prepared,a.seal);cases=cases_from_report(d)
 plans=[dict(case=c.identifier,target_triangles=c.expected_count,sources=len(c.sources),unrepresentable=len(c.source_unrepresentable),whole_case_candidate_reserve=c.expected_count*len(c.sources),whole_case_final_reserve=c.expected_count,inventory_sha256=c.expected_inventory) for c in cases]
 budget=Budget(clock=time.monotonic,deadline=start+COMPUTE_SECONDS)
 result=dict(classification='RUNNER_PREPARATION_ONLY_NO_PRIVATE_PREDICATES',tool=pin(Path(__file__)),prepared=pin(a.prepared),preparation_source=PREP_SOURCE,seal=pin(a.seal),generic_source=GENERIC,generic_sha256=GENERIC_SHA,plan=plans,held_camera_cases=dict(total=9600,status='UNTESTED_UNKNOWN',all_target_ranks=list(range(25)),domains=[dict(label=x['label'],frame=x['frame'],size_mm=x['size_mm'],old_cell=x['old_cell']) for x in d['domains'] if (x['label'],x['frame'])!=('hut',647)],reason='Exact Cartesian product of all25 target ranks and these384 domains; no perlet exposure inference'),limits=dict(candidate_call_cap=CANDIDATE_CALLS,candidate_edge_cap_upper=CANDIDATE_CALLS*72,final_triangle_call_cap=FINAL_CALLS,final_edge_cap_upper=FINAL_CALLS*72,wall_cap_seconds=WALL,computation_deadline_seconds=COMPUTE_SECONDS,address_cap_bytes=RAM,output_cap_bytes=OUTPUT,jobs=1),actual_private_predicate_calls=0,new_rays=0,ledger_accesses=0,runtime_admitted=False)
 if a.execute:
  ram=Path(tempfile.mkdtemp(prefix='triangle-run24-',dir='/dev/shm'));oracle=frozen_oracle(a.repo,ram);rows=execute(cases,budget,oracle)
  result.update(classification='EXACT_REAL_OPPORTUNITY_ONLY_NO_RUNTIME_CERTIFICATE',results=rows,actual_private_predicate_calls=budget.candidate_used+budget.final_invocations,work=budget.receipt())
 result['seconds']=time.monotonic()-start;result['peak_rss_kib']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
 raw=(json.dumps(result,indent=1)+'\n').encode()
 if len(raw)+65536>OUTPUT or time.monotonic()-start>=WALL:raise ValueError('Output/wall cap; no published result')
 a.out.mkdir();(a.out/'report.json').write_bytes(raw);print(json.dumps(dict(classification=result['classification'],report=pin(a.out/'report.json'),seconds=result['seconds'],private_predicates=result['actual_private_predicate_calls'])),flush=True)
if __name__=='__main__':main()
