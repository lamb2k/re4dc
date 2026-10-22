#!/usr/bin/env python3
"""Header-only canonical CRC repair and immutable rekey of selected WORLD36.

Never regenerate pixels, weaken a runtime check, mutate old assets, or write a
whole pack/image. Exact old payload proofs are reused by descriptor/payload SHA.
"""
from pathlib import Path
import hashlib,json,shutil,struct,sys,zlib
import prepare_r101 as p

SOURCES=[Path('/root/re4data/private/texture-rect21-scoped17-20261021'),Path('/root/re4data/private/texture-world-next21-r101-scoped9-v2-20261021'),Path('/root/re4data/private/texture-world-next21-r103-scoped10-20261021')]
INPUTS=p.EVID/'native-bindings-01/inputs'
HEADER=p.tpl.HEADER

def canonical(blob):
    h=list(HEADER.unpack_from(blob));p.require(h[:6]==[p.tpl.MAGIC,2,48,96,1,48] and len(blob)>=144,'exact selected schema')
    p.require(h[6]==144 and h[7]==len(blob)-144,'payload extent');stored=h[8];actual=zlib.crc32(blob[h[2]:])&0xffffffff
    p.require(stored in (actual,zlib.crc32(blob[h[6]:])&0xffffffff),'invalid input CRC (not valid legacy)')
    h[8]=actual;out=HEADER.pack(*h)+blob[HEADER.size:]
    p.require(out[:36]==blob[:36] and out[40:]==blob[40:],'canonical patch changed more than CRC word')
    return out,stored,actual

def original_world(room):
    path=INPUTS/('dc/native/%s/ps2-world.r4pw'%room);record=json.loads(p.FILES.read_text())['files']['/dc/native/%s/ps2-world.r4pw'%room];b=path.read_bytes();p.require(p.sha(b)==record['sha256'],'original world identity');return b,record

def geometry(room):
    record=json.loads(p.FILES.read_text())['files']['/dc/native/%s/ps2-world.re4mesh'%room];track=p.EVID/'standalone-B-01/gdemu/track03.iso'
    with track.open('rb') as f:f.seek((record['extent']-45000)*2048);b=f.read(record['bytes'])
    p.require(p.sha(b)==record['sha256'],'original geometry identity');mh=struct.unpack_from('<4s19I',b);p.require(mh[:3]==(b'R4IM',3,len(b)) and zlib.crc32(b[80:])&0xffffffff==mh[3],'geometry CRC');return mh,dict(source_track=str(track),**record)

