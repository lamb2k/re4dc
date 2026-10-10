#!/usr/bin/env python3
"""Prepare source-identified UI images using the existing TPL converter/package.
prepare_native_ui.py <source-tree> <files.txt> <out-texture-dir>
No resizing, image substitution or runtime GameCube texture decoder. Existing
16-bit package quantization is a visible candidate requiring image acceptance.
"""
import json
from pathlib import Path
import struct
import sys
import zlib
import hashlib
import le_mirror as mirror
from convert_tpl import parse_tpl, build_package, MaterialBinding, TPL_MAGIC


def image_identity(image):
    palette=image.palette_data or b''
    metadata=struct.pack('<5I',image.width,image.height,image.format,
                         image.palette_format if image.palette_format is not None else 0xffffffff,len(palette))
    payload=metadata+image.data+palette
    fnv=2166136261
    for byte in payload:fnv=((fnv^byte)*16777619)&0xffffffff
    return '%08x-%08x'%(zlib.crc32(payload)&0xffffffff,fnv),payload



def material_pair_identity(color_key, mask_key):
    import re
    if not all(re.fullmatch(r'[0-9a-f]{8}-[0-9a-f]{8}', k) for k in (color_key, mask_key)):
        raise ValueError('invalid source texture identity')
    words=[int(v,16) for k in (color_key,mask_key) for v in k.split('-')]
    payload=b'R4MPv001'+struct.pack('<4I',*words)
    fnv=2166136261
    for b in payload:fnv=((fnv^b)*16777619)&0xffffffff
    return '%08x-%08x'%(zlib.crc32(payload)&0xffffffff,fnv)


def prepare_model_pairs(source, files, pairs, dest):
    """Explicit source-selected pairs; private inputs/output, no asset inventory.
    Equal dimensions and shared UVs are required by the matching native adapter.
    The caller supplies existing qualified resource files and reviewed pair IDs.
    """
    needed={p[k] for p in pairs for k in ('color','mask')}
    images={};origins={};fingerprints={}
    def observe(file, offset, data, context):
        if len(data)>=12 and struct.unpack_from('>II',data)==(TPL_MAGIC,0):return
        for i,image in enumerate(parse_tpl(data)):
            key,payload=image_identity(image)
            if key not in needed:continue
            digest=hashlib.sha256(payload).hexdigest()
            if key in fingerprints and fingerprints[key]!=digest:raise ValueError('texture identity collision')
            fingerprints[key]=digest;images[key]=image
            origins.setdefault(key,[]).append(dict(file=file,context=context,tpl_offset=offset,image=i,sha256=digest))
    previous=mirror.TPL_OBSERVER
    mirror.TPL_OBSERVER=observe
    try:
        for file in files:
            path=source/file
            if file.endswith('.das') and file.startswith('st'):
                mirror.prepare_room_archive(file,path.read_bytes())
            else:mirror.convert_file(file,bytearray(path.read_bytes()))
    finally:mirror.TPL_OBSERVER=previous
    missing=needed-images.keys()
    if missing:raise ValueError('missing requested source images: '+','.join(sorted(missing)))
    dest.mkdir(parents=True,exist_ok=False);report=[]
    for pair in pairs:
        color,mask=images[pair['color']],images[pair['mask']]
        if (color.width,color.height)!=(mask.width,mask.height):raise ValueError('different mask dimensions')
        key=material_pair_identity(pair['color'],pair['mask'])
        blob,meta=build_package([color,mask],[MaterialBinding('source-pair',0,1)],
            twiddle=True,pad_to_power_of_two=True,source_intensity_alpha=True,source_mask_alpha=True)
        file=dest/(key+'.re4tex')
        if file.exists() and file.read_bytes()!=blob:raise ValueError('material pair identity collision')
        file.write_bytes(blob)
        report.append(dict(color=pair['color'],mask=pair['mask'],key=key,bytes=len(blob),
            sha256=hashlib.sha256(blob).hexdigest(),native=meta,
            sources={k:origins[pair[k]] for k in ('color','mask')}))
    (dest/'material-pairs.json').write_text(json.dumps(report,indent=2)+'\n')
    return report

def prepare(source, paths, dest):
    # Refuse a stale/mixed destination; a failed build is never promoted over
    # a previous qualified set. The caller packages only after exit status 0.
    dest.mkdir(parents=True,exist_ok=False)
    source_files={p.relative_to(source).as_posix().lower():p for p in source.rglob('*') if p.is_file()}
    entries=[];errors=[];identities={};seen=set();empty_palettes=[]
    def tpl(file,offset,data,context):
        if not any(context == selector or context.startswith(selector + '/')
                   or (':' not in selector and '#' not in selector and
                       (context.startswith(selector + ':') or context.startswith(selector + '#')))
                   for selector in paths):
            return
        try:
            # Source SMDs can use a zero-descriptor palette and pAddTpl.
            # It has no native image to emit; a malformed header still fails.
            empty=False
            if len(data)>=12:
                magic,count,desc=struct.unpack_from('>3I',data)
                empty=magic==TPL_MAGIC and count==0 and 12<=desc<=len(data)
            if empty:
                images=[];empty_palettes.append({'file':file,'context':context,'tpl_offset':offset})
            else:
                images=parse_tpl(data)
            for i,image in enumerate(images):
                key,payload=image_identity(image);sha=hashlib.sha256(payload).hexdigest()
                if key in identities and identities[key]!=sha:
                    raise ValueError('texture identity collision')
                identities[key]=sha
                if key not in seen:
                    package,meta=build_package([image],[MaterialBinding('source',0,None)],
                                              twiddle=True,pad_to_power_of_two=True,source_intensity_alpha=True)
                    path=dest/(key+'.re4tex')
                    tmp=path.with_suffix('.tmp');tmp.write_bytes(package);tmp.replace(path)
                    seen.add(key)
                entries.append({'file':file,'context':context,'tpl_offset':offset,'image':i,'key':key,'source_sha256':sha,
                                'width':image.width,'height':image.height,'format':image.format})
        except (ValueError,IndexError,struct.error) as exc:
            errors.append({'file':file,'tpl_offset':offset,'error':str(exc)})
    previous_observer=mirror.TPL_OBSERVER
    report_start=len(mirror.REPORT)
    mirror.TPL_OBSERVER=tpl
    try:
        for rel in sorted(set(p.split(':',1)[0].split('#',1)[0] for p in paths)):
            if rel.endswith('.arc') and rel not in source_files:
                # Room source TPLs are inside the original compressed container.
                # Reuse the recovered offline decoder and the same qualification
                # traversal; do not treat a viewer package as a source archive.
                container=source_files.get(rel[:-4]+'.das')
                if container is None:
                    errors.append({'file':rel,'error':'source room container absent'});continue
                try:
                    mirror.prepare_room_archive(rel[:-4]+'.das',container.read_bytes())
                except (ValueError,RuntimeError) as exc:
                    errors.append({'file':rel,'error':str(exc)})
            elif rel not in source_files:
                errors.append({'file':rel,'error':'source file absent'});continue
            else:
                mirror.convert_file(rel,bytearray(source_files[rel].read_bytes()))
            # Reuse the existing qualification gate, independently of image export.
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w',suffix='.txt') as required:
            required.write('\n'.join(paths));required.flush()
            errors.extend({'error':p} for p in mirror.check_required(mirror.REPORT[report_start:],required.name))
    finally:mirror.TPL_OBSERVER=previous_observer
    report={'entries':entries,'errors':errors,'empty_palettes':empty_palettes,'unique_images':len(set(e['key'] for e in entries)),
            'presentation':'Existing RGB565/ARGB4444 quantization; source dimensions/texels retained before quantization, padding only; visual acceptance pending.'}
    (dest/'native-ui-report.json').write_text(json.dumps(report,indent=2))
    return report

