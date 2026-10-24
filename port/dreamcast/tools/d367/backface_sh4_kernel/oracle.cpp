// Compile the ACTUAL original C strip routine, with a 32-byte test PVR type.
#include "backface_emit.hpp"
#include <cstring>
extern "C" unsigned backface_oracle(const pvr_vertex_t* cache,const std::uint8_t* indices,
    unsigned n,unsigned mask,unsigned cull,pvr_vertex_t* out,unsigned* pieces) {
    unsigned sent=0;
    *pieces=0;
    auto emit=[&](const std::uint8_t* ix,unsigned count) {
        ++*pieces;
        for(unsigned i=0;i<count;++i) {
            std::memcpy(out+sent,cache+ix[i],32);
            if((mask&255U)==127U) out[sent].flags=PVR_CMD_VERTEX;
            if(i+1==count) out[sent].flags=PVR_CMD_VERTEX_EOL;
            ++sent;
        }
    };
    if(cull!=1U && cull!=2U) return 0;
    if((mask&255U)!=127U && (mask&255U)!=255U) return 0;
    if(mask&256U) {
        unsigned a=0;
        for(unsigned i=0;i<n;++i) {
            if(indices[i]&128U) {
                re4dc::bf::strip(cache,indices+a,i+1-a,mask&255U,cull,emit);
                a=i+1;
            }
        }
        if(a<n) re4dc::bf::strip(cache,indices+a,n-a,mask&255U,cull,emit);
    } else re4dc::bf::strip(cache,indices,n,mask&255U,cull,emit);
    return sent;
}
