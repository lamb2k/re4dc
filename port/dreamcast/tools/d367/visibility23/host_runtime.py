"""Compile the real mesh loader, provenance header, R4SG predicate and selector.

Only filesystem I/O/allocation glue is substituted. This is host evidence, not
Dreamcast execution. Runtime source is supplied explicitly and never modified.
"""
import hashlib
from pathlib import Path
import re
import subprocess


def compile_probe(runtime_tree, scratch):
    tree, scratch = Path(runtime_tree), Path(scratch)
    src = tree / 'port/dreamcast/game/platform/native_static.cpp'
    text = src.read_text()
    condition = re.search(r'if\(std::memcmp\(gb,"R4SG",4\).*?gwhy="header";', text, re.S)
    if not condition or 'policySourceCrc' not in condition[0]:
        raise ValueError('runtime must have the authenticated policySourceCrc R4SG consumer')
    start = text.index('__attribute__((noinline)) unsigned sg_select(')
    end = text.index('\n#if', start)
    selector = text[start:end]
    admission = re.search(r'    Ps2Head h\{\};.*?if\(!ok\)why="sidecar records";\n    }', text, re.S)[0]
    structures = '\n'.join(re.search(r'struct '+name+r' \{[^\n]*', text)[0]
                           for name in ('Ps2Part', 'Ps2Placement', 'Ps2Head'))
    geometry = tree / 'port/dreamcast/room/pvr_geometry.hpp'
    finite = re.search(r'inline bool is_finite\(float value\)\{.*?\n}', geometry.read_text(), re.S)[0]
    stub = scratch / 'kos'
    stub.mkdir()
    (stub / 'fs.h').write_text('#pragma once\ntypedef int file_t;\n#define FILEHND_INVALID (-1)\n')
    room = tree / 'port/dreamcast/room'
    provenance = tree / 'port/dreamcast/tools/d367/texture_rect21/world_rect_provenance.h'
    code = r'''
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iostream>
#include <iterator>
#include <vector>
#include "instanced_mesh.hpp"
#include "world_rect_provenance.h"
std::uint32_t ps2_crc32(const unsigned char* b,unsigned n){
    std::uint32_t x=~0U;
    for(unsigned i=0;i<n;++i){x^=b[i];for(unsigned j=0;j<8;++j)x=(x>>1)^((0U-(x&1U))&0xedb88320U);}
    return ~x;
}
std::vector<unsigned char> read(const char* p){std::ifstream f(p,std::ios::binary);return {std::istreambuf_iterator<char>(f),{}};}
''' + structures + '\nnamespace re4dc::render {\n' + finite + '\n}\n' + selector + r'''
int main(int argc,char** argv){
    if(argc==3 && std::strcmp(argv[1],"select")==0){
        auto b=read(argv[2]);unsigned n=0,mask=0;std::cin>>n>>mask;
        if(n>8 || b.size()!=16*n)return 2;
        float coef[40]={};for(float& c:coef)std::cin>>c;
        std::uint16_t r0[8],r1[8];unsigned lo=0,hi=0,cut=0;
        auto nr=sg_select(reinterpret_cast<const std::uint16_t*>(b.data()),n,coef,mask,r0,r1,lo,hi,cut);
        std::cout<<nr<<' '<<lo<<' '<<hi<<' '<<cut;
        for(unsigned i=0;i<nr;++i)std::cout<<' '<<r0[i]<<' '<<r1[i];
        std::cout<<'\n';return 0;
    }
    if(argc!=4)return 2;
    auto mesh=read(argv[1]),world=read(argv[2]),groups=read(argv[3]);
    re4dc::room::MeshPackage pkg;
    if(!pkg.adopt(mesh.data(),mesh.size(),true,true)){std::cout<<"mesh-reject\n";return 0;}
    // Exact production sidecar validation before the provenance API.
    std::vector<unsigned char> storage=mesh;storage.insert(storage.end(),world.begin(),world.end());
    const auto* s=storage.data();const unsigned mbytes=mesh.size(),psize=world.size();
    struct {re4dc::room::MeshPackage& package;const Ps2Part* parts;const Ps2Placement* placements;} ps2w{pkg,nullptr,nullptr};
    bool ok=psize>=sizeof(Ps2Head);const char* why=ok?nullptr:"sidecar size";
''' + admission + r'''
    if(!ok){std::cout<<"sidecar-reject "<<why<<'\n';return 0;}
    const auto& mh=pkg.header();
    const unsigned policySourceCrc=re4dc::rect21::provenance::policy_source_crc(
        0x109,world.data(),world.size(),mh.crc,mh.bytes,mh.part_count,mh.mesh_count);
    const unsigned gsize=groups.size();auto* gb=groups.data();
    const char* gwhy=nullptr;
    if(gsize<32U || gsize>262144U || (gsize&15U))gwhy="size";
    std::uint32_t w[8]={};
    if(!gwhy){std::memcpy(w,gb,32);
''' + condition[0] + r'''
    }
    std::cout<<std::hex<<policySourceCrc<<' '<<(gwhy?gwhy:"ok")<<'\n';
}
'''
    cpp = scratch / 'runtime_probe.cpp'
    cpp.write_text(code)
    exe = scratch / 'runtime_probe'
    subprocess.run(['g++', '-std=c++17', '-O2', '-I'+str(scratch), '-I'+str(room),
                    '-I'+str(provenance.parent), str(cpp), '-o', str(exe)], check=True)
    files = [src, room/'instanced_mesh.hpp', room/'room_package.hpp', provenance,
             provenance.parent/'provenance_certificates.inc', geometry]
    receipt = {str(p.relative_to(tree)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    receipt['extracted_r4sg_predicate_sha256'] = hashlib.sha256(condition[0].encode()).hexdigest()
    receipt['extracted_sg_select_sha256'] = hashlib.sha256(selector.encode()).hexdigest()
    receipt['extracted_r4pw_admission_sha256'] = hashlib.sha256(admission.encode()).hexdigest()
    return exe, receipt
