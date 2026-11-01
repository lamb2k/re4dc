#if defined(RE4DC_STATIC_OBJ_LIFETIME05) && RE4DC_STATIC_OBJ_LIFETIME05
#include "platform/include/static_obj_lifetime05.hpp"
#include "platform/include/static_obj_siblings05.hpp"
#endif
#if defined(RE4DC_STATIC_OBJ_BATCH33) && RE4DC_STATIC_OBJ_BATCH33
#include "platform/include/static_obj_batch33.hpp"
#endif
#if defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT
#include "platform/include/draw_fallback_audit.h"
#define DFA26_MODEL_HIT(reason, n) ::re4dc::dfa26::hit(::re4dc::dfa26::reason, (n));
#define DFA26_MODEL_SLOW(reason, n, ...) { DFA26_MODEL_HIT(reason, n) __VA_ARGS__ }
#else
#define DFA26_MODEL_HIT(reason, n)
#define DFA26_MODEL_SLOW(reason, n, ...) __VA_ARGS__
#endif
#include "platform/include/gc_asset_motion_unknown.h"
#include "actor_visibility_diag.h"
// Recovered commonModelTrans -> existing native frame/packet/texture owner.
// Diagnostic base-material connection; not full GX lighting/TEV emulation.
#include "light.h"
#include "global.h"
#include "model.h"
#include "gx.h"
#include "native_model.h"
#if defined(RE4DC_STATIC_OBJ_SPANS10) && RE4DC_STATIC_OBJ_SPANS10
#include "platform/include/static_obj_spans10.h"
#include "platform/include/native_draw_owner_stamp.hpp"
#endif
#if defined(RE4DC_GC_ASSET_GATE) && RE4DC_GC_ASSET_GATE
#include "gc_asset_members.h"
#include "player.h"
#endif
#if RE4DC_NATIVE_FOG
#include "view.h"
extern "C" unsigned re4dc_fog_enabled();
extern "C" void re4dc_fog_note_far(float far);
#endif
#include <stddef.h>
#include <string.h>
static_assert(sizeof(ModelPart)==0x20 && offsetof(ModelPart,size)==0x18);
static_assert(offsetof(ModelData,pParts)==0x1c && offsetof(ModelData,nVtx)==0x38);
static_assert(sizeof(void*)==4 && sizeof(GXTexObj)==32);
extern "C" void GXGetProjectionv(float*);
extern "C" void GXGetViewportv(float*);
#if RE4DC_LEON_FACE_LAZY
extern "C" void re4dc_face_lazy_resolve(const void* info);  // trans.cpp (game30.mk LEON_FACE_LAZY)
#endif
#if RE4DC_NATIVE_ACTOR
#include "native_actor.hpp"
#if RE4DC_ACTOR_TRANSACTION
#include "actor_native_owner.h"
#endif

