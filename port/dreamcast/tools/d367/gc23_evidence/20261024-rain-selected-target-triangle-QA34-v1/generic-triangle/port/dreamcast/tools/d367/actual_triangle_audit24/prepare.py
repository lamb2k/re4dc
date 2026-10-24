"""Read-only actual-triangle binding and work census. Deliberately NO proof API."""
import argparse,collections,hashlib,importlib.util,itertools,json,resource,struct,subprocess,sys,tempfile,time,zlib
from fractions import Fraction as Q
from pathlib import Path
BASE='fb254e82ee6f9a3d9e34d53d1d442348a46b9cf2'
LOADER='f48fd69f47c914d57b229606556719c53ac73543'
GENERIC='28c739468ae7d2d2d3c09f81330015e7769dc824'
DISCOVERY='b0d4e84c3b7024bafc276e0171294cbfbf96bc03bc1d3d2b888f9dddd86224a7'
CAP='4cd7f0eef390f9e80ac4e0b82b9fdd919b53e181254c0dce332042c3c7fdd4f5'
LIMIT=256*1024*1024;OUTPUT=16*1024*1024
OLD={8:(18,19,20),12:(20,19,24),13:(25,24,19),14:(24,25,26)}
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def pin(p):return dict(path=str(p),bytes=Path(p).stat().st_size,sha256=sha(p))
def require(p,expected):
 if sha(p)!=expected['sha256'] or Path(p).stat().st_size!=expected['bytes']:raise ValueError('Input pin mismatch '+str(p))
def load(repo,commit,rel,name,ram):
 data=subprocess.check_output(['git','-C',str(repo),'show',commit+':'+rel]);p=ram/(name+'.py');p.write_bytes(data)
 spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m,pin(p)
def physical(s):return tuple(s[k] for k in ('placement','field','part','cluster','level','meshlet'))
def check_inventory(actual,claimed):
 if actual!=claimed:raise ValueError('Incomplete or reordered target inventory')
def validate_component(actual,positions,saved):
 faces={}
 for ordinal,*tri in saved:
  if ordinal in faces or not 0<=ordinal<len(actual) or tuple(actual[ordinal])!=tuple(tri):raise ValueError('Component actual face ordinal/parity')
  faces[ordinal]=tuple(tri)
 def nondeg(t):
  a,b,c=(positions[i] for i in t);u=tuple(y-x for x,y in zip(a,b));v=tuple(y-x for x,y in zip(a,c))
  return any((u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]))
 if not faces or any(not nondeg(t) for t in faces.values()):raise ValueError('Retained component exact degeneracy')
 edges=collections.defaultdict(set)
 for i,t in enumerate(actual):
  if nondeg(t):
   for a,b in zip(t,t[1:]+t[:1]):edges[tuple(sorted((a,b)))].add(i)
 reached={min(faces)};todo=list(reached)
 while todo:
  t=actual[todo.pop()]
  for a,b in zip(t,t[1:]+t[:1]):
   for j in edges[tuple(sorted((a,b)))]-reached:reached.add(j);todo.append(j)
 if reached!=set(faces):raise ValueError('Incomplete retained matched component')
 return faces

def prefix_guard(source,target):
 if source['placement']>=target['placement'] or (source['placement'],source['cluster'])==(target['placement'],target['cluster']):raise ValueError('Source prefix/self guard')

def adjacent(a,b):
 return a!=b and any((u,v)==(y,x) for u,v in zip(a,a[1:]+a[:1]) for x,y in zip(b,b[1:]+b[:1]))
def panels(faces,nondegenerate):
 """Each key is an actual face ordinal. Partners remain within retained roster."""
 out={};missing=[]
 for ordinal,tri in sorted(faces.items()):
  buddies=[j for j,t in sorted(faces.items()) if j!=ordinal and nondegenerate[j] and adjacent(tri,t)] if nondegenerate[ordinal] else []
  if not buddies:missing.append(ordinal);continue
  buddy=buddies[0];a,b=sorted((ordinal,buddy));out[ordinal]=(a,b,tuple(faces[a]+faces[b]))
 return out,missing
def id_atlas(records):
 ordered=sorted(set(records));atlas={r:i+1 for i,r in enumerate(ordered)}
 if len(atlas)!=len(ordered) or len(set(atlas.values()))!=len(ordered):raise ValueError('Panel ID collision')
 return atlas
