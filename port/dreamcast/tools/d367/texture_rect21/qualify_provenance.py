#!/usr/bin/env python3
"""Actual frozen-data + actual native_static predicate provenance regression."""
from pathlib import Path
import argparse, hashlib, json, shutil, struct, subprocess, zlib
import provenance_actual_path as A
import coupled_sidecars as C
from audit_coupled_sidecars import read_pack

def sha(b):return hashlib.sha256(b).hexdigest()
def require(ok,why):
    if not ok:raise ValueError(why)

def crc_collision(blob):
    """Change one texture-key byte; solve last four body bytes back to old CRC."""
    b=bytearray(blob); wanted=zlib.crc32(b[32:])&0xffffffff;b[32]^=1
    offset=len(b)-4;base=zlib.crc32(b[32:])&0xffffffff
    columns=[]
    for bit in range(32):
        x=bytearray(b);x[offset+bit//8]^=1<<(bit%8)
        columns.append((zlib.crc32(x[32:])&0xffffffff)^base)
    basis={}
    for i,column in enumerate(columns):
        mask=1<<i
        while column:
            bit=column.bit_length()-1
            if bit in basis:column^=basis[bit][0];mask^=basis[bit][1]
            else:basis[bit]=(column,mask);break
    target=wanted^base;mask=0
    while target:
        bit=target.bit_length()-1;require(bit in basis,'CRC patch singular')
        target^=basis[bit][0];mask^=basis[bit][1]
    for i in range(32):
        if (mask>>i)&1:b[offset+i//8]^=1<<(i%8)
    require(zlib.crc32(b[32:])&0xffffffff==wanted and b!=blob,'CRC collision fixture')
    return bytes(b)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in('evidence','selected-plan','base-pack','candidate-pack','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();require(not a.out.exists(),'preserve existing output')
    a.out.mkdir()
    files=json.loads((a.evidence/'image-plan-04/baseline-file-identities.json').read_text())['files']
    cert=json.loads((A.HERE/'provenance_certificate.json').read_text())
    selected=json.loads(a.selected_plan.read_text())['selected']
    require(selected==cert['selected_contract'],'selected contract drift')
    old=read_pack(a.base_pack,cert['base_pack']);new=read_pack(a.candidate_pack,cert['candidate_pack'])
    def asset(arm,path,check=True):
        r=files[path]
        with(a.evidence/f'standalone-{arm}-01/gdemu/track03.iso').open('rb')as f:
            f.seek((r['extent']-45000)*2048);b=f.read(r['bytes'])
        require(len(b)==r['bytes'],'asset extent')
        if check:require(sha(b)==r['sha256'],'asset hash '+path)
        return b
    source=A.generate();cpp=a.out/'actual-path.cpp';cpp.write_text(source)
    compiled={}
    for name,flags in [('default',[]),('off',['-DRE4DC_WORLD_RECT21=0']),('on',['-DRE4DC_WORLD_RECT21=1'])]:
        exe=a.out/('actual-path-'+name)
        cmd=['g++','-std=c++17','-Wall','-Wextra','-Werror','-O2','-I'+str(A.HERE),*flags,str(cpp),'-o',str(exe)]
        r=subprocess.run(cmd,capture_output=True,text=True)
        (a.out/('compile-'+name+'.txt')).write_text(r.stdout+r.stderr)
        require(r.returncode==0,'host compile '+name)
        compiled[name]=dict(path=str(exe),sha256=sha(exe.read_bytes()),command=cmd)
    require(compiled['default']['sha256']==compiled['off']['sha256'],'default/explicit0 host bytes')
    rows=[]; semantic={};checks=0
    for spec in cert['rooms']:
        room=spec['room'];name=f'r{room:03x}';pre='/dc/native/'+name+'/'
        bw=asset('B',pre+'ps2-world.r4pw');cw=asset('C',pre+'ps2-world.r4pw',False)
        require(sha(cw)==spec['candidate_world_sha256'],'C sidecar hash')
        bm=asset('B',pre+'ps2-world.re4mesh');cm=asset('C',pre+'ps2-world.re4mesh')
        ids=asset('B',pre+'ps2-world.ids');tc=asset('B',pre+'ps2-world.r4tc')
        require(ids==asset('C',pre+'ps2-world.ids') and tc==asset('C',pre+'ps2-world.r4tc'),'one original metadata lineage')
        pcl=asset('B','/dc/native/r100/interior.cell')if room==0x100 else b''
        if pcl:require(pcl==asset('C','/dc/native/r100/interior.cell'),'PCL exact C')
        rc=asset('B',pre+'room.r4rc');require(rc==asset('C',pre+'room.r4rc'),'R4RC exact C')
        count=struct.unpack_from('<H',rc,12)[0];occl=None
        for off in range(64,64+32*count,32):
            tag,ver,fl,start,size=struct.unpack_from('<4sHHII',rc,off)
            if tag==b'OCCL':occl=rc[start:start+size];require(ver==2,'OCCL version')
        require(occl is not None and struct.unpack_from('<I',occl,12)[0]==spec['source_crc'],'OCCL actual old binding')
        _,bp,_=C.world(bw);_,cp,_=C.world(cw)
        keys=lambda ps:{C.key(x)for x in ps if any(x[:2])}
        _,proof=C.prepare(bw,cw,ids,tc,bm,cm,old(keys(bp)),new(keys(cp)),selected,spec['mesh_sha256'],
                          {'world':sha(bw),'ids':sha(ids),'classes':sha(tc)})
        require(proof['changed_parts']==spec['changed_records'],'certificate cohort differs')
        hist={str(c):sum(tc[24+i]==c for i in proof['changed_parts'])for c in (1,9)}
        semantic[name]=dict(changed_records=len(proof['changed_parts']),changed_class_histogram=hist,
                            mesh_sha256=sha(bm),original_ids_sha256=sha(ids),original_tc_sha256=sha(tc),
                            original_pcl_sha256=sha(pcl)if pcl else None,original_r4rc_sha256=sha(rc),
                            preserved_R4RC_SRCB_origin=True,packages_actual_SHA_descriptor_RGB565_opaque_proof=True)
        def run(arm='C',enabled='on',mutation=0,world=None,mesh_override=None,room_override=None):
            nonlocal checks
            blob=world if world is not None else cw if arm=='C' else bw
            mh=[spec['mesh_crc'],spec['mesh_bytes'],spec['parts'],spec['meshes']]
            if mesh_override:
                k,v=mesh_override;mh[k]=v
            cmd=[compiled[enabled]['path'],str(room if room_override is None else room_override),*map(str,mh),str(mutation)]
            packet=b''.join(struct.pack('<I',len(x))+x for x in(blob,ids,tc,pcl,bm,occl))
            r=subprocess.run(cmd,input=packet,capture_output=True)
            require(r.returncode==0,'probe process '+r.stderr.decode())
            result=json.loads(r.stdout);checks+=1
            row=dict(room=name,arm=arm,enabled=enabled,mutation=mutation,mesh_override=mesh_override,room_override=room_override,result=result)
            rows.append(row);return result
        baseline=None
        def accepted(r):
            require(r['physical'] and r['ids'] and r['trans'] and r['occl'],'four consumers except PC')
            require(bool(r['pc_package'] and r['pc_file'])==(room==0x100),'PC package/file selector')
            if baseline is not None:require((r['unique'],r['class_crc'])==(baseline['unique'],baseline['class_crc']),'binding/class lineage differs')
            require(r['profile_crc']==r['actual_crc'],'profile canonicalized')
            require(r['occl_guards'] and r['movie_current'] and r['movie_bad_refused'] and r['movie_policy_idle'],'liveness/movie')
            require(r['movie_raw_fnv']==A_fnv(cw if r['actual_crc']==spec['physical_body_crc']else bw),'movie physical FNV')
        for enabled in('default','off','on'):
            r=run('B',enabled);accepted(r);require(r['source_crc']==r['actual_crc']==spec['source_crc'],'B anchor')
            baseline=r
        for enabled in('default','off'):
            r=run('C',enabled)
            require(r['physical'] and not(r['ids']or r['trans']or r['occl']or r['pc_package']),'C disabled fallback')
            require(r['source_crc']==r['actual_crc']==spec['physical_body_crc'],'C disabled identity')
        r=run();accepted(r)
        require(r['actual_crc']==spec['physical_body_crc'] and r['source_crc']==spec['source_crc'],'candidate split identity')
        for mutation in(1,6,11):require(not run(mutation=mutation)['physical'],'bad/truncated physical accepted')
        for mutation in(2,7,8,10):
            r=run(mutation=mutation);require(r['physical'] and r['source_crc']==r['actual_crc'] and not(r['ids']or r['trans']or r['occl']or r['pc_package']),'uncertified sidecar mapped')
        collision=crc_collision(cw);r=run(world=collision)
        require(r['physical'] and r['actual_crc']==spec['physical_body_crc'] and r['source_crc']==r['actual_crc'] and not r['ids'],'same-CRC uncertified body mapped')
        for index in range(4):
            value=[spec['mesh_crc'],spec['mesh_bytes'],spec['parts'],spec['meshes']][index]^1
            r=run(mesh_override=(index,value))
            if index>=2:require(not r['physical'],'physical count mismatch')
            else:require(r['source_crc']==r['actual_crc'] and not(r['ids']or r['trans']or r['occl']or r['pc_package']),'uncertified mesh tuple mapped')
        for test_room in(0x101,0x103 if room==0x100 else 0x100):
            r=run(room_override=test_room);require(r['source_crc']==r['actual_crc'] and not r['ids'],'unknown/swapped room mapped')
        r=run(mutation=3);require(not r['ids'] and r['trans'] and r['occl'],'IDs corrupt guard')
        r=run(mutation=4);require(not r['trans'] and r['ids'] and r['occl'],'class body CRC guard')
        if room==0x100:
            r=run(mutation=5);require(not r['pc_file'] and r['pc_package'],'PCL original header guard')
        r=run(mutation=9);require(not r['occl'] and r['ids'] and r['trans'],'OCCL corrupt stamp guard')
    report=dict(scope='Source/host actual extracted paths; filesystem/header seams; no SH4/fullbuild/guest',cases=checks,
                default_explicit0_host_binary_exact=True,compiled=compiled,semantics=semantic,results=rows,
                source_sha256=sha(A.SOURCE.read_bytes()),probe_source_sha256=sha(source.encode()),
                helper_sha256=sha((A.HERE/'world_rect_provenance.h').read_bytes()),
                certificate_sha256=sha((A.HERE/'provenance_certificate.json').read_bytes()),
                actual_geometry_verified=True,all_78_key_only_records_and17_actual_package_contracts_verified=True,
                release_or_hardware_acceptance=False,performance_claim=False,
                limitations=['Host seams do not execute full PC heap/load/lend or room_occl parser',
                             'Full target OFF object/program identity awaits allocated build','No target guest or look gate',
                             'Optional PVS/SG assets absent: wiring reviewed, no data-level admission exercised',
                             'Whole physical VRAM/lifecycle/performance/physical Dreamcast gates remain open'])
    (a.out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k]for k in('cases','default_explicit0_host_binary_exact','source_sha256','helper_sha256')}))

def A_fnv(b):
    h=2166136261
    for x in b:h=((h^x)*16777619)&0xffffffff
    return h

if __name__=='__main__':main()