# Compact contracts are explicitly selected: r100 scenery/model/effect tables
# and the qualified core HUD table. Keep core noise, card images, font data,
# palettes, mip chains and unreviewed CPU consumers resident.
_NATIVE_RECORD = struct.Struct('<8s6I')
_NATIVE_MAGIC = b'R4NREF\0\0'
_NATIVE_TABLE_MAGIC = b'R4NTBL\0\0'


def compact_spans(decoded, references, ranges):
    """Replace sorted non-overlapping source spans and rebase observed offsets.

    Returns the compact bytes and original-to-resident offset mapping. A retained
    reference into a discarded span is rejected, never silently redirected.
    """
    for previous,current in zip(ranges,ranges[1:]):
        if previous[1]>current[0]:raise ValueError('overlapping replacement spans')
    def mapped(offset):
        saved=0
        for a,b,record in ranges:
            if offset<a or (offset==a and a!=b):break
            if offset<b:raise ValueError('retained offset enters replaced span')
            saved+=b-a-len(record)
        return offset-saved
    out=bytearray();cursor=0
    for a,b,record in ranges:
        out+=decoded[cursor:a]+record;cursor=b
    out+=decoded[cursor:]
    for field,base,value in references:
        struct.pack_into('<I',out,mapped(field),mapped(base+value)-mapped(base))
    return out,mapped


def compact_model_uvs(decoded, models):
    """Share byte-identical UV records in qualified rigid r100 scenery only.

    Source positions/normals/colors, GX commands/order and materials stay intact.
    UVs remain the same four-byte source records; this is not quantization or a
    native sidecar. Savings are multiples of 32 to preserve source alignments.
    """
    import re
    ranges=[];entries=[];patches=[];seen=set();retained=[]
    for model_off,size,ctx,layout in models:
        if not re.fullmatch(r'st1/r100\.arc#5/BIN[0-9]+',ctx):
            continue
        if model_off in seen:
            raise ValueError('duplicate observed model owner')
        seen.add(model_off)
        if (layout['joints']!=1 or layout['weights']>1 or
            layout['extended_weights']>255 or
            any(layout[k] for k in ('shape','blend','flip'))):
            retained.append(dict(context=ctx,reason='non-rigid/morph/motion contract retained'))
            continue
        start=layout['uv_offset'];count=layout['uv_count'];end=start+count*4
        if not count:continue
        if start%4 or start<model_off or end>model_off+size or end>len(decoded):
            raise ValueError('model UV range outside its qualified owner')
        if any(a<b and start<b and end>a for a,b in layout['occupied']):
            raise ValueError('model UV array overlaps a retained consumer')
        indices=layout['uv_indices']
        if any(index>=count or field<model_off or field+2>model_off+size or
               (field<end and field+2>start) or
               struct.unpack_from('>H',decoded,field)[0]!=index
               for field,index in indices):
            raise ValueError('model UV index disagrees with qualified source')
        unique={};remap=[];packed=bytearray()
        for i in range(count):
            record=bytes(decoded[start+i*4:start+(i+1)*4])
            if record not in unique:
                unique[record]=len(unique);packed+=record
            remap.append(unique[record])
        saving=(end-start-len(packed))//32*32
        if not saving:
            retained.append(dict(context=ctx,reason='less than 32 aligned bytes saved'))
            continue
        record=bytes(packed)+bytes(end-start-saving-len(packed))
        ranges.append((start,end,record))
        for field,index in indices:
            patches.append((field,remap[index]))
        # Hash the values in original corner order, independent of index numbers.
        digest=hashlib.sha256()
        for _,index in indices:digest.update(decoded[start+index*4:start+(index+1)*4])
        entries.append(dict(context=ctx,source_model=model_off,source_payload=start,
            source_bytes=end-start,resident_bytes=len(record),source_records=count,
            unique_records=len(unique),corner_references=len(indices),recovery_bytes=saving,
            ordered_uv_sha256=digest.hexdigest(),padding_bytes=len(record)-len(packed)))
    # Mutate only after all selections have been validated; the caller owns this
    # decoded candidate, never the original disc or an accepted mirror.
    for field,index in patches:struct.pack_into('>H',decoded,field,index)
    return sorted(ranges),entries,retained


