#!/usr/bin/env python3
"""Host qualification for the next36-world-key/4-certificate proposal."""
from pathlib import Path
import hashlib,json,struct,subprocess,sys,zlib
import prepare_r101 as p
import prepare_r103 as n

def reject(call,label):
    try:call()
    except (ValueError,AssertionError,struct.error):return label
    raise AssertionError('accepted invalid '+label)
def with_crc(b):struct.pack_into('<I',b,20,zlib.crc32(b[32:])&0xffffffff);return bytes(b)

def main():
    out=Path(sys.argv[1]);work=Path(sys.argv[2]);p.require(not work.exists(),'preserve host output');work.mkdir(parents=True)
    report=json.loads((out/'receipt.json').read_text());current=n.INPUT.read_bytes();new=(out/'dc/native/r103/ps2-world.r4pw').read_bytes();mapping={r['original_key']:p.key(r['scoped_key']) for r in report['selected']};p.validate_rebind(current,new,mapping);bad=[]
    # Source record positions are selected deterministically by the actual delta.
    selected_part=report['changed_bindings'][0]['part'];a=p.world.inspect_sidecar(current);unselected=next(r['part'] for r in a if r['key'] not in mapping)
    for label,offset in [('placement',len(new)-1),('width',32+16*selected_part+8),('pass',32+16*selected_part+12),('cull',32+16*selected_part+13),('texture',32+16*selected_part+14),('alpha_flags',32+16*selected_part+15),('newkey',32+16*selected_part),('old_scoped_key',32+16*report['certificate']['inherited_scoped29_rows_preserved'][0]),('unselected_key',32+16*unselected)]:
        b=bytearray(new);b[offset]^=1;raw=with_crc(b);bad.append(reject(lambda:p.validate_rebind(current,raw,mapping),'world:'+label))
    b=bytearray(new);b[24]=1;bad.append(reject(lambda:p.validate_rebind(current,bytes(b),mapping),'world:reserved'))
    b=bytearray(new);b[-1]^=1;bad.append(reject(lambda:p.validate_rebind(current,bytes(b),mapping),'world:physical_crc'))
    index=p.pack_index(p.BASE)
    with p.BASE.open('rb') as f:
        for r in report['selected']:
            row=dict(r,uv_scale=r['normalized_uv']);source=p.read_member(f,index,p.key(r['original_key']));candidate=(out/'textures'/(r['scoped_key']+'.re4tex')).read_bytes();p.validate_pair(source,candidate,row)
            for label,at in [('header_crc',32),('codebook',144),('payload',len(candidate)-1),('physical_width',112),('mip_flags',132)]:
                b=bytearray(candidate);b[at]^=1;bad.append(reject(lambda:p.validate_pair(source,bytes(b),row),r['original_key']+':'+label))
    source_header=(p.RECT/'world_rect_bind.h').read_bytes();prior_table=(p.RECT/'scoped_representations.inc').read_bytes();p.require(prior_table.count(b'1.0f,1.0f')==26,'frozen26 adapter source scope')
    (work/'world_rect_bind.h').write_bytes(source_header);(work/'scoped_representations.inc').write_bytes(prior_table+(out/'proposed_representations.inc').read_bytes())
    header=(p.RECT/'world_rect_provenance.h').read_text();needle='static_assert(sizeof(certificates)/sizeof(certificates[0])==3U);';p.require(header.count(needle)==1,'actual26 provenance count')
    (work/'world_rect_provenance.h').write_text(header.replace(needle,needle.replace('==3U','==4U')))
    original_cert=(p.RECT/'provenance_certificates.inc').read_bytes();(work/'provenance_certificates.inc').write_bytes(original_cert+(out/'proposed_provenance_certificate.inc').read_bytes())
    source_probe=Path('/root/probe/texture-world-next21-host-20261021-02/probe.cpp').read_text();p.require(source_probe.count('assert(argc==4)')==1 and source_probe.count('i<3')==1,'prior actual helper oracle source')
    code=source_probe.replace('assert(argc==4)','assert(argc==5)').replace('i<3','i<4');(work/'probe.cpp').write_text(code)
    command=['g++','-std=c++17','-O1','-g0','-fsanitize=undefined','-fno-sanitize-recover=all',str(work/'probe.cpp'),'-o',str(work/'probe')];built=subprocess.run(command,capture_output=True,text=True);p.require(built.returncode==0,built.stderr)
    current_root=n.INPUT.parents[3];r101=Path('/root/re4data/private/texture-world-next21-r101-scoped9-v2-20261021/dc/native/r101/ps2-world.r4pw')
    paths=[current_root/'dc/native/r100/ps2-world.r4pw',n.INPUT,r101,out/'dc/native/r103/ps2-world.r4pw'];run=subprocess.run([str(work/'probe'),*map(str,paths)],capture_output=True,text=True);p.require(run.returncode==0,run.stderr);p.require(int(run.stdout)==556,'expected actual helper check count')
    # Independent composition stream reconstructs the frozen994 parent first,
    # then verifies next1004; no producer virtual1004 function is called.
    parent,parent_paths=n.inherited994();extra={p.key(r['scoped_key']):out/'textures'/(r['scoped_key']+'.re4tex') for r in report['selected']}
    def stream(extra):
        ks=sorted(set(index)|set(parent_paths)|set(extra));offset=2048+((len(ks)*16+2047)//2048)*2048;at=offset;records=[];rows=[]
        with p.BASE.open('rb') as f:
            for k in ks:
                b=extra[k].read_bytes() if k in extra else parent_paths[k][0].read_bytes() if k in parent_paths else p.read_member(f,index,k);records.append(struct.pack('<4I',*k,at,len(b)));at+=((len(b)+2047)//2048)*2048;rows.append((k,len(b),p.sha(b)))
            ix=b''.join(records);ix+=bytes(offset-2048-len(ix));head=b'RE4PAK1\0'+struct.pack('<5I',1,len(ks),2048,offset,zlib.crc32(ix)&0xffffffff);head+=bytes(2048-len(head));digest=hashlib.sha256(head+ix)
            for k,length,expected in rows:
                b=extra[k].read_bytes() if k in extra else parent_paths[k][0].read_bytes() if k in parent_paths else p.read_member(f,index,k);p.require(p.sha(b)==expected,'composition member changed midread');digest.update(b);digest.update(bytes((-length)%2048))
        return digest.hexdigest(),at,rows
    old_hash,old_bytes,old_rows=stream({});p.require(old_hash==parent['virtual']['pack_sha256'] and old_bytes==parent['virtual']['pack_bytes'],'frozen994 independently reconstructed')
    new_hash,new_bytes,rows=stream(extra);virtual=json.loads((out/'virtual-composition1004.json').read_text());p.require(new_hash==virtual['expected_pack_sha256'] and new_bytes==virtual['expected_pack_bytes'],'1004 independently reconstructed')
    old_rows={k:(size,h) for k,size,h in old_rows};new_rows={k:(size,h) for k,size,h in rows};p.require(all(new_rows[k]==v for k,v in old_rows.items()),'994 member changed in1004');p.require(len(new_rows)==6537 and set(new_rows)-set(old_rows)==set(extra),'only10 append')
    result=dict(schema=1,state='PROPOSED_SOURCE_HOST_QUALIFIED_NOT_INTEGRATED',selected_actual_package_cases=10,rejected_mutations=len(bad),mutation_labels=bad,actual_helper_checks=556,host_proposed_representations=36,host_proposed_certificates=4,actual_adapter_sha256=p.sha(source_header),actual_provenance_sha256=p.sha(header.encode()),actual_parent_table_sha256=p.sha(prior_table),actual_parent_certificates_sha256=p.sha(original_cert),host_only_change='Fixed certificate-count assertion3to4 in host copy; active source unchanged',host_command=command,host_probe_source_sha256=p.sha(code.encode()),host_probe_stdout=run.stdout,host_probe_stderr=run.stderr,independently_reconstructed994_sha256=old_hash,independently_reconstructed1004_sha256=new_hash,all6527_parent_members_preserved_exact=True,index_sector_growth='51to52, stillwithin64',limits=['Actual complete helper functions with proposed tables, not actual integrated TU or SH4/full program.','ASan/UBSan actual native Package reader ten new cases is a separate receipt.','No image, guest, target look/draw/residency/performance/release/hardware acceptance.'])
    (work/'qualification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k] for k in ['rejected_mutations','actual_helper_checks','independently_reconstructed1004_sha256']}))
if __name__=='__main__':main()
