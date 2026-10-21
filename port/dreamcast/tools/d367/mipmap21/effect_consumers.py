"""Read-only effect sequence proof, including retained compact EST records.

EFF is also used by IdTexDataLoad. A format tag or artwork preview does not
establish a particle consumer. These helpers expose source bindings, never
infer actual spawning, drawing or exclusive runtime use from static records.
"""
from __future__ import annotations

import hashlib
import struct
import sys
from pathlib import Path
import zlib

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import compact_effect_records
import le_mirror


def u32(blob,off):
    if off<0 or off+4>len(blob):raise ValueError('effect word outside input')
    return struct.unpack_from('<I',blob,off)[0]


def archive(blob):
    try:slot=le_mirror.native_payload_slot(blob)
    except ValueError:body,offset=blob,0
    else:
        size,offset=struct.unpack_from('<I4xI',blob,slot+4)
        if offset+size>len(blob):raise ValueError('native effect archive bounds')
        body=blob[offset:offset+size]
    n=u32(body,0)
    if not 0<n<=4096 or 16+8*n>len(body):raise ValueError('effect archive table bounds')
    rel=u32(body,4);end=rel if 16+8*n<=rel<=len(body) else len(body)
    offsets=[u32(body,16+4*i) for i in range(n)]
    bounds=sorted(set(o for o in offsets if 16+8*n<=o<end)|{end})
    entries=[]
    for i,off in enumerate(offsets):
        tag=body[16+4*n+4*i:20+4*n+4*i].rstrip(b'\0')
        if off in bounds and off!=end:
            entries.append(dict(off=off,end=bounds[bounds.index(off)+1],tag=tag,index=i+4))
    return body,offset,entries


def compact_index(body,entries):
    tables=[e for e in entries if e['tag']==b'ESQ']
    if not tables:return {}
    if len(tables)!=1:raise ValueError('ambiguous compact effect index')
    e=tables[0];at=e['off']
    if at+32>e['end']:raise ValueError('short compact effect index')
    magic,version,count,stride,crc,size,zero=struct.unpack_from('<8s6I',body,at)
    table=body[at+32:at+32+12*count]
    if (magic!=b'R4ESQTBL' or version!=1 or stride!=12 or zero or size!=len(body)
            or not 0<count<=4096 or len(table)!=12*count or at+32+len(table)>e['end']
            or zlib.crc32(table)&0xffffffff!=crc):
        raise ValueError('invalid compact effect index identity/bounds')
    result={};previous=16+8*u32(body,0)
    for i in range(count):
        off,span,nr=struct.unpack_from('<3I',table,12*i)
        if off<previous or off&3 or span&31 or span<48 or off+span>at or off in result:
            raise ValueError('invalid compact effect sequence range')
        if not nr or nr>(span-48)//4 or struct.unpack_from('<H',body,off)[0]!=nr:
            raise ValueError('compact effect record count differs')
        result[off]=(span,nr);previous=off+span
    return result


def sequence_records(body,off,end,index):
    if off<0 or off+48>end or end>len(body):raise ValueError('effect sequence bounds')
    count=struct.unpack_from('<H',body,off)[0]
    records=[]
    if off not in index:
        if count>(end-off-48)//300:raise ValueError('raw effect sequence truncated')
        return [(off+48+300*i,False,body[off+48+300*i:off+48+300*(i+1)]) for i in range(count)]
    span,nr=index[off]
    if count!=nr or off+span>end:raise ValueError('compact sequence exceeds section')
    expected=48+4*count
    for i in range(count):
        value=u32(body,off+48+4*i);start=value&~1
        stop=(u32(body,off+48+4*(i+1))&~1) if i+1<count else span
        if start!=expected or start&3 or start>=stop or stop>span:
            raise ValueError('compact record offsets differ')
        if value&1:
            if stop-start<12:raise ValueError('short compact record')
            masks=struct.unpack_from('<3I',body,off+start)
            size=12+4*sum(m.bit_count() for m in masks)
            if size>=300 or size>stop-start:raise ValueError('compact record size differs')
            record=compact_effect_records.unpack_record(body[off+start:off+start+size])
            if not compact_effect_records.eligible(record):raise ValueError('compact record consumer is not admitted')
        else:
            size=300
            if size>stop-start:raise ValueError('short raw record inside compact sequence')
            record=body[off+start:off+start+size]
        if i+1<count and size!=stop-start:raise ValueError('gap inside compact effect sequence')
        records.append((off+start,bool(value&1),record));expected=start+size
    if span-expected>=32 or any(body[off+expected:off+span]):raise ValueError('invalid compact effect padding')
    return records


def record_reference_namespace(record):
    """Known EspSeqSet dispatch; unknown generators retain conservative binding.

    IDs FC..FF use Tex_id as an Efm/scroll model index, not the ordinary
    Esp_tex_tbl image index. Generator00/02 spawn through the same EspSeqSet;
    other generators must keep their nominal binding until individually traced.
    """
    if record['sprite_id'] < 0xfc:return 'effect-texture'
    if record['kind']==0 or record['kind']==1 and record['generator_id'] in (0,2):
        return 'effect-model'
    return 'unresolved-generator-model-or-texture'