def accepted_native_package(blob, reference):
    """The deterministic reference package, or a vq_native_ui.py re-encode of it.

    A VQ replacement keeps the file name (source identity), the single
    descriptor's padded dimensions and its 16-bit format, so the runtime UV
    scale (source/native size) is unchanged; only the payload is full VQ.
    """
    from convert_tpl import HEADER, TEXTURE, PAYLOAD_VQ
    if blob==reference:return True
    try:
        h=HEADER.unpack_from(blob);r=HEADER.unpack_from(reference)
        t=TEXTURE.unpack_from(blob,h[5]);u=TEXTURE.unpack_from(reference,r[5])
    except struct.error:return False
    return (h[:6]==r[:6] and h[4]==1 and t[1:4]==u[1:4] and t[7]==PAYLOAD_VQ and
            t[5]==2048+t[1]*t[2]//4 and h[7]==t[5] and len(blob)==h[6]+h[7] and
            zlib.crc32(blob[h[2]:])&0xffffffff==h[8])


def select_upload_only(decoded, palettes, textures, allowed, indexed_allowed=None, native_mips=False):
    """Existing qualified image selection, shared by room/core/enemy producers.

    native_mips (D367 native rendering policy): the Dreamcast renderer samples
    the base level only and re-reads evicted textures from disc, so a base-level
    (minLOD 0) mip chain is externalized whole: the record keys the existing
    base-level package and the removed span covers every source mip level.
    """
    selected=[];retained=[];seen={}
    for tpl_off,raw,ctx in palettes:
        if not allowed(ctx):
            continue
        count,desc=struct.unpack_from('>2I',raw,4)
        if not count:continue
        images=parse_tpl(raw)
        for i,image in enumerate(images):
            header,clut=struct.unpack_from('>2I',raw,desc+i*8)
            pixel=struct.unpack_from('>I',raw,header+8)[0]
            lo,hi=raw[header+33:header+35]
            reason=None
            indexed=bool(indexed_allowed and indexed_allowed(ctx) and clut and
                         image.format in (8,9) and image.palette_data and
                         image.palette_format in (0,1,2) and
                         len(image.palette_data)<= (32 if image.format==8 else 512))
            if (clut or image.palette_data) and not indexed:reason='palette/CPU semantics retained'
            elif (lo or hi) and (not native_mips or lo):reason='source mip chain retained'
            elif image.format in (8,9) and not indexed:reason='indexed source retained'
            if reason:
                retained.append({'context':ctx,'image':i,'reason':reason});continue
            key,identity=image_identity(image)
            package_path=textures/(key+'.re4tex')
            # Verify the existing file against the existing deterministic converter
            # in memory. No candidate encoder or output texture file is written.
            reference,_=build_package([image],[MaterialBinding('source',0,None)],
                twiddle=True,pad_to_power_of_two=True,source_intensity_alpha=True)
            actual=package_path.read_bytes() if package_path.is_file() else b''
            if not accepted_native_package(actual,reference):
                raise ValueError('missing or non-reference native texture: '+key)
            chain=len(image.data)
            if hi:
                from convert_tpl import _expected_image_size
                w,h=image.width,image.height
                for _ in range(hi):
                    w=max(1,w>>1);h=max(1,h>>1);chain+=_expected_image_size(w,h,image.format)
                # Source TPLs pack each chain up to the next payload; small non-square
                # levels are stored in less than the 8x8-block bound above. Remove
                # exactly this image's span: up to the next record, never past it.
                others=[struct.unpack_from('>I',raw,struct.unpack_from('>I',raw,desc+j*8)[0]+8)[0]
                        for j in range(count) if j!=i]+[struct.unpack_from('>I',raw,desc+j*8)[0] for j in range(count)]
                limit=min([o for o in others if o>pixel]+[len(raw)])
                chain=min(chain,limit-pixel)
                if chain<len(image.data) or chain%32:
                    raise ValueError('mip chain does not fit its source span')
            a=tpl_off+pixel;b=a+chain
            if len(image.data)<32 or a%32 or b%32 or b>len(decoded):
                raise ValueError('external texture payload violates source alignment/range')
            crc,fnv=(int(x,16) for x in key.split('-'))
            record=_NATIVE_RECORD.pack(_NATIVE_MAGIC,crc,fnv,image.width,image.height,image.format,chain)
            if indexed:
                # Keep the source CLUT and descriptors resident. Only the immutable
                # index image goes away; runtime binds the existing expanded native
                # image after checking the retained palette against this fingerprint.
                pal=image.palette_data;pf=2166136261
                for v in pal:pf=((pf^v)*16777619)&0xffffffff
                record=b'R4PREF\0\0'+record[8:]+struct.pack('<8I',image.palette_format,len(pal),zlib.crc32(pal)&0xffffffff,pf,0,0,0,0)
                if len(image.data)<len(record):raise ValueError('indexed payload is smaller than identity record')
            entry={'context':ctx,'image':i,'key':key,'source_header':tpl_off+header,
                   'source_tpl':tpl_off,'source_payload':a,'source_bytes':chain,
                   'source_sha256':hashlib.sha256(identity).hexdigest(),
                   'native_package_sha256':hashlib.sha256(actual).hexdigest()}
            if actual!=reference:entry['native_payload']='vq'
            if indexed:
                entry.update(record_bytes=64,palette_bytes=len(image.palette_data),
                    palette_format=image.palette_format,palette_sha256=hashlib.sha256(image.palette_data).hexdigest(),
                    policy='immutable index image externalized; source CLUT retained and checked; native VRAM format unchanged')
            if a in seen:
                if seen[a][0]!=b or seen[a][1]!=record:raise ValueError('incompatible shared payload')
            else:seen[a]=(b,record)
            selected.append(entry)
    ranges=sorted((a,b,record) for a,(b,record) in seen.items())
    return ranges, selected, retained


