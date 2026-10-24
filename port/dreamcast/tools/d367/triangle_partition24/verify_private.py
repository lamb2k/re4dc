"""Structural private-plan controls ONLY; imports no shadow oracle."""
import argparse,dataclasses,hashlib,importlib.util,json,resource,subprocess,sys,tempfile,time
import prepare_private as prep
from fractions import Fraction as Q
from pathlib import Path
SOURCE=prep.PARTITION_SOURCE
def pin(p):return dict(path=str(p),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def tri(t):return tuple(tuple(Q(x) for x in p) for p in t)
reservation=prep.reservation
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--repo',type=Path,required=True);ap.add_argument('--plan',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--expected-plan-sha256',required=True);ap.add_argument('--expected-source',required=True);a=ap.parse_args();start=time.monotonic();owned=prep.own_sources(a.repo,a.expected_source);resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,)*2)
 if a.out.exists() or a.out.resolve().parent!=a.plan.resolve().parent:raise ValueError('Fresh output beside private report required')
 if {p.name for p in a.plan.parent.iterdir()}!={a.plan.name}:raise ValueError('Unexpected preparation output before controls')
 if pin(a.plan)['sha256']!=a.expected_plan_sha256:raise ValueError('Frozen private plan changed')
 d=json.loads(a.plan.read_text())
 if d['partition_source']!=SOURCE or d['preparation_source']!=a.expected_source or d['owned_sources']!=owned:raise ValueError('Frozen preparation source binding changed')
 expected_limits=dict(candidate_calls=100000,candidate_edge_upper=7200000,final_child_checks=10668,final_edge_upper=768096,wholecase_full_reservation_required=True,computation_deadline_seconds=115,wall_cap_seconds=120,address_cap_bytes=prep.RAM,output_cap_bytes=prep.OUTPUT,jobs=1)
 if d['proposed_limits']!=expected_limits:raise ValueError('Proposed bounded wholecase limits changed')
 raw=subprocess.check_output(['git','-C',str(a.repo),'show',SOURCE+':port/dreamcast/tools/d367/triangle_partition24/partition.py'])
 if hashlib.sha256(raw).hexdigest()!=d['partition']['sha256']:raise ValueError('Frozen partition module changed')
 ram=Path(tempfile.mkdtemp(prefix='partition24-structural-',dir='/dev/shm'));path=ram/'structural_partition.py';path.write_bytes(raw);spec=importlib.util.spec_from_file_location('structural_partition',path);p=importlib.util.module_from_spec(spec);sys.modules[spec.name]=p;spec.loader.exec_module(p)
 # No backend is loaded. Every prohibited proof entry is a tripwire.
 def prohibited(*args,**kwargs):raise AssertionError('Private shadow proof is not authorized')
 p.cover_partition=prohibited
 external=Path(d['prepared']['path'])
 if pin(external)!=d['prepared']:raise ValueError('Original external manifest changed')
 original=prep.load(a.repo,prep.RUNNER_SOURCE,'port/dreamcast/tools/d367/actual_triangle_audit24/runner.py','verify_original_runner',ram,prep.RUNNER_SHA)[0].bind(external,Path(d['original_seal']['path']));cases=prep.load(a.repo,prep.RUNNER_SOURCE,'port/dreamcast/tools/d367/actual_triangle_audit24/runner.py','verify_cases_runner',ram,prep.RUNNER_SHA)[0].cases_from_report(original);inventories=[];partitions=[]
 if len(d['targets'])!=len(original['targets']) or len(d['targets'])!=25:raise ValueError('Complete original target inventory')
 for target,old in zip(d['targets'],original['targets']):
  parents=tuple(p.Parent(tuple(x['occurrence']),tuple(x['indices']),x['affine_sha256'],tri(x['positions_exact'])) for x in target['parents']);inv=p.Inventory(parents,target['source_binding_sha256'],target['original_inventory_sha256']);children=tuple(p.Child(tuple(x['parent']),x['identifier'],tri(x['basis']),tri(x['positions_exact'])) for x in target['children'])
  if target['physical']!=old['physical'] or target['rank']!=old['rank'] or len(parents)!=len(old['complete_target_faces']):raise ValueError('Original full tuple/inventory identity')
  for x,y in zip(parents,old['complete_target_faces']):
   if x.indices!=tuple(y['corners']) or x.vertices!=tri(y['positions_exact']) or x.occurrence!=(*old['physical'],y['ordinal']):raise ValueError('Original occurrence/index/affine position binding')
  if hashlib.sha256(bytes.fromhex(target['affine_operand_bytes_hex'])).hexdigest()!=target['affine_sha256'] or any(x.affine_sha256!=target['affine_sha256'] for x in parents):raise ValueError('Exact affine operands')
  if len(target['sources'])!=len(old['source_faces']) or [x['key'] for x in target['sources']]!=[x['key'] for x in old['source_faces']]:raise ValueError('Retained finite source roster')
  answer=p.validate_partition(inv,children)
  if type(answer)is p.Unknown or len(children)!=4*len(parents):raise ValueError('Complete exact canonical children')
  for source,oldsource in zip(target['sources'],cases[3*target['rank']].sources):
   if oldsource.reason:
    if source!={'key':list(oldsource.key),'status':oldsource.reason}:raise ValueError('Explicit unrepresentable source occurrence changed')
   else:
    if tuple(source['physical_record'])!=oldsource.panel_record or tuple(tri(t) for t in source['faces_exact'])!=oldsource.panel_faces or source['panel_id']!=oldsource.panel_id or source['face']!=oldsource.face:raise ValueError('Full unchanged actual source Panel')
    panel=p.PhysicalPanel(source['panel_id'],tuple(source['physical_record']),source['source_binding_sha256'],tuple(tri(t) for t in source['faces_exact']));p._panel(p.FixedFace(panel,source['face']),p.Limits())
  inventories.append(inv);partitions.append(children)
 if len(inventories)!=25 or sum(len(x.parents) for x in inventories)!=889 or sum(len(x) for x in partitions)!=3556:raise ValueError('Complete all25 manifest')
 if len(d['plan'])!=75 or d['proposed_limits']['final_child_checks']!=10668:raise ValueError('Finite75/10668 plan')
 for row,case in zip(d['plan'],cases):
  reservation(row)
  target=d['targets'][case.identifier[0]]
  if tuple(row['case'])!=case.identifier or row['source_faces']!=len(target['sources']) or row['original_parents']!=len(target['parents']) or row['eye_box_exact']!=[[str(v) for v in point] for point in case.eye_box]:raise ValueError('Complete same-domain wholecase binding')
 if sum(row['whole_case_final_child_calls_reserve'] for row in d['plan'])!=10668 or sum(row['final_edge_upper_reserve'] for row in d['plan'])!=768096:raise ValueError('All75 final reserve')
 inv=inventories[0];ch=partitions[0];controls={}
 candidates={'missing_central_child':ch[:3]+ch[4:],'duplicate_corner_for_central':ch[:3]+(ch[0],)+ch[4:],'reverse_central_winding':ch[:3]+(dataclasses.replace(ch[3],vertices=tuple(reversed(ch[3].vertices))),)+ch[4:],'wrong_parent_id':ch[:3]+(dataclasses.replace(ch[3],parent=ch[4].parent),)+ch[4:],'wrong_barycentric_basis':ch[:3]+(dataclasses.replace(ch[3],basis=ch[0].basis),)+ch[4:]}
 for name,mutant in candidates.items():
  answer=p.validate_partition(inv,mutant)
  if type(answer)is not p.Unknown:raise ValueError('Structural mutant accepted '+name)
  controls[name]=answer.reason
 variants={'missing_original_parent':dataclasses.replace(inv,parents=inv.parents[:-1]),'duplicate_original_occurrence':dataclasses.replace(inv,parents=(inv.parents[0],)+inv.parents[:-1]),'wrong_original_indices':dataclasses.replace(inv,parents=(dataclasses.replace(inv.parents[0],indices=tuple(reversed(inv.parents[0].indices))),)+inv.parents[1:]),'wrong_affine_pin':dataclasses.replace(inv,parents=(dataclasses.replace(inv.parents[0],affine_sha256='d'*64),)+inv.parents[1:])}
 for name,mutant in variants.items():
  answer=p.validate_partition(mutant,ch)
  if type(answer)is not p.Unknown:raise ValueError('Original mutant accepted '+name)
  controls[name]=answer.reason
 for field in ('whole_case_candidate_calls_reserve','whole_case_final_child_calls_reserve'):
  bad=dict(d['plan'][0]);bad[field]//=4
  try:reservation(bad)
  except ValueError as e:controls['old_factor1_'+field]=str(e)
  else:raise ValueError('Fourfold reservation mutant accepted')
 for i,field in enumerate(prep.FIELDS):
  valid=prep.reservation(d['plan'][0]);caps=tuple(v-(1 if j==i else 0) for j,v in enumerate(valid));budget=prep.Budget(caps)
  if budget.reserve(d['plan'][0]) or budget.reserved!=(0,0,0,0):raise ValueError('Wholecase budget shortage entered work')
  controls['prework_cap_shortage_'+field]='REFUSED_ATOMICALLY'
 result=dict(classification='PRIVATE_STRUCTURAL_PARTITION_CONTROLS_NO_SHADOW_PREDICATES',source=SOURCE,preparation_source=a.expected_source,owned_sources=owned,tool=pin(Path(__file__)),plan=pin(a.plan),targets=25,original_parent_occurrences=889,canonical_children=3556,wholecase_plans=75,negative_refusals=controls,private_shadow_predicates=0,new_rays=0,ledger_accesses=0,runtime_admitted=False)
 raw=(json.dumps(result,indent=2)+'\n').encode()
 if sum(p.stat().st_size for p in a.plan.parent.iterdir())+len(raw)+65536>prep.OUTPUT or time.monotonic()-start>=120:raise ValueError('All preparation outputs/wall cap')
 a.out.write_bytes(raw);print(json.dumps(result))
if __name__=='__main__':main()
