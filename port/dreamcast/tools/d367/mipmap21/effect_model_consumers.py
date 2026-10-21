"""Source-only Efm registration/TPL bindings, separate from sprite image IDs.

Reuse ps2_items.eff_efm (the existing LE EFF model codec) behind explicit table
and target bounds. Registration does not prove the active owner or that every
TPL descriptor is referenced by a model material.
"""
from __future__ import annotations
import hashlib
import struct
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import ps2_items
import room_smd
import convert_character
import effect_consumers as source
import convert_tpl
from prepare_native_ui import image_identity, material_pair_identity


def effect_models(body,entry,*,index=None):
    start,end=entry['off'],entry['end']
    if start<0 or end>len(body) or end-start<48:raise ValueError('short Efm effect block')
    data=body[start:end];h=struct.unpack_from('<12I',data)
    if h[0]!=11:raise ValueError('unsupported Efm effect version')
    if not h[5]:return []
    ids,offsets=h[5],h[11]
    if ids<48 or ids>len(data)-4:raise ValueError('Efm ID table outside block')
    n=source.u32(data,ids)
    if n>(len(data)-ids-4)//8:raise ValueError('Efm model ID bounds differ')
    if not n:return [] # The source never dereferences a missing data table here.
    if offsets<48 or offsets>len(data)-4:raise ValueError('Efm offset table outside block')
    count=source.u32(data,offsets)
    if n!=count or count>(len(data)-offsets-4)//4:
        raise ValueError('Efm model id/offset table bounds differ')
    entries=[offsets+source.u32(data,offsets+4+4*i) for i in range(count)]
    for at in entries:
        if at<offsets+4+4*count or at>len(data)-20:raise ValueError('Efm entry outside block')
        fields=struct.unpack_from('<5I',data,at)
        if not fields[1] or not fields[2]:raise ValueError('Efm lacks model or TPL')
        for relative in fields[1:]:
            if relative and (relative<20 or at+relative>=len(data)):
                raise ValueError('Efm target outside block or overlaps entry')
    decoded=ps2_items.eff_efm(data,'<')
    if len(decoded)!=count:raise ValueError('Efm codec count differs')
    parsed=source.effect(body,entry,index or {},separate_model_namespace=True)
    references=parsed['effect_model_references']
    result=[]
    for i,(ident,model,tpl) in enumerate(decoded):
        result.append(dict(model_index=ident,model_offset=start+model,tpl_offset=start+tpl,
            model_entry_offset=start+entries[i],effect_end=end,
            sequence_references=[r for r in references if r['model_index']==ident],
            scope='Source registration/TPL binding; active owner and model-material descriptor use remain separate.'))
    return result


def source_model_bindings(blob):
    body,offset,entries=source.archive(blob)
    index=source.compact_index(body,entries)
    results=[]
    for entry in entries:
        if entry['tag']!=b'EFF':continue
        # Reuse the index for compact EST records when proving record routing.
        model_rows=effect_models(body,entry,index=index)
        references=source.effect(body,entry,index,separate_model_namespace=True)['effect_model_references']
        local_ids={row['model_index'] for row in model_rows}
        results.append(dict(archive_entry=entry['index'],effect_offset=entry['off'],models=model_rows,
            effect_model_references=references,external_model_registry_references=[r for r in references if r['model_index'] not in local_ids]))
    return dict(active_body_offset=offset,active_body_bytes=len(body),effects=results)