def native_identity_index(selected, mapped, original_bytes, resident_bytes):
    """Serialize the existing NTR records; archive placement belongs to its loader."""
    table=bytearray()
    for item in selected:
        table+=struct.pack('<3I',mapped(item['source_payload']),mapped(item['source_header']),mapped(item['source_tpl']))
        item['resident_payload']=mapped(item['source_payload'])
        item['resident_header']=mapped(item['source_header'])
        item['resident_tpl']=mapped(item['source_tpl'])
    table_size=(32+len(table)+31)&~31
    header=struct.pack('<8s6I',_NATIVE_TABLE_MAGIC,1,len(selected),12,zlib.crc32(table)&0xffffffff,original_bytes,resident_bytes)
    return header+table+bytes(table_size-32-len(table))


def _compact_upload_only(decoded, references, palettes, textures, allowed, effect_ranges=(), effect_entries=(), indexed_allowed=None, model_ranges=(), model_entries=(), native_mips=False, header_grow=0):
    """Shared source-layout transform, using the existing converter's offsets."""
    import compact_effect_records as effects
    n=struct.unpack_from('<I',decoded)[0]
    offsets=struct.unpack_from('<%dI'%n,decoded,16)
    tags=[bytes(decoded[16+4*n+4*i:20+4*n+4*i]) for i in range(n)]
    extra=1+bool(effect_entries)
    first=min(x for x in offsets if x)
    # header_grow (a room contract's reviewed value, 32-byte aligned): the source header ends flush with the
    # first payload (r104: 46 slots, 384 B), so the payloads move up by header_grow through compact_spans'
    # own rebasing (an empty source span replaced by zeros at the first payload).
    if first+header_grow<16+8*(n+extra):
        raise ValueError('archive lacks spare native-identity header slot')
    grow_ranges=[(first,first,bytes(header_grow))] if header_grow else []
    ranges,selected,retained=select_upload_only(decoded,palettes,textures,allowed,indexed_allowed,native_mips)
    if not ranges:raise ValueError('no qualified upload-only payloads')
    out,mapped=compact_spans(decoded,references,sorted(grow_ranges+ranges+list(effect_ranges)+list(model_ranges)))
    if any(struct.unpack_from('<I',out,16+4*i)[0]!=(mapped(off) if off else 0) for i,off in enumerate(offsets)):
        raise ValueError('archive slot offsets not rebased')
    table_size=(32+12*len(selected)+31)&~31
    effect_size=((32+12*len(effect_entries)+31)&~31) if effect_entries else 0
    final_bytes=len(out)+table_size+effect_size
    new_offsets=[];new_tags=[]
    if effect_entries:
        new_offsets.append(len(out));new_tags.append(b'ESQ\0')
        out+=effects.identity_index(effect_entries,mapped,final_bytes)
    new_offsets.append(len(out));new_tags.append(b'NTR\0')
    out+=native_identity_index(selected,mapped,len(decoded),final_bytes)
    struct.pack_into('<I',out,0,n+extra)
    for i,off in enumerate(new_offsets):struct.pack_into('<I',out,16+4*(n+i),off)
    out[16+4*(n+extra):16+8*(n+extra)]=b''.join(tags+new_tags)
    report={'original_archive_bytes':len(decoded),'resident_archive_bytes':len(out),
        'archive_recovery_bytes':len(decoded)-len(out),'identity_table_bytes':table_size,
        'replacement_record_bytes':sum(len(record) for _,_,record in ranges),'selected':selected,'retained':retained}
    if model_entries:
        for e in model_entries:
            e['resident_model']=mapped(e['source_model'])
            e['resident_payload']=mapped(e['source_payload'])
        report['model_uvs']=dict(entries=model_entries,
            recovery_bytes=sum(b-a-len(v) for a,b,v in model_ranges),
            runtime_metadata_bytes=0,runtime_scratch_bytes=0,
            policy='exact source UV records shared; source GX backing replaced offline')
    if effect_entries:
        for e in effect_entries:e['resident_offset']=mapped(e['source_offset'])
        report['effects']={'entries':effect_entries,'index_bytes':effect_size,
            'recovery_bytes':sum(b-a-len(v) for a,b,v in effect_ranges)-effect_size,
            'policy':'resident exact records; unsupported records/trailers retained; no I/O'}
    return out,report


