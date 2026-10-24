"""Structural private-plan controls ONLY; imports no shadow oracle."""
import argparse,copy,dataclasses,hashlib,importlib.util,json,resource,struct,subprocess,sys,tempfile,time
import prepare_private as prep
from fractions import Fraction as Q
from pathlib import Path
SOURCE=prep.PARTITION_SOURCE
def pin(p):return dict(path=str(p),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def tri(t):return tuple(tuple(Q(x) for x in p) for p in t)
reservation=prep.reservation
def raw_geometry(mesh,policy,physical,loader):
 pi,field,part,cluster,lod,let=physical;h=struct.unpack_from('<4s19I',mesh);hp=struct.unpack_from('<4s7I',policy)
 corners,triangles,_=loader.raw_let(mesh,let);world,_,det,placement,_=loader.raw_mapping(mesh,policy,pi)
 if not det or placement[1]!=field:raise ValueError('Actual physical affine identity')
 po=32+16*hp[3]+52*pi;mi=struct.unpack_from('<H',policy,po)[0];mo=h[10]+68*mi;operands=policy[po+4:po+52]+mesh[mo+20:mo+44]
 return dict(triangles=triangles,xyz=tuple(world(c) for c in corners),operands=operands,affine_sha256=hashlib.sha256(operands).hexdigest())
def authenticate_target_affine(target,old,raw,inputsha,p):
 physical=tuple(old['physical']);actual=raw['affine_sha256']
 if target['affine_operand_bytes_hex']!=raw['operands'].hex() or target['affine_sha256']!=actual:raise ValueError('Actual raw target affine operands differ')
 binding=prep.token(dict(prepared=prep.REPORT_SHA,inputs=inputsha,physical=physical,affine=actual,original_let_index=old['target']['meshlet']))
 parents=tuple(p.Parent((*physical,i),tuple(tri),actual,tuple(raw['xyz'][j] for j in tri)) for i,tri in enumerate(raw['triangles']))
 if target['source_binding_sha256']!=binding or target['original_inventory_sha256']!=p.inventory_digest(parents,binding) or any(x['affine_sha256']!=actual for x in target['parents']):raise ValueError('Actual target affine inventory binding differs')
def authenticate_source_affine(source,raw,inputsha):
 key=tuple(source['key']);a,b=source['actual_ordinals'];indices=(tuple(raw['triangles'][a]),tuple(raw['triangles'][b]));record=(*key[:4],key[5],*indices[0],*indices[1]);faces=tuple(tuple(raw['xyz'][j] for j in t) for t in indices)
 binding=prep.token(dict(prepared=prep.REPORT_SHA,inputs=inputsha,physical=key[:6],affine=raw['affine_sha256'],record=record,ordinals=[a,b]))
 if source['affine_sha256']!=raw['affine_sha256'] or source['source_binding_sha256']!=binding or tuple(source['physical_record'])!=record or tuple(tri(t) for t in source['faces_exact'])!=faces:raise ValueError('Actual raw source affine Panel binding differs')
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
 loader=prep.load(a.repo,prep.LOADER_SOURCE,'port/dreamcast/tools/d367/patch2810_coverage24/coverage.py','verify_raw_reader',ram,original['loader']['sha256'])[0]
 mesh=Path(original['inputs']['ps2-world.re4mesh']['path']).read_bytes();policy=Path(original['inputs']['ps2-world.r4pw']['path']).read_bytes();inputsha={k:v['sha256'] for k,v in original['inputs'].items()};rawcache={}
 def actual(physical):
  key=tuple(physical)
  if key not in rawcache:rawcache[key]=raw_geometry(mesh,policy,key,loader)
  return rawcache[key]
 for target,old in zip(d['targets'],original['targets']):
  parents=tuple(p.Parent(tuple(x['occurrence']),tuple(x['indices']),x['affine_sha256'],tri(x['positions_exact'])) for x in target['parents']);inv=p.Inventory(parents,target['source_binding_sha256'],target['original_inventory_sha256']);children=tuple(p.Child(tuple(x['parent']),x['identifier'],tri(x['basis']),tri(x['positions_exact'])) for x in target['children'])
  if target['physical']!=old['physical'] or target['rank']!=old['rank'] or len(parents)!=len(old['complete_target_faces']):raise ValueError('Original full tuple/inventory identity')
  for x,y in zip(parents,old['complete_target_faces']):
   if x.indices!=tuple(y['corners']) or x.vertices!=tri(y['positions_exact']) or x.occurrence!=(*old['physical'],y['ordinal']):raise ValueError('Original occurrence/index/affine position binding')
  authenticate_target_affine(target,old,actual(old['physical']),inputsha,p)
  if len(target['sources'])!=len(old['source_faces']) or [x['key'] for x in target['sources']]!=[x['key'] for x in old['source_faces']]:raise ValueError('Retained finite source roster')
  answer=p.validate_partition(inv,children)
  if type(answer)is p.Unknown or len(children)!=4*len(parents):raise ValueError('Complete exact canonical children')
  for source,oldsource in zip(target['sources'],cases[3*target['rank']].sources):
   if oldsource.reason:
    if source!={'key':list(oldsource.key),'status':oldsource.reason}:raise ValueError('Explicit unrepresentable source occurrence changed')
   else:
    authenticate_source_affine(source,actual(source['key'][:6]),inputsha)
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
 mutant=copy.deepcopy(d['targets'][0]);operands=bytearray.fromhex(mutant['affine_operand_bytes_hex']);operands[0]^=1;mutant['affine_operand_bytes_hex']=operands.hex();mutant['affine_sha256']=hashlib.sha256(operands).hexdigest()
 for parent in mutant['parents']:parent['affine_sha256']=mutant['affine_sha256']
 mutant['source_binding_sha256']=prep.token(dict(prepared=prep.REPORT_SHA,inputs=inputsha,physical=tuple(mutant['physical']),affine=mutant['affine_sha256'],original_let_index=mutant['original_target']['meshlet']))
 fabricated=tuple(p.Parent(tuple(x['occurrence']),tuple(x['indices']),x['affine_sha256'],tri(x['positions_exact'])) for x in mutant['parents']);mutant['original_inventory_sha256']=p.inventory_digest(fabricated,mutant['source_binding_sha256'])
 try:authenticate_target_affine(mutant,original['targets'][0],actual(mutant['physical']),inputsha,p)
 except ValueError as e:controls['consistent_target_affine_operand_token_inventory_rebind']=str(e)
 else:raise ValueError('Consistent fabricated affine operands accepted')
 source=copy.deepcopy(next(s for s in d['targets'][0]['sources'] if 'panel_id'in s));source['affine_sha256']='d'*64;key=tuple(source['key']);source['source_binding_sha256']=prep.token(dict(prepared=prep.REPORT_SHA,inputs=inputsha,physical=key[:6],affine=source['affine_sha256'],record=source['physical_record'],ordinals=source['actual_ordinals']))
 try:authenticate_source_affine(source,actual(key[:6]),inputsha)
 except ValueError as e:controls['consistent_source_affine_panel_binding_rebind']=str(e)
 else:raise ValueError('Consistent fabricated source affine binding accepted')
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
