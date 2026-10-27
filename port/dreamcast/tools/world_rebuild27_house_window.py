#!/usr/bin/env python3
"""Sparse C-only source-derived house frames, windows and porch exchange.

Private asset authoring only. Keeps original mesh/part/placement/UV/prelight
identities. Five window rings explicitly omit paired-panel dividers and relief;
all source groups, including omitted interior detail, remain in the exchange.
"""
import argparse, hashlib, json, sys
from pathlib import Path

PART_BUDGETS = {47:48,54:40,154:60}
LENGTH = [.99417922945167,0,-.10773884966382]
CROSS = [.10773884966382,0,.99417922945167]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def init(tools, dependencies):
    sys.path.insert(0,str(tools))
    global h,np,shapely,Polygon,box
    import world_rebuild27_house_whole as h
    h.setup(dependencies)
    np=h.np;shapely=h.shapely
    from shapely.geometry import Polygon,box


def polygon_parts(shape):
    return [p for p in (shape.geoms if hasattr(shape,'geoms') else [shape]) if p.geom_type=='Polygon']


def plane(feature, normal):
    normal=np.asarray(normal,float);normal/=np.linalg.norm(normal)
    u=np.cross([0,1,0],normal);u/=np.linalg.norm(u);v=np.cross(normal,u)
    indices=np.flatnonzero((feature.n@normal>.8)&(feature.area>1e-5))
    if not len(indices):raise ValueError('no outward source face '+feature.name)
    points=feature.p[indices]
    xy=np.stack((points@u,points@v),axis=2)
    region=shapely.union_all([Polygon(t) for t in xy])
    return normal,u,v,indices,region,float(np.max(points@normal))


def skin(feature,normal,door=False):
    normal,u,v,indices,region,depth=plane(feature,normal)
    holes=[Polygon(r) for p in polygon_parts(region) for r in p.interiors if Polygon(r).area>25]
    xmin,ymin,xmax,ymax=region.bounds
    if door:
        empty=box(xmin,ymin,xmax,ymax).difference(region)
        holes=[p for p in polygon_parts(empty) if p.area>10000]
        if not holes:raise ValueError('door opening source notch missing')
        holes=[max(holes,key=lambda p:p.area)]
    if not holes:raise ValueError('window source holes missing '+feature.name)
    aperture=shapely.union_all(holes)
    a,b,c,e=aperture.bounds
    # Three mm guard exceeds source-grid rounding; never silently fills an aperture.
    a-=3;b-=3;c+=3;e+=3
    a=max(a,xmin+1);c=min(c,xmax-1);e=min(e,ymax-1)
    if not door:b=max(b,ymin+1)
    else:b=ymin-3
    outer=[(xmin,ymin),(xmax,ymin),(xmax,ymax),(xmin,ymax)]
    inner=[(a,b),(c,b),(c,e),(a,e)]
    quads=[(outer[i],outer[(i+1)%4],inner[(i+1)%4],inner[i]) for i in range(4) if not(door and i==0)]
    target=[];actual=[];clipping=[]
    for quad in quads:
        for ids in ((0,1,2),(0,2,3)):
            points=[np.asarray(quad[i])[0]*u+np.asarray(quad[i])[1]*v+depth*normal for i in ids]
            if np.cross(points[1]-points[0],points[2]-points[0])@normal<0:points.reverse()
            raw=np.rint(((np.asarray(points)-feature.a[:,3])@feature.inv.T-feature.m[8:11])/feature.m[11:14]).astype(int)
            fitted=feature.world(np.clip(raw,0,65535));clipping.extend(np.linalg.norm(fitted-points,axis=1).tolist())
            if max(clipping)>100:raise ValueError('source grid envelope clip exceeds100mm')
            encoded=feature.encode(fitted);target.append(encoded)
            world=feature.world(np.asarray(encoded)[:,:3]);actual.append(Polygon(np.stack((world@u,world@v),axis=1)))
    emitted=shapely.union_all(actual)
    filled=float(emitted.intersection(aperture).area)
    if filled>1e-3:raise ValueError('quantized source aperture filled '+str(filled))
    return target,dict(operation='three-sided main entrance frame' if door else 'one opaque outer ring per physical window',maximum_grid_clip_mm=max(clipping),source_apertures=len(holes),source_aperture_area_mm2=float(aperture.area),quantized_source_aperture_filled_mm2=filled,opening_source_wkt=aperture.wkt,target_projected_wkt=emitted.wkt,projection_basis=[u.tolist(),v.tolist(),normal.tolist()],source_front_triangle_indices=indices.tolist(),outer_bounds_mm=[xmin,ymin,xmax,ymax],inner_bounds_mm=[a,b,c,e],outward_depth_mm=depth,approximation='planar bounding ring; paired overlapping panels merged, inner opening enlarged; existing wall reveals retain depth')


def joined(d,rows,name):
    placement=rows[0][0]['placement'];part=rows[0][0]['part']
    assert all(r['placement']==placement and r['part']==part for r,f in rows)
    ids=[i for r,f in rows for i in r['source_ids']]
    triangles=[t for r,f in rows for t in f.source]
    return h.Feature(d,part,placement,triangles,name),ids