def main():
    p.require(len(sys.argv)==3,'usage canonical_world36.py <new WSL output> <new C mirror>');out,mirror=map(Path,sys.argv[1:]);p.require(not out.exists() and not mirror.exists(),'preserve outputs')
    free=shutil.disk_usage('/mnt/c').free;p.require(free>=p.START_FLOOR+600*1024**2,'C start/peer guard')
    existing=p.pack_index(p.BASE);old_rows=[];receipt_pins=[]
    for root in SOURCES:
        raw=(root/'receipt.json').read_bytes();r=json.loads(raw);receipt_pins.append(dict(path=str(root/'receipt.json'),sha256=p.sha(raw)))
        for row in r['selected']:old_rows.append((root,row))
    p.require(len(old_rows)==36 and len({r['original_key'] for _,r in old_rows})==36 and len({r['scoped_key'] for _,r in old_rows})==36,'frozen36 scope')
    occupied=set(existing)|{p.key(r['scoped_key']) for _,r in old_rows}|{p.key(r['key']) for r in json.loads(p.COVERAGE.read_text())['loose_and_quality_rows']}|{(0x3662c0aa,0xc9e71c00),(0xfefdf580,0xf15c1f47)}
    p.require(p.hashed_file(p.COVERAGE)==p.COVERAGE_SHA,'collision ledger pin');selected=[];mapping={};packages={};table=[];patched=0
    for root,r in old_rows:
        old=(root/'textures'/(r['scoped_key']+'.re4tex')).read_bytes();p.require(p.sha(old)==r['candidate_sha256'],'frozen selected candidate identity')
        new,before,after=canonical(old);native=p.mip.read_native_vq(new);p.require(native.texture[3]==0 and native.texture[6]==4 and native.texture[7]==2,'selected opaque VQ mip contract')
        identity=p.scoped(p.key(r['original_key']),p.sha(new));same=identity==p.key(r['scoped_key']);p.require(same==(old==new),'SHA key migration semantics')
        if not same:p.require(identity not in occupied,'new canonical scoped identity collision')
        occupied.add(identity);p.require(identity not in packages,'duplicate canonical identity');packages[identity]=new;mapping[r['original_key']]=identity;patched+=not same
        lw,lh=r['logical'];w,h=native.texture[1:3];crc=HEADER.unpack_from(new)[8]
        table.append('{0x%08xU,0x%08xU,%dU,%dU,{%dU,%dU,0U,4U,2U,%dU,0x%08xU},1.0f,1.0f},'%(*identity,lw,lh,w,h,len(native.payload),crc))
        selected.append(dict(original_key=r['original_key'],old_scoped_key=r['scoped_key'],scoped_key=p.name(identity),old_candidate_sha256=p.sha(old),candidate_sha256=p.sha(new),source_sha256=r['source_sha256'],old_candidate_crc32=before,candidate_crc32=after,header_crc_only_changed=not same,changed_byte_offsets=[i for i,(a,b) in enumerate(zip(old,new)) if a!=b],logical=[lw,lh],physical=[w,h],uv_scale=[1.,1.],native_format=0,flags=4,payload=2,payload_bytes=len(native.payload),descriptor_payload_sha256=p.sha(old[48:]),texel_palette_payload_sha256=p.sha(old[144:]),descriptor_payload_byte_exact=True,codebook_pixels_mip_chain_uv_alpha_proofs_reused=True,prior_source_receipt=str(root/'receipt.json'),prior_source_receipt_sha256=p.hashed_file(root/'receipt.json'),prior_candidate_path=str(root/'textures'/(r['scoped_key']+'.re4tex')),strict_crc_before=before==(zlib.crc32(old[48:])&0xffffffff),strict_crc_after=True))
    p.require(patched==21 and len(packages)==36,'raw strict classification expected21legacy/15canonical')
    worlds=[];certs=[];cert_lines=[];bound=set();files={}
    for room in ['r100','r101','r103']:
        old,record=original_world(room);rows=p.world.inspect_sidecar(old);new=bytearray(old);changed=[]
        for row in rows:
            if row['key'] not in mapping:continue
            at=32+16*row['part'];target=mapping[row['key']];struct.pack_into('<II',new,at,*target);changed.append(dict(part=row['part'],original_key=row['key'],scoped_key=p.name(target),width=row['width'],height=row['height'],render_pass=row['render_pass'],flags=row['flags'],cull=row['cull'],texture=row['texture']));bound.add(row['key'])
        struct.pack_into('<I',new,20,zlib.crc32(new[32:])&0xffffffff);new=bytes(new);p.validate_rebind(old,new,mapping)
        wh=struct.unpack_from('<4s7I',old);mh,geom=geometry(room);p.require(mh[4:6]==(wh[4],wh[3]),'geometry/world counts');count={'r100':49,'r101':12,'r103':103}[room];p.require(len(changed)==count,'room changed-record scope')
        cert=dict(room=int(room[1:],16),world_bytes=len(new),placements=wh[2],parts=wh[3],meshes=wh[4],physical_body_crc=struct.unpack_from('<I',new,20)[0],physical_file_fnv=p.fnv(new),mesh_crc=mh[3],mesh_bytes=mh[2],source_crc=wh[5],source_world_sha256=record['sha256'],candidate_world_sha256=p.sha(new),mesh_sha256=geom['sha256'],changed_records=changed,unchanged_geometry_placements_materials=True)
        certs.append(cert);cert_lines.append('{0x%xU,%dU,%dU,%dU,%dU,0x%08xU,0x%08xU,0x%08xU,%dU,0x%08xU},'%(cert['room'],len(new),wh[2],wh[3],wh[4],cert['physical_body_crc'],cert['physical_file_fnv'],mh[3],mh[2],wh[5]))
        path='dc/native/'+room+'/ps2-world.r4pw';files[path]=new;worlds.append(dict(path=path,source_sha256=record['sha256'],candidate_sha256=p.sha(new),size=len(new),changed_parts=changed,geometry=geom,source_body_crc32=wh[5],candidate_body_crc32=cert['physical_body_crc']))
    p.require(bound==set(mapping),'all36 keys must have proved native material consumers')
    for k,b in packages.items():files['textures/'+p.name(k)+'.re4tex']=b
    files['proposed_representations.inc']=('// CanonicalCRC WORLD36 only; default-off integration owned by main.\n'+'\n'.join(table)+'\n').encode();files['proposed_provenance_certificates.inc']=('\n'.join(cert_lines)+'\n').encode()
    report=dict(schema='canonical-world36-crc-repair-1',status='DATA_PREPARED_STRICT_HOST_GATE_PENDING',scope='Selected36 only; canonical headerCRC/rekey/material-only rebuild. No pixel regeneration/runtime weakening.',input_receipt_pins=receipt_pins,header_schema='<8s10I',crc_field='Header.payload_crc32 / tpl.HEADER index8 / byte36..39',crc_scope='blob[Header.header_size(48):] descriptor plus payload',old_strict_rejects=21,old_strict_accepts=15,canonical_header_patches=21,new_scoped_ids=21,unchanged_scoped_ids=15,selected=selected,worlds=worlds,certificates=certs,changed_records_total=164,OP_records=160,VA_records=4,all_original_source_anchors_preserved=True,all_old_scoped_assets_and_seals_preserved=True,all_payload_descriptor_mip_palette_bytes_exact=True,redecoded_pixels=False,stale_gate_correction='Previous Package all_passed tested only the streamed final column and masked21 strict-adopt CRC failures. Those Package-admission PASS claims are superseded; old pixel/UV/alpha/geometry proofs remain reusable by exact payload identity.',allocation=dict(initial_C_free=free,cumulative_limit=32*1024**2,start_floor=p.START_FLOOR,runtime_floor=p.RUN_FLOOR,peer_reserve=600*1024**2),limits=['Canonicalbase948 andactor20 composition owned by atlas/main; do not compose over old36 to keep stale scoped IDs accidentally.','Apply original6501/currentcanonical948 base plus canonical36 appends and reviewed actor20replacements; preserve old packs as historical evidence.','No fullpack, image, programme, guest, target look/residency/performance/release/physical acceptance.'])
    files['receipt.json']=(json.dumps(report,indent=2)+'\n').encode();files['old-to-canonical-migration.json']=(json.dumps([dict(original_key=r['original_key'],old_scoped_key=r['old_scoped_key'],canonical_scoped_key=r['scoped_key'],old_sha256=r['old_candidate_sha256'],canonical_sha256=r['candidate_sha256'],old_header_crc=r['old_candidate_crc32'],canonical_header_crc=r['candidate_crc32'],payload_sha256=r['texel_palette_payload_sha256']) for r in selected],indent=2)+'\n').encode()
    p.require(sum(map(len,files.values()))*2<4*1024**2,'canonical delta/mirror<=4MiB forecast');p.require(shutil.disk_usage('/mnt/c').free-sum(map(len,files.values()))*2>=p.RUN_FLOOR,'C runtimefloor')
    for root in [out,mirror]:
        root.mkdir(parents=True)
        for path,b in files.items():
            target=root/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b)
        (root/'SHA256SUMS').write_text(''.join(p.sha(b)+'  '+path+'\n' for path,b in sorted(files.items())))
    p.require(all((out/s).read_bytes()==(mirror/s).read_bytes()==b for s,b in files.items()),'mirrored bytes exact')
    print(json.dumps(dict(selected=36,CRC_only_patches=21,new_scopedIDs=21,unchanged_scopedIDs=15,changed_material_records=164,logical_output_plus_mirror=sum(f.stat().st_size for root in [out,mirror] for f in root.rglob('*') if f.is_file()),worlds=[dict(path=r['path'],sha256=r['candidate_sha256']) for r in worlds])))
if __name__=='__main__':main()