def model_materials(data,*,texture_count=None):
    """Bound source material/UV use; no geometry rewrite or pose evaluation.

    Reuse room_smd layout/part walkers and convert_character primitive order.
    LE metadata/CPU arrays retain BE GX counts and corner indices, as fmt_bin
    and native_actor_fast specify. Only existing 6/8-byte corner layouts apply.
    Unknown opcodes/indices fail; texture255 remains explicitly untextured.
    """
    if len(data)<64:raise ValueError('short effect model')
    layout=room_smd.bin_layout(data,'<')
    if layout['version'] not in (0x20010801,0x20030818):raise ValueError('unsupported effect model version')
    if 'parts' not in layout['region'] or 'tex' not in layout['region']:raise ValueError('effect model lacks parts/UVs')
    stride=8 if layout['flags']&0x80000000 else 6
    tex=layout['ptr']['tex'];texend=layout['region']['tex'][1];parts=layout['ptr']['parts'];partend=layout['region']['parts'][1]
    rows=[]
    for part,(relative,size) in enumerate(room_smd.part_headers(data,'<',layout)):
        at=parts+relative;start=at+32;stop=start+size
        if at<parts or stop>min(len(data),partend):raise ValueError('effect model part overruns region')
        image=data[at+12]
        if texture_count is not None and image!=255 and image>=texture_count:raise ValueError('effect model material TPL index outside table')
        cursor=start;triangles=[]
        while cursor<stop:
            op=data[cursor];cursor+=1
            if op==0:continue
            if op not in (0x80,0x90,0x98) or cursor+2>stop:raise ValueError('unsupported effect model primitive')
            count=struct.unpack_from('>H',data,cursor)[0];cursor+=2
            if count>(stop-cursor)//stride:raise ValueError('effect model primitive overrun')
            records=[struct.unpack_from('>%dH'%(stride//2),data,cursor+stride*i) for i in range(count)];cursor+=count*stride
            if any(rec[0]>=layout['nv'] or rec[1]>=layout['nn'] for rec in records):raise ValueError('effect model position/normal index outside array')
            triangles.extend(convert_character.triangulate(op,records))
        indices=sorted({corner[-1] for tri in triangles for corner in tri});uvs=[]
        for index in indices:
            off=tex+4*index
            if off<tex or off+4>min(texend,len(data)):raise ValueError('effect model UV index outside region')
            signed=bool(layout['flags']&0x80000000);u,v=struct.unpack_from('<2h' if signed else '<2H',data,off);scale=256.0 if signed else 32768.0
            uvs.append((u/scale,v/scale))
        rows.append(dict(part=part,texture_index=image,material_flags=data[at+11],alpha_texture_index=data[at+14],alpha_reference=data[at+20],samples_texture=bool(triangles) and image!=255,triangles=len(triangles),
            UV_indices=indices,UV_bounds=dict(u_min=min(u for u,v in uvs),u_max=max(u for u,v in uvs),v_min=min(v for u,v in uvs),v_max=max(v for u,v in uvs)) if uvs else None))
    return rows


def tpl_images(body,at,*,end=None):
    """Bound LE metadata before reusing the existing GX image codec/identity."""
    if end is None:end=len(body)
    if not 0<=at<end<=len(body):raise ValueError('model TPL effect bounds differ')
    body=body[:end]
    if at+12>len(body):raise ValueError('short model TPL')
    magic,n,desc=struct.unpack_from('<3I',body,at)
    if magic!=convert_tpl.TPL_MAGIC or not n or desc<12 or n>(len(body)-at-desc)//8:
        raise ValueError('model TPL descriptor table outside source')
    for i in range(n):
        header,palette=struct.unpack_from('<2I',body,at+desc+i*8)
        if header<12 or at+header+36>len(body):raise ValueError('model TPL header outside source')
        h,w,fmt,pixels=struct.unpack_from('<2H2I',body,at+header)
        if not w or not h:raise ValueError('model TPL has empty image')
        try:size=ps2_items.image_size(w,h,fmt)
        except KeyError:raise ValueError('unsupported model TPL image') from None
        if pixels<12 or at+pixels+size>len(body):raise ValueError('model TPL pixels outside source')
        if palette:raise ValueError('model TPL indexed palette requires separate contract')
    images=[]
    for image in ps2_items.gc_tpl_images(body[at:],'<'):
        count=ps2_items.image_size(image['w'],image['h'],image['fmt'])
        texture=convert_tpl.TplImage(image['w'],image['h'],image['fmt'],body[at+image['data']:at+image['data']+count])
        key,identity=image_identity(texture);header=at+image['hdr']
        wraps=struct.unpack_from('<2I',body,header+12)
        images.append(dict(image=image['j'],key=key,width=image['w'],height=image['h'],source_format=image['fmt'],
            header_offset=header,pixel_offset=at+image['data'],pixel_bytes=count,source_identity_sha256=hashlib.sha256(identity).hexdigest(),
            wrap_s=wraps[0],wrap_t=wraps[1]))
    return images


def masked_material_bindings(body,model):
    images=tpl_images(body,model['tpl_offset'],end=model.get('effect_end'))
    materials=model_materials(body[model['model_offset']:model['tpl_offset']],texture_count=len(images))
    rows=[]
    for material in materials:
        if not material['samples_texture']:continue
        if material['material_flags']!=4 or material['alpha_reference']!=0:
            raise ValueError('model mask needs explicit material/alpha-reference contract')
        alpha=material['alpha_texture_index']
        if alpha>=len(images):raise ValueError('model alpha descriptor outside TPL')
        color,mask=images[material['texture_index']],images[alpha]
        if any(color[k]!=mask[k] for k in ('width','height','wrap_s','wrap_t')):
            raise ValueError('model color/mask dimensions or wrap differ')
        rows.append(dict(material=material,color=color,mask=mask,pair_key=material_pair_identity(color['key'],mask['key'])))
    return rows
