#!/usr/bin/env python3
"""Same20 closest pairs, authentic old matrix eyes, complete local camera boxes.

No new source search, point-eye occlusion inference, table or renderer change.
500mm first; local250mm only diagnoses zero nominal weighted500mm yield. The
old complete signed-decimetre Y band and requested uncertainty are retained.
"""
import argparse
import collections
import json
import re
import resource
import struct
from fractions import Fraction as Q
from pathlib import Path
import feasibility as f
from exact_shadow import cross,dot,prove

PAIR_REPORT='9fe03775515b1c3c0ea1081bbde8c3bda949aa6b44e6c05c3bd370f60530781c'
MAIN_REPORT='2350db18183592f05d8d9b3fb7bcd8b13f5357f21951e4b7633434477b2436b0'
REVIEW='9d29d4869e216547da4142e3f7edac949c7e8c122d12f9e181502b780174c86a'
CAMERA=re.compile(r'PS2CAM f=(\d+) cf=([0-9a-fA-F]{8}) c=((?:[0-9a-fA-F]{8} ){11}[0-9a-fA-F]{8}) p=((?:[0-9a-fA-F]{8} ){6}[0-9a-fA-F]{8})')


def f32(x):return struct.unpack('<f',struct.pack('<f',float(x)))[0]


def eye_from_bits(words):
    if len(words)!=12:raise ValueError('View arity')
    v=[Q(struct.unpack('<f',struct.pack('<I',int(w,16)))[0]) for w in words]
    rows=[v[4*i:4*i+3] for i in range(3)];t=[v[4*i+3] for i in range(3)]
    cof=[cross(rows[1],rows[2]),cross(rows[2],rows[0]),cross(rows[0],rows[1])]
    det=dot(rows[0],cof[0])
    if not det:raise ValueError('Singular recorded view')
    return tuple(-sum(t[i]*cof[i][k] for i in range(3))/det for k in range(3))


