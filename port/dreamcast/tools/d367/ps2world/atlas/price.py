#!/usr/bin/env python3
"""Offline arithmetic and geometry census only; produces no game assets."""
import itertools, math, json, struct
import census
C=census.build(census.parse_args(require_cameras=True))
from convert_tpl import twiddle_16bpp

ps=[p for p in C.parts if p['spatial_batch']]
pairs=[]
for mi in range(204,212):
    keys=sorted({p['key'] for p in ps if p['mesh']==mi})
    for a,b in itertools.combinations(keys,2):
        n=len(C.codebooks[a]|C.codebooks[b])
        pairs.append(dict(mesh=mi,keys=[a,b],existing_vectors=n))

# Inspect one minimal candidate in cell208: part205 (64x32) + flat part208 (32x32).
# Exact decode of accepted VQ words, then aligned periodic gutter blocks. No encoder.
decoded={}
def decode(key):
    if key in decoded:return decoded[key]
    t=C.texs[key]['textures'][0];w,h=t['width'],t['height'];data=C.payloads[key]
    cb=[struct.unpack_from('<4H',data,i*8) for i in range(256)]
    order=twiddle_16bpp(list(range(w*h//4)),w//2,h//2)
    pixels=[0]*(w*h)
    for at,block in enumerate(order):
        x=block%(w//2)*2;y=block//(w//2)*2;v=cb[data[2048+at]]
        pixels[y*w+x]=v[0];pixels[(y+1)*w+x]=v[1]
        pixels[y*w+x+1]=v[2];pixels[(y+1)*w+x+1]=v[3]
    # Independently reconstitute every accepted 2x2 vector in twiddled order.
    for at,block in enumerate(order):
        x=block%(w//2)*2;y=block//(w//2)*2
        assert (pixels[y*w+x],pixels[(y+1)*w+x],pixels[y*w+x+1],pixels[(y+1)*w+x+1])==cb[data[2048+at]]
    decoded[key]=(w,h,pixels);return decoded[key]

picked=[next(p for p in ps if p['part']==i) for i in (205,208)]
rects=[]
for p in picked:
    w,h,px=decode(p['key']);b=p['uv_bounds']
    lo=[math.floor((b[k]*dim-2)/2)*2 for k,dim in enumerate((w,h))]
    hi=[math.ceil((b[k+2]*dim+2)/2)*2 for k,dim in enumerate((w,h))]
    rw,rh=[hi[k]-lo[k] for k in range(2)]
    bits=[];vectors=set()
    for y in range(0,rh,2):
        for x in range(0,rw,2):
            v=tuple(px[((lo[1]+y+dy)%h)*w+(lo[0]+x+dx)%w] for dx,dy in ((0,0),(0,1),(1,0),(1,1)))
            vectors.add(struct.pack('<4H',*v));bits.append(v)
    rects.append(dict(part=p['part'],key=p['key'],source_origin=lo,width=rw,height=rh,
        exact_vq_vectors=len(vectors),vectors=vectors))
width=128;height=64
rects[0]['atlas_origin']=[0,0];rects[1]['atlas_origin']=[rects[0]['width'],0]
assert sum(r['width'] for r in rects)<=width and max(r['height'] for r in rects)<=height
vectors=set().union(*(r.pop('vectors') for r in rects))
candidate=dict(parts=[p['part'] for p in picked],mesh=208,page_size=[width,height],
    payload_bytes=2048+width*height//4,original_payload_bytes=sum(C.texs[p['key']]['resident_bytes'] for p in picked),
    exact_vq_vector_count=len(vectors),gutter_pixels_at_least=2,rects=rects,
    note='Lossless texel/codebook construction feasibility only. UV requantization, loader residency and visible drawlist still require verification.')
candidate['payload_delta_if_both_originals_retired']=candidate['payload_bytes']-candidate['original_payload_bytes']
candidate['payload_delta_if_both_originals_stay']=candidate['payload_bytes']


mapped=[]
for p,r in zip(picked,rects):
    part=C.mesh['parts'][p['part']]
    w,h,_=decode(p['key'])
    refs=set()
    for li in range(part[6],part[6]+part[7]):
        corners,strips=C.F.let_corners(C.mesh,C.mesh['lets'][li])
        refs.update(corners[c] for s in strips for c in s)
    for vi in refs:
        v=C.mesh['verts'][vi]
        uv=[part[8+k]+part[10+k]*v[3+k] for k in range(2)]
        mapped.append([(uv[k]*dim-r['source_origin'][k]+r['atlas_origin'][k])/page for k,dim,page in ((0,w,width),(1,h,height))])
bias=[C.F.f32(min(uv[k] for uv in mapped)) for k in range(2)]
scale=[C.F.f32((max(uv[k] for uv in mapped)-bias[k])/65535) for k in range(2)]
error=[0.,0.]
for uv in mapped:
    for k,page in enumerate((width,height)):
        q=max(0,min(65535,round((uv[k]-bias[k])/scale[k])))
        error[k]=max(error[k],abs((bias[k]+q*scale[k]-uv[k])*page))
candidate['source_uv_bounds']={str(p['part']):p['uv_bounds'] for p in picked}
candidate['source_uv_spans']={str(p['part']):p['uv_span'] for p in picked}
candidate['uv_remap_grid_estimate']={'bias':bias,'scale':scale,'max_error_texels_uv':error,
    'limitation':'Python double decode and mapped arithmetic, float32 grid coefficients. Not exact SH4 arithmetic or raster output.'}

samekey={}
for p in ps:
    key=(p['mesh'],p['key'],p['pass_id'],p['cull'],p['side_flags'][1],*p['part_flags'][1:])
    samekey.setdefault(key,[]).append(p)
samekey_candidates=[]
for key,pp in samekey.items():
    if len(pp)<2:continue
    grids=[C.mesh['parts'][p['part']][8:12] for p in pp]
    samekey_candidates.append({'mesh':key[0],'key':key[1],'parts':[p['part'] for p in pp],
        'source_texture_indices':[p['part_flags'][0] for p in pp],'uv_grids':grids,
        'same_uv_grid':all(g==grids[0] for g in grids),
        'referenced_vertex_sum':sum(p['referenced_vertices'] for p in pp)})

resident_path=census.Path(C.fx['dc/resident.bin'])
resident_blob=resident_path.read_bytes()
keys={tuple(int(x,16) for x in p['key'].split('-')) for p in picked}
records=[struct.unpack_from('<4H2I',resident_blob,i) for i in range(0,len(resident_blob),16)]
candidate['resident_index']={'source':str(resident_path),'sha256':C.sha(resident_blob),
    'matching_records':[r for r in records if tuple(r[4:6]) in keys]}
candidate['nonspatial_world_references']={p['key']:C.texs[p['key']]['nonspatial_parts'] for p in picked}

# Historical camera geometry only. Mirrors world_out and box_class rejection for
# unchanged identity-placed static spatial cells; viewport origin assumed zero.
camfile=C.args.historical_cameras
cams=[[float(x) for x in s.split()] for s in camfile.read_text().splitlines() if s.strip()]
def visible(m,V,P,far):
    lo=m[14:17];hi=m[17:20];c=[(lo[i]+hi[i])*.5 for i in range(3)];h=[(hi[i]-lo[i])*.5 for i in range(3)]
    near=P[6]/(P[5]-1)
    planes=[[P[1],0,P[2]-1,0],[-P[1],0,-P[2]-1,0],[0,-P[3],-P[4]-1,0],[0,P[3],P[4]-1,0],[0,0,-1,-near],[0,0,1,far]]
    for a,b,z,d in planes:
        n=[a*V[i]+b*V[4+i]+z*V[8+i] for i in range(3)]
        d+=a*V[3]+b*V[7]+z*V[11]
        if sum(n[i]*c[i]+abs(n[i])*h[i] for i in range(3))+d < -1:return False
    vc=[sum(V[4*r+i]*c[i] for i in range(3))+V[4*r+3] for r in range(3)]
    vh=[sum(abs(V[4*r+i])*h[i] for i in range(3)) for r in range(3)]
    if -vc[2]+vh[2]<near or -vc[2]-vh[2]>far:return False
    return all(a*vc[0]+b*vc[1]+z*vc[2]+abs(a)*vh[0]+abs(b)*vh[1]+abs(z)*vh[2] >= -0.0001 for a,b,z,d in planes[:4])
draws=[]
for i,cam in enumerate(cams):
    V,P,far=cam[:12],cam[12:19],cam[19]
    seen=[mi for mi in range(204,212) if visible(C.mesh['meshes'][mi],V,P,far)]
    pp=[p['part'] for p in ps if p['mesh'] in seen]
    draws.append(dict(pose=i,cells=seen,spatial_parts=len(pp),ideal_atlas_parts=len(seen),
        ideal_reduction=len(pp)-len(seen),candidate_cell208_admitted=208 in seen))
hist=dict(source=str(camfile),source_sha256=C.sha(camfile.read_bytes()),poses=len(draws),
    limitations='Historical t2exact poses, current spatial32 geometry, Python double arithmetic, zero viewport origin. No dynamic/protected parts, LOD emission, strip groups or exact current118 claim.',
    spatial_parts_min=min(x['spatial_parts'] for x in draws),spatial_parts_max=max(x['spatial_parts'] for x in draws),
    ideal_reduction_min=min(x['ideal_reduction'] for x in draws),ideal_reduction_max=max(x['ideal_reduction'] for x in draws),
    draws=draws)
result=dict(candidate=candidate,samekey_candidates=samekey_candidates,compatible_existing_vq_pairs=[p for p in pairs if p['existing_vectors']<=256],
    samecell_pairs=len(pairs),historical_camera_census=hist)
(C.OUT/'pricing.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
print(json.dumps({**result,'historical_camera_census':{k:v for k,v in hist.items() if k!='draws'}},indent=2,sort_keys=True))
