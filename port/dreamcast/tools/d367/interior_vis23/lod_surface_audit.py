#!/usr/bin/env python3
"""Exact all-selectable-LOD surface lemma and fail-open closure prerequisite.

No cull table or asset is emitted. An oriented facet is a witness only when it
exists in every selectable LOD of its own source cluster. Independent mixed LOD
choices are therefore covered without assuming equal level numbers. Unmatched
source edges are never welded or filled. Topology alone never admits a hull.
All geometry, bounds, camera weights and reports are private output only.
"""
import argparse,collections,hashlib,importlib.util,json,struct,subprocess,sys
from fractions import Fraction
from pathlib import Path

INTEGRATION='fb254e82ee6f9a3d9e34d53d1d442348a46b9cf2'
POLICY_FILES=['port/dreamcast/game/platform/native_static.cpp','port/dreamcast/game/platform/include/scenery_chunk_select.inc','port/dreamcast/game/platform/include/scenery_select_lean2.inc','port/dreamcast/room/pvr_geometry.cpp','port/dreamcast/room/pvr_geometry.hpp','port/dreamcast/room/instanced_mesh.hpp','port/dreamcast/room/nonempty_lod.hpp','port/dreamcast/game/platform/quality.cpp','port/dreamcast/tools/d367/rr/recipe.conf']
EXPECTED={'QUALITY':'1','QUALITY_LOD_PX':'5','SCENERY_FAR_LOD':'4','SCENERY_DEDUP':'0','PS2_PVS':'0','CPU_BACKFACE':'0','PS2_WORLD_NONEMPTY_LOD':'1','PS2_STRIP_GROUPS':'1','SCENERY_SELECT_ONLY':'1','SCENERY_REPLAY_LEAN':'1','SCENERY_SUBMIT_BATCH':'1','WORLD_RECT21':'1'}

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def identity(p):return dict(path=str(p),bytes=Path(p).stat().st_size,sha256=sha(p))
def sub(a,b):return tuple(a[i]-b[i] for i in range(3))
def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def canonical(tri):
 t=tuple(tuple(int(x) for x in q) for q in tri)
 if len(t)!=3 or any(len(q)!=3 for q in t):raise ValueError('Triangle arity')
 if not any(cross(sub(t[1],t[0]),sub(t[2],t[0]))):return None
 return min(t,t[1:]+t[:1],t[2:]+t[:2])
def selectable(counts):
 if not counts:raise ValueError('Missing cluster levels')
 selected=set()
 for raw in range(len(counts)):
  lv=raw
  while lv and not counts[lv]:lv-=1
  selected.add(lv)
 return sorted(selected)
def invariant(level_facets,counts):
 levels=selectable(counts)
 if len(level_facets)!=len(counts):raise ValueError('Level cardinality mismatch')
 # Geometry is intersected per source cluster, never across owner/cluster aliases.
 return set.intersection(*(set(level_facets[i]) for i in levels)),levels

def topology(facets):
 # Input duplicates are retained. A coincident duplicate cannot seal a crack.
 facets=list(facets);edges=collections.defaultdict(list)
 for i,t in enumerate(facets):
  if canonical(t)!=t:raise ValueError('Noncanonical or degenerate witness')
  for j in range(3):
   a,b=t[j],t[(j+1)%3];edges[tuple(sorted((a,b)))].append((i,a<b))
 parent=list(range(len(facets)))
 def find(i):
  while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
  return i
 for uses in edges.values():
  for i,_ in uses[1:]:parent[find(i)]=find(uses[0][0])
 groups=collections.defaultdict(list)
 for i in range(len(facets)):groups[find(i)].append(i)
 result=[]
 for members in groups.values():
  belongs=set(members);es=[(e,u) for e,u in edges.items() if u[0][0] in belongs]
  boundary=[e for e,u in es if len(u)==1];nonman=[e for e,u in es if len(u)>2]
  winding=[e for e,u in es if len(u)==2 and u[0][1]==u[1][1]]
  verts=sorted({q for i in members for q in facets[i]});volume6=sum(dot(t[0],cross(t[1],t[2])) for t in (facets[i] for i in members))
  # Even a closed oriented graph can self-intersect or be a solid prop. This is
  # a prerequisite only. Renderer numeric/state/opacity receipts remain absent.
  candidate=bool(members and not boundary and not nonman and not winding and volume6)
  result.append(dict(facets=len(members),vertices=len(verts),edges=len(es),boundary_edges=boundary,nonmanifold_edges=nonman,winding_conflicts=winding,signed_grid_volume6=volume6,closed_oriented_graph_prerequisite=candidate,enclosure_proven=False,runtime_admitted=False,fail_open=True,grid_lo=[min(q[k] for q in verts) for k in range(3)],grid_hi=[max(q[k] for q in verts) for k in range(3)]))
 return sorted(result,key=lambda x:-x['facets'])

