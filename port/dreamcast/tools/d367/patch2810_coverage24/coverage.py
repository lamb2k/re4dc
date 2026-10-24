"""Two approved patch2810 disks; exact full supported domains, no rays/assets."""
import argparse,collections,hashlib,itertools,json,resource,struct,subprocess,sys,tempfile,time,zlib
from fractions import Fraction as Q
from pathlib import Path
LIMIT=268435456;OUTPUT_CAP=16777216;MATH_COMMIT='581482ed4'
AUDIT_SHA='6f1b579f17b0f3a875941465935cfc5e36774c599b7f37d5a7a527108c3ce0b4'
DISCOVERY_SHA='1f80a2ddeb4980bf328e1d705716028b9d422d31125a631809f2d9f7de80af74'
FACES={8:(18,19,20),12:(20,19,24),13:(25,24,19),14:(24,25,26)}
def digest(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def pin(path):return dict(path=str(path),bytes=Path(path).stat().st_size,sha256=digest(path))
def require(path,expected):
 if digest(path)!=expected['sha256'] or Path(path).stat().st_size!=expected['bytes']:raise ValueError('Pinned source mismatch '+str(path))
def vsub(a,b):return tuple(x-y for x,y in zip(a,b))
def normal(a,b,c):
 u=vsub(b,a);v=vsub(c,a);return (u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0])
def scalar(a,b):return sum(x*y for x,y in zip(a,b))
def det3(a,b,c):return a[0]*(b[1]*c[2]-b[2]*c[1])-a[1]*(b[0]*c[2]-b[2]*c[0])+a[2]*(b[0]*c[1]-b[1]*c[0])
def boxcorners(b):return tuple(itertools.product(*zip(*b)))
def qr(v):return [str(x) for x in v]
def raw_let(mesh,li):
 h=struct.unpack_from('<4s19I',mesh);fv,fs,sb,n,sc,*bounds=struct.unpack_from('<IIIHH6H',mesh,h[12]+28*li)
 if h[19] or not 1<=n<=256:raise ValueError('Unsupported encoded/local vertex layout')
 pos=h[14]+fs
 ix=struct.unpack_from('<%dH'%n,mesh,pos) if sc&32768 else tuple(range(n));pos+=2*n if sc&32768 else 0
 if max(ix)+fv>=h[7] or fs+(2*n if sc&32768 else 0)+sb>h[8]:raise ValueError('Raw let section')
 cs=[struct.unpack_from('<6H',mesh,h[13]+12*(fv+i)) for i in ix];end=pos+sb;ref=[];native=[];strips=0
 while pos<end:
  nstrip=mesh[pos];pos+=1;s=mesh[pos:pos+nstrip];pos+=nstrip;strips+=1
  if nstrip<3 or pos>end or any(i>=n for i in s):raise ValueError('Raw strip extent/index')
  for k in range(nstrip-2):
   a,b,c=s[k:k+3];ref.append((a,b,c) if k%2==0 else (c,b,a));native.append((a,b,c) if k%2==0 else (b,a,c))
 if strips!=(sc&32767):raise ValueError('Raw strip count')
 return cs,ref,native

def raw_mapping(mesh,policy,pi):
 h=struct.unpack_from('<4s19I',mesh);hp=struct.unpack_from('<4s7I',policy);pl=struct.unpack_from('<HH12f',policy,32+16*hp[3]+52*pi);mi=pl[0]
 mr=struct.unpack_from('<HBBHHIII12f',mesh,h[10]+68*mi);af=tuple(tuple(Q(pl[2+4*i+j]) for j in range(4)) for i in range(3));org=tuple(Q(v) for v in mr[8:11]);step=tuple(Q(v) for v in mr[11:14])
 def world(q):return tuple(af[i][3]+sum(af[i][k]*(org[k]+step[k]*int(q[k])) for k in range(3)) for i in range(3))
 def legacy_float(q):
  x=[mr[8+k]+mr[11+k]*int(q[k]) for k in range(3)]
  return tuple(sum(pl[2+4*i+k]*x[k] for k in range(3))+pl[2+4*i+3] for i in range(3))
 return world,legacy_float,det3(af[0][:3],af[1][:3],af[2][:3]),pl,mr

