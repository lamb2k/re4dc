// FLASHLIGHT_POOL (effects30.mk, #55 item 3, user option B): an additive, untextured light pool (trans.cpp
// re4dc_flashlight_pool): a fan of view-space triangles, the centre at the pool colour and the ring black (Gouraud),
// laid on the ground ahead of Leon. Translucent list, normal depth test (GEQUAL: a nearer wall hides it), no depth
// write, fog off. Same deferred FIFO node and frame owner as FX_STRIP21's quads (native_effect_strip21.inc).
namespace {
unsigned pool_drawn,pool_refused;
}
extern "C" int re4dc_effect_fan(const Re4dcEffectFan* f){
    if(!f || f->n<3 || f->n>16 || !frame_ready || stream_aborted || draining_parts){++pool_refused;return 0;}
#if RE4DC_TA_DIRECT
    if(direct_open){++pool_refused;return 0;}
#endif
#if defined(RE4DC_PVR_RTT) && RE4DC_PVR_RTT
    if(rtt::capture_slot>=0){++pool_refused;return 0;}
#endif
    if(f->projection[0]!=0 || f->viewport[2]<=0 || f->viewport[3]<=0){++pool_refused;return 0;}
    const float near=f->projection[6]/(f->projection[5]-1);
    if(!re4dc::render::is_finite(near) || near<=0){++pool_refused;return 0;}
    Re4dcEffectQuad pq{};   // projection context for project()
    std::memcpy(pq.projection,f->projection,sizeof pq.projection);std::memcpy(pq.viewport,f->viewport,sizeof pq.viewport);
    alignas(32) pvr_vertex_t packet[1+3*16];
    pvr_poly_cxt_t c;pvr_poly_cxt_col(&c,PVR_LIST_TR_POLY);
    c.gen.culling=PVR_CULLING_NONE;c.gen.shading=PVR_SHADE_GOURAUD;c.gen.fog_type=PVR_FOG_DISABLE;
    c.depth.comparison=PVR_DEPTHCMP_GEQUAL;c.depth.write=PVR_DEPTHWRITE_DISABLE;
    c.blend.src=PVR_BLEND_ONE;c.blend.dst=PVR_BLEND_ONE;
    pvr_poly_compile(reinterpret_cast<pvr_poly_hdr_t*>(packet),&c);
    float sx[17],sy[17],sz[17];
    for(unsigned i=0;i<=f->n;++i){
        const float* p=i<f->n?f->ring[i]:f->centre;
        for(unsigned k=0;k<3;++k)if(!re4dc::render::is_finite(p[k])){++pool_refused;return 0;}
        if(!(-p[2]>=near)){++pool_refused;return 0;}   // the pool is ahead of the camera; a crossing one is skipped
        float x=p[0],y=p[1],z=p[2];re4dc::effect_strip21::project(x,y,z,&pq);sx[i]=x;sy[i]=y;sz[i]=z;
    }
    pvr_vertex_t* v=packet+1;
    for(unsigned i=0;i<f->n;++i){
        const unsigned a=i,b=(i+1)%f->n,ix[3]={f->n,a,b};
        for(unsigned k=0;k<3;++k,++v){
            const unsigned j=ix[k];
            v->flags=k==2?PVR_CMD_VERTEX_EOL:PVR_CMD_VERTEX;v->x=sx[j];v->y=sy[j];v->z=sz[j];v->u=v->v=0;
            v->argb=j==f->n?f->centre_argb:0xff000000U;v->oargb=0;
        }
    }
    const unsigned bytes=(1+3*f->n)*sizeof(pvr_vertex_t);
    if(source_draws_finished){
        stream_select(PVR_LIST_TR_POLY);if(stream_aborted)return 0;
        stream_send(packet,bytes);++pool_drawn;return 1;
    }
    const unsigned required=kEffectQuad21Node+bytes,margin=8192;
    unsigned char* storage=frame_storage;unsigned* top=&deferred_top;
    if(required+margin>deferred_top || deferred_top-required-margin<std::max(8192U,nquad*unsigned(sizeof(Re4dcUiQuad)))){
        if(!deferred_spill){deferred_spill=static_cast<unsigned char*>(re4dc_model_deferred_storage(&deferred_spill_capacity));deferred_spill_top=deferred_spill_capacity;}
        if(!deferred_spill || required>deferred_spill_top){++pool_refused;return 0;}
        storage=deferred_spill;top=&deferred_spill_top;
    }
    *top-=required;auto* node=new(storage+*top) DeferredPart{};
    node->lighting=kEffectQuad21Tag;node->changed[0]=bytes;
    std::memcpy(storage+*top+kEffectQuad21Node,packet,bytes);
    if(deferred_last)deferred_last->next=node;else deferred_first=node;
    deferred_last=node;++deferred_count;++pool_drawn;
    return 1;
}
