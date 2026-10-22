#!/usr/bin/env python3
"""Strict actual Package gates; require BOTH adopt and checked stream success."""
from pathlib import Path
import hashlib,json,os,shutil,struct,subprocess,sys,zlib
import prepare_r101 as p
import canonical_world36 as c

HOST=Path('/root/re4data/private/texture-actors21-compose20-current965-v2-20261021/host02')

def main():
    out=Path(sys.argv[1]);work=Path(sys.argv[2]);p.require(not work.exists(),'preserve host outputs');work.mkdir(parents=True)
    raw=(out/'receipt.json').read_bytes();r=json.loads(raw);canonical_paths=[out/'textures'/(x['scoped_key']+'.re4tex') for x in r['selected']];old_paths=[Path(x['prior_candidate_path']) for x in r['selected']]
    sourceids=[]
    for relative in ['reader.cpp','texture_package.cpp','texture_package.hpp','room_storage.cpp','room_storage.hpp']:
        original=HOST/relative;data=original.read_bytes()
        if relative!='reader.cpp':p.require(data==(p.ROOT/'room'/relative).read_bytes(),'actual Package source changed '+relative)
        (work/relative).write_bytes(data);sourceids.append(dict(path=relative,sha256=p.sha(data),bytes=len(data)))
    for original in HOST.glob('*.h'):shutil.copyfile(original,work/original.name)
    for dirname in ['dc','kos']:shutil.copytree(HOST/dirname,work/dirname)
    subprocesses=[];env=dict(os.environ,ASAN_OPTIONS='detect_leaks=1:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')
    arms=[]
    for ui in [0,1]:
        for mip in [0,1]:
            arm='ui%d-mip%d-crc1'%(ui,mip);exe=work/arm;command=['g++','-std=c++17','-O1','-g0','-fsanitize=address,undefined','-fno-omit-frame-pointer','-no-pie','-DRE4DC_STORAGE_BOUNCE_BYTES=16384','-DRE4DC_PVR_PIPELINE=1','-DRE4DC_TEX_RESIDENT=1','-DRE4DC_TEX_PAYLOAD_CRC=1','-DRE4DC_UI_VRAM='+str(ui),'-DRE4DC_CAST_MIPMAP='+str(mip),'-I'+str(work),str(work/'reader.cpp'),str(work/'texture_package.cpp'),str(work/'room_storage.cpp'),'-o',str(exe)]
            build=subprocess.run(command,capture_output=True,text=True);p.require(build.returncode==0,build.stderr)
            run=subprocess.run([str(exe),*map(str,canonical_paths)],capture_output=True,text=True,env=env);p.require(run.returncode==0 and not run.stderr,run.stderr)
            lines=[s.split('|') for s in run.stdout.splitlines()];p.require(len(lines)==36,'actual36 cases')
            for columns in lines:
                if mip:p.require(columns[1:3]==['ok','ok'],'strict adopt/stream must BOTH accept '+str(columns[:3]));p.require(int(columns[3])&0xc0000000==0xc0000000,'VQ/mip format')
                else:p.require(columns[1:3]==['invalid texture dimensions, format, layout or payload size']*2,'mipOFF actual payload-size contract rejection')
            legacy=[]
            if mip:
                old=subprocess.run([str(exe),*map(str,old_paths)],capture_output=True,text=True,env=env);p.require(old.returncode==0 and not old.stderr,old.stderr)
                old_lines=[s.split('|') for s in old.stdout.splitlines()];p.require(len(old_lines)==36,'old36 classifier')
                for row,cols in zip(r['selected'],old_lines):
                    expected=['ok','ok'] if row['strict_crc_before'] else ['payload CRC mismatch','streamed payload read or CRC mismatch']
                    p.require(cols[1:3]==expected,'old strict classification '+str(cols[:3]));legacy.append(dict(old_key=row['old_scoped_key'],adopt=cols[1],stream=cols[2],strict_crc_before=row['strict_crc_before']))
            arms.append(dict(arm=arm,command=command,exe_sha256=p.hashed_file(exe),exe_bytes=exe.stat().st_size,canonical_results=lines,old36_strict_results=legacy,stdout=run.stdout,sanitizer_stderr=run.stderr))
    # The normal reader returns0 even for CRC rejection; positive checks above
    # inspect both columns. Independently corrupt payloads to prove CRC1 lives.
    mutations=[];probe=work/'ui0-mip1-crc1'
    for index in [0,17,26]:
        b=bytearray(canonical_paths[index].read_bytes());b[-1]^=1;target=work/('corrupt-payload-'+str(index)+'.re4tex');target.write_bytes(b)
        run=subprocess.run([str(probe),str(target)],capture_output=True,text=True,env=env);p.require(run.returncode==0 and not run.stderr,run.stderr);columns=run.stdout.strip().split('|');p.require(columns[1:3]==['payload CRC mismatch','streamed payload read or CRC mismatch'],'corrupt payload both strictpaths');mutations.append(dict(case=index,result=columns[1:3]))
    # Confirm all three rebuilt worlds differ only in key words/physical CRC;
    # original metadata identities and semantic class anchors stay unchanged.
    mapping={x['original_key']:p.key(x['scoped_key']) for x in r['selected']};meta=[];classes_OP=0;classes_VA=0
    file_manifest=json.loads(p.FILES.read_text())['files'];track=p.EVID/'standalone-B-01/gdemu/track03.iso'
    def existing(room,leaf):
        ident=file_manifest['/dc/native/'+room+'/'+leaf]
        with track.open('rb') as f:f.seek((ident['extent']-45000)*2048);data=f.read(ident['bytes'])
        p.require(p.sha(data)==ident['sha256'],'original metadata pin');return data,ident
    for room,world in zip(['r100','r101','r103'],r['worlds']):
        old,_=c.original_world(room);new=(out/world['path']).read_bytes();p.validate_rebind(old,new,mapping);source_crc=world['source_body_crc32'];tc,tcid=existing(room,'ps2-world.r4tc');th=struct.unpack_from('<4s5I',tc);p.require(th[:2]==(b'R4TC',1) and th[3]==len(p.world.inspect_sidecar(old)) and th[4]==source_crc and zlib.crc32(tc[24:24+th[3]])&0xffffffff==th[5],'class source anchor/CRC')
        for row in world['changed_parts']:
            expected=9 if row['flags']&1 else 1;p.require(tc[24+row['part']]==expected,'original OP/VA class must remain valid');classes_VA+=expected==9;classes_OP+=expected==1
        ids_blob,idid=existing(room,'ps2-world.ids');ih=struct.unpack_from('<4s3I',ids_blob);p.require(ih[:2]==(b'R4ID',1) and ih[3]==source_crc,'ID source anchor')
        rc,rcid=existing(room,'room.r4rc');n=struct.unpack_from('<I',rc,12)[0];occl=False
        for i in range(n):
            tag,version,flags,at,size=struct.unpack_from('<4sHHII',rc,64+32*i)
            if tag==b'OCCL':p.require(version==2 and struct.unpack_from('<I',rc,at+12)[0]==source_crc,'OCCL source anchor');occl=True
        p.require(occl,'original OCCL present');meta.append(dict(room=room,original_class_sha256=tcid['sha256'],original_ID_sha256=idid['sha256'],original_room_sha256=rcid['sha256'],source_crc=source_crc,original_metadata_changed=False,changed_parts=len(world['changed_parts'])))
    p.require(classes_OP==160 and classes_VA==4,'class census164')
    result=dict(schema=1,state='CANONICAL_WORLD36_STRICT_SOURCE_HOST_PASS',selected=36,legacy_CRC_repairs=21,canonical_unchanged=15,header_offset=36,header_size=48,adopt_crc_enabled=True,stream_crc_forced='RE4DC_TEX_PAYLOAD_CRC=1 in ALL four actual compiler commands',positive_both_paths=72,negative_mipOFF_both_paths=72,old36_strict_classification_per_ON_arm=dict(rejects=21,accepts=15),corrupt_payload_negatives=mutations,source_files=sourceids,arms=arms,coupled_metadata=meta,OP_rows=160,VA_rows=4,all36_descriptor_payload_bytes_preserved=True,pixel_reddecode_performed=False,prior_gate_correction=r['stale_gate_correction'],limits=['Actual unchanged Package nativehost sources/KOS I/O stubs and ASan/UBSan; not SH4/KOS hardware execution.','Active runtime/recipe/default untouched. No fullpack/programme/image/guest or target acceptance.'])
    (work/'qualification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k] for k in ['state','positive_both_paths','negative_mipOFF_both_paths','OP_rows','VA_rows']}))
if __name__=='__main__':main()