def block(text,begin,end):
 if text.count(begin)!=1:raise ValueError('Nonunique policy begin '+begin)
 x=text.index(begin);y=text.index(end,x)
 return text[x:y]
def bind_source(repo,profile):
 if subprocess.check_output(['git','-C',str(repo),'rev-parse',INTEGRATION],text=True).strip()!=INTEGRATION:raise ValueError('Missing exact integration')
 if subprocess.run(['git','-C',str(repo),'merge-base','--is-ancestor',INTEGRATION,'HEAD'],capture_output=True).returncode:raise ValueError('Integration not merged')
 rows={}
 for rel in POLICY_FILES:
  original=subprocess.check_output(['git','-C',str(repo),'show',INTEGRATION+':'+rel]);current=(repo/rel).read_bytes()
  # Owned earlier PVS receipts alter native_static outside these core policy
  # blocks. All other bounded renderer policy files must equal integration.
  if rel.endswith('native_static.cpp'):
   for begin,end in [('const float px_x=RE4DC_SCREEN_HALF_WF*std::fabs(P[1])','    const auto& pk=ps2w.package;'),('    int draw_clusters(){','            ++stats.lod_draws')]:
    if block(original.decode(),begin,end)!=block(current.decode(),begin,end):raise ValueError('Core selector changed')
  elif current!=original:raise ValueError('Renderer policy differs from integration: '+rel)
  rows[rel]=dict(integration_sha256=hashlib.sha256(original).hexdigest(),owned_tree_sha256=hashlib.sha256(current).hexdigest())
 actual={}
 for line in profile.read_text().splitlines():
  if '=' in line:
   key,value=line.split('=',1)
   if key in actual:raise ValueError('Duplicate resolved knob')
   actual[key]=value
 for k,v in EXPECTED.items():
  if actual.get(k)!=v:raise ValueError('Wrong current resolved '+k)
 return dict(integration=INTEGRATION,owned_head=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip(),files=rows,profile=identity(profile),knobs={k:actual[k] for k in EXPECTED},effective_lod_divisor=20,scope='Current integration core renderer LOD/box/frustum policy pinned. Topology does not replay numeric emitted vertices or prove opacity/state.')

