#!/usr/bin/env python3
"""Named whole-house arena authoring; private source geometry, existing materials.

Architectural operations are explicit by source component and role. This is not
an unconstrained mesh decimator. No runtime, staging or acceptance is provided.
"""
import argparse,collections,copy,json,sys
from pathlib import Path
import world_rebuild27 as w
import world_rebuild27_arena as arena


def setup(dependencies):
    sys.path.insert(0,str(dependencies))
    global np,shapely
    import numpy as np
    import shapely


class Feature:
    def __init__(self,d,part,placement,triangles,name):
        self.d=d;self.part=part;self.placement=placement;self.name=name
        self.mesh=d['placements'][placement][0];self.m=d['meshes'][self.mesh]
        self.source=[tuple(tuple(v)for v in t)for t in triangles]
        self.p=np.asarray(arena.world_triangles(d,self.mesh,placement,self.source),float)
        self.local=np.asarray(self.source,float)
        self.n=np.cross(self.p[:,1]-self.p[:,0],self.p[:,2]-self.p[:,0]);self.area=np.linalg.norm(self.n,axis=1)
        self.n/=np.maximum(self.area[:,None],1e-18)
        a=np.asarray(d['placements'][placement][2:]).reshape(3,4);self.a=a;self.inv=np.linalg.inv(a[:,:3])
        self.samples=[]
    def world(self,q):
        return (np.asarray(q)*self.m[11:14]+self.m[8:11])@self.a[:,:3].T+self.a[:,3]
    def q(self,p):
        q=np.rint(((np.asarray(p)-self.a[:,3])@self.inv.T-self.m[8:11])/self.m[11:14]).astype(int)
        w.require((q>=0).all()and(q<=65535).all(),'authored source grid bounds '+self.name)
        return q
    def sample(self,p,normal):
        allowed=(self.n@normal>.25)&(self.area>1e-7)
        w.require(allowed.any(),'no same-side attribute source '+self.name+' target '+str(normal.tolist())+' source '+str(self.n.tolist()))
        indices=np.flatnonzero(allowed);ts=self.p[allowed];a=ts[:,0];ab=ts[:,1]-a;ac=ts[:,2]-a;ap=p-a
        d00=np.einsum('ij,ij->i',ab,ab);d01=np.einsum('ij,ij->i',ab,ac);d11=np.einsum('ij,ij->i',ac,ac)
        d20=np.einsum('ij,ij->i',ap,ab);d21=np.einsum('ij,ij->i',ap,ac);den=d00*d11-d01*d01
        b=(d11*d20-d01*d21)/np.maximum(den,1e-18);c=(d00*d21-d01*d20)/np.maximum(den,1e-18)
        weights=np.stack((1-b-c,b,c),axis=1);valid=(weights>=-1e-10).all(1)
        points=np.einsum('ij,ijk->ik',weights,ts);dist=np.sum((points-p)**2,axis=1);dist[~valid]=np.inf
        for i,j in ((0,1),(1,2),(2,0)):
            edge=ts[:,j]-ts[:,i];t=np.clip(np.einsum('ij,ij->i',p-ts[:,i],edge)/np.maximum(np.einsum('ij,ij->i',edge,edge),1e-18),0,1)
            candidate=ts[:,i]+edge*t[:,None];dd=np.sum((candidate-p)**2,axis=1);replace=dd<dist
            ew=np.zeros_like(weights);ew[:,i]=1-t;ew[:,j]=t
            weights[replace]=ew[replace];dist[replace]=dd[replace]
        which=int(np.argmin(dist));source=int(indices[which]);weights=weights[which]
        corners=self.local[source];uv=np.rint(weights@corners[:,3:5]).astype(int)
        packed=corners[:,5].astype(int);rgb=np.stack(((packed>>10)&31,(packed>>5)&31,packed&31),axis=1)
        rgb=np.rint(weights@rgb).astype(int);alpha=int(packed[int(np.argmax(weights))])&0x8000
        self.samples.append(dict(source_triangle=source,weights=weights.tolist(),distance_mm=float(np.sqrt(dist[which])),normal_dot=float(self.n[source]@normal)))
        return [int(uv[0]),int(uv[1]),alpha|(int(rgb[0])<<10)|(int(rgb[1])<<5)|int(rgb[2])]
    def encode(self,tri):
        q=self.q(tri);p=self.world(q);normal=np.cross(p[1]-p[0],p[2]-p[0]);length=np.linalg.norm(normal)
        w.require(length>1e-5,'degenerate authored triangle '+self.name);normal/=length
        return tuple(tuple(map(int,v))+tuple(self.sample(point,normal))for v,point in zip(q,p))
    def box(self):
        points=self.p.reshape(-1,3);center=points.mean(0);_,_,axes=np.linalg.svd(points-center,full_matrices=False)
        if np.linalg.det(axes)<0:axes[2]*=-1
        local=(points-center)@axes.T;lo=local.min(0);hi=local.max(0);out=[];clipping=[]
        for axis in range(3):
            other=[i for i in range(3)if i!=axis]
            for side in (0,1):
                quad=[]
                for u,v in ((0,0),(1,0),(1,1),(0,1)):
                    p=lo.copy();p[axis]=(lo,hi)[side][axis];p[other[0]]=(lo,hi)[u][other[0]];p[other[1]]=(lo,hi)[v][other[1]];quad.append(p@axes+center)
                fitted=[]
                for point in quad:
                    raw=np.rint(((point-self.a[:,3])@self.inv.T-self.m[8:11])/self.m[11:14]).astype(int);fitted_point=self.world(np.clip(raw,0,65535));clipping.append(float(np.linalg.norm(fitted_point-point)));fitted.append(fitted_point)
                quad=fitted
                n=np.cross(quad[1]-quad[0],quad[2]-quad[0]);wanted=axes[axis]*(1 if side else -1)
                if n@wanted<0:quad.reverse()
                out.extend(self.encode([quad[0],quad[i],quad[i+1]])for i in (1,2))
        w.require(max(clipping)<100,'door fitted envelope exceeds100mm source bound')
        return out,dict(maximum_source_envelope_clip_mm=max(clipping),operation='explicit six-face source-oriented door volume within original source grid',source_extent_mm=(hi-lo).tolist(),new_triangles=12,detail_tradeoff='plank relief and small ironwork become source-texture detail; owner/placement/material unchanged')
    def surface(self,indices,normal=None,flat=False,tolerance=1.0):
        from shapely.geometry import Polygon
        points=self.p[indices];normal=self.n[indices].sum(0)if normal is None else np.asarray(normal,float)
        w.require(np.linalg.norm(normal)>1e-9,'surface normal');normal/=np.linalg.norm(normal)
        seed=np.eye(3)[np.argmin(np.abs(normal))];u=np.cross(seed,normal);u/=np.linalg.norm(u);v=np.cross(normal,u)
        origin=points.reshape(-1,3).mean(0);xy=np.stack(((points-origin)@u,(points-origin)@v),axis=2)
        polygons=[Polygon(t)for t in xy if abs((t[1,0]-t[0,0])*(t[2,1]-t[0,1])-(t[1,1]-t[0,1])*(t[2,0]-t[0,0]))>1e-6]
        if not polygons:return [],dict(operation='zero projected area',source_triangles=len(indices))
        region=shapely.union_all(polygons);region=shapely.make_valid(region)
        simple=region.simplify(tolerance,preserve_topology=True)
        if not simple.is_valid:simple=region
        components=list(simple.geoms)if hasattr(simple,'geoms')else[simple]
        component_polygons=[p for p in components if p.geom_type=='Polygon'and p.area>1e-5]
        source_xy=xy.reshape(-1,2);source_xyz=points.reshape(-1,3);out=[];quantized_sliver_area=0;emitted_polygons=[]
        depth=float(np.max((points-origin)@normal))if flat else 0
        for polygon in component_polygons:
            triangles=shapely.constrained_delaunay_triangles(polygon)
            for t in triangles.geoms:
                coords=np.asarray(t.exterior.coords)[:3];world=[]
                for coord in coords:
                    distance=np.sum((source_xy-coord)**2,axis=1);near=int(np.argmin(distance))
                    if flat:
                        aa=xy[:,0];bb=xy[:,1]-aa;cc=xy[:,2]-aa;pp=coord-aa
                        determinant=bb[:,0]*cc[:,1]-bb[:,1]*cc[:,0]
                        safe=np.where(np.abs(determinant)>1e-9,determinant,1)
                        wb=(pp[:,0]*cc[:,1]-pp[:,1]*cc[:,0])/safe
                        wc=(bb[:,0]*pp[:,1]-bb[:,1]*pp[:,0])/safe
                        weights=np.stack((1-wb-wc,wb,wc),axis=1)
                        valid=(weights>=-1e-7).all(1)&(np.abs(determinant)>1e-9)
                        if valid.any():
                            candidates=np.einsum('ij,ijk->ik',weights[valid],points[valid]);world.append(candidates[np.argmax(candidates@normal)])
                        else:world.append(source_xyz[near])
                    elif distance[near]<1e-5:world.append(source_xyz[near])
                    else:world.append(origin+coord[0]*u+coord[1]*v)
                if np.cross(world[1]-world[0],world[2]-world[0])@normal<0:world.reverse()
                q=self.q(world);actual=self.world(q)
                if np.linalg.norm(np.cross(actual[1]-actual[0],actual[2]-actual[0]))<=1e-5:
                    quantized_sliver_area+=float(t.area);continue
                if np.cross(actual[1]-actual[0],actual[2]-actual[0])@normal<0:world.reverse();actual=actual[::-1]
                out.append(self.encode(world));projected=np.stack(((actual-origin)@u,(actual-origin)@v),axis=1);emitted_polygons.append(Polygon(projected))
        source_holes=sum(len(p.interiors)for p in(list(region.geoms)if hasattr(region,'geoms')else[region])if p.geom_type=='Polygon')
        target_holes=sum(len(p.interiors)for p in component_polygons)
        w.require(source_holes==target_holes,'source aperture count changed '+self.name)
        actual_region=shapely.union_all(emitted_polygons)
        def significant_holes(shape):
            polys=list(shape.geoms)if hasattr(shape,'geoms')else[shape]
            return sum(Polygon(h).area>=25 for p in polys if p.geom_type=='Polygon'for h in p.interiors)
        w.require(significant_holes(region)==significant_holes(actual_region),'significant aperture changed after quantization '+self.name)
        return out,dict(operation='named projected source-surface contour triangulation',source_triangles=len(indices),target_triangles=len(out),source_holes=source_holes,target_holes=target_holes,flat_front_skin=flat,source_relief_mm=float(np.ptp((points-origin)@normal)),projected_source_area_mm2=float(region.area),projected_target_area_mm2=float(simple.area),projected_symmetric_difference_mm2=float(region.symmetric_difference(simple).area),boundary_tolerance_mm=tolerance,quantized_sliver_area_mm2=quantized_sliver_area,actual_quantized_symmetric_difference_mm2=float(region.symmetric_difference(actual_region).area),significant_source_holes=significant_holes(region),significant_actual_holes=significant_holes(actual_region))
    def front(self):
        horizontal=np.flatnonzero((np.abs(self.n[:,1])<.4)&(self.area>1e-7))
        w.require(len(horizontal)>0,'vertical architectural window front required')
        source=max(horizontal,key=lambda i:float(self.area[self.n@self.n[i]>.8].sum()))
        normal=self.n[source]
        indices=np.flatnonzero(self.n@normal>.8).tolist()
        target,proof=self.surface(indices,normal=normal,flat=False,tolerance=1.0)
        proof.update(operation='explicit vertical window front skin; existing house reveal retains opening depth',source_component_triangles=len(self.source),source_front_triangles=indices,detail_tradeoff='beveled frame back/side faces removed; source front contour/apertures retained')
        return target,proof
    def patches(self,angle=10,depth=35):
        remaining=set(range(len(self.source)));out=[];proof=[]
        while remaining:
            seed=max(remaining,key=lambda i:self.area[i]);normal=self.n[seed]
            compatible=[i for i in remaining if self.n[i]@normal>=np.cos(np.deg2rad(angle))]
            center=self.p[seed].mean(0);chosen=[i for i in compatible if np.max(np.abs((self.p[i]-center)@normal))<=depth]
            if not chosen:chosen=[seed]
            remaining.difference_update(chosen)
            target,record=self.surface(chosen,normal=normal,tolerance=1.0)
            if len(target)>len(chosen):
                target=[self.source[i]for i in chosen];record=dict(operation='source surface retained; contour triangulation would cost more',source_triangles=len(chosen),target_triangles=len(chosen))
            out.extend(target);proof.append(record)
        return out,dict(operation='named face groups; preserve all source orientations/apertures',patches=proof,source_triangles=len(self.source),target_triangles=len(out))


