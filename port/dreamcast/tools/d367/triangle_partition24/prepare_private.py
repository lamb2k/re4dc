"""Private inventory and fourfold budget PREPARATION. No shadow oracle calls."""
import argparse,hashlib,importlib.util,json,resource,struct,subprocess,sys,tempfile,time
from fractions import Fraction as Q
from pathlib import Path
PARTITION_SOURCE='4305e0eca9b0f5261a67ab3433e09ab63c9537db'
PARTITION_SHA='f227a5bf26ae4d65ca97481f92d3e3220beee3cbbf6979cd8299ba1b827f0278'
RUNNER_SOURCE='78cbd962ee0d98dc700d0fb452500a16ac35b14c'
LOADER_SOURCE='f48fd69f47c914d57b229606556719c53ac73543'
REPORT_SHA='22b2fe4dc83c0a0ba846eefb822fe1dead4bbbaa850b1e838dc5eaaadc56d57c'
SEAL_SHA='ef328388f80574e2fc41bf4f01a9b983822c6b20a28c8844a72eafdc7c17e265'
RUNNER_SHA='16b5ee651f6d9c7aea3e709d104d4b30aad7f22fc13bd574f0da666dc4b2d71d'
RAM=256*1024*1024;OUTPUT=16*1024*1024
OWNED=('partition.py','test_partition.py','prepare_private.py','verify_private.py','test_preparation.py','seal_private.py','README.md','PRIVATE-PREPARATION.md','origin-before-helper-checkpoint.txt')
CAPS=(100000,7200000,10668,768096)
FIELDS=('whole_case_candidate_calls_reserve','candidate_edge_upper_reserve','whole_case_final_child_calls_reserve','final_edge_upper_reserve')
def reservation(row):
 f=row['original_parents'];n=row['canonical_children'];s=row['source_faces']
 if any(type(x)is not int or x<0 for x in (f,n,s)) or f==0 or n!=4*f:raise ValueError('Complete fourfold wholecase inventory required')
 expected=(n*s,72*n*s,n,72*n)
 if any(type(row[k])is not int or row[k]!=v for k,v in zip(FIELDS,expected)):raise ValueError('Complete fourfold wholecase reserve required')
 return expected
class Budget:
 """PREPARATION arithmetic only: reserve ALL four limits atomically before work.
 There is no scene-work method, oracle, execution loop or grant in this class.
 """
 def __init__(self,caps=CAPS):
  if type(caps)is not tuple or len(caps)!=4 or any(type(x)is not int or x<0 for x in caps) or any(x>y for x,y in zip(caps,CAPS)):raise ValueError('Bounded candidate/final caps required')
  self.caps=caps;self.reserved=(0,0,0,0)
 def reserve(self,row):
  values=reservation(row)
  if any(v>cap-used for v,cap,used in zip(values,self.caps,self.reserved)):return False
  self.reserved=tuple(used+v for used,v in zip(self.reserved,values));return True

def own_sources(repo,expected_source):
 if len(expected_source)!=40 or any(x not in '0123456789abcdef' for x in expected_source):raise ValueError('Exact source commit required')
 root=Path(__file__).resolve().parent;result={}
 for name in OWNED:
  path=root/name;rel=path.relative_to(repo.resolve()).as_posix();data=subprocess.check_output(['git','-C',str(repo),'show',expected_source+':'+rel])
  if path.read_bytes()!=data:raise ValueError('Preparation source bytes differ from frozen commit: '+name)
  result[name]=pin(path)
 return result