def main():
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('--source-tree',required=True,type=Path);a.add_argument('--profile',required=True,type=Path);a.add_argument('--staging-plan',required=True,type=Path);a.add_argument('--prepared',required=True,type=Path);a.add_argument('--replay',action='append',type=Path,default=[]);a.add_argument('--out',required=True,type=Path);v=a.parse_args()
 if v.out.exists():raise ValueError('Preserve prior output')
 source=bind_source(v.source_tree,v.profile);root=v.prepared;receipt=json.loads((root/'prepare-receipt.json').read_text());pkg=root/'inputs'
 staged=json.loads(v.staging_plan.read_text());files={}
 for name in ['ps2-world.re4mesh','ps2-world.r4pw','ps2-world.ids']:
  p=pkg/name;actual=Path(staged['replace']['dc/native/r10d/'+name]);pin=receipt['inputs'][name]
  if sha(p)!=pin['sha256'] or p.stat().st_size!=pin['bytes'] or sha(actual)!=sha(p):raise ValueError('Current staged input mismatch '+name)
  files[name]=dict(prepared=identity(p),current_source=identity(actual))
 if any('/r10d/' in k for k in staged['remove']):raise ValueError('Current staging removes room input')
 if 'dc/native/r10d/ps2-world.r4sg' in staged['replace'] or (pkg/'ps2-world.r4sg').exists():raise ValueError('SG source not qualified for this room audit')
 reader=root/'helpers/interior/r4im.py';spec=importlib.util.spec_from_file_location('pinned_r4im',reader);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);p=mod.Pkg(pkg/'ps2-world.re4mesh',pkg/'ps2-world.r4pw')
 if p.magic!=b'R4IM' or p.version!=3:raise ValueError('Unsupported mesh format')
 ids=(pkg/'ps2-world.ids').read_bytes();magic,version,n,crc=struct.unpack_from('<4sIII',ids)
 if magic!=b'R4ID' or version!=1 or n!=len(p.placements) or len(ids)<16+n:raise ValueError('Invalid IDs')
 shape_cache={};placements=[];instance=0;instance_keys=[]
 for pi,pl in enumerate(p.placements):
  mesh=p.meshes[pl['mesh']];facets=[];parts=[];clusters=[]
  affine=[[Fraction(float(pl['affine'][i,j])) for j in range(3)] for i in range(3)]
  det=dot(affine[0],cross(affine[1],affine[2]));singular=not det
  for part in range(mesh['first_part'],mesh['first_part']+mesh['part_count']):
   meta=p.pmeta[part];reserved=Path(pkg/'ps2-world.r4pw').read_bytes()[32+16*part+15]
   eligible=meta['pass_']==0 and meta['cull'] in [0,2] and not reserved&1
   fc,cc=p.plod[part];parts.append(dict(part=part,pass_=meta['pass_'],cull=meta['cull'],vertex_alpha=bool(reserved&1),geometry_prerequisite=eligible))
   for ci in range(fc,fc+cc):
    cl=p.clusters[ci];levels=[];counts=[];raw_count=[]
    for lv in range(cl['level_count']):
     fm,nm,_=p.levels[cl['first_level']+lv];counts.append(nm);ll=set();total=0
     for li in range(fm,fm+nm):
      if li not in shape_cache:
       corners,ix=p.let_tris(li);shape_cache[li]=[(tuple(tuple(0 if mesh['step'][k]==0 else int(corners[j,k]) for k in range(3)) for j in tri)) for tri in ix]
      for tri in shape_cache[li]:
       t=canonical(tri)
       if t is not None:ll.add(t);total+=1
     levels.append(ll);raw_count.append(total)
    keep,selected=invariant(levels,counts)
    if eligible and not singular:facets.extend(keep)
    r=dict(instance=instance,part=part,cluster=ci,level_meshlet_counts=counts,selectable_levels=selected,oriented_facets_per_level=[len(x) for x in levels],nondegenerate_triangles_per_level=raw_count,invariant_facets=len(keep),geometry_prerequisite=eligible,invariant_subset_verified=all(keep<=levels[lv] for lv in selected))
    clusters.append(r);instance_keys.append((pi,part,ci));instance+=1
  owner=ids[16+pl['placement']];comps=topology(facets)
  placements.append(dict(placement=pi,field=pl['placement'],owner=owner,conditional_source=owner!=255,mesh=pl['mesh'],singular_affine=singular,affine_bytes_sha256=hashlib.sha256(struct.pack('<12f',*pl['affine'].flatten())).hexdigest(),parts=parts,clusters=clusters,components=comps,oriented_invariant_facets=len(facets),closed_graphs=sum(x['closed_oriented_graph_prerequisite'] for x in comps),unresolved_boundaries=sum(len(x['boundary_edges']) for x in comps),enclosure_proven=False,fail_open=True))
 weighted=[]
 for replay in v.replay:
  rows=json.loads(replay.read_text());frames=[x['frame'] for x in rows]
  if frames!=list(range(500,795,7)):raise ValueError('Wrong retained camera frame window')
  totals=collections.Counter()
  for frame in rows:
   if len(frame['instances'])!=len(instance_keys):raise ValueError('Replay instance mismatch')
   for j,r in enumerate(frame['instances']):
    if r['instance']!=j or tuple(r[k] for k in ['placement','part','cluster'])!=instance_keys[j]:raise ValueError('Replay source namespace mismatch')
    totals[r['placement']]+=r['corners']
  weighted.append(dict(input=identity(replay),frames=len(rows),label='Earlier camera-build baked-pose host selector weights only; not current target counters or hull visibility',mean_selected_corners=sum(totals.values())/len(rows),closed_graph_prerequisite_corners_mean=sum(totals[i] for i,r in enumerate(placements) if r['closed_graphs'])/len(rows)))
 out=dict(schema=1,kind='Exact all-selectable-LOD invariant source-surface lemma and fail-open topology prerequisite; no hull/cull admission',tool=identity(Path(__file__)),source=source,staging_plan=identity(v.staging_plan),prepared_receipt=identity(root/'prepare-receipt.json'),reader=identity(reader),inputs=files,mesh_crc=f'{p.mesh_crc:08x}',policy_crc=f'{p.sidecar_crc:08x}',placements=placements,historical_camera_weights=weighted,total_clusters=instance,all_lod_subset_verified=all(c['invariant_subset_verified'] for r in placements for c in r['clusters']),actual_runtime_cuts=0,enclosures_proven=0,runtime_admitted=False,fail_open=True,limitations=['No seam welding, planar fills or sampled-ray enclosure.', 'Every cluster independently selects a source LOD; witnesses intersect that cluster selectable levels, including authored empty base.', 'Faces lost from this conservative subset are unresolved coverage, not proved physical holes.', 'Closed oriented edge graph is not non-self-intersection, interior-volume, source-state, numeric or material proof.', 'No unconditional current emitted opaque/depth/prefix/affine receipt is provided; all geometry remains drawn.', 'No all-LOD target interior membership, portal proof, timing, new data option or runtime implementation is claimed.'])
 v.out.parent.mkdir(parents=True,exist_ok=True)
 with v.out.open('x') as f:json.dump(out,f,indent=1);f.write('\n')
 print(json.dumps(dict(source=source['owned_head'],placements=len(placements),clusters=instance,invariant_facets=sum(r['oriented_invariant_facets'] for r in placements),closed_graphs=sum(r['closed_graphs'] for r in placements),unresolved_boundaries=sum(r['unresolved_boundaries'] for r in placements),enclosures_proven=0,runtime_cuts=0,historical_camera_weights=weighted)))

if __name__=='__main__':main()
