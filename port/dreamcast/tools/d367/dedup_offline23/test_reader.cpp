// Host-only semantic and no-allocation admission test for the real R4IM reader.
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <iterator>
#include <new>
#include <vector>
#include "../../../room/instanced_mesh.hpp"
static bool watch=false;static unsigned allocations=0;
void* operator new(std::size_t n){if(watch)++allocations;if(auto* p=std::malloc(n))return p;throw std::bad_alloc();}
void operator delete(void* p)noexcept{std::free(p);}
void operator delete(void* p,std::size_t)noexcept{std::free(p);}
using namespace re4dc::room;
std::vector<std::uint8_t> read(const char* path){std::ifstream f(path,std::ios::binary);if(!f)throw std::runtime_error(path);return {std::istreambuf_iterator<char>(f),{}};}
bool adopt(MeshPackage& p,const std::vector<std::uint8_t>& b){allocations=0;watch=true;const bool ok=p.adopt(b.data(),b.size(),true,true);watch=false;if(allocations)throw std::runtime_error("reader allocated");return ok;}
std::vector<CompactVertex12> stream(const MeshPackage& p){
    std::vector<CompactVertex12> out;
    for(unsigned i=0;i<p.header().meshlet_count;++i){
        const auto& l=p.meshlets()[i];const auto* v=p.vertices()+l.first_vertex;
        auto s=p.strip_begin(l);const auto end=s+l.strip_bytes;
        while(s<end){const unsigned n=*s++;for(unsigned k=0;k<n;++k){
            const unsigned j=s[k];const auto& in=v[p.indexed(l)?p.pool_offsets(l)[j]:j];auto c=in;
#if RE4DC_SCENERY_DEDUP==3
            if(p.repeat_count(l)){
                const auto& xyz=p.offline_position(v,l.vertex_count-p.repeat_count(l),l.vertex_count,in);
                c.x=xyz.x;c.y=xyz.y;c.z=xyz.z;
            }
#endif
            out.push_back(c);
        }s+=n;}
    }
    return out;
}
int main(int argc,char** argv){
    if(argc<3 || argc>4)return 2;auto a=read(argv[1]),b=read(argv[2]);MeshPackage pa,pb;
    if(!adopt(pa,a)){std::cerr<<"base "<<pa.error()<<'\n';return 3;}
#if RE4DC_SCENERY_DEDUP==3
    if(!adopt(pb,b)){std::cerr<<"encoded "<<pb.error()<<'\n';return 4;}
    if(pb.source_crc()!=pa.header().crc || pb.source_bytes()!=pa.header().bytes)return 18;
    const auto sa=stream(pa),sb=stream(pb);
    if(sa.size()!=sb.size() || std::memcmp(sa.data(),sb.data(),sa.size()*sizeof(sa[0])))return 5;
    if(argc==4){
        auto g=read(argv[3]);std::uint32_t groups=0;std::memcpy(&groups,g.data()+12,4);
        watch=true;allocations=0;const bool ok=pb.offline_groups(g.data()+32,g.size()-32,groups);watch=false;
        if(!ok || allocations)return 9;
        // An out-of-range corner span must not be published even if a file CRC was repaired.
        bool changed=false;
        for(unsigned i=0;i<pb.header().meshlet_count && !changed;++i)for(unsigned j=0;j<groups && !changed;++j){
            const auto off=32+16*(i*groups+j);std::uint16_t end=0;std::memcpy(&end,g.data()+off+12,2);
            if(end){g[off+15]=255;changed=true;}
        }
        if(pb.offline_groups(g.data()+32,g.size()-32,groups))return 10;
    }
    const auto source_crc=pb.source_crc(),source_bytes=pb.source_bytes();pb.close();
    if(!pb.offline_dedup() || pb.source_crc()!=source_crc || pb.source_bytes()!=source_bytes || pb.valid())return 11;
    if(!adopt(pb,b))return 12; // close -> reread -> adopt keeps the exact stored layout
    if(!adopt(pb,a) || pb.offline_dedup())return 13; // next ordinary room clears the old marker
    if(!adopt(pb,b))return 14;
    unsigned chosen=0;while(chosen<pb.header().meshlet_count && !pb.repeat_count(pb.meshlets()[chosen]))++chosen;
    if(chosen==pb.header().meshlet_count)return 6;
    const auto l=pb.meshlets()[chosen];const auto off=pb.header().vertex_offset+12*(l.first_vertex+l.vertex_count-pb.repeat_count(l));
    for(unsigned kind=0;kind<5;++kind){auto bad=b;
        if(kind==0)bad[76]^=1; // unknown marker
        if(kind==1){const std::uint16_t chain=l.vertex_count-pb.repeat_count(l);std::memcpy(bad.data()+off,&chain,2);}
        if(kind==2)bad[off+2]^=1; // broken repeat tag
        if(kind==3){const std::uint16_t wrong=std::uint16_t((l.vertex_count<<7)|pb.strip_total(l));std::memcpy(bad.data()+pb.header().meshlet_offset+28*chosen+14,&wrong,2);}
        if(kind==4){const std::uint32_t short_extent=std::uint32_t(b.size()-1);std::memcpy(bad.data()+68,&short_extent,4);}
        // A rejected replacement must unpublish an earlier successful bind.
        MeshPackage reject;if(!adopt(reject,b))return 16;
        if(adopt(reject,bad) || reject.valid()){std::cerr<<"accepted/stale malformed "<<kind<<'\n';return 7;}
        if(!adopt(reject,a) || reject.offline_dedup())return 17;
    }
    std::cout<<"PASS ordered corners="<<sa.size()<<" no reader allocations; malformed marker/source/tag/count refused\n";
#else
    if(adopt(pb,b)){std::cerr<<"default reader accepted encoded strip count\n";return 8;}
    std::cout<<"PASS base admitted; default reader refused encoded package\n";
#endif
}