def pin(p):return dict(path=str(p),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def load(repo,commit,rel,name,ram,expected=None):
 data=subprocess.check_output(['git','-C',str(repo),'show',commit+':'+rel])
 if expected is not None and hashlib.sha256(data).hexdigest()!=expected:raise ValueError('Frozen source mismatch '+name)
 dest=ram/(name+'.py');dest.write_bytes(data);spec=importlib.util.spec_from_file_location(name,dest);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m,pin(dest)
def encoded(x):return json.dumps(x,sort_keys=True,separators=(',',':')).encode()
def token(x):return hashlib.sha256(encoded(x)).hexdigest()
def exact(t):return [[str(v) for v in point] for point in t]
def manifest(p):return dict(occurrence=p.occurrence,indices=p.indices,affine_sha256=p.affine_sha256,positions_exact=exact(p.vertices))
def child_manifest(c):return dict(parent=c.parent,identifier=c.identifier,basis=exact(c.basis),positions_exact=exact(c.vertices))

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--repo',type=Path,required=True);ap.add_argument('--prepared',type=Path,required=True);ap.add_argument('--seal',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--expected-source',required=True);a=ap.parse_args();start=time.monotonic();resource.setrlimit(resource.RLIMIT_AS,(RAM,RAM));owned=own_sources(a.repo,a.expected_source)
 if a.out.exists() or a.out.resolve().is_relative_to(a.repo.resolve()):raise ValueError('Fresh private output required')
 if pin(a.prepared)['sha256']!=REPORT_SHA or pin(a.seal)['sha256']!=SEAL_SHA:raise ValueError('Exact external original inventory required')
 ram=Path(tempfile.mkdtemp(prefix='partition24-prep-',dir='/dev/shm'))
 old,oldpin=load(a.repo,RUNNER_SOURCE,'port/dreamcast/tools/d367/actual_triangle_audit24/runner.py','old_frozen_runner',ram,RUNNER_SHA)
 d=old.bind(a.prepared,a.seal);cases=old.cases_from_report(d)
 part,partpin=load(a.repo,PARTITION_SOURCE,'port/dreamcast/tools/d367/triangle_partition24/partition.py','frozen_partition',ram,PARTITION_SHA)
 loader,loaderpin=load(a.repo,LOADER_SOURCE,'port/dreamcast/tools/d367/patch2810_coverage24/coverage.py','frozen_original_reader',ram,d['loader']['sha256'])
 mesh=Path(d['inputs']['ps2-world.re4mesh']['path']).read_bytes();policy=Path(d['inputs']['ps2-world.r4pw']['path']).read_bytes();h=struct.unpack_from('<4s19I',mesh);hp=struct.unpack_from('<4s7I',policy);inputsha={k:v['sha256'] for k,v in d['inputs'].items()};cache={}
 def physical_geometry(key):
  key=tuple(key)
  if key not in cache:
   pi,field,pr,cl,lv,li=key;cc,triangles,native=loader.raw_let(mesh,li);world,_,det,pl,mr=loader.raw_mapping(mesh,policy,pi)
   if not det or pl[1]!=field:raise ValueError('Original physical affine identity')
   po=32+16*hp[3]+52*pi;mi=struct.unpack_from('<H',policy,po)[0];mo=h[10]+68*mi;operands=policy[po+4:po+52]+mesh[mo+20:mo+44]
   xyz=tuple(world(c) for c in cc);cache[key]=dict(corners=cc,triangles=triangles,xyz=xyz,affine_operand_bytes_hex=operands.hex(),affine_sha256=hashlib.sha256(operands).hexdigest())
  return cache[key]
 # FIRST establish EVERY original actual occurrence for ALL25 targets.
 originals=[]
 for row in d['targets']:
  physical=tuple(row['physical']);g=physical_geometry(physical);saved=row['complete_target_faces']
  if len(saved)!=len(g['triangles']) or [x['ordinal'] for x in saved]!=list(range(len(saved))):raise ValueError('Complete original inventory extent/order')
  parents=[]
  for ordinal,(tri,r) in enumerate(zip(g['triangles'],saved)):
   vertices=tuple(g['xyz'][j] for j in tri)
   if tuple(r['corners'])!=tuple(tri) or vertices!=tuple(tuple(Q(v) for v in p) for p in r['positions_exact']):raise ValueError('Original actual parity/indices/exact affine mismatch')
   parents.append(part.Parent((*physical,ordinal),tuple(tri),g['affine_sha256'],vertices))
  binding=token(dict(prepared=REPORT_SHA,inputs=inputsha,physical=physical,affine=g['affine_sha256'],original_let_index=row['target']['meshlet']))
  parents=tuple(parents);inv=part.Inventory(parents,binding,part.inventory_digest(parents,binding));originals.append((row,inv,g))
 if len(originals)!=25 or sum(len(inv.parents) for _,inv,_ in originals)!=889:raise ValueError('Complete fixed25/889 original manifest required BEFORE partition')
 # Sources are only the SAME retained roster, rederived from the SAME actual bytes.
 targets=[];source_occurrences=0
 for row,inv,g in originals:
  rank=row['rank'];oldcase=cases[3*rank];sources=[]
  if len(oldcase.sources)!=len(row['source_faces']):raise ValueError('Complete retained source occurrence inventory')
  for spec,r in zip(oldcase.sources,row['source_faces']):
   if spec.key!=tuple(r['key']):raise ValueError('Saved source order changed')
   source_occurrences+=1
   if spec.reason:
    sources.append(dict(key=spec.key,status=spec.reason));continue
   key=spec.key[:6];sg=physical_geometry(key);oa,ob=r['panel_face_ordinals'];indices=(tuple(sg['triangles'][oa]),tuple(sg['triangles'][ob]));record=(*key[:4],key[5],*indices[0],*indices[1]);faces=tuple(tuple(sg['xyz'][j] for j in t) for t in indices)
   if record!=spec.panel_record or faces!=spec.panel_faces:raise ValueError('Original full source Panel changed')
   sourcebinding=token(dict(prepared=REPORT_SHA,inputs=inputsha,physical=key,affine=sg['affine_sha256'],record=record,ordinals=[oa,ob]))
   panel=part.PhysicalPanel(spec.panel_id,record,sourcebinding,faces);fixed=part.FixedFace(panel,spec.face)
   # Structural full-record validation only, NEVER cover_partition or generic predicates.
   part._panel(fixed,part.Limits())
   sources.append(dict(key=spec.key,status='UNCHANGED_RETAINED_ACTUAL_SOURCE',panel_id=spec.panel_id,physical_record=record,source_binding_sha256=sourcebinding,affine_sha256=sg['affine_sha256'],actual_ordinals=[oa,ob],faces_exact=[exact(t) for t in faces],face=spec.face))
  if len(sources)!=len(row['source_faces']):raise ValueError('Complete unchanged source roster')
  children=part.canonical_partition(inv)
  if type(children)is part.Unknown:raise ValueError('Whole target partition refused: '+children.reason)
  validated=part.validate_partition(inv,children)
  if type(validated)is part.Unknown or len(children)!=4*len(inv.parents):raise ValueError('Complete canonical partition required')
  targets.append(dict(rank=rank,physical=row['physical'],original_target=row['target'],authored_counts=row['authored_counts'],fresh_effective_lod_guard_required=row['fresh_effective_lod_guard_required'],source_binding_sha256=inv.source_binding_sha256,original_inventory_sha256=inv.expected_inventory_sha256,affine_operand_bytes_hex=g['affine_operand_bytes_hex'],affine_sha256=g['affine_sha256'],parents=[manifest(p) for p in inv.parents],children=[child_manifest(c) for c in children],sources=sources,unrepresentable_source_faces=row['unrepresentable_source_faces']))
 if source_occurrences!=1036 or sum(len(t['children']) for t in targets)!=3556:raise ValueError('Finite unchanged source/partition census')
 plan=[]
 for case in cases:
  rank=case.identifier[0];t=targets[rank];n=len(t['children']);sources=len(t['sources'])
  plan.append(dict(case=case.identifier,original_parents=len(t['parents']),canonical_children=n,source_faces=sources,unrepresentable=len(t['unrepresentable_source_faces']),whole_case_candidate_calls_reserve=n*sources,candidate_edge_upper_reserve=72*n*sources,whole_case_final_child_calls_reserve=n,final_edge_upper_reserve=72*n,original_inventory_sha256=t['original_inventory_sha256'],eye_box_exact=[[str(x) for x in point] for point in case.eye_box]))
 for row in plan:reservation(row)
 expected=sum(len(t['children']) for t in targets)*3
 if expected!=10668 or len(plan)!=75:raise ValueError('Fixed final10668/75 plan')
 out=dict(classification='CANONICAL_PARTITION_PRIVATE_PREPARATION_ONLY_NO_SHADOW_PREDICATES',tool=pin(Path(__file__)),preparation_source=a.expected_source,owned_sources=owned,owned_source_bytes=sum(p['bytes'] for p in owned.values()),base='fb254e82ee6f9a3d9e34d53d1d442348a46b9cf2',partition_source=PARTITION_SOURCE,partition=partpin,old_runner_source=RUNNER_SOURCE,old_runner=oldpin,original_reader_source=LOADER_SOURCE,original_reader=loaderpin,prepared=pin(a.prepared),original_seal=pin(a.seal),inputs=d['inputs'],source=d['source'],material_pins=d['material_pins'],source_capability=d['capability'],authentic_cameras=d['authentic_camera_logs'],targets=targets,plan=plan,held_camera_cases=dict(total=9600,status='UNTESTED_UNKNOWN',all_target_ranks=list(range(25)),domains=[dict(label=x['label'],frame=x['frame'],size_mm=x['size_mm'],old_cell=x['old_cell']) for x in d['domains'] if(x['label'],x['frame'])!=('hut',647)]),summary=dict(targets=25,original_parent_occurrences=889,canonical_children=3556,source_face_occurrences=1036,wholelet_domain_cases=75,candidate_calls_exhaustive_upper=sum(x['whole_case_candidate_calls_reserve'] for x in plan),candidate_edge_exhaustive_upper=sum(x['candidate_edge_upper_reserve'] for x in plan),final_child_checks_exhaustive_upper=expected,final_edge_exhaustive_upper=72*expected),proposed_limits=dict(candidate_calls=100000,candidate_edge_upper=7200000,final_child_checks=10668,final_edge_upper=768096,wholecase_full_reservation_required=True,computation_deadline_seconds=115,wall_cap_seconds=120,address_cap_bytes=RAM,output_cap_bytes=OUTPUT,jobs=1),actual_shadow_predicates=0,new_rays=0,ledger_accesses=0,runtime_admitted=False,limitations=['Canonical child arithmetic is proof-domain preparation only; microgeometry NEVER rendered.','Complete original inventory/indices/affine operands were rederived before any child; every parent keeps all4 ordered canonical children.','Same fixed physical sources/full Panel records and authentic whole eye domains, no source-pool or domain change.','No actual source face/child coverage has been tested; all75cases untested under this new sufficient condition.','Remaining9600other-camera cases UNTESTED_UNKNOWN; no exposure/gain inferred.','Original target effectiveLOD1 tuples retained; fresh LOD guards remain necessary.','Numeric/raster/source-prefix/material/emission/frame/lifetime/SH4/current-source qualification remains external/unqualified.'])
 out['limits']=dict(seconds=time.monotonic()-start,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,address_cap_bytes=RAM,output_cap_bytes=OUTPUT,jobs=1);raw=(json.dumps(out,indent=1)+'\n').encode()
 if len(raw)+65536>OUTPUT or time.monotonic()-start>=120:raise ValueError('Preparation output/wall cap')
 a.out.mkdir();(a.out/'report.json').write_bytes(raw);print(json.dumps(dict(classification=out['classification'],report=pin(a.out/'report.json'),summary=out['summary'],limits=out['limits'],shadow_predicates=0)),flush=True)
if __name__=='__main__':main()
