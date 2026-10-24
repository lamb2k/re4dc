#!/usr/bin/env python3
"""Sparse exact IDEAL triangle-shadow feasibility; never emits a PVS or asset.

Pins the frozen source, physical affines, ownership, all-LOD geometry, intrinsic
opacity descriptors and old camera corpus. Finite views weight only the proven
full-box results. No renderer/raster admission or hardware/performance claim.
"""
import argparse
import collections
import hashlib
import json
import re
import resource
import struct
import sys
from fractions import Fraction as Q
from itertools import product
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
import lod_surface_audit as audit
from surface_mesh import Pkg
from exact_shadow import corners, cross, dot, nominal_filter, prove, sub

PACK_SHA='5bba464a1175d8ebe153d5aecb629ea9637807c2bf4fc438a32c17148d0729da'
REPORT_SHA='7a1bb45dc427edc011e0322eb1bc3495157b2b3d794ac23d72fe3d3732d17a60'
LIMIT=256*1024*1024


def digest(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def identity(p):return dict(path=str(p),bytes=Path(p).stat().st_size,sha256=digest(p))


def material_census(repo,pack,p):
    if digest(pack)!=PACK_SHA:raise ValueError('Unreviewed actual texture package')
    hdr=repo/'port/dreamcast/room/texture_package.hpp'
    table=repo/'port/dreamcast/tools/d367/texture_rect21/scoped_representations.inc'
    flags={k:1<<int(re.search(k+r'\s*=\s*1U\s*<<\s*(\d+)U',hdr.read_text())[1]) for k in ('kAlpha','kBinaryAlpha','kMipmap','kTopDrop')}
    forbidden=flags['kAlpha']|flags['kBinaryAlpha']|flags['kTopDrop']
    reps={}
    for line in table.read_text().splitlines():
        if line.startswith('{'):
            row=[int(x,0) for x in re.findall(r'(0x[0-9a-f]+|[0-9]+)U',line)]
            if len(row)!=11:raise ValueError('Rect21 row contract')
            reps[tuple(row[:4])]=tuple(row[4:])
    results={}
    with pack.open('rb') as f:
        magic,ver,n,off,_,_=struct.unpack('<8s5I',f.read(28))
        if magic!=b'RE4PAK1\0' or ver!=1:raise ValueError('Pack format')
        f.seek(off);rows=list(struct.iter_unpack('<4I',f.read(16*n)))
        index={(crc,fnv):(o,s) for crc,fnv,o,s in rows}
        if len(index)!=n:raise ValueError('Duplicate pack key')
        for part,m in enumerate(p.pmeta):
            key=(m['crc'],m['fnv']);reason=None;desc=None
            if key not in index:reason='missing pack descriptor'
            else:
                o,size=index[key];f.seek(o);th=struct.unpack('<8s10I',f.read(48))
                if th[0]!=b'RE4DCTX\0' or th[4]!=1:raise ValueError('Texture member format')
                f.seek(o+th[5]);t=struct.unpack('<64s8I',f.read(96))
                desc=(t[1],t[2],t[3],t[6],t[7],t[5],th[8])
                if desc[2]!=0:reason='not intrinsic RGB565'
                elif desc[3]&forbidden:reason='alpha/binary-alpha/true-topdrop'
                elif desc[:2]!=(m['w'],m['h']) and reps.get((*key,m['w'],m['h']))!=desc:reason='unproved size adaptation'
            results[part]=dict(eligible=reason is None,reason=reason,descriptor=desc,logical=[*key,m['w'],m['h']])
    return results,dict(pack=identity(pack),header=identity(hdr),rect21_table=identity(table),actual_flags=flags,scope='Immutable descriptor prerequisite only; actual residency/header/depth/material commit still required')


def mapping(p,pi):
    pl=p.placements[pi];m=p.meshes[pl['mesh']]
    affine=[[Q(float(x)) for x in row] for row in pl['affine']]
    org=list(map(lambda x:Q(float(x)),m['origin']));step=list(map(lambda x:Q(float(x)),m['step']))
    def world(q):
        local=[org[k]+step[k]*int(q[k]) for k in range(3)]
        return tuple(sum((affine[i][k]*local[k] for k in range(3)),affine[i][3]) for i in range(3))
    determinant=dot(affine[0][:3],cross(affine[1][:3],affine[2][:3]))
    return world,determinant


def collect(p,policy,ids,materials):
    conditional=audit.conditional_fields(ids)
    faces=[];targets=[];reasons=collections.Counter();all_stable=0
    for pi,pl in enumerate(p.placements):
        mesh=p.meshes[pl['mesh']];world,determinant=mapping(p,pi)
        static=pl['placement'] not in conditional and determinant!=0
        for part in range(mesh['first_part'],mesh['first_part']+mesh['part_count']):
            meta=p.pmeta[part];fc,nc=p.plod[part]
            material=materials[part]['eligible'] and meta['pass_']==0 and not(policy[32+part*16+15]&1) and meta['cull'] in (0,2)
            for ci in range(fc,fc+nc):
                cl=p.clusters[ci];levels=[];counts=[];allq=[];refs={}
                for lv in range(cl['level_count']):
                    fm,nm,_=p.levels[cl['first_level']+lv];counts.append(nm);facets=set()
                    for li in range(fm,fm+nm):
                        cs,ts=p.let_tris(li)
                        allq.extend(tuple(int(c[k]) for k in range(3)) for c in cs)
                        for triple in ts:
                            raw=tuple(tuple(0 if mesh['step'][k]==0 else int(cs[j][k]) for k in range(3)) for j in triple)
                            facet=audit.canonical(raw)
                            if facet is not None:
                                facets.add(facet)
                                # Preserve the actual parity-correct source triple. Cyclic
                                # canonicalization is geometry only, not matcher identity.
                                refs.setdefault(facet,(lv,li,tuple(triple),raw))
                    levels.append(facets)
                keep,selected=audit.invariant(levels,counts)
                all_stable+=len(keep)
                target=dict(instance=len(targets),placement=pi,field=pl['placement'],part=part,cluster=ci,static=static,ordinary=meta['pass_']==0,level_count=cl['level_count'])
                if allq:
                    lo=tuple(min(q[k] for q in allq) for k in range(3));hi=tuple(max(q[k] for q in allq) for k in range(3))
                    wc=[world(q) for q in product(*zip(lo,hi))]
                    target['box']=(tuple(min(q[k] for q in wc) for k in range(3)),tuple(max(q[k] for q in wc) for k in range(3)))
                    target['box_float']=tuple(tuple(float(x) for x in b) for b in target['box'])
                targets.append(target)
                if not static:reasons['conditional_or_singular_faces']+=len(keep);continue
                if not material:reasons['unproved_material_or_path_faces']+=len(keep);continue
                for facet in sorted(keep):
                    lv,li,triple,raw=refs[facet]
                    # Use raw order, including exact source strip parity.
                    wf=tuple(tuple(float(x) for x in world(q)) for q in raw)
                    n=cross(sub(wf[1],wf[0]),sub(wf[2],wf[0]));area2=sum(x*x for x in n)
                    if not area2:continue
                    faces.append(dict(placement=pi,field=pl['placement'],part=part,cluster=ci,meshlet=li,level=lv,corners=triple,grid=raw,level_count=cl['level_count'],cull=meta['cull'],area2=area2))
    return faces,targets,dict(all_stable_faces=all_stable,eligible_stable_faces=len(faces),excluded=dict(reasons),unconditional_static_target_clusters=sum(t['static'] and t['ordinary'] and 'box' in t for t in targets))


def cells(path,p):
    b=path.read_bytes();h=struct.unpack_from('<4s7I3f5I',b)
    magic,version,crc,mb,pc,ni,nx,nz,x0,z0,size,ns,sb,active,_,_=h
    if (magic,version,crc,mb,pc,ni)!=(b'R4PV',1,p.mesh_crc,len(p.m),p.sidecar_crc,318):raise ValueError('Frozen control PVS identity mismatch')
    extent=64+8*nx*nz+ns*sb
    if len(b)!=((extent+31)&~31) or any(b[extent:]):raise ValueError('Cell padded extent')
    sets=b[64+8*nx*nz:extent]
    if any(not(sets[k*sb+i//8]>>(i%8)&1) for k in range(ns) for i in range(ni)):raise ValueError('Expected preserved all-visible control')
    out=[]
    for i in range(nx*nz):
        ix,ylo,yhi,pad=struct.unpack_from('<HhhH',b,64+8*i)
        if ix==65535:continue
        if ix>=ns or pad:raise ValueError('Cell encoding')
        x,z=i%nx,i//nx
        lo=(Q(x0)+x*Q(size),Q(ylo*100),Q(z0)+z*Q(size))
        hi=(lo[0]+Q(size),Q(yhi*100),lo[2]+Q(size))
        out.append(dict(cell=i,box=(lo,hi),box_float=tuple(tuple(float(v) for v in q) for q in (lo,hi))))
    if len(out)!=active:raise ValueError('Cell count')
    return out


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source-tree',type=Path,required=True);ap.add_argument('--frozen',type=Path,required=True)
    ap.add_argument('--cells',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--faces-per-stratum',type=int,default=64)
    a=ap.parse_args()
    if not 1<=a.faces_per_stratum<=256:raise ValueError('Bounded sparse face cap')
    if a.out.exists():raise ValueError('Preserve old evidence')
    resource.setrlimit(resource.RLIMIT_AS,(LIMIT,LIMIT))
    r=a.frozen
    if digest(r/'report.json')!=REPORT_SHA:raise ValueError('Frozen R6 report mismatch')
    source=audit.bind_source(a.source_tree,r/'current-resolved-knobs.txt')
    inputs=r/'prepared/inputs'
    for name,pin in audit.FROZEN_INPUT_SHA256.items():
        if digest(inputs/name)!=pin:raise ValueError('Frozen input mismatch '+name)
    stage=json.loads((r/'current-staging-plan.json').read_text())
    for name in ('ps2-world.re4mesh','ps2-world.r4pw','ps2-world.ids'):
        if digest(Path(stage['replace']['dc/native/r10d/'+name]))!=digest(inputs/name):raise ValueError('Actual current source mismatch')
    p=Pkg(inputs/'ps2-world.re4mesh',inputs/'ps2-world.r4pw');policy=(inputs/'ps2-world.r4pw').read_bytes()
    ids=(inputs/'ps2-world.ids').read_bytes();original=Pkg(inputs/'ps2-world.re4mesh',inputs/'original.r4pw')
    if struct.unpack_from('<4sIII',ids)!=(b'R4ID',1,len(p.placements),original.sidecar_crc) or original.placements!=p.placements:raise ValueError('Original/current exact affine ownership binding')
    materials,materialpins=material_census(a.source_tree,Path(stage['replace']['dc/tex.pak']),p)
    faces,targets,census=collect(p,policy,ids[16:16+len(p.placements)],materials)
    domains=cells(a.cells,p)
    selected=[];strata={}
    for one in (True,False):
        group=sorted((f for f in faces if (f['level_count']==1)==one),key=lambda f:(-f['area2'],f['placement'],f['part'],f['cluster'],f['grid']))
        picked=group[:a.faces_per_stratum];selected.extend(picked)
        strata['single_lod' if one else 'multi_lod']=dict(eligible=len(group),examined=len(picked),ranking='largest exact-input float area squared; rank only, never proof')
    eligible=[t for t in targets if t['static'] and t['ordinary'] and 'box' in t]
    pairs=[];tested=0;filtered=0;exact_attempts=0
    for si,f in enumerate(selected):
        world,_=mapping(p,f['placement']);tri=tuple(world(q) for q in f['grid']);tf=tuple(tuple(float(x) for x in v) for v in tri)
        for d in domains:
            for t in eligible:
                # A cluster cannot certify itself. Prefix order is priced separately.
                if t['placement']==f['placement'] and t['cluster']==f['cluster']:continue
                tested+=1
                if not nominal_filter(tf,d['box_float'],t['box_float']):filtered+=1;continue
                exact_attempts+=1;nominal=prove(tri,d['box'],t['box'])
                if not nominal['proven']:continue
                safe=prove(tri,d['box'],t['box'],vertex_error=32,eye_error=32,target_error=32,eye_clearance=2000,target_clearance=32)
                pairs.append(dict(source=si,cell=d['cell'],target=t['instance'],nominal=nominal,requested_interval=safe,prefix_order=t['placement']>f['placement'],single_lod=f['level_count']==1))
        print(json.dumps(dict(progress_face=si+1,total_faces=len(selected),nominal_pairs=len(pairs))),flush=True)
    nominal={(x['cell'],x['target']) for x in pairs}
    safe={(x['cell'],x['target']) for x in pairs if x['requested_interval']['proven']}
    mechanical={(x['cell'],x['target']) for x in pairs if x['requested_interval']['proven'] and x['single_lod'] and x['prefix_order']}
    # Receipt sets/16-panel admission and actual clipping/header/raster are absent.
    out=dict(schema=1,kind='Sparse exact IDEAL triangle-shadow feasibility; no runtime admission',tool=identity(Path(__file__)),math_tool=identity(Path(__file__).with_name('exact_shadow.py')),source=source,inputs={name:identity(inputs/name) for name in audit.FROZEN_INPUT_SHA256},frozen_report=identity(r/'report.json'),staging_plan=identity(r/'current-staging-plan.json'),control_cells=identity(a.cells),material=materialpins,material_parts=materials,census=census,strata=strata,domains=len(domains),pair_tests=tested,float_rejections=filtered,exact_attempts=exact_attempts,nominal_hidden_cell_clusters=len(nominal),requested_interval_hidden_cell_clusters=len(safe),single_lod_prefix_prerequisite_cell_clusters=len(mechanical),selected_faces=selected,targets=[{k:v for k,v in t.items() if k not in ('box','box_float')} for t in targets],pairs=pairs,renderer_admitted_cell_clusters=0,actual_runtime_cuts=0,modelled_ms=None,go_1ms=False,coverage='Partial: top area-ranked face cap independently in one-LOD and multi-LOD strata. Untested faces remain unknown; no all-algorithm NO-GO.',ideal_uncertainty=dict(source_vertex_mm=32,eye_box_mm=32,target_box_mm=32,eye_plane_clearance_mm=2000,target_plane_clearance_mm=32,basis='Requested IDEAL perturbations only, not established actual SH4/raster error bounds'),limits=dict(rlimit_as_bytes=LIMIT,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,jobs=1),limitations=['Exact full-product geometry theorem only; no sampled-ray proof.','Serialized f32 grid and int16 Y cells are ideal domains. Actual f32 selector preimage and true view eye need independent enclosure.','Current all-LOD witness membership is not source emission. Actual source cull side/near/far/strip clipping/header/material/prefix receipts remain required.','32mm perturbations do not prove actual SH4/FTRV/reciprocal/FPSCR/viewport/raster edge/sample/depth coverage.','Single-LOD prefix is a prerequisite, not runtime compatibility qualification or 16-panel receipt coverage.','No table/data/renderer changes, no target run, no hardware gain, no source-exclusive current net cost model.'])
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open('x') as f:json.dump(out,f,indent=1);f.write('\n')
    print(json.dumps({k:out[k] for k in ('census','strata','domains','pair_tests','exact_attempts','nominal_hidden_cell_clusters','requested_interval_hidden_cell_clusters','single_lod_prefix_prerequisite_cell_clusters','renderer_admitted_cell_clusters','modelled_ms','limits')}))

if __name__=='__main__':main()
