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
        self.samples=[];self.attribute_indices=None;self.attribute_domain_normal=None
    def world(self,q):
        return (np.asarray(q)*self.m[11:14]+self.m[8:11])@self.a[:,:3].T+self.a[:,3]
    def q(self,p):
        q=np.rint(((np.asarray(p)-self.a[:,3])@self.inv.T-self.m[8:11])/self.m[11:14]).astype(int)
        w.require((q>=0).all()and(q<=65535).all(),'authored source grid bounds '+self.name)
        return q
    def sample(self,p,normal):
        allowed=(self.n@normal>.25)&(self.area>1e-7)
        if self.attribute_indices is not None:allowed&=np.isin(np.arange(len(self.source)),self.attribute_indices)
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
        return tuple(tuple(map(int,v))+tuple(self.sample(point,normal if self.attribute_domain_normal is None else self.attribute_domain_normal))for v,point in zip(q,p))
    def audit_target(self,target,predecessor=None):
        """Bind every witness to the final emitted corner, never rejected proposals."""
        self.samples=[];result=[]
        exact={tuple(t[k:]+t[:k]):(i,k)for i,t in enumerate(self.source)for k in range(3)}
        for ti,t in enumerate(target):
            t=tuple(tuple(v)for v in t)
            if predecessor is not None:
                w.require(t==tuple(tuple(v)for v in predecessor[ti]),'pinned predecessor corner identity')
                result.extend(dict(target_triangle=ti,target_corner=ci,kind='reviewed-R4-predecessor-exact',predecessor_triangle=ti,predecessor_corner=ci)for ci in range(3));continue
            if t in exact:
                source,shift=exact[t]
                for ci in range(3):
                    weights=[0.,0.,0.];weights[(ci+shift)%3]=1.
                    result.append(dict(target_triangle=ti,target_corner=ci,kind='exact-source',source_triangle=source,weights=weights,distance_mm=0.,normal_dot=1.))
                continue
            points=self.world(np.array(t)[:,:3]);normal=np.cross(points[1]-points[0],points[2]-points[0]);normal/=np.linalg.norm(normal)
            for ci,(corner,point)in enumerate(zip(t,points)):
                domain=normal if self.attribute_domain_normal is None else self.attribute_domain_normal
                attribute=self.sample(point,domain)
                w.require(tuple(attribute)==tuple(corner[3:]),'final attribute witness mismatch '+self.name+' '+str((ti,ci)))
                result.append(dict(self.samples[-1],target_triangle=ti,target_corner=ci,kind='same-side-source-barycentric'if self.attribute_domain_normal is None else'source-oriented-sheet-barycentric',sampling_domain_normal=domain.tolist(),target_source_normal_dot=float(self.n[self.samples[-1]['source_triangle']]@normal)))
        w.require(len(result)==3*len(target),'final corner witness cardinality')
        return result

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

    def roof_sheet(self,underside=False):
        from shapely.geometry import Polygon,LineString
        from shapely.ops import split
        length=np.array([.99417922945167,0,-.10773884966382]);cross=np.array([.10773884966382,0,.99417922945167])
        indices=np.flatnonzero(((self.n[:,1]<-.25)if underside else(self.n[:,1]>.25))&(self.area>1e-7));self.attribute_indices=indices;self.attribute_domain_normal=np.array([0.,-1. if underside else 1.,0.])
        pts=self.p[indices];xy=np.stack((pts@length,pts@cross),axis=2)
        region=shapely.set_precision(shapely.union_all([Polygon(t)for t in xy]),.1)
        polys=list(region.geoms)if hasattr(region,'geoms')else[region];simplified=[]
        for polygon in polys:
            if polygon.geom_type!='Polygon':continue
            ring=[np.array(x)for x in polygon.exterior.coords[:-1]]
            while len(ring)>3:
                changed=False
                for i,b in enumerate(ring):
                    if len(self.source)==139 and 3100<=b[0]<=5750 and 17400<=b[1]<=19500:continue
                    a,c=ring[i-1],ring[(i+1)%len(ring)];edge=c-a;t=np.clip((b-a)@edge/max(edge@edge,1e-9),0,1)
                    if np.linalg.norm(b-(a+t*edge))<=40:
                        proposal=ring[:i]+ring[i+1:];candidate=Polygon(proposal,[h.coords for h in polygon.interiors])
                        if candidate.is_valid:ring=proposal;changed=True;break
                if not changed:break
            simplified.append(Polygon(ring,[h.coords for h in polygon.interiors]))
        simple=shapely.union_all(simplified);pieces=simplified
        cuts=[]
        if len(self.source)==139:
            cuts=[LineString([(u,-100000),(u,100000)])for u in(5695,5984,6275)]+[LineString([(-100000,v),(100000,v)])for v in(16906,)]
        if underside:
            points=pts.reshape(-1,3);peaks=points[points[:,1]>=points[:,1].max()-100];cross_axis=1 if np.ptp(points@length)>np.ptp(points@cross)else 0
            position=float(np.median(peaks@(cross if cross_axis==1 else length)))
            cuts=[LineString([(-100000,position),(100000,position)])]if cross_axis==1 else[LineString([(position,-100000),(position,100000)])]
        for cut in cuts:
            pieces=[piece for p in pieces for piece in split(p,cut).geoms if piece.geom_type=='Polygon']
        def lift(coord):
            aa=xy[:,0];bb=xy[:,1]-aa;cc=xy[:,2]-aa;pp=coord-aa;den=bb[:,0]*cc[:,1]-bb[:,1]*cc[:,0];safe=np.where(abs(den)>1e-9,den,1)
            b=(pp[:,0]*cc[:,1]-pp[:,1]*cc[:,0])/safe;c=(bb[:,0]*pp[:,1]-bb[:,1]*pp[:,0])/safe;weights=np.stack((1-b-c,b,c),axis=1)
            valid=(weights>=-1e-7).all(1)&(abs(den)>1e-9)
            if valid.any():height=float(np.max(np.einsum('ij,ij->i',weights[valid],pts[valid,:,1])))
            else:
                best=None
                for i,j in((0,1),(1,2),(2,0)):
                    edge=xy[:,j]-xy[:,i];t=np.clip(np.einsum('ij,ij->i',coord-xy[:,i],edge)/np.maximum(np.einsum('ij,ij->i',edge,edge),1e-9),0,1)
                    distance=np.sum((xy[:,i]+edge*t[:,None]-coord)**2,axis=1);k=int(np.argmin(distance));value=float(pts[k,i,1]*(1-t[k])+pts[k,j,1]*t[k])
                    if best is None or distance[k]<best[0]:best=(distance[k],value)
                height=best[1]
            return coord[0]*length+coord[1]*cross+np.array([0,height,0])
        out=[];actual_polys=[]
        for piece in pieces:
            for triangle in shapely.constrained_delaunay_triangles(piece).geoms:
                world=[lift(np.array(x))for x in list(triangle.exterior.coords)[:3]];q=self.q(world);actual=self.world(q)
                if np.linalg.norm(np.cross(actual[1]-actual[0],actual[2]-actual[0]))<1e-5:continue
                if(np.cross(actual[1]-actual[0],actual[2]-actual[0])[1]<0)!=underside:world.reverse();actual=actual[::-1]
                out.append(self.encode(world));actual_polys.append(Polygon(np.stack((actual@length,actual@cross),axis=1)))
        actual_region=shapely.union_all(actual_polys)
        return out,dict(operation='authored broad source roof/ceiling sheet with genuine source cutout contours',underside=underside,attribute_policy='nearest original upper/downward source sheet; coarse-face normal does not select distant fine-fold donor; actual coarse/source dots recorded separately',source_triangles=len(self.source),target_triangles=len(out),source_surface_triangles=indices.tolist(),boundary_tolerance_mm=40,ridge_cross_stations_mm=[5695,5984,6275]if len(self.source)==139 else[],length_stations_mm=[16906]if len(self.source)==139 else[],source_footprint_wkt=region.wkt,target_footprint_wkt=actual_region.wkt,projected_symmetric_difference_mm2=float(region.symmetric_difference(actual_region).area),projected_hausdorff_mm=float(region.hausdorff_distance(actual_region)),detail_tradeoff='source tile corrugations become broad 3D sheets; existing PS2 pixel detail reused')
    def ribbon(self,indices,normal):
        from shapely.geometry import Polygon,LineString
        pts=self.p[indices];normal=np.asarray(normal,float);normal/=np.linalg.norm(normal)
        centered=pts.reshape(-1,3)-pts.reshape(-1,3).mean(0);along=np.linalg.svd(centered,full_matrices=False)[2][0];u=along-(along@normal)*normal;u/=np.linalg.norm(u);v=np.cross(normal,u);origin=pts.reshape(-1,3).mean(0)
        xy=np.stack(((pts-origin)@u,(pts-origin)@v),axis=2);region=shapely.set_precision(shapely.union_all([Polygon(t)for t in xy if Polygon(t).area>1e-6]),.1)
        polygons=[p for p in(list(region.geoms)if hasattr(region,'geoms')else[region])if p.geom_type=='Polygon'and p.area>=1]
        if any(p.interiors for p in polygons):
            target,proof=self.surface(indices,normal=normal,tolerance=1.0);proof['ribbon_refused_source_apertures_retained']=True;return target,proof
        coords=np.concatenate([np.asarray(p.exterior.coords)for p in polygons]);lo,bot,hi,top=region.bounds
        stations=list(np.linspace(lo,hi,5))
        for height in(bot,top):
            near=coords[abs(coords[:,1]-height)<=10,0]
            if len(near):stations.extend((float(near.min()),float(near.max())))
        stations=sorted(set(round(x,5)for x in stations));profile=[];out=[];actual_polys=[]
        def lift(coord):
            best=None
            for i,j in((0,1),(1,2),(2,0)):
                edge=xy[:,j]-xy[:,i];t=np.clip(np.einsum('ij,ij->i',coord-xy[:,i],edge)/np.maximum(np.einsum('ij,ij->i',edge,edge),1e-9),0,1);dist=np.sum((xy[:,i]+edge*t[:,None]-coord)**2,axis=1);k=int(np.argmin(dist));p=pts[k,i]*(1-t[k])+pts[k,j]*t[k]
                if best is None or dist[k]<best[0]:best=(dist[k],p)
            return best[1]
        for station in stations:
            x=min(hi-1e-4,max(lo+1e-4,station));cut=region.intersection(LineString([(x,bot-100000),(x,top+100000)]))
            if cut.is_empty:
                closest=coords[np.argmin(abs(coords[:,0]-x)),0];cut=region.intersection(LineString([(closest,bot-100000),(closest,top+100000)]))
            if cut.is_empty:continue
            _,low,_,high=cut.bounds;profile.append((lift(np.array([x,low])),lift(np.array([x,high]))))
        for (a,b),(c,d)in zip(profile,profile[1:]):
            for triangle in([a,c,d],[a,d,b]):
                q=self.q(triangle);actual=self.world(q)
                if np.linalg.norm(np.cross(actual[1]-actual[0],actual[2]-actual[0]))<1e-5:continue
                if np.cross(actual[1]-actual[0],actual[2]-actual[0])@normal<0:triangle=list(reversed(triangle));actual=actual[::-1]
                out.append(self.encode(triangle));actual_polys.append(Polygon(np.stack(((actual-origin)@u,(actual-origin)@v),axis=1)))
        if len(out)>=len(indices):return [self.source[i]for i in indices],dict(operation='source fringe retained; broad ribbon would not save',source_triangles=len(indices),target_triangles=len(indices))
        actual=shapely.union_all(actual_polys)
        return out,dict(operation='authored continuous source roof-fringe ribbon profiles',source_triangles=len(indices),target_triangles=len(out),profile_stations=stations,source_fragment_polygons=len(polygons),source_apertures=0,projected_hausdorff_mm=float(region.hausdorff_distance(actual)),projected_symmetric_difference_mm2=float(region.symmetric_difference(actual).area),source_contour_wkt=region.wkt,actual_contour_wkt=actual.wkt,detail_tradeoff='fine separated fringe facets approximated by continuous profile ribbons; existing PS2 alpha cutout texture unchanged; not an all-source-silhouette PASS')
    def architecture(self,roof_up=False,tolerance=1.0,ribbons=False,ends_only=False):
        length=np.array([.99417922945167,0,-.10773884966382]);cross=np.array([.10773884966382,0,.99417922945167]);up=np.array([0,1,0])
        width=self.p.reshape(-1,3)@length;depth=self.p.reshape(-1,3)@cross
        ridge=length if np.ptp(width)>np.ptp(depth)else cross;side=cross if ridge is length else length
        y=up if roof_up else -up
        directions=[ridge,-ridge,(side+y)/np.sqrt(2),(-side+y)/np.sqrt(2),y,-y]
        assignment=np.argmax(self.n@np.array(directions).T,axis=1);out=[];proof=[]
        for direction,normal in enumerate(directions):
            if ends_only and direction not in(0,1):continue
            indices=np.flatnonzero(assignment==direction).tolist()
            if not indices:continue
            # Separate source planes more than500mm apart; no merging of buildings or material parts.
            ordered=sorted(indices,key=lambda i:float(self.p[i].mean(0)@normal));groups=[[]];previous=None
            for i in ordered:
                offset=float(self.p[i].mean(0)@normal)
                if previous is not None and offset-previous>500:groups.append([])
                groups[-1].append(i);previous=offset
            for group in groups:
                target,record=self.ribbon(group,normal)if ribbons else self.surface(group,normal=normal,tolerance=tolerance)
                if not target:target=[self.source[i]for i in group];record['zero_projection_source_retained']=True
                record.update(architectural_face=direction,source_triangle_indices=group)
                out.extend(target);proof.append(record)
        return out,dict(operation='explicit gable ends and two architectural roof skins',patches=proof,source_triangles=len(self.source),target_triangles=len(out),roof_up=roof_up)
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
    w.require(w.sha(a.r4.read_bytes())==plan['exchange']['sha256'],'reviewed R4 exchange file pin')
    r4=json.loads(a.r4.read_text());w.require(r4['candidate_sha256']==plan['inputs']['B']['sha256']['ps2-world.re4mesh'],'reviewed R4 core identity')
    for rec,feature in features:
        if rec['part']==160 or(rec['part']==288 and rec['source_triangles']==262):
            role='wall'if rec['part']==160 else'roof';target=[tuple(tuple(v)for v in t['corners'])for t in r4[role]['target']];proof=dict(operation='reviewed R4 upper-prelight-corrected core reused',source_triangles=len(feature.source),target_triangles=len(target))
        elif rec['part']in(326,328):target,proof=feature.box()
        elif rec['part']==54:target,proof=feature.front()
        elif rec['part']==145:target,proof=feature.architecture(tolerance=40,ribbons=True)
        elif rec['part']==56 and len(feature.source)>2:
            target,proof=feature.roof_sheet(underside=True);target.extend(t for i,t in enumerate(feature.source)if feature.n[i,1]>=-.25);proof['other_source_orientations_retained']=int((feature.n[:,1]>=-.25).sum());proof['target_triangles']=len(target)
        elif rec['part']==154 and len(feature.source)==73:target,proof=feature.architecture(ribbons=True)
        elif rec['part']in(47,154,158):target,proof=feature.patches()
        elif rec['part']==288 and rec['source_triangles']in(139,26):
            target,proof=feature.roof_sheet()
            extras=np.flatnonzero(feature.n[:,1]<=.25).tolist()
            target.extend(feature.source[i]for i in extras)
            proof.update(other_orientation_source_indices_retained=extras,other_orientation_triangles_retained=len(extras),target_triangles=len(target),cutout_preservation='approximate source boundary, maximum40mm simplification; quantified decoded footprint differences')
        else:target=feature.source;proof=dict(operation='source retained',source_triangles=len(target),target_triangles=len(target))
        predecessor=target if proof['operation']=='reviewed R4 upper-prelight-corrected core reused'else None
        attributes=feature.audit_target(target,predecessor)
        target_first=len(parts[rec['part']]);parts[rec['part']].extend(target)
        rows.append(dict(component=rec['component'],part=rec['part'],mesh=rec['mesh'],placement=rec['placement'],source_ids=rec['source_ids'],source_triangles=len(feature.source),target_triangles=len(target),proof=proof,target_first=target_first,attributes=attributes))
    a.out.mkdir(parents=True)
    result=dict(schema='re4dc.house-whole-draft/1',source_sha256={n:w.sha(v)for n,v in files.items()},source_plan_sha256=w.sha(a.plan.read_bytes()),tool_sha256=w.sha(Path(__file__).read_bytes()),features=rows,parts={str(k):v for k,v in parts.items()},appearance_accepted=False)
    (a.out/'DRAFT.json').write_text(json.dumps(result,separators=(',',':'))+'\n')
    print(json.dumps(dict(output=str(a.out),per_part={p:len(ts)for p,ts in parts.items()},total=sum(map(len,parts.values()))),indent=2))
    if a.emit:emit(a,d,files,plan,result,features)


