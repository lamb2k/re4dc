#pragma once
#include <cstdint>
#include <cstring>

// WORLD_METER only. All seven identity words belong to the measured window:
// room, Options View, PVS mode, opaque override, XLU override, shell override, package generation.
namespace re4dc::pvs23 {
constexpr unsigned kIdentityWords=7;
inline bool same(const unsigned* a,const unsigned* b){
    return std::memcmp(a,b,kIdentityWords*sizeof(unsigned))==0;
}
struct Geometry {
    std::uint64_t transformed[3]{},input_inside[3]{};
    void add(unsigned pass,const std::uint8_t* codes,unsigned n,unsigned mask){
        if(pass>=3)return;
        transformed[pass]+=n;
        // Mask 0: classify() already proved the whole cache interval inside.
        // Screen-only checks likewise have a proved near/far interior bound.
        if(!mask){input_inside[pass]+=n;return;}
        for(unsigned i=0;i<n;++i)if(!(codes[i]&mask))++input_inside[pass];
    }
    void clear(){*this=Geometry{};}
};
}