def precount(faces,sources,cells=387):
 return dict(domains=cells,target_faces=faces,source_faces=sources,primitive_calls_upper=faces*sources*cells,edge_determinants_upper=72*faces*sources*cells,plane_evaluations_upper=11*faces*sources*cells,final_assignment_edge_upper=72*faces*cells)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--repo',type=Path,required=True);ap.add_argument('--evidence',type=Path,required=True);ap.add_argument('--audit',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
 resource.setrlimit(resource.RLIMIT_AS,(LIMIT,LIMIT));start=time.monotonic();ram=Path(tempfile.mkdtemp(prefix='triangle-prep24-',dir='/dev/shm'))
 if a.out.exists() or a.out.is_relative_to(a.repo):raise ValueError('Fresh private external output required')
 if subprocess.check_output(['git','-C',str(a.repo),'rev-parse',BASE],text=True).strip()!=BASE:raise ValueError('Missing frozen integration')
 c,loaderpin=load(a.repo,LOADER,'port/dreamcast/tools/d367/patch2810_coverage24/coverage.py','bound_loader',ram)
 # Generic source is authenticated but NEVER imported/called on private data.
 generic=subprocess.check_output(['git','-C',str(a.repo),'show',GENERIC+':port/dreamcast/tools/d367/triangle_shadow24/exact_shadow.py'])
 if hashlib.sha256(generic).hexdigest()!='9c0f85d588be2020a1506325da078e27a99c23b81f783ff3db268f6082a64f41':raise ValueError('Generic helper source mismatch')
 au=json.loads(a.audit.read_text());c.require(a.audit,dict(sha256=c.AUDIT_SHA,bytes=16627));old=json.loads(Path(au['input']['path']).read_text());c.require(Path(au['input']['path']),au['input'])
 path=a.evidence/'I001-discovery24-effective0-r1/run-r1/report.json'
 if sha(path)!=DISCOVERY:raise ValueError('Discovery census changed')
 d=json.loads(path.read_text());frozen,mathram,mathpins,f,s,_,_=c.snapshot(a.repo,au,old)
 for item in d['inputs'].values():require(Path(item['path']),item)
 r6=a.evidence/'I001-fb254-lod-surface-r6';profile=r6/'current-resolved-knobs.txt';source=f.audit.bind_source(Path('/root/probe/interior-discovery24'),profile)
 if source['files']!=d['source']['files'] or source['knobs']!=d['source']['knobs']:raise ValueError('Source/profile mismatch')
 cap_path=Path(d['capability']['receipt_path'])
 if sha(cap_path)!=CAP:raise ValueError('Capability receipt mismatch')
 cap=json.loads(cap_path.read_text())
 if cap['runtime_admitted'] is not False or cap['status']!='HOST_COMPILED_CAPABILITY_ONLY' or cap['compiled_macros']!={'RE4DC_PS2_PVS_EFFECTIVE0_SOURCES':1,'RE4DC_PS2_WORLD_NONEMPTY_LOD':1,'RE4DC_MESH_LOD':1,'RE4DC_PS2_WORLD_MESH':1}:raise ValueError('Wrong future source capability')
 for name in ('helper','nonempty','helper_block','compiler','binary','harness','actual_audit','actual_mesh'):require(Path(cap[name]['path']),cap[name])
 if cap['actual_clusters']!=95 or cap['all_valid_raw_lods']!=190:raise ValueError('Incomplete fallback capability')
 inputs=Path(d['inputs']['ps2-world.re4mesh']['path']).parent;mesh=(inputs/'ps2-world.re4mesh').read_bytes();policy=(inputs/'ps2-world.r4pw').read_bytes();ids=(inputs/'ps2-world.ids').read_bytes();h=struct.unpack_from('<4s19I',mesh);hp=struct.unpack_from('<4s7I',policy)
 if h[:3]!=(b'R4IM',3,len(mesh)) or zlib.crc32(mesh[80:])!=h[3] or hp[:2]!=(b'R4PW',1) or hp[3:5]!=(h[5],h[4]) or zlib.crc32(policy[32:])!=hp[5]:raise ValueError('Actual header/body CRC')
 p=f.Pkg(inputs/'ps2-world.re4mesh',inputs/'ps2-world.r4pw');op=f.Pkg(inputs/'ps2-world.re4mesh',inputs/'original.r4pw')
 if p.placements!=op.placements or struct.unpack_from('<4sIII',ids)!=(b'R4ID',1,len(p.placements),op.sidecar_crc):raise ValueError('Physical IDs/affine binding')
 instancekeys=[]
 for pi,pl in enumerate(p.placements):
  mr=p.meshes[pl['mesh']]
  for part in range(mr['first_part'],mr['first_part']+mr['part_count']):
   fc,nc=p.plod[part]
   instancekeys.extend((pi,part,ci) for ci in range(fc,fc+nc))
 if len(instancekeys)!=318:raise ValueError('Actual physical instance namespace')
 conditional=f.audit.conditional_fields(ids[16:16+len(p.placements)]);stage=json.loads((r6/'current-staging-plan.json').read_text())
 for name in ('ps2-world.re4mesh','ps2-world.r4pw','ps2-world.ids'):
  if sha(Path(stage['replace']['dc/native/r10d/'+name]))!=sha(inputs/name):raise ValueError('Staged source mismatch')
 mats,matpins=f.material_census(Path('/root/probe/interior-discovery24'),Path(stage['replace']['dc/tex.pak']),p)
 if json.loads(json.dumps(mats))!=d['material_parts']:raise ValueError('Material identity')
 cache={}
 def geometry(meta,is_source=False):
  key=physical(meta)
  if key not in cache:
   pi,field,part,ci,lv,li=key;cc,tt,nt=c.raw_let(mesh,li);pc,pt=p.let_tris(li);check_inventory((cc,tt),(pc,pt));world,fw,det,pl,mr=c.raw_mapping(mesh,policy,pi);ref,rd=f.mapping(p,pi);fc,nc=p.plod[part];cl=p.clusters[ci];levels=[p.levels[cl['first_level']+j] for j in range(cl['level_count'])];counts=[x[1] for x in levels]
   if not (det and det==rd and pl[1]==field and field not in conditional and ids[16+pi]==meta['owner'] and mr[6]<=part<mr[6]+mr[7] and fc<=ci<fc+nc and 0<=lv<len(levels) and levels[lv][0]<=li<levels[lv][0]+levels[lv][1] and p.pmeta[part]['pass_']==0):raise ValueError('Physical membership/static/LOD/owner')
   xyz=tuple(world(q) for q in cc)
   if any(xyz[i]!=ref(q) for i,q in enumerate(cc)):raise ValueError('Independent Fraction affine')
   for t,alternate in zip(tt,nt):
    if c.normal(*(xyz[j] for j in t))!=c.normal(*(xyz[j] for j in alternate)):raise ValueError('Actual parity winding')
   qlo=tuple(min(q[k] for q in cc) for k in range(3));qhi=tuple(max(q[k] for q in cc) for k in range(3));bp=[fw(q) for q in itertools.product(*zip(qlo,qhi))];oldbox=[[min(v[k] for v in bp) for k in range(3)],[max(v[k] for v in bp) for k in range(3)]]
   g=dict(key=key,box_float=oldbox,corners=cc,triangles=tt,xyz=xyz,counts=counts,selectable=f.audit.selectable(counts),degenerate=[i for i,t in enumerate(tt) if not any(c.normal(*(xyz[j] for j in t)))],cull=p.pmeta[part]['cull'],vertex_alpha=bool(policy[32+16*part+15]&1),eligible=mats[part]['eligible'])
   cache[key]=g
  g=cache[key]
  if is_source:
   pi,field,part,ci,lv,li=key
   actual=dict(static=True,unconditional=True,nonsingular=True,level_count=len(g['counts']),cull=g['cull'],vertex_alpha=g['vertex_alpha'],material_eligible=g['eligible'],pass_=0)
   claimed=dict(meta['prerequisites']);claimed['pass_']=claimed.pop('pass')
   if claimed!=actual or meta['authored_meshlet_counts']!=g['counts'] or lv!=0 or not g['counts'][0] or any(g['counts'][1:]) or not g['eligible'] or g['vertex_alpha'] or g['cull'] not in (0,2):raise ValueError('Source intrinsic/fallback prerequisites')
  return g
 hut=next(v for v in d['views'] if v['camera']['label']=='hut');ranked=[x for x in hut['ranked_lets'] if x['all_fixed_samples_hit']]
 if len(ranked)!=25 or [(r['target']['instance'],r['target']['meshlet']) for r in ranked[:2]]!=[(199,812),(202,822)]:raise ValueError('Fixed25 target/order census')
 targets=[];allrecords=[];paneldefs={};sourcekeys=set()
 for rank,row in enumerate(ranked):
  target=row['target'];g=geometry(target);roster={};components=[]
  if len(g['corners'])!=target['host_corner_records'] or g['box_float']!=target['box'] or instancekeys[target['instance']]!=(target['placement'],target['part'],target['cluster']):raise ValueError('Target corner/instance/box completeness')
  for pid in sorted(map(int,row['sampled_patch_hit_counts'])):
   component=hut['patches'][str(pid)];sm=component['source'];sg=geometry(sm,True)
   prefix_guard(sm,target)
   if len(component['component_triangles'])!=component['triangle_count']:raise ValueError('Incomplete saved component')
   faces=validate_component(sg['triangles'],sg['xyz'],component['component_triangles'])
   for ordinal,*tri in component['component_triangles']:
    k=(*physical(sm),ordinal)
    if k in roster and roster[k]['corners']!=tri:raise ValueError('Aliased source face definition')
    roster.setdefault(k,dict(key=k,corners=tri,positions_exact=[[str(x) for x in sg['xyz'][j]] for j in tri],components=[],old_restore=False))['components'].append(pid);sourcekeys.add(k)
   components.append(dict(id=pid,physical=physical(sm),actual_faces=len(faces),topology_union_claim=False))
  # Restored old faces may only be drawn from this target retained physical component.
  if rank<2:
   oldsrc=next(x['source'] for x in hut['patches'].values() if physical(x['source'])==(116,116,178,182,0,786));sg=geometry(oldsrc,True)
   for ordinal,tri in OLD.items():
    if tuple(sg['triangles'][ordinal])!=tri:raise ValueError('Old audited patch face changed')
    k=(*physical(oldsrc),ordinal)
    if k not in roster:raise ValueError('Old restoration outside retained component requires separate provenance')
    roster[k]['old_restore']=True
  # Partners restricted to SAME target roster and SAME physical source let.
  bylet=collections.defaultdict(dict)
  for k,r in roster.items():bylet[k[:6]][k[6]]=tuple(r['corners'])
  missing=[]
  for sk,faces in bylet.items():
   sg=cache[sk];nondeg={i:any(c.normal(*(sg['xyz'][j] for j in t))) for i,t in faces.items()};bindings,unmapped=panels(faces,nondeg)
   for ordinal in unmapped:missing.append((*sk,ordinal))
   for ordinal,(aord,bord,six) in bindings.items():
    record=(*sk[:4],sk[5],*six);definition=(*sk,aord,bord)
    if record in paneldefs and paneldefs[record]!=definition:raise ValueError('Duplicate-face ordinal alias in full Panel record')
    paneldefs[record]=definition;roster[(*sk,ordinal)]['panel_record']=record;roster[(*sk,ordinal)]['panel_face']=int(ordinal==bord);roster[(*sk,ordinal)]['panel_face_ordinals']=[aord,bord];allrecords.append(record)
  targetfaces=[dict(ordinal=i,corners=t,degenerate=i in g['degenerate'],positions_exact=[[str(x) for x in g['xyz'][j]] for j in t]) for i,t in enumerate(g['triangles'])]
  targets.append(dict(rank=rank,target=target,physical=physical(target),authored_counts=g['counts'],all_raw_choices_effective=g['selectable'],fresh_effective_lod_guard_required=len(g['selectable'])>1,complete_target_faces=targetfaces,matched_components=components,source_faces=list(roster.values()),unrepresentable_source_faces=missing,precount=precount(len(targetfaces),len(roster)),known_exposure=dict(view='hut',frame=647,host_preSG_corners=len(g['corners']),other128_perlet_exposure='UNKNOWN'),actual_prefix_receipt='UNQUALIFIED'))
 proof_header=Path('/root/work/lanes/interior-vis23/port/dreamcast/game/platform/include/pvs23_proof.hpp')
 if sha(proof_header)!='1881d1d814fdc7bb787991a2cd6f67ebab293d5c2a7efa42cdd515fb07821ba4':raise ValueError('Production Panel reader/layout changed')
 atlas=id_atlas(allrecords)
 for t in targets:
  for r in t['source_faces']:
   if 'panel_record' in r:r['panel_id']=atlas[tuple(r['panel_record'])]
 # Bind unchanged authentic cameras/domains; do not evaluate shadow predicates.
 r6report=r6/'report.json';smallpath=a.evidence/'I001-fb254-smaller-domains-r1/report.json';basepath=a.evidence/'I001-fb254-triangle-shadow-r1/bounded512-report.json'
 if sha(r6report)!=f.REPORT_SHA or sha(smallpath)!='e42fac7e3521c7ac549f2fb1a7ddd47aaffcb5b7d80d94f496cdf83a8fc5e6b7' or sha(basepath)!=s.MAIN_REPORT:raise ValueError('Camera/domain reports mismatch')
 prior=json.loads(r6report.read_text());small=json.loads(smallpath.read_text());prep=r6/'prepared/prepare-receipt.json';require(prep,prior['prepared_receipt']);frames,weights,logs=s.raw_cameras(json.loads(prep.read_text()),prior,r6)
 if len(frames)!=129 or [(x['label'],x['frame'],x['view_bits'],[str(v) for v in x['eye']]) for x in frames]!=[(x['label'],x['frame'],x['view_bits'],x['eye_exact']) for x in small['per_camera']]:raise ValueError('Authentic129 camera identity')
 domains={x['cell']:x for x in f.cells(a.evidence/'I001-fb254-triangle-shadow-r1/preserved-control.pvs',p)};eyes=[]
 for cam,oldrow in zip(frames,small['per_camera']):
  full=domains[oldrow['old_cell']]['box']
  for size in (2000,500,250):
   b=full if size==2000 else s.window(cam['eye'],full,size)
   if (b[0][1],b[1][1])!=(full[0][1],full[1][1]):raise ValueError('FullY changed')
   oldbox=oldrow['variants'].get(str(size),{}).get('box_exact')
   if oldbox is not None and [[str(x) for x in v] for v in b]!=oldbox:raise ValueError('Domain changed')
   eyes.append(dict(label=cam['label'],frame=cam['frame'],size_mm=size,old_cell=oldrow['old_cell'],box_exact=[[str(x) for x in v] for v in b],raw_camera_record_sha256=cam['raw_camera_record_sha256']))
 inputbits=max(max(abs(x.numerator).bit_length(),x.denominator.bit_length()) for g in cache.values() for point in g['xyz'] for x in point)
 eyebits=max(max(abs(Q(x).numerator).bit_length(),Q(x).denominator.bit_length()) for row in eyes for point in row['box_exact'] for x in point)
 if max(inputbits,eyebits)>256:raise ValueError('Generic exact scalar input exceeds bound')
 summary=dict(max_geometry_scalar_bits=inputbits,max_eye_scalar_bits=eyebits,targets=25,domains_per_target=387,wholelet_domain_cases=25*387,target_triangle_occurrences=sum(len(t['complete_target_faces']) for t in targets),source_face_occurrences=sum(len(t['source_faces']) for t in targets),unique_source_faces=len(sourcekeys),panel_records=len(atlas),unrepresentable_source_occurrences=sum(len(t['unrepresentable_source_faces']) for t in targets),target_degenerate_occurrences=sum(sum(f['degenerate'] for f in t['complete_target_faces']) for t in targets),**{k:sum(t['precount'][k] for t in targets) for k in ('primitive_calls_upper','edge_determinants_upper','plane_evaluations_upper','final_assignment_edge_upper')})
 out=dict(classification='PREPARATION_ONLY_NO_ACTUAL_SHADOW_PREDICATES',base=BASE,tool=pin(Path(__file__)),loader=loaderpin,math_source=frozen,math_pins=mathpins,generic_source=GENERIC,generic_sha256=hashlib.sha256(generic).hexdigest(),discovery=pin(path),audit=pin(a.audit),source=source,inputs=d['inputs'],capability=pin(cap_path),material_pins=matpins,production_panel_source=pin(proof_header),authentic_camera_logs=logs,domains=eyes,panel_atlas=[dict(identifier=i,record=r,actual_face_definition=paneldefs[r]) for r,i in atlas.items()],targets=targets,summary=summary,actual_shadow_predicate_calls=0,new_rays=0,ledger_accesses=0,runtime_admitted=False,limits=dict(address_cap_bytes=LIMIT,output_cap_bytes=OUTPUT,seconds=time.monotonic()-start,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,jobs=1),limitations=['All target faces retained including degenerates; no target subset can be positive.','Sources comprise complete saved matched components, independent actual triangles only; no union/topology theorem.','Production Panel requires two distinct opposite-edge adjacent retained actual faces in same physical let; deterministic lowest ordinal partner; unrepresentable source remains UNKNOWN.','Future geometric proof only: numeric/raster/source prefix/emission/actual selector/LOD/frame liveness remain unqualified.','Known perlet exposure is hut647 preSG only; other128 cameras have no perlet exposure proof.','Target effective levels remain actual including1; multi-effective targets need fresh effectiveLOD guard.','Raw exhaustive work census is not a120s execution allocation; root must bound actual run before predicates.'])
 raw=(json.dumps(out,indent=1)+'\n').encode()
 if len(raw)+65536>OUTPUT:raise ValueError('Output cap')
 if out['limits']['seconds']>120:raise ValueError('Prep exceeded120s')
 a.out.mkdir();(a.out/'report.json').write_bytes(raw);(a.out/'summary.json').write_text(json.dumps(dict(classification=out['classification'],summary=summary,limits=out['limits'],report=pin(a.out/'report.json')),indent=2)+'\n');print(json.dumps(json.loads((a.out/'summary.json').read_text())),flush=True)
if __name__=='__main__':main()
