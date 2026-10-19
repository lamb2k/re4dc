// Host format/cache-contract check. Inputs are private generated assets, never committed.
#include "../../../room/world_plan.hpp"
#include <cassert>
#include <fstream>
#include <iostream>
#include <iterator>
#include <vector>
using re4dc::worldplan::View;
int main(int argc,char** argv){
    assert(argc==2);std::ifstream f(argv[1],std::ios::binary);
    std::vector<std::uint8_t> bytes((std::istreambuf_iterator<char>(f)),{});assert(bytes.size()>=128);
    const auto* w=reinterpret_cast<const std::uint32_t*>(bytes.data());
    const std::vector<std::uint8_t> original=bytes;
    auto adopt=[&](View& v,unsigned size){return v.adopt(bytes.data(),size,w[2],w[10],w[8],w[9],w[4],w[5],w[6],w[30],w[31]);};
    View v;assert(adopt(v,bytes.size()));unsigned combinations=0;
    for(unsigned i=0;i<w[2];++i){
        unsigned n;const auto* g=v.groups(i,n);
        for(unsigned bits=0;bits<(1U<<n);++bits){
            std::uint16_t a[8],b[8];unsigned lo,hi,cut;
            const unsigned nr=View::select(g,n,bits,a,b,lo,hi,cut);
            assert(nr+cut==n && View::selected(g,n,b,nr)==bits);
            unsigned previous=0,j=0,l=255,h=0;
            for(unsigned k=0;k<n;++k){
                if(bits&(1U<<k)){assert(a[j]==previous && b[j]==g[8*k+6]);++j;
                    l=std::min(l,unsigned(g[8*k+7]&255));h=std::max(h,unsigned(g[8*k+7]>>8));}
                previous=g[8*k+6];
            }
            assert(j==nr && lo==l && hi==h);++combinations;
        }
    }
    float view[12]{},proj[7]{},vp[6]{};
    v.frame(view,proj,vp,25000);v.meshlet(0)=155;v.cluster(0)=2;
    v.frame(view,proj,vp,25000);assert(v.meshlet(0)==155 && v.cluster(0)==2);
    view[3]=1;v.frame(view,proj,vp,25000);assert(!v.meshlet(0) && !v.cluster(0));
    v.meshlet(0)=42;vp[0]=1;v.frame(view,proj,vp,25000);assert(!v.meshlet(0));
    v.meshlet(0)=42;proj[6]=1;v.frame(view,proj,vp,25000);assert(!v.meshlet(0));
    v.meshlet(0)=42;v.frame(view,proj,vp,12000);assert(!v.meshlet(0));
    assert(!adopt(v,bytes.size())); // used scratch cannot be mistaken for fresh compiled input
    bytes=original;
    for(unsigned size=0;size<bytes.size()-100;size+=257)assert(!adopt(v,size));
    const unsigned offsets[]={14,15,16,17,18,20,21,23,25,26,27,28,29};
    for(unsigned field:offsets){auto* m=reinterpret_cast<std::uint32_t*>(bytes.data());const auto old=m[field];m[field]+=4;
        assert(!adopt(v,bytes.size()));m[field]=old;}
    assert(adopt(v,bytes.size()));
    std::cout<<"PASS groups="<<w[2]<<" visibility_combinations="<<combinations
             <<" exact_key_invalidation=4 malformed_offsets=13 bounded_scratch=yes\n";
}
