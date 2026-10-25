#pragma once
// Build 12 SDS1: reuse the established position/UV/colour kernel directly on
// the current SQ slot. No transformed RAM cache, output-index read or new
// assembly. The caller proves the whole bound inside and owns the SQ lock.
#include "mesh_fastpath.hpp"
#if defined(__sh__)
#include <dc/sq.h>
#endif

namespace re4dc::scenery_data {
struct SqCommit {
    void operator()(std::uint32_t* slot)const{
#if defined(RE4DC_SCENERY_DIRECT_HOST_COMMIT)
        RE4DC_SCENERY_DIRECT_HOST_COMMIT(slot);
#elif defined(__sh__)
        sq_flush(slot);
#else
        (void)slot;
#endif
    }
};

// Commit is also the controlled sink seam: tests record exactly the eight
// words written before each burst. Production never reads store-queue memory.
template<class Commit=SqCommit>
inline std::uint32_t* emit_direct_strip(std::uint32_t* sq,const vp::Vertex12* in,
                                        unsigned count,const vp::Constants& constants,Commit commit={}){
    for(unsigned i=0;i<count;++i,sq+=8){
        auto* vertex=reinterpret_cast<pvr_vertex_t*>(sq);
        vertex->flags=i+1U==count?PVR_CMD_VERTEX_EOL:PVR_CMD_VERTEX;
        vertex->oargb=0;
        vp::transform<vp::kChecksNone>(in+i,1,vertex,nullptr,constants);
        commit(sq);
    }
    return sq;
}
}