extern "C" void* re4dc_prim_tail(unsigned bytes,unsigned reserve);
#endif
namespace {
#if RE4DC_NATIVE_ACTOR
// Once per source Render(): the actor workspace is the unused tail of this
// frame's primitive buffer. Trans() filled the buffer before Render(); the next
// SetPrimBuffPtr() (after Render() and its translucent drain) releases it, so
// nothing stays resident. 56 KiB covers the largest D358 actor info
// (3622 positions x 12 + 2785 normals x 4 = 54,604 B); a larger or unfunded
// info declines to the generic path.
unsigned actor_frame=~0U;
#if RE4DC_ACTOR_TRANSACTION
bool actor_frame_live;
#endif
void bind_actor_frame(){
#if RE4DC_ACTOR_TRANSACTION
    if(actor_frame_live && actor_frame==pG->Frame_cnt)return;
    actor_frame_live=true;
#else
    if(actor_frame==pG->Frame_cnt)return;
#endif
    actor_frame=pG->Frame_cnt;
    constexpr unsigned kBytes=56*1024,kReserve=16*1024;
#if RE4DC_NATIVE_ACTOR_FAST
    // Meshlet path: per-part conversion scratch + skin tables; 96 KiB when
    // the buffer has it, else the same 56 KiB (larger parts then decline).
    // While a deferred LOD build waits, first the larger size it asks for,
    // then 128 KiB (most parts' simplifier fits).
    constexpr unsigned kFastBytes=96*1024,kLodBytes=128*1024;
    if(const unsigned want=re4dc_actor_workspace_want()){
        if(void* lw=re4dc_prim_tail(want,kReserve)){re4dc_actor_frame(lw,want);return;}
        if(want>kLodBytes)
            if(void* mw=re4dc_prim_tail(kLodBytes,kReserve)){re4dc_actor_frame(mw,kLodBytes);return;}
    }
    if(void* fw=re4dc_prim_tail(kFastBytes,kReserve)){re4dc_actor_frame(fw,kFastBytes);return;}
#endif
    void* w=re4dc_prim_tail(kBytes,kReserve);
#if RE4DC_NATIVE_ACTOR_FAST && RE4DC_ACTOR_CROWD
    // Crowds fill the buffer with per-info skin arrays: parts already
    // converted still draw from a small workspace (skin tables only).
    if(!w)for(unsigned small=32*1024;small>=12*1024;small-=10*1024)
        if(void* sw=re4dc_prim_tail(small,kReserve)){re4dc_actor_frame(sw,small);return;}
#endif
    re4dc_actor_frame(w,w?kBytes:0);
}
#endif
Re4dcUiImage selected{},mask{};
unsigned mask_ref=256,mask_same_uv;
unsigned wrap_s,wrap_t;
float scroll_u,scroll_v;
}
#if RE4DC_NATIVE_ACTOR_FAST
#if RE4DC_COARSE_LEON
extern "C" int re4dc_coarse_actor_source(const void*,Re4dcActorSource*);
extern "C" void re4dc_bind_actor_frame(){bind_actor_frame();}
#if RE4DC_ACTOR_TRANSACTION
extern "C" void re4dc_actor_model_frame_retire(){actor_frame_live=false;}
#endif
#endif
// Unskinned source arrays of an info, for draw-time skinning (NATIVE_ACTOR_SKIN).
extern "C" int re4dc_actor_model_source(const void* info_ptr,Re4dcActorSource* out){
#if RE4DC_ACTOR_TRANSACTION
    if(re4dc_actor_owned_source(info_ptr,pG->Frame_cnt,out))return 1;
#endif

#if RE4DC_COARSE_LEON
    if(re4dc_coarse_actor_source(info_ptr,out))return 1;
#endif
    auto* info=(const cModelInfo*)info_ptr;
    if(!info || !out || !info->pData)return 0;
    const ModelData* d=info->pData;
    out->positions=(const unsigned char*)d->vtxOrig;out->normals=(const unsigned char*)d->nrmOrig;
    out->position_count=d->nVtx;out->normal_count=d->nNrm;
    out->palette_entries=d->weight_ext_num>0xff?d->weight_ext_num:d->weight_palette_num;
    out->small_normals=(d->flags&0x20000000U)!=0;
    return 1;
}
#if RE4DC_NATIVE_ACTOR_SKIN_LAZY
// NATIVE_ACTOR_SKIN_LAZY: after re4dc_skin_materialize() gave a lazily
// deferred info its arrays, the part view takes them as this bridge would.
extern "C" int re4dc_actor_model_buffers(Re4dcModelPart* p){
    auto* info=(const cModelInfo*)p->info;
#if RE4DC_LEON_FACE_LAZY
    re4dc_face_lazy_resolve(info);  // LEON_FACE_LAZY (trans.cpp): a deferred face info's arrays, before they are read
#endif
    p->positions=(const unsigned char*)info->pPosBuf[pG->vtx_buf_no];
    p->normals=(const unsigned char*)info->pNrmBuf[pG->vtx_buf_no];
    return p->positions && p->normals;
}
#endif
// Static prelit hint: no motion playing (Motion.pMot NULL), no shape
// (vertex delta) table and no shape-animation flag on the info.
extern "C" int re4dc_actor_model_prelit(const void* model,const void* info_ptr){
#if RE4DC_COARSE_LEON
    Re4dcActorSource alternate{};if(re4dc_coarse_actor_source(info_ptr,&alternate))return 0;
#endif
    auto* m=(const cModel*)model;auto* info=(const cModelInfo*)info_ptr;
    if(!m || !info || !info->pData)return 0;
    return !m->pMotion && !info->pData->shapeOfs && !(info->be_flag&2);
}
#if RE4DC_ACTOR_CROWD
#include "em10.h"
// Crowd render class: Ganado-family enemies (cEm10 modules em10..em20;
// cModel kindid 0) are 1, their head info (Em10Work::pHead) 2; else 0.
extern "C" int re4dc_actor_model_class(const void* model,const void* info_ptr){
    auto* m=(const cModel*)model;
    if(!m || m->kindid!=0 || m->id<0x10 || m->id>0x20)return 0;
    cEm10* em=(cEm10*)m;
    return EM10_WK(em)->pHead==(const cModelInfo*)info_ptr?2:1;
}
#endif
#if defined(RE4DC_GIGANTE_LIGHTS) && RE4DC_GIGANTE_LIGHTS
// GIGANTE_LIGHTS (native_actor_fast.cpp build_lights): the enemy id of a kindid-0 model, else -1.
extern "C" int re4dc_actor_model_id(const void* model){
    auto* m=(const cModel*)model;
    return m && m->kindid==0 ? int(m->id) : -1;
}
#if defined(RE4DC_STATUE_LIGHTS) && RE4DC_STATUE_LIGHTS
// STATUE_LIGHTS: the object id of a kindid-1 model (cObj), else -1.
extern "C" int re4dc_actor_obj_id(const void* model){
    auto* m=(const cModel*)model;
    return m && m->kindid==1 ? int(m->id) : -1;
}
#endif
#endif
#endif
#if defined(RE4DC_BARN28_DIAG) && RE4DC_BARN28_DIAG
// BARN28_DIAG (barn28.mk): kindid << 8 | id of a model (-1 none), for the B28L rows.
extern "C" int re4dc_b28_model_kind(const void* model){
    auto* m=(const cModel*)model;
    return m ? int((unsigned(m->kindid)&255U)<<8|(unsigned(m->id)&255U)) : -1;
}
#endif
#if defined(RE4DC_FALLBACK_AUDIT29) && RE4DC_FALLBACK_AUDIT29
// Read the source declarations only when a new diagnostic row is installed.
// Unknown chunk/attachment identities stay unknown; never guess a package row.
extern "C" void re4dc_fa29_actor_identity(const Re4dcModelPart* p,unsigned* tag,unsigned* info_index,unsigned* offset){
    *tag=*info_index=*offset=~0U;
    const auto* m=static_cast<const cModel*>(p->model);
    const auto* info=static_cast<const cModelInfo*>(p->info);
    if(!m)return;
    *tag=((unsigned(m->kindid)&255U)<<24)|((unsigned(m->id)&255U)<<16)|
         ((unsigned(m->type)&255U)<<8)|(unsigned(m->nParts)&255U);
    const cModelInfo* q=m->pModelInfo;
    for(unsigned n=0;q && n<1024;++n,q=q->pList){if(q==info){*info_index=n;break;}}
    if(!info || !info->pData || p->part==p->info)return;
    const auto* d=info->pData;
    const uintptr_t base=reinterpret_cast<uintptr_t>(d),part=reinterpret_cast<uintptr_t>(p->part);
    // Only publish an offset after finding the submitted part in this model's
    // real part table. A chunk's synthetic view is not an offline source row.
    const ModelPart* source=d->pParts;
    for(unsigned n=0;source && n<d->displist_num && n<4096;++n){
        if(source==p->part){
            if(part>=base && part-base<16U*1024U*1024U)*offset=unsigned(part-base);
            break;
        }
        if(source->size>1024U*1024U)break;
        source=reinterpret_cast<const ModelPart*>(reinterpret_cast<const unsigned char*>(source)+sizeof(ModelPart)+source->size);
    }
}
#endif
extern "C" void re4dc_model_material(const void* object,float u,float v,unsigned flags){
    selected={};mask={};mask_ref=256;mask_same_uv=0;
    if(!object || (flags&4))return; // multi-texture blend needs its own native path
    // Current native GXTexObj layout, after source texture animation/swaps.
    const unsigned* w=(const unsigned*)object;
    selected.pixels=(const void*)w[0];selected.width=w[1]>>16;selected.height=w[1]&65535;
    selected.format=w[2];selected.palette_format=0xffffffffU;
    wrap_s=(w[3]>>8)&255;wrap_t=w[3]&255;
    scroll_u=(flags&1)?u:0;scroll_v=(flags&1)?v:0;
}
extern "C" void re4dc_model_alpha_material(const void* object,unsigned ref,unsigned same_uv){
#if RE4DC_D349_RENDERER_STACK
    if(!object)return;
    const unsigned* w=(const unsigned*)object;
    mask.pixels=(const void*)w[0];mask.width=w[1]>>16;mask.height=w[1]&65535;
    mask.format=w[2];mask.palette_format=0xffffffffU;
    mask_ref=ref;mask_same_uv=same_uv && ((w[3]>>8)&255)==wrap_s && (w[3]&255)==wrap_t;
#else
    (void)object;(void)ref;(void)same_uv;
#endif
}
#if RE4DC_FRONT_NATIVE>=2
// D367 FRONT_NATIVE=2 (trans.cpp ModelRender): the source path records a hash per field group of
// every part it submits for one model (mode 1); the native replay (mode 2) is compared part by
// part and not drawn. Groups: 0 geometry/arrays/modes, 1 modelview, 2 projection+viewport,
// 3 texture+uv, 4 alpha state, 5 alpha mask, 6 static binding, 7 lighting contents,
// 8 (groups bit 0x100) the PVR header words (cmd/ISP/TSP/TCW; words 4-7 are not written by
// pvr_poly_compile): the header re4dc_model_packet_begin built for the
// source part (drawn in place; deferred, static-package and rejected parts are "unchecked")
// against re4dc_model_header_preview of the replayed part. Groups bit 0x80000000 = count overflow.
extern "C" void re4dc_log(const char* fmt,...);
extern "C" int re4dc_model_header_preview(const Re4dcModelPart* p,void* out);
namespace {
constexpr unsigned kFrontParts=512,kFrontGroups=8;
unsigned front_mode,front_n,front_k,front_model_bad,front_block=~0U,front_logged;
unsigned front_hash[kFrontParts][kFrontGroups];
unsigned front_models,front_parts,front_bad_parts,front_bad_models,front_group_bad[kFrontGroups];
unsigned front_cur=~0U,front_hdr[kFrontParts][8];
unsigned char front_hdr_ok[kFrontParts];
unsigned front_hdr_alpha[kFrontParts];
unsigned front_g8_checked,front_g8_bad,front_g8_unchecked,front_g8_nopreview;
inline unsigned fnv(unsigned h,const void* p,unsigned n){
    auto* b=(const unsigned char*)p;for(unsigned i=0;i<n;++i)h=(h^b[i])*16777619U;return h;
}
template<class T> inline unsigned fv(unsigned h,const T& v){return fnv(h,&v,sizeof(v));}
inline unsigned fimg(unsigned h,const Re4dcUiImage& i){
    h=fv(h,i.pixels);h=fv(h,i.palette);h=fv(h,i.width);h=fv(h,i.height);h=fv(h,i.format);
    h=fv(h,i.palette_format);return fv(h,i.palette_bytes);
}
void front_hash_part(const Re4dcModelPart* p,unsigned* g){
    const unsigned s=2166136261U;unsigned h=s;
    h=fv(h,p->model);h=fv(h,p->info);h=fv(h,p->part);h=fv(h,p->positions);h=fv(h,p->normals);
    h=fv(h,p->uv);h=fv(h,p->stream);h=fv(h,p->position_count);h=fv(h,p->normal_count);
    h=fv(h,p->position_stride);h=fv(h,p->stream_bytes);h=fv(h,p->shift);h=fv(h,p->flags);
    h=fv(h,p->cull);h=fv(h,p->blend);h=fv(h,p->depth_mode);h=fv(h,p->material_flags);
    h=fv(h,p->colors);h=fv(h,p->normal_stride);h=fv(h,p->normal_shift);g[0]=fv(h,p->static_geometry);
    g[1]=fnv(s,p->modelview,sizeof(p->modelview));
    g[2]=fnv(fnv(s,p->projection,sizeof(p->projection)),p->viewport,sizeof(p->viewport));
    h=fimg(s,p->image);h=fv(h,p->uv_offset[0]);h=fv(h,p->uv_offset[1]);h=fv(h,p->wrap_s);g[3]=fv(h,p->wrap_t);
    g[4]=fv(s,p->alpha_state);
    h=fimg(s,p->mask);h=fv(h,p->mask_ref);g[5]=fv(h,p->mask_same_uv);
    h=fv(s,p->serial);h=fv(h,p->world);h=fv(h,p->view);g[6]=fnv(h,p->source_key,sizeof(p->source_key));
    g[7]=p->lighting?fnv(s,p->lighting,sizeof(*p->lighting)):0;
}
// The emitters may hand packet_begin an adjusted copy: native_static draws a vertex-alpha part
// whose alpha cannot reach the image (all vertices opaque, or blend 0 unmasked) as alpha_state
// 255. That is the only adjustment group 8 accepts (counted); any other alpha_state change
// is previewed as is and so shows as a group 8 mismatch.
Re4dcModelPart front_g8_part;
unsigned front_g8_adjusted;
const Re4dcModelPart* front_g8_alpha(const Re4dcModelPart* p,unsigned alpha_state){
    if(!(p->alpha_state&256) || alpha_state!=255)return p;
    front_g8_part=*p;front_g8_part.alpha_state=255;++front_g8_adjusted;return &front_g8_part;
}
int front_verify_part(const Re4dcModelPart* p){
    if(!front_mode)return 0;
    unsigned g[kFrontGroups];front_hash_part(p,g);
    if(front_mode==1){
        if(front_n<kFrontParts){memcpy(front_hash[front_n],g,sizeof(g));front_hdr_ok[front_n]=0;front_cur=front_n;}
        ++front_n;return 0;
    }
    const unsigned k=front_k++;++front_parts;
    unsigned bad=k<front_n && k<kFrontParts?0U:0x80000000U;
    for(unsigned i=0;!bad && i<kFrontGroups;++i)if(g[i]!=front_hash[k][i]){bad|=1U<<i;++front_group_bad[i];}
    if(!bad){
        unsigned h[8];
        if(!front_hdr_ok[k])++front_g8_unchecked;
        else if(!re4dc_model_header_preview(p->alpha_state==front_hdr_alpha[k]?p:front_g8_alpha(p,front_hdr_alpha[k]),h))++front_g8_nopreview;
        else if(++front_g8_checked,memcmp(h,front_hdr[k],16)){
            bad|=0x100U;++front_g8_bad;
            if(front_logged<24){++front_logged;
                re4dc_log("front_native: GROUP8 frame=%u part=%p source=%08x,%08x,%08x,%08x native=%08x,%08x,%08x,%08x\n",pG->Frame_cnt,p->part,
                          front_hdr[k][0],front_hdr[k][1],front_hdr[k][2],front_hdr[k][3],h[0],h[1],h[2],h[3]);}
        }
    }
    if(bad){
        ++front_bad_parts;front_model_bad=1;
        if(front_logged<24){++front_logged;
            re4dc_log("front_native: MISMATCH frame=%u model=%p info=%p part=%p k=%u groups=0x%x\n",
                      pG->Frame_cnt,p->model,p->info,p->part,k,bad);}
    }
    return 1;
}
}
extern "C" void re4dc_front_header_built(const void* header,unsigned alpha_state){
    if(front_mode==1 && front_cur<kFrontParts && !front_hdr_ok[front_cur]){
        memcpy(front_hdr[front_cur],header,sizeof(front_hdr[0]));front_hdr_ok[front_cur]=1;
        front_hdr_alpha[front_cur]=alpha_state;
    }
}
extern "C" void re4dc_front_verify(int mode){
    if(mode==1)front_n=0;
    else if(mode==2){front_k=0;front_model_bad=0;}
    else if(front_mode==2){
        ++front_models;
        if(front_k!=front_n){front_model_bad=1;
            if(front_logged<24){++front_logged;re4dc_log("front_native: COUNT frame=%u source=%u native=%u\n",pG->Frame_cnt,front_n,front_k);}}
        front_bad_models+=front_model_bad;
        const unsigned block=pG->Frame_cnt/600;
        if(block!=front_block){front_block=block;
            re4dc_log("front_native: frame=%u models=%u parts=%u bad_models=%u bad_parts=%u groups=%u,%u,%u,%u,%u,%u,%u,%u\n",
                pG->Frame_cnt,front_models,front_parts,front_bad_models,front_bad_parts,front_group_bad[0],front_group_bad[1],
                front_group_bad[2],front_group_bad[3],front_group_bad[4],front_group_bad[5],front_group_bad[6],front_group_bad[7]);
            re4dc_log("front_native: group8 frame=%u checked=%u bad=%u unchecked=%u nopreview=%u opaque_vertex_alpha=%u\n",pG->Frame_cnt,
                front_g8_checked,front_g8_bad,front_g8_unchecked,front_g8_nopreview,front_g8_adjusted);}
    }
    front_mode=(unsigned)mode;
}
#endif
#if defined(RE4DC_GCOBJ_SKIP) && RE4DC_GCOBJ_SKIP
// GCOBJ_SKIP (crowd.mk, measurement only): the GC-path object classes; statics only when only_static.
static inline bool re4dc_gcobj_class(unsigned kind, unsigned id, bool only_static) {
    if (kind == 0) return id == 0x41 || id == 0x43 || id == 0x45 || id == 0x46 || (!only_static && id == 0x42);
    if (kind == 1) return id == 0x00 || id == 0x21 || (!only_static && (id == 0x12 || id == 0x19));
    return false;
}
#endif
#if defined(RE4DC_STATIC_OBJ_BATCH) && RE4DC_STATIC_OBJ_BATCH
// STATIC_OBJ_BATCH (crowd.mk): one actor part per run of identical-record display lists of one static object info.
// All state but a pointer lives in heap-4 room cells, freed at room leave (KOS malloc and BSS have no room).
extern "C" int re4dc_actor_stream_encoded(const unsigned char* stream,unsigned bytes);  // native_actor_fast.cpp
extern "C" void* re4dc_static_alloc(unsigned bytes);                                    // ui_bridge.cpp
extern "C" void re4dc_static_free(void* data);
extern "C" int re4dc_room4_state(unsigned* generation,unsigned* cells,unsigned* bytes,unsigned* stale,unsigned* refused);
namespace sob {
constexpr unsigned kMaxParts=16,kEntries=48,kSentinel=8;
struct Entry {
    const void* model; const void* info; const void* data; unsigned n,bytes;
    const ModelPart* parts[kMaxParts]; unsigned char head[kMaxParts][kSentinel];
    unsigned char* buf;
};
struct Pending {
    bool on; Re4dcModelPart rec; re4dc::render::SourceLighting light;
    const void* model; const void* info; unsigned n; const ModelPart* parts[kMaxParts];
};
struct State { unsigned generation,count,bytes; Pending pend; Entry e[kEntries]; };
State* S=nullptr;
unsigned seen_frame=~0U,generation=0; bool live=false;
const void* cur_model=nullptr; const void* cur_info=nullptr; unsigned cur_idx=0;
struct Stats { unsigned groups,lists,merged,saved,built,refused,singles,lit,log; } st{};
#if defined(RE4DC_STATIC_OBJ_LIFETIME05) && RE4DC_STATIC_OBJ_LIFETIME05
re4dc::sob05::Cell<State> owner;
bool validate(){
    State* prior=S;
    S=owner.get();
    live=re4dc_room4_live_generation(&generation)!=0;
    if(prior && !S){cur_model=cur_info=nullptr;cur_idx=0;}
    return S!=nullptr;
}
#endif
inline bool static_class(const cModel* m){
    const unsigned k=m->kindid,id=m->id;
    return (k==0&&(id==0x41||id==0x43||id==0x45||id==0x46))||(k==1&&id==0x21);
}
// build_lights folds point lights at the blob centre: only these groups' lighting depends on where the centre is.
inline bool centre_lit(const re4dc::render::SourceLighting& L){
    return L.enable && !L.ambient_vertex && !L.material_vertex && L.diffuse==2 && L.mask;
}
#if defined(RE4DC_SOB_WORDCMP) && RE4DC_SOB_WORDCMP
// Word compare (newlib memcmp is a byte loop): both records are word-aligned structs of whole words.
inline bool words_equal(const void* x,const void* y,unsigned bytes){
    const unsigned* a=(const unsigned*)x;const unsigned* b=(const unsigned*)y;
    for(unsigned i=0,n=bytes/4U;i<n;++i)if(a[i]!=b[i])return false;
    return true;
}
static_assert(sizeof(Re4dcModelPart)%4U==0 && sizeof(re4dc::render::SourceLighting)%4U==0,"word compare");
// Records equal but for the stream, its size, the part header and the lighting address; lighting content equal.
inline bool same(const Re4dcModelPart& a,const Re4dcModelPart& b){
    if(a.lighting!=b.lighting && !words_equal(a.lighting,b.lighting,sizeof(re4dc::render::SourceLighting)))return false;
    Re4dcModelPart t=b;t.stream=a.stream;t.stream_bytes=a.stream_bytes;t.part=a.part;t.lighting=a.lighting;
    return words_equal(&a,&t,sizeof t);
}
#else
// Records equal but for the stream, its size, the part header and the lighting address; lighting content equal.
inline bool same(const Re4dcModelPart& a,const Re4dcModelPart& b){
    Re4dcModelPart t=b;t.stream=a.stream;t.stream_bytes=a.stream_bytes;t.part=a.part;t.lighting=a.lighting;
    return !memcmp(&a,&t,sizeof t) && !memcmp(a.lighting,b.lighting,sizeof(re4dc::render::SourceLighting));
}
#endif
inline const unsigned char* list_of(const ModelPart* q){return (const unsigned char*)q+0x20;}
void new_frame(){
    seen_frame=pG->Frame_cnt;
#if defined(RE4DC_STATIC_OBJ_LIFETIME05) && RE4DC_STATIC_OBJ_LIFETIME05
    validate();
#else
    unsigned cells,bytes,stale,refused;
    live=re4dc_room4_state(&generation,&cells,&bytes,&stale,&refused)!=0;
    if(S && (!live || S->generation!=generation))S=nullptr;  // a heap-4 reset without a room leave: the cells are gone
#endif
    if(seen_frame-st.log>=600U){
        st.log=seen_frame;
        re4dc_log("SOBATCH frame=%u groups=%u lists=%u merged=%u saved=%u built=%u refused=%u singles=%u lit=%u entries=%u bytes=%u\n",
            seen_frame,st.groups,st.lists,st.merged,st.saved,st.built,st.refused,st.singles,st.lit,
            S?S->count:0U,S?S->bytes:0U);
    }
}
#if !defined(RE4DC_STATIC_OBJ_LIFETIME05) || !RE4DC_STATIC_OBJ_LIFETIME05
Entry* find(const Pending& q){
    for(unsigned k=0;k<S->count;++k){
        Entry& e=S->e[k];
        if(e.model!=q.model || e.info!=q.info || e.n!=q.n || e.data!=((const cModelInfo*)q.info)->pData)continue;
        unsigned total=0;bool ok=true;
        for(unsigned i=0;ok && i<e.n;++i){
            ok=e.parts[i]==q.parts[i] && !memcmp(e.head[i],list_of(q.parts[i]),kSentinel);
            total+=q.parts[i]->size;
        }
        if(ok && total==e.bytes)return &e;
    }
    return nullptr;
}
Entry* build(const Pending& q){
    if(S->count>=kEntries)return nullptr;
    unsigned total=0;
    for(unsigned i=0;i<q.n;++i){
        const unsigned b=q.parts[i]->size;
        if(b<32 || re4dc_actor_stream_encoded(list_of(q.parts[i]),b))return nullptr;  // only unconverted GX lists
        total+=b;
    }
    if(total>0x3FFF0U)return nullptr;
    auto* buf=(unsigned char*)re4dc_static_alloc(total);
    if(!buf)return nullptr;
    if((unsigned)buf&31U){re4dc_static_free(buf);return nullptr;}  // display lists are 32-byte aligned
    Entry& e=S->e[S->count++];
    unsigned at=0;
    for(unsigned i=0;i<q.n;++i){
        memcpy(buf+at,list_of(q.parts[i]),q.parts[i]->size);at+=q.parts[i]->size;
        e.parts[i]=q.parts[i];memcpy(e.head[i],list_of(q.parts[i]),kSentinel);
    }
    e.model=q.model;e.info=q.info;e.data=((const cModelInfo*)q.info)->pData;e.n=q.n;e.bytes=total;e.buf=buf;
    S->bytes+=total;++st.built;
    return &e;
}
#endif
#if RE4DC_STATIC_OBJ_SPANS10
struct SpanFence10 {const State* state;unsigned generation,incarnation;};
bool span_current10(const void* context){
    const auto& f=*static_cast<const SpanFence10*>(context);
    return validate() && S==f.state && owner.generation==f.generation && owner.incarnation==f.incarnation;
}
bool submit_spans10(const Pending& q){
    Re4dcModelSpan10 spans[kMaxParts];
    for(unsigned i=0;i<q.n;++i){
        // Unknown source extents retain the ordinary uncached path. Never
        // inspect a source header using the room-cell token as its authority.
        if(!re4dc_model_draw_owner_stamp(q.parts[i],32).valid())return false;
        spans[i]={q.parts[i],list_of(q.parts[i]),q.parts[i]->size};
    }
    const SpanFence10 fence{S,owner.generation,owner.incarnation};
    return re4dc_model_submit_spans10(&q.rec,spans,q.n,span_current10,&fence)!=0;
}
#endif
void flush(){
#if defined(RE4DC_STATIC_OBJ_LIFETIME05) && RE4DC_STATIC_OBJ_LIFETIME05
    if(!validate())return;
    // Submission may reenter room retirement. Keep the record/light off the
    // room cell, and drop it before touching source pointers after retirement.
    State* const held=S;
    const unsigned held_generation=owner.generation,held_incarnation=owner.incarnation;
    Pending q=S->pend;
    S->pend.on=false;
    q.rec.lighting=&q.light;
#else
    Pending& q=S->pend;
#endif
    if(!q.on)return;
#if RE4DC_GC_ASSET_MOTION_UNKNOWN
    // Held/cached merged groups never borrow the replay caller's current pose.
    re4dc_gcasset::MotionUnknownScope gcasset_motion_scope(re4dc_gcasset::MotionDelayedModel|re4dc_gcasset::MotionModelPose|re4dc_gcasset::MotionViewTrack);
#endif
    q.on=false;
    ++st.groups;st.lists+=q.n;
    Re4dcModelPart r=q.rec;
    if(q.n>1){
#if RE4DC_STATIC_OBJ_SPANS10
        if(submit_spans10(q)){++st.merged;st.saved+=q.n-1;return;}
#endif
#if !defined(RE4DC_STATIC_OBJ_LIFETIME05) || !RE4DC_STATIC_OBJ_LIFETIME05
        Entry* e=find(q);
        if(!e)e=build(q);
        if(e){
            r.stream=e->buf;r.stream_bytes=e->bytes;r.part=q.parts[0];
            ++st.merged;st.saved+=q.n-1;
            re4dc_model_submit(&r);
            return;
        }
#endif
#if defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT
        DFA26_MODEL_HIT(ModelObjectBatchRefused, q.n)
#endif
        ++st.refused;
    } else ++st.singles;
    for(unsigned i=0;i<q.n;++i){
#if defined(RE4DC_STATIC_OBJ_LIFETIME05) && RE4DC_STATIC_OBJ_LIFETIME05
        if(!validate() || S!=held || owner.generation!=held_generation || owner.incarnation!=held_incarnation)return;
#endif
        r.part=q.parts[i];r.stream=list_of(q.parts[i]);r.stream_bytes=q.parts[i]->size;
        re4dc_model_submit(&r);
    }
}
// 1: the part was taken (held, or submitted with its run); 0: the caller submits it.
bool take(const cModel* m,const cModelInfo* info,const ModelData* d,const ModelPart* part,const Re4dcModelPart& p){
#if defined(RE4DC_STATIC_OBJ_LIFETIME05) && RE4DC_STATIC_OBJ_LIFETIME05
    validate(); // frame identity cannot authorize a pointer after a same-frame reset
#endif
    if(pG->Frame_cnt!=seen_frame)new_frame();
    if(m!=cur_model || info!=cur_info){cur_model=m;cur_info=info;cur_idx=0;}
    const unsigned idx=++cur_idx;
    bool eligible=live && static_class(m) && p.blend==0 && p.lighting && d->displist_num>1 &&
                  d->displist_num<=kMaxParts && p.stream==list_of(part) && p.stream_bytes==part->size;
    if(eligible && centre_lit(*p.lighting)){
        if(idx==1)++st.lit;
        eligible=RE4DC_STATIC_OBJ_BATCH>=2;
    }
    if(eligible && !S){
#if defined(RE4DC_STATIC_OBJ_LIFETIME05) && RE4DC_STATIC_OBJ_LIFETIME05
        const unsigned expected=generation;
        State* fresh=(State*)re4dc_static_alloc(sizeof(State));
        // static_alloc may reclaim other packages; establish publication identity
        // only after it returns, before the first payload write.
        if(owner.bind(fresh,expected)){S=fresh;memset(S,0,sizeof(State));S->generation=expected;}
        else {
            S=nullptr;unsigned now=0;
            // A returned allocation with token zero (exhaustion) remains an
            // ordinary valid cell. Return it instead of leaking each refusal.
            if(re4dc_room4_live_generation(&now) && re4dc_room4_cell_valid(fresh,sizeof(State),now))
                re4dc_static_free(fresh);
        }
        if(!S)eligible=false;
#else
        S=(State*)re4dc_static_alloc(sizeof(State));
        if(S){memset(S,0,sizeof(State));S->generation=generation;}
        else eligible=false;
#endif
    }
#if defined(RE4DC_STATIC_OBJ_LIFETIME05) && RE4DC_STATIC_OBJ_LIFETIME05
    State* const held=S;
    const unsigned held_generation=owner.generation,held_incarnation=owner.incarnation;
#endif
    if(S && S->pend.on){
        const Pending& q=S->pend;
        if(!eligible || q.info!=info || q.model!=m || !same(q.rec,p))flush();
    }
#if defined(RE4DC_STATIC_OBJ_LIFETIME05) && RE4DC_STATIC_OBJ_LIFETIME05
    // flush/submit can retire this room or reenter another object run.
    if(eligible && (!validate() || S!=held || owner.generation!=held_generation || owner.incarnation!=held_incarnation))eligible=false;
#endif
    if(!eligible){DFA26_MODEL_HIT(ModelObjectBatchSplit, 1)if(idx>=d->displist_num)cur_info=nullptr;return false;}
    Pending& q=S->pend;
    if(!q.on){
        q.on=true;q.rec=p;q.light=*p.lighting;q.rec.lighting=&q.light;
        q.model=m;q.info=info;q.n=0;
    }
    q.parts[q.n++]=part;
    if(idx>=d->displist_num){flush();cur_info=nullptr;}
    return true;
}
}
// Room leave (ui_bridge.cpp re4dc_room_leave, before re4dc_room4_close): return every cell.
extern "C" void re4dc_sob_room_leave(){
#if defined(RE4DC_STATIC_OBJ_LIFETIME05) && RE4DC_STATIC_OBJ_LIFETIME05
    sob::State* state=sob::owner.get();
    // Detach pending/global references before free or any possible reentry.
    sob::owner.clear();sob::S=nullptr;sob::cur_model=sob::cur_info=nullptr;sob::cur_idx=0;
    sob::live=false;
    if(state)re4dc_static_free(state); // no persistent copied lists without source authority
#else
    if(!sob::S)return;
    for(unsigned k=0;k<sob::S->count;++k)re4dc_static_free(sob::S->e[k].buf);
    re4dc_static_free(sob::S);
    sob::S=nullptr;sob::cur_model=nullptr;sob::cur_info=nullptr;
#endif
}
#endif
#if defined(RE4DC_SOB_DUMP) && RE4DC_SOB_DUMP
#include <stdio.h>
// SOB_DUMP (crowd.mk, diagnostic): static etc object parts captured at first draw for the offline STATIC_OBJ_BAKE.
extern "C" int re4dc_actor_stream_encoded(const unsigned char* stream,unsigned bytes);
extern "C" void* re4dc_static_alloc(unsigned bytes);
extern "C" int re4dc_ui_part_key(const Re4dcModelPart* p,unsigned* crc,unsigned* fnv);  // native_ui.cpp
#if RE4DC_NATIVE_ACTOR_SKIN_LAZY
extern "C" int re4dc_actor_materialize_lazy(Re4dcModelPart* p);  // native_actor_fast.cpp
#endif
extern "C" int re4dc_room4_state(unsigned* generation,unsigned* cells,unsigned* bytes,unsigned* stale,unsigned* refused);
namespace sobdump {
constexpr unsigned kBytes=384u*1024u,kSeen=160,kLines=8,kLine=96,kMods=48,kSettle=60;
struct State { unsigned generation,used,sent,nseen,done,nlist,nmod; const void* seen[kSeen][2]; const void* lists[kSeen];
               const void* mod[kMods]; unsigned mod_frame[kMods]; unsigned char data[kBytes]; };
State* S=nullptr; unsigned frame_seen=~0U;
#if defined(RE4DC_STATIC_OBJ_LIFETIME05) && RE4DC_STATIC_OBJ_LIFETIME05
re4dc::sob05::Cell<State> owner;
bool validate(){S=owner.get();return S!=nullptr;}
bool current(const re4dc::sob05::Cell<State>& held){
    const bool ok=re4dc::sob05::current(owner,held);S=owner.get();return ok;
}
#endif
inline bool target(const cModel* m){
    const unsigned k=m->kindid,id=m->id;
    return (k==0&&(id==0x41||id==0x43||id==0x45||id==0x46))||(k==1&&id==0x21);
}
unsigned fnv(unsigned h,const void* p,unsigned n){const unsigned char* b=(const unsigned char*)p;for(unsigned i=0;i<n;++i)h=(h^b[i])*16777619U;return h;}
unsigned rest_hash(const cModel* m){
    unsigned h=fnv(2166136261U,m->mat,sizeof(Mtx));
    const cParts* q=(const cParts*)m->pParts;
    for(unsigned i=0;i<m->nParts && q;++i,q=q->pList)h=fnv(h,q->mat,sizeof(Mtx));
    return h;
}
void put(const void* p,unsigned n){
    if(S->used+n>kBytes){S->used=kBytes+1;return;}
    memcpy(S->data+S->used,p,n);S->used+=n;
}
void put32(unsigned v){put(&v,4);}
void frame(){
    frame_seen=pG->Frame_cnt;
#if defined(RE4DC_STATIC_OBJ_LIFETIME05) && RE4DC_STATIC_OBJ_LIFETIME05
    if(!validate())return;
    const auto held=owner;
#else
    unsigned g,c,b,st,rf;
    if(!re4dc_room4_state(&g,&c,&b,&st,&rf)){S=nullptr;return;}
    if(S && S->generation!=g)S=nullptr;
#endif
    if(!S || S->done || S->used>kBytes)return;
    char line[16+2*kLine+2];
    for(unsigned n=0;n<kLines && S->sent<S->used;++n){
        unsigned k=S->used-S->sent;if(k>kLine)k=kLine;
        int o=snprintf(line,sizeof line,"SOBX %06x ",S->sent);
        for(unsigned i=0;i<k;++i){static const char hx[]="0123456789abcdef";line[o++]=hx[S->data[S->sent+i]>>4];line[o++]=hx[S->data[S->sent+i]&15];}
        line[o++]='\n';line[o]=0;
        re4dc_log("%s",line);
#if defined(RE4DC_STATIC_OBJ_LIFETIME05) && RE4DC_STATIC_OBJ_LIFETIME05
        if(!current(held))return;
#endif
        S->sent+=k;
    }
}
bool ensure(){
#if defined(RE4DC_STATIC_OBJ_LIFETIME05) && RE4DC_STATIC_OBJ_LIFETIME05
    validate();
    if(!S){
        unsigned g=0;if(!re4dc_room4_live_generation(&g))return false;
        State* fresh=(State*)re4dc_static_alloc(sizeof(State));
        // Allocation can reclaim a package or reenter a newer owner.
        if(validate()){re4dc::sob05::discard(fresh,sizeof(State));return false;}
        if(!owner.bind(fresh,g)){re4dc::sob05::discard(fresh,sizeof(State));return false;}
        S=fresh;memset(S,0,sizeof(State)-kBytes);S->generation=g;
        const auto held=owner;
        re4dc_log("SOBX BEGIN room=%03x generation=%u\n",unsigned(pG->room_id),g);
        if(!current(held))return false;
    }
#else
    unsigned g,c,b,st,rf;
    if(!re4dc_room4_state(&g,&c,&b,&st,&rf))return false;
    if(S && S->generation!=g)S=nullptr;
    if(!S){
        S=(State*)re4dc_static_alloc(sizeof(State));
        if(!S){re4dc_log("SOBX FAIL alloc\n");return false;}
        memset(S,0,sizeof(State)-kBytes);S->generation=g;
        re4dc_log("SOBX BEGIN room=%03x generation=%u\n",unsigned(pG->room_id),g);
    }
#endif
    return true;
}
void part(const cModel* m,const cModelInfo* info,const ModelData* d,const ModelPart* pt,const Re4dcModelPart& p){
    if(pG->Frame_cnt!=frame_seen)frame();
    if(!target(m))return;
    unsigned g,c,b,st,rf;
    if(!re4dc_room4_state(&g,&c,&b,&st,&rf))return;
    if(!ensure())return;
#if defined(RE4DC_STATIC_OBJ_LIFETIME05) && RE4DC_STATIC_OBJ_LIFETIME05
    const auto held=owner;
#endif
    {   // settle: the first frames of a model hold matrices the game has not set yet (zero / identity)
        unsigned k=0;
        while(k<S->nmod && S->mod[k]!=m)++k;
        if(k==S->nmod){if(S->nmod>=kMods)return;S->mod[k]=m;S->mod_frame[k]=pG->Frame_cnt;++S->nmod;}
        if(pG->Frame_cnt-S->mod_frame[k]<kSettle)return;
    }
    for(unsigned i=0;i<S->nseen;++i)if(S->seen[i][0]==m && S->seen[i][1]==pt)return;
    if(S->nseen>=kSeen || S->used>kBytes)return;
    S->seen[S->nseen][0]=m;S->seen[S->nseen][1]=pt;++S->nseen;
    const int slot=-1;  // objects are keyed by id + rest position (getRoomEtc2 is not in the image)
    unsigned list_idx=0;{const ModelPart* q=d->pParts;while(q && q!=pt && list_idx<d->displist_num){q=(const ModelPart*)((const unsigned char*)q+0x20+q->size);++list_idx;}}
    const bool encoded=re4dc_actor_stream_encoded(p.stream,p.stream_bytes)!=0;
    const unsigned stride=(p.flags&0x80000000U)?8U:6U;
    unsigned nuv=0,nclr=0;
    const unsigned char* raw=encoded?nullptr:p.stream;unsigned raw_bytes=encoded?0U:p.stream_bytes;
    if(encoded){  // the part's raw copy (SOBL record: magic, total, model, data, part, bytes, index, list)
        for(unsigned o=0;o+28<=S->used && o+28<=kBytes;){
            unsigned mg,tot,q;memcpy(&mg,S->data+o,4);memcpy(&tot,S->data+o+4,4);
            if(tot<8)break;
            if(mg==0x4C424F53U){memcpy(&q,S->data+o+16,4);if(q==(unsigned)(size_t)pt){memcpy(&raw_bytes,S->data+o+20,4);raw=S->data+o+28;break;}}
            o+=tot;
        }
    }
    if(raw){
        unsigned o=0;const unsigned char* s=raw;
        while(o<raw_bytes){
            const unsigned op=s[o++];if(!op)continue;
            if(raw_bytes-o<2)break;
            const unsigned n=(s[o]<<8)|s[o+1];o+=2;
            if(n>(raw_bytes-o)/stride)break;
            for(unsigned k=0;k<n;++k){
                const unsigned char* t=s+o+k*stride;
                const unsigned uv=(t[stride-2]<<8)|t[stride-1];if(uv+1>nuv)nuv=uv+1;
                if(stride==8){const unsigned ci=(t[4]<<8)|t[5];if(ci+1>nclr)nclr=ci+1;}
            }
            o+=n*stride;
        }
    }
    unsigned crc=0,fnvk=0;re4dc_ui_part_key(&p,&crc,&fnvk);
#if defined(RE4DC_STATIC_OBJ_LIFETIME05) && RE4DC_STATIC_OBJ_LIFETIME05
    if(!current(held))return;
#endif
    const unsigned list_bytes=encoded?0U:p.stream_bytes;
    const unsigned npos=p.position_count,nnrm=p.normal_count;
    const unsigned len=4*4+16*4+24*4+4*4+npos*p.position_stride+nnrm*p.normal_stride+nuv*4+nclr*4+list_bytes;
    const unsigned at=S->used;
    put32(0x52424F53U);put32(0);
    put32(unsigned(slot)&0xFFFFU | (unsigned(m->kindid)<<16) | (unsigned(m->id)<<24));
    put32(list_idx | (unsigned(d->displist_num)<<16));
    put32((unsigned)(size_t)m);put32((unsigned)(size_t)info);put32((unsigned)(size_t)d);put32((unsigned)(size_t)pt);
    put32(rest_hash(m));put32(crc);put32(fnvk);put32(p.flags);put32(p.material_flags);
    put32(p.position_stride|(p.normal_stride<<8)|(unsigned(p.shift)<<16)|(unsigned(p.normal_shift)<<24));
    put32(p.blend|(p.cull<<8)|(p.depth_mode<<16)|(p.alpha_state<<24));
    put32(npos|(nnrm<<16));put32(nuv|(nclr<<16));put32(list_bytes);
    put(p.modelview,48);put(&pG->Cam.v_mat[0][0],48);
    put(&m->pos,12);put(&m->ang,12);put32(m->be_flag);put32(info->be_flag);
    put32(p.lighting?unsigned(sizeof(re4dc::render::SourceLighting)):0U);
    if(p.lighting)put(p.lighting,sizeof(re4dc::render::SourceLighting));
    Re4dcModelPart q=p;
#if RE4DC_NATIVE_ACTOR_SKIN_LAZY
    if(!q.positions)re4dc_actor_materialize_lazy(&q);  // lazily skinned info: the source's own CPU skin of this frame
#if defined(RE4DC_STATIC_OBJ_LIFETIME05) && RE4DC_STATIC_OBJ_LIFETIME05
    if(!current(held))return;
#endif
#endif
    if(q.positions)put(q.positions,npos*p.position_stride);else put32(0xDEADBEEFU);
    if(q.normals)put(q.normals,nnrm*p.normal_stride);
    if(p.uv)put(p.uv,nuv*4);
    if(p.colors)put(p.colors,nclr*4);
    if(list_bytes)put(p.stream,list_bytes);
    while(S->used<=kBytes && (S->used&3))put("",1);
    if(S->used<=kBytes){const unsigned total=S->used-at;memcpy(S->data+at+4,&total,4);}
    (void)len;
}
}
// SOB_DUMP: raw lists of a target model, from the model asset walk (before the plan owner encodes them in place).
extern "C" void re4dc_sobdump_lists(const void* model){
    using namespace sobdump;
    const cModel* m=(const cModel*)model;
    if(!target(m) || !ensure() || S->used>kBytes)return;
    for(const cModelInfo* info=m->pModelInfo;info;info=info->pList){
        const ModelData* d=info->pData;if(!d)continue;
        const ModelPart* q=d->pParts;
        for(unsigned i=0;q && i<d->displist_num;++i,q=(const ModelPart*)((const unsigned char*)q+0x20+q->size)){
            bool seen=false;
            for(unsigned k=0;k<S->nlist && !seen;++k)seen=S->lists[k]==q;
            if(seen || S->nlist>=kSeen)continue;
            const unsigned char* l=(const unsigned char*)q+0x20;
            if(re4dc_actor_stream_encoded(l,q->size))continue;
            S->lists[S->nlist++]=q;
            const unsigned at=S->used;
            put32(0x4C424F53U);put32(0);put32((unsigned)(size_t)m);put32((unsigned)(size_t)d);put32((unsigned)(size_t)q);
            put32(q->size);put32(i|(unsigned(d->displist_num)<<16));put(l,q->size);
            while(S->used<=kBytes && (S->used&3))put("",1);
            if(S->used<=kBytes){const unsigned total=S->used-at;memcpy(S->data+at+4,&total,4);}
        }
    }
}
#endif
#if defined(RE4DC_STATIC_OBJ_BAKE) && RE4DC_STATIC_OBJ_BAKE
// STATIC_OBJ_BAKE (crowd.mk; render only, default 0; lane crowd12 2026-10-15): static etc objects baked into the
// room's PS2 world package draw from it while the game asks to draw them at their baked rest pose (bit-identical
// model and part matrices); every other state is the object's live draw. Decided once per frame before submission
// (re4dc_sob_bake_frame, from re4dc_prepare_model_assets), applied by the world (PS2_PLACE_GATE) and ModelRender.
#include "trans.h"
#include "trans_ot.h"
extern "C" void* re4dc_static_alloc(unsigned bytes);
extern "C" int re4dc_room4_state(unsigned* generation,unsigned* cells,unsigned* bytes,unsigned* stale,unsigned* refused);
extern "C" void re4dc_ps2_place_own(unsigned room,unsigned placement);
extern "C" void re4dc_ps2_place_gate(unsigned room,unsigned placement,int draw_world);
extern "C" int re4dc_ps2_place_ready(unsigned room,unsigned placement);
extern "C" void re4dc_log(const char* fmt,...);
extern "C" void re4dc_ps2_place_prepare_fn(unsigned room,void (*fn)(unsigned room));
extern "C" unsigned re4dc_ui_frame();
namespace sobake {
struct Entry { unsigned short room; unsigned char kind,id; unsigned rest; unsigned short placement; };
// generated by p_bake5.py (package r101-t13, settled capture) from the bake (sob_bake.py objects json + ps2_world_append.py append.json)
const Entry kTable[]={
    {0x101,1,0x21,0x5f72f97eU,209},  // obj 0, 318 tris
    {0x101,0,0x41,0x00ed2644U,210},  // obj 1, 392 tris
    {0x101,0,0x41,0x306f21baU,211},  // obj 2, 392 tris
    {0x101,0,0x41,0x8d5d8a7fU,212},  // obj 3, 392 tris
    {0x101,0,0x41,0x1bb92949U,213},  // obj 4, 176 tris
    {0x101,0,0x43,0x9db6b9b5U,214},  // obj 5, 164 tris
    {0x101,0,0x43,0xfe795e45U,215},  // obj 6, 164 tris
    {0x101,0,0x43,0x2f9f4cf9U,216},  // obj 7, 44 tris
    {0x101,0,0x45,0xb7a5508eU,217},  // obj 8, 564 tris
    {0x101,0,0x45,0xfbe099a8U,218},  // obj 9, 460 tris
    {0x101,0,0x45,0x1518af79U,219},  // obj 10, 460 tris
    {0x101,0,0x46,0x6b8d2aa1U,220},  // obj 11, 252 tris
    {0x101,0,0x46,0xa299dde1U,221},  // obj 12, 4 tris
    {0x101,0,0x46,0x0e6ad519U,222},  // obj 13, 4 tris
};
constexpr unsigned kN=sizeof(kTable)/sizeof(kTable[0]);
struct Obj { const cModel* m; const unsigned* rest; unsigned words,live; unsigned char ready,draw,prev,seen;
#if defined(RE4DC_STATIC_OBJ_LIFETIME05) && RE4DC_STATIC_OBJ_LIFETIME05
    unsigned rest_incarnation;
#endif
};
struct State { unsigned generation,room,first,n,frames,drawn,switches,frame; Obj obj[kN]; };
State* S=nullptr;
#if defined(RE4DC_STATIC_OBJ_LIFETIME05) && RE4DC_STATIC_OBJ_LIFETIME05
re4dc::sob05::Cell<State> owner;
bool validate(){S=owner.get();return S!=nullptr;}
bool current(const re4dc::sob05::Cell<State>& held){
    const bool ok=re4dc::sob05::current(owner,held);S=owner.get();return ok;
}
bool rest_current(const Obj& o){
    return o.rest && o.words<=~0U/4 && o.rest_incarnation &&
        re4dc_room4_cell_incarnation(o.rest,o.words*4,owner.generation)==o.rest_incarnation;
}
void live_fallback(unsigned room){
    for(const auto& e:kTable)if(e.room==room)re4dc_ps2_place_gate(room,e.placement,0);
}
#endif
inline bool cls(const cModel* m){
    const unsigned k=m->kindid,id=m->id;
    return (k==0&&(id==0x41||id==0x43||id==0x45||id==0x46))||(k==1&&id==0x21);
}
unsigned words_of(const cModel* m){
    unsigned n=1;const cParts* q=(const cParts*)m->pParts;
    for(unsigned i=0;i<m->nParts && q;++i,q=q->pList)++n;
    return n*(sizeof(Mtx)/4);
}
// the model and part matrices in SOB_DUMP order, as words (fill) or compared with a rest copy (same)
void fill(const cModel* m,unsigned* w){
    memcpy(w,m->mat,sizeof(Mtx));w+=sizeof(Mtx)/4;
    const cParts* q=(const cParts*)m->pParts;
    for(unsigned i=0;i<m->nParts && q;++i,q=q->pList){memcpy(w,q->mat,sizeof(Mtx));w+=sizeof(Mtx)/4;}
}
bool same(const cModel* m,const unsigned* w){
    const unsigned* a=(const unsigned*)m->mat;
    for(unsigned k=0;k<sizeof(Mtx)/4;++k)if(a[k]!=w[k])return false;
    w+=sizeof(Mtx)/4;
    const cParts* q=(const cParts*)m->pParts;
    for(unsigned i=0;i<m->nParts && q;++i,q=q->pList){
        const unsigned* b=(const unsigned*)q->mat;
        for(unsigned k=0;k<sizeof(Mtx)/4;++k)if(b[k]!=w[k])return false;
        w+=sizeof(Mtx)/4;
    }
    return true;
}
unsigned fnv(const unsigned* w,unsigned n){
    unsigned h=2166136261U;const unsigned char* b=(const unsigned char*)w;
    for(unsigned i=0;i<n*4;++i)h=(h^b[i])*16777619U;
    return h;
}
void bind(const cModel* m){
#if defined(RE4DC_STATIC_OBJ_LIFETIME05) && RE4DC_STATIC_OBJ_LIFETIME05
    if(!validate())return;
    const auto held=owner;
#endif
    for(unsigned i=0;i<S->n;++i)if(S->obj[i].m==m)return;
    const unsigned n=words_of(m);
    unsigned* t=nullptr;unsigned hash=0;
    for(unsigned i=0;i<S->n;++i){
        const Entry& e=kTable[S->first+i];Obj& o=S->obj[i];
        if(o.m || e.kind!=m->kindid || e.id!=m->id)continue;
        if(!t){t=(unsigned*)__builtin_alloca(n*4);fill(m,t);hash=fnv(t,n);}
        if(hash!=e.rest)continue;
        unsigned* w=(unsigned*)re4dc_static_alloc(n*4);
        if(!w)return;
#if defined(RE4DC_STATIC_OBJ_LIFETIME05) && RE4DC_STATIC_OBJ_LIFETIME05
        if(!current(held)){re4dc::sob05::discard(w,n*4);return;}
        const unsigned token=re4dc_room4_cell_incarnation(w,n*4,held.generation);
        if(!token){re4dc::sob05::discard(w,n*4);return;}
        o.rest_incarnation=token;
#endif
        memcpy(w,t,n*4);
        o.m=m;o.rest=w;o.words=n;
        re4dc_log("SOBAKE bind room=%03x placement=%u id=%02x model=%08x words=%u\n",S->room,e.placement,e.id,
                  (unsigned)(size_t)m,n);
        return;
    }
}
}
namespace sobake {
// The PS2 world's prepare callback (first PS2 pass of the ui frame, during the OT execution: registration done,
// scenery not yet submitted): decide every baked object of the room and gate its placement.
void decide(unsigned room);
}
extern "C" void re4dc_sob_bake_room_leave();
// Render_before (re4dc_prepare_model_assets): room state, placements owned, the prepare callback registered.
extern "C" void re4dc_sob_bake_frame(){
    using namespace sobake;
    const unsigned room=pG->room_id;
    unsigned g,c,b,st,rf;
    if(!re4dc_room4_state(&g,&c,&b,&st,&rf)){S=nullptr;return;}
#if defined(RE4DC_STATIC_OBJ_LIFETIME05) && RE4DC_STATIC_OBJ_LIFETIME05
    validate();
#else
    if(S && S->generation!=g)S=nullptr;          // the room heap was retired with its cells
#endif
#if defined(RE4DC_STATIC_OBJ_LIFETIME05) && RE4DC_STATIC_OBJ_LIFETIME05
    if(S && S->room!=room){
        re4dc_sob_bake_room_leave();
        if(validate())return; // a free callback installed a different state
    }
#else
    if(S && S->room!=room)re4dc_sob_bake_room_leave();  // same heap, the game moved on: give the cells back
#endif
    if(!S){
        unsigned first=kN,n=0;
        for(unsigned i=0;i<kN;++i)if(kTable[i].room==room){if(first==kN)first=i;++n;}
        if(!n)return;
#if defined(RE4DC_STATIC_OBJ_LIFETIME05) && RE4DC_STATIC_OBJ_LIFETIME05
        State* fresh=(State*)re4dc_static_alloc(sizeof(State));
        if(validate()){re4dc::sob05::discard(fresh,sizeof(State));return;}
        if(!owner.bind(fresh,g)){re4dc::sob05::discard(fresh,sizeof(State));S=nullptr;return;}
        S=fresh;
#else
        S=(State*)re4dc_static_alloc(sizeof(State));
#endif
        if(!S)return;
        memset(S,0,sizeof(State));S->generation=g;S->room=room;S->first=first;S->n=n;S->frame=~0U;
        for(unsigned i=0;i<n;++i)S->obj[i].live=~0U;
    }
#if defined(RE4DC_STATIC_OBJ_LIFETIME05) && RE4DC_STATIC_OBJ_LIFETIME05
    const auto held=owner;
    for(unsigned i=0;i<S->n;++i){
        re4dc_ps2_place_own(room,kTable[S->first+i].placement);
        if(!current(held))return;
    }
#else
    for(unsigned i=0;i<S->n;++i)re4dc_ps2_place_own(room,kTable[S->first+i].placement);
#endif
    re4dc_ps2_place_prepare_fn(room,sobake::decide);
}
void sobake::decide(unsigned room){
#if defined(RE4DC_STATIC_OBJ_LIFETIME05) && RE4DC_STATIC_OBJ_LIFETIME05
    if(!validate() || S->room!=room){live_fallback(room);return;}
    const auto held=owner;
#else
    if(!S || S->room!=room)return;
#endif
    S->frame=re4dc_ui_frame();
    for(unsigned i=0;i<S->n;++i)S->obj[i].draw=S->obj[i].seen=0;
    for(unsigned table=0;table<OT_MAX;++table){
        const auto& ot=g_OtWork[table];
        if(!ot.list || !ot.max)continue;
        for(auto* node=&ot.list[ot.max-1];node;node=node->next){
            if(!node->data || node->func!=(void (*)(void*))ModelRender)continue;
            const cModel* m=(const cModel*)node->data;
            if(!cls(m) || m->invisible_factor*m->invisible_factor2==0.0f)continue;
            unsigned i=0;
            while(i<S->n && S->obj[i].m!=m)++i;
            if(i==S->n){bind(m);
#if defined(RE4DC_STATIC_OBJ_LIFETIME05) && RE4DC_STATIC_OBJ_LIFETIME05
                if(!current(held)){live_fallback(room);return;}
#endif
                i=0;while(i<S->n && S->obj[i].m!=m)++i;if(i==S->n)continue;}
            Obj& o=S->obj[i];
            const unsigned placement=kTable[S->first+i].placement;
#if defined(RE4DC_STATIC_OBJ_LIFETIME05) && RE4DC_STATIC_OBJ_LIFETIME05
            if(!o.ready){
                const bool ready=re4dc_ps2_place_ready(room,placement)!=0;
                if(!current(held)){live_fallback(room);return;}
                o.ready=ready;
            }
#else
            if(!o.ready)o.ready=re4dc_ps2_place_ready(room,placement)!=0;
#endif
            o.seen=1;
            if(o.live==S->frame)continue;  // ModelRender drew it live already this frame
            o.draw=o.ready && words_of(m)==o.words &&
#if defined(RE4DC_STATIC_OBJ_LIFETIME05) && RE4DC_STATIC_OBJ_LIFETIME05
                rest_current(o) &&
#endif
                same(m,o.rest);
        }
    }
    unsigned drawn=0;
    for(unsigned i=0;i<S->n;++i){
        const unsigned placement=kTable[S->first+i].placement;
        Obj& o=S->obj[i];
        re4dc_ps2_place_gate(room,placement,o.draw);
#if defined(RE4DC_STATIC_OBJ_LIFETIME05) && RE4DC_STATIC_OBJ_LIFETIME05
        if(!current(held)){live_fallback(room);return;}
#endif
        drawn+=o.draw;
        if(o.draw!=o.prev && o.m && S->switches<64){
            ++S->switches;
            // why live: seen 0 = no OT ModelRender entry (or invisible); else ready, words, first differing word
            unsigned k=~0U,was=0,now=0;
            if(o.seen && o.ready && words_of(o.m)==o.words
#if defined(RE4DC_STATIC_OBJ_LIFETIME05) && RE4DC_STATIC_OBJ_LIFETIME05
               && rest_current(o)
#endif
            ){
                unsigned* w=(unsigned*)__builtin_alloca(o.words*4);fill(o.m,w);
                for(k=0;k<o.words && w[k]==o.rest[k];++k){}
                if(k<o.words){was=o.rest[k];now=w[k];}
            }
            re4dc_log("SOBAKE switch room=%03x frame=%u placement=%u id=%02x draw=%u seen=%u ready=%u words=%u/%u diff=%d %08x>%08x\n",
                      room,unsigned(pG->Frame_cnt),placement,kTable[S->first+i].id,o.draw,o.seen,o.ready,
                      o.seen?words_of(o.m):0U,o.words,int(k),was,now);
#if defined(RE4DC_STATIC_OBJ_LIFETIME05) && RE4DC_STATIC_OBJ_LIFETIME05
            if(!current(held)){live_fallback(room);return;}
#endif
        }
        o.prev=o.draw;
    }
    S->drawn+=drawn;
    if(!(++S->frames%600U))re4dc_log("SOBAKE room=%03x frames=%u baked_draws=%u now=%u/%u\n",room,S->frames,S->drawn,drawn,S->n);
}
// Room leave (ui_bridge.cpp re4dc_room_leave): the rest copies and the state go back to heap 4.
extern "C" void re4dc_static_free(void* data);
extern "C" void re4dc_sob_bake_room_leave(){
    using namespace sobake;
#if defined(RE4DC_STATIC_OBJ_LIFETIME05) && RE4DC_STATIC_OBJ_LIFETIME05
    auto held=owner;State* state=held.get();
    owner.clear();S=nullptr; // detach before frees can reenter a replacement
    if(!state)return;
    for(unsigned i=0;i<state->n;++i){
        Obj& o=state->obj[i];
        const unsigned* rest=o.rest;const unsigned words=o.words,token=o.rest_incarnation;
        o.rest=nullptr;o.rest_incarnation=0;
        if(words<=~0U/4 && token && re4dc_room4_cell_incarnation(rest,words*4,held.generation)==token)
            re4dc_static_free(const_cast<unsigned*>(rest));
        if(!held.get())return;
    }
    re4dc_static_free(state);
#else
    if(!S)return;
    for(unsigned i=0;i<S->n;++i)if(S->obj[i].rest)re4dc_static_free(const_cast<unsigned*>(S->obj[i].rest));
    re4dc_static_free(S);
    S=nullptr;
#endif
}
// ModelRender (trans.cpp): 1 when this frame's decision draws the model from the world.
extern "C" int re4dc_sob_bake_skip(const void* model){
    using namespace sobake;
#if defined(RE4DC_STATIC_OBJ_LIFETIME05) && RE4DC_STATIC_OBJ_LIFETIME05
    if(!validate())return 0;
#else
    if(!S)return 0;
#endif
    const unsigned f=re4dc_ui_frame();
    for(unsigned i=0;i<S->n;++i)if(S->obj[i].m==model){
        if(S->frame==f)return S->obj[i].draw;
        S->obj[i].live=f;  // before this frame's decision: live draw, the decision gates its placement off
        return 0;
    }
    return 0;
}
#endif

