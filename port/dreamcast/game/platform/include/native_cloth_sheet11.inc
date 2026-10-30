// CLOTH_SHEET11: prepared single-texture bands through the existing effect FIFO.
#include "native_cloth_sheet11.hpp"
#include "cloth_strip_geometry11.hpp"
#if defined(RE4DC_CLOTH_MATERIAL11) && RE4DC_CLOTH_MATERIAL11
#include "cloth_material11_source.hpp"
#include <dc/sq.h>
#endif
namespace {
using ClothOutcome11=re4dc::NativeDrawOutcome;
struct ClothPrepared11 {
    unsigned header[8],frame,slot,incarnation,cols,rows;
    float su,sv;
    Re4dcEffectQuad clip;
#if defined(RE4DC_CLOTH_MATERIAL11) && RE4DC_CLOTH_MATERIAL11
    unsigned primary_slot,primary_incarnation;
    Re4dcClothCheck11 source_check;
#endif
};
static_assert(sizeof(ClothPrepared11)<=sizeof(Re4dcClothMaterial11));
static_assert(sizeof(pvr_poly_hdr_t)==32);
bool cloth_ready11(const ClothPrepared11& m){
#if RE4DC_TA_DIRECT
    if(direct_open)return false;
#endif
#if defined(RE4DC_PVR_RTT) && RE4DC_PVR_RTT
    if(rtt::capture_slot>=0)return false;
#endif
    return frame_ready && !stream_aborted && !draining_parts && m.frame==frame && m.slot<kTextureCount &&
        m.incarnation && entries[m.slot].valid && entries[m.slot].upload_incarnation==m.incarnation && entries[m.slot].frame==frame
#if defined(RE4DC_CLOTH_MATERIAL11) && RE4DC_CLOTH_MATERIAL11
        && (!m.primary_incarnation || (m.primary_slot<kTextureCount && entries[m.primary_slot].valid &&
            entries[m.primary_slot].upload_incarnation==m.primary_incarnation && entries[m.primary_slot].frame==frame))
        && (!m.source_check.current || m.source_check.current(m.source_check.context))
#endif
        ;
}
#if defined(RE4DC_CLOTH_MATERIAL11) && RE4DC_CLOTH_MATERIAL11
re4dc::NativeDrawResult cloth_failure11(const ClothPrepared11& m){
    return {m.source_check.current && !m.source_check.current(m.source_check.context)?
        ClothOutcome11::PartialAbort:ClothOutcome11::Refused};
}
#define RE4DC_CLOTH_REFUSED11(m) cloth_failure11(m)
#else
#define RE4DC_CLOTH_REFUSED11(m) {ClothOutcome11::Refused}
#endif
re4dc::NativeDrawResult cloth_publish11(const ClothPrepared11& m,const pvr_vertex_t* packet,unsigned count){
    if(!cloth_ready11(m))return RE4DC_CLOTH_REFUSED11(m);
#if RE4DC_TA_DIRECT
    if(direct_open)return RE4DC_CLOTH_REFUSED11(m);
#endif
    const unsigned bytes=(count+1)*sizeof(pvr_vertex_t);
    if(source_draws_finished){
        stream_select(PVR_LIST_TR_POLY);if(!cloth_ready11(m))return RE4DC_CLOTH_REFUSED11(m);
        stream_send(packet,bytes);++fx_direct;
        return {stream_aborted || !cloth_ready11(m)?ClothOutcome11::PartialAbort:ClothOutcome11::Submitted,1,0};
    }
    const unsigned required=kEffectQuad21Node+bytes,margin=8192;
    unsigned char* storage=frame_storage;unsigned* top=&deferred_top;
    if(required+margin>deferred_top || deferred_top-required-margin<std::max(8192U,nquad*unsigned(sizeof(Re4dcUiQuad)))){
        if(!deferred_spill){deferred_spill=static_cast<unsigned char*>(re4dc_model_deferred_storage(&deferred_spill_capacity));deferred_spill_top=deferred_spill_capacity;}
#if defined(RE4DC_FX_R200_ENTRY_CAP) && RE4DC_FX_R200_ENTRY_CAP
        if(!deferred_spill || required>deferred_spill_top){
            if(!fx_r200_tail_select(required,storage,top)){++fx_dropped;RE4DC_FQ_DROP(true,required);return RE4DC_CLOTH_REFUSED11(m);}
        }else{storage=deferred_spill;top=&deferred_spill_top;}
#else
        if(!deferred_spill || required>deferred_spill_top){++fx_dropped;RE4DC_FQ_DROP(true,required);return RE4DC_CLOTH_REFUSED11(m);}
        storage=deferred_spill;top=&deferred_spill_top;
#endif
    }
    if(!cloth_ready11(m))return RE4DC_CLOTH_REFUSED11(m);
    *top-=required;auto* node=new(storage+*top) DeferredPart{};
    node->lighting=kEffectQuad21Tag;node->changed[0]=bytes;
    std::memcpy(storage+*top+kEffectQuad21Node,packet,bytes);
    if(deferred_last)deferred_last->next=node;else deferred_first=node;
    deferred_last=node;++deferred_count;++fx_queued;
    frame_queue_peak=std::max(frame_queue_peak,unsigned(sizeof(frame_storage))-deferred_top+deferred_spill_capacity-deferred_spill_top);
    return {ClothOutcome11::Queued,0,1};
}
}
#if defined(RE4DC_CLOTH_MATERIAL11) && RE4DC_CLOTH_MATERIAL11
static int cloth_prepare_impl11(const Re4dcEffectMesh21* m,Re4dcClothMaterial11* out,re4dc::NativeDrawResult* stop,bool source_depth){
#else
extern "C" int re4dc_cloth_prepare11(const Re4dcEffectMesh21* m,Re4dcClothMaterial11* out,re4dc::NativeDrawResult* stop){
#endif
    if(out)std::memset(out->state,0,sizeof out->state);
    if(!stop)return 0;
    *stop={ClothOutcome11::UnsupportedBeforePublication};
#if defined(RE4DC_CLOTH_TILES11) && RE4DC_CLOTH_TILES11
    if(!m || !out || m->cols<2 || m->cols>255 || m->rows<2 || m->rows>50)return 0;
#else
    if(!m || !out || m->cols<2 || m->cols>100 || m->rows<2 || m->rows>50)return 0;
#endif
    // Revoke any previous receipt before a failed prepare can expose it again.
    auto* prepared=new(out->state) ClothPrepared11{};
    if(!frame_ready || stream_aborted || draining_parts){*stop={ClothOutcome11::Refused};return 0;}
#if RE4DC_TA_DIRECT
    if(direct_open)return 0;
#endif
#if defined(RE4DC_PVR_RTT) && RE4DC_PVR_RTT
    if(rtt::capture_slot>=0)return 0;
#endif
    auto& q=prepared->clip;
    std::memcpy(q.projection,m->projection,sizeof q.projection);std::memcpy(q.viewport,m->viewport,sizeof q.viewport);
    q.color=m->color;q.src=m->src;q.dst=m->dst;q.wrap_s=m->wrap_s;q.wrap_t=m->wrap_t;
    if(!effect_quad21_valid(q))return 0;
    if(!(q.color>>24)){*stop={ClothOutcome11::PolicySkip};return 0;}
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
    if(!e || !e->valid || !e->upload_incarnation){++fx_missing;*stop={ClothOutcome11::Refused};return 0;}
    const auto& t=e->package.textures()[0];
    const unsigned w=RE4DC_COVER_W(e->package,m->image.width),h=RE4DC_COVER_H(e->package,m->image.height);
    if((m->wrap_s && w!=t.width)||(m->wrap_t && h!=t.height))return 0;
    prepared->su=float(w)/float(t.width);prepared->sv=float(h)/float(t.height);
    pvr_poly_cxt_t c;pvr_poly_cxt_txr(&c,PVR_LIST_TR_POLY,re4dc::texture::pvr_format(t),RE4DC_TSP_W(t),RE4DC_TSP_H(t),e->package.pvr_texture(0),PVR_FILTER_BILINEAR);
    // Preserve the current native cloth approximation. The source alpha>4 /
    // normal Z-write and stage0 scale/clamp are explicitly unresolved.
    c.gen.culling=PVR_CULLING_NONE;c.depth.comparison=PVR_DEPTHCMP_GEQUAL;c.depth.write=PVR_DEPTHWRITE_DISABLE;
#if defined(RE4DC_CLOTH_MATERIAL11) && RE4DC_CLOTH_MATERIAL11
    if(source_depth)c.depth.write=PVR_DEPTHWRITE_ENABLE;
#endif
    c.blend.src=(pvr_blend_mode_t)m->src;c.blend.dst=(pvr_blend_mode_t)m->dst;
    c.txr.env=PVR_TXRENV_MODULATEALPHA;c.txr.alpha=PVR_TXRALPHA_ENABLE;
    c.txr.uv_clamp=(pvr_uv_clamp_t)((m->wrap_s?0:PVR_UVCLAMP_U)|(m->wrap_t?0:PVR_UVCLAMP_V));
#if RE4DC_NATIVE_FOG
    c.gen.fog_type=re4dc_fog_enabled()?PVR_FOG_TABLE:PVR_FOG_DISABLE;
#endif
    alignas(32) pvr_poly_hdr_t header;pvr_poly_compile(&header,&c);std::memcpy(prepared->header,&header,sizeof header);
    prepared->frame=frame;prepared->slot=unsigned(e-entries);prepared->incarnation=e->upload_incarnation;
    prepared->cols=m->cols;prepared->rows=m->rows;e->frame=frame;
    if(!cloth_ready11(*prepared)){*stop={ClothOutcome11::Refused};return 0;}
    return 1;
}
#if defined(RE4DC_CLOTH_MATERIAL11) && RE4DC_CLOTH_MATERIAL11
extern "C" int re4dc_cloth_prepare11(const Re4dcEffectMesh21* m,Re4dcClothMaterial11* out,re4dc::NativeDrawResult* stop){
    return cloth_prepare_impl11(m,out,stop,false);
}
namespace {
// Package::upload() allocates data_size bytes and publishes completion only
// after every transfer. This exact non-mip RGB565 class has 128 real texel
// bytes; do not read a VQ/codebook, palette, partial upload or cached alias.
const volatile std::uint32_t* cloth_upload11(const ClothPrepared11& material){
    if(!cloth_ready11(material))return nullptr;
    auto& package=entries[material.slot].package;
    if(!package.upload_complete() || package.header().texture_count!=1)return nullptr;
    const auto& t=package.textures()[0];
    if(t.width!=8 || t.height!=8 || t.format!=re4dc::texture::kRgb565 || t.flags ||
        t.data_size!=128 || t.reserved_0 ||
        (t.payload!=re4dc::texture::kPayloadLinear && t.payload!=re4dc::texture::kPayloadTwiddled))return nullptr;
    const auto address=reinterpret_cast<std::uintptr_t>(package.pvr_texture(0));
    // KOS804b3195ebd1a06a27cc2b3a5eacf7a2429040a3 pvr_mem.h/pvr_regs.h:
    // SH-4-compatible pointers in the non-cacheable P2 texture mapping;
    // guarantees 32-byte allocations. Limit this class to retail VRAM bounds.
    constexpr std::uintptr_t first=PVR_RAM_INT_BASE,last=first+8U*1024U*1024U;
    if((address&31U) || address<first || address>last-128U)return nullptr;
    return reinterpret_cast<const volatile std::uint32_t*>(address);
}
}
extern "C" int re4dc_cloth_material11(const Re4dcEffectMesh21* m,const re4dc::cloth_material11::Source* source,
    Re4dcClothCheck11 check,Re4dcClothMaterial11* out,re4dc::NativeDrawResult* stop){
    if(out)std::memset(out->state,0,sizeof out->state);
    if(!stop)return 0;
    *stop={ClothOutcome11::UnsupportedBeforePublication};
    if(!m || !source || !out || !check.current || m->color!=0xffffffffU ||
        m->src!=4 || m->dst!=5 || m->wrap_s || m->wrap_t || !source->primary.white())return 0;
    const auto current=[&](){return check.current(check.context) && source->current();};
    const auto retired=[&](){if(current())return false;*stop={ClothOutcome11::PartialAbort};return true;};
    if(retired())return 0;
    Key external{};
    if(external_image_key(source->primary.image,external) || external_image_key(source->secondary.image,external))return 0;
    Re4dcEffectMesh21 first=*m;first.image=source->primary.image;
    Re4dcClothMaterial11 primary_storage;
    const int first_ready=cloth_prepare_impl11(&first,&primary_storage,stop,false);
    if(retired())return 0;
    if(!first_ready)return 0;
    ClothPrepared11 primary;std::memcpy(&primary,primary_storage.state,sizeof primary);
    Re4dcEffectMesh21 second=*m;second.image=source->secondary.image;
    const int second_ready=cloth_prepare_impl11(&second,out,stop,true);
    if(retired()){std::memset(out->state,0,sizeof out->state);return 0;}
    if(!second_ready)return 0;
    auto* prepared=reinterpret_cast<ClothPrepared11*>(out->state);
    prepared->primary_slot=primary.slot;prepared->primary_incarnation=primary.incarnation;prepared->source_check=check;
    // No FIFO publication exists yet. Every failure revokes the prepared view.
    const auto fail=[&](ClothOutcome11 why){std::memset(out->state,0,sizeof out->state);*stop={why};return 0;};
    if(!cloth_ready11(primary) || !cloth_ready11(*prepared))return fail(ClothOutcome11::Refused);
    const auto* first_upload=cloth_upload11(primary);const auto* second_upload=cloth_upload11(*prepared);
    if(!first_upload || !second_upload)return fail(ClothOutcome11::UnsupportedBeforePublication);
    // sq_lock may yield. Revalidate both entries and sources after acquiring
    // it, then drain both queues before aligned volatile 32-bit P2 reads.
    // Pinned KOS sq_cpy itself does not wait for its last writeback.
    sq_lock(const_cast<std::uint32_t*>(first_upload));
    bool live=current() && cloth_ready11(primary) && cloth_ready11(*prepared);
    bool exact=false;
    if(live){
        sq_wait();
        live=cloth_upload11(primary)==first_upload && cloth_upload11(*prepared)==second_upload;
        if(live)exact=re4dc::cloth_material11::uploaded_texels(first_upload,source->primary) &&
                      re4dc::cloth_material11::uploaded_texels(second_upload,source->secondary);
    }
    sq_unlock();
    if(!current())return fail(ClothOutcome11::PartialAbort);
    if(!live || !cloth_ready11(primary) || !cloth_ready11(*prepared))return fail(ClothOutcome11::Refused);
    if(!exact)return fail(ClothOutcome11::UnsupportedBeforePublication);
    return 1;
}
#endif
extern "C" re4dc::NativeDrawResult re4dc_cloth_band11(const Re4dcClothMaterial11* material,const Re4dcClothBand11* b){
    if(!material || !b || !b->top || !b->bottom)return {ClothOutcome11::UnsupportedBeforePublication};
    ClothPrepared11 m;std::memcpy(&m,material->state,sizeof m);
    if(!cloth_ready11(m))return RE4DC_CLOTH_REFUSED11(m);
    if(b->columns<2 || b->columns>100 || b->first_column>m.cols || b->columns>m.cols-b->first_column || b->row>=m.rows-1)return {ClothOutcome11::UnsupportedBeforePublication};
    const float near=m.clip.projection[6]/(m.clip.projection[5]-1);unsigned behind=0;
    for(unsigned i=0;i<b->columns;++i){behind+=!(-b->top[3*i+2]>=near);behind+=!(-b->bottom[3*i+2]>=near);
        for(unsigned a=0;a<3;++a)if(!re4dc::render::is_finite(b->top[3*i+a]) || !re4dc::render::is_finite(b->bottom[3*i+a]))return {ClothOutcome11::UnsupportedBeforePublication};}
    if(behind==2*b->columns)return {ClothOutcome11::Culled};
    const float du=1.f/float(m.cols-1),dv=1.f/float(m.rows-1),v0=b->row*dv;
    alignas(32) pvr_vertex_t packet[201];std::memcpy(packet,m.header,sizeof m.header);
    if(behind){
        re4dc::NativeDrawProgress progress;
        for(unsigned i=0;i+1<b->columns;++i){
            auto q=m.clip;const float* p[4]={b->top+3*i,b->bottom+3*i,b->top+3*(i+1),b->bottom+3*(i+1)};
            const float u[4]={(b->first_column+i)*du,(b->first_column+i)*du,(b->first_column+i+1)*du,(b->first_column+i+1)*du};
            const float v[4]={v0,v0+dv,v0,v0+dv};
            for(unsigned k=0;k<4;++k){std::memcpy(q.positions[k],p[k],3*sizeof(float));q.u[k]=u[k]*m.su;q.v[k]=v[k]*m.sv;}
            alignas(32) pvr_vertex_t vertices[12];const unsigned count=re4dc::cloth11::cell(q,vertices);
            if(!count)continue;
            if(fx_count>=RE4DC_EFFECT_SPRITE_MAX){++fx_capped;progress.add({ClothOutcome11::Refused});return progress.result;}
            std::memcpy(packet+1,vertices,count*sizeof(pvr_vertex_t));auto result=cloth_publish11(m,packet,count);
            if(result.published()){++cloth21_quads;++fx_count;fx_peak=std::max(fx_peak,fx_count);}
            if(!progress.add(result)){++cloth21_drop;return progress.result;}
        }
        return progress.result;
    }
    float x0=1e30f,x1=-1e30f,y0=1e30f,y1=-1e30f;
    for(unsigned i=0;i<b->columns;++i)for(unsigned row=0;row<2;++row){auto& v=packet[1+2*i+row];const auto* p=(row?b->bottom:b->top)+3*i;
        float x=p[0],y=p[1],z=p[2];re4dc::effect_strip21::project(x,y,z,const_cast<Re4dcEffectQuad*>(&m.clip));
        x0=std::min(x0,x);x1=std::max(x1,x);y0=std::min(y0,y);y1=std::max(y1,y);
        v.flags=PVR_CMD_VERTEX;v.x=x;v.y=y;v.z=z;v.u=(b->first_column+i)*du*m.su;v.v=(v0+row*dv)*m.sv;v.argb=m.clip.color;v.oargb=0;}
    if(x1<0 || y1<0 || x0>RE4DC_SCREEN_WF || y0>RE4DC_SCREEN_HF)return {ClothOutcome11::Culled};
    packet[2*b->columns].flags=PVR_CMD_VERTEX_EOL;auto result=cloth_publish11(m,packet,2*b->columns);
    if(result.published())++cloth21_rows;else if(!result.complete())++cloth21_drop;
    return result;
}
#undef RE4DC_CLOTH_REFUSED11
