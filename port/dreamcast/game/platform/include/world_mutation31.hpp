// Build31 EF09: the existing PS2 package publisher's non-wrapping lifetime.
// A token only names a publication made by the named loader/movie paths. It
// does not certify arbitrary writes to package, material or texture bytes.
#pragma once
#include <climits>

namespace re4dc::world_mutation31 {
inline bool live(unsigned generation,bool published){
    return published && generation && generation!=UINT_MAX;
}
inline void revoke(unsigned& generation,bool& published){
    published=false;
    if(generation!=UINT_MAX)++generation;
}
inline bool publish(unsigned generation,bool& published){
    published=generation && generation!=UINT_MAX;
    return published;
}
}
