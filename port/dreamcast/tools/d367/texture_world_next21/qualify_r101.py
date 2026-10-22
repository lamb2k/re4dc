#!/usr/bin/env python3
"""Independent focused tests for proposed r101 table/certificate integration.

The C++ probe uses the actual unchanged adapter header with the proposed26-row
table. Only the provenance header's fixed certificate-count assertion changes
from2 to3 in the HOST COPY; no runtime/shared file is edited.
"""
from pathlib import Path
import hashlib, importlib.util, json, os, shutil, struct, subprocess, sys, zlib

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('preparer',HERE/'prepare_r101.py');p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
def sha(b):return hashlib.sha256(b).hexdigest()
def must_refuse(call,label):
    try:call()
    except (ValueError,AssertionError,struct.error):return label
    raise AssertionError('accepted invalid '+label)
def fix_crc(b):
    struct.pack_into('<I',b,20,zlib.crc32(b[32:])&0xffffffff);return bytes(b)

def main():
    output=Path(sys.argv[1]);work=Path(sys.argv[2]);p.require(not work.exists(),'preserve previous host tests');work.mkdir(parents=True)
    r=json.loads((output/'receipt.json').read_text());base=p.pack_index(p.BASE);old=p.INPUT.read_bytes();new=(output/'dc/native/r101/ps2-world.r4pw').read_bytes();mapping={x['original_key']:p.key(x['scoped_key']) for x in r['selected']}
    p.validate_rebind(old,new,mapping);bad=[]
    for label,offset,value in [('placement',len(new)-1,1),('width',32+12*16+8,1),('pass',32+12,1),('cull',32+13,1),('texture',32+14,1),('flags',32+15,1),('unselected_key',32+16,1),('selected_key',32,1)]:
        mutated=bytearray(new);mutated[offset]^=value;b=fix_crc(mutated);bad.append(must_refuse(lambda:p.validate_rebind(old,b,mapping),'world:'+label))
    b=bytearray(new);b[24]=1;bad.append(must_refuse(lambda:p.validate_rebind(old,bytes(b),mapping),'world:reserved'))
    b=bytearray(new);b[-1]^=1;bad.append(must_refuse(lambda:p.validate_rebind(old,bytes(b),mapping),'world:physical_crc'))
    # Every actual selected file still matches the preexisting qualified payload.
    with p.BASE.open('rb') as f:
        for row in r['selected']:
            row=dict(row,uv_scale=row['normalized_uv'])
            source=p.read_member(f,base,p.key(row['original_key']));candidate=(output/'textures'/(row['scoped_key']+'.re4tex')).read_bytes();p.validate_pair(source,candidate,row)
            for label,offset in [('body_crc',32),('codebook',144),('payload',len(candidate)-1),('physical_width',112),('flags',132)]:
                b=bytearray(candidate);b[offset]^=1;bad.append(must_refuse(lambda:p.validate_pair(source,bytes(b),row),row['original_key']+':'+label))
    adapter=(p.RECT/'world_rect_bind.h').read_bytes();original_inc=(p.RECT/'scoped_representations.inc').read_bytes();extra=(output/'proposed_representations.inc').read_bytes()
    (work/'world_rect_bind.h').write_bytes(adapter);(work/'scoped_representations.inc').write_bytes(original_inc+extra)
    provenance=(p.RECT/'world_rect_provenance.h').read_text();needle='static_assert(sizeof(certificates)/sizeof(certificates[0])==2U);';assert provenance.count(needle)==1
    (work/'world_rect_provenance.h').write_text(provenance.replace(needle,needle.replace('==2U','==3U')))
    certinc=(p.RECT/'provenance_certificates.inc').read_bytes()+(output/'proposed_provenance_certificate.inc').read_bytes();(work/'provenance_certificates.inc').write_bytes(certinc)
    code=r'''
#include "world_rect_bind.h"
#include "world_rect_provenance.h"
#include <cassert>
#include <fstream>
#include <vector>
#include <iostream>
using namespace re4dc::rect21;
std::vector<unsigned char> read(const char* path){std::ifstream f(path,std::ios::binary);assert(f);return {std::istreambuf_iterator<char>(f),{}};}
int main(int argc,char**argv){
  assert(argc==4);unsigned checks=0;
  for(const auto&r:qualified){
    float u=-9,v=-11;assert(!adapt(r.crc,r.fnv,r.logical_width,r.logical_height,r.stored,u,v));assert(u==-9&&v==-11);++checks;
    assert(adapt(r.crc,r.fnv,r.logical_width,r.logical_height,r.stored,u,v,true));assert(u==1&&v==1);++checks;
    for(unsigned field=0;field<11;++field){
      auto d=r.stored;unsigned c=r.crc,f=r.fnv,w=r.logical_width,h=r.logical_height;
      switch(field){case0:c^=1;break;case1:f^=1;break;case2:w^=1;break;case3:h^=1;break;case4:d.width^=1;break;case5:d.height^=1;break;case6:d.format^=1;break;case7:d.flags^=1;break;case8:d.payload^=1;break;case9:d.bytes^=1;break;case10:d.checksum^=1;break;}
      u=-9;v=-11;assert(!adapt(c,f,w,h,d,u,v,true));assert(u==-9&&v==-11);++checks;
    }
    const unsigned tsp=((__builtin_ctz(r.stored.width)-3)<<3)|(__builtin_ctz(r.stored.height)-3);
    assert(header_dimensions(tsp,r.stored.width,r.stored.height));assert(!header_dimensions(tsp^1,r.stored.width,r.stored.height));checks+=2;
  }
  for(unsigned i=0;i<3;++i){
    const auto&c=provenance::certificates[i];auto b=read(argv[i+1]);
    assert(provenance::policy_source_crc(c.room,b.data(),b.size(),c.mesh_crc,c.mesh_bytes,c.parts,c.meshes)==c.source_crc);++checks;
    auto actual=provenance::word(b.data()+20);
    assert(provenance::policy_source_crc(c.room^8,b.data(),b.size(),c.mesh_crc,c.mesh_bytes,c.parts,c.meshes)==actual);++checks;
    assert(provenance::policy_source_crc(c.room,b.data(),b.size(),c.mesh_crc^1,c.mesh_bytes,c.parts,c.meshes)==actual);++checks;
    // Same-header/CRC forged body still fails complete-file FNV certificate.
    b.back()^=1;assert(provenance::policy_source_crc(c.room,b.data(),b.size(),c.mesh_crc,c.mesh_bytes,c.parts,c.meshes)==actual);++checks;
  }
  std::cout<<checks<<"\n";
}
'''
    # C++ switch labels deliberately use conventional separate tokens.
    import re
    code=re.sub(r'case(\d+):',r'case \1:',code)
    (work/'probe.cpp').write_text(code);exe=work/'probe'
    command=['g++','-std=c++17','-O1','-g0','-fsanitize=undefined','-fno-sanitize-recover=all',str(work/'probe.cpp'),'-o',str(exe)]
    build=subprocess.run(command,capture_output=True,text=True);p.require(build.returncode==0,build.stderr)
    current=Path('/root/re4data/private/texture-rect21-current948-scoped17-20261021')
    paths=[current/'dc/native/r100/ps2-world.r4pw',current/'dc/native/r103/ps2-world.r4pw',output/'dc/native/r101/ps2-world.r4pw']
    run=subprocess.run([str(exe),*map(str,paths)],capture_output=True,text=True);p.require(run.returncode==0,run.stderr)
    # Verify the virtual pack without calling the producer's writer/layout code.
    virtual=json.loads((output/'virtual-composition.json').read_text());entries={p.key(m['key']):m for m in virtual['members']};require_base=set(base)<=set(entries);p.require(require_base and len(entries)==6527,'independent member census')
    data=2048+((len(entries)*16+2047)//2048)*2048;at=data;raw_ix=bytearray();blocks=[]
    with p.BASE.open('rb') as f:
        for k,m in sorted(entries.items()):
            b=p.read_member(f,base,k) if k in base else (output/'textures'/(p.name(k)+'.re4tex')).read_bytes();p.require(sha(b)==m['sha256'] and len(b)==m['bytes'],'independent membership bytes')
            raw_ix+=struct.pack('<4I',*k,at,len(b));at+=((len(b)+2047)//2048)*2048;blocks.append((k,len(b)))
        raw_ix+=bytes(data-2048-len(raw_ix));header=b'RE4PAK1\0'+struct.pack('<5I',1,len(entries),2048,data,zlib.crc32(raw_ix)&0xffffffff);header+=bytes(2048-len(header));h=hashlib.sha256(header+raw_ix)
        for k,n in blocks:
            b=p.read_member(f,base,k) if k in base else (output/'textures'/(p.name(k)+'.re4tex')).read_bytes();h.update(b);h.update(bytes((-n)%2048))
    p.require(h.hexdigest()==virtual['expected_pack_sha256'] and at==virtual['expected_pack_bytes'],'independent virtual pack digest')
    result=dict(schema=1,selected_package_identity_and_descriptor_cases=9,rejected_mutations=len(bad),mutation_labels=bad,actual_adapter_checks=int(run.stdout),adapter_source_sha256=sha(adapter),active_header_unchanged=True,host_proposed_representation_rows=26,host_proposed_certificate_rows=3,host_provenance_copy_count_assertion='2 to3 only; production helper remains2',host_command=command,host_probe_source_sha256=sha(code.encode()),host_probe_sha256=sha(exe.read_bytes()),host_stdout=run.stdout,host_stderr=run.stderr,virtual_pack_independently_rehashed=h.hexdigest(),base_member_bytes_preserved=len(base),new_member_bytes=9,no_full_pack_written=True,limits=['The table/certificate combination is a HOST PROPOSAL. Active source still admits17 textures/two certificates.','Exact same nine preexisting packages previously passed native Package ASan/UBSan; this unit reuses those byte identities and adds independent decoder/table/sidecar/composition gates.','No SH4 object, full program, Flycast, release or physical acceptance.'])
    (work/'qualification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k] for k in ['rejected_mutations','actual_adapter_checks','virtual_pack_independently_rehashed','base_member_bytes_preserved']}))
if __name__=='__main__':main()
