// chunk_submit.cpp: the shared chunk-submit back end (chunk_submit.h; lane scenery19). Built with CHUNK_SUBMIT=1 (otherwise empty).
// Cache layout (lent by the caller): [0, 8192) 256 corner vertices (32 B, pvr_vertex_t), [8192, 12288) 256 points
// {x, y, 1/w, pad} (16 B), [12288, 12544) corner outcodes, [12544, 12800) point outcodes.
#if defined(RE4DC_CHUNK_SUBMIT) && RE4DC_CHUNK_SUBMIT
#include "chunk_submit.h"
#if defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT
#include "include/draw_fallback_audit.h"
#endif
#include "re4dc_screen.h"
#include <kos.h>
#include <cstdint>
#include <cstring>
#include "../../room/mesh_fastpath.hpp"

namespace {
constexpr unsigned kPointOff=256U*32U,kCornerCodeOff=kPointOff+256U*16U,kPointCodeOff=kCornerCodeOff+256U;
inline pvr_vertex_t* verts(re4dc_chunk_sink* s){return reinterpret_cast<pvr_vertex_t*>(s->cache);}
inline float* pts(re4dc_chunk_sink* s){return reinterpret_cast<float*>(s->cache+kPointOff);}
inline std::uint8_t* ccodes(re4dc_chunk_sink* s){return s->cache+kCornerCodeOff;}
inline std::uint8_t* pcodes(re4dc_chunk_sink* s){return s->cache+kPointCodeOff;}
constexpr unsigned kScreen=re4dc::vp::screen_mask(re4dc::vp::kChecksAll),kDepth=re4dc::vp::depth_mask(re4dc::vp::kChecksAll);

// One strip's AND / OR of its corners' outcodes; idx: n index bytes (actor form: bit 7 masked off).
inline re4dc::vp::StripCodes codes_of(const std::uint8_t* oc,const std::uint8_t* idx,unsigned n,unsigned mask){
    unsigned all=0xff,any=0;
    for(unsigned k=0;k<n;++k){const unsigned c=oc[idx[k]&mask];all&=c;any|=c;}
    return {all,any};
}
// Store-queue send of n corners by index (actor form: bit 7 masked off), EOL on the last.
inline std::uint32_t* send(std::uint32_t* sq,const pvr_vertex_t* v,const std::uint8_t* idx,unsigned n,unsigned mask){
    if(mask==0xffU)return re4dc::vp::emit_sq(sq,v,idx,n);
    std::uint8_t tmp[256];
    for(unsigned k=0;k<n;++k)tmp[k]=std::uint8_t(idx[k]&mask);
    return re4dc::vp::emit_sq(sq,v,tmp,n);
}
}

