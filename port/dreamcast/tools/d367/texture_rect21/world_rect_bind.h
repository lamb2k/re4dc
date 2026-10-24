#pragma once
#include <cstdint>

// This private-candidate adapter is uninstalled unless its caller opts in.
// It only describes selected native world direct packets. It grants no generic
// model/actor/UI or legacy world-packet admission.
namespace re4dc::rect21 {
struct Descriptor {
    unsigned width,height,format,flags,payload,bytes,checksum;
};
struct Representation {
    unsigned crc,fnv,logical_width,logical_height;
    Descriptor stored;
    float u_scale,v_scale;
};
inline constexpr Representation qualified[] = {
#if defined(RE4DC_FOLIAGE_MIP24) && RE4DC_FOLIAGE_MIP24
// lane mip-finish24: the same 798 keys, 86 foliage/cut-out rows rebound to the fol24 pack's coverage mip chains
#include "scoped_representations_fol24.inc"
#else
#include "scoped_representations.inc"
#endif
};
inline constexpr unsigned qualified_count=sizeof(qualified)/sizeof(qualified[0]);
constexpr bool keys_ordered() {
    for(unsigned i=1;i<qualified_count;++i) {
        const auto& a=qualified[i-1];const auto& b=qualified[i];
        if(a.crc>b.crc || (a.crc==b.crc && a.fnv>=b.fnv))return false;
    }
    return true;
}
static_assert(qualified_count==798U && keys_ordered());

// Pinned KOS pvr_poly_compile stores log2(size)-3 in TSP bits 5..3/2..0.
// A retired Entry can reuse its slot/address. Reject a cached physical extent
// from another selected representation before considering a header-cache hit.
inline bool header_dimensions(unsigned tsp,unsigned width,unsigned height) {
    if(width<8 || height<8 || width>1024 || height>1024 ||
       (width&(width-1)) || (height&(height-1)))return false;
    const unsigned w=unsigned(__builtin_ctz(width))-3U;
    const unsigned h=unsigned(__builtin_ctz(height))-3U;
    return (tsp&63U)==((w<<3)|h);
}

inline bool adapt(unsigned crc,unsigned fnv,unsigned width,unsigned height,
                  const Descriptor& actual,float& u,float& v,bool enabled=false) {
    if(!enabled)return false;
    // Immutable sorted keys avoid scanning 792 descriptors per direct packet.
    // Use unsigned comparisons without SH-4 64-bit arithmetic or a mutable index.
    unsigned lo=0,hi=qualified_count;
    while(lo<hi) {
        const unsigned mid=lo+(hi-lo)/2U;
        const auto& candidate=qualified[mid];
        if(candidate.crc<crc || (candidate.crc==crc && candidate.fnv<fnv))lo=mid+1U;
        else hi=mid;
    }
    if(lo==qualified_count)return false;
    const auto& r=qualified[lo];const auto& s=r.stored;
    if(r.crc!=crc || r.fnv!=fnv || r.logical_width!=width || r.logical_height!=height ||
       actual.width!=s.width || actual.height!=s.height || actual.format!=s.format ||
       actual.flags!=s.flags || actual.payload!=s.payload || actual.bytes!=s.bytes ||
       actual.checksum!=s.checksum)return false;
    // Publish neither scale until the complete immutable descriptor matches.
    u=r.u_scale;v=r.v_scale;return true;
}
}
