#!/usr/bin/env python3
"""Prepare the next assessed ten r103 rectangles, preserving the frozen994 arm."""
from pathlib import Path
import ctypes,hashlib,json,shutil,struct,sys,zlib
import prepare_r101 as p

E=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/texture-world-next21-r103-20261021')
COHORT=E/'source-cohort-01'
MANIFEST=Path('/root/re4data/private/texture-combined994-plan-v2-20261021/COMBINED994-MANIFEST.json')
MANIFEST_SHA='df730880a3db9c580e3a5615df54b9060cca915ae9701d3dcb002fe92a9d0dc6'
INPUT=Path('/root/re4data/private/texture-rect21-current948-scoped17-20261021/dc/native/r103/ps2-world.r4pw')
ORIGINAL=p.EVID/'native-bindings-01/inputs/dc/native/r103/ps2-world.r4pw'
OLD_SCOPE=Path('/root/re4data/private/texture-rect21-scoped17-20261021/receipt.json')

def mesh():
    record=json.loads(p.FILES.read_text())['files']['/dc/native/r103/ps2-world.re4mesh']
    track=p.EVID/'standalone-B-01/gdemu/track03.iso'
    with track.open('rb') as f:f.seek((record['extent']-45000)*2048);b=f.read(record['bytes'])
    p.require(p.sha(b)==record['sha256'],'r103 geometry identity');mh=struct.unpack_from('<4s19I',b)
    p.require(mh[:3]==(b'R4IM',3,len(b)) and zlib.crc32(b[80:])&0xffffffff==mh[3],'r103 geometry CRC/header')
    return b,mh,dict(path='/dc/native/r103/ps2-world.re4mesh',source_track=str(track),**record)

def inherited994():
    raw=MANIFEST.read_bytes();p.require(p.sha(raw)==MANIFEST_SHA,'frozen994 manifest identity');m=json.loads(raw)
    p.require(m['virtual']['pack_sha256']=='7ed1984d180bfa81978d979d3b37b687e44eba0fdf5782c1b26b472337cae22f' and m['virtual']['global_members']==6527,'994 frozen parent')
    paths={}
    for row in m['per_key_bindings']:
        b=Path(row['candidate']['path']).read_bytes();p.require(p.sha(b)==row['candidate']['sha256'] and len(b)==row['candidate']['bytes'],'parent candidate identity')
        k=p.key(row['key']);p.require(k not in paths,'duplicate994 override');paths[k]=(Path(row['candidate']['path']),row['family'])
    p.require(len(paths)==29,'994 component scope');return m,paths