extern "C" {
void re4dc_chunk_window_begin(re4dc_chunk_sink* s,std::uint32_t* sq,void* cache,unsigned limit,re4dc_chunk_clip_fn clip,
                              void* clip_ctx){
    s->sq=sq;s->cache=static_cast<std::uint8_t*>(cache);s->clip=clip;s->clip_ctx=clip_ctx;s->limit=limit;
    s->points=s->corners=0;s->slots=s->strips=s->culled=s->clipped=0;
    s->vsrc=s->cache;s->csrc=s->cache+kCornerCodeOff;
}
void re4dc_chunk_header(re4dc_chunk_sink* s,const std::uint32_t words[8]){
    std::uint32_t* q=s->sq;
    for(unsigned i=0;i<8;++i)q[i]=words[i];
    __asm__ __volatile__("pref @%0" : : "r"(q) : "memory");
    s->sq=q+8;
}
void re4dc_chunk_points_grid(re4dc_chunk_sink* s,const std::uint16_t* xyz,unsigned stride,unsigned n,float near_distance,
                             float far_distance){
    float* p=pts(s);std::uint8_t* oc=pcodes(s);
    const auto* b=reinterpret_cast<const std::uint8_t*>(xyz);
    for(unsigned i=0;i<n;++i,b+=stride,p+=4){
        const auto* v=reinterpret_cast<const std::uint16_t*>(b);
        float x=float(v[0]),y=float(v[1]),z=float(v[2]),w=1.0f;
        VP_FTRV(x,y,z,w);
        // 1/w as the HW_LEAN transform: fsrra(w * w)
        float inv=w*w;
        __asm__("fsrra %0" : "+f"(inv));
        const float sx=x*inv,sy=y*inv;
        p[0]=sx;p[1]=sy;p[2]=inv;p[3]=0.0f;
        unsigned code=(sx<0.0f?8U:0U)|(sx>RE4DC_SCREEN_WF?4U:0U)|(sy<0.0f?2U:0U)|(sy>RE4DC_SCREEN_HF?1U:0U);
        code=(code<<2)|(w<near_distance?2U:0U)|(w>far_distance?1U:0U);
        oc[i]=std::uint8_t(code);
    }
    s->points=n;
}
void re4dc_chunk_points_screen(re4dc_chunk_sink* s,const float* xy_invw,const std::uint8_t* outcodes,unsigned n){
    float* p=pts(s);
    for(unsigned i=0;i<n;++i,p+=4,xy_invw+=3){p[0]=xy_invw[0];p[1]=xy_invw[1];p[2]=xy_invw[2];p[3]=0.0f;}
    std::memcpy(pcodes(s),outcodes,n);
    s->points=n;
}
void re4dc_chunk_corners(re4dc_chunk_sink* s,const std::uint8_t* point,const float* uv,const std::uint32_t* argb,unsigned n){
    pvr_vertex_t* v=verts(s);const float* p=pts(s);const std::uint8_t* pc=pcodes(s);std::uint8_t* oc=ccodes(s);
    for(unsigned i=0;i<n;++i){
        const float* q=p+4U*point[i];
        v[i].flags=PVR_CMD_VERTEX;v[i].x=q[0];v[i].y=q[1];v[i].z=q[2];
        v[i].u=uv[2*i];v[i].v=uv[2*i+1];v[i].argb=argb[i];v[i].oargb=0;
        oc[i]=pc[point[i]];
    }
    s->corners=n;s->vsrc=v;s->csrc=oc;
}
void re4dc_chunk_vertices_direct(re4dc_chunk_sink* s,const void* vertices,const std::uint8_t* outcodes,unsigned n){
    s->vsrc=vertices;s->csrc=outcodes;s->corners=n;
}
const void* re4dc_chunk_vertices(const re4dc_chunk_sink* s){return s->vsrc;}
const std::uint8_t* re4dc_chunk_outcodes(const re4dc_chunk_sink* s){return s->csrc;}
std::uint32_t** re4dc_chunk_sq(re4dc_chunk_sink* s){return &s->sq;}
int re4dc_chunk_strips(re4dc_chunk_sink* s,const std::uint8_t* strips,unsigned strip_bytes,unsigned form){
    const std::uint8_t* const end=strips+strip_bytes;
    const auto* v=static_cast<const pvr_vertex_t*>(s->vsrc);const std::uint8_t* oc=s->csrc;
    const unsigned mask=form==RE4DC_CHUNK_STRIPS_ACTOR?0x7fU:0xffU;
    while(strips<end){
        unsigned n;const std::uint8_t* idx;
        if(form==RE4DC_CHUNK_STRIPS_ACTOR){idx=strips;n=1;while(!(idx[n-1]&0x80U))++n;strips+=n;}
        else {n=*strips++;idx=strips;strips+=n;}
        const re4dc::vp::StripCodes c=codes_of(oc,idx,n,mask);
        if(c.all&kDepth){++s->culled;continue;}
        if((c.any&kDepth) || n>s->limit){
#if defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT
            // Capacity takes precedence when both predicates are true.
            if(s->clip)re4dc::dfa26::hit(n>s->limit?re4dc::dfa26::ChunkClipCapacity:re4dc::dfa26::ChunkClipDepth);
#endif
            ++s->clipped;
            const int r=s->clip?s->clip(s->clip_ctx,idx,n,form):1;
            if(r<=0)return r;
            continue;
        }
        if(c.all&kScreen){++s->culled;continue;}
        s->sq=send(s->sq,v,idx,n,mask);s->slots+=n;++s->strips;
    }
    return 1;
}
std::uint32_t* re4dc_chunk_window_end(re4dc_chunk_sink* s){return s->sq;}
}
#endif