#if defined(RE4DC_PROP_PLAN) && RE4DC_PROP_PLAN
extern "C" unsigned re4dc_stream_model_bytes_now();
// PROP_PLAN=1 (lane cast16 2026-10-17; render only, exact, default 0): a rigid part (vtxOrig positions) whose model's
// local bounding box lies wholly outside one clip plane (a screen edge, near or far) is not submitted: every
// triangle it holds would be clipped away, so the picture is the same. The box is computed once per ModelData
// (key: data pointer, vertex array, count, shift and 8 sampled position words) instead of preparing parts that
// emit nothing every frame (r103 farm scenery: ~111 parts a frame, 0 bytes).
namespace pplan {
struct Box { const void* d; const void* v; unsigned n, shift, sig; float lo[3], hi[3]; };
Box boxes[256];
unsigned culled, tested, built, bad;
unsigned sig_of(const short* v, unsigned n) {
    unsigned h = n * 2654435761u;
    for (unsigned k = 0; k < 8; ++k) { const unsigned i = (n * k) / 8; h = (h ^ (unsigned) (unsigned short) v[i * 4] ^ ((unsigned) (unsigned short) v[i * 4 + 2] << 16)) * 16777619u; }
    return h;
}
const Box* box_of(const ModelData* d) {
    const short* v = (const short*) d->vtxOrig; const unsigned n = d->nVtx;
    if (!v || !n) return nullptr;
    Box& b = boxes[(((unsigned) d) >> 5) & 255];
    const unsigned sig = sig_of(v, n);
    if (b.d == d && b.v == v && b.n == n && b.shift == d->shift && b.sig == sig) return &b;
    const float sc = 1.0f / (float) (1u << d->shift);
    float lo[3] = {1e30f, 1e30f, 1e30f}, hi[3] = {-1e30f, -1e30f, -1e30f};
    for (unsigned i = 0; i < n; ++i) for (unsigned c = 0; c < 3; ++c) { const float x = v[i * 4 + c] * sc; if (x < lo[c]) lo[c] = x; if (x > hi[c]) hi[c] = x; }
    b.d = d; b.v = v; b.n = n; b.shift = d->shift; b.sig = sig;
    for (unsigned c = 0; c < 3; ++c) { b.lo[c] = lo[c]; b.hi[c] = hi[c]; }
    ++built; return &b;
}
// A skinned info: the box of this frame's skinned positions (pPosBuf, stride 6), once per info per frame.
struct SBox { const void* info; const void* v; unsigned frame, n; Box b; };
SBox sboxes[64];
const Box* skinned_box_of(const void* info, const short* v, unsigned n, unsigned shift, unsigned frame) {
    if (!v || !n) return nullptr;
    SBox& e = sboxes[(((unsigned) info) >> 4) & 63];
    if (e.info == info && e.v == v && e.frame == frame && e.n == n) return &e.b;
    const float sc = 1.0f / (float) (1u << shift);
    float lo[3] = {1e30f, 1e30f, 1e30f}, hi[3] = {-1e30f, -1e30f, -1e30f};
    for (unsigned i = 0; i < n; ++i) for (unsigned c = 0; c < 3; ++c) { const float x = v[i * 3 + c] * sc; if (x < lo[c]) lo[c] = x; if (x > hi[c]) hi[c] = x; }
    e.info = info; e.v = v; e.frame = frame; e.n = n;
    for (unsigned c = 0; c < 3; ++c) { e.b.lo[c] = lo[c]; e.b.hi[c] = hi[c]; }
    return &e.b;
}
// True when the box is wholly outside one plane of the drawn volume (homogeneous half-space tests, w = -z).
bool outside(const Box& b, const float mv[3][4], const float* pr, const float* vp) {
    if (pr[0] != 0 || vp[2] <= 0 || vp[3] <= 0) return false;
    const float near = pr[6] / (pr[5] - 1), far = pr[6] / pr[5];
    if (!(near > 0) || !(far > near)) return false;
    const float xmax = 1.0f - 2.0f * vp[0] / vp[2], xmin = -1.0f - 2.0f * vp[0] / vp[2];
    const float ymax = 1.0f + 2.0f * vp[1] / vp[3], ymin = 2.0f * vp[1] / vp[3] - 1.0f;
    const float m = 1.02f;  // margin: only boxes clearly outside
    unsigned all = 0x3f;
    for (unsigned k = 0; k < 8; ++k) {
        const float x = (k & 1) ? b.hi[0] : b.lo[0], y = (k & 2) ? b.hi[1] : b.lo[1], z = (k & 4) ? b.hi[2] : b.lo[2];
        const float ex = mv[0][0] * x + mv[0][1] * y + mv[0][2] * z + mv[0][3];
        const float ey = mv[1][0] * x + mv[1][1] * y + mv[1][2] * z + mv[1][3];
        const float ez = mv[2][0] * x + mv[2][1] * y + mv[2][2] * z + mv[2][3];
        const float w = -ez, cx = pr[1] * ex + pr[2] * ez, cy = pr[3] * ey + pr[4] * ez;
        unsigned o = 0;
        if (cx > xmax * w + (m - 1) * (w < 0 ? -w : w) + 1e-3f) o |= 1;
        if (cx < xmin * w - (m - 1) * (w < 0 ? -w : w) - 1e-3f) o |= 2;
        if (cy > ymax * w + (m - 1) * (w < 0 ? -w : w) + 1e-3f) o |= 4;
        if (cy < ymin * w - (m - 1) * (w < 0 ? -w : w) - 1e-3f) o |= 8;
        if (w < near * 0.98f) o |= 16;
        if (w > far * 1.02f) o |= 32;
        all &= o;
        if (!all) return false;
    }
    return all != 0;
}
}
#endif
#if defined(RE4DC_PROP_PROF) && RE4DC_PROP_PROF
extern "C" void re4dc_pprof_add(const void* model, unsigned pth, unsigned us, unsigned b);  // native_model.cpp
extern "C" unsigned re4dc_stream_model_bytes_now();
extern "C" unsigned long long re4dc_otp_now_us();
#endif
#if defined(RE4DC_LEON_PS2_PORTRAIT_HAIR) && RE4DC_LEON_PS2_PORTRAIT_HAIR
extern "C" int re4dc_portrait_hair(const void*,const void*,const Re4dcModelPart*);
#endif
extern "C" void re4dc_draw_model_part(const void* model,const void* info_ptr,
 const void* part_ptr,const float mv[3][4],unsigned pass){
    if(!RE4DC_MODEL_DIAG() || pass)return;
#if defined(RE4DC_PROP_PROF) && RE4DC_PROP_PROF
    struct BridgeProf { const void* m; unsigned long long t0; unsigned b0;
        ~BridgeProf(){re4dc_pprof_add(m,9,unsigned(re4dc_otp_now_us()-t0),re4dc_stream_model_bytes_now()-b0);} }
      bridge_prof{model,re4dc_otp_now_us(),re4dc_stream_model_bytes_now()};
#endif
#if defined(RE4DC_GCOBJ_SKIP) && (RE4DC_GCOBJ_SKIP == 3 || RE4DC_GCOBJ_SKIP == 4)
    if(re4dc_gcobj_class(((const cModel*)model)->kindid,((const cModel*)model)->id,RE4DC_GCOBJ_SKIP==4))return;
#endif
#if RE4DC_NATIVE_ACTOR
    bind_actor_frame();
#endif
    auto* m=(const cModel*)model;auto* info=(const cModelInfo*)info_ptr;
    auto* part=(const ModelPart*)part_ptr;const auto* d=info->pData;
#if defined(RE4DC_GC_STUB_SKIP) && RE4DC_GC_STUB_SKIP
    // GC_STUB_SKIP (crowd.mk): fewer than 3 positions draws nothing on any path (every path declines or emits
    // degenerate triangles); skip the per-part record, actor attempt and builder.
    if(d->nVtx<3)return;
#endif
    Re4dcModelPart p{};p.model=m;p.info=info;p.part=part;
    const bool rigid=(m->be_flag&0x4000) ||
      (d->weight_palette_num<=1 && d->weight_ext_num<=0xff && !(info->be_flag&2) && d->nParts==1);
#if RE4DC_LEON_FACE_LAZY
    if(!rigid)re4dc_face_lazy_resolve(info);  // LEON_FACE_LAZY (trans.cpp): a deferred face info's arrays first
#endif
    p.positions=(const unsigned char*)(rigid?d->vtxOrig:info->pPosBuf[pG->vtx_buf_no]);
    p.normals=(const unsigned char*)(rigid?d->nrmOrig:info->pNrmBuf[pG->vtx_buf_no]);
    p.position_stride=rigid?8:6;p.position_count=d->nVtx;p.normal_count=d->nNrm;
    p.uv=(const unsigned char*)d->pTex;p.stream=(const unsigned char*)part+32;p.stream_bytes=part->size;
    p.shift=d->shift;p.flags=d->flags;p.material_flags=part->flags;
    p.cull=re4dc_model_cull(m->CullMode,(pG->Debug_flg[0]&0x20000000)!=0);
    p.blend=info->blend_mode;p.depth_mode=m->z_mode;
    memcpy(p.modelview,mv,sizeof(p.modelview));RE4DC_GXF_GET_PROJECTION(p.projection);RE4DC_GXF_GET_VIEWPORT(p.viewport);
#if RE4DC_NATIVE_FOG
    // Fog as the source set it for this draw (effects/filters/thermal turn it
    // off temporarily) rides in the spare source_key[2] byte, so the part
    // layout (and the deferral queue's word diffs) is unchanged; the
    // fog-derived View far plane (light.cpp setFog) is global frame state.
    p.source_key[2]=(unsigned char)re4dc_fog_enabled();re4dc_fog_note_far(View._zfar);
#endif
    p.colors=(const unsigned char*)d->pClr;p.alpha_state=re4dc_gx_model_alpha();
    p.image=selected;p.uv_offset[0]=scroll_u;p.uv_offset[1]=scroll_v;p.wrap_s=wrap_s;p.wrap_t=wrap_t;
#if RE4DC_D349_RENDERER_STACK
    p.mask=mask;p.mask_ref=mask_ref;p.mask_same_uv=mask_same_uv;
#if RE4DC_BRIDGE_LEAN
    // Borrow the live GX state for this synchronous submit (no 0.5 KiB zero +
    // copy per part); nothing changes it before re4dc_model_submit returns and
    // the translucent queue still snapshots its own copy.
    p.lighting=re4dc_gx_model_lighting_ref();
#else
    re4dc::render::SourceLighting lighting;
    re4dc_gx_model_lighting(&lighting);p.lighting=&lighting;
#endif
    const bool nrm8=(d->flags&0x20000000U)!=0;
    p.static_geometry=rigid && m->kindid==2 && !d->shapeOfs && !(info->be_flag&2);
    p.normal_stride=nrm8?(rigid?4:3):(rigid?8:6);p.normal_shift=nrm8?6:14;
#endif
#if RE4DC_NATIVE_STATIC && !RE4DC_NATIVE_MESH
    // Single-node static scroll objects only: a multi-node part's own matrix is
    // not represented by the object-level placement the package was baked at.
    // Every other part keeps these words at their defaults, because translucent
    // parts are queued as word differences in a bounded deferral queue (D367).
    if(p.static_geometry && m->nParts<=1){
        p.serial=m->serial;p.world=&m->mat[0][0];p.view=&pG->Cam.v_mat[0][0];
        p.source_key[0]=part->texId;p.source_key[1]=(part->flags&4)?part->alphaTex:0xff;
    }
#endif
#if defined(RE4DC_STATIC_OBJ_BATCH33) && RE4DC_STATIC_OBJ_BATCH33
    // The existing deferred view stores all four source-key bytes. Only final
    // identical TA headers may be joined; each part keeps its own source draw.
    if(re4dc::sob33::eligible_class(m->kindid,m->id))
        p.source_key[3]=re4dc::sob33::marker(d->displist_num,p.blend);
#endif
#if defined(RE4DC_LEON_PS2_PORTRAIT_HAIR) && RE4DC_LEON_PS2_PORTRAIT_HAIR
    if(re4dc_portrait_hair(m,info,&p))return;  // coarse_actor.cpp: the PS2 hair for the portrait GameCube hair info
#endif
#if RE4DC_FRONT_NATIVE>=2
    if(front_verify_part(&p))return;  // native replay: compared, not drawn
#endif
#if RE4DC_ACTOR_TRANSACTION_DIAG
    re4dc_actor_vis_source(m,info,&p);
#endif
#if defined(RE4DC_SOB_DIAG) && RE4DC_SOB_DIAG
    {   // SOB_DIAG (crowd.mk, diagnostic): the static object classes' part records
        const unsigned k=m->kindid,id=m->id;
        const bool st=(k==0&&(id==0x41||id==0x43||id==0x45||id==0x46))||(k==1&&(id==0x00||id==0x21));
        if(st && pG->Frame_cnt%600==300)
            re4dc_log("SOB %u %x %x %x %x %x %x %u %u %u %u %x %u %u %x %u\n",pG->Frame_cnt%100000,(unsigned)m&0xffffff,id|(k<<8),(unsigned)info&0xffffff,(unsigned)part&0xffffff,(unsigned)p.image.pixels&0xffffff,(unsigned)p.uv&0xffffff,p.position_count,p.position_stride,p.normal_stride,p.shift,p.flags>>16,p.blend,p.alpha_state,(unsigned)p.colors&0xffffff,p.stream_bytes);
    }
#endif
#if defined(RE4DC_PROP_PLAN) && RE4DC_PROP_PLAN
    {static unsigned seen;if(m->id==2 && m->kindid==1 && seen<6){++seen;re4dc_log("PPLAN id2 rigid=%u be4000=%u wp=%u wext=%u ib2=%u np=%u nvtx=%u shift=%u\n",(unsigned)rigid,(unsigned)((m->be_flag&0x4000)!=0),(unsigned)d->weight_palette_num,(unsigned)d->weight_ext_num,(unsigned)((info->be_flag&2)!=0),(unsigned)d->nParts,(unsigned)d->nVtx,(unsigned)d->shift);}
     static unsigned pf;if(pG->Frame_cnt/600!=pf){pf=pG->Frame_cnt/600;re4dc_log("PPLAN tested=%u culled=%u built=%u bad=%u\n",pplan::tested,pplan::culled,pplan::built,pplan::bad);}}
    {++pplan::tested;const auto* bx=rigid?pplan::box_of(d):
        pplan::skinned_box_of(info,(const short*)p.positions,d->nVtx,d->shift,pG->Frame_cnt);
#if RE4DC_PROP_PLAN==2
        if(bx && pplan::outside(*bx,mv,p.projection,p.viewport)){++pplan::culled;const unsigned b0=re4dc_stream_model_bytes_now();
            re4dc_model_submit(&p);const unsigned db=re4dc_stream_model_bytes_now()-b0;
            if(db>=96){++pplan::bad;if(pplan::bad<8)re4dc_log("PPLAN BAD kind=%u id=%x rigid=%u bytes=%u\n",(unsigned)m->kindid,(unsigned)m->id,(unsigned)rigid,db);}return;}}
#else
        if(bx && pplan::outside(*bx,mv,p.projection,p.viewport)){++pplan::culled;return;}}