def emit(a,d,files,plan,draft_doc,features):
    """Three standard-format arena packages, no runtime or archive mutation."""
    import struct,subprocess,zlib,shutil
    w.require(not a.emit.exists(),'immutable final arena output exists')
    cblob=a.c_groups.read_bytes();cgroups=json.loads(cblob)
    w.require(w.sha(cblob)=='cd139d8e733cd40673b94f6f57ce8f484cdeb8bd5dcc99a6ab721b7b47a73037','reviewed C groups pin')
    w.require(cgroups['source_sha256']==draft_doc['source_sha256']and cgroups['source_plan_sha256']==draft_doc['source_plan_sha256'],'C input pins')
    selected=collections.defaultdict(set)
    for r in plan['components']:
        for li,ti in r['source_ids']:selected[li].add(ti)
    base={li:[t for ti,t in enumerate(w.level_triangles(d,lv))if ti in selected[li]]for li,lv in enumerate(d['levels'])}
    expected={'A':base,'B':{li:[]for li in base},'C':{li:[]for li in base}}
    # Original selected higher levels for B; C replaces frame/trim higher levels below.
    level_lod={c[6]+k:k for c in d['clusters']for k in range(c[7])}
    for arm in('B','C'):
        for li in base:
            if level_lod[li]>0:expected[arm][li]=list(base[li])
    source_rows={r['component']:r for r in draft_doc['features']};c_dispositions=[]
    for rec,feature in features:
        row=source_rows[rec['component']];first=min(li for li,ti in rec['source_ids']);part=rec['part']
        target=draft_doc['parts'][str(part)][row['target_first']:row['target_first']+row['target_triangles']]
        expected['B'][first].extend(target)
        if part in(47,54,154):continue
        if part in(9,10)and a.omit_c_liners:
            ct=[];proof={'operation':'sparse cost-floor: interior black liner/shadow surfaces omitted; exterior plaster mass retained','source_triangles':len(feature.source),'target_triangles':0}
        elif part==145:
            feature.attribute_indices=None;ct,proof=feature.architecture(tolerance=40,ribbons=True,ends_only=True)
            proof['detail_tradeoff']='gable/end source profiles retained; underside fine alpha fringe omitted, broad roof/ceiling retained separately'
            proof['attributes']=feature.audit_target(ct)
        else:ct=target;proof={'operation':'same target as B','target_triangles':len(ct)}
        expected['C'][first].extend(ct)
        c_dispositions.append(dict(component=rec['component'],part=part,source_ids=rec['source_ids'],target_first_level=first,target_triangles=len(ct),proof=proof))
    # Proxy groups cover every original selected component/triangle of these three parts.
    for part,records in cgroups['parts'].items():
        wanted=collections.Counter(tuple(i)for r in plan['components']if r['part']==int(part)and r['lod']==0 for i in r['source_ids'])
        actual=collections.Counter(tuple(i)for r in records for i in r['source_ids'])
        w.require(actual==wanted,'C complete source group coverage '+part)
        for rec in records:
            first=min(li for li,ti in rec['source_ids']);expected['C'][first].extend(rec['target'])
        # At every source higher ordinal, reuse the bounded sparse group in a single existing cluster.
        fc,cc=d['part_lods'][int(part)];alltarget=[t for r in records for t in r['target']]
        for ordinal in range(1,max(d['clusters'][ci][7]for ci in range(fc,fc+cc))):
            candidates=[d['clusters'][ci][6]+ordinal for ci in range(fc,fc+cc)if ordinal<d['clusters'][ci][7]]
            for li in candidates:expected['C'][li]=[]
            expected['C'][min(candidates)]=alltarget
    class Levels(dict):
        def __init__(self,values):
            self.cursor=collections.Counter()
            super().__init__((ci,[values[c[6]+i]for i in range(c[7])if d['levels'][c[6]+i][1]])for ci,c in enumerate(d['clusters']))
        def __getitem__(self,ci):
            k=self.cursor[ci];self.cursor[ci]+=1;return dict.__getitem__(self,ci)[k]
    expected={arm:{li:[tuple(tuple(v)for v in t)for t in ts]for li,ts in levels.items()}for arm,levels in expected.items()}
    docs={}
    for arm in('B','C'):
        working=copy.deepcopy(d);working.pop('index_layout',None);working['schema']=w.codec.SCHEMA
        docs[arm]=w.install_shells(working,Levels(expected[arm]))
        # Enclose ALL levels, including merged target skins whose source component boxes were smaller.
        for ci,c in enumerate(docs[arm]['clusters']):
            verts=[v for li in range(c[6],c[6]+c[7])for t in expected[arm][li]for v in t]
            if verts:c[:6]=[min(v[k]for v in verts)for k in range(3)]+[max(v[k]for v in verts)for k in range(3)]
    texrows=json.loads((a.plan.parent/'TEXTURE-UNION.json').read_text())
    keys={tuple(d['materials'][r['part']][:4])for r in plan['components']}
    texrows=[r for r in texrows if tuple(r['key'])in keys];w.require(len(keys)==len(texrows)==17,'exact17 original residents, no baked maps')
    placements=sorted(set(r['placement']for r in plan['components']));w.require(len(placements)==19,'house placement count')
    a.emit.mkdir(parents=True);rows=[];receipts=[]
    for index,arm in enumerate(('A','B','C')):
        out=a.emit/'native/r101'/('arena'+str(index));out.mkdir(parents=True)
        if arm=='A':
            src=a.plan.parent/'native/r101/arena0'
            for n in w.SOURCE_INPUTS+('ps2-world.r4sg',):shutil.copyfile(src/n,out/n)
        else:
            (out/'ps2-world.raw.re4mesh').write_bytes(w.codec.serialize_mesh(docs[arm]))
            for n in w.UNCHANGED_COMPANIONS:(out/n).write_bytes(files[n])
            run=subprocess.run([sys.executable,str(Path(__file__).parent/'ps2_strip_groups.py'),str(out/'ps2-world.raw.re4mesh'),str(out/'ps2-world.r4pw'),str(out/'ps2-world.re4mesh'),str(out/'ps2-world.r4sg'),'--groups','4','--report',str(out/'strip-groups.json')],capture_output=True,text=True,check=True)
            (out/'strip-groups.log').write_text(run.stdout+run.stderr)
            sg=bytearray((out/'ps2-world.r4sg').read_bytes());struct.pack_into('<I',sg,24,0x68100b21);(out/'ps2-world.r4sg').write_bytes(sg)
        mesh=(out/'ps2-world.re4mesh').read_bytes();final=w.codec.decode(mesh,files['ps2-world.r4pw']);crc=struct.unpack_from('<I',mesh,12)[0]
        w.require(zlib.crc32(mesh[80:])&0xffffffff==crc,'actual bodyCRC '+arm)
        for n in w.UNCHANGED_COMPANIONS:w.require((out/n).read_bytes()==files[n],'all companion readback '+arm+n)
        for key in('meshes','placements','materials','part_lods'):w.require(final[key]==d[key],'immutable identity '+arm+key)
        w.require([c[6:]for c in final['clusters']]==[c[6:]for c in d['clusters']],'cluster identity '+arm)
        for li,level in enumerate(final['levels']):w.require(w.canonical(w.level_triangles(final,level))==w.canonical([tuple(tuple(v)for v in t)for t in expected[arm][li]]),'all-level emitted corners '+arm+str(li))
        for ci,c in enumerate(final['clusters']):
            for li in range(c[6],c[6]+c[7]):
                for ji in range(final['levels'][li][0],sum(final['levels'][li][:2])):
                    j=final['meshlets'][ji]
                    for vi in w.codec.local_vertices(final,ji):
                        v=final['vertices'][vi]
                        w.require(all(j[5+k]<=v[k]<=j[8+k]and c[k]<=v[k]<=c[k+3]for k in range(3)),'actual meshlet/cluster bounds '+arm+str((ci,ji)))
        counts=[sum(len(expected[arm][c[6]+k])for c in d['clusters']if k<c[7])for k in range(max(c[7]for c in d['clusters']))]
        receipt=dict(arm=index+1,arm_label=arm,scope=('original','rebuilt','sparse')[index],candidate_sha256=w.sha(mesh),candidate_crc=crc,candidate_crc_hex='%08x'%crc,candidate_bytes=len(mesh),l0_triangles=counts[0],per_lod_triangles=counts,vertices=len(final['vertices']),meshlets=len(final['meshlets']),stored_triangle_corners=3*sum(counts),level_counts=[len(expected[arm][li])for li in base],all707_levels_exact=True,actual_meshlet_cluster_bounds_checked=True,source_identity_exact=True,companions_sha256={n:w.sha((out/n).read_bytes())for n in w.UNCHANGED_COMPANIONS},appearance_accepted=False,timing_available=False)
        (out/'RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n');receipts.append(receipt)
        rows.append([0x101,len(files['ps2-world.r4pw']),len(d['placements']),len(d['parts']),len(d['meshes']),struct.unpack_from('<I',files['ps2-world.r4pw'],20)[0],w.fnv(files['ps2-world.r4pw']),crc,len(mesh),0x68100b21])
    cert='// PRIVATE three-arm source-policy admission.\nstatic constexpr Certificate rebuild27_certificates[]={\n'+''.join('{'+','.join('0x%08xU'%v for v in row)+'},\n'for row in rows)+'};\n'
    (a.emit/'world_rebuild27_certificates.inc').write_text(cert)
    header='// PRIVATE; include inside re4dc::house_arena27.\nconstexpr unsigned placements[]={'+','.join(str(v)+'U'for v in placements)+'};\n'
    header+='constexpr unsigned textures[][4]={\n'+''.join('{'+','.join('0x%08xU'%v for v in r['key'])+'},\n'for r in texrows)+'};\n'
    header+='constexpr unsigned mesh_identity[3][2]={\n'+''.join('{0x%08xU,%dU},\n'%(r['candidate_crc'],r['candidate_bytes'])for r in receipts)+'};\n'
    (a.emit/'world_rebuild27_arena.inc').write_text(header)
    (a.emit/'TEXTURE-UNION.json').write_text(json.dumps(texrows,indent=2)+'\n')
    (a.emit/'SOURCE-FEATURES.json').write_text(json.dumps(draft_doc,separators=(',',':'))+'\n')
    (a.emit/'C-DISPOSITIONS.json').write_text(json.dumps(dict(common=c_dispositions,proxy_exchange_sha256=w.sha(cblob),proxy_groups=cgroups),separators=(',',':'))+'\n')
    (a.emit/'GENERATOR.py').write_bytes(Path(__file__).read_bytes())
    (a.emit/'arena-plan.json').write_bytes(a.plan.read_bytes())
    receipt=dict(schema='re4dc.house-arena-whole/2',scope=['original','rebuilt','sparse'],arms=receipts,source_sha256=draft_doc['source_sha256'],plan_sha256=w.sha(a.plan.read_bytes()),tool_sha256=w.sha(Path(__file__).read_bytes()),c_groups_sha256=w.sha(cblob),placements=placements,union_texture_keys=17,new_textures=0,baked_maps=0,original_assets_unchanged=True,geometry_only=True,budget_target={'B':[900,1500],'C':[300,600]},budget_met=False,budget_target_miss_reason='retained roof underside orientation strips and interior black liners; coverage takes priority over target',B_budget=[900,1500],C_budget=[300,600],B_budget_met=900<=receipts[1]['l0_triangles']<=1500,C_budget_met=300<=receipts[2]['l0_triangles']<=600,qualification='source/host-only; neither appearance nor timing acceptance')
    (a.emit/'RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n')
    (a.emit/'RECIPE.txt').write_text('PRIVATE original/rebuilt/sparse whole-house arena; existing R4IM/R4PW/R4SG.\nCommand: '+json.dumps(sys.argv)+'\nB preserves source roof139 ten orientation extras. Roof cutout boundary is approximate <=40mm, not exact.\nC loses fine fringe, selected interior liner surfaces if requested, and proxy-listed framing/bevels/interior stair details.\n17 original PS2 resident keys shared equally; no new maps, texture pruning, runtime, staging or performance claim.\n')
    (a.emit/'SHA256SUMS').write_text(''.join(w.sha(p.read_bytes())+'  '+p.relative_to(a.emit).as_posix()+'\n'for p in sorted(a.emit.rglob('*'))if p.is_file()))
    print(json.dumps(dict(final=str(a.emit),arms=receipts),indent=2))


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--source',type=Path,required=True);ap.add_argument('--plan',type=Path,required=True);ap.add_argument('--dependencies',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--r4',type=Path,required=True)
    ap.add_argument('--emit',type=Path);ap.add_argument('--c-groups',type=Path);ap.add_argument('--omit-c-liners',action='store_true')
    a=ap.parse_args();draft(a)
if __name__=='__main__':main()