def independent_disk(faces):
 edges=collections.defaultdict(list);vs=set();adj=[set() for t in faces]
 for i,t in enumerate(faces):
  if len(set(t))!=3:raise ValueError('Repeated vertex')
  vs.update(t)
  for a,b in zip(t,t[1:]+t[:1]):edges[tuple(sorted((a,b)))].append((i,a,b))
 boundary=[]
 for uses in edges.values():
  if len(uses)==1:boundary.append(uses[0][1:])
  elif len(uses)==2:
   if uses[0][1:]!=uses[1][1:][::-1]:raise ValueError('Independent winding')
   adj[uses[0][0]].add(uses[1][0]);adj[uses[1][0]].add(uses[0][0])
  else:raise ValueError('Independent nonmanifold')
 seen={0};todo=[0]
 while todo:
  for j in adj[todo.pop()]-seen:seen.add(j);todo.append(j)
 if len(seen)!=len(faces) or len(vs)-len(edges)+len(faces)!=1:raise ValueError('Independent disk Euler/connectivity')
 out={};inc={}
 for a,b in boundary:
  if a in out or b in inc:raise ValueError('Independent pinched boundary')
  out[a]=b;inc[b]=a
 start=min(out);cycle=[start]
 while out[cycle[-1]]!=start:
  if out[cycle[-1]] in cycle:raise ValueError('Independent boundary repeat')
  cycle.append(out[cycle[-1]])
 if len(cycle)!=len(boundary) or set(out)!=set(inc):raise ValueError('Independent multiple boundaries')
 for v in vs:
  link=collections.defaultdict(set)
  for t in faces:
   if v in t:
    a,b=[x for x in t if x!=v];link[a].add(b);link[b].add(a)
  reached={next(iter(link))};todo=list(reached)
  while todo:
   for j in link[todo.pop()]-reached:reached.add(j);todo.append(j)
  if reached!=set(link):raise ValueError('Independent disconnected link')
  degree=[len(link[j]) for j in link]
  if v in out:
   if sorted(degree)!=[1,1]+[2]*(len(degree)-2) or {j for j in link if len(link[j])==1}!={inc[v],out[v]}:raise ValueError('Independent boundary link')
  elif len(link)<3 or set(degree)!={2}:raise ValueError('Independent interior link')
 return dict(vertices=len(vs),edges=len(edges),faces=len(faces),euler=1,boundary=cycle,all_vertex_links_checked=True)

def plane_audit(vertices,faces,eye,target):
 rows=[];allowed={1,-1}
 for tri in faces:
  a,b,c=[vertices[i] for i in tri];n=normal(a,b,c);d=-scalar(n,a)
  if not any(n):raise ValueError('Degenerate admitted face')
  def support(box):
   return (d+sum(n[k]*box[0 if n[k]>=0 else 1][k] for k in range(3)),d+sum(n[k]*box[1 if n[k]>=0 else 0][k] for k in range(3)))
  er,tr=support(eye),support(target);signs={s for s in (1,-1) if (er[0]>0 and tr[1]<0 if s==1 else er[1]<0 and tr[0]>0)};allowed&=signs
  rows.append(dict(normal=qr(n),offset=str(d),eye_range=qr(er),target_range=qr(tr)))
 return rows,sorted(allowed)

def edge_audit(vertices,cycle,eye,target,sigma):
 failing=[]
 for a,b in zip(cycle,cycle[1:]+cycle[:1]):
  values=[(-sigma*det3(vsub(vertices[a],e),vsub(vertices[b],e),vsub(t,e)),ei,ti) for ei,e in enumerate(boxcorners(eye)) for ti,t in enumerate(boxcorners(target))]
  low,ei,ti=min(values)
  if low<=0:failing.append(dict(edge=[a,b],minimum=str(low),worst_eye_corner=ei,worst_target_corner=ti,negative_products=sum(v<0 for v,_,_ in values),zero_products=sum(v==0 for v,_,_ in values),products=64))
 return failing