#endif
#endif
#if defined(RE4DC_SOB_DUMP) && RE4DC_SOB_DUMP
    sobdump::part(m,info,d,part,p);  // SOB_DUMP (diagnostic): first-draw capture for STATIC_OBJ_BAKE
#endif
#if defined(RE4DC_STATIC_OBJ_BATCH) && RE4DC_STATIC_OBJ_BATCH
    if(sob::take(m,info,d,part,p))return;  // STATIC_OBJ_BATCH: held for its info's run
#endif
    re4dc_model_submit(&p);
#if RE4DC_ACTOR_TRANSACTION_DIAG
    re4dc_actor_vis_source_end();
#endif
#if RE4DC_FRONT_NATIVE>=2
    front_cur=~0U;  // group 8: headers built later (deferred drain) are not this part's
#endif
}

#if defined(RE4DC_BACKFACE_CENSUS) && RE4DC_BACKFACE_CENSUS
// Deferred/source actor submissions no longer have the transaction's class
// scope. Read the same synchronous model identity the bridge already uses;
// do not walk actors or infer cModel offsets in the platform emitter.
extern "C" unsigned re4dc_backface_model_tag(const void* model) {
    const auto* m=static_cast<const cModel*>(model);
    if(!m || m->kindid!=0)return 0;
    const unsigned id=unsigned(m->id);
    return ((id==0?3u:(id>=0x10 && id<=0x20)?4u:5u)<<8)|id;
}
#endif
#if RE4DC_ACTOR_CENSUS
// ACTOR_CENSUS (diagnostic): id | ot_type << 8 | nParts << 16 of a submitted part's model.
extern "C" unsigned re4dc_actor_census_key(const void* model) {
    const cModel* m = static_cast<const cModel*>(model);
    return m ? (unsigned(m->id) & 0xffU) | ((unsigned(m->ot_type) & 0xffU) << 8) | ((unsigned(m->nParts) & 0xffffU) << 16) : ~0U;
}
extern "C" unsigned re4dc_actor_census_vptr(const void* model) {
    return model ? *static_cast<const unsigned*>(model) : 0U;  // first word: the vtable pointer (modern GCC layout)
}
extern "C" void re4dc_actor_census_describe(const void* model, unsigned verts) {
    // First sighting of each cObj00-shaped model: kind / type / scroll block / world position.
    static const void* seen[64]; static unsigned nseen;
    for (unsigned i = 0; i < nseen; ++i) if (seen[i] == model) return;
    if (nseen < 64) seen[nseen++] = model; else return;
    const cModel* m = static_cast<const cModel*>(model);
    const float* w = m->pParts ? &m->pParts->mat[0][0] : nullptr;
    re4dc_log("ACENSUS_OBJ m=%p kind=%u type=%u ot=%u blk=%d verts=%u pos=%d,%d,%d\n", model, unsigned(m->kindid),
              unsigned(m->type), unsigned(m->ot_type), reinterpret_cast<const int*>(model)[0x324 / 4], verts,
              w ? int(w[3]) : 0, w ? int(w[7]) : 0, w ? int(w[11]) : 0);
}
#endif
#if defined(RE4DC_GC_ASSET_GATE) && RE4DC_GC_ASSET_GATE
// Use the source declarations here; platform diagnostics never duplicate the
// cModel/cModelInfo layout. The data pointer remains subject to member bounds
// and owner-generation validation in gc_asset_members before any byte read.
extern "C" unsigned re4dc_gcasset_model_identity(const void* model,const void* info,const void** data) {
    if(data)*data=nullptr;
    if(!model || !info || !data)return 0xffffffffU;
    const auto* m=static_cast<const cModel*>(model);
    *data=static_cast<const cModelInfo*>(info)->pData;
    return (unsigned(m->kindid)&255U)<<24 | (unsigned(m->id)&255U)<<16 | (unsigned(m->type)&255U)<<8 |
        (unsigned(m->nParts)&255U);
}
// Class/role selects a diagnostic consumer only; member SHA determines origin.
extern "C" unsigned re4dc_gcasset_weapon_consumer(const void* model,const void* info,unsigned arc,unsigned family) {
    if(!model || !info)return 0;
    const auto* m=static_cast<const cModel*>(model);
    if(family==re4dc_gcasset::WeaponOwner)return 1;
    if(m->kindid==1)switch(m->id) {
        case 0x21:case 0x23:case 0x24:case 0x25:case 0x27:case 0x28:case 0x2b:case 0x2c:
        case 0x2d:case 0x2e:case 0x2f:case 0x30:case 0x31:case 0x32:case 0x33:case 0x34:
        case 0x36:case 0x3c:case 0x3d:case 0x1a:case 0x22:case 0x29:case 0x2a:case 0x3a:return 1;
    }
    if(family==re4dc_gcasset::PlayerOwner &&
       ((m->kindid==1 && m->id==0x0a && arc==0x7a) || (m->kindid==0 && m->id==0x4f && arc==0x72)))return 1;
    return pPL && model==pPL && pPL->Body && (info==pPL->Body->pRight || info==pPL->Body->pLeft);
}
#endif
#if defined(RE4DC_MODEL_DROP_LOG) && RE4DC_MODEL_DROP_LOG
// MODEL_DROP_LOG (native_ui.cpp): a refused part's model as kind<<24 | id<<16 | type<<8 | nParts (low byte), or
// 0xffffffff when the part has no model pointer in main RAM.
extern "C" unsigned re4dc_model_drop_describe(const void* model) {
    const unsigned a = (unsigned) model & 0x1fffffffU;
    if (!model || ((unsigned) model & 3U) || a < 0x0c000000U || a >= 0x0d000000U) return 0xffffffffU;
    const cModel* m = static_cast<const cModel*>(model);
    return (unsigned(m->kindid) & 0xffU) << 24 | (unsigned(m->id) & 0xffU) << 16 | (unsigned(m->type) & 0xffU) << 8 |
           (unsigned(m->nParts) & 0xffU);
}
#endif
#if defined(RE4DC_ACC_CROWD_TIER) && RE4DC_ACC_CROWD_TIER
// ACC_CROWD_TIER (crowd.mk): a hanging accessory object (cObj12, kind 1 id 0x12, em10SetAccesory) attached to a Ganado
// (kind 0, id 0x10..0x20): that Ganado's model, else null. The parent link is Obj12Work::oya (cObj work + 0x10).
#include "obj.h"
extern "C" const void* re4dc_actor_accessory_parent(const void* model) {
    const cModel* m = static_cast<const cModel*>(model);
    if (!m || m->kindid != 1 || m->id != 0x12) return nullptr;
    const cModel* oya = static_cast<const cObj*>(m)->o12.oya;
    return oya && oya->kindid == 0 && oya->id >= 0x10 && oya->id <= 0x20 ? oya : nullptr;
}
#endif
#if defined(RE4DC_CALLPROF) && RE4DC_CALLPROF
// CALLPROF (game30.mk): an actor part's model as kindid << 8 | id for platform/callprof.cpp.
extern "C" void re4dc_callprof_part_key(unsigned path,unsigned key);
extern "C" void re4dc_callprof_part(const void* model,unsigned path){
    const cModel* m=static_cast<const cModel*>(model);
    re4dc_callprof_part_key(path,m?(unsigned(m->kindid)<<8|unsigned(m->id)):0xffffU);
}
#endif
#if defined(RE4DC_DSA_XLU28) && RE4DC_DSA_XLU28
// DRAW_SETUP_AUDIT_XLU (draw_setup_audit.mk): a model's kind/id/type key for the XM rows; 0xffffff when the pointer is
// not a cModel in main RAM (borrowed views, static packages).
extern "C" unsigned re4dc_dsa28_model_key(const void* model) {
    const unsigned a = (unsigned) model & 0x1fffffffU;
    if (!model || ((unsigned) model & 3U) || a < 0x0c000000U || a >= 0x0d000000U) return 0xffffffU;
    const cModel* m = static_cast<const cModel*>(model);
    return (unsigned(m->kindid) & 255u) << 16 | (unsigned(m->id) & 255u) << 8 | (unsigned(m->type) & 255u);
}
#endif
#if defined(RE4DC_PROP_PROF) && RE4DC_PROP_PROF
extern "C" unsigned re4dc_propprof_key(const void* model) {
    const cModel* m = static_cast<const cModel*>(model);
    return m ? (unsigned(m->kindid) & 255u) << 16 | (unsigned(m->id) & 255u) << 8 | (unsigned(m->type) & 255u) : 0xffffffu;
}
#endif