def window(eye,old,size):
    if size not in (500,250):raise ValueError('Unapproved bounded quantization')
    x0,z0=Q(f32(eye[0]-size//2)),Q(f32(eye[2]-size//2))
    box=((x0,old[0][1],z0),(x0+size,old[1][1],z0+size))
    if not(box[0][0]<eye[0]<box[1][0] and box[0][2]<eye[2]<box[1][2] and box[0][1]<=eye[1]<=box[1][1]):raise ValueError('Authentic eye outside full serialized local domain')
    return box


def wsl_path(path):
    if path.startswith('C:'):return Path('/mnt/c/'+path[3:].replace('\\','/'))
    return Path(path)


def raw_cameras(prepared,prior,r6):
    weights={};frames=[];total=0;logs=[]
    for label,entry in zip(('hut','turn','walk'),prepared['logs']):
        log=wsl_path(entry['path'])
        if f.digest(log)!=entry['sha256']:raise ValueError('Authentic capture log changed')
        byframe={}
        for m in CAMERA.finditer(log.read_text(errors='replace')):
            total+=1;frame=int(m[1])
            if frame in range(500,795,7):byframe[frame]=m
        if sorted(byframe)!=list(range(500,795,7)):raise ValueError('Missing retained authentic camera')
        replay=r6/(label+'-selected-instances.json')
        pin=next(x['input']['sha256'] for x in prior['historical_camera_weights'] if Path(x['input']['path']).name==replay.name)
        if f.digest(replay)!=pin:raise ValueError('Frozen selector weights changed')
        rows=json.loads(replay.read_text())
        if [r['frame'] for r in rows]!=sorted(byframe):raise ValueError('Camera/selector frames mismatch')
        weights[label]={r['frame']:r['instances'] for r in rows}
        for frame,m in sorted(byframe.items()):
            eye=eye_from_bits(m[3].split())
            frames.append(dict(label=label,frame=frame,eye=eye,view_bits=m[3].split(),projection_bits=m[4].split(),far_bits=m[2],raw_camera_record_sha256=__import__('hashlib').sha256(m[0].encode()).hexdigest()))
        logs.append(dict(label=label,log=f.identity(log),weights=f.identity(replay)))
    if total!=prepared['exact_cameras'] or total!=3155:raise ValueError('Full old camera record count changed')
    return frames,weights,logs


def price(cases,weights,targets,faces):
    nominal={x['target'] for x in cases if x['nominal']['proven']}
    safe={x['target'] for x in cases if x['requested_interval'] and x['requested_interval']['proven']}
    def corners(ids):return sum(weights[i]['corners'] for i in ids)
    single=collections.defaultdict(set);single_safe=collections.defaultdict(set)
    for x in cases:
        s=faces[x['source']];target=targets[x['target']]
        if s['level_count']==1 and target['placement']>s['placement']:
            if x['nominal']['proven']:single[x['source']].add(x['target'])
            if x['requested_interval'] and x['requested_interval']['proven']:single_safe[x['source']].add(x['target'])
    return dict(nominal_union_cluster_targets=sorted(nominal),nominal_union_host_selected_corners=corners(nominal),requested_interval_union_cluster_targets=sorted(safe),requested_interval_union_host_selected_corners=corners(safe),best_one_source_single_lod_prefix_nominal_corners=max([corners(v) for v in single.values()]+[0]),best_one_source_single_lod_prefix_interval_corners=max([corners(v) for v in single_safe.values()]+[0]),runtime_admitted_corners=0)


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--source-tree',required=True,type=Path);ap.add_argument('--evidence',required=True,type=Path);ap.add_argument('--r6',required=True,type=Path);ap.add_argument('--review',required=True,type=Path);ap.add_argument('--out',required=True,type=Path);a=ap.parse_args()
    if a.out.exists():raise ValueError('Preserve old output')
    resource.setrlimit(resource.RLIMIT_AS,(f.LIMIT,f.LIMIT))
    if f.digest(a.review)!=REVIEW:raise ValueError('Independent prototype review missing/changed')
    mainpath=a.evidence/'bounded512-report.json';diagpath=a.evidence/'diagnostic-report.json'
    if f.digest(mainpath)!=MAIN_REPORT or f.digest(diagpath)!=PAIR_REPORT:raise ValueError('Frozen bounded cohort changed')
    base=json.loads(mainpath.read_text());diag=json.loads(diagpath.read_text());pairs=diag['closest_opposite_plane_pairs']
    if len(pairs)!=20 or len(base['selected_faces'])!=512:raise ValueError('Fixed cohort cardinality')
    prior=json.loads((a.r6/'report.json').read_text())
    if f.digest(a.r6/'report.json')!=f.REPORT_SHA:raise ValueError('R6 report changed')
    prep=a.r6/'prepared/prepare-receipt.json'
    if f.digest(prep)!=prior['prepared_receipt']['sha256']:raise ValueError('Camera provenance receipt changed')
    source=f.audit.bind_source(a.source_tree,a.r6/'current-resolved-knobs.txt')
    for name,pin in base['inputs'].items():
        if f.digest(Path(pin['path']))!=pin['sha256']:raise ValueError('Exact current input changed')
    root=Path(base['inputs']['ps2-world.r4pw']['path']).parent;p=f.Pkg(root/'ps2-world.re4mesh',root/'ps2-world.r4pw')
    materials,_=f.material_census(a.source_tree,Path(base['material']['pack']['path']),p)
    _,targets,census=f.collect(p,(root/'ps2-world.r4pw').read_bytes(),(root/'ps2-world.ids').read_bytes()[16:16+len(p.placements)],materials)
    if census!=base['census']:raise ValueError('Material/ownership/surface census changed')
    domains=f.cells(a.evidence/'preserved-control.pvs',p);domainmap={d['cell']:d for d in domains};faces=base['selected_faces']
    frames,weights,logs=raw_cameras(json.loads(prep.read_text()),prior,a.r6)
    triangle={}
    for pair in pairs:
        i=pair['source'];s=faces[i];world,_=f.mapping(p,s['placement']);triangle[i]=tuple(world(q) for q in s['grid'])
        if prove(triangle[i],domainmap[pair['cell']]['box'],targets[pair['target']]['box'])!=pair['exact_nominal']:raise ValueError('Current oracle differs from frozen exact pair result')
    rows=[]
    for camera in frames:
        eye=camera['eye'];matching=[d for d in domains if all(d['box'][0][k]<=eye[k]<=d['box'][1][k] for k in range(3))]
        if len(matching)>1:raise ValueError('Boundary camera has ambiguous original domain')
        rows.append(dict(**{k:v for k,v in camera.items() if k!='eye'},eye_exact=[str(x) for x in eye],old_cell=None if not matching else matching[0]['cell'],variants={}))
    def run(size):
        allcases=0;positive=0;summary=collections.defaultdict(lambda:collections.Counter());refusals=collections.Counter()
        for camera,row in zip(frames,rows):
            relevant=[q for q in pairs if q['cell']==row['old_cell']]
            cases=[];box=None
            if relevant:
                box=window(camera['eye'],domainmap[row['old_cell']]['box'],size)
                for pair in relevant:
                    nominal=prove(triangle[pair['source']],box,targets[pair['target']]['box']);allcases+=1
                    if nominal['proven']:positive+=1
                    else:refusals[nominal['reason']]+=1
                    safe=prove(triangle[pair['source']],box,targets[pair['target']]['box'],vertex_error=32,eye_error=32,target_error=32,eye_clearance=2000,target_clearance=32) if nominal['proven'] else None
                    cases.append(dict(source=pair['source'],target=pair['target'],nominal=nominal,requested_interval=safe))
            selected=weights[row['label']][row['frame']]
            if len(selected)!=318 or any(r['instance']!=i or any(r[k]!=targets[i][k] for k in ('placement','part','cluster')) for i,r in enumerate(selected)):raise ValueError('Current selector target namespace mismatch')
            pricing=price(cases,selected,targets,faces)
            row['variants'][str(size)]=dict(applicable=bool(cases),box_exact=None if box is None else [[str(x) for x in q] for q in box],nx=1,nz=1,file_size_with_one_set=128,selector_preimage_certified=False,cases=cases,pricing=pricing)
            for key,value in pricing.items():
                if isinstance(value,int):summary[row['label']][key]+=value
        return dict(cases=allcases,exact_nominal_positive_cases=positive,exact_nominal_refusals=dict(refusals),host_corner_sums={k:dict(v) for k,v in summary.items()},camera_counts={label:sum(r['label']==label for r in rows) for label in weights})
    summaries={'500':run(500)}
    total500=sum(s['nominal_union_host_selected_corners'] for s in summaries['500']['host_corner_sums'].values())
    if total500==0 and summaries['500']['exact_nominal_refusals'].get('edge_unknown',0):summaries['250']=run(250)
    out=dict(kind='Same20 closest fixed source/cluster pairs in authentic-camera-centered complete local domains; IDEAL only',tool=f.identity(Path(__file__)),dependencies={p.name:f.identity(p) for p in [Path(f.__file__),Path(__file__).with_name('exact_shadow.py'),Path(f.audit.__file__),Path(f.__file__).parent.parent/'surface_mesh.py']},source=source,independent_review=f.identity(a.review),base_report=f.identity(mainpath),closest_pairs=f.identity(diagpath),authentic_capture_logs=logs,original_camera_profile=base['camera_provenance'],original_domains='Full frozen 2m cells and same integer-decimetre Y limits; all20 baseline exact tests refuse.',source_faces_fixed=512,closest_pairs_fixed=20,actual_retained_cameras=len(rows),all_logged_exact_cameras=3155,quantization_order='500mm first; local250mm only because500mm has zero nominal weighted corners and edge refusals remain',summaries=summaries,per_camera=rows,assumptions=base['ideal_uncertainty'],limits=dict(rlimit_as_bytes=f.LIMIT,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,jobs=1),runtime_admitted_cuts=0,modelled_ms=None,go_1ms=False,limitations=['No extra face/target search or new partition. Existing whole-cluster targets only.','Authentic eyes are exact inverses of recorded f32 views; not point-eye occlusion tests. Complete500/250mm boxes retain original full Y bands.','Local origins are serialized f32; actual float-selector preimages and true renderer eye perturbations are not certified.','32mm and2000mm requested engineering conditions do not certify SH4/near/raster coverage.','Corner weights are frozen current-divisor20 baked-pose host replay at43 frames per old camera capture, not current runtime counters.','Nominal unions may need several source panels. One-source one-LOD prefix prices avoid claiming an unconstructed global16-panel certificate.','Actual source cull/near/far/material/numeric/emission/committed receipts remain absent; all runtime geometry draws.'])
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open('x') as dst:json.dump(out,dst,indent=1);dst.write('\n')
    print(json.dumps(dict(summaries=summaries,limits=out['limits'],runtime_admitted=0,modelled_ms=None)))

if __name__=='__main__':main()
