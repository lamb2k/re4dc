#!/usr/bin/env python3
"""Host binding checks using the private, pinned r101 R4PW as input.

The checks use an actual private candidate and mutate its bytes and binding
arguments. They are not a visual/performance certificate. No private bytes
leave the explicitly selected output directory.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import struct

REL = "port/dreamcast/tools/d367/texture_rect21/world_rect_provenance.h"


def run(command, **kwargs):
    return subprocess.run(command, capture_output=True, text=True, **kwargs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--world", type=Path, required=True)
    parser.add_argument("--mesh", type=Path, required=True, help="Actual private candidate R4IM")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    repo, out = args.repo.resolve(), args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    header = repo / REL
    old = out / "baseline-header.h"
    old.write_text(subprocess.check_output(["git", "-C", str(repo), "show", "HEAD:" + REL], text=True))
    flags = ["g++", "-std=c++17", "-DRE4DC_SCENERY_N256=1", "-DRE4DC_WORLD_SG26=1", "-I" + str(header.parent)]
    tokens = []
    for name, source in (("before", old), ("absent", header), ("zero", header)):
        extra = ["-DRE4DC_WORLD_REBUILD27=0"] if name == "zero" else []
        result = run(flags + extra + ["-E", "-P", "-x", "c++", str(source)])
        if result.returncode:
            raise RuntimeError(result.stderr)
        (out / (name + ".tokens")).write_text(result.stdout)
        tokens.append(result.stdout)
    if not tokens[0] == tokens[1] == tokens[2]:
        raise AssertionError("Off preprocessor token identity failed")
    mesh = args.mesh.read_bytes()
    mesh_bytes, mesh_crc = struct.unpack_from("<II", mesh, 8)
    if mesh_bytes != len(mesh) or mesh_crc == 0x4ec31f36:
        raise ValueError("Need an actual changed candidate mesh")
    row = ("{0x101U,17100U,223U,342U,204U,0x7f878babU,0xddb50572U,"
           + hex(mesh_crc) + "U," + str(mesh_bytes) + "U,0x68100b21U}")
    private = out / "world_rebuild27_certificates.inc"
    private.write_text("inline constexpr Certificate rebuild27_certificates[] = {" + row + "};\n")
    source = out / "consumer.cpp"
    source.write_text('''#include <fstream>
#include <iterator>
#include <vector>
#include <iostream>
#include "world_rect_provenance.h"
std::uint32_t crc32(const unsigned char* p,unsigned n){
    std::uint32_t c=0xffffffffU;
    while(n--){c^=*p++;for(unsigned k=0;k<8;++k)c=(c>>1)^((0U-(c&1U))&0xedb88320U);}
    return ~c;
}
int main(int argc,char** argv){
    using namespace re4dc::rect21::provenance;
    if(argc!=3)return 2;
    std::ifstream f(argv[1],std::ios::binary);
    std::vector<unsigned char> w((std::istreambuf_iterator<char>(f)),{});
    if(w.size()!=17100U)return 3;
    std::ifstream mf(argv[2],std::ios::binary);
    std::vector<unsigned char> mesh((std::istreambuf_iterator<char>(mf)),{});
    if(mesh.size()!=CANDIDATE_BYTES)return 4;
    const auto actual=word(w.data()+20);
    auto call=[&](unsigned room,unsigned crc,unsigned bytes,unsigned parts,unsigned meshes){
        return policy_source_crc(room,w.data(),unsigned(w.size()),crc,bytes,parts,meshes,mesh.data(),crc32);
    };
    unsigned checks=0;
    auto check=[&](bool ok){++checks;if(!ok){std::cerr<<"failed "<<checks<<"\\n";exit(10);}};
    check(call(0x101U,0x4ec31f36U,1223744U,342U,204U)==0x68100b21U);
    check(call(0x101U,CANDIDATE_CRC,CANDIDATE_BYTES,342U,204U)==0x68100b21U);
    check(call(0x101U,CANDIDATE_CRC^1U,CANDIDATE_BYTES,342U,204U)==actual);
    check(call(0x100U,CANDIDATE_CRC,CANDIDATE_BYTES,342U,204U)==actual);
    check(call(0x101U,CANDIDATE_CRC,CANDIDATE_BYTES+1U,342U,204U)==actual);
    check(call(0x101U,CANDIDATE_CRC,CANDIDATE_BYTES,341U,204U)==actual);
    check(call(0x101U,CANDIDATE_CRC,CANDIDATE_BYTES,342U,203U)==actual);
    for(unsigned at: {0U,4U,8U,12U,16U,24U,28U,40U,17099U}){
        w[at]^=1;
        check(call(0x101U,CANDIDATE_CRC,CANDIDATE_BYTES,342U,204U)==actual);
        w[at]^=1;
    }
    check(policy_source_crc(0x101U,nullptr,17100,0x12345678,4096,342,204)==0);
    check(policy_source_crc(0x101U,w.data(),31,0x12345678,4096,342,204)==0);
    check(policy_source_crc(0x101U,w.data(),unsigned(w.size()),CANDIDATE_CRC,CANDIDATE_BYTES,342,204)==actual);
    for(unsigned at: {0U,8U,12U,16U,20U,80U,unsigned(mesh.size()-1U)}){
        mesh[at]^=1;
        check(call(0x101U,CANDIDATE_CRC,CANDIDATE_BYTES,342U,204U)==actual);
        mesh[at]^=1;
    }
    check(policy_source_crc(0x101U,w.data(),unsigned(w.size()),CANDIDATE_CRC,CANDIDATE_BYTES,342,204,mesh.data(),nullptr)==actual);
    std::cout<<checks<<" consumer checks passed\\n";
}
'''.replace("CANDIDATE_CRC", hex(mesh_crc) + "U").replace("CANDIDATE_BYTES", str(mesh_bytes) + "U"))
    enabled = flags + ["-I" + str(out), "-DRE4DC_WORLD_REBUILD27=1"]
    result = run(enabled + [str(source), "-o", str(out / "consumer")])
    if result.returncode:
        raise RuntimeError(result.stderr)
    result = run([str(out / "consumer"), str(args.world.resolve()), str(args.mesh.resolve())])
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    (out / "consumer.log").write_text(result.stdout + result.stderr)
    private.write_text(private.read_text().replace("0x68100b21U", "0x68100b20U"))
    refused = run(enabled + ["-fsyntax-only", str(source)])
    (out / "wrong-source.log").write_text(refused.stderr)
    if refused.returncode == 0 or "static assertion failed" not in refused.stderr:
        raise AssertionError("Wrong source certificate was accepted")
    receipt = {
        "scope": "source/host only; actual private candidate and mutations", "consumer": result.stdout.strip(),
        "off_tokens_identical": True, "wrong_source_compile_refused": True,
        "world_sha256": hashlib.sha256(args.world.read_bytes()).hexdigest(),
        "mesh_sha256": hashlib.sha256(mesh).hexdigest(),
        "header_sha256": hashlib.sha256(header.read_bytes()).hexdigest(),
        "target": "not run", "physical_console": "not run",
    }
    (out / "RESULT.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
