#include "actor_visibility_diag.h"
// Recovered commonModelTrans -> existing native frame/packet/texture owner.
// Diagnostic base-material connection; not full GX lighting/TEV emulation.
#include "light.h"
#include "global.h"
#include "model.h"
#include "gx.h"
#include "native_model.h"
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
#endif
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
inline bool static_class(const cModel* m){
    const unsigned k=m->kindid,id=m->id;
    return (k==0&&(id==0x41||id==0x43||id==0x45||id==0x46))||(k==1&&id==0x21);
}
// build_lights folds point lights at the blob centre: only these groups' lighting depends on where the centre is.
inline bool centre_lit(const re4dc::render::SourceLighting& L){
    return L.enable && !L.ambient_vertex && !L.material_vertex && L.diffuse==2 && L.mask;
}
// Records equal but for the stream, its size, the part header and the lighting address; lighting content equal.
inline bool same(const Re4dcModelPart& a,const Re4dcModelPart& b){
    Re4dcModelPart t=b;t.stream=a.stream;t.stream_bytes=a.stream_bytes;t.part=a.part;t.lighting=a.lighting;
    return !memcmp(&a,&t,sizeof t) && !memcmp(a.lighting,b.lighting,sizeof(re4dc::render::SourceLighting));
}
inline const unsigned char* list_of(const ModelPart* q){return (const unsigned char*)q+0x20;}
void new_frame(){
    seen_frame=pG->Frame_cnt;
    unsigned cells,bytes,stale,refused;
    live=re4dc_room4_state(&generation,&cells,&bytes,&stale,&refused)!=0;
    if(S && (!live || S->generation!=generation))S=nullptr;  // a heap-4 reset without a room leave: the cells are gone
    if(seen_frame-st.log>=600U){
        st.log=seen_frame;
        re4dc_log("SOBATCH frame=%u groups=%u lists=%u merged=%u saved=%u built=%u refused=%u singles=%u lit=%u entries=%u bytes=%u\n",
            seen_frame,st.groups,st.lists,st.merged,st.saved,st.built,st.refused,st.singles,st.lit,
            S?S->count:0U,S?S->bytes:0U);
    }
}
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
void flush(){
    Pending& q=S->pend;
    if(!q.on)return;
    q.on=false;
    ++st.groups;st.lists+=q.n;
    Re4dcModelPart r=q.rec;
    if(q.n>1){
        Entry* e=find(q);
        if(!e)e=build(q);
        if(e){
            r.stream=e->buf;r.stream_bytes=e->bytes;r.part=q.parts[0];
            ++st.merged;st.saved+=q.n-1;
            re4dc_model_submit(&r);
            return;
        }
        ++st.refused;
    } else ++st.singles;
    for(unsigned i=0;i<q.n;++i){
        r.part=q.parts[i];r.stream=list_of(q.parts[i]);r.stream_bytes=q.parts[i]->size;
        re4dc_model_submit(&r);
    }
}
// 1: the part was taken (held, or submitted with its run); 0: the caller submits it.
bool take(const cModel* m,const cModelInfo* info,const ModelData* d,const ModelPart* part,const Re4dcModelPart& p){
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
        S=(State*)re4dc_static_alloc(sizeof(State));
        if(S){memset(S,0,sizeof(State));S->generation=generation;}
        else eligible=false;
    }
    if(S && S->pend.on){
        const Pending& q=S->pend;
        if(!eligible || q.info!=info || q.model!=m || !same(q.rec,p))flush();
    }
    if(!eligible){if(idx>=d->displist_num)cur_info=nullptr;return false;}
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
    if(!sob::S)return;
    for(unsigned k=0;k<sob::S->count;++k)re4dc_static_free(sob::S->e[k].buf);
    re4dc_static_free(sob::S);
    sob::S=nullptr;sob::cur_model=nullptr;sob::cur_info=nullptr;
}
#endif
extern "C" void re4dc_draw_model_part(const void* model,const void* info_ptr,
 const void* part_ptr,const float mv[3][4],unsigned pass){
    if(!re4dc_model_diagnostic_enabled() || pass)return;
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
    memcpy(p.modelview,mv,sizeof(p.modelview));GXGetProjectionv(p.projection);GXGetViewportv(p.viewport);
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
