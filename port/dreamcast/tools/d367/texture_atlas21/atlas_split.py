#!/usr/bin/env python3
"""Isolate one proven square Leon tile, retaining source geometry and base pixels.

Outputs new private resources and ordered FE/v3 run bindings. Existing atlases,
runtime sources, recipes and animation data are never changed. Adoption needs a
separately guarded material/run integration and target sampling/resource checks.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import struct
import sys
import zlib

TOOLS=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(TOOLS))
sys.path.insert(0,str(TOOLS/'d367'/'ps2leon'))
import mipmap_vq as mip
import convert_tpl as tpl
import hands_pack

TARGET='SourceTex_878b23c0-e7038833'
PACK_SHA='18fcee11491f2c1f212863d6d6b572b3997f691b2e990217e1c2518f134021ef'
SOURCE_SEAL='487ad3c970d2443db2b15d489e61f2cff7e1ef1377e44b579b6917aa2735b31b'
KEYS={'standard':'ec255e66-76812316','pl08':'7506e95f-68cf2211'}

def sha(blob):return hashlib.sha256(blob).hexdigest()
def dump(path,row):path.write_text(json.dumps(row,indent=2)+'\n',newline='\n')
def r32(n):return (n+31)&~31

def read_fe(blob):
    """Bounded FE/v3 level0 decoder; preserve emitted rotation and draw order."""
    if len(blob)<32:raise ValueError('short FE stream')
    magic,version,flags,levels,nm,color,rec4,idx4,lod4,bake4=struct.unpack_from('<BBBBHHHHHH',blob)
    if (magic,version,levels,lod4,bake4)!=(254,3,0,0,0) or flags&0x83:
        raise ValueError('candidate requires opaque, unbaked, level0 FE/v3')
    if not 32+nm*8<=rec4*4<=idx4*4<=len(blob):raise ValueError('FE table bounds')
    out=[]
    for m in range(nm):
        count,first,off=struct.unpack_from('<IHH',blob,32+m*8)
        nv,ni,nt=count&255,(count>>8)&4095,count>>20
        if not 3<=nv<=128 or ni>1024 or rec4*4+(first+nv)*6>idx4*4 or idx4*4+off+ni>len(blob):
            raise ValueError('FE meshlet bounds')
        records=[struct.unpack_from('<3H',blob,rec4*4+(first+k)*6) for k in range(nv)]
        run=[];before=len(out)
        for index in blob[idx4*4+off:idx4*4+off+ni]:
            if index&127>=nv:raise ValueError('FE record reference')
            run.append(index&127)
            if index&128:
                if len(run)<3:raise ValueError('FE short strip')
                for k in range(len(run)-2):
                    at=(k,k+1,k+2) if not k&1 else (k+1,k,k+2)
                    out.append(tuple(records[run[a]] for a in at))
                run=[]
        if run or len(out)-before!=nt:raise ValueError('FE triangle count')
    return out

def make_fe(triangles,uv,reference):
    """Exact ordered triangle strips; source bounds/colour remain conservative."""
    meshlets=[];records=[];index=[];lookup={}
    def finish():
        nonlocal records,index,lookup
        if index:meshlets.append((records,index))
        records=[];index=[];lookup={}
    for triangle in triangles:
        needed=sum(c not in lookup for c in set(triangle))
        if len(records)+needed>128 or len(index)+3>1024:finish()
        for k,corner in enumerate(triangle):
            if corner not in lookup:lookup[corner]=len(records);records.append(corner)
            index.append(lookup[corner]|(128 if k==2 else 0))
    finish()
    header=bytearray(reference[:32]);excess=0
    for pair in struct.iter_unpack('<2H',uv):
        for value in pair:
            if value:
                significance=value.bit_length()-((value&-value).bit_length()-1)
                excess=max(excess,significance-8)
    header[2]=min(excess,31)<<2
    rec_at=(32+8*len(meshlets)+3)&~3
    rec_data=b''.join(struct.pack('<3H',*c) for recs,_ in meshlets for c in recs)
    idx_at=(rec_at+len(rec_data)+3)&~3
    struct.pack_into('<H',header,4,len(meshlets))
    struct.pack_into('<4H',header,8,rec_at//4,idx_at//4,0,0)
    table=bytearray();first=offset=0
    for recs,indices in meshlets:
        table+=struct.pack('<IHH',len(recs)|(len(indices)<<8)|((len(indices)//3)<<20),first,offset)
        first+=len(recs);offset+=len(indices)
    blob=bytes(header)+table
    blob+=bytes(rec_at-len(blob))+rec_data
    blob+=bytes(idx_at-len(blob))+bytes(i for _,indices in meshlets for i in indices)
    blob+=bytes(r32(len(blob))-len(blob))
    if read_fe(blob)!=triangles:raise ValueError('ordered FE reconstruction changed triangles')
    return blob

def crop_vq(blob,rect):
    """Morton sub-plane crop, no pixel encoding, padding, stretching or book edit."""
    source=mip.read_native_vq(blob)
    x,y,side=rect
    if source.size!=512 or source.mipmapped or side<8 or side&(side-1) or x%2 or y%2 or x+side>512 or y+side>512:
        raise ValueError('unsupported exact VQ crop')
    source_order=tpl.twiddle_16bpp(list(range(256*256)),256,256)
    linear=bytearray(256*256)
    for at,index in enumerate(source_order):linear[index]=source.base_indices[at]
    n=side//2
    crop=bytes(linear[(y//2+yy)*256+x//2+xx] for yy in range(n) for xx in range(n))
    order=tpl.twiddle_16bpp(list(range(n*n)),n,n)
    indices=bytes(crop[index] for index in order)
    payload=source.codebook+indices
    h,t=list(source.header),list(source.texture)
    t[1]=t[2]=side;t[5]=len(payload);h[7]=len(payload)
    body=tpl.TEXTURE.pack(*t)+payload
    # Package::adopt/open_streamed CRC covers descriptors and payload together.
    # Accept legacy source checksums, but always emit the canonical contract.
    h[8]=zlib.crc32(body)&0xffffffff
    result=tpl.HEADER.pack(*h)+body
    if mip.read_native_vq(result).codebook!=source.codebook:raise ValueError('source book changed')
    return result

def remap(pair,rect):
    x,y,side=rect;scale=512//side
    result=((pair[0]-x*64)*scale,(pair[1]-y*64)*scale)
    if any(v<0 or v>32768 for v in result):raise ValueError('UV outside isolated tile')
    return result

def chunks(actor,inputs):
    arrays=hands_pack.arrays((inputs/'leon_runtime.h').read_text())
    if actor=='standard':return arrays['i1']
    blob=(inputs/'pl08_package.re4cp').read_bytes()
    if blob[:8]!=b'RE4PL08\0':raise ValueError('pl08 magic')
    e=struct.unpack_from('<16I',blob,64)
    if e[:2]!=(0,0):raise ValueError('selected pl08 body role')
    def part(offset,size):
        if offset<256 or offset+size>len(blob):raise ValueError('pl08 array bounds')
        return blob[offset:offset+size]
    return dict(pos=part(e[7],e[8]),nrm=part(e[9],e[10]),uv=part(e[11],e[12]),
                gx=part(e[13],e[6]),weights=part(e[14],e[4]*16))

def budget_groups(groups,uv,rect,max_runs):
    """Retain source order and isolate only segments fitting the existing plan."""
    if max_runs<3:raise ValueError('no room for a bounded source tile run')
    if len(groups)<=max_runs:return groups,[]
    x,y,side=rect
    def crossings(triangles,lod):
        scale=1<<lod;count=0
        for triangle in triangles:
            for c in triangle:
                u,v=uv[c[2]];a=math.floor(u/64/scale-.5);b=math.floor(v/64/scale-.5)
                count+=(a*scale<x or (a+2)*scale>x+side or b*scale<y or (b+2)*scale>y+side)
        return count
    selected=[(i,tris) for i,(pick,tris) in enumerate(groups) if pick]
    selected.sort(key=lambda row:(-crossings(row[1],2),-crossings(row[1],3),-len(row[1]),row[0]))
    keep={i for i,_ in selected[:(max_runs-1)//2]}
    held=[dict(source_segment=i,triangles=len(tris),conservative_crossing_corners_at128=crossings(tris,2))
          for i,tris in selected if i not in keep]
    merged=[]
    for i,(pick,tris) in enumerate(groups):
        pick=pick and i in keep
        if not merged or merged[-1][0]!=pick:merged.append((pick,list(tris)))
        else:merged[-1][1].extend(tris)
    if len(merged)>max_runs:raise ValueError('existing run budget exceeded')
    return merged,held

def ordered_bindings(arrays,rect,out,max_runs=14):
    uv=list(struct.iter_unpack('<2H',arrays['uv']));source=read_fe(arrays['gx'])
    groups=[];selected=0
    x,y,side=rect
    for tri in source:
        own=[x<=uv[c[2]][0]/64<x+side and y<=uv[c[2]][1]/64<y+side for c in tri]
        if any(own) and not all(own):raise ValueError('triangle crosses selected tile ownership')
        pick=all(own)
        if not groups or groups[-1][0]!=pick:groups.append((pick,[]))
        groups[-1][1].append(tri);selected+=pick
    target_triangles=selected
    groups,held=budget_groups(groups,uv,rect,max_runs)
    selected=sum(len(tris) for pick,tris in groups if pick)
    reports=[];roundtrip=[];sample_uv=[]
    for number,(pick,tris) in enumerate(groups):
        folder=out/f'run-{number:03d}';folder.mkdir(parents=True)
        if pick:
            used=list(dict.fromkeys(c[2] for tri in tris for c in tri));translate={old:i for i,old in enumerate(used)}
            new_uv=[remap(uv[old],rect) for old in used]
            ub=b''.join(struct.pack('<2H',*p) for p in new_uv)
            changed=[tuple((c[0],c[1],translate[c[2]]) for c in tri) for tri in tris]
            sample_uv.extend([[uv[c[2]] for c in tri] for tri in tris])
            reverse={i:old for old,i in translate.items()}
        else:ub=arrays['uv'];changed=tris;reverse=None
        stream=make_fe(changed,ub,arrays['gx'])
        back=read_fe(stream)
        if pick:back=[tuple((c[0],c[1],reverse[c[2]]) for c in tri) for tri in back]
        roundtrip.extend(back)
        (folder/'uv.bin').write_bytes(ub);(folder/'stream.meshlets').write_bytes(stream)
        reports.append(dict(index=number,texture='isolated' if pick else 'original-atlas',triangles=len(tris),
            uv_bytes=len(ub),stream_bytes=len(stream),uv_sha256=sha(ub),stream_sha256=sha(stream)))
    if roundtrip!=source or not selected:raise ValueError('ordered geometry identity failed')
    for name in ('pos','nrm','weights'):(out/('source-'+name+'.bin')).write_bytes(arrays[name])
    return dict(source_triangles=len(source),source_tile_triangles=target_triangles,selected_triangles=selected,
        held_segments_for_existing_run_budget=held,role_run_budget=max_runs,runs=reports,
        position_normal_weight_bytes_unchanged={n:sha(arrays[n]) for n in ('pos','nrm','weights')},
        emitted_triangle_order_rotation_indices_and_winding_exact=True),sample_uv

def sample(image,uv):
    import numpy as np
    h,w=image.shape[:2];p=np.asarray(uv,dtype=np.float64)*[w,h]-.5
    lo=np.floor(p).astype(np.int64);f=p-lo
    x0=np.clip(lo[:,0],0,w-1);x1=np.clip(lo[:,0]+1,0,w-1)
    y0=np.clip(lo[:,1],0,h-1);y1=np.clip(lo[:,1]+1,0,h-1)
    return ((1-f[:,0,None])*(1-f[:,1,None])*image[y0,x0]+f[:,0,None]*(1-f[:,1,None])*image[y0,x1]
            +(1-f[:,0,None])*f[:,1,None]*image[y1,x0]+f[:,0,None]*f[:,1,None]*image[y1,x1])

def comparison(before,after,rect,tri_uv,out):
    import numpy as np
    from PIL import Image,ImageDraw
    x,y,side=rect
    weights=np.array([[a/4,b/4,(4-a-b)/4] for a in range(5) for b in range(5-a)])
    corners=np.array(tri_uv,dtype=np.float64)/32768
    uv=np.einsum('ij,tjk->tik',weights,corners).reshape(-1,2)
    local=(uv*512-[x,y])/side
    base=np.array(mip.decode_level(before,512),dtype=np.uint8).reshape(512,512,4)
    crop=base[y:y+side,x:x+side]
    exact=np.array(mip.decode_level(after,side),dtype=np.uint8).reshape(side,side,4)
    if not np.array_equal(crop,exact):raise ValueError('cropped full-resolution pixels changed')
    error=np.abs(sample(base.astype(float),uv)-sample(exact.astype(float),local)).max()
    if error>1e-10:raise ValueError('base bilinear sampling identity failed')
    rows=[];panels=[]
    yy,xx=np.mgrid[0:128,0:128];grid=(np.stack([xx.ravel(),yy.ravel()],axis=1)+.5)/128
    global_grid=(grid*side+[x,y])/512
    for lod in range(10):
        a=max(1,512>>lod);b=max(1,side>>lod)
        old=np.array(mip.decode_level(before,a),dtype=float).reshape(a,a,4)
        new=np.array(mip.decode_level(after,b),dtype=float).reshape(b,b,4)
        scale=side//b
        reference=crop.astype(float).reshape(b,scale,b,scale,4).mean(axis=(1,3))
        target=sample(reference,local)[:,:3]
        first,last=sample(old,uv)[:,:3],sample(new,local)[:,:3]
        mse0=float(((first-target)**2).mean());mse1=float(((last-target)**2).mean())
        rows.append(dict(lod=lod,original_atlas_side=a,isolated_side=b,samples=len(uv),
            before_mse=mse0,after_mse=mse1,before_max_error=float(abs(first-target).max()),
            after_max_error=float(abs(last-target).max()),isolated_foreign_tile_footprints=0))
        if lod in (2,3,4,5):
            panels.append((lod,[sample(old,global_grid),sample(new,grid),sample(reference,grid)]))
    sheet=Image.new('RGB',(3*256,4*282),(25,25,25));draw=ImageDraw.Draw(sheet)
    for row,(lod,images) in enumerate(panels):
        for col,pixels in enumerate(images):
            im=Image.fromarray(np.clip(np.rint(pixels[:,:3]),0,255).astype('uint8').reshape(128,128,3)).resize((256,256),Image.Resampling.NEAREST)
            sheet.paste(im,(col*256,row*282+26))
            draw.text((col*256+5,row*282+5),f'LOD{lod}: '+['atlas','isolated tile','box reference'][col],fill=(255,255,255))
    sheet.save(out/'sampling-before-after.png')
    Image.fromarray(crop).save(out/'exact-base-crop.png')
    return dict(base_crop_pixels_exact=True,base_bilinear_samples=len(uv),base_bilinear_max_error=float(error),
        source_uv_affine_exact=True,padding_or_stretching=False,sampler='bilinear clamp, source body material wrap_s=wrap_t=0',
        levels=rows,scope='Static source UVs and texture sampling; no projected derivatives or gameplay image')

def run(source_root,out,enabled=False):
    if out.exists():raise ValueError('preserve existing candidate')
    seal=(source_root/'SHA256SUMS-actors-v2').read_bytes()
    if sha(seal)!=SOURCE_SEAL:raise ValueError('source actor seal changed')
    sealed={name:digest for digest,name in (line.split('  ',1) for line in seal.decode().splitlines())}
    names=['sampling-scope-v1.json','leon-source-policy-v1.json','leon-v1/inputs/leon_tiles.json',
           'leon-v1/inputs/leon_runtime.h','leon-extra-v1/inputs/leon_runtime.h','leon-extra-v1/inputs/pl08_package.re4cp']
    names += [f'{cohort}/{kind}/{key}.re4tex' for actor,cohort in [('standard','leon-v1'),('pl08','leon-extra-v1')]
              for kind in ('originals','replacements') for key in (KEYS[actor],)]
    for name in names:
        if sha((source_root/name).read_bytes())!=sealed[name]:raise ValueError('selected sealed source changed: '+name)
    out.mkdir(parents=True)
    dump(out/'source-inputs.json',dict(actor_seal_sha256=SOURCE_SEAL,selected={name:sealed[name] for name in names}))
    policies=['sampling-scope-v1.json','leon-source-policy-v1.json']
    for name in policies:(out/name).write_bytes((source_root/name).read_bytes())
    tiles=json.loads((source_root/'leon-v1/inputs/leon_tiles.json').read_text())['source_uv_tiles']
    tile=tiles[TARGET]
    if tile['width']!=tile['height'] or tile['width']!=128:raise ValueError('selected tile must be exact square128')
    rect=(tile['x'],512-tile['y']-tile['height'],128)
    rows=[]
    for actor,cohort in [('standard','leon-v1'),('pl08','leon-extra-v1')]:
        inputs=source_root/cohort/'inputs';key=KEYS[actor]
        blob=(source_root/cohort/'originals'/(key+'.re4tex')).read_bytes()
        policy=json.loads((source_root/'leon-source-policy-v1.json').read_text())
        expected=next(p['source_package_sha256'] for p in policy['rows'] if p['key']==key)
        if sha(blob)!=expected:raise ValueError('source atlas identity changed')
        folder=out/actor;folder.mkdir()
        (folder/'original-atlas.re4tex').write_bytes(blob)
        if not enabled:
            (folder/'candidate.re4tex').write_bytes(blob);rows.append(dict(actor=actor,disabled_identity=True,source_sha256=sha(blob)));continue
        cropped=crop_vq(blob,rect)
        candidate,evidence=mip.add_mipmaps(cropped,enabled=True,engine='numpy')
        (folder/'candidate.re4tex').write_bytes(candidate)
        (folder/'base-crop.re4tex').write_bytes(cropped)
        before=(source_root/cohort/'replacements'/(key+'.re4tex')).read_bytes()
        original=mip.read_native_vq(blob);after=mip.read_native_vq(candidate)
        if after.codebook!=original.codebook:raise ValueError('original codebook changed')
        arr=chunks(actor,inputs)
        # The existing plan permits22 runs. Reserve all other body roles and
        # the source's maximum two hair runs; no runtime capacity is raised.
        old_plan_bound=9 if actor=='standard' else 10
        binding,uv=ordered_bindings(arr,rect,folder/'bindings',max_runs=22-(old_plan_bound-1))
        binding['conservative_total_plan_runs']=old_plan_bound-1+len(binding['runs'])
        binding['existing_plan_run_capacity']=22
        quality=comparison(mip.read_native_vq(before),after,rect,uv,folder)
        seed=('texture-atlas21:v1:'+key+':'+TARGET+':'+sha(candidate)).encode()
        crc=zlib.crc32(seed)&0xffffffff;fnv=hands_pack.fnv(seed)
        row=dict(actor=actor,source_key=key,source_package_sha256=sha(blob),candidate_sha256=sha(candidate),
            derived_key=f'{crc:08x}-{fnv:08x}',tile=TARGET,physical_crop=list(rect),
            codebook_exact=True,base_indices='exact Morton sub-plane crop',original_atlas_unchanged=True,
            added_payload_bytes=len(after.payload),added_payload_32bytes=r32(len(after.payload)),
            source_header_sha256=sha((inputs/'leon_runtime.h').read_bytes()),
            source_pl08_package_sha256=sha((inputs/'pl08_package.re4cp').read_bytes()) if actor=='pl08' else None,
            bindings=binding,sampling=quality,mipmap=evidence)
        dump(folder/'report.json',row);rows.append(row)
    report=dict(schema='re4dc-atlas-split-1',enabled=enabled,source_pack_sha256=PACK_SHA,tile=TARGET,
        no_existing_package_replaced=True,new_runtime_knob_default=0,runtime_integration_accepted=False,
        source_geometry_material_animation_contracts_preserved=True,
        note='Ordered offline run bindings only. Existing material slots remain; derived opaque tile material must be appended by a separately guarded integration.',
        held=['Other atlas tiles','Dynamic hand/headless/LOD qualification','Runtime material/run admission and budgets','Projected LOD/sampling/look','Hardware timing'],textures=rows)
    dump(out/'report.json',report)
    return report

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source-root',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--enable-atlas-split',action='store_true');a=ap.parse_args()
    result=run(a.source_root,a.out,a.enable_atlas_split)
    print(json.dumps(dict(enabled=result['enabled'],textures=len(result['textures']),keys=[r.get('derived_key') for r in result['textures']])))

if __name__=='__main__':main()