def source_features(d,plan):
    result=[]
    for rec in plan['components']:
        if rec['lod']!=0:continue
        ts=[w.level_triangles(d,d['levels'][li])[ti]for li,ti in rec['source_ids']]
        result.append((rec,Feature(d,rec['part'],rec['placement'],ts,rec['component'])))
    return result


def draft(a):
    setup(a.dependencies)
    w.require(not a.out.exists(),'immutable draft output exists')
    plan=json.loads(a.plan.read_text());d,files,owners,policy=w.load(a.source)
    for n in w.SOURCE_INPUTS:w.require(w.sha(files[n])==plan['inputs']['A']['sha256'][n],'source pin '+n)
    features=source_features(d,plan);rows=[];parts=collections.defaultdict(list)
    for rec,feature in features:
        if rec['part']in(326,328):target,proof=feature.box()
        elif rec['part']==54:target,proof=feature.front()
        elif rec['part']in(56,145,154,158):target,proof=feature.patches()
        elif rec['part']==288 and rec['source_triangles']!=262:target,proof=feature.patches()
        else:target=feature.source;proof=dict(operation='source retained',source_triangles=len(target),target_triangles=len(target))
        parts[rec['part']].extend(target)
        rows.append(dict(component=rec['component'],part=rec['part'],mesh=rec['mesh'],placement=rec['placement'],source_ids=rec['source_ids'],source_triangles=len(feature.source),target_triangles=len(target),proof=proof,attributes=feature.samples))
    a.out.mkdir(parents=True)
    result=dict(schema='re4dc.house-whole-draft/1',source_sha256={n:w.sha(v)for n,v in files.items()},source_plan_sha256=w.sha(a.plan.read_bytes()),tool_sha256=w.sha(Path(__file__).read_bytes()),features=rows,parts={str(k):v for k,v in parts.items()},appearance_accepted=False)
    (a.out/'DRAFT.json').write_text(json.dumps(result,separators=(',',':'))+'\n')
    print(json.dumps(dict(output=str(a.out),per_part={p:len(ts)for p,ts in parts.items()},total=sum(map(len,parts.values()))),indent=2))


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--source',type=Path,required=True);ap.add_argument('--plan',type=Path,required=True);ap.add_argument('--dependencies',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();draft(a)
if __name__=='__main__':main()