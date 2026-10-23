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
    if(!q || !frame_ready || stream_aborted || draining_parts)return 0;
#if RE4DC_TA_DIRECT
    if(direct_open)return 0;
#endif
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
    const unsigned covered_w=RE4DC_COVER_W(e->package,q->image.width),covered_h=RE4DC_COVER_H(e->package,q->image.height);
    if((q->wrap_s && covered_w!=t.width)||(q->wrap_t && covered_h!=t.height))return 0;
    const float su=float(covered_w)/float(t.width),sv=float(covered_h)/float(t.height);
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
    const unsigned required=kEffectQuad21Node+bytes,margin=RE4DC_FX_QUEUE_MARGIN;
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
#if defined(RE4DC_CLOTH_NATIVE) && RE4DC_CLOTH_NATIVE
// CLOTH_NATIVE: an esp4e cloth sheet, one TR strip packet per row pair through the same FIFO node as the quads above.
// A row with a point in front of the near plane goes through re4dc_effect_quad (clipped) cell by cell instead.
namespace {
unsigned cloth21_rows,cloth21_quads,cloth21_drop,cloth21_log_frame,cloth21_calls,cloth21_why[8];float cloth21_last[3];unsigned cloth21_argb,cloth21_cull;
}
extern "C" int re4dc_effect_mesh21(const Re4dcEffectMesh21* m){
    if(++cloth21_calls%30000U==1U)re4dc_log("cloth native: calls=%u why=%u,%u,%u,%u,%u,%u rows=%u culled=%u quads=%u dropped=%u scr=%d,%d,%d argb=%08x\n",cloth21_calls,cloth21_why[0],cloth21_why[1],cloth21_why[2],cloth21_why[3],cloth21_why[4],cloth21_why[5],cloth21_rows,cloth21_cull,cloth21_quads,cloth21_drop,int(cloth21_last[0]),int(cloth21_last[1]),int(cloth21_last[2]*100000.f),cloth21_argb);
    if(!m || !m->positions || m->cols<2 || m->rows<2 || m->cols>100 || m->rows>50){++cloth21_why[0];return 0;}
    if(!frame_ready || stream_aborted || draining_parts){++cloth21_why[1];return 0;}
#if RE4DC_TA_DIRECT
    if(direct_open)return 0;
#endif
#if defined(RE4DC_PVR_RTT) && RE4DC_PVR_RTT
    if(rtt::capture_slot>=0)return 0;
#endif
    if((m->color>>24)==0)return 1;
    if(m->src>7 || m->dst>7 || m->wrap_s>1 || m->wrap_t>1 || m->projection[0]!=0 || m->viewport[2]<=0 || m->viewport[3]<=0){++cloth21_why[2];return 0;}
    const float near=m->projection[6]/(m->projection[5]-1);
    if(!re4dc::render::is_finite(near) || near<=0){++cloth21_why[3];return 0;}
    Re4dcEffectQuad pq{};   // projection context for project() and the clipped fallback cells
    pq.image=m->image;std::memcpy(pq.projection,m->projection,sizeof pq.projection);std::memcpy(pq.viewport,m->viewport,sizeof pq.viewport);
    pq.color=m->color;pq.src=m->src;pq.dst=m->dst;pq.wrap_s=m->wrap_s;pq.wrap_t=m->wrap_t;
#if defined(RE4DC_FX_CORE_TEX_PREP) && RE4DC_FX_CORE_TEX_PREP
    fxCoreBeginFxFrame();
#else
    if(fx_frame!=frame){fx_frame=frame;fx_count=0;
#if defined(RE4DC_EFFECT_ROOM) && RE4DC_EFFECT_ROOM
        fx_new_loads=0;
#endif
    }
#endif
#if defined(RE4DC_EFFECT_ROOM) && RE4DC_EFFECT_ROOM
    fx_resident_only=frame-fx_evict_frame<=1 || fx_new_loads>=kFxNewLoads;
#if defined(RE4DC_FX_TEX_POOL) && RE4DC_FX_TEX_POOL
    if(!fx_pool_full && fx_new_loads<kFxNewLoads)fx_resident_only=false;
#endif
    const unsigned opens=load_opens;
#endif
#if RE4DC_UI_HANDLES
    Entry* e=resolve(m->image,nullptr,true);
#else
    Entry* e=load(m->image);
#endif
#if defined(RE4DC_EFFECT_ROOM) && RE4DC_EFFECT_ROOM
    fx_resident_only=false;fx_new_loads+=load_opens-opens;
#endif
#if defined(RE4DC_FX_CORE_TEX_PREP) && RE4DC_FX_CORE_TEX_PREP
    fxCoreTextureAcquired(m->image,e);
#endif
    if(!e){++fx_missing;++cloth21_why[4];return 0;}
    const auto& t=e->package.textures()[0];
    const unsigned covered_w=RE4DC_COVER_W(e->package,m->image.width),covered_h=RE4DC_COVER_H(e->package,m->image.height);
    if((m->wrap_s && covered_w!=t.width)||(m->wrap_t && covered_h!=t.height)){++cloth21_why[5];return 0;}
    const float su=float(covered_w)/float(t.width),sv=float(covered_h)/float(t.height);
    pvr_poly_cxt_t c;pvr_poly_cxt_txr(&c,PVR_LIST_TR_POLY,re4dc::texture::pvr_format(t),
        RE4DC_TSP_W(t),RE4DC_TSP_H(t),e->package.pvr_texture(0),PVR_FILTER_BILINEAR);
    c.gen.culling=PVR_CULLING_NONE;c.depth.comparison=PVR_DEPTHCMP_GEQUAL;c.depth.write=PVR_DEPTHWRITE_DISABLE;
    c.blend.src=(pvr_blend_mode_t)m->src;c.blend.dst=(pvr_blend_mode_t)m->dst;
    c.txr.env=PVR_TXRENV_MODULATEALPHA;c.txr.alpha=PVR_TXRALPHA_ENABLE;
    c.txr.uv_clamp=(pvr_uv_clamp_t)((m->wrap_s?0:PVR_UVCLAMP_U)|(m->wrap_t?0:PVR_UVCLAMP_V));
#if RE4DC_NATIVE_FOG
    c.gen.fog_type=re4dc_fog_enabled()?PVR_FOG_TABLE:PVR_FOG_DISABLE;
#endif
    alignas(32) pvr_vertex_t packet[1+200];
    pvr_poly_compile(reinterpret_cast<pvr_poly_hdr_t*>(packet),&c);
    const unsigned cols=m->cols;
    const float du=1.0f/float(cols-1),dv=m->v_step,v0=m->v_top;
    int drawn=0;
    for(unsigned r=0;r+1<m->rows;++r){
        const float* top=m->positions+3*r*cols;const float* bot=top+3*cols;
        unsigned behind=0;
        for(unsigned i=0;i<cols;++i){
            behind+=!(-top[3*i+2]>=near);behind+=!(-bot[3*i+2]>=near);
            for(unsigned k=0;k<3;++k)if(!re4dc::render::is_finite(top[3*i+k]) || !re4dc::render::is_finite(bot[3*i+k]))return drawn;
        }
        if(behind==2*cols){++cloth21_cull;continue;}   // the whole row is behind the near plane
        if(behind){   // cell by cell, near-clipped (source quad order: top-left, bottom-left, bottom-right, top-right)
            for(unsigned i=0;i+1<cols;++i){
                Re4dcEffectQuad q=pq;const float* corner[4]={top+3*i,bot+3*i,bot+3*(i+1),top+3*(i+1)};
                const float us[4]={i*du,i*du,(i+1)*du,(i+1)*du},vs[4]={v0+r*dv,v0+(r+1)*dv,v0+(r+1)*dv,v0+r*dv};
                for(unsigned k=0;k<4;++k){for(unsigned a=0;a<3;++a)q.positions[k][a]=corner[k][a];q.u[k]=us[k];q.v[k]=vs[k];}
                if(re4dc_effect_quad(&q))++cloth21_quads;else ++cloth21_drop;
            }
            continue;
        }
        pvr_vertex_t* v=packet+1;
        float x0=1e30f,x1=-1e30f,y0=1e30f,y1=-1e30f;
        for(unsigned i=0;i<cols;++i)for(unsigned s=0;s<2;++s,++v){
            const float* p=(s?bot:top)+3*i;float x=p[0],y=p[1],z=p[2];
            re4dc::effect_strip21::project(x,y,z,&pq);
            x0=std::min(x0,x);x1=std::max(x1,x);y0=std::min(y0,y);y1=std::max(y1,y);
            v->flags=PVR_CMD_VERTEX;v->x=x;v->y=y;v->z=z;v->u=i*du*su;v->v=(v0+(r+s)*dv)*sv;v->argb=m->color;v->oargb=0;
        }
        if(x1<0 || y1<0 || x0>RE4DC_SCREEN_WF || y0>RE4DC_SCREEN_HF){++cloth21_cull;continue;}   // off screen
        packet[2*cols].flags=PVR_CMD_VERTEX_EOL;cloth21_last[0]=packet[1].x;cloth21_last[1]=packet[1].y;cloth21_last[2]=packet[1].z;cloth21_argb=m->color;
        const unsigned bytes=(2*cols+1)*sizeof(pvr_vertex_t);
        if(source_draws_finished){
            stream_select(PVR_LIST_TR_POLY);if(stream_aborted)return drawn;
            stream_send(packet,bytes);++fx_direct;++cloth21_rows;++drawn;continue;
        }
        const unsigned required=kEffectQuad21Node+bytes,margin=8192;
        unsigned char* storage=frame_storage;unsigned* tp=&deferred_top;
        if(required+margin>deferred_top || deferred_top-required-margin<std::max(8192U,nquad*unsigned(sizeof(Re4dcUiQuad)))){
            if(!deferred_spill){deferred_spill=static_cast<unsigned char*>(re4dc_model_deferred_storage(&deferred_spill_capacity));deferred_spill_top=deferred_spill_capacity;}
            if(!deferred_spill || required>deferred_spill_top){++fx_dropped;++cloth21_drop;RE4DC_FQ_DROP(true,required);continue;}
            storage=deferred_spill;tp=&deferred_spill_top;
        }
        *tp-=required;auto* node=new(storage+*tp) DeferredPart{};
        node->lighting=kEffectQuad21Tag;node->changed[0]=bytes;
        std::memcpy(storage+*tp+kEffectQuad21Node,packet,bytes);
        if(deferred_last)deferred_last->next=node;else deferred_first=node;
        deferred_last=node;++deferred_count;
        ++fx_queued;++cloth21_rows;++drawn;
        frame_queue_peak=std::max(frame_queue_peak,unsigned(sizeof(frame_storage))-deferred_top+deferred_spill_capacity-deferred_spill_top);
    }
    e->frame=frame;
    if(frame-cloth21_log_frame>=600U){cloth21_log_frame=frame;
        re4dc_log("cloth native: f=%u grid=%ux%u rows=%u quads=%u dropped=%u\n",frame,m->cols,m->rows,cloth21_rows,cloth21_quads,cloth21_drop);}
    return drawn;
}
#endif