# Reviewed room slot contracts: archive slot count, the SMD scenery owner, the EFF
# owners whose image ids gate CPU-noise images, the ITM owner and the local BIN/TPL
# model texture slots. Every other slot (CAM, SAT/EAT collision, LIT, AEV, ESL/EMI,
# RTP, MDT, CNS, scripts, sound) stays byte-identical; only upload-only images move
# to the existing native packages.
ROOM_CONTRACTS={
    'r100':dict(slots=51,smd=5,effs=(8,),itm=10,model_slots=(26,28,33,36,38,46)),
    # r101 (frontier W4): 37 slots; SMD#4 scenery TPL0, EFF#7 room effects,
    # EFF#35 local effects, ITM#9, model TPLs #27/#29/#34 (after BIN #26/#28/#33).
    'r101':dict(slots=37,smd=4,effs=(7,35),itm=9,model_slots=(27,29,34)),
    # r103 (W8b): 37 slots, r101's owner layout without model slots and with one
    # EFF: SMD#4 scenery TPL0, EFF#7 room effects, ITM#9. FCV#27-36 (the corpse
    # motions) and every other slot stay byte-identical.
    'r103':dict(slots=37,smd=4,effs=(7,),itm=9,model_slots=()),
    # r106 (route lane): 55 slots, r101's owner layout: SMD#4 scenery TPL0, EFF#7 room
    # effects, EFF#42 local effects, ITM#9, model TPLs #47/#49/#51 (after BIN #46/#48/#50).
    'r106':dict(slots=55,smd=4,effs=(7,42),itm=9,model_slots=(47,49,51)),
    # r104 (route lane): 46 slots, r106's owner layout without the model BIN/TPL pairs: SMD#4 scenery
    # TPL0, EFF#7 room effects, EFF#42 local effects, ITM#9.
    # Its header ends flush with the first payload: header_grow=32 makes room for the NTR slot.
    'r104':dict(slots=46,smd=4,effs=(7,42),itm=9,model_slots=(),header_grow=32),
    # r107 (route lane): 27 slots, r103's owner layout (SMD#4, EFF#7, ITM#9; no EMI/BIN/FCV/SEQ tail).
    'r107':dict(slots=27,smd=4,effs=(7,),itm=9,model_slots=()),
    # r105 (route lane): r107's 27-slot layout.
    'r105':dict(slots=27,smd=4,effs=(7,),itm=9,model_slots=()),
    # Chapter 1-3 (route lane c13): r102 and r108 have r107's 27-slot layout; r109 adds three SAT
    # (#27-29, byte-identical); r10a has 46 slots: EMI#27, BIN#28, FCV/SEQ#29-45 (byte-identical) and
    # EFF#42 local effects; its header ends flush with the first payload, as r104's (header_grow=32).
    'r102':dict(slots=27,smd=4,effs=(7,),itm=9,model_slots=()),
    'r108':dict(slots=27,smd=4,effs=(7,),itm=9,model_slots=()),
    'r109':dict(slots=30,smd=4,effs=(7,),itm=9,model_slots=()),
    'r10a':dict(slots=46,smd=4,effs=(7,42),itm=9,model_slots=(),header_grow=32),
    # r10b (route, chapter 1-3's end, the lake): 36 slots, SMD#4, EFF#7 room effects, EFF#34 local effects,
    # ITM#9, model TPL#27 (after BIN#26: the floating island); FCV#28-31, EMI#32, DSE#33, UWF#35 byte-identical.
    'r10b':dict(slots=36,smd=4,effs=(7,34),itm=9,model_slots=(27,)),
    # r210 (St2, world coverage lane): 36 slots, SMD#4, EFF#7, ITM#9, model TPL#31 (after BIN#30); FCV#27-29/#32-35
    # (the lift motions) and every other slot stay byte-identical.
    'r210':dict(slots=36,smd=4,effs=(7,),itm=9,model_slots=(31,)),
    # r40c (St4, world coverage lane): r107's 27-slot layout.
    'r40c':dict(slots=27,smd=4,effs=(7,),itm=9,model_slots=()),
    # r219 (St2, world coverage lane, st2_2): r210's layout in 35 slots: SMD#4, EFF#7, ITM#9, model TPL#31 (after
    # BIN#30); FCV#27-29/#32-34 stay byte-identical (slot tags of the GC disc 1 St2/r219.das).
    'r219':dict(slots=35,smd=4,effs=(7,),itm=9,model_slots=(31,)),
    # r40a (St4, world coverage lane, st4_0 + em1f): r40c's owner layout in 30 slots; FCV#27-29 byte-identical.
    # Its header ends flush with the first payload (256 B), as r104's: header_grow=32 makes room for the NTR slot.
    'r40a':dict(slots=30,smd=4,effs=(7,),itm=9,model_slots=(),header_grow=32),
    # Follow-up 7 (world coverage lane, St1; slot tags of the GC disc 1 St1/<room>.das, assets.sh discover):
    # r109: 30 slots, r107's owner layout + SAT#27-29; header ends flush with the first payload (256 B): header_grow 32.
    'r109':dict(slots=30,smd=4,effs=(7,),itm=9,model_slots=(),header_grow=32),
    # r10c: 35 slots, SMD#4, EFF#7, ITM#9, model TPL#28 (after BIN#27); FCV#29-34 byte-identical.
    'r10c':dict(slots=35,smd=4,effs=(7,),itm=9,model_slots=(28,)),
    # r10f: 48 slots, models TPL#28 (BIN#27) and TPL#32 (BIN#31; BIN#30 alone); FCV#29/#33-46, EMI#47 byte-identical.
    'r10f':dict(slots=48,smd=4,effs=(7,),itm=9,model_slots=(28,32)),
    # r11a: r107's 27-slot layout.
    'r11a':dict(slots=27,smd=4,effs=(7,),itm=9,model_slots=()),
    # r40b (St4, st4_0 + em1f; follow-up 7): r40c's 27-slot layout (header ends at 232 of 256: no growth).
    'r40b':dict(slots=27,smd=4,effs=(7,),itm=9,model_slots=()),
}

