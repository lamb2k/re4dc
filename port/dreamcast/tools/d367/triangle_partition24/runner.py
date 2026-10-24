"""Finite grant-only partition runner. Default: plan with zero scene predicates."""
import argparse,collections,dataclasses,hashlib,importlib.util,json,resource,subprocess,sys,tempfile,time
from fractions import Fraction as Q
from pathlib import Path
import prepare_private as prep
import verify_private as verify
PREPARATION_SOURCE='be113d594ed5c6b411d0fffaed84a61bcf4bff3f'
PLAN_SHA='24ef9acac6f1b616f832aa7a1cd36cce656cccb8ac51f4efa3e2f3e049bda324'
SEAL_SHA='786192cefc3309e10929fa33608f73133ee18f1cac94e021e8675909636f5ba6'
CONTROLS_SHA='4ffc4a2785c4ac26cff01941a54320c14a9fe9087455b6634aa7093181fafebc'
GENERIC_SOURCE='28c739468ae7d2d2d3c09f81330015e7769dc824'
GENERIC_SHA='9c0f85d588be2020a1506325da078e27a99c23b81f783ff3db268f6082a64f41'
OWNED=prep.OWNED+('runner.py','test_runner.py','RUNNER.md')
LIMITS=dict(candidate_calls=100000,candidate_edges=7200000,final_children=10668,final_edges=768096,compute_seconds=115,wall_seconds=120,address_bytes=268435456,output_bytes=16777216,jobs=1)
def pin(p):return prep.pin(Path(p))
def require(p,sha):
 if pin(p)['sha256']!=sha:raise ValueError('Frozen input changed '+str(p))
def exact(t):return tuple(tuple(Q(v) for v in x) for x in t)
def record(case):
 return dict(identifier=case.identifier,inventory=case.inventory.expected_inventory_sha256,parents=[prep.manifest(p) for p in case.inventory.parents],children=[prep.child_manifest(c) for c in case.children],eye_box=[[str(v) for v in x] for x in case.eye_box],sources=[dict(key=s.key,reason=s.reason,fixed=None if s.fixed is None else dict(identifier=s.fixed.panel.identifier,record=s.fixed.panel.record,binding=s.fixed.panel.source_binding_sha256,faces=[prep.exact(t) for t in s.fixed.panel.faces],face=s.fixed.face)) for s in case.sources])
@dataclasses.dataclass(frozen=True)
class Source:
 key:tuple
 fixed:object=None
 reason:str|None=None
@dataclasses.dataclass(frozen=True)
class Case:
 identifier:tuple
 inventory:object
 children:tuple
 sources:tuple
 eye_box:tuple
 expected_fingerprint:str

def authenticate_case(case,p):
 if prep.token(record(case))!=case.expected_fingerprint:raise ValueError('Case source/eye/inventory drift')
 answer=p.validate_partition(case.inventory,case.children)
 if type(answer)is p.Unknown:raise ValueError('Incomplete original parent/child inventory: '+answer.reason)
 if type(case.sources)is not tuple or not case.sources or len({s.key for s in case.sources})!=len(case.sources):raise ValueError('Finite ordered unique source roster required')
 if type(case.eye_box)is not tuple or len(case.eye_box)!=2:raise ValueError('Whole exact eye box required')
 for point in case.eye_box:p._point(point,p.Limits())
 if any(case.eye_box[0][i]>case.eye_box[1][i] for i in range(3)):raise ValueError('Whole eye bounds')
 by_id={};by_record={}
 for source in case.sources:
  if source.reason:
   if source.fixed is not None:raise ValueError('Unrepresentable source cannot supply a face')
   continue
  panel,faces=p._panel(source.fixed,p.Limits());definition=(panel.record,panel.source_binding_sha256,faces)
  if panel.identifier in by_id and by_id[panel.identifier]!=definition or panel.record in by_record and by_record[panel.record]!=panel.identifier:raise ValueError('Full physical Panel alias')
  by_id[panel.identifier]=definition;by_record[panel.record]=panel.identifier
 return dict(original_parents=len(case.inventory.parents),canonical_children=len(case.children),source_faces=len(case.sources),whole_case_candidate_calls_reserve=len(case.children)*len(case.sources),candidate_edge_upper_reserve=72*len(case.children)*len(case.sources),whole_case_final_child_calls_reserve=len(case.children),final_edge_upper_reserve=72*len(case.children))