def virtual1004(base,index,parent_paths,added):
    keys=sorted(set(index)|set(parent_paths)|set(added));p.require(len(keys)==6537,'1004 global members')
    data=2048+((len(keys)*16+2047)//2048)*2048;at=data;ix=bytearray()
    def blob(f,k):
        return added[k] if k in added else parent_paths[k][0].read_bytes() if k in parent_paths else p.read_member(f,index,k)
    with base.open('rb') as f:
        for k in keys:
            n=len(blob(f,k));ix+=struct.pack('<4I',*k,at,n);at+=((n+2047)//2048)*2048
        ix+=bytes(data-2048-len(ix));header=b'RE4PAK1\0'+struct.pack('<5I',1,len(keys),2048,data,zlib.crc32(ix)&0xffffffff);header+=bytes(2048-len(header));h=hashlib.sha256(header+ix);members=[];mips=0
        for k in keys:
            b=blob(f,k);h.update(b);h.update(bytes((-len(b))%2048));mips+=bool(p.tpl.TEXTURE.unpack_from(b,48)[6]&4)
            kind='r103-ten' if k in added else parent_paths[k][1] if k in parent_paths else 'base-preserved'
            members.append(dict(key=p.name(k),bytes=len(b),sha256=p.sha(b),kind=kind,source_path=str(parent_paths[k][0]) if k in parent_paths else None))
    p.require(mips==1004,'composed mip total')
    return dict(parent_manifest_sha256=MANIFEST_SHA,parent_virtual_pack_sha256='7ed1984d180bfa81978d979d3b37b687e44eba0fdf5782c1b26b472337cae22f',parent_members=6527,parent_mips=994,candidate_members=6537,candidate_mips=mips,index_sectors=52,previous_index_sectors=51,runtime_index_sector_capacity=64,index_crc32=zlib.crc32(ix)&0xffffffff,data_offset=data,expected_pack_sha256=h.hexdigest(),expected_pack_bytes=at,archive_delta_from994=at-156164096,base_members_preserved_exact=6498,inherited_actor_replacements=20,inherited_r101_additions=9,new_r103_additions=10,full_pack_written=False,members=members)

def main():
    p.require(len(sys.argv)==3,'usage: prepare_r103.py <new WSL output> <new C mirror>');out,mirror=map(Path,sys.argv[1:]);p.require(not out.exists() and not mirror.exists(),'preserve output')
    free=shutil.disk_usage('/mnt/c').free;p.require(free>=p.START_FLOOR+600*1024**2,'freshC+conservativepeer600MiB')
    parent,parent_paths=inherited994();index=p.pack_index(p.BASE);p.require(p.hashed_file(p.BASE)==p.BASE_SHA and len(index)==6518,'existing written965 base')
    prior=INPUT.read_bytes();original=ORIGINAL.read_bytes();prior_scope=json.loads(OLD_SCOPE.read_text());prior_world=next(r for r in prior_scope['worlds'] if '/r103/' in r['path'])
    p.require(p.sha(prior)==prior_world['candidate_sha256'] and p.sha(original)==prior_world['source_sha256'],'preserve prior17 r103 world identity')
    before=p.world.inspect_sidecar(original);current=p.world.inspect_sidecar(prior);prior_map={r['original_key']:p.key(r['scoped_key']) for r in prior_scope['selected']};p.validate_rebind(original,prior,prior_map)
    existing_rows=[i for i,(a,b) in enumerate(zip(before,current)) if a['key']!=b['key']];p.require(len(existing_rows)==29,'prior29r103 row preservation')
    source_raw=(COHORT/'receipt.json').read_bytes();source=json.loads(source_raw);p.require(source['room']=='r103' and len(source['selected'])==10 and source['independent_mip_decodes']==80 and source['held']==[],'ten assessed compatible converters')
    p.require(source['queue_sha256']=='06bac8fb1d09669e69dbc50a5acfa06981a52d6a674ca9e63f487f659d4cab58' and source['bindings_sha256']=='e24a1ee4150c91f1228879f92bb9e6e934176fc6d3c1011f45c265ea8d606003' and source['oracle_sha256']==p.ORACLE_SHA,'existing assessed queue/bindings/oracle pins')
    occupied=set(index)|set(parent_paths)|{p.key(r['key']) for r in json.loads(p.COVERAGE.read_text())['loose_and_quality_rows']}|{(0x3662c0aa,0xc9e71c00),(0xfefdf580,0xf15c1f47)}
    mapping={};added={};selected=[];lib=ctypes.CDLL(str(p.ORACLE));p.require(p.hashed_file(p.ORACLE)==p.ORACLE_SHA and p.hashed_file(p.COVERAGE)==p.COVERAGE_SHA,'oracle/collision ledger pin')
    with p.BASE.open('rb') as f:
        for row in source['selected']:
            old=p.read_member(f,index,p.key(row['key']));b=(COHORT/'packages'/(row['key']+'.re4tex')).read_bytes();n=p.validate_pair(old,b,row);new=p.scoped(p.key(row['key']),p.sha(b));p.require(new not in occupied,'immutable key collision');occupied.add(new);mapping[row['key']]=new;added[new]=b
            proof=p.decode_proof(lib,old,n);p.require(abs(proof['base_rgb_rmse']-row['source_texel_center_rgb_rmse'])<1e-9,'filtered base decoder agreement')
            selected.append(dict(original_key=row['key'],scoped_key=p.name(new),source_sha256=p.sha(old),candidate_sha256=p.sha(b),candidate_crc32=n.header[8],logical=[256,128],physical=[128,128],native_format=0,flags=4,payload=2,payload_bytes=7510,source_payload_bytes=10240,rounded_original=10240,rounded_candidate=7520,codebook_exact=True,**proof))
    new_world,changed=p.rebind(prior,mapping);p.require(len(changed)==74,'expected new74 material rows');combined_map=dict(prior_map,**mapping);p.validate_rebind(original,new_world,combined_map)
    p.require(all(prior[32+16*i:48+16*i]==new_world[32+16*i:48+16*i] for i in existing_rows),'prior scoped29 rows changed')
    p.require({c['original_key'] for c in changed}==set(mapping),'missing new scoped binding')
    geometry,mh,geometry_proof=mesh();wh=struct.unpack_from('<4s7I',original);p.require(mh[4:6]==(wh[4],wh[3]),'world/geometry counts')
    cert=dict(room=0x103,world_bytes=len(new_world),placements=wh[2],parts=wh[3],meshes=wh[4],physical_body_crc=struct.unpack_from('<I',new_world,20)[0],physical_file_fnv=p.fnv(new_world),mesh_crc=mh[3],mesh_bytes=len(geometry),source_crc=wh[5],original_world_sha256=p.sha(original),parent994_world_sha256=p.sha(prior),candidate_world_sha256=p.sha(new_world),mesh_sha256=p.sha(geometry),new_changed_records=[c['part'] for c in changed],inherited_scoped29_rows_preserved=existing_rows,cumulative_r103_changed_records=103,unchanged_geometry_placements_material_pass_cull_alpha=True)
    composition=virtual1004(p.BASE,index,parent_paths,added)
    table=['// PROPOSED NEXT r103 ten; current994 table remains frozen.']
    for r in selected:
        a,b=p.key(r['scoped_key']);table.append('{0x%08xU,0x%08xU,256U,128U,{128U,128U,0U,4U,2U,7510U,0x%08xU},1.0f,1.0f},'%(a,b,r['candidate_crc32']))
    certline='{0x103U,%dU,%dU,%dU,%dU,0x%08xU,0x%08xU,0x%08xU,%dU,0x%08xU},\n'%(cert['world_bytes'],cert['placements'],cert['parts'],cert['meshes'],cert['physical_body_crc'],cert['physical_file_fnv'],cert['mesh_crc'],cert['mesh_bytes'],cert['source_crc'])
    report=dict(schema='re4dc-next1004-r103-ten-1',scope='Separate NEXT cohort. Frozen994 inputs/programme qualification stay unchanged.',source_baseline='845abb1f4ad3a2721d17f64899b6dc59d4bce66c',parent_manifest_sha256=MANIFEST_SHA,parent_virtual_pack_sha256=parent['virtual']['pack_sha256'],source_converter_receipt_sha256=p.sha(source_raw),existing_queue_sha256=source['queue_sha256'],existing_bindings_sha256=source['bindings_sha256'],converter='existing room_cohort.py/compact.shorter_square + mipmap_vq.add_mipmaps',selected=selected,changed_bindings=changed,certificate=cert,geometry=geometry_proof,all_prior17_and_r1019_preserved=True,prior_r10329_scoped_bindings_byte_exact=True,proposed_certificate_coexistence='Retain current3 certificates and append this4th distinct physical r103 certificate so994 and1004 can share reviewed source; original r103 source anchor unchanged.',independent_decoded_levels=80,source_rounded=102400,candidate_rounded=75200,request_delta=-27200,held=[],dependencies={str(x):p.hashed_file(x) for x in [Path(__file__),Path(p.__file__),p.RECT/'room_cohort.py',p.RECT/'compact.py',p.ROOT/'tools/mipmap_vq.py',p.ROOT/'tools/convert_tpl.py']},limits=['Existing assessed792 queue filtered for one already-compatible cohort; no full6501 reassessment.','RGB base filtered/requantized; original codebooks/opaque alpha/normalized native repeatUV preserved. Original TPL wrap flags are not inferred.','Currentwritten965/frozenvirtual994 remain unchanged. 1004 is prepared virtual only.','Actual new package host/metadata/helper gates must pass separately; no target draw/look/residency/performance/release/hardware acceptance.','Original metadata stays byteexact with reviewed semantic source CRC; no forged physical or dependency CRC.'])
    files={'receipt.json':(json.dumps(report,indent=2)+'\n').encode(),'virtual-composition1004.json':(json.dumps(composition,indent=2)+'\n').encode(),'proposed_representations.inc':('\n'.join(table)+'\n').encode(),'proposed_provenance_certificate.inc':certline.encode(),'dc/native/r103/ps2-world.r4pw':new_world}
    files.update({'textures/'+p.name(k)+'.re4tex':b for k,b in added.items()});p.require(2*sum(map(len,files.values()))+8*1024**2<=32*1024**2,'new unit32MiB output bound');p.require(shutil.disk_usage('/mnt/c').free-2*sum(map(len,files.values()))>=p.RUN_FLOOR,'runtime floor')
    for root in [out,mirror]:
        root.mkdir(parents=True)
        for relative,b in files.items():
            target=root/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b)
        (root/'SHA256SUMS').write_text(''.join(p.sha(b)+'  '+relative+'\n' for relative,b in sorted(files.items())))
    p.require(all(p.hashed_file(out/s)==p.hashed_file(mirror/s)==p.sha(b) for s,b in files.items()),'exact mirror')
    print(json.dumps(dict(new_keys=10,new_bindings=74,inherited_r103_bindings_preserved=29,decoded_levels=80,current_frozen_parent_mips=994,proposed_next_mips=1004,virtual_pack_sha256=composition['expected_pack_sha256'],virtual_pack_bytes=composition['expected_pack_bytes'],index_sectors=52,output_and_mirror_bytes=sum(pth.stat().st_size for r in [out,mirror] for pth in r.rglob('*') if pth.is_file()),certificate=cert)))
if __name__=='__main__':main()