def snapshot(repo,audit,discovery):
 frozen=subprocess.check_output(['git','-C',str(repo),'rev-parse',MATH_COMMIT+'^{commit}'],text=True).strip();ram=Path(tempfile.mkdtemp(prefix='patch2810-exact-',dir='/dev/shm'));base=ram/'interior_vis23';mathdir=base/'triangle_shadow_next';mathdir.mkdir(parents=True);pins={}
 for name in ('exact_patch.py','exact_union.py','exact_shadow.py','feasibility.py','smaller_domains.py','../surface_mesh.py','../lod_surface_audit.py'):
  rel='port/dreamcast/tools/d367/interior_vis23/'+('triangle_shadow_next/'+name if not name.startswith('../') else name[3:]);data=subprocess.check_output(['git','-C',str(repo),'show',frozen+':'+rel]);dest=(mathdir/name).resolve();dest.write_bytes(data);pins[dest.name]=pin(dest)
  if dest.name in discovery['parent_tool_pins'] and pins[dest.name]['sha256']!=discovery['parent_tool_pins'][dest.name]['sha256']:raise ValueError('Frozen/report helper mismatch '+name)
 if pins['exact_patch.py']['sha256']!='2f4f2017013a7d8ffca3d6563a79f699b3277f066e1a6fdc0fe558d4fb019f41':raise ValueError('Unreviewed connected oracle')
 sys.path[:0]=[str(mathdir),str(base)];import feasibility,smaller_domains,exact_patch,exact_union
 return frozen,ram,pins,feasibility,smaller_domains,exact_patch,exact_union

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source-tree',type=Path,required=True);ap.add_argument('--audit',type=Path,required=True);ap.add_argument('--evidence',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
 resource.setrlimit(resource.RLIMIT_AS,(LIMIT,LIMIT));start=time.monotonic()
 if a.out.exists() or a.out.is_relative_to(a.source_tree):raise ValueError('Fresh private output required')
 if digest(a.audit)!=AUDIT_SHA:raise ValueError('Topology audit changed')
 au=json.loads(a.audit.read_text());report=Path(au['input']['path']);require(report,au['input']);d=json.loads(report.read_text())
 if digest(report)!=DISCOVERY_SHA:raise ValueError('Discovery changed')
 frozen,ram,pins,f,s,patch,union=snapshot(a.source_tree,au,d)
 for item in au['input_assets'].values():require(Path(item['path']),item)
 for name,p in au['helper_pins'].items():require(Path(p['path']),p)
 source=f.audit.bind_source(Path('/root/probe/interior-discovery24'),a.evidence/'I001-fb254-lod-surface-r6/current-resolved-knobs.txt')
 if source['files']!=d['source']['files'] or source['knobs']!=d['source']['knobs']:raise ValueError('Source/policy drift')
 basepath=a.evidence/'I001-fb254-triangle-shadow-r1/bounded512-report.json';smallpath=a.evidence/'I001-fb254-smaller-domains-r1/report.json';r6=a.evidence/'I001-fb254-lod-surface-r6'
 if digest(basepath)!=s.MAIN_REPORT or digest(smallpath)!='e42fac7e3521c7ac549f2fb1a7ddd47aaffcb5b7d80d94f496cdf83a8fc5e6b7' or digest(r6/'report.json')!=f.REPORT_SHA:raise ValueError('Domain/camera source changed')
 base=json.loads(basepath.read_text());small=json.loads(smallpath.read_text());prior=json.loads((r6/'report.json').read_text());prep=r6/'prepared/prepare-receipt.json'
 if digest(prep)!=prior['prepared_receipt']['sha256']:raise ValueError('Camera receipt changed')
 frames,weights,logs=s.raw_cameras(json.loads(prep.read_text()),prior,r6)
 if len(frames)!=129 or [(c['label'],c['frame'],c['view_bits'],qr(c['eye'])) for c in frames]!=[(c['label'],c['frame'],c['view_bits'],c['eye_exact']) for c in small['per_camera']]:raise ValueError('129 camera identity')
 inputs=Path(au['input_assets']['ps2-world.re4mesh']['path']).parent;mesh=(inputs/'ps2-world.re4mesh').read_bytes();policy=(inputs/'ps2-world.r4pw').read_bytes();ids=(inputs/'ps2-world.ids').read_bytes();original=(inputs/'original.r4pw').read_bytes();h=struct.unpack_from('<4s19I',mesh);hp=struct.unpack_from('<4s7I',policy)
 if h[:3]!=(b'R4IM',3,len(mesh)) or zlib.crc32(mesh[80:])!=h[3] or hp[:2]!=(b'R4PW',1) or hp[3:5]!=(h[5],h[4]) or zlib.crc32(policy[32:])!=hp[5]:raise ValueError('Raw copied header/CRC')
 p=f.Pkg(inputs/'ps2-world.re4mesh',inputs/'ps2-world.r4pw');op=f.Pkg(inputs/'ps2-world.re4mesh',inputs/'original.r4pw')
 if p.placements!=op.placements or struct.unpack_from('<4sIII',ids)!=(b'R4ID',1,len(p.placements),op.sidecar_crc):raise ValueError('Physical ownership/affine')
 conditional=f.audit.conditional_fields(ids[16:16+len(p.placements)])
 stage=json.loads((r6/'current-staging-plan.json').read_text())
 for name in ('ps2-world.re4mesh','ps2-world.r4pw','ps2-world.ids'):
  if digest(Path(stage['replace']['dc/native/r10d/'+name]))!=digest(inputs/name):raise ValueError('Actual staged source changed '+name)
 materials,materialpins=f.material_census(Path('/root/probe/interior-discovery24'),Path(stage['replace']['dc/tex.pak']),p)
 if json.loads(json.dumps(materials))!=d['material_parts']:raise ValueError('Material identity')
 cs,ts,native=raw_let(mesh,786);pcs,pts=p.let_tris(786)
 if cs!=pcs or ts!=pts or len(cs)!=63 or len(ts)!=44:raise ValueError('Independent source let decoder')
 world,fw,det,pl,mr=raw_mapping(mesh,policy,116);reference_world,rd=f.mapping(p,116)
 if not det or det!=rd or pl[1]!=116 or 116 in conditional or ids[16+116]!=254:raise ValueError('Source static physical affine')
 source_meta=p.pmeta[178];fc,nc=p.plod[178];cl=p.clusters[182];levels=[p.levels[cl['first_level']+i] for i in range(cl['level_count'])]
 if not(mr[6]<=178<mr[6]+mr[7] and fc<=182<fc+nc and len(levels)==1 and levels[0][0]<=786<levels[0][0]+levels[0][1] and source_meta['pass_']==0 and source_meta['cull']==2 and not policy[32+16*178+15]&1 and materials[178]['eligible']):raise ValueError('Source membership/LOD/material')
 for i,q in enumerate(cs):
  if world(q)!=reference_world(q):raise ValueError('Independent exact source affine')
 for ordinal,tri in FACES.items():
  if tuple(ts[ordinal])!=tri:raise ValueError('Actual oriented source face')
  if normal(*(world(cs[i]) for i in tri))!=normal(*(world(cs[i]) for i in native[ordinal])):raise ValueError('Native parity winding/plane')
 source_vertices={i:world(cs[i]) for tri in FACES.values() for i in tri};hut=next(v for v in d['views'] if v['camera']['label']=='hut');targets=[]
 for instance,pi,part,cluster,li,n,ords in ((199,121,186,190,812,64,[8,12]),(202,123,188,192,822,40,[8,12,13,14])):
  auditrow=next(x for x in au['targets'] if x['target_tuple']==[instance,0,li]);saved=next(x['target'] for x in hut['ranked_lets'] if x['target']['instance']==instance and x['target']['meshlet']==li);cc,tt,nt=raw_let(mesh,li);tw,tf,td,tpl,tmr=raw_mapping(mesh,policy,pi);fc,nc=p.plod[part];tc=p.clusters[cluster];ll=[p.levels[tc['first_level']+j] for j in range(tc['level_count'])];counts=[x[1] for x in ll]
  if not(td and len(cc)==n and cc==p.let_tris(li)[0] and tmr[6]<=part<tmr[6]+tmr[7] and fc<=cluster<fc+nc and ll[0][0]<=li<ll[0][0]+ll[0][1] and tpl[1]==pi and pi not in conditional and ids[16+pi]==254 and p.pmeta[part]['pass_']==0):raise ValueError('Target physical/let membership')
  choices=[]
  for raw in range(len(counts)):
   effective=raw
   while effective and not counts[effective]:effective-=1
   choices.append(effective)
  if counts!=[x['let_count'] for x in auditrow['authored_levels']] or set(choices)!={0} or source['knobs']['PS2_WORLD_NONEMPTY_LOD']!='1':raise ValueError('Effective LOD0 proof')
  qlo=tuple(min(c[k] for c in cc) for k in range(3));qhi=tuple(max(c[k] for c in cc) for k in range(3));ws=[tw(q) for q in boxcorners((qlo,qhi))];box=(tuple(min(v[k] for v in ws) for k in range(3)),tuple(max(v[k] for v in ws) for k in range(3)));floats=[tf(q) for q in boxcorners((qlo,qhi))];oldbox=[[min(v[k] for v in floats) for k in range(3)],[max(v[k] for v in floats) for k in range(3)]]
  if oldbox!=saved['box']:raise ValueError('Saved let full-box construction drift')
  faces=tuple(FACES[i] for i in ords);top=patch.indexed_disk(faces);independent=independent_disk(faces)
  if list(top['boundary'])!=independent['boundary'] or independent['boundary']!=auditrow['minimum_connected_disk']['all_minimum_disks'][0]['topology']['boundary']:raise ValueError('Independent disk boundary')
  targets.append(dict(instance=instance,placement=pi,field=pi,owner=254,part=part,cluster=cluster,level=0,meshlet=li,corner_records=n,ordinals=ords,faces=faces,box=box,authored_level_counts=counts,all_raw_choices_effective=choices,topology=independent))
 domains={x['cell']:x for x in f.cells(a.evidence/'I001-fb254-triangle-shadow-r1/preserved-control.pvs',p)};rows=[];summary={};cache={};nominal_evals=requested_evals=0
 for size in (2000,500,250):
  counts=collections.defaultdict(collections.Counter)
  for camera,old in zip(frames,small['per_camera']):
   if old['old_cell'] is None:raise ValueError('Missing original supported domain')
   full=domains[old['old_cell']]['box'];box=full if size==2000 else s.window(camera['eye'],full,size)
   if box[0][1]!=full[0][1] or box[1][1]!=full[1][1]:raise ValueError('Height domain changed')
   priorbox=old['variants'].get(str(size),{}).get('box_exact')
   if priorbox is not None and [qr(b) for b in box]!=priorbox:raise ValueError('Local domain mismatch')
   for target in targets:
    outcomes={};planes,signs=plane_audit(source_vertices,target['faces'],box,target['box']);cycle=target['topology']['boundary']
    modes=('pair_union','strict_convex','boundary_kernel') if target['instance']==199 else ('strict_convex','boundary_kernel')
    for mode in modes:
     key=(target['instance'],mode,box)
     if key not in cache:
      method=union.prove_union if mode=='pair_union' else patch.prove_patch;kw={} if mode=='pair_union' else dict(boundary_mode=mode)
      nominal=method(source_vertices,target['faces'],box,target['box'],**kw);nominal_evals+=1
      if nominal['proven'] and not signs:raise ValueError('Independent plane contradiction')
      if not signs and nominal['reason'] not in ('plane_unknown','face_plane_or_orientation_unknown'):raise ValueError('Plane refusal contradiction')
      detail=dict(independent_plane_common_signs=signs,independent_plane_ranges=planes)
      if signs:detail['independent_nonpositive_boundary_products']=edge_audit(source_vertices,cycle,box,target['box'],signs[0])
      requested=method(source_vertices,target['faces'],box,target['box'],vertex_error=32,eye_error=32,target_error=32,eye_clearance=2000,target_clearance=32,**kw) if nominal['proven'] else None;requested_evals+=int(requested is not None)
      cache[key]=dict(nominal=nominal,requested_32mm_ideal=requested,diagnostic=detail)
     result=cache[key];outcomes[mode]=result;counter=counts[str(target['instance'])+'/'+mode];counter['domains']+=1;counter['nominal_positive']+=int(result['nominal']['proven']);counter['requested_positive']+=int(bool(result['requested_32mm_ideal'] and result['requested_32mm_ideal']['proven']))
     if not result['nominal']['proven']:counter['refusal_'+result['nominal']['reason']]+=1
    rows.append(dict(size_mm=size,label=camera['label'],frame=camera['frame'],old_cell=old['old_cell'],view_bits=camera['view_bits'],raw_camera_record_sha256=camera['raw_camera_record_sha256'],eye_exact=qr(camera['eye']),eye_box_exact=[qr(b) for b in box],target_instance=target['instance'],outcomes=outcomes,conditional_preSG_corner_ceiling=target['corner_records'] if any(v['nominal']['proven'] for v in outcomes.values()) else 0,actual_selected_let_in_this_historical_frame='UNKNOWN',actual_selector_preimage_certified=False,runtime_admitted=False))
  summary[str(size)]={k:dict(v) for k,v in counts.items()};print(json.dumps(dict(size=size,summary=summary[str(size)])),flush=True)
 out=dict(classification='EXACT_IDEAL_SUPPORTED_DOMAIN_SUFFICIENT_TEST_ONLY_NO_RUNTIME_CERTIFICATE',tool=pin(Path(__file__)),base_source=subprocess.check_output(['git','-C',str(a.source_tree),'rev-parse','HEAD'],text=True).strip(),frozen_math_commit=frozen,snapshot=str(ram),dependencies=pins,topology_audit=pin(a.audit),discovery=pin(report),inputs=au['input_assets'],source=source,material_pins=materialpins,authentic_cameras=logs,authentic_camera_frames=129,historical_camera_profile='e9bf7, old 54s request/55.4..55.8s wall; no new guest or current exact55 claim',source_geometry=dict(placement=116,field=116,owner=254,part=178,cluster=182,level=0,meshlet=786,declared_levels=levels,actual_oriented_faces=FACES,exact_positions={i:qr(v) for i,v in source_vertices.items()},independent_raw_parity_and_normals_equal=True),targets=[{k:([qr(b) for b in v] if k=='box' else v) for k,v in t.items()} for t in targets],summaries=summary,results=rows,new_ray_queries=0,ledger_changes=0,nominal_unique_tests=nominal_evals,requested_interval_unique_tests=requested_evals,runtime_admitted_corners=0,gain_ms=None,maximum_distinct_target_corner_opportunity=104,limits=dict(address_cap_bytes=LIMIT,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,output_cap_bytes=OUTPUT_CAP,jobs=1,seconds=time.monotonic()-start),limitations=['Sufficient IDEAL continuous box geometry only; refusal means unknown, not visible.','No all15 patch, hull, weld, flatten, point-eye substitution, tiny/new domain or ray search.','Targetlet boxes are exact rational versions of the same full authored-grid-AABB construction; all effective choices use0 under pinned NONEMPTY_LOD1.','104 distinct preSG host corner records are conditional opportunity, not selected let/group identities across historical129 frames or measured savings.','Actual cull/near/clip/SH4/FPSCR/cache/kernel/seam/raster/depth/material/source prefix/pose/AREA/selector remain unqualified.','No source/table/data/runtime/asset/recipe/SDK/guest/media or converter change.'])
 raw=(json.dumps(out,indent=1)+'\n').encode()
 if len(raw)+65536>OUTPUT_CAP:raise ValueError('Whole output cap incl64KiB metadata reserve')
 a.out.mkdir();(a.out/'report.json').write_bytes(raw);print(json.dumps(dict(status=out['classification'],report=pin(a.out/'report.json'),limits=out['limits'],nominal_tests=nominal_evals,requested_tests=requested_evals,new_rays=0)),flush=True)
if __name__=='__main__':main()
