#include "include/gc_asset_motion_unknown.h"
// Narrow ModelData indexed-stream adapter, not a GX display-list interpreter.
// Only an explicitly enabled base-texture diagnostic currently uses this path.
#include "re4dc_screen.h"
#include "native_model.h"
#include "include/gc_asset_members.h"
#if RE4DC_GC_ASSET_GATE
extern "C" unsigned re4dc_gcasset_model_identity(const void*,const void*,const void**);
extern "C" unsigned re4dc_gcasset_weapon_consumer(const void*,const void*,unsigned,unsigned);
#endif
#include "native_render_profile.hpp"
#include "native_reuse_audit.hpp"
#if RE4DC_NATIVE_RENDER_PROFILE && defined(__sh__)
re4dc::profile::State re4dc::profile::state;
#endif
#include "re4dc_platform.h"
#include "native_static.h"
#if RE4DC_KOS_HEAP_CHECK
extern "C" void re4dc_halt(const char*,int);
#endif
#include "../../room/pvr_geometry.hpp"
#include "../../room/native_draw_plan.hpp"
#ifndef RE4DC_NATIVE_STATIC
#define RE4DC_NATIVE_STATIC 0
#endif
#ifndef RE4DC_D349_RENDERER_STACK
#define RE4DC_D349_RENDERER_STACK 0
#endif
#ifndef RE4DC_NATIVE_ACTOR
#define RE4DC_NATIVE_ACTOR 0
#endif
#if RE4DC_NATIVE_ACTOR
#include "native_actor.hpp"
#endif
#ifndef RE4DC_MODEL_DRAW_PLANS
#define RE4DC_MODEL_DRAW_PLANS 0
#endif
#include <cmath>
#include <cstring>
#include <cstdint>
#include <algorithm>
#include <new>
#if RE4DC_D349_RENDERER_STACK && defined(__sh__)
#include <dc/matrix.h>
#include <dc/matrix3d.h>
#endif
#ifndef RE4DC_MODEL_ROOM_STRIPS
#define RE4DC_MODEL_ROOM_STRIPS 0
#endif
#ifndef RE4DC_MODEL_POSITION_CACHE
#define RE4DC_MODEL_POSITION_CACHE 1
#endif
namespace {
Re4dcModelWorkStats work_stats{};
#if RE4DC_D349_RENDERER_STACK
// Conservative subset of the historical static-light reuse: exact dependency
// snapshots, no frozen camera-relative lights or premature partial clamp. Two
// stable admissions avoid an LRU thrashing across all scenery every frame.
struct StaticLightContext {
    const void* part=nullptr;const void* positions=nullptr;const void* normals=nullptr;
    float modelview[12];re4dc::render::SourceLighting lighting;
    unsigned generation=0;
};
struct StaticLightValue { unsigned generation=0,position=0,normal=0,color=0;float rgb[3]; };
struct StaticLighting {
    StaticLightContext contexts[2];StaticLightValue values[192];unsigned generation=0;
};
static_assert(sizeof(StaticLighting)<=8192);
StaticLighting* static_lighting=nullptr;
StaticLightContext* prepare_room_static_lighting(const Re4dcModelPart& p){
    if(!p.static_geometry || !p.lighting)return nullptr;
    if(!static_lighting){unsigned bytes;void* data=re4dc_model_static_lighting_storage(&bytes);
        if(!data || bytes<sizeof(StaticLighting))return nullptr;
        static_lighting=new(data) StaticLighting{};}
    StaticLightContext* slot=nullptr;
    for(auto& context:static_lighting->contexts){
        if(context.part==p.part){slot=&context;break;}
        if(!context.part && !slot)slot=&context;
    }
    if(!slot)return nullptr;
    if(slot->part!=p.part || slot->positions!=p.positions || slot->normals!=p.normals ||
       std::memcmp(slot->modelview,p.modelview,sizeof(p.modelview)) ||
       std::memcmp(&slot->lighting,p.lighting,sizeof(slot->lighting))){
        slot->part=p.part;slot->positions=p.positions;slot->normals=p.normals;
        std::memcpy(slot->modelview,p.modelview,sizeof(p.modelview));slot->lighting=*p.lighting;
        slot->generation=++static_lighting->generation;++work_stats.static_light_invalidations;
    }
    return slot;
}
StaticLightValue* light_room_vertex(StaticLightContext* context,unsigned vi,unsigned ni,unsigned color){
    if(!context)return nullptr;
    return &static_lighting->values[(vi*7+ni*17+color+context->generation)%192];
}
#endif

#if RE4DC_D349_RENDERER_STACK
// D349 prepare-once/consume-many slots, adapted to live source identities.
// Replaces the part-local tables with one bounded model/batch spanning compatible
// parts and passes. No corner copy, persistent pose, heap charge or fixed lights.
Re4dcPreparationStats preparation_stats{};
struct PositionSlot { unsigned serial=0;re4dc::render::ProjectedVertex value; };
struct NormalSlot { unsigned serial=0;float value[3]; };
struct ShadeSlot { unsigned serial=0;float rgb[3];unsigned packed; };
// The same preparation workspace, retained at model/frame scope. Source indices
// address fixed slots directly; there is no corner map, hash probe or hot-loop
// retirement. Most space serves normals/lighting, the measured dominant cost.
constexpr unsigned kRetainedPositions=896,kRetainedNormals=2560;
struct NormalShadeSlot { NormalSlot normal;ShadeSlot shade;std::uint16_t position,color; };
struct RetainedPreparation {
    PositionSlot positions[kRetainedPositions];NormalShadeSlot normals[kRetainedNormals];
};
static_assert(sizeof(RetainedPreparation)==131072);
struct PositionState {
    const void* model=nullptr;const void* info=nullptr;const unsigned char* array=nullptr;
    unsigned count=0,stride=0,shift=0;float modelview[12]{},projection[7]{},viewport[6]{};
    bool matches(const Re4dcModelPart& p)const {
        return model==p.model && info==p.info && array==p.positions && count==p.position_count &&
          stride==p.position_stride && shift==p.shift && !std::memcmp(modelview,p.modelview,sizeof(modelview)) &&
          !std::memcmp(projection,p.projection,sizeof(projection)) && !std::memcmp(viewport,p.viewport,sizeof(viewport));
    }
    void assign(const Re4dcModelPart& p){model=p.model;info=p.info;array=p.positions;count=p.position_count;stride=p.position_stride;shift=p.shift;
        std::memcpy(modelview,p.modelview,sizeof(modelview));std::memcpy(projection,p.projection,sizeof(projection));std::memcpy(viewport,p.viewport,sizeof(viewport));}
};
struct NormalState {
    const void* model=nullptr;const void* info=nullptr;const unsigned char* array=nullptr;
    unsigned count=0,stride=0,shift=0;float matrix[12]{};
    bool matches(const Re4dcModelPart& p)const {return model==p.model && info==p.info && array==p.normals && count==p.normal_count &&
        stride==p.normal_stride && shift==p.normal_shift && !std::memcmp(matrix,p.lighting->normal_matrix,sizeof(matrix));}
    void assign(const Re4dcModelPart& p){model=p.model;info=p.info;array=p.normals;count=p.normal_count;stride=p.normal_stride;shift=p.normal_shift;std::memcpy(matrix,p.lighting->normal_matrix,sizeof(matrix));}
};
struct PreparedModelBatch {
    PositionSlot positions[re4dc::render::kLocalSlots];
    NormalSlot normals[re4dc::render::kLocalSlots];ShadeSlot shades[re4dc::render::kLocalSlots];
    unsigned serial=0,position_generation=0,normal_generation=0,shade_generation=0;
    unsigned retained_position_generation=0,retained_normal_generation=0,retained_shade_generation=0;
    RetainedPreparation* retained=nullptr;
    const re4dc::render::LocalBatch* domain=nullptr;
    unsigned next(){
        if(++serial==0){ // once per 2^32 state changes, never per-frame retirement
            for(auto& s:positions)s.serial=0;for(auto& s:normals)s.serial=0;for(auto& s:shades)s.serial=0;
            // A wrap may occur between activate()'s three assignments. Keep
            // every active generation nonzero so cleared slots cannot hit.
            if(retained){for(auto& s:retained->positions)s.serial=0;
                for(auto& s:retained->normals)s.normal.serial=s.shade.serial=0;}
            serial=7;position_generation=1;normal_generation=2;shade_generation=3;
            retained_position_generation=4;retained_normal_generation=5;retained_shade_generation=6;domain=nullptr;
        }
        return serial;
    }
    void activate(const re4dc::render::LocalBatch* selected){
        if(domain==selected)return;
        domain=selected;position_generation=next();normal_generation=next();shade_generation=next();
        ++preparation_stats.position_batches;++preparation_stats.normal_batches;++preparation_stats.shade_batches;
    }
    PositionState position;NormalState normal;re4dc::render::PreparedSourceLights lights{};
    static constexpr unsigned channel_bytes=sizeof(re4dc::render::SourceLighting)-offsetof(re4dc::render::SourceLighting,ambient);
    unsigned char channels[channel_bytes]{};const void* colors=nullptr;
    bool position_valid=false,normal_valid=false,lights_valid=false,channels_valid=false;
    void invalidate(){position_valid=normal_valid=lights_valid=channels_valid=false;domain=nullptr;}
    void prepare(const Re4dcModelPart& p){
        ++preparation_stats.parts;bool shade_changed=false;
        if(!position_valid || !position.matches(p)){
            position.assign(p);position_valid=true;position_generation=next();retained_position_generation=next();shade_changed=true;++preparation_stats.position_states;
        }else ++preparation_stats.position_state_hits;
        if(p.lighting){const auto& source=*p.lighting;
            if(!normal_valid || !normal.matches(p)){
                normal.assign(p);normal_valid=true;normal_generation=next();retained_normal_generation=next();shade_changed=true;++preparation_stats.normal_states;
            }else ++preparation_stats.normal_state_hits;
            unsigned count=0;bool same=lights_valid;
            if(source.enable)for(unsigned i=0;i<8;++i)if(source.mask&(1U<<i)){
                if(count>=lights.count || std::memcmp(&lights.lights[count],&source.lights[i],sizeof(re4dc::render::SourceLight)))same=false;
                ++count;}
            same=same && lights.count==count;
            if(!same){lights=re4dc::render::prepare_actor_lights(source);lights_valid=true;shade_changed=true;++preparation_stats.light_builds;}
            else ++preparation_stats.light_build_hits;
            const void* selected_colors=(source.ambient_vertex||source.material_vertex)?p.colors:nullptr;
            if(!channels_valid || colors!=selected_colors || std::memcmp(channels,source.ambient,channel_bytes)){
                std::memcpy(channels,source.ambient,channel_bytes);colors=selected_colors;channels_valid=true;shade_changed=true;}
        }else {normal_valid=channels_valid=false;shade_changed=true;}
        // Mutable source RGB has no publication serial yet. Conservatively invalidate
        // it once at the submission boundary, never compare color keys per vertex.
        if(p.lighting && (p.lighting->ambient_vertex || p.lighting->material_vertex))shade_changed=true;
        if(shade_changed){shade_generation=next();retained_shade_generation=next();}
    }
};
static_assert(sizeof(PreparedModelBatch)<=12288,"Batch must fit existing packet scratch");
PreparedModelBatch* prepared_batch=nullptr;
PreparedModelBatch* acquire_batch(const Re4dcModelPart& p){
    if(!prepared_batch){unsigned bytes=0;void* memory=re4dc_model_preparation_storage(&bytes);
        if(!memory || bytes<sizeof(PreparedModelBatch))return nullptr;
        prepared_batch=new(memory) PreparedModelBatch{};}
    if(!prepared_batch->retained){unsigned bytes=0;void* memory=re4dc_model_retained_storage(&bytes);
        if(memory && bytes>=sizeof(RetainedPreparation)){
            prepared_batch->retained=static_cast<RetainedPreparation*>(memory);prepared_batch->invalidate();}}
    prepared_batch->prepare(p);return prepared_batch;
}
#endif
unsigned be16(const unsigned char* p){return (unsigned(p[0])<<8)|p[1];}
// Native-order halfwords. A 2-byte memcpy from an unaligned pointer is a libcall
// on SH (move-by-pieces ratio 2), four per UV corner in the D367 profile.
static_assert(__BYTE_ORDER__==__ORDER_LITTLE_ENDIAN__);
unsigned u16(const unsigned char* p){return unsigned(p[0])|(unsigned(p[1])<<8);}
short s16(const unsigned char* p){return short(u16(p));}
// 2^-shift without the ldexpf/scalbnf libcalls (shift < 127).
float pow2_neg(unsigned shift){return __builtin_bit_cast(float,(127U-shift)<<23);}
bool ram(const void* p,unsigned bytes){
#if defined(__sh__)
    auto a=(std::uintptr_t)p;
    return a>=0x8c000000U && a<0x8d000000U && bytes<=0x8d000000U-a;
#else
    return p!=nullptr;
#endif
}
struct Projection { const float* p; const float* v; };
void project(float& x,float& y,float& z,void* context){
    const auto& c=*(const Projection*)context;
    const float inv=1.0f/(-z);
    x=(c.v[2]*.5f*(c.p[1]*x+c.p[2]*z)*inv+c.v[0]+c.v[2]*.5f)*RE4DC_SCREEN_WF/c.v[2];
    y=(-c.v[3]*.5f*(c.p[3]*y+c.p[4]*z)*inv+c.v[1]+c.v[3]*.5f)*RE4DC_SCREEN_HF/c.v[3];
    z=inv;
}
struct Builder {
    const Re4dcModelPart& p; Re4dcModelPacket packet{};
    Projection projection; re4dc::render::ClipParameters clip;
    unsigned used=0,input=0,stride; float scale;
    unsigned strip_vertices=0,output=0,local_position_base=4095;
    unsigned pending_intact=0,pending_reconstructed=0;
    void committed_strips(){
        RE4DC_PROFILE_COUNT(IntactStrips,pending_intact);RE4DC_PROFILE_COUNT(ReconstructedStrips,pending_reconstructed);
        pending_intact=pending_reconstructed=0;
    }
    const re4dc::render::DrawPlanBounds* bounds=nullptr;
#if RE4DC_D349_RENDERER_STACK
    re4dc::render::PreparedSourceLights lights{};
    StaticLightContext* static_context=nullptr;
    PreparedModelBatch* batch=nullptr;ShadeSlot* prepared_shade=nullptr;
    const re4dc::render::DrawLocalPlan* locals=nullptr;
    const re4dc::render::LocalBatch* local_batch=nullptr;
    unsigned local_position=0,local_normal=0;
    bool shade_by_normal=false;
    bool dense_pos=false,dense_normal=false,dense_shade=false;
    void select_local(const re4dc::render::LocalBatch* selected){
        local_batch=selected;
        dense_pos=batch && selected && selected->position_count && selected->position_count<=re4dc::render::kLocalSlots;
        dense_normal=batch && selected && selected->normal_count && selected->normal_count<=re4dc::render::kLocalSlots;
        shade_by_normal=selected && selected->shade_mode==re4dc::render::LocalShadeMode::by_normal;
        dense_shade=selected && ((shade_by_normal && dense_normal) ||
            (selected->shade_mode==re4dc::render::LocalShadeMode::by_position && dense_pos));
        if(batch && selected)batch->activate(selected);
    }
    struct CachedLight { unsigned position=~0U,normal=0,color=0;float rgb[3]; } shades[64]{};
#endif
#if RE4DC_D349_RENDERER_STACK && defined(__sh__)
    alignas(32) matrix_t position_matrix{};
    bool matrix_dirty=true;
    void load_position_matrix(){
        if(!matrix_dirty)return;
        for(unsigned row=0;row<3;++row)for(unsigned col=0;col<4;++col)
            position_matrix[col][row]=p.modelview[4*row+col];
        position_matrix[0][3]=position_matrix[1][3]=position_matrix[2][3]=0;position_matrix[3][3]=1;
        mat_load(&position_matrix);matrix_dirty=false;
    }
#endif
    bool streaming=false,bound=false,submitted=false,restart_uv=false,resource_failed=false;
#if RE4DC_MODEL_POSITION_CACHE
    // Part-local, source-indexed reuse. Never weld equal coordinates or retain
    // source pointers across submissions. UVs/normals keep their own identities.
    // Collisions simply recompute. The same bounded table survives packet flushes
    // and UV-scale retries because neither changes the source position transform.
    struct CachedPosition { re4dc::render::ProjectedVertex value; unsigned key; };
    CachedPosition positions[64]{};
    static_assert(sizeof(positions)==2048);
#endif
    bool bind(){
        if(bound)return true;
        const float u=packet.u_scale,v=packet.v_scale;
        if(!re4dc_model_packet_begin(&p,&packet)){resource_failed=true;return false;}
#if RE4DC_D349_RENDERER_STACK && defined(__sh__)
        matrix_dirty=true; // texture/storage binding may yield to another task
#endif
        bound=true;
        // No chunk has been published at this point. Alternate native layouts
        // must use their true UV scale before clipping, just like the reference.
        if(u!=packet.u_scale || v!=packet.v_scale){restart_uv=true;return false;}
        return true;
    }
    bool flush(){
        if(!streaming || !bind())return false;
#if RE4DC_D349_RENDERER_STACK
        ++preparation_stats.packet_flushes;
#endif
        re4dc_model_packet_commit(used);re4dc::reuse_audit::commit(used);committed_strips();submitted=true;
#if RE4DC_D349_RENDERER_STACK && defined(__sh__)
        matrix_dirty=true;
#endif
        used=strip_vertices=0; // same owner, header, texture pin and scratch
        return true;
    }
    const unsigned char* corner_at(const unsigned char* p,unsigned i)const{return p+i*stride;}
    bool vertex(const unsigned char* corner,re4dc::render::RenderVertex& v,float& opacity){
        const unsigned vi=be16(corner),ni=be16(corner+2),ti=be16(corner+stride-2);
        if(vi>=p.position_count || ni>=p.normal_count || !ram(p.uv+ti*4,4))return false;
        return vertex_indices(vi,ni,ti,(p.flags&0x80000000U)?be16(corner+4):0,v,opacity);
    }
    bool vertex_indices(unsigned vi,unsigned ni,unsigned ti,unsigned ci,re4dc::render::RenderVertex& v,float& opacity){
        RE4DC_PROFILE_SCOPE(TransformProject);
        re4dc::reuse_audit::reference(vi,ni,ti,ci);
        v={};++work_stats.position_references;
#if RE4DC_D349_RENDERER_STACK
        // Installation inspected every immutable source corner in this span.
        // walk_plan selects only its legal units (whole strips/fans), including
        // global ordinals skipped by culling, so direct subtraction stays in
        // the boundary-qualified range without repeating its checks here.
        if(dense_pos)local_position=vi-local_batch->position_base;
        if(dense_normal)local_normal=ni-local_batch->normal_base;
        prepared_shade=nullptr;
        if(p.lighting){
            preparation_stats.normal_dense_references+=dense_normal;
            preparation_stats.shade_dense_references+=dense_shade;
        }
#endif
#if RE4DC_MODEL_POSITION_CACHE
        unsigned slot=vi&63U;
#if RE4DC_D349_RENDERER_STACK
        if(dense_pos)++work_stats.local_position_references;
        else {++work_stats.general_position_references;
            if(local_position_base!=4095 && vi>=local_position_base && vi-local_position_base<64)slot=vi-local_position_base;
        }
#endif
        auto& cached=positions[slot];
#if RE4DC_D349_RENDERER_STACK
        PositionSlot* shared_position=nullptr;unsigned position_serial=0;
        if(batch && batch->retained && vi<kRetainedPositions){
            shared_position=&batch->retained->positions[vi];position_serial=batch->retained_position_generation;
        }else if(dense_pos){shared_position=&batch->positions[local_position];position_serial=batch->position_generation;}
        if(shared_position?shared_position->serial==position_serial:cached.key==vi+1U){
            v.position=shared_position?shared_position->value:cached.value;++work_stats.position_hits;
        }else
#else
        if(cached.key==vi+1U){v.position=cached.value;++work_stats.position_hits;}else
#endif
#endif
        {
            const unsigned char* pos=p.positions+vi*p.position_stride;
            const float a=s16(pos)*scale,b=s16(pos+2)*scale,c=s16(pos+4)*scale;
#if RE4DC_D349_RENDERER_STACK && defined(__sh__)
            load_position_matrix();float x=a,y=b,z=c,w=1;
            // This boundary needs camera-space XYZ, before the source projection.
            // KOS mat_trans_single replaces Z with reciprocal W; the historical
            // room uses that only AFTER its combined projection matrix.
            mat_trans_nodiv(x,y,z,w);
#else
            const float* m=p.modelview;
            float x=m[0]*a+m[1]*b+m[2]*c+m[3];
            float y=m[4]*a+m[5]*b+m[6]*c+m[7];
            float z=m[8]*a+m[9]*b+m[10]*c+m[11];
#endif
            ++work_stats.position_transforms;
            if(!re4dc::render::is_finite(x)||!re4dc::render::is_finite(y)||!re4dc::render::is_finite(z))return false;
            v.position.world_x=x;v.position.world_y=y;v.position.world_z=z;v.position.depth=-z;
            // Behind/near vertices are clipped before projection is consumed.
            if(z!=0)project(x,y,z,&projection);
            v.position.x=x;v.position.y=y;v.position.z=z;
#if RE4DC_MODEL_POSITION_CACHE
#if RE4DC_D349_RENDERER_STACK
            if(shared_position){shared_position->value=v.position;shared_position->serial=position_serial;}else
#endif
            {cached.value=v.position;cached.key=vi+1U;}
#endif
        }
        profile_scope.move(re4dc::profile::PacketPack);
        const auto* uv=p.uv+ti*4;
        float u=(p.flags&0x80000000U)?s16(uv)/256.f:u16(uv)/32768.f;
        float w=(p.flags&0x80000000U)?s16(uv+2)/256.f:u16(uv+2)/32768.f;
        v.u=(u+p.uv_offset[0])*packet.u_scale;v.v=(w+p.uv_offset[1])*packet.v_scale;
        v.light_red=v.light_green=v.light_blue=1;
#if RE4DC_D349_RENDERER_STACK
        if(p.lighting){
            RE4DC_PROFILE_SCOPE(Lighting);
            auto& legacy_shade=shades[(vi*7+ni*17+ci)&63U];
            ShadeSlot* shared_shade=nullptr;bool shared_hit=false;unsigned shade_serial=0;
            auto* retained=(batch && batch->retained && ni<kRetainedNormals)?&batch->retained->normals[ni]:nullptr;
            const bool retain_shade=retained && !(dense_shade && !shade_by_normal);
            const unsigned shade_color=(p.lighting->ambient_vertex || p.lighting->material_vertex)?ci:0;
            if(retain_shade){shared_shade=&retained->shade;shade_serial=batch->retained_shade_generation;
                // A source normal may be shared by DIFFERENT positions/colors.
                // Direct addressing never asserts that those lit inputs agree.
                shared_hit=shared_shade->serial==shade_serial && retained->position==vi && retained->color==shade_color;
            }else if(dense_shade){shared_shade=&batch->shades[shade_by_normal?local_normal:local_position];
                shade_serial=batch->shade_generation;shared_hit=shared_shade->serial==shade_serial;}
            float* rgb=shared_shade?shared_shade->rgb:legacy_shade.rgb;
            if(shared_shade?!shared_hit:(legacy_shade.position!=vi || legacy_shade.normal!=ni || legacy_shade.color!=ci)){
                bool normal_hit=false;NormalSlot* shared_normal=nullptr;unsigned normal_serial=0;
                if(retained){shared_normal=&retained->normal;normal_serial=batch->retained_normal_generation;}
                else if(dense_normal){shared_normal=&batch->normals[local_normal];normal_serial=batch->normal_generation;}
                if(shared_normal)normal_hit=shared_normal->serial==normal_serial;
                float nx,ny,nz;
                if(normal_hit){nx=shared_normal->value[0];ny=shared_normal->value[1];nz=shared_normal->value[2];++preparation_stats.normal_hits;}
                else {
                const auto* normal=p.normals+ni*p.normal_stride;
                const float factor=pow2_neg(p.normal_shift);
                float n[3];for(unsigned i=0;i<3;++i)
                    n[i]=(p.normal_shift==6?float(static_cast<signed char>(normal[i])):float(s16(normal+i*2)))*factor;
                const auto* m=p.lighting->normal_matrix;
                nx=m[0]*n[0]+m[1]*n[1]+m[2]*n[2];
                ny=m[4]*n[0]+m[5]*n[1]+m[6]*n[2];
                nz=m[8]*n[0]+m[9]*n[1]+m[10]*n[2];
#if RE4DC_GROUND_LIGHT_FIX&2
                // GROUND_LIGHT_FIX bit 2: unit-length lighting normal, as GX (Dolphin) lights. Raw S8/64 normals are
                // ~1.97 long at scale 1 and ~0.2 at r101's scale-10 ground placements before this.
                {const float q=nx*nx+ny*ny+nz*nz;if(q>0.0f){const float r=1.0f/std::sqrt(q);nx*=r;ny*=r;nz*=r;}}
#endif
                ++work_stats.normal_transforms;
                if(shared_normal){shared_normal->serial=normal_serial;shared_normal->value[0]=nx;shared_normal->value[1]=ny;shared_normal->value[2]=nz;}
                }
                const unsigned char white[]={255,255,255,255};
                const auto* color=(p.lighting->ambient_vertex || p.lighting->material_vertex)?p.colors+ci*4:white;
                const unsigned color_value=u16(color)|(u16(color+2)<<16);
                auto* value=light_room_vertex(static_context,vi,ni,color_value);
                if(value && value->generation==static_context->generation && value->position==vi &&
                   value->normal==ni && value->color==color_value){
                    rgb[0]=value->rgb[0];rgb[1]=value->rgb[1];rgb[2]=value->rgb[2];++work_stats.static_light_hits;
                }else {
                re4dc::reuse_audit::light();
                re4dc::render::evaluate_prepared_source_lighting(
                    v.position.world_x,v.position.world_y,v.position.world_z,nx,ny,nz,
                    *p.lighting,batch?batch->lights:lights,color,rgb);

                work_stats.light_evaluations+=(batch?batch->lights:lights).count;
                    if(value){value->generation=static_context->generation;value->position=vi;value->normal=ni;
                        value->color=color_value;value->rgb[0]=rgb[0];value->rgb[1]=rgb[1];value->rgb[2]=rgb[2];++work_stats.static_light_misses;}
                }
                if(shared_shade){shared_shade->serial=shade_serial;
                    if(retain_shade){retained->position=vi;retained->color=shade_color;}
                    shared_shade->packed=0; // bit 24 marks a prepared RGB value
                }else {legacy_shade.position=vi;legacy_shade.normal=ni;legacy_shade.color=ci;}
            }else ++work_stats.light_hits;
            v.light_red=rgb[0];v.light_green=rgb[1];v.light_blue=rgb[2];
            prepared_shade=shared_shade;
        }
#endif
        // Source channel alpha is independent of base texture alpha. Vertex
        // source uses its own BE corner identity, never the position cache key.
        const unsigned alpha=(p.alpha_state&256)?p.colors[ci*4+3]:(p.alpha_state&255);
        opacity=alpha/255.0f;
        return true;
    }
    template<class Corner>
    bool triangle(const Corner* a,const Corner* b,const Corner* c){
        RE4DC_PROFILE_SCOPE(ClipFallback);
        re4dc::render::RenderVertex in[3];float opacity[3];
        if(!vertex(a,in[0],opacity[0])||!vertex(b,in[1],opacity[1])||!vertex(c,in[2],opacity[2]))return false;
        pvr_vertex_t out[6];++input;
        const auto crossing=[&](const re4dc::render::RenderVertex& v){return v.position.depth<clip.near_distance || v.position.depth>clip.far_distance;};
        if(crossing(in[0]) || crossing(in[1]) || crossing(in[2]))++work_stats.clipped_triangles;
        unsigned count=re4dc::render::clip_projected_triangle(in,out,p.cull,clip,nullptr,opacity);
        if(!count)++work_stats.culled_triangles;
        for(unsigned i=0;i<count;++i)if(!append_triangle(out+i*3))return false;
        return true;
    }
    bool append_triangle(const pvr_vertex_t* triangle){
        RE4DC_PROFILE_SCOPE(PacketPack);
        auto* dst=(pvr_vertex_t*)packet.vertices;
        // PVR alternates strip winding. Match the exact two preceding vertices
        // (including UV/color seams), then retain just the new third vertex.
        // CPU clipping/culling has already selected the surviving triangles.
        const unsigned parity=strip_vertices&1;
        const auto equal=[](const pvr_vertex_t& a,const pvr_vertex_t& b){
            return std::memcmp((const unsigned char*)&a+4,
                               (const unsigned char*)&b+4,sizeof(a)-4)==0;
        };
        if(strip_vertices>=3 && equal(dst[used-2+parity],triangle[0]) &&
                                equal(dst[used-1-parity],triangle[1])){
            if(used==packet.capacity){
                if(!flush())return false;
                return append_triangle(triangle); // begin a correctly wound strip
            }
            dst[used-1].flags=PVR_CMD_VERTEX;
            dst[used]=triangle[2];dst[used++].flags=PVR_CMD_VERTEX_EOL;++strip_vertices;
        }else{
            if(packet.capacity-used<3){
                if(!flush())return false;
                return append_triangle(triangle);
            }
            std::memcpy(dst+used,triangle,3*sizeof(*dst));
            dst[used].flags=dst[used+1].flags=PVR_CMD_VERTEX;
            dst[used+2].flags=PVR_CMD_VERTEX_EOL;used+=3;strip_vertices=3;
        }
        ++output;
        return true;
    }
#if RE4DC_MODEL_ROOM_STRIPS
    // Use the room/character one-pass strip preparation with source-selected
    // corners. Private tail space in the EXISTING packet buffer holds prepared
    // vertices; front space holds the worst-case split output. Nothing is
    // published until the full primitive qualifies, so fallback needs no fence
    // or additional allocation. CPU cull/alpha/order remain exactly unchanged.
    template<class Corner>
    int room_strip(const Corner* corners,unsigned count){
        RE4DC_PROFILE_SCOPE(PacketPack);
        if(count<3)return 0;
#if RE4DC_D349_RENDERER_STACK
        // Historical direct path: qualify in the final private packet range,
        // then publish the original strip. PVR headers own facing/culling.
        if(count>packet.capacity)return 0;
        if(count>packet.capacity-used){if(!streaming || !flush())return -1;}
        auto* prepared=(pvr_vertex_t*)packet.vertices+used;
#else
        const unsigned worst=3*(count-2);
        if(count+worst>packet.capacity-used)return 0;
        auto* prepared=(pvr_vertex_t*)packet.vertices+packet.capacity-count;
#endif
        unsigned outside=15;
        const bool ready=re4dc::render::prepare_direct_strip(
            prepared,count,clip.near_distance,clip.far_distance,
            [&](unsigned local,re4dc::render::DirectStripVertex& out){
                re4dc::render::RenderVertex v;float opacity;
                if(!vertex(corner_at(corners,local),v,opacity))return false;
                outside&=(v.position.x<0?1U:0U)|(v.position.x>clip.width?2U:0U)|
                         (v.position.y<0?4U:0U)|(v.position.y>clip.height?8U:0U);
                re4dc::reuse_audit::pack();
                const unsigned alpha=unsigned(std::clamp(opacity*255.f,0.f,255.f));
                const auto channel=[](float x){return unsigned(std::clamp(x*255.f,0.f,255.f));};
                unsigned rgb;
#if RE4DC_D349_RENDERER_STACK
                if(prepared_shade && p.lighting){
                    if(!(prepared_shade->packed&0x1000000U)){
                        prepared_shade->packed=0x1000000U|(channel(v.light_red)<<16)|(channel(v.light_green)<<8)|channel(v.light_blue);
                        ++preparation_stats.color_packs;
                    }
                    rgb=prepared_shade->packed&0xffffffU;
                }else
#endif
                rgb=(channel(v.light_red)<<16)|(channel(v.light_green)<<8)|channel(v.light_blue);
                out={v.position.depth,v.position.x,v.position.y,v.position.z,
                     v.u,v.v,(alpha<<24)|rgb,v.offset_color};
                return true;
            });
        if(!ready){++work_stats.room_strip_fallbacks;RE4DC_PROFILE_COUNT(StripClipFallbacks,1);return 0;}
        ++work_stats.room_prepared_strips;work_stats.room_prepared_corners+=count;
#if RE4DC_D349_RENDERER_STACK
        input+=count-2;
        if(outside){++work_stats.culled_primitives;work_stats.culled_triangles+=count-2;return 1;}
        used+=count;output+=count-2;strip_vertices=0;++pending_intact;
#else
        // The room's direct path delegates culling to its PVR headers. The
        // recovered frame currently uses CPU culling; share its exact reject
        // predicate and preserve ordered surviving strips without changing the
        // frame/material owner or its hardware cull state.
        const unsigned output_before=output;
        for(unsigned i=2;i<count;++i){
            ++input;
            const auto& a=prepared[i-2+(i&1)];
            const auto& b=prepared[i-1-(i&1)];
            const auto& c=prepared[i];
            if(!re4dc::render::triangle_visible_xy(a,b,c,p.cull,clip.width,clip.height)){++work_stats.culled_triangles;continue;}
            const pvr_vertex_t triangle[3]={a,b,c};
            if(!append_triangle(triangle))return -1;
        }
        if(output>output_before)++pending_reconstructed;
#endif
        return 1;
    }
#endif
    template<class Corner>
    bool primitive(const Corner* v,unsigned n,re4dc::render::DrawTopology kind){
        using re4dc::render::DrawTopology;
#if RE4DC_D349_RENDERER_STACK && defined(__sh__)
        matrix_dirty=true; // load once for the compatible primitive run
#endif
#if RE4DC_MODEL_ROOM_STRIPS
        if(kind==DrawTopology::strip){
            const int result=room_strip(v,n);
            if(result<0)return false;
            if(result>0)return true;
        }
#endif
        if(kind==DrawTopology::quads){for(unsigned i=0;i<n;i+=4)
            if(!triangle(corner_at(v,i),corner_at(v,i+1),corner_at(v,i+2)) ||
               !triangle(corner_at(v,i),corner_at(v,i+2),corner_at(v,i+3)))return false;
        }else if(kind==DrawTopology::triangles){for(unsigned i=0;i<n;i+=3)
            if(!triangle(corner_at(v,i),corner_at(v,i+1),corner_at(v,i+2)))return false;
        }else{for(unsigned i=2;i<n;++i){
            unsigned a=kind==DrawTopology::fan?0:i-2,b=i-1;
            if(kind==DrawTopology::strip && (i&1)){unsigned t=a;a=b;b=t;}
            if(!triangle(corner_at(v,a),corner_at(v,b),corner_at(v,i)))return false;
        }}
        return true;
    }
    bool walk_plan(const re4dc::render::NativeDrawPlan& plan){
        RE4DC_PROFILE_SCOPE(Topology);
        unsigned ordinal=0;
#if RE4DC_D349_RENDERER_STACK
        unsigned batch_index=0;
#endif
        for(unsigned i=0;i<plan.primitive_count;++i){
            const auto& part=plan.primitives()[i];local_position_base=part.local_base;
#if RE4DC_D349_RENDERER_STACK
            if(bounds && i<bounds->primitive_count && !re4dc::render::primitive_visible(bounds->primitives()[i],
                p.modelview,p.projection,p.viewport,clip.near_distance,clip.far_distance,0)){
                ++work_stats.culled_primitives;ordinal+=part.repeats()*part.corner_count;continue;
            }
#endif
            for(unsigned repeat=0;repeat<part.repeats();++repeat){
                const auto* corners=p.stream+part.corner_offset(repeat,stride);
#if RE4DC_D349_RENDERER_STACK
                unsigned at=0;
                while(at<part.corner_count){
                    const re4dc::render::LocalBatch* selected=nullptr;unsigned limit=ordinal+part.corner_count;
                    if(locals){
                        while(batch_index<locals->batches && locals->entries()[batch_index].first_corner+locals->entries()[batch_index].corner_count<=ordinal+at)++batch_index;
                        if(batch_index<locals->batches){const auto& candidate=locals->entries()[batch_index];
                            if(ordinal+at>=candidate.first_corner){selected=&candidate;limit=std::min<unsigned>(limit,candidate.first_corner+candidate.corner_count);}
                            else limit=std::min<unsigned>(limit,candidate.first_corner);
                        }
                    }
                    select_local(selected);
                    const unsigned count=limit-ordinal-at;
                    if(!count || !primitive(corners+at*stride,count,part.topology))return false;
                    at+=count;
                }
#else
                if(!primitive(corners,part.corner_count,part.topology))return false;
#endif
                ordinal+=part.corner_count;
            }
        }
        return true;
    }
    bool walk(bool emit){
        RE4DC_PROFILE_SCOPE(Topology);
        work_stats.gx_walk_bytes+=p.stream_bytes;
        unsigned offset=0;
        while(offset<p.stream_bytes){
            unsigned op=p.stream[offset++];if(!op)continue;
            if(p.stream_bytes-offset<2)return false;
            unsigned n=be16(p.stream+offset);offset+=2;
            if(n>(p.stream_bytes-offset)/stride)return false;
            const auto* v=p.stream+offset;offset+=n*stride;
            if((op==0x80 && n%4) || (op==0x90 && n%3) ||
               (op!=0x80 && op!=0x90 && op!=0x98 && op!=0xa0))return false;
            if(!emit){
            for(unsigned i=0;i<n;++i){
                if(be16(v+i*stride)>=p.position_count || be16(v+i*stride+2)>=p.normal_count ||
                   !ram(p.uv+be16(v+i*stride+stride-2)*4,4))return false;
            }
            if((p.alpha_state&256) || (p.lighting && (p.lighting->ambient_vertex || p.lighting->material_vertex))) {
                for(unsigned i=0;i<n;++i)
                    if(!ram(p.colors+be16(v+i*stride+4)*4,4))return false;
            }
            continue;
            }
            const auto kind=op==0x80?re4dc::render::DrawTopology::quads:
                op==0x90?re4dc::render::DrawTopology::triangles:
                op==0x98?re4dc::render::DrawTopology::strip:re4dc::render::DrawTopology::fan;
            if(!primitive(v,n,kind))return false;
        }
        return true;
    }
};
}
#if defined(RE4DC_LEON_LIGHT_HEADROOM) && RE4DC_LEON_LIGHT_HEADROOM
extern "C" int re4dc_leon_hr_image(const Re4dcUiImage* image);  // native_ui.cpp: one of Leon's 2x packages
unsigned leon_hr_parts;  // parts drawn at x0.5 here (log census)
#endif
#if defined(RE4DC_CALLPROF) && RE4DC_CALLPROF
extern "C" void re4dc_callprof_part(const void* model, unsigned path);  // model_bridge.cpp
#endif
#if defined(RE4DC_PROP_PROF) && RE4DC_PROP_PROF
// PROP_PROF=1 (lane cast16 2026-10-17; diagnostic, default 0): re4dc_model_submit time and PVR bytes per model
// (kind / id / type) and route: 1 static package, 2 native actor, 3 prepared draw plan, 4 generic walk, 0 refused.
// PPF lines every 120 UI frames (top 20 by time).
extern "C" unsigned re4dc_propprof_key(const void* model);
extern "C" unsigned re4dc_stream_model_bytes_now();
extern "C" unsigned long long re4dc_otp_now_us();
extern "C" unsigned re4dc_ui_frame();
namespace pprof {
struct Row { unsigned key, path, n, us, bytes; };
Row rows[96]; unsigned nrows, over, last;
unsigned path;
void add(unsigned key, unsigned pth, unsigned us, unsigned b) {
    for (unsigned k = 0; k < nrows; ++k) if (rows[k].key == key && rows[k].path == pth) { rows[k].n++; rows[k].us += us; rows[k].bytes += b; return; }
    if (nrows == 96) { ++over; return; }
    rows[nrows++] = Row{key, pth, 1, us, b};
}
void window() {
    const unsigned fr = re4dc_ui_frame();
    if (!last) { last = fr; return; }
    if (fr - last < 30) return;
    re4dc_log("PPF f=%u frames=%u rows=%u over=%u\n", fr, fr - last, nrows, over);
    for (unsigned i = 0; i < 20 && i < nrows; ++i) {
        unsigned b = i; for (unsigned k = i + 1; k < nrows; ++k) if (rows[k].us > rows[b].us) b = k;
        Row t = rows[i]; rows[i] = rows[b]; rows[b] = t;
        re4dc_log("PPF  kind=%u id=%x type=%x path=%u parts=%u us=%u bytes=%u\n", rows[i].key >> 16, (rows[i].key >> 8) & 255, rows[i].key & 255,
                  rows[i].path, rows[i].n, rows[i].us, rows[i].bytes);
    }
    nrows = 0; over = 0; last = fr;
}
struct Scope {
    unsigned key; unsigned long long t0; unsigned b0;
    explicit Scope(const Re4dcModelPart* p) : key(p ? re4dc_propprof_key(p->model) : 0xffffffu), t0(re4dc_otp_now_us()), b0(re4dc_stream_model_bytes_now()) { path = 0; window(); }
    ~Scope() { add(key, path, unsigned(re4dc_otp_now_us() - t0), re4dc_stream_model_bytes_now() - b0); }
};
}
// The bridge's whole re4dc_draw_model_part (path 9) and other callers' spans.
extern "C" void re4dc_pprof_add(const void* model, unsigned pth, unsigned us, unsigned b) {
    pprof::add(model ? re4dc_propprof_key(model) : 0xffffffu, pth, us, b);
}
#define PP_PATH(x) (pprof::path = (x))
#else
#define PP_PATH(x) ((void) 0)
#endif
extern "C" void re4dc_model_submit(const Re4dcModelPart* p){
#if RE4DC_GC_ASSET_GATE
    // Replacement/static paths must supply their own immutable asset proof.
    // A source caller's BIN cannot certify the bytes their emitter consumes.
    re4dc_gcasset::SourceScope gcasset_source_scope;
#if RE4DC_GC_ASSET_MOTION_UNKNOWN
    re4dc_gcasset::MotionUnknownScope gcasset_motion_scope(re4dc_gcasset::motion_model_reason());
#endif
#endif
#if defined(RE4DC_PROP_PROF) && RE4DC_PROP_PROF
    pprof::Scope pprof_scope(p);
#endif
#if defined(RE4DC_CALLPROF) && RE4DC_CALLPROF
    re4dc_callprof_part(p ? p->model : nullptr, 2);
#endif
    RE4DC_PROFILE_SCOPE(ModelSetup);
    if(!RE4DC_MODEL_DIAG())return;
#if defined(RE4DC_LEON_LIGHT_HEADROOM) && RE4DC_LEON_LIGHT_HEADROOM
    // LEON_LIGHT_HEADROOM: Leon's textures are 2x on the disc and only his owner path halves its colours. Any other
    // draw of them (the radio-call portrait, a source fallback, any later path) arrives here: its lighting record
    // takes tev_scale x0.5, so GX lighting, the exact evaluator and the constant colour all draw it as with the 1x
    // textures. Records already halved are skipped: the owner's lit record (LEON_SOURCE_LIGHT marker
    // normal_matrix[3]) and every x0.5 record (marker normal_matrix[7], also on the owner's flat record), so a
    // deferred part re-submitted at the drain is not halved twice. normal_matrix[3]/[7] are unused translation words.
#if defined(RE4DC_ACTOR_NO_CLEAR) && RE4DC_ACTOR_NO_CLEAR
    // ACTOR_NO_CLEAR (game30.mk): the x0.5 copies are built only for a Leon 2x part (copy-constructed: the same
    // words as default construction + assignment); every other part no longer default-initialises ~0.7 KB here.
    alignas(Re4dcModelPart) unsigned char hr_view_mem[sizeof(Re4dcModelPart)];
    alignas(re4dc::render::SourceLighting) unsigned char hr_lighting_mem[sizeof(re4dc::render::SourceLighting)];
    if(p && p->lighting && p->lighting->normal_matrix[3]!=1.0e30f && p->lighting->normal_matrix[7]!=1.0e30f &&
       re4dc_leon_hr_image(&p->image)){
        auto* hr_lighting=::new(static_cast<void*>(hr_lighting_mem)) re4dc::render::SourceLighting(*p->lighting);
        hr_lighting->tev_scale*=0.5f;hr_lighting->normal_matrix[7]=1.0e30f;
        auto* hr_view=::new(static_cast<void*>(hr_view_mem)) Re4dcModelPart(*p);
        hr_view->lighting=hr_lighting;p=hr_view;
#else
    Re4dcModelPart hr_view;
    re4dc::render::SourceLighting hr_lighting;
    if(p && p->lighting && p->lighting->normal_matrix[3]!=1.0e30f && p->lighting->normal_matrix[7]!=1.0e30f &&
       re4dc_leon_hr_image(&p->image)){
        hr_view=*p;hr_lighting=*p->lighting;hr_lighting.tev_scale*=0.5f;hr_lighting.normal_matrix[7]=1.0e30f;
        hr_view.lighting=&hr_lighting;p=&hr_view;
#endif
        if(leon_hr_parts++<4 || !(leon_hr_parts&1023U))
            re4dc_log("LEON_HR source part %ux%u fmt=%u x0.5 n=%u\n",p->image.width,p->image.height,p->image.format,leon_hr_parts);
    }
#endif
#if RE4DC_NATIVE_STATIC
    // A bound scroll part draws its prelit package batches instead (or defers,
    // or is covered by an earlier part with the same material key).
    if(p && re4dc_static_submit(p)){PP_PATH(1);return;}
    // A fallback part leaves the static identity words behind: they differ per
    // object, and the translucent queue snapshots parts as word differences.
#if defined(RE4DC_ACTOR_NO_CLEAR) && RE4DC_ACTOR_NO_CLEAR
    alignas(Re4dcModelPart) unsigned char plain_mem[sizeof(Re4dcModelPart)];  // ACTOR_NO_CLEAR: built only when used
    if(p && p->world){auto* plain=::new(static_cast<void*>(plain_mem)) Re4dcModelPart(*p);plain->serial=0;
        plain->world=plain->view=nullptr;plain->source_key[0]=0;plain->source_key[1]=0xff;p=plain;}
#else
    Re4dcModelPart plain;
    if(p && p->world){plain=*p;plain.serial=0;plain.world=plain.view=nullptr;
        plain.source_key[0]=0;plain.source_key[1]=0xff;p=&plain;}
#endif
#endif
#if RE4DC_GC_ASSET_GATE
    if(p) {
        const void* data=nullptr;re4dc_gcasset::ModelMember member;
        if(re4dc_gcasset::replay_use.serial!=0xffffffffU){
            // gc-catalog24b accepts an actor part selected through its model member (ActorSourceScope::accepted);
            // its deferred replay keeps that member serial only when the live member holds the BIN this part
            // draws, so a queued serial never relabels other geometry (cast-ps2-25 r17: the h2 translucent room
            // model drawn after the codec screen lost its proof here).
            const auto& r=re4dc_gcasset::replay_use;
            const bool held=!r.payload && r.serial && re4dc_gcasset_model_identity(p->model,p->info,&data)!=0xffffffffU &&
                re4dc_gcasset::member_contains(r.serial,data,64);
            re4dc_gcasset::source_use={r.payload||held?r.serial:0,r.mask,p->model,p->info,r.payload};
        }
        else if(re4dc_gcasset_model_identity(p->model,p->info,&data)!=0xffffffffU &&
           re4dc_gcasset::member_lookup(data,&member)) {
            const unsigned mask=(1U<<re4dc_gcasset::SourceGeometry)|
                (re4dc_gcasset_weapon_consumer(p->model,p->info,member.arc,member.family)?1U<<re4dc_gcasset::Weapon:0U);
            // Role is known, but a full BIN hash does not authenticate every
            // consumed UV/color/weight/shape extent or prepared derivation.
            re4dc_gcasset::source_use={0,mask,p->model,p->info};
        }
    }
#endif
#if RE4DC_NATIVE_ACTOR
    // Non-scenery parts (actors, weapons, room SMD objects): dense per-info
    // preparation (native_actor.cpp). It declines before any side effect and
    // the generic path below then runs unchanged.
#if RE4DC_MODEL_STREAM_FIX && RE4DC_NATIVE_ACTOR_FAST
    if(p && (!p->static_geometry || re4dc_actor_stream_encoded(p->stream,p->stream_bytes)) && re4dc_actor_submit(p)){PP_PATH(2);return;}
#else
    if(p && !p->static_geometry && re4dc_actor_submit(p))return;
#endif
#if RE4DC_KOS_HEAP_CHECK
    if(p && p->stream && p->stream_bytes>=32 && p->stream[0]==0xfe){
        re4dc_log("MODEL_BLOB_DECLINED pos=%08x normal=%08x static=%u info=%08x stream=%08x\n",
          unsigned((std::uintptr_t)p->positions),unsigned((std::uintptr_t)p->normals),p->static_geometry,
          unsigned((std::uintptr_t)p->info),unsigned((std::uintptr_t)p->stream));
    }
#endif
#endif
#if RE4DC_NATIVE_ACTOR_SKIN
    // Declined part of an info whose source CalcSk1_x pass was deferred
    // (trans.cpp): fill its pPosBuf/pNrmBuf now, before the walker reads them.
#if RE4DC_NATIVE_ACTOR_SKIN_LAZY
    // NATIVE_ACTOR_SKIN_LAZY: a part of an info Trans() gave no arrays (NULL
    // positions): allocate and skin them now; on failure the checks below
    // reject the part.
    Re4dcModelPart lazy_part;
    if(p && !p->positions){lazy_part=*p;re4dc_actor_materialize_lazy(&lazy_part);p=&lazy_part;}
    else
#endif
    if(p)re4dc_actor_materialize(p);
#endif
#if RE4DC_MODEL_STREAM_FIX && RE4DC_NATIVE_ACTOR_FAST
    // A previous part can materialize this info while a deferred view still
    // has null arrays. Refreshing those arrays makes the packed actor path
    // eligible again; its old GX plan describes bytes that no longer exist.
    if(p && re4dc_actor_stream_encoded(p->stream,p->stream_bytes)){
        if(re4dc_actor_submit(p)){PP_PATH(2);return;}
        // Invalid packed input has no GX fallback. Report the rejected part
        // before any stale index can reach a position/normal/shading cache.
#if RE4DC_KOS_HEAP_CHECK
        re4dc_log("MODEL_BLOB_REJECTED stream=%08x info=%08x\n",unsigned((std::uintptr_t)p->stream),unsigned((std::uintptr_t)p->info));
        re4dc_halt("Converted stream rejected",0);
#endif
        re4dc_model_result(1,0,0);return;
    }
#endif
#if RE4DC_KOS_HEAP_CHECK
    if(p && p->stream && p->stream_bytes>=32 && p->stream[0]==0xfe){
        re4dc_log("MODEL_BLOB_FALLBACK model=%08x info=%08x part=%08x stream=%08x bytes=%u static=%u flags=%08x alpha=%u cull=%u blend=%u\n",
          unsigned((std::uintptr_t)p->model),unsigned((std::uintptr_t)p->info),unsigned((std::uintptr_t)p->part),
          unsigned((std::uintptr_t)p->stream),p->stream_bytes,p->static_geometry,p->flags,p->alpha_state,p->cull,p->blend);
        re4dc_log("MODEL_BLOB_ARRAYS pos=%08x/%u/%u shift=%u normal=%08x/%u/%u shift=%u light=%08x colors=%08x uv=%08x\n",
          unsigned((std::uintptr_t)p->positions),p->position_count,p->position_stride,p->shift,
          unsigned((std::uintptr_t)p->normals),p->normal_count,p->normal_stride,p->normal_shift,
          unsigned((std::uintptr_t)p->lighting),unsigned((std::uintptr_t)p->colors),unsigned((std::uintptr_t)p->uv));
        if(p->lighting)re4dc_log("MODEL_BLOB_LIGHT enable=%u attenuation=%u ambient_vertex=%u material_vertex=%u projection=%f viewport=%f/%f\n",
          p->lighting->enable,p->lighting->attenuation,p->lighting->ambient_vertex,p->lighting->material_vertex,
          double(p->projection[0]),double(p->viewport[2]),double(p->viewport[3]));
        re4dc_halt("Converted stream reached GX",0);
    }
#endif
#if RE4DC_GC_ASSET_GATE
    // An actor decline may have restored a frozen/outer context. The generic
    // walker has no complete constituent receipt yet; preserve class only.
    re4dc_gcasset::source_use={0,re4dc_gcasset::source_use.mask,p?p->model:nullptr,p?p->info:nullptr};
#endif
    if(!p || p->alpha_state>511 || ((p->alpha_state&256) && (!(p->flags&0x80000000U) || !p->colors)) || p->shift>30 || (p->position_stride!=6 && p->position_stride!=8) ||
       !p->position_count || !p->normal_count || p->stream_bytes>1024*1024 ||
       !ram(p->positions,p->position_count*p->position_stride) || !ram(p->stream,p->stream_bytes) ||
       p->projection[0]!=0 || p->viewport[2]<=0 || p->viewport[3]<=0){re4dc_model_result(1,0,0);return;}
    Projection projection{p->projection,p->viewport};
    const float near=p->projection[6]/(p->projection[5]-1),far=p->projection[6]/p->projection[5];
    if(!std::isfinite(near)||!std::isfinite(far)||near<=0||far<=near){re4dc_model_result(1,0,0);return;}
    if(p->cull==3){re4dc_model_result(0,0,0);return;}
    ++work_stats.part_preparations;
    Builder b{*p,{},projection,{near,far,RE4DC_SCREEN_W,RE4DC_SCREEN_H,project,nullptr},0,0,
              (p->flags&0x80000000U)?8U:6U,pow2_neg(p->shift)};
    b.clip.context=&b.projection;
#if RE4DC_D349_RENDERER_STACK
    if(p->lighting){
        if((p->normal_shift!=6 && p->normal_shift!=14) ||
           !ram(p->normals,p->normal_count*p->normal_stride) ||
           (p->lighting->enable && p->lighting->attenuation!=1 && p->lighting->attenuation!=2) ||
           ((p->lighting->ambient_vertex || p->lighting->material_vertex) && (!(p->flags&0x80000000U) || !p->colors))){
            ++work_stats.lighting_rejects;re4dc_model_result(1,0,0);return;
        }
    }
#endif

    // Source data remains live throughout this synchronous call. In streaming
    // mode each bounded chunk is consumed once by the existing native owner;
    // no whole-scene copy and no repeated deformation/preparation pass.
    b.streaming=re4dc_model_packet_streaming()!=0;
    if(!re4dc_model_packet_reserve(p,&b.packet)){re4dc_model_result(2,0,0);return;}
    const re4dc::render::NativeDrawPlan* plan=nullptr;
#if RE4DC_MODEL_DRAW_PLANS
    int invalid=0;
    plan=re4dc_model_acquire_draw_plan(p,&invalid);
    struct PlanLease { const re4dc::render::NativeDrawPlan* p; ~PlanLease(){if(p)re4dc_model_release_draw_plan();} } lease{plan};
    if(invalid){re4dc_model_result(1,0,0);return;}
#endif
    if(plan){PP_PATH(3);
#if RE4DC_D349_RENDERER_STACK
        b.bounds=re4dc_model_acquired_bounds();b.locals=re4dc_model_acquired_locals();
        if(b.bounds && !re4dc::render::group_visible(b.bounds->group,p->modelview,p->projection,p->viewport,near,far,0)){
            ++work_stats.culled_groups;re4dc_model_result(0,0,0);return;
        }
#endif
        ++work_stats.prepared_parts;
        if(!ram(p->uv,(plan->max_uv+1)*4) ||
           (((p->alpha_state&256) || (p->lighting && (p->lighting->ambient_vertex || p->lighting->material_vertex))) && !ram(p->colors,(plan->max_color+1)*4))){re4dc_model_result(1,0,0);return;}
    }else {
        ++work_stats.unprepared_parts;PP_PATH(4);
        if(!b.walk(false)){re4dc_model_result(1,0,0);return;}
    }
#if RE4DC_D349_RENDERER_STACK
    if(re4dc_model_defer_part(p))return;
    b.batch=acquire_batch(*p);
    if(!b.batch && p->lighting)b.lights=re4dc::render::prepare_actor_lights(*p->lighting);
    b.static_context=b.batch?nullptr:prepare_room_static_lighting(*p);
#endif
#if RE4DC_NATIVE_REUSE_AUDIT && RE4DC_D349_RENDERER_STACK
    re4dc::reuse_audit::Scope reuse_audit(*p,plan,b.bounds,b.packet,p->lighting?(b.batch?b.batch->lights.count:b.lights.count):0);
#endif
    const auto emit=[&](){return plan?b.walk_plan(*plan):b.walk(true);};
    bool okay=emit();
    if(okay && b.used)okay=b.bind();
    if(!okay && b.restart_uv){
        // First binding precedes every publication. Restart only for a verified
        // alternate UV scale, retaining the already selected native texture.
        b.restart_uv=false;b.used=b.input=b.output=b.strip_vertices=0;b.pending_intact=b.pending_reconstructed=0;
        okay=emit();
        if(okay && b.used)okay=b.bind();
    }
    if(!okay){
        if(b.submitted)re4dc_model_packet_abort();
        re4dc_model_result(b.resource_failed?2:3,b.input,0);return;
    }
    re4dc_model_packet_commit(b.used);re4dc::reuse_audit::commit(b.used);b.committed_strips();re4dc_model_result(0,b.input,b.output);
}

extern "C" const Re4dcModelWorkStats* re4dc_model_work_stats(){return &work_stats;}

extern "C" void re4dc_model_detach_retained_storage(){
#if RE4DC_D349_RENDERER_STACK
    if(prepared_batch){prepared_batch->retained=nullptr;prepared_batch->invalidate();}
#endif
}
extern "C" void re4dc_model_preparation_frame(){
#if RE4DC_D349_RENDERER_STACK
    if(prepared_batch)prepared_batch->invalidate();
#endif
}
extern "C" const Re4dcPreparationStats* re4dc_model_preparation_stats(){
#if RE4DC_D349_RENDERER_STACK
    return &preparation_stats;
#else
    static Re4dcPreparationStats none{};return &none;
#endif
}
extern "C" void re4dc_model_invalidate_static_lighting(){
#if RE4DC_D349_RENDERER_STACK
    if(static_lighting)new(static_lighting) StaticLighting{};
    if(prepared_batch)prepared_batch->invalidate();
#endif
}

#if defined(__sh__)
#include <arch/timer.h>
extern "C" unsigned re4dc_model_source_stamp(){return unsigned(timer_us_gettime64());}
extern "C" void re4dc_model_source_span(unsigned stage,unsigned start){
    if(stage<6)work_stats.source_prepare_us[stage]+=re4dc_model_source_stamp()-start;
}
extern "C" void re4dc_model_skipped_writeback(unsigned bytes){work_stats.pose_writeback_bytes_skipped+=bytes;}
#endif

#if defined(RE4DC_TEST_GENERATIONS) && RE4DC_D349_RENDERER_STACK
extern "C" void re4dc_model_test_serial(unsigned value){if(prepared_batch)prepared_batch->serial=value;}
#endif