class Interrupted(Exception):pass
class Budget:
 """One active whole-case reservation; only close returns unused capacity."""
 def __init__(self,caps=prep.CAPS,clock=time.monotonic,deadline=None):
  prep.Budget(caps);self.caps=caps;self.used=(0,0,0,0);self.active=None;self.clock=clock;self.deadline=clock()+115 if deadline is None else deadline
 def check(self):
  if self.clock()>=self.deadline:raise Interrupted('UNKNOWN_WALL_BUDGET')
 def reserve(self,row):
  self.check()
  if self.active is not None:raise ValueError('Nested reservation; refund only after case')
  values=prep.reservation(row)
  if any(v>cap-used for v,cap,used in zip(values,self.caps,self.used)):return False
  self.active=[values,(0,0,0,0)];return True
 def take(self,values):
  self.check()
  if self.active is None or any(v<0 or v>cap-used for v,cap,used in zip(values,self.active[0],self.active[1])):raise ValueError('Wholecase reserved work exceeded')
  self.active[1]=tuple(x+y for x,y in zip(self.active[1],values));self.used=tuple(x+y for x,y in zip(self.used,values))
 def candidate(self):self.take((1,72,0,0))
 def final(self,n):self.take((0,0,n,72*n))
 def close(self):self.active=None
 def receipt(self):return dict(caps=self.caps,used=self.used,active_reservation=self.active,unused_reservations_returned_only_after_case=True)
class Oracle:
 """Count actual generic invocations separately from conservative edge reserves."""
 def __init__(self,base):self.base=base;self.triangle_calls=0;self.assigned_calls=0
 def __getattr__(self,name):return getattr(self.base,name)
 def cover_triangle(self,*args):self.triangle_calls+=1;return self.base.cover_triangle(*args)
 def cover_assigned(self,*args):self.assigned_calls+=1;return self.base.cover_assigned(*args)

def solve(case,budget,p,oracle):
 plan=authenticate_case(case,p);started=False;failures=collections.Counter()
 try:
  if not budget.reserve(plan):return dict(status='UNTESTED_UNKNOWN_BUDGET',started=False)
  started=True;eyes=oracle.eye_box(*case.eye_box)
  if type(eyes)is oracle.Unknown:return dict(status='UNKNOWN_EYE_DOMAIN',started=True)
  assignments=[];panels=set()
  for i,child in enumerate(case.children):
   chosen=None
   for source in case.sources:
    if source.reason:failures[source.reason]+=1;continue
    budget.candidate();answer=oracle.cover_triangle(eyes,source.fixed.panel.faces[source.fixed.face],child.vertices);budget.check()
    if type(answer)is oracle.Unknown:failures[answer.reason]+=1;continue
    if type(answer)is not oracle.TriangleProof:return dict(status='UNKNOWN_PRIMITIVE_RESULT',started=True,partial_assignment_discarded=True)
    chosen=source;break
   if chosen is None:return dict(status='UNKNOWN_NO_FIXED_SOURCE',started=True,first_uncovered_child=i,parent=child.parent,partial_assignment_discarded=True,refusals=dict(failures))
   panels.add(chosen.fixed.panel.identifier)
   if len(panels)>16:return dict(status='UNKNOWN_GLOBAL_PANEL_CAP',started=True,first_excess_child=i,partial_assignment_discarded=True)
   assignments.append(chosen)
  if len(assignments)!=len(case.children):raise ValueError('Incomplete wholelet fixed assignment')
  budget.final(len(case.children));answer=p.cover_partition(case.inventory,case.children,eyes,tuple(s.fixed for s in assignments),oracle);budget.check()
  if type(answer)is p.Unknown:return dict(status='UNKNOWN_FINAL_'+answer.reason,started=True,partial_assignment_discarded=True)
  if type(answer)is not p.PartitionProof or answer.child_count!=len(case.children) or answer.original_occurrences!=tuple(t.occurrence for t in case.inventory.parents) or answer.inventory_sha256!=case.inventory.expected_inventory_sha256 or len(answer.assignments)!=len(case.children) or len(answer.base_proof.triangles)!=len(case.children) or answer.dependencies!=tuple(sorted(panels)):return dict(status='UNKNOWN_FINAL_INCOMPLETE_RESULT',started=True,partial_assignment_discarded=True)
  return dict(status='NOMINAL_EXACT_REAL_OPPORTUNITY_ONLY',started=True,original_parent_occurrences=len(case.inventory.parents),complete_children=len(case.children),inventory_sha256=answer.inventory_sha256,physical_dependencies=answer.physical_dependencies,dependencies=answer.dependencies,assignments=[dict(child=i,source=s.key,panel=s.fixed.panel.identifier,face=s.fixed.face) for i,s in enumerate(assignments)],minimum_margins=dict(eye=str(min(t.min_eye_plane for t in answer.base_proof.triangles)),target=str(min(t.min_target_plane for t in answer.base_proof.triangles)),edge=str(min(t.min_edge_volume for t in answer.base_proof.triangles))),refusals=dict(failures),runtime_admitted=False)
 except Interrupted as e:return dict(status=str(e),started=started,partial_assignment_discarded=True)
 except (MemoryError,OverflowError):return dict(status='UNKNOWN_MEMORY_ALLOCATION',started=started,partial_assignment_discarded=True)
 finally:
  if started:budget.close()

