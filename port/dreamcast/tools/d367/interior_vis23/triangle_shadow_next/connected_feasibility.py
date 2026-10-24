#!/usr/bin/env python3
"""Exactly one authenticated discovery patch, full camera domains, IDEAL only.

No sampled visibility proof, welded endpoint, fitted hull, new target bit or
renderer/data change. Source and target geometry are redecoded from exact pins.
"""
import argparse
import collections
import json
import resource
from fractions import Fraction as Q
from pathlib import Path
import feasibility as f
import smaller_domains as s
from exact_patch import indexed_disk,prove_patch

DISCOVERY='f153b9a467a1c653346b1955868164453a36a847d81df67bc4f05a2edb058964'
REVIEWS={'review-connected-patch-plan.md':'aff55c37c441cab6c8d5d19e69127122e668efc8533bce4b2c732ba0a71f810f','review-boundary-kernel.md':'6099aa1d7364b92362590f70663ebb42a844bd57df23564249fa6e3b81a5871b'}
SMALLER='e42fac7e3521c7ac549f2fb1a7ddd47aaffcb5b7d80d94f496cdf83a8fc5e6b7'
TRIANGLES=((8,9,10),(11,10,9),(10,11,12),(10,12,13),(14,13,12),(13,14,15))

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 for n in ('source-tree','r6','base-evidence','smaller-evidence','discovery','reviews','out'):ap.add_argument('--'+n,type=Path,required=True)
 a=ap.parse_args()
 if a.out.exists():raise ValueError('Preserve old report')
 resource.setrlimit(resource.RLIMIT_AS,(f.LIMIT,f.LIMIT))
 if f.digest(a.discovery)!=DISCOVERY:raise ValueError('Discovery source changed')
 for name,digest in REVIEWS.items():
  if f.digest(a.reviews/name)!=digest:raise ValueError('Unreviewed theorem')
 basepath=a.base_evidence/'bounded512-report.json';smallpath=a.smaller_evidence/'report.json'
 if f.digest(basepath)!=s.MAIN_REPORT or f.digest(smallpath)!=SMALLER or f.digest(a.r6/'report.json')!=f.REPORT_SHA:raise ValueError('Frozen binding changed')
 base=json.loads(basepath.read_text());small=json.loads(smallpath.read_text());prior=json.loads((a.r6/'report.json').read_text())
 source=f.audit.bind_source(a.source_tree,a.r6/'current-resolved-knobs.txt')
 for pin in base['inputs'].values():
  if f.digest(Path(pin['path']))!=pin['sha256']:raise ValueError('Exact geometry/physical policy/ID input changed')
 root=Path(base['inputs']['ps2-world.r4pw']['path']).parent;p=f.Pkg(root/'ps2-world.re4mesh',root/'ps2-world.r4pw');policy=(root/'ps2-world.r4pw').read_bytes();ids=(root/'ps2-world.ids').read_bytes()[16:16+len(p.placements)]
 materials,materialpins=f.material_census(a.source_tree,Path(base['material']['pack']['path']),p)
 faces,targets,census=f.collect(p,policy,ids,materials)
 if census!=base['census']:raise ValueError('Census changed')
 pl=p.placements[165];mesh=p.meshes[pl['mesh']];cl=p.clusters[234];fc,nc=p.plod[230];first,nm,_=p.levels[cl['first_level']]
 if not(mesh['first_part']<=230<mesh['first_part']+mesh['part_count'] and fc<=234<fc+nc and cl['level_count']==1 and first<=951<first+nm and pl['placement']==165):raise ValueError('Whole source/LOD owner changed')
 cs,ts=p.let_tris(951)
 if tuple(tuple(ts[i]) for i in range(4,10))!=TRIANGLES:raise ValueError('Actual parity-correct triples changed')
 world,det=f.mapping(p,165)
 if not det or 165 in f.audit.conditional_fields(ids):raise ValueError('Conditional/singular source')
 for tri in TRIANGLES:
  if not any(x['placement']==165 and x['part']==230 and x['cluster']==234 and x['meshlet']==951 and tuple(x['corners'])==tri for x in faces):raise ValueError('Actual face not stable ordinary opaque all-LOD source')
 vertices={i:world(cs[i][:3]) for tri in TRIANGLES for i in tri};topology=indexed_disk(TRIANGLES)
 target=targets[299]
 if tuple(target[k] for k in ('placement','part','cluster','field'))!=(209,268,272,209) or not target['ordinary'] or target['conditional']:raise ValueError('Target allLOD namespace changed')
 discovery=json.loads(a.discovery.read_text());patch=discovery['cameras'][0]['patches']['5131']
 if tuple(tuple(x[1:]) for x in patch['actual_component_triangles'])!=TRIANGLES or tuple(patch['source'][k] for k in ('placement','part','cluster','level','meshlet'))!=(165,230,234,0,951):raise ValueError('Discovery actual endpoint binding changed')
 prep=a.r6/'prepared/prepare-receipt.json'
 if f.digest(prep)!=prior['prepared_receipt']['sha256']:raise ValueError('Camera receipt changed')
 frames,weights,logs=s.raw_cameras(json.loads(prep.read_text()),prior,a.r6)
 if len(frames)!=129 or [(x['label'],x['frame'],x['view_bits'],[str(v) for v in x['eye']]) for x in frames]!=[(x['label'],x['frame'],x['view_bits'],x['eye_exact']) for x in small['per_camera']]:raise ValueError('Authentic 129-eye binding changed')
 domains={d['cell']:d for d in f.cells(a.base_evidence/'preserved-control.pvs',p)};rows=[];summary={};cache={}
 for size in (2000,500,250):
  counts=collections.defaultdict(collections.Counter);size_rows=[]
  for camera,old in zip(frames,small['per_camera']):
   if old['old_cell'] is None:continue
   full=domains[old['old_cell']]['box'];box=full if size==2000 else s.window(camera['eye'],full,size)
   if size!=2000 and [[str(v) for v in side] for side in box]!=old['variants'][str(size)]['box_exact']:raise ValueError('Complete old-height domain changed')
   selected=weights[camera['label']][camera['frame']][299]
   if tuple(selected[k] for k in ('placement','part','cluster'))!=(209,268,272):raise ValueError('Host pricing namespace changed')
   outcomes={}
   for mode in ('strict_convex','boundary_kernel'):
    key=(mode,box)
    if key not in cache:
     nominal=prove_patch(vertices,TRIANGLES,box,target['box'],boundary_mode=mode)
     requested=prove_patch(vertices,TRIANGLES,box,target['box'],vertex_error=32,eye_error=32,target_error=32,eye_clearance=2000,target_clearance=32,boundary_mode=mode) if nominal['proven'] else None
     cache[key]=dict(nominal=nominal,requested_interval=requested)
    result=cache[key];outcomes[mode]=result;counter=counts[mode];counter['domains']+=1
    counter['nominal_positive']+=int(result['nominal']['proven']);counter['requested_interval_positive']+=int(bool(result['requested_interval'] and result['requested_interval']['proven']))
    counter['nominal_host_selected_corners']+=selected['corners'] if result['nominal']['proven'] else 0
    counter['requested_host_selected_corners']+=selected['corners'] if result['requested_interval'] and result['requested_interval']['proven'] else 0
    if not result['nominal']['proven']:counter['refusal_'+result['nominal']['reason']]+=1
   size_rows.append(dict(label=camera['label'],frame=camera['frame'],old_cell=old['old_cell'],eye_exact=[str(v) for v in camera['eye']],view_bits=camera['view_bits'],raw_camera_record_sha256=camera['raw_camera_record_sha256'],box_exact=[[str(v) for v in side] for side in box],selected_target=selected,outcomes=outcomes,actual_selector_preimage_certified=False,runtime_admitted_corners=0))
  summary[str(size)]={k:dict(v) for k,v in counts.items()};rows.append(dict(size_mm=size,per_camera=size_rows));print(json.dumps(dict(size=size,summary=summary[str(size)])),flush=True)
 out=dict(kind='ONE actual connected six-face patch full-domain IDEAL strict/kernel feasibility',tool=f.identity(Path(__file__)),dependencies={n:f.identity(Path(__file__).with_name(n)) for n in ('exact_patch.py','exact_shadow.py','exact_union.py','feasibility.py','smaller_domains.py')},source=source,inputs=base['inputs'],r6=f.identity(a.r6/'report.json'),discovery=f.identity(a.discovery),reviews={n:f.identity(a.reviews/n) for n in REVIEWS},camera_profile='Historical e9bf7 capture only, 54 s requested / 55.4-55.8 s wall, not current exact55 qualification',authentic_logs=logs,source_geometry=dict(placement=165,part=230,cluster=234,meshlet=951,level_count=1,all_selectable_levels=[0],actual_parity_triangles=TRIANGLES,positions={i:[str(v) for v in p] for i,p in vertices.items()},topology=topology,conditional=False,material=materials[230]),target={k:([[str(v) for v in side] for side in value] if k=='box' else value) for k,value in target.items()},material_pins=materialpins,source_prefix=dict(ordinal_precedes=True,actual_emission_receipt='UNPROVEN'),summaries=summary,results=rows,runtime_admitted_cuts=0,modelled_ms=None,go_1ms=False,limits=dict(address_space_bytes=f.LIMIT,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,jobs=1),limitations=['IDEAL nominal/requested32mm intervals do not bound actual SH4, true eye/selector, near/far/clip/cache/kernel/cull, raster/depth or prefix/material receipts.','One source index is a correlated physical endpoint variable; actual common projected construction remains unqualified.','Host baked-pose divisor20 target corner counts are not current runtime counters and cannot supply ms.','Current table guard single-LOD source condition retained. Target allLOD box includes every authored level; empty level falls back.','No PVS/table/data/target partition/runtime/SDK/guest/media/asset/recipe/allocation/converter or actor changes.'])
 a.out.parent.mkdir(parents=True,exist_ok=True)
 with a.out.open('x') as dst:json.dump(out,dst,indent=1);dst.write('\n')
 print(json.dumps(dict(runtime_admitted=0,modelled_ms=None,limits=out['limits'])))

if __name__=='__main__':main()
