#pragma once
#include "static_obj_lifetime05.hpp"
extern "C" void re4dc_static_free(void*);
namespace re4dc { namespace sob05 {
// Compare an out-of-band snapshot after an allocator/callback can retire or
// replace the room cell. Do not inspect either payload to establish currency.
template<class T> bool current(Cell<T>& owner,const Cell<T>& held){
    return owner.get()==held.pointer && held.pointer &&
        owner.generation==held.generation && owner.incarnation==held.incarnation;
}
// A refused publication can still return a live ordinary allocation, including
// the exhausted-token case. Return only that current allocation to the heap.
inline void discard(void* p,unsigned bytes){
    unsigned generation=0;
    if(re4dc_room4_live_generation(&generation) && re4dc_room4_cell_valid(p,bytes,generation))
        re4dc_static_free(p);
}
}}