def execute(cases,budget,p,oracle):
 rows=[];halt=None
 for case in cases:
  before=budget.used
  if halt:answer=dict(status=halt,started=False)
  else:
   try:answer=solve(case,budget,p,oracle)
   except (MemoryError,OverflowError):answer=dict(status='UNKNOWN_MEMORY_ALLOCATION',started=False,partial_assignment_discarded=True)
   if answer['status'] in ('UNTESTED_UNKNOWN_BUDGET','UNKNOWN_WALL_BUDGET','UNKNOWN_MEMORY_ALLOCATION'):halt=answer['status']
  rows.append(dict(case=case.identifier,case_fingerprint=case.expected_fingerprint,**answer,candidate_calls=budget.used[0]-before[0],candidate_edges_upper=budget.used[1]-before[1],final_child_checks_upper=budget.used[2]-before[2],final_edges_upper=budget.used[3]-before[3]))
 return rows

def own_sources(repo,source):
 if len(source)!=40 or any(x not in '0123456789abcdef' for x in source):raise ValueError('Exact runner source required')
 folder=Path(__file__).resolve().parent;result={}
 for name in OWNED:
  path=folder/name;rel=path.relative_to(repo.resolve()).as_posix();raw=subprocess.check_output(['git','-C',str(repo),'show',source+':'+rel])
  if path.read_bytes()!=raw:raise ValueError('Frozen runner source changed '+name)
  result[name]=pin(path)
 return result

