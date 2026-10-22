#!/usr/bin/env python3
"""Dry audit of frozen B/C R4ID/R4TC repairs; writes JSON only, never assets."""
from pathlib import Path
import argparse, hashlib, json, struct, zlib
import coupled_sidecars as C


def read_pack(path, expected):
    with path.open('rb') as f:
        C.require(hashlib.file_digest(f,'sha256').hexdigest()==expected,'pack identity')
        f.seek(0);magic,v,n,ix,off=struct.unpack('<8s4I',f.read(24))
        C.require(magic==b'RE4PAK1\0','pack header');f.seek(ix)
        rows=list(struct.iter_unpack('<4I',f.read(n*16)))
    index={'%08x-%08x'%(a,b):(o,s)for a,b,o,s in rows}
    def get(keys):
        result={}
        with path.open('rb')as f:
            for key in keys:
                C.require(key in index,'missing package '+key);o,s=index[key];f.seek(o);result[key]=f.read(s)
        return result
    return get


def main():
    a=argparse.ArgumentParser(description=__doc__)
    for n in('evidence','freeze','selected-plan','base-pack','candidate-pack','out'):a.add_argument('--'+n,type=Path,required=True)
    a=a.parse_args();C.require(not a.out.exists(),'preserve prior report')
    files=json.loads((a.evidence/'image-plan-04/baseline-file-identities.json').read_text())['files']
    selected=json.loads(a.selected_plan.read_text())['selected']
    old=read_pack(a.base_pack,'e19cfc464e789e97ca96864adfc2a4cd44443a9f4775bebd842c3e184a65559b')
    new=read_pack(a.candidate_pack,'bbcef25f0090fa4004e03331a33c84f8f89fd3582704e4a08945a8f6a15d5026')
    def asset(arm,name):
        r=files[name]
        with(a.evidence/('standalone-'+arm+'-01/gdemu/track03.iso')).open('rb')as f:
            f.seek((r['extent']-45000)*2048);blob=f.read(r['bytes'])
        if arm=='B' or not name.endswith('.r4pw'):C.require(C.digest(blob)==r['sha256'],'asset identity '+name)
        return blob
    reports={}
    for room in('r100','r103'):
        pre='/dc/native/'+room+'/';ow=asset('B',pre+'ps2-world.r4pw');nw=asset('C',pre+'ps2-world.r4pw')
        om=asset('B',pre+'ps2-world.re4mesh');nm=asset('C',pre+'ps2-world.re4mesh')
        ids=asset('B',pre+'ps2-world.ids');tc=asset('B',pre+'ps2-world.r4tc')
        C.require(asset('C',pre+'ps2-world.ids')==ids and asset('C',pre+'ps2-world.r4tc')==tc,'current C dependent bytes unexpectedly differ')
        _,op,_=C.world(ow);_,np,_=C.world(nw)
        keys=lambda ps:{C.key(p)for p in ps if any(p[:2])}
        outputs,proof=C.prepare(ow,nw,ids,tc,om,nm,old(keys(op)),new(keys(np)),selected,files[pre+'ps2-world.re4mesh']['sha256'],
                                {k:files[pre+n]['sha256']for k,n in [('world','ps2-world.r4pw'),('ids','ps2-world.ids'),('classes','ps2-world.r4tc')]})
        h=struct.unpack_from('<4s19I',om);meshes=[struct.unpack_from('<HBBHHIII12f',om,h[10]+68*i)for i in range(h[4])]
        details=[]
        for i in proof['changed_parts']:
            mr=[(mi,m)for mi,m in enumerate(meshes)if m[6]<=i<m[6]+m[7]]
            C.require(len(mr)==1,'part owner');mi,m=mr[0];p=struct.unpack_from('<IIBBBBII4f',om,h[11]+36*i)
            details.append(dict(part=i,old_key=C.key(op[i]),new_key=C.key(np[i]),logical=list(op[i][2:4]),render_pass=op[i][4],vertex_alpha=bool(op[i][7]&1),class_code=tc[24+i],mesh=mi,source_bin=m[0],common=m[1],owner=m[2],source_part_offset=p[0],source_part_size=p[1],source_texture_slot=p[2],mesh_alpha=p[3],mesh_flags=p[4],uv_bias=list(p[8:10]),uv_scale=list(p[10:12])))
        proof.update(changed_part_material_refs=details,changed_part_pass_counts={str(p):sum(x['render_pass']==p for x in details)for p in range(3)},changed_class_histogram={str(c):sum(x['class_code']==c for x in details)for c in range(11)},dependent_files={n:dict(bytes=len(blob),predicted_sha256=C.digest(blob),changed_byte_ranges=[[12,16]]if n=='ids'else[[16,20]])for n,blob in outputs.items()},materialization=False)
        reports[room]=proof
    report=dict(scope='Two specific dependent gates, dry metadata only',source='004cf224674fa60cf08dc10e641c723de238a0fd',program='a58579b87da0c45267cb93efe29feea2438da9ddab62d0fe31c47a1c6ff32c71',full_equivalence=False,rooms=reports,open_consumers=['PCL1/runtime interior constant','OCCL and other active whole-R4PW consumers'],regression_controls=['Original B class/ID bindings accepted at original CRC','Current bad C class/ID bindings rejected; preserve logs','Prepared bytes change only ID[12:16] and TC[16:20], retain file sizes/full payloads','Identical-world OFF/control produces byte-identical dependencies','Any geometry/placement/pass/alpha/layout/mapping/member/class mutation rejects','No new image or guest; source/frame/camera/performance acceptance separate'])
    with a.out.open('x')as f:json.dump(report,f,indent=2)
    print(json.dumps({room:dict(parts=len(p['changed_parts']),passes=p['changed_part_pass_counts'],ids=p['dependent_files']['ids'],classes=p['dependent_files']['classes'])for room,p in reports.items()}))

if __name__=='__main__':main()
