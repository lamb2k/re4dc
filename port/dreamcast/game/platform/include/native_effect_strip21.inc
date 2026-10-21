// FX_STRIP21: current source view-space quads through the existing effect FIFO.
// Included once beside effect_line. No frame owner, source pointer retention,
// private heap or new texture cache. Packet count is bounded by two near-clipped
// source GX_QUADS triangles, at most 12 vertices.
#include "effect_strip_geometry21.hpp"
#if RE4DC_NATIVE_FOG
extern "C" unsigned re4dc_fog_enabled();
#endif
namespace {
DeferredLighting* const kEffectQuad21Tag=reinterpret_cast<DeferredLighting*>(0x5354);
constexpr unsigned kEffectQuad21Node=(sizeof(DeferredPart)+31)&~31U;
}
extern "C" int re4dc_effect_quad(const Re4dcEffectQuad* q){
    if(!q || !frame_ready || stream_aborted || draining_parts || direct_open)return 0;
#if defined(RE4DC_PVR_RTT) && RE4DC_PVR_RTT
    if(rtt::capture_slot>=0)return 0; // RTT strips need their capture-owner contract
#endif
    if((q->color>>24)==0)return 1;
    alignas(32) pvr_vertex_t vertices[12];
    const unsigned count=re4dc::effect_strip21::vertices(*q,vertices);
    if(!count)return 1;
#if defined(RE4DC_FX_CORE_TEX_PREP) && RE4DC_FX_CORE_TEX_PREP
    fxCoreBeginFxFrame();
#else
    if(fx_frame!=frame){fx_frame=frame;fx_count=0;
#if defined(RE4DC_EFFECT_ROOM) && RE4DC_EFFECT_ROOM
        fx_new_loads=0;
#endif
    }
#endif
    if(fx_count>=RE4DC_EFFECT_SPRITE_MAX){++fx_capped;return 0;}
#if defined(RE4DC_EFFECT_ROOM) && RE4DC_EFFECT_ROOM
    fx_resident_only=frame-fx_evict_frame<=1 || fx_new_loads>=kFxNewLoads;
#if defined(RE4DC_FX_TEX_POOL) && RE4DC_FX_TEX_POOL
    if(!fx_pool_full && fx_new_loads<kFxNewLoads)fx_resident_only=false;
#endif
    const unsigned opens=load_opens;
#endif
#if RE4DC_UI_HANDLES
    Entry* e=resolve(q->image,nullptr,true);
#else
    Entry* e=load(q->image);
#endif
#if defined(RE4DC_EFFECT_ROOM) && RE4DC_EFFECT_ROOM
    fx_resident_only=false;fx_new_loads+=load_opens-opens;
#endif
#if defined(RE4DC_FX_CORE_TEX_PREP) && RE4DC_FX_CORE_TEX_PREP
    fxCoreTextureAcquired(q->image,e);
#endif
    if(!e){++fx_missing;return 0;}
#if defined(RE4DC_FX_TEX_POOL) && RE4DC_FX_TEX_POOL
    // Share the ordinary effect pool's room budget and retirement bookkeeping.
    {const unsigned i=unsigned(e-entries);
     if(i<kTextureCount && !fx_pool_pin[i] && e->valid){const unsigned bytes=e->package.vram_bytes();
         if(fx_pool_bytes+bytes<=unsigned(RE4DC_FX_TEX_POOL)*1024U){fx_pool_pin[i]=true;fx_pool_size[i]=bytes;fx_pool_bytes+=bytes;++fx_pool_pins;}
         else fx_pool_full=1;
     }}
#endif
    const auto& t=e->package.textures()[0];
    // Preserve repeating-source extent. Padding may only scale clamped axes.
    if((q->wrap_s && q->image.width!=t.width)||(q->wrap_t && q->image.height!=t.height))return 0;
    const float su=float(q->image.width)/float(t.width),sv=float(q->image.height)/float(t.height);
    for(unsigned i=0;i<count;++i){vertices[i].u*=su;vertices[i].v*=sv;}
    alignas(32) pvr_vertex_t packet[13];
    pvr_poly_cxt_t c;pvr_poly_cxt_txr(&c,PVR_LIST_TR_POLY,re4dc::texture::pvr_format(t),
        RE4DC_TSP_W(t),RE4DC_TSP_H(t),e->package.pvr_texture(0),PVR_FILTER_BILINEAR);
    c.gen.culling=PVR_CULLING_NONE;c.depth.comparison=PVR_DEPTHCMP_GEQUAL;c.depth.write=PVR_DEPTHWRITE_DISABLE;
    c.blend.src=(pvr_blend_mode_t)q->src;c.blend.dst=(pvr_blend_mode_t)q->dst;
    c.txr.env=PVR_TXRENV_MODULATEALPHA;c.txr.alpha=PVR_TXRALPHA_ENABLE;
    c.txr.uv_clamp=(pvr_uv_clamp_t)((q->wrap_s?0:PVR_UVCLAMP_U)|(q->wrap_t?0:PVR_UVCLAMP_V));
#if RE4DC_NATIVE_FOG
    c.gen.fog_type=re4dc_fog_enabled()?PVR_FOG_TABLE:PVR_FOG_DISABLE;
#endif
    pvr_poly_compile(reinterpret_cast<pvr_poly_hdr_t*>(packet),&c);
    std::memcpy(packet+1,vertices,count*sizeof(pvr_vertex_t));
    const unsigned bytes=(count+1)*sizeof(pvr_vertex_t);
    if(source_draws_finished){
        stream_select(PVR_LIST_TR_POLY);if(stream_aborted)return 0;
        e->frame=frame;stream_send(packet,bytes);++fx_direct;++fx_count;return 1;
    }
    const unsigned required=kEffectQuad21Node+bytes,margin=8192;
    unsigned char* storage=frame_storage;unsigned* top=&deferred_top;
    if(required+margin>deferred_top || deferred_top-required-margin<std::max(8192U,nquad*unsigned(sizeof(Re4dcUiQuad)))){
        if(!deferred_spill){deferred_spill=static_cast<unsigned char*>(re4dc_model_deferred_storage(&deferred_spill_capacity));deferred_spill_top=deferred_spill_capacity;}
        if(!deferred_spill || required>deferred_spill_top){++fx_dropped;RE4DC_FQ_DROP(true,required);return 0;}
        storage=deferred_spill;top=&deferred_spill_top;
    }
    *top-=required;auto* node=new(storage+*top) DeferredPart{};
    node->lighting=kEffectQuad21Tag;node->changed[0]=bytes;
    std::memcpy(storage+*top+kEffectQuad21Node,packet,bytes);
    if(deferred_last)deferred_last->next=node;else deferred_first=node;
    deferred_last=node;++deferred_count;e->frame=frame;
    ++fx_queued;++fx_count;fx_peak=std::max(fx_peak,fx_count);
    frame_queue_peak=std::max(frame_queue_peak,unsigned(sizeof(frame_storage))-deferred_top+deferred_spill_capacity-deferred_spill_top);
    return 1;
}