def bind(repo,directory,ram):
 require(directory/'report.json',PLAN_SHA);require(directory/'PREPARATION-SEAL.json',SEAL_SHA);require(directory/'structural-controls.json',CONTROLS_SHA)
 d=json.loads((directory/'report.json').read_text());seal=json.loads((directory/'PREPARATION-SEAL.json').read_text());controls=json.loads((directory/'structural-controls.json').read_text())
 if d['preparation_source']!=PREPARATION_SOURCE or d['partition_source']!=prep.PARTITION_SOURCE or d['actual_shadow_predicates']!=0 or controls['private_shadow_predicates']!=0 or seal['runtime_admitted'] is not False:raise ValueError('Preparation provenance')
 if prep.own_sources(repo,PREPARATION_SOURCE)!=d['owned_sources']:raise ValueError('Frozen preparation sources drifted')
 p,ppin=prep.load(repo,prep.PARTITION_SOURCE,'port/dreamcast/tools/d367/triangle_partition24/partition.py','runtime_frozen_partition',ram,prep.PARTITION_SHA)
 old,oldpin=prep.load(repo,prep.RUNNER_SOURCE,'port/dreamcast/tools/d367/actual_triangle_audit24/runner.py','runtime_original_runner',ram,prep.RUNNER_SHA)
 original=old.bind(Path(d['prepared']['path']),Path(d['original_seal']['path']));oldcases=old.cases_from_report(original)
 if len(d['targets'])!=25 or len(d['plan'])!=75:raise ValueError('Complete target/domain census')
 loader,loaderpin=prep.load(repo,prep.LOADER_SOURCE,'port/dreamcast/tools/d367/patch2810_coverage24/coverage.py','runtime_original_reader',ram,original['loader']['sha256']);mesh=Path(original['inputs']['ps2-world.re4mesh']['path']).read_bytes();policy=Path(original['inputs']['ps2-world.r4pw']['path']).read_bytes();inputsha={k:v['sha256'] for k,v in original['inputs'].items()};rawcache={}
 def actual(physical):
  key=tuple(physical)
  if key not in rawcache:rawcache[key]=verify.raw_geometry(mesh,policy,key,loader)
  return rawcache[key]
 cases=[]
 for row,oldcase in zip(d['plan'],oldcases):
  rank=oldcase.identifier[0];t=d['targets'][rank];saved=original['targets'][rank]
  if tuple(row['case'])!=oldcase.identifier or t['rank']!=rank or t['physical']!=saved['physical'] or len(t['parents'])!=len(saved['complete_target_faces']):raise ValueError('Exact target tuple/parent inventory')
  parents=tuple(p.Parent(tuple(x['occurrence']),tuple(x['indices']),x['affine_sha256'],exact(x['positions_exact'])) for x in t['parents']);inv=p.Inventory(parents,t['source_binding_sha256'],t['original_inventory_sha256']);children=tuple(p.Child(tuple(x['parent']),x['identifier'],exact(x['basis']),exact(x['positions_exact'])) for x in t['children'])
  verify.authenticate_target_affine(t,saved,actual(saved['physical']),inputsha,p)
  for parent,face in zip(parents,saved['complete_target_faces']):
   if parent.occurrence!=(*saved['physical'],face['ordinal']) or parent.indices!=tuple(face['corners']) or parent.vertices!=exact(face['positions_exact']) or parent.affine_sha256!=t['affine_sha256']:raise ValueError('Actual original triangle binding')
  if len(t['sources'])!=len(oldcase.sources):raise ValueError('Complete source roster')
  sources=[]
  for source,olds in zip(t['sources'],oldcase.sources):
   if tuple(source['key'])!=olds.key:raise ValueError('Finite source order drift')
   if olds.reason:
    if source!={'key':list(olds.key),'status':olds.reason}:raise ValueError('Unrepresentable occurrence drift')
    sources.append(Source(olds.key,None,olds.reason));continue
   verify.authenticate_source_affine(source,actual(source['key'][:6]),inputsha)
   faces=tuple(exact(x) for x in source['faces_exact'])
   if tuple(source['physical_record'])!=olds.panel_record or faces!=olds.panel_faces or source['panel_id']!=olds.panel_id or source['face']!=olds.face:raise ValueError('Original full Panel source binding')
   panel=p.PhysicalPanel(source['panel_id'],tuple(source['physical_record']),source['source_binding_sha256'],faces);sources.append(Source(olds.key,p.FixedFace(panel,source['face'])))
  eye=exact(row['eye_box_exact'])
  if eye!=oldcase.eye_box:raise ValueError('Authentic whole eye domain drift')
  case=Case(oldcase.identifier,inv,children,tuple(sources),eye,'');case=dataclasses.replace(case,expected_fingerprint=prep.token(record(case)))
  if authenticate_case(case,p)!=dict((k,row[k]) for k in ('original_parents','canonical_children','source_faces',*prep.FIELDS)):raise ValueError('Fourfold wholecase reserve drift')
  cases.append(case)
 if sum(len(c.children) for c in cases)!=10668 or sum(len(c.inventory.parents) for c in cases)!=2667:raise ValueError('All75/889/3556 census')
 return d,tuple(cases),p,dict(partition=ppin,old_runner=oldpin,original_reader=loaderpin)

def grant_binding(source,review_sha,cases,output):
 return dict(issuer='/root',approved=True,scope='PARTITION24_PRIVATE_NOMINAL75_ONLY',runner_source=source,review_sha256=review_sha,partition_source=prep.PARTITION_SOURCE,generic_source=GENERIC_SOURCE,preparation_source=PREPARATION_SOURCE,plan_sha256=PLAN_SHA,seal_sha256=SEAL_SHA,controls_sha256=CONTROLS_SHA,cases_sha256=prep.token([c.expected_fingerprint for c in cases]),case_count=len(cases),limits=LIMITS,output=str(output.resolve()),new_rays=0,ledger_accesses=0,runtime_admitted=False)