def compact_room(source_file, textures, destination, compact_effects=False, compact_palettes=False, compact_uvs=False, compact_mips=False):
    """Prepare one smaller qualified .dar through the existing room builder.

    Uses the converter's recorded relative offsets, not a second archive parser
    or runtime lazy loader. No texture files are generated by this operation.
    """
    source_file, textures, destination = map(Path, (source_file, textures, destination))
    name=source_file.name.lower()
    room=name[:-4] if name.endswith('.das') else ''
    if room not in ROOM_CONTRACTS:
        raise ValueError('only the reviewed consumer contracts are supported: '+' '.join(sorted(ROOM_CONTRACTS)))
    if room!='r100' and (compact_effects or compact_palettes or compact_uvs):
        raise ValueError('effect/palette/UV compaction is reviewed for r100 only')
    contract=ROOM_CONTRACTS[room]
    if destination.exists():
        raise FileExistsError(destination)
    stage='st'+room[1]   # the room's stage directory (st1 / st2 / st4)
    rel='%s/%s.das'%(stage,room);arc='%s/%s.arc'%(stage,room)
    source=source_file.read_bytes();references=[];palettes=[];sequences=[];models=[]
    previous_tpl,previous_offsets,previous_seq=mirror.TPL_OBSERVER,mirror.OFFSET_OBSERVER,mirror.SEQUENCE_OBSERVER
    previous_model=mirror.MODEL_OBSERVER
    start=len(mirror.REPORT)
    if compact_uvs:
        mirror.MODEL_OBSERVER=lambda file,off,size,ctx,layout: models.append((off,size,ctx,layout)) if file==arc else None
    mirror.TPL_OBSERVER=lambda file,off,data,ctx: palettes.append((off,data,ctx))
    mirror.OFFSET_OBSERVER=lambda file,field,base,value: references.append((field,base,value)) if file==arc else None
    mirror.SEQUENCE_OBSERVER=lambda file,off,data,ctx: sequences.append((off,data,ctx)) if file==arc else None
    try:
        _,decoded=mirror.prepare_room_archive(rel,source)
        container=bytearray(source);mirror.convert_file(rel,container)
    finally:
        mirror.TPL_OBSERVER,mirror.OFFSET_OBSERVER,mirror.SEQUENCE_OBSERVER=previous_tpl,previous_offsets,previous_seq
        mirror.MODEL_OBSERVER=previous_model
    coverage=mirror.REPORT[start:]
    # This is the existing whole-archive + sound qualification gate, before any
    # candidate transformation. It cannot be replaced by sidecar existence.
    mirror.prepare_native_room(rel,container,decoded,coverage)
    n=struct.unpack_from('<I',decoded)[0]
    offsets=struct.unpack_from('<%dI'%n,decoded,16)
    tags=[bytes(decoded[16+4*n+4*i:20+4*n+4*i]) for i in range(n)]
    if (n!=contract['slots'] or tags[contract['smd']]!=b'SMD\0' or tags[contract['itm']]!=b'ITM\0' or
        any(tags[e]!=b'EFF\0' for e in contract['effs']) or
        (room!='r100' and any(tags[m]!=b'TPL\0' or tags[m-1]!=b'BIN\0' for m in contract['model_slots'])) or
        min(offsets)+contract.get('header_grow',0)<16+8*(n+1)):
        raise ValueError('%s archive layout differs from reviewed contract'%room)
    eff_ids_by_slot={}
    for slot in contract['effs']:
        eff=offsets[slot];eff_ids=eff+struct.unpack_from('<I',decoded,eff+4)[0]
        num_eff=struct.unpack_from('<I',decoded,eff_ids)[0]
        eff_ids_by_slot[slot]=[struct.unpack_from('<H',decoded,eff_ids+4+i*8)[0] for i in range(num_eff)]
    model_slots=set(contract['model_slots'])
    def allowed(ctx):
        for slot,ids in eff_ids_by_slot.items():
            if ctx.startswith(arc+'#%d/tpl'%slot):
                ident=int(ctx.rsplit('tpl',1)[1])
                # Espgen42/45 consume 0xFE as CPU noise. Never externalize it.
                return ident<len(ids) and ids[ident]!=0xfe
        return (ctx in (arc+'#%d/TPL0'%contract['smd'],arc+'#%d/item'%contract['itm']) or
                any(ctx==arc+'#'+str(i) for i in model_slots))
    effect_ranges=[];effect_entries=[];skipped=[]
    if compact_effects:
        import compact_effect_records as effects
        # These EFF owners all register through EspDataLoad. EST access uses the
        # existing opaque-reference adapter; SST/path/model data remain raw.
        families=[arc+'#8']+[arc+'#11/'+name+'.eff' for name in ('et00','et01','et02','et0d','obm2b')]
        if tags[11]!=b'ETM\0' or struct.unpack_from('<I',decoded,4)[0]:
            raise ValueError('r100 effect ownership layout differs from reviewed contract')
        for family in families:
            qualified=[]
            for off,data,ctx in sequences:
                if ctx!=family+'/est':continue
                used=48+300*struct.unpack_from('<H',data)[0]
                if used>len(data):raise ValueError('truncated room sequence')
                if any(data[used:]):
                    skipped.append({'source_offset':off,'source_bytes':len(data),'reason':'unexplained trailer retained unchanged'})
                else:qualified.append((off,data,ctx))
            er,ee=effects.prepare_sequences(qualified,family)
            effect_ranges+=er;effect_entries+=ee
        effect_ranges.sort();effect_entries.sort(key=lambda e:e['source_offset'])
        if not effect_entries:raise ValueError('no qualified room sequences')
    # Existing r100 EFF texture consumers retain their CLUT/animation tables.
    # CPU noise ID FE, mip chains, all other palettes and families stay resident.
    def indexed_allowed(ctx):
        return compact_palettes and ctx.startswith(arc+'#8/tpl') and allowed(ctx)
    model_ranges=[];model_entries=[];model_retained=[]
    if compact_uvs:
        model_ranges,model_entries,model_retained=compact_model_uvs(decoded,models)
        if not model_entries:raise ValueError('no qualified scenery UV saving')
    out,stats=_compact_upload_only(decoded,references,palettes,textures,allowed,
        effect_ranges,effect_entries,indexed_allowed,model_ranges,model_entries,compact_mips,contract.get('header_grow',0))
    if compact_uvs:stats['model_uvs']['retained']=model_retained
    if compact_effects:stats['effects']['skipped']=skipped
    _,packaged=mirror.prepare_native_room(rel,container,out,coverage)
    report={'contract':'r100-resident-effects-v1' if compact_effects else room+'-upload-only-v1','source_file':str(source_file),
            'source_sha256':hashlib.sha256(source).hexdigest(),
            **stats,
            'qualification':coverage,'loading':'source DVD queue reads compact type-0 directly; original sound container retained',
            'limits':'No mip/CLUT/CPU-noise removal; optional immutable r100 EFF index images use existing native packages. No source-archive saving accepted before target measurement.',
            'compact_palettes':compact_palettes,'compact_uvs':compact_uvs,'compact_mips':compact_mips,
            'room_contract':contract}
    destination.mkdir()
    (destination/(room+'.dar')).write_bytes(packaged)
    (destination/(room+'.arc')).write_bytes(out)
    (destination/'compact-room-report.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def compact_option(source_file, textures, destination):
    """Compact the persistent English option/death owner, keeping source IDs.

    Its two EFF families are consumed by IdTexDataLoad; UWF, palette images and
    mip chains remain resident. This plain tagged file uses the existing DVD
    fixed-region bounds check, not the room .dar transport.
    """
    source_file,textures,destination=map(Path,(source_file,textures,destination))
    if source_file.name.lower()!='option.dat':raise ValueError('expected option.dat')
    if destination.exists():raise FileExistsError(destination)
    rel='ss/eng/option.dat';source=source_file.read_bytes();decoded=bytearray(source)
    references=[];palettes=[];start=len(mirror.REPORT)
    old_tpl,old_offsets=mirror.TPL_OBSERVER,mirror.OFFSET_OBSERVER
    mirror.TPL_OBSERVER=lambda file,off,data,ctx:palettes.append((off,data,ctx))
    mirror.OFFSET_OBSERVER=lambda file,field,base,value:references.append((field,base,value))
    try:mirror.convert_file(rel,decoded)
    finally:mirror.TPL_OBSERVER,mirror.OFFSET_OBSERVER=old_tpl,old_offsets
    coverage=mirror.REPORT[start:]
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w') as required:
        required.write(rel+'\n');required.flush()
        bad=mirror.check_required(coverage,required.name)
    if bad:raise ValueError('unqualified option dependency: '+', '.join(bad))
    n=struct.unpack_from('<I',decoded)[0]
    offsets=struct.unpack_from('<%dI'%n,decoded,16)
    tags=[bytes(decoded[16+4*n+4*i:20+4*n+4*i]) for i in range(n)]
    if n!=11 or tags!=[b'EFF\0' if i in (0,4) else b'UWF\0' for i in range(11)] or struct.unpack_from('<I',decoded,4)[0]:
        raise ValueError('option layout differs from reviewed contract')
    ids_by_family={}
    for slot in (0,4):
        eff=offsets[slot];ids_at=eff+struct.unpack_from('<I',decoded,eff+4)[0]
        count=struct.unpack_from('<I',decoded,ids_at)[0]
        ids_by_family[rel+'#'+str(slot)]=[struct.unpack_from('<H',decoded,ids_at+4+i*8)[0] for i in range(count)]
    def allowed(ctx):
        for family,ids in ids_by_family.items():
            if ctx.startswith(family+'/tpl'):
                index=int(ctx.rsplit('tpl',1)[1])
                return index<len(ids) and ids[index]!=0xfe
        return False
    out,stats=_compact_upload_only(decoded,references,palettes,textures,allowed)
    def body(data,i):
        count=struct.unpack_from('<I',data)[0];ofs=struct.unpack_from('<%dI'%count,data,16)
        return data[ofs[i]:min([o for o in ofs if o>ofs[i]]+[len(data)])]
    for i in range(n):
        if i not in (0,4) and body(decoded,i)!=body(out,i):
            raise ValueError('option UI layout changed: '+str(i))
    report={'contract':'english-option-upload-only-v1','source_file':str(source_file),
        'source_sha256':hashlib.sha256(source).hexdigest(),**stats,'qualification':coverage,
        'required_reservation_bytes':(len(out)+31)&~31,
        'loading':'plain tagged file reads directly into selected option reservation; bind before source TPL relocation',
        'limits':'Persistent pause/death data; palettes and UWF retained. Mutable ARAM fallback is not qualified. Target saving requires smaller reservation.'}
    destination.mkdir();(destination/'option.dat').write_bytes(out)
    (destination/'compact-option-report.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def compact_core(source_file, textures, destination, include_effects=False, compact_effects=False):
    """Externalize core HUD #25 and optionally the qualified effect #1 table.

    Optional EST packing reuses the resident codec for audited core owners 0/D1.
    Nonzero sequence trailers stay raw; original heads and all records survive.
    Other families retain exact converted bytes and qualification status.
    The optional effect family requires its Path/PathVtx conversion as well;
    it never qualifies VIB/SAT. CPU noise, palettes and mip chains stay resident.
    """
    source_file,textures,destination=map(Path,(source_file,textures,destination))
    if source_file.name.lower()!='core.das':raise ValueError('expected core.das')
    if destination.exists():raise FileExistsError(destination)
    rel='etc/core.das';slots=(1,25) if include_effects else (25,)
    families=[rel+':0#'+str(i) for i in slots]
    source=source_file.read_bytes();container=bytearray(source);references=[];palettes=[];sequences=[]
    old_tpl,old_offsets,old_seq=mirror.TPL_OBSERVER,mirror.OFFSET_OBSERVER,mirror.SEQUENCE_OBSERVER
    start=len(mirror.REPORT)
    mirror.TPL_OBSERVER=lambda file,off,data,ctx: palettes.append((off,data,ctx))
    mirror.OFFSET_OBSERVER=lambda file,field,base,value: references.append((field,base,value))
    mirror.SEQUENCE_OBSERVER=lambda file,off,data,ctx:sequences.append((off,data,ctx))
    try:mirror.convert_file(rel,container)
    finally:mirror.TPL_OBSERVER,mirror.OFFSET_OBSERVER,mirror.SEQUENCE_OBSERVER=old_tpl,old_offsets,old_seq
    coverage=mirror.REPORT[start:]
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w') as required:
        required.write('\n'.join(families+([rel+':0#1',rel+':0#16'] if compact_effects else []))+'\n');required.flush()
        bad=mirror.check_required(coverage,required.name)
    # Sound semantics stay on the original DVD queue, with the converted nested
    # container retained verbatim. Require its existing conversion to succeed.
    bad += [str(e.get('part')) for e in coverage if '/' in str(e.get('part','')) and
            (not e.get('handled') or e.get('complete') is not True or e.get('error'))]
    if bad:raise ValueError('unqualified selected core dependency: '+', '.join(bad))
    slot=mirror.native_payload_slot(container)
    size,base=struct.unpack_from('<I4xI',container,slot+4)
    decoded=container[base:base+size]
    n=struct.unpack_from('<I',decoded)[0]
    offsets=struct.unpack_from('<%dI'%n,decoded,16)
    checked_slots=set(slots).union((1,16) if compact_effects else ())
    if n!=36 or any(decoded[16+4*n+i*4:20+4*n+i*4]!=b'EFF\0' for i in checked_slots):
        raise ValueError('core layout differs from reviewed contract')
    ids_by_family={}
    for slot,family in zip(slots,families):
        eff=offsets[slot];ids_at=eff+struct.unpack_from('<I',decoded,eff+4)[0]
        count=struct.unpack_from('<I',decoded,ids_at)[0]
        ids_by_family[family]=[struct.unpack_from('<H',decoded,ids_at+4+i*8)[0] for i in range(count)]
    def allowed(ctx):
        for family,ids in ids_by_family.items():
            if ctx.startswith(family+'/tpl'):
                index=int(ctx.rsplit('tpl',1)[1])
                return index<len(ids) and ids[index]!=0xfe
        return False
    refs=[(f-base,b-base,v) for f,b,v in references if base<=f<base+size]
    palettes=[(o-base,d,c) for o,d,c in palettes if base<=o<base+size]
    effect_ranges=[];effect_entries=[];skipped=[]
    if compact_effects:
        import compact_effect_records as effects
        if struct.unpack_from('<I',decoded,4)[0]:raise ValueError('core REL not supported')
        for i in (1,16):
            family=rel+':0#'+str(i);qualified=[]
            for o,data,ctx in sequences:
                if ctx!=family+'/est':continue
                used=48+300*struct.unpack_from('<H',data)[0]
                if used>len(data):raise ValueError('truncated core sequence')
                if any(data[used:]):
                    skipped.append({'source_offset':o-base,'source_bytes':len(data),'reason':'unexplained trailer retained unchanged'})
                else:qualified.append((o-base,data,ctx))
            er,ee=effects.prepare_sequences(qualified,family)
            effect_ranges+=er;effect_entries+=ee
        effect_ranges.sort();effect_entries.sort(key=lambda e:e['source_offset'])
        if not effect_entries:raise ValueError('no qualified core sequences')
    out,stats=_compact_upload_only(decoded,refs,palettes,textures,allowed,effect_ranges,effect_entries)
    if compact_effects:stats['effects']['skipped']=skipped
    # A whole unselected family can move, but its internal offsets and all
    # payload bytes must remain unchanged, including presently raw sections.
    def body(data,i):
        num=struct.unpack_from('<I',data)[0];ofs=struct.unpack_from('<%dI'%num,data,16)
        return data[ofs[i]:min([o for o in ofs if o>ofs[i]]+[len(data)])]
    for i in range(n):
        if i not in checked_slots and offsets[i] and body(decoded,i)!=body(out,i):
            raise ValueError('unselected core family changed: '+str(i))
    packaged=mirror.replace_native_payload(container,out)
    report={'contract':'core-resident-effects-v1' if compact_effects else 'core-effects-hud-upload-only-v1' if include_effects else 'core-hud-upload-only-v1','source_file':str(source_file),
        'source_sha256':hashlib.sha256(source).hexdigest(),**stats,
        'qualification':coverage,'qualified_selection':sorted(set(families+([rel+':0#1',rel+':0#16'] if compact_effects else []))),
        'retained_unqualified':[e for e in coverage if e.get('complete') is False or not e.get('handled')],
        'loading':'compact type-0 reads directly into matching fixed core reservation; original sound blocks retained',
        'limits':'Selected upload-only textures and optional audited EST readers only; other core coverage unchanged. Target savings require a smaller actual reservation. Debug effect editing is not qualified.'}
    destination.mkdir();(destination/'core.das').write_bytes(packaged)
    (destination/'core.arc').write_bytes(out)
    (destination/'compact-core-report.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__=='__main__':
    if any(flag in sys.argv for flag in ('--compact-room','--compact-core','--compact-option')):
        import argparse
        parser=argparse.ArgumentParser(description='Compact reviewed source texture families using existing native packages')
        choice=parser.add_mutually_exclusive_group(required=True)
        choice.add_argument('--compact-room',type=Path)
        choice.add_argument('--compact-core',type=Path)
        choice.add_argument('--compact-option',type=Path)
        parser.add_argument('--core-effects',action='store_true',help='also externalize qualified core EFF #1 upload-only images')
        parser.add_argument('--compact-core-est',action='store_true',help='lossless resident packing for qualified core EST #1/#16')
        parser.add_argument('--compact-room-est',action='store_true',help='lossless resident packing for qualified r100 EST owners')
        parser.add_argument('--compact-room-palettes',action='store_true',help='externalize reviewed r100 EFF index images; keep source palettes and existing native VRAM format')
        parser.add_argument('--compact-room-uvs',action='store_true',help='share exact source UV records in qualified rigid r100 scenery')
        parser.add_argument('--compact-room-mips',action='store_true',help='native rendering policy: externalize base-level r100 mip chains whole (Dreamcast samples the base level only)')
        parser.add_argument('--textures',type=Path,required=True)
        parser.add_argument('--output',type=Path,required=True)
        args=parser.parse_args()
        if args.core_effects and not args.compact_core:parser.error('--core-effects requires --compact-core')
        if args.compact_core_est and not args.compact_core:parser.error('--compact-core-est requires --compact-core')
        if args.compact_room_est and not args.compact_room:parser.error('--compact-room-est requires --compact-room')
        if args.compact_room_palettes and not args.compact_room:parser.error('--compact-room-palettes requires --compact-room')
        if args.compact_room_uvs and not args.compact_room:parser.error('--compact-room-uvs requires --compact-room')
        if args.compact_room_mips and not args.compact_room:parser.error('--compact-room-mips requires --compact-room')
        if args.compact_option:report=compact_option(args.compact_option,args.textures,args.output)
        elif args.compact_core:report=compact_core(args.compact_core,args.textures,args.output,args.core_effects,args.compact_core_est)
        else:report=compact_room(args.compact_room,args.textures,args.output,args.compact_room_est,args.compact_room_palettes,args.compact_room_uvs,args.compact_room_mips)
        print('compact archive:',report['original_archive_bytes'],'->',report['resident_archive_bytes'],
              'recovery',report['archive_recovery_bytes'],'identities',len(report['selected']))
    else:
        source,manifest,dest=map(Path,sys.argv[1:])
        paths=[s.strip().lower() for s in manifest.read_text().splitlines() if s.strip() and not s.lstrip().startswith('#')]
        report=prepare(source,paths,dest)
        print('native UI images:',report['unique_images'],'errors:',report['errors'])
        sys.exit(2 if report['errors'] else 0)