def effect(body,entry,index,*,separate_model_namespace=False):
    start,end=entry['off'],entry['end']
    if start+48>end:raise ValueError('short EFF header')
    h=struct.unpack_from('<12I',body,start)
    if h[0]!=11:raise ValueError('unsupported EFF version')
    def ids(rel):
        if not rel:return []
        at=start+rel;n=u32(body,at)
        if at<start+48 or n>(end-at-4)//8:raise ValueError('effect id table bounds')
        return [struct.unpack_from('<H',body,at+4+8*i)[0] for i in range(n)]
    def offsets(rel):
        if not rel:return []
        at=start+rel;n=u32(body,at)
        if at<start+48 or n>(end-at-4)//4:raise ValueError('effect offset table bounds')
        out=[at+u32(body,at+4+4*i) for i in range(n)]
        if any(o<at+4+4*n or o>=end for o in out):raise ValueError('effect target outside section')
        return out
    tex_ids,tpls=ids(h[1]),offsets(h[6])
    if len(tex_ids)!=len(tpls):raise ValueError('effect texture id/TPL counts differ')
    records=[]
    for kind,li,di in (('est',2,8),('sst',3,9)):
        names,starts=ids(h[li]),offsets(h[di])
        if len(names)!=len(starts):raise ValueError('effect sequence id/data counts differ')
        section_end=min([start+v for v in h[1:] if v>h[di]]+[end]) if h[di] else end
        sorted_starts=sorted(set(starts))
        for name,off in zip(names,starts):
            following=[s for s in sorted_starts if s>off]
            stop=min(following+[section_end])
            for i,(at,packed,record) in enumerate(sequence_records(body,off,stop,index)):
                if record[264] not in (0,1):raise ValueError('unexpected source effect record kind')
                records.append(dict(section=kind,sequence_id=name,sequence_offset=off,
                    record_index=i,record_offset=at,record_sha256=hashlib.sha256(record).hexdigest(),
                    compact=packed,kind=record[264],sprite_id=record[1],texture_id=record[2],
                    parts_no=record[7],screen_parts=0xf8<=record[7]<=0xfd,
                    tool_flags=u32(record,8),shimmer_type=record[195],mask_texture_id=record[197],
                    generator_id=record[265],size_base=struct.unpack_from('<2f',record,136)))
    image_records=([r for r in records if record_reference_namespace(r)!='effect-model']
                   if separate_model_namespace else records)
    result=dict(archive_entry=entry['index'],offset=start,
        textures=[dict(texture_id=tid,tpl_offset=tpl,records=[r for r in image_records if r['texture_id']==tid])
                  for tid,tpl in zip(tex_ids,tpls)],records=len(records))
    if separate_model_namespace:
        result['effect_model_references']=[dict(r,reference_namespace='effect-model',model_index=r['texture_id'])
                                          for r in records if record_reference_namespace(r)=='effect-model']
        result['unresolved_reference_namespaces']=[r for r in records
            if record_reference_namespace(r)=='unresolved-generator-model-or-texture']
    return result


def source_bindings(blob,*,separate_model_namespace=False):
    body,offset,entries=archive(blob);index=compact_index(body,entries)
    return dict(active_body_offset=offset,active_body_bytes=len(body),compact_sequences=len(index),
        effects=[effect(body,e,index,separate_model_namespace=separate_model_namespace) for e in entries if e['tag']==b'EFF'])


def record_sampling(record,common_sprite_ids,*,extended=False,contract_version=None):
    """Static texture sampling class, not a guarantee of actual drawing.

    Extended contracts are source-specific: Espgen00 emits the same record via
    EspSeqSet; Esp0b_Trans calls EspCommonTrans after position jitter. Esp11
    drives light state, Esp46 colour filters and Esp4a camera shake without
    sampling their record's texture. Esp4c also draws nothing itself but sets
    reflection texture state, so it deliberately remains a held consumer.
    Version 3 adds path emitter 02, whose EspSeqSet child retains the same record
    sampler; only position/size/speed/alpha change. Esp0c starts another EST and
    never samples its nominal texture. Earlier v1/v2 contracts stay unchanged.
    """
    version = (2 if extended else 1) if contract_version is None else contract_version
    if version not in (1,2,3):raise ValueError('unknown effect sampling contract version')
    extended = version >= 2
    ident=record['sprite_id'];kind=record['kind']
    generator=record['generator_id'] if kind==1 else 0
    emitter=kind==1 and (generator==0 or version>=3 and generator==2)
    if kind!=0 and not (extended and emitter):return 'hold-generator'
    if extended and (ident in (0x11,0x46,0x4a) or version>=3 and ident==0x0c):
        return 'no-record-texture-sampling'
    if record['screen_parts']:return 'hold-screen'
    if record['tool_flags']&(0x10000|0x4000|0x2000) or record['shimmer_type']:
        return 'hold-RTT-shimmer-or-negative'
    if ident not in common_sprite_ids and not (extended and ident==0x0b):return 'hold-custom-renderer'
    return ('common-world-sprite-emitter02' if generator==2 else 'common-world-sprite-emitter00') if emitter else 'common-world-sprite'