def record(d,rows,label,target=None,proof=None,feature=None,losses=None):
    feature,ids=joined(d,rows,label) if feature is None else (feature,[i for r,f in rows for i in r['source_ids']])
    target=[] if target is None else target
    witnesses=[]
    if feature.samples:
        assert len(feature.samples)==len(target)*3
        for i,s in enumerate(feature.samples):
            witnesses.append(dict(target_triangle=i//3,target_corner=i%3,source_id=ids[s['source_triangle']],weights=s['weights'],distance_mm=s['distance_mm'],normal_dot=s['normal_dot']))
    elif target:
        # Exact source corner witnesses for retained originals.
        for i in range(len(target)):
            for j in range(3):witnesses.append(dict(target_triangle=i,target_corner=j,source_id=ids[i],weights=[int(k==j)for k in range(3)],distance_mm=0,normal_dot=1))
    return dict(label=label,part=feature.part,mesh=feature.mesh,placement=feature.placement,source_components=[r['component']for r,f in rows],source_ids=ids,target=target,source_triangles=len(ids),target_triangles=len(target),retained_source_ids=ids if target==feature.source else [],replaced_source_ids=ids if target and target!=feature.source else [],omitted_source_ids=ids if not target else [],preserved=['original material key, placement and mesh-grid basis','every source aperture remains clear'] if target else [],losses=losses or [],opening_proof=proof or {},attribute_witnesses=witnesses)


def build(source,plan_path):
    plan=json.loads(plan_path.read_text());pins=plan['inputs']['A']['sha256']
    actual={name:digest(source/name) for name in pins}
    if actual!=pins:raise ValueError('all five baseline source pins required')
    if len(actual)!=5:raise ValueError('five source files required')
    d,files,owners,policy=h.w.load(source)
    features=[(r,f)for r,f in h.source_features(d,plan)if r['part']in PART_BUDGETS]
    parts={str(p):[]for p in PART_BUDGETS};assigned=set()
    def add(rows,label,mode='exact',normal=None,losses=None):
        f,ids=joined(d,rows,label)
        if mode=='exact':target=f.source;proof={'operation':'source triangles exact, including all side/orientation coverage'}
        elif mode in('ring','door'):target,proof=skin(f,normal,door=mode=='door')
        else:target=[];proof={'operation':'explicit C detail omission'}
        out=record(d,rows,label,target,proof,f,losses);parts[str(f.part)].append(out)
        for r,_ in rows:
            if r['component']in assigned:raise ValueError('duplicate source component')
            assigned.add(r['component'])
    windows=[x for x in features if x[0]['part']==54]
    # Physical source locations, not a normal-only selection: front, left, wing, rear, right.
    centers=[np.array(x,float)for x in [(-700,4100,11520),(1600,4600,8740),(5640,4500,17940),(8320,4100,20740),(9460,4100,10420)]]
    bins=[[]for _ in centers]
    for row in windows:
        p=row[1].p.mean((0,1));score=[float(np.linalg.norm((p-c)*[1,.1,1]))for c in centers];bins[int(np.argmin(score))].append(row)
    normals=[-np.array(LENGTH),-np.array(CROSS),-np.array(LENGTH),np.array(CROSS),np.array(LENGTH)]
    for name,rows,n in zip(['left paired','front','west wing','rear paired','right paired'],bins,normals):
        if not rows:raise ValueError('missing physical window '+name)
        add(rows,name+' window outer frame','ring',n,['fine crossbars, paired-panel central divider, frame rear/bevel faces omitted explicitly'])
    # Named exterior eave and gable components retain every original face; no orientation filter.
    exterior={'9000018':'front long eave','9000095':'rear long eave','9000275':'wing west eave','9000501':'wing east eave','9000335':'rear west gable edge','9000365':'rear east gable edge','9000527':'front east gable edge','9000561':'inner east gable edge','9200177':'front west gable edge','9200237':'inner west gable edge'}
    for r,f in features:
        suffix=r['component'].split(':')[-1]
        if r['part']==47 and suffix in exterior:add([(r,f)],exterior[suffix])
        if r['part']==47 and suffix=='9000000':add([(r,f)],'main entrance primary U frame','door',np.array(CROSS),['door surround bevel/relief and rear faces simplified'])
    porch={'28700151':'porch landing and source stepped footprint','28700059':'exterior porch sloping rail','28700061':'outer porch stair newel','28700073':'inner porch stair newel'}
    for r,f in features:
        if r['part']==154 and r['component'].split(':')[-1]in porch:add([(r,f)],porch[r['component'].split(':')[-1]])
    for part in PART_BUDGETS:
        omitted=[x for x in features if x[0]['part']==part and x[0]['component']not in assigned]
        if omitted:add(omitted,'C explicit interior and secondary trim omissions','omit',losses=['interior rafters/posts/stair framing, secondary exterior corner posts, decorative fascia and duplicate window/door trim omitted; source triangles fully enumerated'])
        count=sum(x['target_triangles']for x in parts[str(part)])
        if count>PART_BUDGETS[part]:raise ValueError('part budget '+str(part)+' '+str(count))
        expect={tuple(i)for r,f in features if r['part']==part for i in r['source_ids']}
        got=[tuple(i)for row in parts[str(part)]for i in row['source_ids']]
        if len(got)!=len(set(got))or set(got)!=expect:raise ValueError('full source coverage')
    return dict(schema='re4dc.world-rebuild27.c-shell-groups/1',source_sha256=actual,source_plan_sha256=digest(plan_path),parts=parts,budgets=PART_BUDGETS,counts={p:dict(source=sum(r['source_triangles']for r in rows),target=sum(r['target_triangles']for r in rows))for p,rows in parts.items()},source_only_ps2=True,new_textures=False,acceptance='source geometry/UV/aperture authoring only; appearance and native acceptance pending')


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--plan',type=Path,required=True);ap.add_argument('--tools',type=Path,required=True);ap.add_argument('--dependencies',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    init(a.tools,a.dependencies);result=build(a.source,a.plan);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result['counts']))
if __name__=='__main__':main()