def authorize(grant,grant_sha,review,review_sha,source,cases,output):
 if grant is None or review is None or grant_sha is None or review_sha is None:raise ValueError('Execute requires separately pinned root grant and source review')
 require(grant,grant_sha);require(review,review_sha)
 if json.loads(grant.read_text())!=grant_binding(source,review_sha,cases,output):raise ValueError('Root grant source/review/plan/cases/output/caps mismatch')
 return dict(grant=pin(grant),review=pin(review))

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--repo',type=Path,required=True);ap.add_argument('--prepared-directory',type=Path,required=True);ap.add_argument('--expected-source',required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--execute',action='store_true');ap.add_argument('--grant',type=Path);ap.add_argument('--grant-sha256');ap.add_argument('--review',type=Path);ap.add_argument('--review-sha256');a=ap.parse_args();start=time.monotonic();resource.setrlimit(resource.RLIMIT_AS,(LIMITS['address_bytes'],)*2)
 if a.out.exists() or a.out.resolve().is_relative_to(a.repo.resolve()) or a.out.resolve().is_relative_to(a.prepared_directory.resolve()):raise ValueError('Fresh external output outside preserved preparation required')
 sources=own_sources(a.repo,a.expected_source)
 with tempfile.TemporaryDirectory(prefix='partition24-run-',dir='/dev/shm') as temp:
  ram=Path(temp);d,cases,p,modules=bind(a.repo,a.prepared_directory,ram);budget=Budget(deadline=start+115)
  result=dict(classification='RUNNER_PREPARATION_ONLY_NO_SCENE_PREDICATES',source=a.expected_source,owned_sources=sources,owned_source_bytes=sum(x['bytes'] for x in sources.values()),frozen_modules=modules,prepared=pin(a.prepared_directory/'report.json'),preparation_seal=pin(a.prepared_directory/'PREPARATION-SEAL.json'),limits=LIMITS,cases_sha256=prep.token([c.expected_fingerprint for c in cases]),plan=[dict(case=c.identifier,case_fingerprint=c.expected_fingerprint,**authenticate_case(c,p)) for c in cases],grant_template=grant_binding(a.expected_source,'<independent-review-sha256>',cases,a.out),private_candidate_triangle_calls=0,private_final_assigned_batch_calls=0,new_rays=0,ledger_accesses=0,runtime_admitted=False,other9600_cases='UNTESTED_UNKNOWN',numeric_raster_prefix_current_runtime='UNQUALIFIED')
  if a.execute:
   result['authorization']=authorize(a.grant,a.grant_sha256,a.review,a.review_sha256,a.expected_source,cases,a.out)
   generic,gpin=prep.load(a.repo,GENERIC_SOURCE,'port/dreamcast/tools/d367/triangle_shadow24/exact_shadow.py','runtime_generic28c',ram,GENERIC_SHA);oracle=Oracle(generic)
   result.update(classification='NOMINAL_EXACT_REAL_OPPORTUNITY_ONLY_NO_RUNTIME_CERTIFICATE',results=execute(cases,budget,p,oracle),generic=gpin,work=budget.receipt(),private_candidate_triangle_calls=oracle.triangle_calls,private_final_assigned_batch_calls=oracle.assigned_calls)
  else:result['results']=[dict(case=c.identifier,status='UNTESTED_UNKNOWN',started=False) for c in cases]
  result['seconds']=time.monotonic()-start;result['peak_rss_kib']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
  raw=(json.dumps(result,indent=1)+'\n').encode()
  if len(raw)+65536>LIMITS['output_bytes'] or time.monotonic()-start>=120:raise ValueError('Output/wall cap; no result published')
  a.out.mkdir();(a.out/'report.json').write_bytes(raw);print(json.dumps(dict(classification=result['classification'],report=pin(a.out/'report.json'),seconds=result['seconds'],triangle_calls=result['private_candidate_triangle_calls'],assigned_calls=result['private_final_assigned_batch_calls'])),flush=True)
if __name__=='__main__':main()
