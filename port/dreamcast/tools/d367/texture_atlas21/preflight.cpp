#include "coarse_actor_preflight.h"
#include <fstream>
#include <vector>
#include <cstdio>
#include <cstdlib>

static std::vector<unsigned char> load(const char* path) {
    std::ifstream file(path,std::ios::binary);
    return {std::istreambuf_iterator<char>(file),std::istreambuf_iterator<char>()};
}
int main(int argc,char** argv) {
    if(argc!=7)return 2;
    auto p=load(argv[1]),n=load(argv[2]),u=load(argv[3]),s=load(argv[4]),w=load(argv[5]);
    re4dc_source::ChunkInput c{{p.data(),p.size()},{n.data(),n.size()},{u.data(),u.size()},
        {s.data(),s.size()},{w.data(),w.size()},unsigned(p.size()/8),unsigned(n.size()/8),
        unsigned(w.size()/16),unsigned(std::strtoul(argv[6],nullptr,10)),119u};
    re4dc_source::ChunkProof proof{};
    const auto error=re4dc_source::preflight_chunk(c,proof);
    std::printf("{\"code\":%u,\"meshlets\":%u,\"records\":%u,\"indices\":%u,\"triangles\":%u}\n",
        unsigned(error),proof.meshlets,proof.records,proof.indices,proof.triangles);
    return error==re4dc_source::BlobError::None?0:1;
}
