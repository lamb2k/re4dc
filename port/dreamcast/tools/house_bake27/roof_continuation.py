"""Explicit PS2-only continuation for roof pixels missing the normal-ray bake.

This edits no geometry and never samples another component or material. The
caller must separately establish that source gaps are not genuine apertures.
"""
import bpy
import json
import math
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

def apply(out,source,target,image,exchange):
    src=exchange['roof']['source'];xyz=np.asarray([[[p[0]/1000,-p[2]/1000,p[1]/1000] for p in t['world_mm']] for t in src])
    source_uv=np.asarray([t['uv'] for t in src]);prelight=np.asarray([t['prelight_rgba'] for t in src])
    sn=np.cross(xyz[:,1]-xyz[:,0],xyz[:,2]-xyz[:,0]);sn/=np.maximum(np.linalg.norm(sn,axis=1)[:,None],1e-12)
    basis=np.stack((xyz[:,1]-xyz[:,0],xyz[:,2]-xyz[:,0]),axis=2);inverse=np.linalg.pinv(basis)
    all_bvh=BVHTree.FromPolygons([v.co for v in source.data.vertices],[list(p.vertices) for p in source.data.polygons],all_triangles=True)
    tex=bpy.data.images.get('roof-ps2-source.png');assert tex is not None
    tw,th=tex.size;texels=np.asarray(tex.pixels[:],float).reshape(th,tw,4)
    pixels=np.asarray(image.pixels[:],float).reshape(512,512,4);mask=np.zeros((512,512),float)
    miss=hit=unresolved=0;max_distance=0.;area=0.;by_triangle=[]
    def sample(uv):
        x=(uv[0]%1)*tw-.5;y=((1-uv[1])%1)*th-.5
        x0,y0=math.floor(x),math.floor(y);fx,fy=x-x0,y-y0
        return texels[y0%th,x0%tw]*(1-fx)*(1-fy)+texels[y0%th,(x0+1)%tw]*fx*(1-fy)+texels[(y0+1)%th,x0%tw]*(1-fx)*fy+texels[(y0+1)%th,(x0+1)%tw]*fx*fy
    for poly in target.data.polygons:
        uv=np.asarray([target.data.uv_layers['BAKE_UV'].data[i].uv[:] for i in poly.loop_indices])*512
        lo=np.maximum(np.floor(uv.min(0)).astype(int),0);hi=np.minimum(np.ceil(uv.max(0)).astype(int),511)
        target_xyz=np.asarray([target.data.vertices[target.data.loops[i].vertex_index].co[:] for i in poly.loop_indices]);normal=np.asarray(poly.normal[:])
        eligible=np.where(sn@normal>math.cos(math.radians(25)))[0]
        # Only source surfaces parallel to this target plane, within200mm;
        # tangential extrapolation may cross a source tile seam/omitted board.
        plane_distance=np.abs((xyz[eligible]-target_xyz.mean(0))@normal).min(1)
        eligible=eligible[plane_distance<=.2]
        if len(eligible):
            near_bvh=BVHTree.FromPolygons([Vector(p) for tri in xyz[eligible] for p in tri],[(i*3,i*3+1,i*3+2) for i in range(len(eligible))],all_triangles=True)
        else:near_bvh=None
        inverse_uv=np.linalg.pinv(np.stack((uv[1]-uv[0],uv[2]-uv[0]),axis=1))
        occupied=changed=0;distance_max=0
        for y in range(lo[1],hi[1]+1):
            for x in range(lo[0],hi[0]+1):
                bary=inverse_uv@(np.asarray([x+.5,y+.5])-uv[0]);weights=np.asarray([1-bary.sum(),*bary])
                if weights.min()<-1e-8:continue
                occupied+=1;point=weights@target_xyz
                ray=all_bvh.ray_cast(Vector(point+normal*.25),Vector(-normal),1.)
                if ray[0] is not None:hit+=1;continue
                miss+=1
                near=near_bvh.find_nearest(Vector(point)) if near_bvh else None
                if not near or near[0] is None:unresolved+=1;continue
                index=int(eligible[near[2]]);distance=float(near[3])
                if distance>1.5:unresolved+=1;continue
                # Unbounded source UV extrapolation continues the existing PS2
                # repeating texture. Clamp only source prelight interpolation.
                bary=inverse[index]@(point-xyz[index,0]);uw=np.asarray([1-bary.sum(),*bary]);uv_source=uw@source_uv[index]
                bary_near=inverse[index]@(np.asarray(near[0])-xyz[index,0]);cw=np.clip([1-bary_near.sum(),*bary_near],0,1);cw/=cw.sum()
                color=sample(uv_source);color[:3]*=(cw@prelight[index])[:3];color[3]=1
                pixels[y,x]=color;mask[y,x]=1;changed+=1;max_distance=max(max_distance,distance);distance_max=max(distance_max,distance)
        surface_area=float(np.linalg.norm(np.cross(target_xyz[1]-target_xyz[0],target_xyz[2]-target_xyz[0]))*.5)
        area+=surface_area*changed/max(occupied,1)
        by_triangle.append(dict(target_triangle=poly.index,atlas_occupied_pixels=occupied,continued_pixels=changed,source_max_distance_m=distance_max,source_candidate_triangles=len(eligible)))
    # Unresolved cap orientations stay explicit; never silently replace them
    # with a flat color, another material or an unrelated texture.
    image.pixels.foreach_set(pixels.astype(np.float32).ravel());image.update()
    diagnostic=bpy.data.images.new('ROOF_RAY_MISS_MASK',512,512,alpha=False,float_buffer=False)
    rgba=np.stack((mask,mask,mask,np.ones_like(mask)),axis=2).astype(np.float32);diagnostic.pixels.foreach_set(rgba.ravel());diagnostic.colorspace_settings.name='Non-Color'
    diagnostic.filepath_raw=str(out/'roof-continuation-mask.png');diagnostic.file_format='PNG';diagnostic.save()
    receipt=dict(method='Explicit nearest same-roof-component/material near-coplanar PS2 texture continuation for normal-ray miss pixels only',maximum_source_normal_angle_degrees=25,source_plane_distance_limit_m=.2,source_tangential_distance_limit_m=1.5,ray_hit_pixels=hit,ray_miss_pixels=miss,continued_pixels=int(mask.sum()),unresolved_pixels=unresolved,estimated_affected_surface_area_m2=area,maximum_source_distance_m=max_distance,triangles=by_triangle,geometry_unchanged=True,source_window_door_holes_unchanged=True,appearance_accepted=False,timing_available=False)
    (out/'ROOF-CONTINUATION.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt
