#!/usr/bin/env python3
"""Selectable em12 key residency via existing qualified source/FCV transport.

All FCV headers/joint identities, SEQ event tables, EFF behavior, meshes and ordinal
slots stay resident. Native key files are exact existing little-endian codec
output, consumed only through bounded source-motion evaluation leases. No clip
is removed because it was absent from a replay; original DRS remains untouched.
Optional upload-only textures use the existing NTR/shared native package path;
palettes, mip chains and unreviewed embedded EFM textures stay resident.
pl00/wep02 also support textures-only preparation, retaining every motion.
"""
from pathlib import Path
import argparse, hashlib, json, struct, tempfile, zlib
import le_mirror as mirror
import compact_effect_records as effects
from prepare_native_ui import compact_spans, select_upload_only, native_identity_index

MAGIC=b'R4MOTBL\0'
STRIDE=20
MAX_CLIP=32768
# Ganado modules link the shared em10.cpp (config/G4BE08/modules.py): same EFF slot0
# family, FCV/SEQ transport and source motion evaluators as em12 (frontier W1).
# em13 (r104's chapter 1-2 Ganados; native scene lane 2026-10-03): the same three units as em12/em15
# (config/G4BE08/modules.py: em13/em10.cpp, em10_tmpl.cpp, em13_set.cpp), so the same consumers. Its GC
# archive's 4,367,968 B body did not fit r104's heap 4 (DVD: Memory allocate failed, EmSetFromList2 Id=13).
# em17 (r108's chapter 1-3 Ganados, route lane c13): em17/em10.cpp, em10_tmpl.cpp, em17_set.cpp, the same three
# units; its GC archive did not fit r108's heap 4 next to the room and its PS2 world (route-c13-r102c).
GANADO=('em12.drs','em15.drs','em13.drs','em17.drs')
SMALL=('em26.drs','em28.drs','em21.drs','em2b.drs')
# Small enemies whose motions also leave the body: em21 (r100 trap dog) plays every clip through
# MotionSetCore/MotionMove (src/em21/em21.cpp; ARC() otherwise only feeds modelInit), the leased
# evaluators in motion.cpp. Needed for heap 4 in r100's post-house ambush (em21 + em23 + em2a).
# em23 (crows) passes its ARC motions only to MotionSetCore; em2a (traps) also reads a clip's
# frame count from the FCV header (*(u16*)ARC(0xB)), which stays resident, and lends its subArc
# to the player's trap motions (same leased evaluator). Their textures are not audited: motion only.
MOTION_SMALL=('em21.drs','em23.drs','em2a.drs','em2b.drs')
# em2b (El Gigante, r119; route lane r119 2026-10-10): every FCV it names goes to MotionSetCore, directly or through
# em2bBlendMotSet (two MotionSetCore calls; the blend work is evaluated by MotionMoveCore), MotSetObj16 (the
# parasite head and the tentacles: MotionSetCore) and plBlendMotSet / MotionSetCore on the player while it lends
# Leon its subArc (the grab). The one other FCV read is ARC(0xE2)'s header maxFrame (em2bTentacleSet), which
# stays resident. Textures: the top-level model TPLs (the four giant variants, the parasite, tentacles, chain,
# rock, the tree it uproots, the grabbed-player prop) go through modelInit / ModInfoMgr / SetObj16 / SetChain /
# SetRock; its EFF slot keeps its own textures. em2b is a ROUTE_OVL room overlay, so its static REL is stripped
# with the knob-conditional module set (ROUTE_OVL_MODULES). The room's heap 4: r119 frees 3,854,656 B in two
# cells, the largest 2,770,912 B, under the 4,689,664 B rel-stripped body.
ROUTE_OVL_MODULES=('em2b',)
# Leon's archives, textures-only: pl00 (jacket, costume 0) and pl08 (no jacket, costume 1: title.cpp picks it in
# every room but r120/r100/r101/r103/r106 once the r106 closet event has run). Same cPlLeon consumers, so pl08
# takes pl00's reviewed textures-only contract (route lane 2026-10-01, r104).
LEON=('pl00.drs','pl08.drs')

def prepare(source, destination, hot_slots=(), textures=None, keep_motion_resident=False, compact_effects=False):
    source,destination=map(Path,(source,destination))
    name=source.name.lower();file='em/'+name
    if name not in GANADO+SMALL+MOTION_SMALL+LEON+('wep02.drs',) or (name not in GANADO+MOTION_SMALL and not keep_motion_resident):
        raise ValueError('supported contracts: Ganado (em12/em15/em13) and em21/em23/em2a motion; em26/em28/em21/pl00/pl08/wep02 textures')
    if textures is not None and name not in GANADO+SMALL+LEON+('wep02.drs',):raise ValueError('textures not audited for '+name)
    if compact_effects and name not in GANADO+SMALL:raise ValueError('only enemy EFF slot0 effect consumers qualified')
    if keep_motion_resident and textures is None and not compact_effects:raise ValueError('no selected compaction')
    if destination.exists():raise FileExistsError(destination)
    hot_slots=set(hot_slots)
    original=source.read_bytes();converted=bytearray(original);refs=[];palettes=[];sequences=[]
    old=mirror.OFFSET_OBSERVER;old_tpl=mirror.TPL_OBSERVER;old_seq=mirror.SEQUENCE_OBSERVER;start=len(mirror.REPORT)
    mirror.OFFSET_OBSERVER=lambda file,field,base,value:refs.append((field,base,value))
    mirror.TPL_OBSERVER=lambda file,off,data,ctx:palettes.append((off,data,ctx))
    mirror.SEQUENCE_OBSERVER=lambda file,off,data,ctx:sequences.append((off,data,ctx))
    try:mirror.convert_file(file,converted)
    finally:mirror.OFFSET_OBSERVER=old;mirror.TPL_OBSERVER=old_tpl;mirror.SEQUENCE_OBSERVER=old_seq
    coverage=mirror.REPORT[start:]
    with tempfile.NamedTemporaryFile(mode='w') as required:
        required.write(file+'\n');required.flush()
        bad=mirror.check_required(coverage,required.name)
    if bad:raise ValueError('unqualified enemy: '+', '.join(bad))
    # Retain the already-implemented static REL policy; don't restore PPC code.
    converted=mirror.compact_static_rel(file,converted,coverage,mirror.static_module_ids(
        tuple(m for m in ROUTE_OVL_MODULES if m==source.stem.lower())))
    slot=mirror.native_payload_slot(converted)
    size,base=struct.unpack_from('<I4xI',converted,slot+4)
    body=converted[base:base+size]
    count,rel=struct.unpack_from('<2I',body)
    boundary=rel or len(body)
    offsets=struct.unpack_from('<%dI'%count,body,16)
    tags=[bytes(body[16+4*count+4*i:20+4*count+4*i]) for i in range(count)]
    first=min(x for x in offsets if x)
    effect_ranges,effect_entries=effects.prepare_sequences(
        [(o-base,d,c) for o,d,c in sequences if base<=o<base+boundary],file+':0#0') if compact_effects else ([],[])
    if compact_effects and not effect_entries:raise ValueError('no eligible effect sequences')
    extra_slots=int(not keep_motion_resident)+int(textures is not None)+int(bool(effect_entries))
    header_growth=(max(0,16+8*(count+extra_slots)-first)+31)&~31
    texture_ranges=[];selected=[];retained=[]
    if textures is not None:
        # Only top-level player/weapon TPLs are selected. Enemy EFF slot0
        # retains D326's separate texture-ID/noise audit; no new EFF family is
        # automatically qualified by this filename extension.
        top_tpl={file+':0#'+str(i) for i,t in enumerate(tags) if t==b'TPL\0'}
        ids=[]
        if name in GANADO:
            if tags[0]!=b'EFF\0':raise ValueError('em12 effect family changed')
            eff=offsets[0];ids_at=eff+struct.unpack_from('<I',body,eff+4)[0]
            num_ids=struct.unpack_from('<I',body,ids_at)[0]
            ids=[struct.unpack_from('<H',body,ids_at+4+i*8)[0] for i in range(num_ids)]
        def allowed(ctx):
            if ctx in top_tpl:return True
            if name in GANADO and ctx.startswith(file+':0#0/tpl'):
                i=int(ctx.rsplit('tpl',1)[1]);return i<len(ids) and ids[i]!=0xfe
            return False
        local_palettes=[(o-base,d,c) for o,d,c in palettes if base<=o<base+boundary]
        texture_ranges,selected,retained=select_upload_only(body,local_palettes,Path(textures),allowed)
        if not texture_ranges:raise ValueError('no qualified enemy textures selected')
    if rel and rel+64!=len(body):raise ValueError('expected retained 64-byte static REL descriptor')
    original_size,original_base=struct.unpack_from('>I4xI',original,slot+4)
    codec=mirror.motion_codec();ranges=[];entries=[];files={};oversized=[]
    for off in ([] if keep_motion_resident else sorted(set(offsets))):
        if not off:continue
        slots=[i for i,o in enumerate(offsets) if o==off]
        if tags[slots[0]]!=b'FCV\0':continue
        if any(tags[i]!=b'FCV\0' for i in slots):raise ValueError('mixed-tag alias')
        end=min([o for o in offsets if o>off]+[boundary])
        raw=original[original_base+off:original_base+end]
        parsed=codec.parse(raw)
        if codec.serialise(parsed)!=raw:raise ValueError('source FCV roundtrip differs')
        native=codec.serialise(parsed,'<')
        if native!=body[off:end]:raise ValueError('native FCV differs from qualified archive')
        if not parsed.joints:continue # empty motion is already 32 bytes; keep ordinary
        if len(native)>MAX_CLIP:
            # em21: a clip over the runtime's slot limit stays resident (ordinary FCV, exact bytes);
            # the Ganado contract keeps refusing, as before.
            if name in MOTION_SMALL:oversized.append({'source_arc_indices':[i+4 for i in slots],'bytes':len(native)});continue
            raise ValueError('clip exceeds validated cache slot')
        prefix=codec.header_size(len(parsed.joints));resident=(prefix+31)&~31
        if resident>=len(native):continue
        crc=zlib.crc32(native)&0xffffffff
        fnv=2166136261
        for byte in native:fnv=((fnv^byte)*16777619)&0xffffffff
        key='%08x-%08x'%(crc,fnv)
        if key in files and files[key]!=native:raise ValueError('motion identity collision')
        files[key]=native
        ranges.append((off,end,native[:prefix]+bytes(resident-prefix)))
        entries.append({'source_offset':off,'slots':slots,'bytes':len(native),'prefix_bytes':prefix,
                        'resident_bytes':resident,'hot':bool(hot_slots.intersection(i+4 for i in slots)),'source_arc_indices':[i+4 for i in slots],'key':key,'crc':crc,'fnv':fnv,
                        'sha256':hashlib.sha256(native).hexdigest(),'classification':'reloadable key data; stable header retained'})
    if not entries and not keep_motion_resident:raise ValueError('no qualified motion payloads')
    ranges=sorted(ranges+texture_ranges+effect_ranges)
    local_refs=[(f-base,b-base,v) for f,b,v in refs if base<=f<base+boundary]
    # Existing fmt_drs_body preserves this scalar; it is also an archive-relative
    # boundary and must follow the moved static REL, unlike per-FCV key offsets.
    if rel:local_refs.append((4,0,rel))
    if header_growth:ranges.insert(0,(first,first,bytes(header_growth)))
    out,mapped=compact_spans(body,local_refs,ranges)
    # Insert MTC before the static module so readEmData's data/REL split stays true.
    new_rel=mapped(boundary);table=bytearray()
    for e in entries:
        e['resident_offset']=mapped(e['source_offset'])
        table+=struct.pack('<5I',e['resident_offset'],e['bytes'],e['crc'],e['fnv'],int(e['hot']))
    table_bytes=((32+len(table)+31)&~31) if entries else 0
    texture_index_bytes=((32+12*len(selected)+31)&~31) if selected else 0
    effect_index_bytes=((32+12*len(effect_entries)+31)&~31) if effect_entries else 0
    final_bytes=len(out)+table_bytes+texture_index_bytes+effect_index_bytes
    tables=bytearray();new_tags=[];new_offsets=[]
    if effect_entries:
        new_tags.append(b'ESQ\0');new_offsets.append(new_rel)
        tables+=effects.identity_index(effect_entries,mapped,final_bytes)
    if selected:
        new_tags.append(b'NTR\0');new_offsets.append(new_rel+len(tables))
        tables+=native_identity_index(selected,mapped,len(body),final_bytes)
    if entries:
        new_tags.append(b'MTC\0');new_offsets.append(new_rel+len(tables))
        header=struct.pack('<8s6I',MAGIC,2,len(entries),STRIDE,zlib.crc32(table)&0xffffffff,final_bytes,MAX_CLIP)
        tables+=header+table+bytes(table_bytes-32-len(table))
    out=out[:new_rel]+tables+out[new_rel:]
    struct.pack_into('<2I',out,0,count+extra_slots,new_rel+len(tables) if rel else 0)
    for i,off in enumerate(new_offsets):struct.pack_into('<I',out,16+4*(count+i),off)
    out[16+4*(count+extra_slots):16+8*(count+extra_slots)]=b''.join(tags+new_tags)
    # Every non-FCV archive family and module descriptor retains exact bytes.
    for off in sorted(set(offsets)):
        if not off:continue
        end=min([o for o in offsets if o>off]+[boundary])
        if (keep_motion_resident or tags[list(offsets).index(off)]!=b'FCV\0') and not any(off<=a<end for a,b,_ in texture_ranges+effect_ranges):
            assert out[mapped(off):mapped(end)]==body[off:end]
    if rel:assert out[-64:]==body[-64:]
    packaged=mirror.replace_native_payload(converted,out)
    report={'contract':source.stem+'-native-textures-v1' if keep_motion_resident else source.stem+'-source-motion-cache-v2','source_sha256':hashlib.sha256(original).hexdigest(),
            'original_static_body_bytes':size,'resident_body_bytes':len(out),
            'archive_recovery_bytes':size-len(out),'index_bytes':table_bytes,'header_growth_bytes':header_growth,
            'motion_source_bytes':sum(e['bytes'] for e in entries),'motion_header_bytes':sum(e['resident_bytes'] for e in entries),
            'motions_resident':keep_motion_resident,
            'effects':{'entries':effect_entries,'index_bytes':effect_index_bytes,
                'recovery_bytes':sum(b-a-len(v) for a,b,v in effect_ranges)-effect_index_bytes,
                'policy':'all records resident; exact native word reconstruction, stable retained generator references'},
            'textures':{'selected':selected,'retained':retained,'identity_table_bytes':texture_index_bytes,
                'removed_payload_bytes':sum(b-a for a,b,_ in texture_ranges),
                'replacement_record_bytes':32*len(texture_ranges)},
            'max_clip_bytes':max((e['bytes'] for e in entries),default=0),'oversized_resident':oversized,
            'hot_payload_bytes':sum(e['bytes'] for e in entries if e['hot']),
            'cold_reserve_bytes':2*max((e['bytes'] for e in entries if not e['hot']),default=0),
            'cache_policy':None if keep_motion_resident else 'retain hot set and LRU cold entries until capacity pressure; evaluation release never evicts','entries':entries,'qualification':coverage,
            'retained':'all SEQ events, EFF behavior tables, CPU/palette/mip texels, models/materials/skeletons and exact FCV headers',
            'lifetime':'all motions remain source-owned; native identity views follow archive ownership' if keep_motion_resident else 'keys remain cached; pins protect source MotionSetCore, MotionMoveCore, MotionGetSpeed and MotionGetPosition; header/SEQ pointers remain source-archive-owned',
            'limits':'offline contract only until native binding, source consumer lifetimes, actual heap and visible output are qualified; motion selection also requires complete prefetch/concurrency audit'}
    destination.mkdir();(destination/'mot').mkdir()
    for key,data in files.items():(destination/'mot'/(key+'.fcv')).write_bytes(data)
    (destination/name).write_bytes(packaged)
    (destination/(source.stem+'.arc')).write_bytes(out)
    (destination/'motion-residency-report.json').write_text(json.dumps(report,indent=2)+'\n')
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True,type=Path);p.add_argument('--output',required=True,type=Path)
    p.add_argument('--hot-audit',type=Path,help='Source-derived diagnostic hot-set audit; not a replay usage filter')
    p.add_argument('--diagnostic-incomplete-prefetch',action='store_true',help='Allow a clearly labelled source-audit diagnostic, never production qualification')
    p.add_argument('--textures',type=Path,help='Existing exact native texture packages; externalize reviewed upload-only enemy texels')
    p.add_argument('--keep-motion-resident',action='store_true',help='Texture-only selection retains every FCV payload; no motion cache')
    p.add_argument('--compact-effects',action='store_true',help='Selectable lossless resident em12 EST records; original heads and all effect behavior retained')
    a=p.parse_args()
    if not a.keep_motion_resident and not a.hot_audit:p.error('--hot-audit is required for motion residency')
    audit=json.loads(a.hot_audit.read_text()) if a.hot_audit else {}
    if not a.keep_motion_resident and not audit.get('source_complete') and not a.diagnostic_incomplete_prefetch:
        p.error('prefetch/concurrency audit is incomplete; explicit diagnostic selection required')
    r=prepare(a.source,a.output,audit.get('union',{}).get('source_arc_indices',()),a.textures,a.keep_motion_resident,a.compact_effects)
    report_path=a.output/'motion-residency-report.json'
    r['prefetch_audit']=audit
    r['runtime_qualified']=False
    report_path.write_text(json.dumps(r,indent=2)+'\n')
    print('em12 resident body',r['original_static_body_bytes'],'->',r['resident_body_bytes'],'motion entries',len(r['entries']),'hot + cold cap',r['hot_payload_bytes']+r['cold_reserve_bytes'])
