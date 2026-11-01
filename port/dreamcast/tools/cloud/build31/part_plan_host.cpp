#include "../../../game/platform/include/world_part_plan29.hpp"
#include <array>
#include <cassert>
#include <cstdio>
#include <vector>
struct Meta {std::uint32_t crc,fnv;std::uint16_t width,height;std::uint8_t pass,cull,texture,reserved;};
struct Header {unsigned mesh_count,part_count;};
struct Mesh {unsigned first_part,part_count;};
struct Part {unsigned meshlet_count;};
struct Package {
    Header h;std::vector<Mesh> m;std::vector<Part> p;
    const Header& header()const{return h;}const Mesh* meshes()const{return m.data();}const Part* parts()const{return p.data();}
};
static unsigned selected(const Meta& m,unsigned foliage,unsigned trans){
    if(m.reserved&1U)return m.pass;
    if(m.pass==2 && foliage)return foliage==3?3U:1U;
    if(m.pass==2 && trans)return trans==3?3U:trans-1U;
    return m.pass;
}
int main(){
    using namespace re4dc::wp29;
    alignas(32) unsigned char memory[kMaxBytes];
    Package pk{{6,48},{},{}};std::vector<Meta> meta;
    for(unsigned m=0;m<6;++m)pk.m.push_back({m*8,8});
    for(unsigned p=0;p<48;++p){pk.p.push_back({1+p%300});meta.push_back({p*33,p*23,64,128,std::uint8_t(p%3),std::uint8_t(p%3),std::uint8_t(p),std::uint8_t((p/3)%2)});}
    const auto original=meta;unsigned cases=0;
    for(unsigned foliage=0;foliage<2;++foliage)for(unsigned trans=0;trans<2;++trans){
        Layout layout;assert(compile(memory,sizeof(memory),pk,meta.data(),foliage,trans,layout));
        const auto* spans=reinterpret_cast<const Span*>(memory);const auto* records=reinterpret_cast<const Record*>(memory+layout.offset);
        for(unsigned f=0;f<(foliage?4U:1U);++f)for(unsigned t=0;t<(trans?4U:1U);++t)
        for(unsigned m=0;m<6;++m)for(unsigned pass=0;pass<3;++pass){
            std::vector<unsigned> expected,actual;
            for(unsigned i=m*8;i<(m+1)*8;++i)if(selected(meta[i],f,t)==pass)expected.push_back(i);
            const auto& span=spans[3*m+pass];
            unsigned prev=0;
            for(unsigned k=0;k<span.count;++k){
                const auto& r=records[span.first+k];assert(!k || r.index>prev);prev=r.index;
                const Meta restored=metadata<Meta>(r);assert(std::memcmp(&restored,&meta[r.index],sizeof(Meta))==0);
                assert(r.key[4]==pass && r.key[5]==restored.cull && r.meshlets==pk.p[r.index].meshlet_count);
                if(selected(restored,f,t)==pass)actual.push_back(r.index);
            }
            assert(actual==expected);++cases;
        }
        assert(std::memcmp(original.data(),meta.data(),meta.size()*sizeof(Meta))==0);
        Layout invalid;
        assert(!compile(memory+1,sizeof(memory)-1,pk,meta.data(),foliage,trans,invalid));
        assert(!compile(memory,layout.bytes-1,pk,meta.data(),foliage,trans,invalid));
    }
    Layout invalid;
    meta[0].pass=3;assert(!measure(pk,meta.data(),false,false,invalid));meta=original;
    pk.p[0].meshlet_count=65536;assert(!measure(pk,meta.data(),false,false,invalid));pk.p[0].meshlet_count=1;
    pk.m[0].first_part=49;assert(!measure(pk,meta.data(),false,false,invalid));pk.m[0]={0,8};
    pk.h.mesh_count=3000;assert(!measure(pk,meta.data(),false,false,invalid));pk.h.mesh_count=6;
    pk.h.part_count=65537;assert(!measure(pk,meta.data(),false,false,invalid));pk.h.part_count=48;
    assert(!measure(pk,static_cast<const Meta*>(nullptr),false,false,invalid));
    std::printf("PASS part plan: %u ordered live-policy cases + bounds/alignment/capacity/source identity\n",cases);
}
