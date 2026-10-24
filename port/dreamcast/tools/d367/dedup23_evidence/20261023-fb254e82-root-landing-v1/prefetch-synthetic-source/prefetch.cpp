#define RE4DC_SCENERY_DEDUP 3
// Production source bodies are substituted by check_runtime.py. External
// renderer edges below are controlled, instrumented fixtures, not replacements
// intended for the game or for performance pricing.
#include <algorithm>
#include <array>
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>

#define RE4DC_TA_DIRECT 1
#define RE4DC_TA_MATERIAL_DIAG 0
#define RE4DC_PS2_WORLD_TRANSITION_OWNER 1
#define RE4DC_PS2_WORLD_R11F_OWNER 1
#define RE4DC_WORLD_HOLE_DIAG 1
#define RE4DC_UI_POLY_ORDER 1
#define RE4DC_SS_UI_ORDER 1
#define RE4DC_WORLD_RECT21 1
#define RE4DC_PS2_WORLD_PREFLIGHT_DIAG CHECK_DIAGNOSTICS
#define RE4DC_PS2_WORLD_HDR_CACHE 1
#define RE4DC_PS2_HDR_ON true
#define RE4DC_NATIVE_FOG 1
#define RE4DC_PS2_WORLD_FOG_SOURCE 1
#define RE4DC_SCENERY_PIECE_STATE 1
#define RE4DC_WORLD_AUTOSORT 1
#define RE4DC_PS2_INTERIOR_CULL 2
#define RE4DC_SKY_FAR 2
#define RE4DC_MV_SHADOWS 1
#define RE4DC_TA_HASH 1
#define RE4DC_PS2_WORLD_SOURCE_TEX_PREP 1
#define RE4DC_PT_BLEND_FIX 1
#define RE4DC_TA_GUARD 0
#define RE4DC_D349_RENDERER_STACK 1
#define RE4DC_PVR_STREAM 1

using pvr_list_t = unsigned;
using pvr_ptr_t = void*;
using pvr_cull_mode_t = unsigned;
constexpr unsigned PVR_LIST_OP_POLY=0, PVR_LIST_PT_POLY=4, PVR_LIST_TR_POLY=2;
constexpr unsigned PVR_CULLING_NONE=0,PVR_CULLING_CCW=1,PVR_CULLING_CW=2;
constexpr unsigned PVR_FILTER_BILINEAR=1,PVR_DEPTHCMP_GEQUAL=6,PVR_DEPTHWRITE_DISABLE=0,PVR_DEPTHWRITE_ENABLE=1;
constexpr unsigned PVR_BLEND_SRCALPHA=4,PVR_BLEND_ONE=1,PVR_BLEND_INVSRCALPHA=5,PVR_BLEND_ZERO=0;
constexpr unsigned PVR_TXRENV_MODULATEALPHA=3,PVR_TXRALPHA_ENABLE=1,PVR_TXRALPHA_DISABLE=0,PVR_UVCLAMP_NONE=0;
constexpr unsigned PVR_FOG_TABLE=0,PVR_FOG_DISABLE=2,PVR_TA_CMD_MODIFIER=0x80;
constexpr uintptr_t PVR_TA_INPUT=0x10000000;
struct Key { unsigned crc,fnv; bool operator==(const Key& b)const{return crc==b.crc&&fnv==b.fnv;} };
struct Texture { unsigned width=64,height=64,format=0,flags=0,payload=0,data_size=4096; };
struct PackageHeader { unsigned payload_crc32=0,texture_count=1; };
struct Package {
    Texture texture;PackageHeader h;unsigned address=1;
    const Texture* textures()const{return &texture;}
    const PackageHeader& header()const{return h;}
    pvr_ptr_t pvr_texture(unsigned)const{return reinterpret_cast<void*>(uintptr_t(address));}
    bool upload_complete()const{return true;}
};
struct Entry { bool valid=false;Key key{};unsigned frame=0;Package package; };
struct pvr_poly_hdr_t { unsigned cmd,words[7]; };
struct pvr_poly_cxt_t {
    struct {unsigned culling=0,fog_type=0;} gen;
    struct {unsigned comparison=0,write=0;} depth;
    struct {unsigned src=0,dst=0;} blend;
    struct {unsigned env=0,alpha=0,uv_clamp=0;} txr;
    unsigned list=0,format=0,width=0,height=0,address=0;
};
struct Packet {
    std::uint32_t flags;float x,y,z,u,v;std::uint32_t argb,oargb;
};
using pvr_vertex_t=Packet;
constexpr std::uint32_t PVR_CMD_VERTEX=0xe0000000U,PVR_CMD_VERTEX_EOL=0xf0000000U;
float vp_host_xmtrx[4][4];
static unsigned geometry_low_at;

struct Re4dcModelDirect { std::uint32_t* sq;void* scratch;unsigned scratch_capacity;float u_scale,v_scale; };
struct Re4dcUiImage { const void* data;const void* palette;unsigned width,height,format,flags,unused; };
constexpr unsigned kModelPacketBytes=65536,kPs2HdrSets=16,kPs2HdrWays=4;
struct Ps2HdrSlot { unsigned crc,fnv,size,mode;Entry* entry;pvr_ptr_t texture;std::uint32_t words[4]; };
static Entry entries[12];
static Ps2HdrSlot ps2_hdr[kPs2HdrSets][kPs2HdrWays];
static unsigned char ps2_hdr_next[kPs2HdrSets];
static unsigned ps2_hdr_hits,ps2_hdr_fills,ps2_hdr_log,ps2_piece_hits;
static Packet storage[kModelPacketBytes/32];
static Packet* model_packets=storage;
static unsigned model_used,model_pending,frame=100,frame_pvr_calls,frame_pvr_bytes,stream_model_bytes,stream_peak_bytes;
static unsigned direct_parts,direct_slots,model_header_hits,model_header_builds,model_texture_rejects;
static unsigned stream_closed_lists,quads_flushed,nquad,mv_receivers;
static unsigned re4dc_ps2_check_header,re4dc_ps2_sky_header,re4dc_mv_receiver;
static unsigned* re4dc_ps2_piece_slot;
static unsigned piece_words[12];
static Entry* model_handle;
static bool direct_open,frame_ready=true,stream_aborted,stream_scene=true,ui_order,world_autosort=true;
static bool draining_parts,source_draws_finished;
static unsigned desired_list,stream_list;
static unsigned whd_why;
static const char* whd_load_why;
static bool source_valid=true,r11f_valid=true,storage_ok=true,load_ok=true,rect_ok=true,header_dims_ok=true,fog=true;
static bool source_group_claimed;
static unsigned acquire_invalid_at,acquire_invalid_kind;
static unsigned source_failures,r11f_failures,loads,logs,missing,acquired,diagbind,hash_calls,ui_flushes;
static unsigned owner_cut_stage,owner_stage,abort_on_select;
static unsigned lock_calls,unlock_calls,unsafe_calls;
static bool locked;
alignas(32) static std::uint32_t sq_storage[1024*1024];
static std::vector<std::uint32_t> sent;
static std::vector<unsigned> returns,capacities,u_bits,v_bits;

static bool re4dc_source_world_group_claimed(){return source_group_claimed;}
static bool re4dc_source_world_binding_valid(){
    // A claimed walk may diagnose failure inside the predicate. The old
    // renderer already calls this during an active part; the new idle retained
    // lock must be released before entering this potentially logging edge.
    if(source_group_claimed){if(locked&&!direct_open)++unsafe_calls;if(!source_valid)++logs;}
    return source_valid;
}
static void re4dc_source_world_binding_failed(){if(locked)++unsafe_calls;++source_failures;}
static bool re4dc_r11f_binding_valid(){return r11f_valid;}
static void re4dc_r11f_binding_failed(){if(locked)++unsafe_calls;++r11f_failures;}
static void boundary(){if(owner_cut_stage&&++owner_stage==owner_cut_stage)source_valid=false;}
static bool ensure_model_storage(){if(!model_packets){if(locked)++unsafe_calls;if(storage_ok)model_packets=storage;}return model_packets!=nullptr;}
static void re4dc_missing(const char*){++missing;}
static void re4dc_log(const char*,...){if(locked)++unsafe_calls;++logs;}
static void sourceWorldDiagBind(Key){if(locked)++unsafe_calls;++diagbind;}
static void sourceWorldTextureAcquired(Key){
std::fill(&vp_host_xmtrx[0][0],&vp_host_xmtrx[0][0]+16,-9999.0f);
++acquired;
if(geometry_low_at&&acquired==geometry_low_at)model_pending=kModelPacketBytes/32-300;
if(acquire_invalid_at&&acquired==acquire_invalid_at){if(acquire_invalid_kind==1)source_valid=false;else r11f_valid=false;}}
static bool re4dc_ps2_world_fog(){return fog;}
static void ui_order_flush(){if(locked)++unsafe_calls;++ui_flushes;quads_flushed=nquad;boundary();}
static void stream_open(){if(locked)++unsafe_calls;stream_scene=true;stream_list=desired_list;boundary();}
static void stream_select(pvr_list_t list){
    desired_list=list;
    if(!stream_scene)stream_open();
    else if(stream_list!=list){if(locked)++unsafe_calls;stream_closed_lists|=1U<<stream_list;stream_list=list;boundary();}
    if(abort_on_select)stream_aborted=true;
}
static void world_sort_begin(){if(!world_autosort&&!ui_order){if(locked)++unsafe_calls;world_autosort=true;}}
static void ui_order_polygon_header(pvr_poly_hdr_t& h){if(ui_order)h.cmd=(h.cmd&~(7U<<24))|(PVR_LIST_TR_POLY<<24);}
static void ps2_check_header(pvr_poly_hdr_t& h){h.words[0]^=0x1000U;h.words[1]^=0x80000000U;}
static void ps2_sky_header(pvr_poly_hdr_t& h){h.words[1]^=0x00400000U;}
static std::uint32_t* sq_lock(void*){assert(!locked);locked=true;++lock_calls;return sq_storage;}
static void sq_unlock(){assert(locked);locked=false;++unlock_calls;}
static void sq_flush(std::uint32_t* p){assert(locked);assert(p>=sq_storage&&p+8<=sq_storage+1024*1024);sent.insert(sent.end(),p,p+8);}
static void re4dc_ta_hash(const void*,unsigned){++hash_calls;}
#define RE4DC_WHD(x) (whd_why=(x))
#define RE4DC_GAD_HIT(x) do{}while(0)
#define RE4DC_TOUCH(e) do{if(pin)(e).frame=frame;else if(frame&&(e).frame+1<frame)(e).frame=frame-1;}while(0)
#define RE4DC_TSP_W(t) ((t).width)
#define RE4DC_TSP_H(t) ((t).height)
namespace re4dc::texture { static unsigned pvr_format(const Texture& t){return t.format;} }
namespace re4dc::render {
static void begin_pvr_packet(Packet* p,std::uint32_t& n,const pvr_poly_hdr_t& h){std::memcpy(p,&h,32);n=1;}
}
namespace re4dc::rect21 {
struct Descriptor { unsigned width,height,format,flags,payload,data_size,crc; };
static bool header_dimensions(unsigned,unsigned,unsigned){return header_dims_ok;}
static bool adapt(unsigned,unsigned,unsigned w,unsigned h,Descriptor d,float& u,float& v,bool){
    if(!rect_ok)return false;
    u=float(d.width)/float(w);v=float(d.height)/float(h);return true;
}
}
static Entry* load(const Re4dcUiImage&,bool,const Key* key){
    if(locked)++unsafe_calls;
    ++loads;boundary();
    if(!load_ok)return nullptr;
    for(auto& e:entries)if(e.valid&&e.key==*key){constexpr bool pin=false;RE4DC_TOUCH(e);return &e;}
    return nullptr;
}
static void pvr_poly_cxt_txr(pvr_poly_cxt_t* c,unsigned list,unsigned fmt,unsigned w,unsigned h,void* addr,unsigned){
    *c={};c->list=list;c->format=fmt;c->width=w;c->height=h;c->address=unsigned(uintptr_t(addr));
}
static void pvr_poly_compile(pvr_poly_hdr_t* h,const pvr_poly_cxt_t* c){
    h->cmd=0x80840000U|(c->list<<24);
    h->words[0]=(c->gen.culling<<24)|(c->depth.comparison<<16)|(c->depth.write<<8)|c->txr.alpha;
    h->words[1]=(c->gen.fog_type<<28)|(c->blend.src<<24)|(c->blend.dst<<20)|(c->width<<8)|c->height;
    h->words[2]=c->address;
    std::fill(h->words+3,h->words+7,0U);
}

#pragma once
#include <cstdint>

struct Re4dcModelDirect;

// Borrowed only by one synchronous scenery chunk replay. Each logical part
// still ends normally; sq retains only the original SQ lock's base address.
// Reusing that base preserves the ordinary per-part address/window limit.
struct Re4dcWorldSubmitBatch { std::uint32_t* sq=nullptr; };

extern "C" int re4dc_ps2_world_direct_begin_batch(const unsigned*,Re4dcModelDirect*,Re4dcWorldSubmitBatch*);
extern "C" void re4dc_ps2_world_direct_end_batch(unsigned,Re4dcWorldSubmitBatch*);
// Close only between logical parts. A live direct part must end first.
extern "C" void re4dc_ps2_world_batch_close(Re4dcWorldSubmitBatch*);

#if RE4DC_SCENERY_SUBMIT_BATCH
// The same logical end for ordinary and batched world parts. Only the caller
// decides whether to release the physical SQ mutex before this accounting.
static void model_direct_account(unsigned vertices){
#else
extern "C" void re4dc_model_direct_end(unsigned vertices){
#endif
#if RE4DC_TA_DIRECT
#if !RE4DC_SCENERY_SUBMIT_BATCH
    if(!direct_open)return;
    sq_unlock();direct_open=false;
#endif
    if(vertices>32767)re4dc_missing("native direct part exceeded the store-queue window");
    ++direct_parts;direct_slots+=vertices;
#if RE4DC_TA_GUARD
    guard_account(1,vertices);
#endif
    frame_pvr_bytes+=vertices*32;stream_model_bytes+=vertices*32;
    if(stream_model_bytes>stream_peak_bytes)stream_peak_bytes=stream_model_bytes;
    model_used=0;
#else
    (void)vertices;
#endif
}
#if RE4DC_SCENERY_SUBMIT_BATCH
extern "C" void re4dc_model_direct_end(unsigned vertices){
    if(!direct_open)return;
    sq_unlock();direct_open=false;
    model_direct_account(vertices);
}
extern "C" void re4dc_ps2_world_batch_close(Re4dcWorldSubmitBatch* batch){
    // A nested-begin refusal does not revoke the current part's ownership.
    if(batch && batch->sq && !direct_open){sq_unlock();batch->sq=nullptr;}
}
extern "C" void re4dc_ps2_world_direct_end_batch(unsigned vertices,Re4dcWorldSubmitBatch* batch){
    if(!batch || !batch->sq){re4dc_model_direct_end(vertices);return;}
    if(!direct_open)return;
    direct_open=false;
    // The original end reports overflow after unlocking. Keep that boundary.
    if(vertices>32767U)re4dc_ps2_world_batch_close(batch);
    model_direct_account(vertices);
}
#endif

#if RE4DC_SCENERY_SUBMIT_BATCH
// One implementation for the ordinary and batched entry points: the cache,
// material gates, header modifiers and accounting below remain shared.
extern "C" __attribute__((noinline,noclone)) int re4dc_ps2_world_direct_begin_batch(const unsigned* k,Re4dcModelDirect* out,Re4dcWorldSubmitBatch* batch){
    struct FailedBegin {
        Re4dcWorldSubmitBatch* batch;bool accepted=false;
        ~FailedBegin(){if(!accepted)re4dc_ps2_world_batch_close(batch);}
    } failed_begin{batch};
#else
extern "C" int re4dc_ps2_world_direct_begin(const unsigned* k,Re4dcModelDirect* out){
#endif
#if RE4DC_TA_MATERIAL_DIAG
#if RE4DC_SCENERY_SUBMIT_BATCH
    re4dc_ps2_world_batch_close(batch);
#endif
    tamat::Scope source_scope(1);
#endif
#if RE4DC_TA_DIRECT
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
#if RE4DC_SCENERY_SUBMIT_BATCH
    // A claimed group's validity walk can log and mutate failure state itself.
    // Its ordinary unlocked entry boundary must precede the predicate too.
    if(batch && batch->sq && re4dc_source_world_group_claimed())re4dc_ps2_world_batch_close(batch);
    if(!re4dc_source_world_binding_valid()){re4dc_ps2_world_batch_close(batch);re4dc_source_world_binding_failed();return 0;}
#else
    if(!re4dc_source_world_binding_valid()){re4dc_source_world_binding_failed();return 0;}
#endif
#endif
    if(direct_open){RE4DC_WHD(1);re4dc_missing("native direct part nested");return 0;}
#if RE4DC_SCENERY_SUBMIT_BATCH
    // ensure_model_storage may allocate and log only when the slab is absent.
    if(!model_packets)re4dc_ps2_world_batch_close(batch);
#endif
#if RE4DC_WORLD_HOLE_DIAG
    whd_why=(!k || !out || k[4]>2 || k[5]>2)?10U:!frame_ready?2U:stream_aborted?3U:!ensure_model_storage()?4U:
            model_used+32>kModelPacketBytes/32?5U:0U;
    if(whd_why)return 0;
#else
    if(!k || !out || k[4]>2 || k[5]>2 || !frame_ready || stream_aborted ||
       !ensure_model_storage() || model_used+32>kModelPacketBytes/32)return 0;
#endif
#if RE4DC_UI_POLY_ORDER && RE4DC_SS_UI_ORDER
#if RE4DC_SCENERY_SUBMIT_BATCH
    if(ui_order && quads_flushed<nquad){re4dc_ps2_world_batch_close(batch);ui_order_flush();}
#else
    if(ui_order && quads_flushed<nquad)ui_order_flush();
#endif
    if(stream_aborted)return 0;
#endif
#if RE4DC_PS2_WORLD_R11F_OWNER
#if RE4DC_SCENERY_SUBMIT_BATCH
    if(!re4dc_r11f_binding_valid()){re4dc_ps2_world_batch_close(batch);re4dc_r11f_binding_failed();return 0;}
#else
    if(!re4dc_r11f_binding_valid()){re4dc_r11f_binding_failed();return 0;}
#endif
#endif
    const Key key{k[0],k[1]};
#if RE4DC_WORLD_RECT21
    float rect_u=1.0f,rect_v=1.0f;
    // The selected representation owns its UV rule. Repeat-square scales the
    // short axis; filtered shorter-square keeps normalized UVs unchanged.
    // Never infer either rule from a dimension mismatch alone.
    const auto rect_scale=[&](const Entry& entry){
        const auto& t=entry.package.textures()[0];
        if(t.width==k[2] && t.height==k[3])return true;
        return re4dc::rect21::adapt(k[0],k[1],k[2],k[3],
            {t.width,t.height,t.format,t.flags,t.payload,t.data_size,entry.package.header().payload_crc32},
            rect_u,rect_v,true);
    };
#endif
#if RE4DC_PS2_WORLD_PREFLIGHT_DIAG
#if RE4DC_SCENERY_SUBMIT_BATCH
    re4dc_ps2_world_batch_close(batch);
#endif
    sourceWorldDiagBind(key); // before a cache hit or a load, and before SQ lock
#endif
#if RE4DC_PS2_WORLD_HDR_CACHE
    const bool hdr_on=RE4DC_PS2_HDR_ON;
    unsigned hdr_size=0,hdr_mode=0,hdr_set=0;Ps2HdrSlot* hit=nullptr;
    if(hdr_on){
        // The fog latch changes only at the scenery draw (native_ps2_world.cpp), never inside stream_select.
#if RE4DC_NATIVE_FOG && RE4DC_PS2_WORLD_FOG_SOURCE
        const unsigned hdr_fog=re4dc_ps2_world_fog()?1U:0U;
#else
        const unsigned hdr_fog=0;
#endif
        hdr_size=k[2]|k[3]<<16;hdr_mode=k[4]|k[5]<<2|hdr_fog<<4|0x100U;
        hdr_set=(k[0]^(k[1]>>7)^(k[1]<<3)^(k[4]*0x9e5U)^(k[5]*0x3c1U))&(kPs2HdrSets-1U);
        if(frame-ps2_hdr_log>=600U){
#if RE4DC_SCENERY_SUBMIT_BATCH
            re4dc_ps2_world_batch_close(batch);
#endif
            ps2_hdr_log=frame;
#if RE4DC_PS2_WORLD_HDR_CACHE==2
            re4dc_log("PS2HDR frame=%u hits=%u fills=%u checked=%u mismatched=%u\n",frame,ps2_hdr_hits,ps2_hdr_fills,ps2_hdr_checked,ps2_hdr_bad);
#elif RE4DC_SCENERY_PIECE_STATE
            re4dc_log("PS2HDR frame=%u hits=%u fills=%u piece_hits=%u\n",frame,ps2_hdr_hits,ps2_hdr_fills,ps2_piece_hits);
#else
            re4dc_log("PS2HDR frame=%u hits=%u fills=%u\n",frame,ps2_hdr_hits,ps2_hdr_fills);
#endif
        }
#if RE4DC_SCENERY_PIECE_STATE
        // SCENERY_PIECE_STATE: the part's slot word (room file SCPS) names its slot: no set scan when it still holds
        // this key (the entry / VRAM address test below applies as for any hit)
        if(re4dc_ps2_piece_slot && *re4dc_ps2_piece_slot && *re4dc_ps2_piece_slot<=kPs2HdrSets*kPs2HdrWays){
            Ps2HdrSlot& s=(&ps2_hdr[0][0])[*re4dc_ps2_piece_slot-1U];
            if(s.mode==hdr_mode && s.crc==k[0] && s.fnv==k[1] && s.size==hdr_size){hit=&s;++ps2_piece_hits;}
        }
        if(!hit)
#endif
        for(auto& s:ps2_hdr[hdr_set])
            if(s.mode==hdr_mode && s.crc==k[0] && s.fnv==k[1] && s.size==hdr_size){hit=&s;break;}
#if RE4DC_SCENERY_PIECE_STATE
        if(hit && re4dc_ps2_piece_slot)*re4dc_ps2_piece_slot=unsigned(hit-&ps2_hdr[0][0])+1U;
#endif
    }
#if RE4DC_WORLD_RECT21
    if(hit && hit->entry->valid && hit->entry->key==key){
        const auto& resident=hit->entry->package.textures()[0];
        if(!re4dc::rect21::header_dimensions(hit->words[2],RE4DC_TSP_W(resident),RE4DC_TSP_H(resident)))hit=nullptr;
    }
#endif
    if(hit && hit->entry->valid && hit->entry->key==key && hit->entry->package.pvr_texture(0)==hit->texture){
        const Ps2HdrSlot& slot=*hit;
        Entry* const handle=slot.entry;
#if RE4DC_WORLD_RECT21
        // The same complete descriptor gate runs on hot and cold paths, before
        // any header reaches the TA. Top-level drops or replaced data reject.
        if(!rect_scale(*handle)){RE4DC_WHD(7);return 0;}
#endif
        {constexpr bool pin=false;RE4DC_TOUCH(*handle);} // load()'s hit bookkeeping (pin=false)
        const unsigned pass=k[4];
        const pvr_list_t list=pass==0?PVR_LIST_OP_POLY:pass==1?PVR_LIST_PT_POLY:PVR_LIST_TR_POLY;
#if RE4DC_SCENERY_SUBMIT_BATCH
        if(!stream_scene || stream_list!=list
#if RE4DC_UI_POLY_ORDER
           || ui_order
#endif
        )re4dc_ps2_world_batch_close(batch);
#endif
        stream_select(list);
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
#if RE4DC_SCENERY_SUBMIT_BATCH
    if(!re4dc_source_world_binding_valid()){re4dc_ps2_world_batch_close(batch);re4dc_source_world_binding_failed();return 0;}
#else
    if(!re4dc_source_world_binding_valid()){re4dc_source_world_binding_failed();return 0;}
#endif
#endif

#if RE4DC_PS2_WORLD_R11F_OWNER
#if RE4DC_SCENERY_SUBMIT_BATCH
        if(!re4dc_r11f_binding_valid()){re4dc_ps2_world_batch_close(batch);re4dc_r11f_binding_failed();return 0;}
#else
        if(!re4dc_r11f_binding_valid()){re4dc_r11f_binding_failed();return 0;}
#endif
#endif
#if RE4DC_WORLD_AUTOSORT
#if RE4DC_SCENERY_SUBMIT_BATCH
        if(!world_autosort)re4dc_ps2_world_batch_close(batch);
#endif
        world_sort_begin();
#endif
        if(stream_aborted){RE4DC_WHD(8);return 0;}
        pvr_poly_hdr_t header;
        auto* hw=reinterpret_cast<std::uint32_t*>(&header);
        for(unsigned i=0;i<4;++i){hw[i]=slot.words[i];hw[4+i]=0;}
        ++model_header_hits;++ps2_hdr_hits;
#if RE4DC_PS2_WORLD_HDR_CACHE==2
        // =2 (diagnostic): the uncached lookup and compile beside every hit; a different Entry or word is counted.
        {
            const Re4dcUiImage image{&key,nullptr,k[2],k[3],5,0,0};
            Entry* const ref_handle=load(image,false,&key);
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
#if RE4DC_SCENERY_SUBMIT_BATCH
    if(!re4dc_source_world_binding_valid()){re4dc_ps2_world_batch_close(batch);re4dc_source_world_binding_failed();return 0;}
#else
    if(!re4dc_source_world_binding_valid()){re4dc_source_world_binding_failed();return 0;}
#endif
#endif

#if RE4DC_PS2_WORLD_R11F_OWNER
#if RE4DC_SCENERY_SUBMIT_BATCH
            if(!re4dc_r11f_binding_valid()){re4dc_ps2_world_batch_close(batch);re4dc_r11f_binding_failed();return 0;}
#else
            if(!re4dc_r11f_binding_valid()){re4dc_r11f_binding_failed();return 0;}
#endif
#endif
            bool bad=ref_handle!=handle;
            if(!bad){
                const auto& t=ref_handle->package.textures()[0];
                pvr_poly_cxt_t c;pvr_poly_cxt_txr(&c,list,re4dc::texture::pvr_format(t),RE4DC_TSP_W(t),RE4DC_TSP_H(t),ref_handle->package.pvr_texture(0),PVR_FILTER_BILINEAR);
                const pvr_cull_mode_t cull[]={PVR_CULLING_NONE,PVR_CULLING_CCW,PVR_CULLING_CW};
                c.gen.culling=cull[k[5]];
                c.depth.comparison=PVR_DEPTHCMP_GEQUAL;
                c.depth.write=pass==2?PVR_DEPTHWRITE_DISABLE:PVR_DEPTHWRITE_ENABLE;
                c.blend.src=(pass==2 || (RE4DC_PT_BLEND_FIX && pass==1))?PVR_BLEND_SRCALPHA:PVR_BLEND_ONE;
                c.blend.dst=(pass==2 || (RE4DC_PT_BLEND_FIX && pass==1))?PVR_BLEND_INVSRCALPHA:PVR_BLEND_ZERO;
                c.txr.env=PVR_TXRENV_MODULATEALPHA;
                c.txr.alpha=pass?PVR_TXRALPHA_ENABLE:PVR_TXRALPHA_DISABLE;
                c.txr.uv_clamp=PVR_UVCLAMP_NONE;
#if RE4DC_NATIVE_FOG && RE4DC_PS2_WORLD_FOG_SOURCE
                c.gen.fog_type=re4dc_ps2_world_fog()?PVR_FOG_TABLE:PVR_FOG_DISABLE;
#elif RE4DC_NATIVE_FOG
                c.gen.fog_type=PVR_FOG_TABLE;
#endif
                pvr_poly_hdr_t ref;pvr_poly_compile(&ref,&c);
                bad=std::memcmp(&ref,&header,16)!=0; // words 0..3: pvr_poly_compile leaves 4..7 unset
            }
            ++ps2_hdr_checked;
            if(bad && ++ps2_hdr_bad<=8)re4dc_log("PS2HDR mismatch frame=%u key=%08x-%08x pass=%u cull=%u entry=%d/%d\n",
                frame,k[0],k[1],pass,k[5],int(handle-entries),ref_handle?int(ref_handle-entries):-1);
        }
#endif
#if RE4DC_PS2_INTERIOR_CULL==2
        if(re4dc_ps2_check_header)ps2_check_header(header);
#endif
#if defined(RE4DC_SKY_FAR) || defined(RE4DC_LOOK_TOGGLE)
        if(re4dc_ps2_sky_header)ps2_sky_header(header);
#endif
#if RE4DC_MV_SHADOWS
        if(re4dc_mv_receiver && list==PVR_LIST_OP_POLY
#if RE4DC_UI_POLY_ORDER
            && !ui_order
#endif
        ){reinterpret_cast<std::uint32_t*>(&header)[0]|=PVR_TA_CMD_MODIFIER;++mv_receivers;}
#endif

#if RE4DC_UI_POLY_ORDER
        ui_order_polygon_header(header);
#endif
        std::uint32_t count;re4dc::render::begin_pvr_packet(model_packets+model_used,count,header);
        RE4DC_GAD_HIT(handle->key);
    model_pending=model_used+count;model_handle=handle;
#if RE4DC_SCENERY_SUBMIT_BATCH
        if(!stream_scene){re4dc_ps2_world_batch_close(batch);stream_open();}
#else
        if(!stream_scene)stream_open();
#endif
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
#if RE4DC_SCENERY_SUBMIT_BATCH
    if(!re4dc_source_world_binding_valid()){re4dc_ps2_world_batch_close(batch);re4dc_source_world_binding_failed();return 0;}
#else
    if(!re4dc_source_world_binding_valid()){re4dc_source_world_binding_failed();return 0;}
#endif
#endif

#if RE4DC_PS2_WORLD_R11F_OWNER
#if RE4DC_SCENERY_SUBMIT_BATCH
        if(!re4dc_r11f_binding_valid()){re4dc_ps2_world_batch_close(batch);re4dc_r11f_binding_failed();return 0;}
#else
        if(!re4dc_r11f_binding_valid()){re4dc_r11f_binding_failed();return 0;}
#endif
#endif
#if RE4DC_SCENERY_SUBMIT_BATCH
        auto* sq=batch && batch->sq?batch->sq:static_cast<std::uint32_t*>(static_cast<void*>(sq_lock((void*)PVR_TA_INPUT)));
        if(batch)batch->sq=sq;
#else
        auto* sq=static_cast<std::uint32_t*>(static_cast<void*>(sq_lock((void*)PVR_TA_INPUT)));
#endif
        const auto* words=reinterpret_cast<const std::uint32_t*>(model_packets+model_used);
        for(unsigned i=0;i<8;++i)sq[i]=words[i];
#if RE4DC_TA_HASH
        re4dc_ta_hash(words,32);
#endif
        sq_flush(sq);
        direct_open=true;
        model_handle->frame=frame; // the header is in the TA: pinned for this scene
#if RE4DC_PS2_WORLD_SOURCE_TEX_PREP
        sourceWorldTextureAcquired(key);
#endif
        ++frame_pvr_calls;frame_pvr_bytes+=32;stream_model_bytes+=32;
        out->sq=sq+8;out->scratch=model_packets+model_pending;out->scratch_capacity=kModelPacketBytes/32-model_pending;
#if RE4DC_WORLD_RECT21
        out->u_scale=rect_u;out->v_scale=rect_v;
#else
        out->u_scale=out->v_scale=1;
#endif
#if RE4DC_SCENERY_SUBMIT_BATCH
        failed_begin.accepted=true;
#endif
        return 1;
    }
#endif
    const Re4dcUiImage image{&key,nullptr,k[2],k[3],5,0,0};
#if RE4DC_WORLD_HOLE_DIAG
    whd_load_why="other";
#endif
#if RE4DC_SCENERY_SUBMIT_BATCH
    re4dc_ps2_world_batch_close(batch);
#endif
    Entry* handle=load(image,false,&key);
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
#if RE4DC_SCENERY_SUBMIT_BATCH
    if(!re4dc_source_world_binding_valid()){re4dc_ps2_world_batch_close(batch);re4dc_source_world_binding_failed();return 0;}
#else
    if(!re4dc_source_world_binding_valid()){re4dc_source_world_binding_failed();return 0;}
#endif
#endif

#if RE4DC_PS2_WORLD_R11F_OWNER
#if RE4DC_SCENERY_SUBMIT_BATCH
    if(!re4dc_r11f_binding_valid()){re4dc_ps2_world_batch_close(batch);re4dc_r11f_binding_failed();return 0;}
#else
    if(!re4dc_r11f_binding_valid()){re4dc_r11f_binding_failed();return 0;}
#endif
#endif
    if(!handle || !frame_ready || stream_aborted || direct_open){RE4DC_WHD(!handle?6U:!frame_ready?2U:stream_aborted?3U:1U);++model_texture_rejects;return 0;}
    const auto& t=handle->package.textures()[0];
#if RE4DC_WORLD_RECT21
    if(!rect_scale(*handle)){RE4DC_WHD(7);return 0;}
#else
    if(t.width!=k[2] || t.height!=k[3]){RE4DC_WHD(7);return 0;} // repeated UVs cannot use padding
#endif
    const unsigned pass=k[4];
    const pvr_list_t list=pass==0?PVR_LIST_OP_POLY:pass==1?PVR_LIST_PT_POLY:PVR_LIST_TR_POLY;
#if RE4DC_SCENERY_SUBMIT_BATCH
    if(!stream_scene || stream_list!=list
#if RE4DC_UI_POLY_ORDER
       || ui_order
#endif
    )re4dc_ps2_world_batch_close(batch);
#endif
    stream_select(list);
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
#if RE4DC_SCENERY_SUBMIT_BATCH
    if(!re4dc_source_world_binding_valid()){re4dc_ps2_world_batch_close(batch);re4dc_source_world_binding_failed();return 0;}
#else
    if(!re4dc_source_world_binding_valid()){re4dc_source_world_binding_failed();return 0;}
#endif
#endif

#if RE4DC_PS2_WORLD_R11F_OWNER
#if RE4DC_SCENERY_SUBMIT_BATCH
    if(!re4dc_r11f_binding_valid()){re4dc_ps2_world_batch_close(batch);re4dc_r11f_binding_failed();return 0;}
#else
    if(!re4dc_r11f_binding_valid()){re4dc_r11f_binding_failed();return 0;}
#endif
#endif
#if RE4DC_WORLD_AUTOSORT
#if RE4DC_SCENERY_SUBMIT_BATCH
    if(!world_autosort)re4dc_ps2_world_batch_close(batch);
#endif
    world_sort_begin();
#endif
    if(stream_aborted){RE4DC_WHD(8);return 0;}
    pvr_poly_cxt_t c;pvr_poly_cxt_txr(&c,list,re4dc::texture::pvr_format(t),RE4DC_TSP_W(t),RE4DC_TSP_H(t),handle->package.pvr_texture(0),PVR_FILTER_BILINEAR);
    const pvr_cull_mode_t cull[]={PVR_CULLING_NONE,PVR_CULLING_CCW,PVR_CULLING_CW};
    c.gen.culling=cull[k[5]];
    c.depth.comparison=PVR_DEPTHCMP_GEQUAL;
    c.depth.write=pass==2?PVR_DEPTHWRITE_DISABLE:PVR_DEPTHWRITE_ENABLE;
    c.blend.src=(pass==2 || (RE4DC_PT_BLEND_FIX && pass==1))?PVR_BLEND_SRCALPHA:PVR_BLEND_ONE;
    c.blend.dst=(pass==2 || (RE4DC_PT_BLEND_FIX && pass==1))?PVR_BLEND_INVSRCALPHA:PVR_BLEND_ZERO;
    c.txr.env=PVR_TXRENV_MODULATEALPHA;
    c.txr.alpha=pass?PVR_TXRALPHA_ENABLE:PVR_TXRALPHA_DISABLE;
    c.txr.uv_clamp=PVR_UVCLAMP_NONE;
#if RE4DC_NATIVE_FOG && RE4DC_PS2_WORLD_FOG_SOURCE
    c.gen.fog_type=re4dc_ps2_world_fog()?PVR_FOG_TABLE:PVR_FOG_DISABLE; // source GX fog at the scenery draw
#elif RE4DC_NATIVE_FOG
    c.gen.fog_type=PVR_FOG_TABLE;
#endif
    pvr_poly_hdr_t header;pvr_poly_compile(&header,&c);++model_header_builds;
#if RE4DC_PS2_WORLD_HDR_CACHE
    if(hdr_on){
        auto* hw=reinterpret_cast<std::uint32_t*>(&header);
        hw[4]=hw[5]=hw[6]=hw[7]=0; // never written by pvr_poly_compile here (stack contents before; unused by the PVR)
        // The key's stale slot if it has one, else the set's next slot in turn.
        Ps2HdrSlot& slot=hit?*hit:ps2_hdr[hdr_set][ps2_hdr_next[hdr_set]++%kPs2HdrWays];
        slot.crc=k[0];slot.fnv=k[1];slot.size=hdr_size;slot.mode=hdr_mode;slot.entry=handle;
        slot.texture=handle->package.pvr_texture(0);
        for(unsigned i=0;i<4;++i)slot.words[i]=hw[i];
        ++ps2_hdr_fills;
#if RE4DC_SCENERY_PIECE_STATE
        if(re4dc_ps2_piece_slot)*re4dc_ps2_piece_slot=unsigned(&slot-&ps2_hdr[0][0])+1U;
#endif
    }
#endif
#if RE4DC_PS2_INTERIOR_CULL==2
    if(re4dc_ps2_check_header)ps2_check_header(header);
#endif
#if defined(RE4DC_SKY_FAR) || defined(RE4DC_LOOK_TOGGLE)
    if(re4dc_ps2_sky_header)ps2_sky_header(header);
#endif
#if RE4DC_MV_SHADOWS
    if(re4dc_mv_receiver && list==PVR_LIST_OP_POLY
#if RE4DC_UI_POLY_ORDER
            && !ui_order
#endif
        ){reinterpret_cast<std::uint32_t*>(&header)[0]|=PVR_TA_CMD_MODIFIER;++mv_receivers;}
#endif

#if RE4DC_UI_POLY_ORDER
    ui_order_polygon_header(header);
#endif
    std::uint32_t count;re4dc::render::begin_pvr_packet(model_packets+model_used,count,header);
    RE4DC_GAD_HIT(handle->key);
    model_pending=model_used+count;model_handle=handle;
#if RE4DC_SCENERY_SUBMIT_BATCH
    if(!stream_scene){re4dc_ps2_world_batch_close(batch);stream_open();}
#else
    if(!stream_scene)stream_open();
#endif
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
#if RE4DC_SCENERY_SUBMIT_BATCH
    if(!re4dc_source_world_binding_valid()){re4dc_ps2_world_batch_close(batch);re4dc_source_world_binding_failed();return 0;}
#else
    if(!re4dc_source_world_binding_valid()){re4dc_source_world_binding_failed();return 0;}
#endif
#endif

#if RE4DC_PS2_WORLD_R11F_OWNER
#if RE4DC_SCENERY_SUBMIT_BATCH
    if(!re4dc_r11f_binding_valid()){re4dc_ps2_world_batch_close(batch);re4dc_r11f_binding_failed();return 0;}
#else
    if(!re4dc_r11f_binding_valid()){re4dc_r11f_binding_failed();return 0;}
#endif
#endif
#if RE4DC_SCENERY_SUBMIT_BATCH
    auto* sq=batch && batch->sq?batch->sq:static_cast<std::uint32_t*>(static_cast<void*>(sq_lock((void*)PVR_TA_INPUT)));
    if(batch)batch->sq=sq;
#else
    auto* sq=static_cast<std::uint32_t*>(static_cast<void*>(sq_lock((void*)PVR_TA_INPUT)));
#endif
    const auto* words=reinterpret_cast<const std::uint32_t*>(model_packets+model_used);
    for(unsigned i=0;i<8;++i)sq[i]=words[i];
#if RE4DC_TA_HASH
    re4dc_ta_hash(words,32);
#endif
    sq_flush(sq);
    direct_open=true;
    model_handle->frame=frame; // the header is in the TA: pinned for this scene
#if RE4DC_PS2_WORLD_SOURCE_TEX_PREP
        sourceWorldTextureAcquired(key);
#endif
    ++frame_pvr_calls;frame_pvr_bytes+=32;stream_model_bytes+=32;
    out->sq=sq+8;out->scratch=model_packets+model_pending;out->scratch_capacity=kModelPacketBytes/32-model_pending;
#if RE4DC_WORLD_RECT21
    out->u_scale=rect_u;out->v_scale=rect_v;
#else
    out->u_scale=out->v_scale=1;
#endif
#if RE4DC_SCENERY_SUBMIT_BATCH
    failed_begin.accepted=true;
#endif
    return 1;
#else
    (void)k;(void)out;return 0;
#endif
}
#if RE4DC_SCENERY_SUBMIT_BATCH
extern "C" int re4dc_ps2_world_direct_begin(const unsigned* k,Re4dcModelDirect* out){
    return re4dc_ps2_world_direct_begin_batch(k,out,nullptr);
}
#endif

#if RE4DC_SCENERY_SUBMIT_BATCH
static Re4dcWorldSubmitBatch batch;
#endif

static unsigned bits(float f){unsigned result;std::memcpy(&result,&f,4);return result;}
static std::uint32_t* emit(std::uint32_t* sq,unsigned n,unsigned id){
    for(unsigned j=0;j<n;++j){for(unsigned w=0;w<8;++w)sq[w]=0xf0000000U|(id<<16)|(j<<3)|w;sq_flush(sq);sq+=8;}
    return sq;
}
static void key_for(unsigned index,unsigned pass,unsigned cull,unsigned out[6]){
    out[0]=0x11000001U+index*17U;out[1]=0x22000103U+index*31U;out[2]=64;out[3]=64;out[4]=pass;out[5]=cull;
}
static void seed(unsigned index,unsigned pass=0,unsigned cull=2){
    unsigned k[6];key_for(index,pass,cull,k);Entry& e=entries[index];e.valid=true;e.key={k[0],k[1]};e.frame=10;e.package={};e.package.address=0x8000U+index*4096U;
    const unsigned size=k[2]|k[3]<<16,mode=pass|cull<<2|unsigned(fog)<<4|0x100U;
    const unsigned set=(k[0]^(k[1]>>7)^(k[1]<<3)^(pass*0x9e5U)^(cull*0x3c1U))&(kPs2HdrSets-1U);
    auto& slot=ps2_hdr[set][ps2_hdr_next[set]++%kPs2HdrWays];slot.crc=k[0];slot.fnv=k[1];slot.size=size;slot.mode=mode;slot.entry=&e;slot.texture=e.package.pvr_texture(0);
    pvr_poly_cxt_t c;pvr_poly_cxt_txr(&c,pass==0?PVR_LIST_OP_POLY:pass==1?PVR_LIST_PT_POLY:PVR_LIST_TR_POLY,0,64,64,slot.texture,1);
    c.gen.culling=cull;c.depth.comparison=PVR_DEPTHCMP_GEQUAL;c.depth.write=pass==2?PVR_DEPTHWRITE_DISABLE:PVR_DEPTHWRITE_ENABLE;
    c.blend.src=pass?PVR_BLEND_SRCALPHA:PVR_BLEND_ONE;c.blend.dst=pass?PVR_BLEND_INVSRCALPHA:PVR_BLEND_ZERO;
    c.txr.alpha=pass?PVR_TXRALPHA_ENABLE:PVR_TXRALPHA_DISABLE;c.gen.fog_type=fog?PVR_FOG_TABLE:PVR_FOG_DISABLE;
    pvr_poly_hdr_t h;pvr_poly_compile(&h,&c);std::memcpy(slot.words,&h,16);
    piece_words[index]=unsigned(&slot-&ps2_hdr[0][0])+1U;
}
static void normal_part(unsigned index,unsigned pass,unsigned cull,unsigned n,unsigned style=0){
    unsigned k[6];key_for(index,pass,cull,k);re4dc_ps2_piece_slot=piece_words+index;
    Re4dcModelDirect out{};
    const unsigned* key=style==1?nullptr:k;
    Re4dcModelDirect* dest=style==2?nullptr:&out;
#if RE4DC_SCENERY_SUBMIT_BATCH
    const int result=style==3?re4dc_ps2_world_direct_begin(key,dest):
        re4dc_ps2_world_direct_begin_batch(key,dest,style==4?nullptr:&batch);
#else
    const int result=re4dc_ps2_world_direct_begin(key,dest);
#endif
    returns.push_back(result);
    if(result){
        capacities.push_back(out.scratch_capacity);u_bits.push_back(bits(out.u_scale));v_bits.push_back(bits(out.v_scale));
        assert(out.scratch==model_packets+model_pending);emit(out.sq,n,index);
#if RE4DC_SCENERY_SUBMIT_BATCH
        if(style==3)re4dc_model_direct_end(n);
        else re4dc_ps2_world_direct_end_batch(n,style==4?nullptr:&batch);
#else
        re4dc_model_direct_end(n);
#endif
    }
    re4dc_ps2_piece_slot=nullptr;
}
// Actual production Emitter, borrow/gather, emit_pick, replay and clipper.
// Geometry is a small validated synthetic R4IM; no game asset is present.
#define RE4DC_SCENERY_CHUNK 1
#define RE4DC_MESH_DIRECT 1
#define RE4DC_PS2_WORLD_MESH 1
#define RE4DC_PS2_VERTEX_ALPHA 1
#define RE4DC_PS2_PVS 0
#define RE4DC_SKY_ANY 1
#define RE4DC_MESH_FASTPATH 1
#define RE4DC_MESH_PRIME_LAZY 1
#define RE4DC_PS2_WORLD_LEAN 23
#define RE4DC_PS2_STRIP_GROUPS 1
#define RE4DC_MESH_VP_SCHED 1
#define RE4DC_MESH_STRIP_LEAN 1
#define RE4DC_HW_LEAN 1
#define RE4DC_SCENERY_SCREEN_MEMO 1
#define RE4DC_INV255 /255.0f
#include "/root/probe/dedup-prefetch-context23/port/dreamcast/room/instanced_mesh.hpp"
#include "/root/probe/dedup-prefetch-context23/port/dreamcast/room/mesh_fastpath.hpp"
#include "/root/probe/dedup-prefetch-context23/port/dreamcast/room/mesh_fastpath_sched.hpp"
#include "/root/probe/dedup-prefetch-context23/port/dreamcast/room/pvr_geometry.hpp"
#include "/root/probe/dedup-prefetch-context23/port/dreamcast/room/static_room_prepare.hpp"

namespace re4dc::render {
std::uint32_t shade_color(float red, float green, float blue) {
    const std::uint32_t r = static_cast<std::uint32_t>(
        std::clamp(red * 255.0f, 0.0f, 255.0f));
    const std::uint32_t g = static_cast<std::uint32_t>(
        std::clamp(green * 255.0f, 0.0f, 255.0f));
    const std::uint32_t b = static_cast<std::uint32_t>(
        std::clamp(blue * 255.0f, 0.0f, 255.0f));
    return 0xff000000U | (r << 16U) | (g << 8U) | b;
}
RenderVertex interpolate_vertex(const RenderVertex& a, const RenderVertex& b,
                                float t, const ClipParameters& parameters) {
    RenderVertex result{};
    result.position.world_x = a.position.world_x +
                              (b.position.world_x - a.position.world_x) * t;
    result.position.world_y = a.position.world_y +
                              (b.position.world_y - a.position.world_y) * t;
    result.position.world_z = a.position.world_z +
                              (b.position.world_z - a.position.world_z) * t;
    result.position.depth = a.position.depth +
                            (b.position.depth - a.position.depth) * t;
    result.u = a.u + (b.u - a.u) * t;
    result.v = a.v + (b.v - a.v) * t;
    result.light_red = a.light_red + (b.light_red - a.light_red) * t;
    result.light_green =
        a.light_green + (b.light_green - a.light_green) * t;
    result.light_blue = a.light_blue + (b.light_blue - a.light_blue) * t;
    result.offset_color = a.offset_color;
    float x = result.position.world_x;
    float y = result.position.world_y;
    float z = result.position.world_z;
    parameters.project(x, y, z, parameters.context);
    result.position.x = x;
    result.position.y = y;
    result.position.z = z;
    return result;
}
std::uint32_t clip_projected_triangle(const RenderVertex* source,
                                       pvr_vertex_t* output,
                                       std::uint8_t cull_mode,
                                       const ClipParameters& parameters,
                                       ClipStats* stats, const float* alpha) {
#if RE4DC_COPY_LEAN
    // Entries [0, clipped_count) are written before any read; the zero-fill
    // was a 208-byte memset per clipped triangle (D367 LD: ~1.1 ms/frame).
    RenderVertex clipped[4];
    float clipped_alpha[4]; // read only where written (alpha != nullptr)
#else
    RenderVertex clipped[4]{};
    float clipped_alpha[4]{}; // optional source alpha, no growth of room vertex caches
#endif
    unsigned clipped_count = 0;
    unsigned inside_count = 0;
    for(unsigned corner = 0; corner < 3; ++corner) {
        inside_count +=
            source[corner].position.depth >= parameters.near_distance ? 1U : 0U;
    }
    if(inside_count == 3U) {
        if(stats != nullptr) {
            ++stats->accepts;
        }
        clipped[0] = source[0];
        clipped[1] = source[1];
        clipped[2] = source[2];
        clipped_count = 3U;
        if(alpha)for(unsigned i=0;i<3;++i)clipped_alpha[i]=alpha[i];
    } else if(inside_count == 0U) {
        if(stats != nullptr) {
            ++stats->rejects;
        }
        return 0;
    } else {
        if(stats != nullptr) {
            ++stats->crossings;
        }
        RenderVertex previous = source[2];
        float previous_alpha=alpha?alpha[2]:1.0f;
        bool previous_inside =
            previous.position.depth >= parameters.near_distance;
        for(unsigned corner = 0; corner < 3; ++corner) {
            const RenderVertex current = source[corner];
            const float current_alpha=alpha?alpha[corner]:1.0f;
            const bool current_inside =
                current.position.depth >= parameters.near_distance;
            if(current_inside != previous_inside) {
                const float t =
                    (parameters.near_distance - previous.position.depth) /
                    (current.position.depth - previous.position.depth);
                if(alpha)clipped_alpha[clipped_count]=previous_alpha+(current_alpha-previous_alpha)*t;
                clipped[clipped_count++] =
                    interpolate_vertex(previous, current, t, parameters);
            }
            if(current_inside) {
                if(alpha)clipped_alpha[clipped_count]=current_alpha;
                clipped[clipped_count++] = current;
            }
            previous = current;previous_alpha=current_alpha;
            previous_inside = current_inside;
        }
    }
    if(clipped_count < 3) {
        return 0;
    }

    std::uint32_t triangle_count = 0;
    for(unsigned fan = 1; fan + 1 < clipped_count; ++fan) {
        const RenderVertex triangle[3] = {clipped[0], clipped[fan],
                                          clipped[fan + 1]};
        const bool beyond_far =
            triangle[0].position.depth > parameters.far_distance &&
            triangle[1].position.depth > parameters.far_distance &&
            triangle[2].position.depth > parameters.far_distance;
        if(beyond_far || !triangle_visible_xy(
               triangle[0].position, triangle[1].position, triangle[2].position,
               cull_mode, parameters.width, parameters.height)) continue;
        pvr_vertex_t* destination = output + triangle_count * 3U;
        for(unsigned corner = 0; corner < 3; ++corner) {
            destination[corner] = {
                .flags = corner == 2 ? PVR_CMD_VERTEX_EOL : PVR_CMD_VERTEX,
                .x = triangle[corner].position.x,
                .y = triangle[corner].position.y,
                .z = triangle[corner].position.z,
                .u = triangle[corner].u,
                .v = triangle[corner].v,
                .argb = shade_color(triangle[corner].light_red,
                                    triangle[corner].light_green,
                                    triangle[corner].light_blue),
                .oargb = triangle[corner].offset_color,
            };
            if(alpha){
                const unsigned index=corner==0?0:fan+corner-1;
                const auto a=static_cast<std::uint32_t>(std::clamp(clipped_alpha[index]*255.0f,0.0f,255.0f));
                destination[corner].argb=(destination[corner].argb&0x00ffffffU)|(a<<24U);
            }
        }
        ++triangle_count;
    }
    return triangle_count;
}
}
struct QueuePart {unsigned cull=1;float uv_offset[2]{.125f,-.25f},projection[7]{},viewport[6]{};};
using Re4dcModelPart=QueuePart;
struct Re4dcModelPacket {void* vertices;unsigned capacity;float u_scale,v_scale;};
static unsigned model_parts,model_empty_parts,model_input,model_output,packet_aborts;
static unsigned pick_calls,lut_calls,screen_loads,queue_native,queue_fallback,queue_aborts;
static unsigned re4dc_mv_camera_frame=~0U;
static float re4dc_mv_projection[7],re4dc_mv_viewport[6];
static std::vector<unsigned> queue_events;
static std::uint32_t lut[512],ps2_lut4[512];
static bool ps2_lut4_built;
namespace piece {static const void* pkg;static unsigned* table;}
namespace whd {static void note(unsigned,const unsigned*){assert(!locked);}}
namespace lean {
constexpr unsigned kMode=23;
static pvr_vertex_t* prime_at;
static unsigned primed;
static struct {unsigned prime_reuse=0,prime_bad=0;}st;
}
static struct {unsigned batches=0,bind_rejects=0,groups_visible=0,reserve_rejects=0,strips=0,strips_clipped=0,strips_culled=0,triangles_clipped=0,vertices=0;}stats;
static unsigned re4dc_ui_frame(){return frame;}
const std::uint32_t* ps2_vertex_alpha_lut(){
    if(!ps2_lut4_built){
        for(unsigned i=0;i<256;++i){
            ps2_lut4[i]=(i>>4)*0x11000000U|(i&15U)*0x110000U;
            ps2_lut4[256+i]=(i>>4)*0x1100U|(i&15U)*0x11U;
        }
        ps2_lut4_built=true;
    }
    return ps2_lut4;
}
static int re4dc_model_packet_streaming(){return 1;}
static void re4dc_model_packet_commit(unsigned){assert(false);}
static void re4dc_model_result(unsigned reason,unsigned input,unsigned output){
    assert(reason==0);++model_parts;if(!output)++model_empty_parts;model_input+=input;model_output+=output;
    queue_events.insert(queue_events.end(),{8,reason,input,output});
}
static void re4dc_model_packet_abort(){assert(!locked);++packet_aborts;stream_aborted=true;model_used=0;model_handle=nullptr;}
static int re4dc_model_direct_begin(const QueuePart*,Re4dcModelDirect*){assert(false);return 0;}
static int re4dc_model_packet_begin(const QueuePart*,Re4dcModelPacket*){assert(false);return 0;}
static std::uint32_t* re4dc_ta_put(std::uint32_t* q,const pvr_vertex_t* v,unsigned n){
    for(unsigned i=0;i<n;++i){std::memcpy(q,v+i,32);sq_flush(q);q+=8;}return q;
}

// SH4-only walk_lean's hardware edge, using the repository's portable codes
// and emit helpers. It has the documented depth-cull/clip/screen-cull ordering.
// The production C++ strips_lean caller and clipper remain unmodified below.
namespace re4dc::vp {
static const std::uint8_t* walk_lean(const std::uint8_t* s,const std::uint8_t* end,const std::uint8_t* oc,
    const pvr_vertex_t* cache,unsigned limit,std::uint32_t*& q,unsigned& culled,unsigned& emitted){
    while(s<end){
        const unsigned n=*s;
        const auto code=codes(oc,s+1,n);
        if(code.all&depth_mask(kChecksAll)){++culled;s+=n+1;continue;}
        if((code.any&depth_mask(kChecksAll))||n>limit)return s;
        if(code.all&screen_mask(kChecksAll))++culled;
        else {
            auto* first=reinterpret_cast<pvr_vertex_t*>(q);
            auto* last=emit(first,cache,s+1,n);
            for(auto* v=first;v<last;++v)sq_flush(reinterpret_cast<std::uint32_t*>(v));
            q=reinterpret_cast<std::uint32_t*>(last);++emitted;
        }
        s+=n+1;
    }
    return s;
}
}
void load_screen(const float* mv,const float* p,const float* v){
#if RE4DC_SCENERY_REPLAY_LEAN && RE4DC_SCENERY_SCREEN_MEMO
    alignas(32) static matrix_t screen;
    static float last[20]; static bool have=false;
    // Compare the existing bitwise key in place. A memo hit needs no 80-byte
    // temporary input copy, and still reloads the matrix after a yielding bind.
    if(have && !std::memcmp(mv,last,48) && !std::memcmp(p+1,last+12,16) &&
       !std::memcmp(v,last+16,16)){mat_load(&screen);return;}
    std::memcpy(last,mv,48);std::memcpy(last+12,p+1,16);std::memcpy(last+16,v,16);have=true;
#endif
    const float sx=RE4DC_SCREEN_WF/v[2],sy=RE4DC_SCREEN_HF/v[3];
    const float row0[4]={RE4DC_SCREEN_HALF_WF*p[1],0,RE4DC_SCREEN_HALF_WF*p[2]-sx*(v[0]+v[2]*.5f),0};
    const float row1[4]={0,-RE4DC_SCREEN_HALF_HF*p[3],-RE4DC_SCREEN_HALF_HF*p[4]-sy*(v[1]+v[3]*.5f),0};
    const float row2[4]={0,0,1,0},row3[4]={0,0,-1,0};
    const float* rows[4]={row0,row1,row2,row3};
#if !(RE4DC_SCENERY_REPLAY_LEAN && RE4DC_SCENERY_SCREEN_MEMO)
    alignas(32) static matrix_t screen;
#endif
#if RE4DC_SCENERY_SCREEN_MEMO && !RE4DC_SCENERY_REPLAY_LEAN
    // SCENERY_SCREEN_MEMO (scenery19): parts of one placement bind with the same inputs; the same inputs give the
    // same matrix (identical arithmetic), so reload the last one. Exact.
    static float last[20]; static bool have=false;
    float in[20];
    std::memcpy(in,mv,48);in[12]=p[1];in[13]=p[2];in[14]=p[3];in[15]=p[4];std::memcpy(in+16,v,16);
    if(have && !std::memcmp(in,last,sizeof(in))){mat_load(&screen);return;}
    std::memcpy(last,in,sizeof(in));have=true;
#endif
    for(unsigned r=0;r<4;++r)for(unsigned c=0;c<4;++c){
        float value=c==3?rows[r][3]:0.0f;
        for(unsigned k=0;k<3;++k)value+=rows[r][k]*mv[4*k+c];
        screen[c][r]=value; // KOS matrix_t is column-major for ftrv
    }
    mat_load(&screen);
}
namespace dedup {
__attribute__((noinline)) void fill(const re4dc::vp::Vertex12* in,pvr_vertex_t* cache,std::uint8_t* oc,unsigned u,
                                    unsigned n,const std::uint8_t* s,const re4dc::vp::Constants& k,unsigned clo=0,unsigned chi=255){
    const float au=k.f.au,bu=k.f.bu,av=k.f.av,bv=k.f.bv;
    const std::uint32_t* lut=k.lut;const std::uint32_t andm=k.and_mask,orb=k.or_bits;
    for(unsigned j=u;j<n;++j){
#if RE4DC_SCENERY_DEDUP==3
        const unsigned q=in[j].x; // validated SDO3 refs are this repeat vertex's x word
        (void)s;
        if(q<clo || q>chi)continue; // an unselected repeat never reads an unprimed first
#else
        const unsigned q=*s++;
#endif
        const pvr_vertex_t& a=cache[q];pvr_vertex_t& d=cache[j];
        d.x=a.x;d.y=a.y;d.z=a.z;oc[j]=oc[q];
        const auto& v=in[j];
        float fu=float(v.u),fv=float(v.v),ru=bu,rv=bv;
        // the transform's u = fmac(float(u), au, bu), v = fmac(float(v), av, bv)
        ru=ru+au*fu; // host-only FMAC edge
        rv=rv+av*fv; // host-only FMAC edge
        d.u=ru;d.v=rv;
        const unsigned c=v.color;
        d.argb=((lut[c>>8]|lut[256U+(c&255U)])&andm)|orb;
#if defined(RE4DC_SCENERY_DEDUP_CHECK) && RE4DC_SCENERY_DEDUP_CHECK
        // check build: the knob-off kernel on this corner, word for word (outcode screen/depth bits only)
        static unsigned checked=0,bad=0;
        alignas(32) pvr_vertex_t t[2];std::uint8_t to[8];
#if RE4DC_SCENERY_DEDUP==3
        auto ref=v;ref.x=in[q].x;ref.y=in[q].y;ref.z=in[q].z;
        re4dc::vp::transform_sched<re4dc::vp::kChecksAll>(&ref,1,t,to,k);
#else
        re4dc::vp::transform_sched<re4dc::vp::kChecksAll>(&v,1,t,to,k);
#endif
        std::uint32_t wa[6],wb[6];
        std::memcpy(wa,&t[0].x,24);std::memcpy(wb,&d.x,24);
        ++checked;
        if(q<clo || q>chi){--checked;continue;}   // its first copy was not transformed: the repeat is not drawn
        if(std::memcmp(wa,wb,24) || ((to[0]^oc[j])&0x3fU)){
            if(++bad<=16)re4dc_log("SCNDEDUP CHECK bad j=%u q=%u n=%u ref %08x %08x %08x %08x %08x %08x oc %02x got %08x %08x %08x %08x %08x %08x oc %02x\n",
                j,q,n,wa[0],wa[1],wa[2],wa[3],wa[4],wa[5],to[0],wb[0],wb[1],wb[2],wb[3],wb[4],wb[5],oc[j]);
        }
        if(!(checked&0x3ffffU) || bad==1)re4dc_log("SCNDEDUP CHECK checked=%u bad=%u\n",checked,bad);
#endif
    }
}
}
struct Emitter {
    const Re4dcModelPart& p;
    float mv[12];  // package -> view: group bounds
    float near,far;
    float mvq[12]={}; // stored corner -> view (mv, or mv with the AoS12 grid folded in)
    const std::uint32_t* palette=nullptr;
    Re4dcModelPacket packet{}; pvr_vertex_t* dst=nullptr;
    unsigned used=0,input=0,output=0,alpha=0;
    unsigned limit=0; // packet slots strips may use: packet.capacity less any borrowed tail
    bool streaming=false,bound=false,submitted=false;
    bool vertex_alpha=false; // corner alpha from the colour palette (source vertex alpha)
#if RE4DC_SCENERY_DEDUP==3
    const re4dc::room::CompactVertex12* dd_base=nullptr;
    unsigned dd_unique=0,dd_count=0; // borrowed meshlet context, no allocation or retained mask
#endif
    re4dc::render::ClipParameters clip{};
#if RE4DC_PS2_WORLD_MESH
    const unsigned* ps2=nullptr; // PS2_WORLD_MESH part: {crc, fnv, width, height, pass, cull}; binds by key, not by p
#if RE4DC_SCENERY_PIECE_STATE
    std::uint32_t* piece_slot=nullptr; // SCENERY_PIECE_STATE: this part's header-slot word (SCPS), nullptr: none
#endif
#endif
#if RE4DC_HW_LEAN
    float proj_bx=0,proj_by=0; // project()'s viewport offsets in 640x480 pixels
#if RE4DC_RES_MODES
    float proj_hw=320,proj_hh=240; // RES_MODES: the render size's halves per part (project() reads no globals)
#endif
    void set_clip(){
        const float* v=p.viewport;
#if RE4DC_RES_MODES
        proj_hw=RE4DC_SCREEN_HALF_WF;proj_hh=RE4DC_SCREEN_HALF_HF;
#endif
        proj_bx=(v[0]+v[2]*.5f)*RE4DC_SCREEN_WF/v[2];proj_by=(v[1]+v[3]*.5f)*RE4DC_SCREEN_HF/v[3];
        clip={near,far,RE4DC_SCREEN_W,RE4DC_SCREEN_H,project,this};
    }
#else
    void set_clip(){clip={near,far,RE4DC_SCREEN_W,RE4DC_SCREEN_H,project,this};}
#endif

    static void project(float& x,float& y,float& z,void* context){
        const auto& d=*static_cast<const Emitter*>(context);
        const float* p=d.p.projection;const float* v=d.p.viewport;
#if RE4DC_HW_LEAN && defined(__sh__)
        // 1/|z| by fsrra(z*z): the clipper only keeps corners with depth=-z >= near > 0.
        // The viewport terms are per part (proj_setup): v[2]*.5*W/v[2] = W/2, v[3]*.5*H/v[3] = H/2 for the current
        // render size (RES_MODES: 320/120 in a 240-line mode; the defaults are the 640x480 constants).
        float inv=z*z;
        __asm__("fsrra %0" : "+f"(inv));
        (void)v;
#if RE4DC_RES_MODES
        x=d.proj_hw*(p[1]*x+p[2]*z)*inv+d.proj_bx;
        y=-d.proj_hh*(p[3]*y+p[4]*z)*inv+d.proj_by;
#else
        x=RE4DC_SCREEN_HALF_WF*(p[1]*x+p[2]*z)*inv+d.proj_bx;
        y=-RE4DC_SCREEN_HALF_HF*(p[3]*y+p[4]*z)*inv+d.proj_by;
#endif
        z=inv;
        return;
#else
        const float inv=1.0f/(-z);
#endif
        x=(v[2]*.5f*(p[1]*x+p[2]*z)*inv+v[0]+v[2]*.5f)*RE4DC_SCREEN_WF/v[2];
        y=(-v[3]*.5f*(p[3]*y+p[4]*z)*inv+v[1]+v[3]*.5f)*RE4DC_SCREEN_HF/v[3];
        z=inv;
    }
#if RE4DC_MESH_DIRECT
    // Store-queue sink (MeshDraw only): the header goes to the TA at bind(),
    // strips follow as they are accepted; the slab range is staging for the
    // clipper and the transform cache only. Nothing can be rolled back once
    // bound, so later failures abort the frame (submitted).
    bool direct=false; std::uint32_t* sq=nullptr; unsigned slots=0;
#if RE4DC_SCENERY_SUBMIT_BATCH
    Re4dcWorldSubmitBatch* submit_batch=nullptr; // borrowed only inside chunk_flush
    void end_direct(){if(sq){
        if(submit_batch)re4dc_ps2_world_direct_end_batch(slots,submit_batch);
        else re4dc_model_direct_end(slots);
        sq=nullptr;
    }}
#else
    void end_direct(){if(sq){re4dc_model_direct_end(slots);sq=nullptr;}}
#endif
    void put(unsigned n){sq=re4dc_ta_put(sq,dst+used,n);slots+=n;}
#endif
    bool bind(){
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
#if RE4DC_SCENERY_SUBMIT_BATCH
        // Claimed transition groups may log from the validity walk itself.
        if(submit_batch && !sq && re4dc_source_world_group_claimed())
            re4dc_ps2_world_batch_close(submit_batch);
        if(!re4dc_source_world_binding_valid()){
            // A new part has not bound yet; release the previous part's idle
            // lock before the existing owner-failure/abort callback.
            if(submit_batch && !sq)re4dc_ps2_world_batch_close(submit_batch);
            re4dc_source_world_binding_failed();return false;
        }
#else
        if(!re4dc_source_world_binding_valid()){re4dc_source_world_binding_failed();return false;}
#endif
#endif
        if(bound)return true;
#if RE4DC_MV_SHADOWS
        struct MvReceiver{MvReceiver(){re4dc_mv_receiver=1;}~MvReceiver(){re4dc_mv_receiver=0;}} mv_receiver;
        if(p.projection[0]==0 && p.viewport[2]>0 && p.viewport[3]>0 && re4dc_mv_camera_frame!=re4dc_ui_frame()){
            std::memcpy(re4dc_mv_projection,p.projection,sizeof(re4dc_mv_projection));
            std::memcpy(re4dc_mv_viewport,p.viewport,sizeof(re4dc_mv_viewport));
            re4dc_mv_camera_frame=re4dc_ui_frame();
        }
#endif
#if defined(RE4DC_SHADOW_BLOB) && RE4DC_SHADOW_BLOB
        if(p.projection[0]==0 && p.viewport[2]>0 && p.viewport[3]>0 && re4dc_blob_camera_frame!=re4dc_ui_frame()){
            std::memcpy(re4dc_blob_projection,p.projection,sizeof(re4dc_blob_projection));
            std::memcpy(re4dc_blob_viewport,p.viewport,sizeof(re4dc_blob_viewport));
            re4dc_blob_camera_frame=re4dc_ui_frame();
        }
#endif
#if RE4DC_MESH_DIRECT
        if(direct){
            Re4dcModelDirect out{};
#if RE4DC_PS2_WORLD_MESH
#if RE4DC_SCENERY_PIECE_STATE
            re4dc_ps2_piece_slot=ps2?piece_slot:nullptr;
#if RE4DC_SCENERY_SUBMIT_BATCH
            const int begun=ps2?(submit_batch?re4dc_ps2_world_direct_begin_batch(ps2,&out,submit_batch):
                                re4dc_ps2_world_direct_begin(ps2,&out)):re4dc_model_direct_begin(&p,&out);
#else
            const int begun=ps2?re4dc_ps2_world_direct_begin(ps2,&out):re4dc_model_direct_begin(&p,&out);
#endif
            re4dc_ps2_piece_slot=nullptr;
            if(!begun)return false;
#else
#if RE4DC_SCENERY_SUBMIT_BATCH
            if(!(ps2?(submit_batch?re4dc_ps2_world_direct_begin_batch(ps2,&out,submit_batch):
                                  re4dc_ps2_world_direct_begin(ps2,&out)):re4dc_model_direct_begin(&p,&out)))return false;
#else
            if(!(ps2?re4dc_ps2_world_direct_begin(ps2,&out):re4dc_model_direct_begin(&p,&out)))return false;
#endif
#endif
#else
            if(!re4dc_model_direct_begin(&p,&out))return false;
#endif
            sq=out.sq;submitted=true;
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
            if(!re4dc_source_world_binding_valid()){
#if RE4DC_SCENERY_SUBMIT_BATCH
                end_direct();
                if(submit_batch)re4dc_ps2_world_batch_close(submit_batch);
                re4dc_source_world_binding_failed();return false;
#else
                end_direct();re4dc_source_world_binding_failed();return false;
#endif
            }
#endif
#if RE4DC_PS2_WORLD_R11F_OWNER
            if(!re4dc_r11f_binding_valid()) {
#if RE4DC_SCENERY_SUBMIT_BATCH
                end_direct();
                if(submit_batch)re4dc_ps2_world_batch_close(submit_batch);
                re4dc_r11f_binding_failed();return false;
#else
                end_direct();re4dc_r11f_binding_failed();return false;
#endif
            }
#endif
            packet.vertices=out.scratch;packet.capacity=out.scratch_capacity;
            packet.u_scale=out.u_scale;packet.v_scale=out.v_scale;
            dst=static_cast<pvr_vertex_t*>(out.scratch);bound=true;limit=out.scratch_capacity;
            load_screen(mvq,p.projection,p.viewport); // binding may yield
            return true;
        }
#endif
        if(!re4dc_model_packet_begin(&p,&packet))return false;
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
        if(!re4dc_source_world_binding_valid()){re4dc_source_world_binding_failed();return false;}
#endif
#if RE4DC_PS2_WORLD_R11F_OWNER
        if(!re4dc_r11f_binding_valid()){re4dc_r11f_binding_failed();return false;}
#endif
        dst=static_cast<pvr_vertex_t*>(packet.vertices);bound=true;limit=packet.capacity;
        load_screen(mvq,p.projection,p.viewport); // binding may yield
        return true;
    }
    bool flush(){
        if(!streaming || !used)return false;
        re4dc_model_packet_commit(used);submitted=true;used=0;
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
        if(!re4dc_source_world_binding_valid()){re4dc_source_world_binding_failed();return false;}
#endif
        load_screen(mvq,p.projection,p.viewport);
        return true;
    }
    float u(float value)const{return (value+p.uv_offset[0])*packet.u_scale;}
    float v(float value)const{return (value+p.uv_offset[1])*packet.v_scale;}
    // AoS12 corners stay in grid units: mvq folds origin + q * step in, so the
    // per-corner cost is three integer conversions, not a dequantize.
    re4dc::render::StaticCorner corner(const re4dc::room::CompactVertex& in)const{
        return {in.x,in.y,in.z,in.u,in.v,in.argb};
    }
    // Packages index a palette; lit meshes (palette==nullptr) store ARGB1555.
    [[gnu::always_inline]] static std::uint32_t argb1555(std::uint16_t c){
        const std::uint32_t r=(c>>10)&31U,g=(c>>5)&31U,b=c&31U;
        return ((c&0x8000U)?0xff000000U:0U)|(((r<<3)|(r>>2))<<16)|(((g<<3)|(g>>2))<<8)|((b<<3)|(b>>2));
    }
    // Per corner: this unit is -Os, which otherwise keeps the decode out of line.
#if RE4DC_PS2_VERTEX_ALPHA
    // PS2_VERTEX_ALPHA (game30.mk): a marked PS2 world part stores ARGB4444 corner colours (the vertex alpha).
    bool c4444=false;
    [[gnu::always_inline]] static std::uint32_t argb4444(std::uint16_t c){
        return ((c>>12)&15U)*0x11000000U|((c>>8)&15U)*0x110000U|((c>>4)&15U)*0x1100U|(c&15U)*0x11U;
    }
    [[gnu::always_inline]] re4dc::render::StaticCorner corner(const re4dc::room::CompactVertex12& in)const{
#if RE4DC_SCENERY_DEDUP==3
        const auto& xyz=re4dc::room::MeshPackage::offline_position(dd_base,dd_unique,dd_count,in);
        return {float(xyz.x),float(xyz.y),float(xyz.z),in.u,in.v,
                palette?palette[in.color]:c4444?argb4444(in.color):argb1555(in.color)};
#else
        return {float(in.x),float(in.y),float(in.z),in.u,in.v,
                palette?palette[in.color]:c4444?argb4444(in.color):argb1555(in.color)};
#endif
    }
#else
    [[gnu::always_inline]] re4dc::render::StaticCorner corner(const re4dc::room::CompactVertex12& in)const{
#if RE4DC_SCENERY_DEDUP==3
        const auto& xyz=re4dc::room::MeshPackage::offline_position(dd_base,dd_unique,dd_count,in);
        return {float(xyz.x),float(xyz.y),float(xyz.z),in.u,in.v,palette?palette[in.color]:argb1555(in.color)};
#else
        return {float(in.x),float(in.y),float(in.z),in.u,in.v,palette?palette[in.color]:argb1555(in.color)};
#endif
    }
#endif
    void clip_vertex(const re4dc::render::StaticCorner& in,const re4dc::room::CompactBatch& batch,
                     re4dc::render::RenderVertex& out){
        float x=mvq[0]*in.x+mvq[1]*in.y+mvq[2]*in.z+mvq[3];
        float y=mvq[4]*in.x+mvq[5]*in.y+mvq[6]*in.z+mvq[7];
        float z=mvq[8]*in.x+mvq[9]*in.y+mvq[10]*in.z+mvq[11];
#if RE4DC_COPY_LEAN
        out.offset_color=0; // every other field is assigned below (no 52-byte memset per corner)
#else
        out={};
#endif
        out.position.world_x=x;out.position.world_y=y;out.position.world_z=z;out.position.depth=-z;
        if(z!=0)project(x,y,z,this);
        out.position.x=x;out.position.y=y;out.position.z=z;
        out.u=u(batch.uv_bias[0]+float(in.u)*batch.uv_scale[0]);
        out.v=v(batch.uv_bias[1]+float(in.v)*batch.uv_scale[1]);
        out.light_red=float((in.argb>>16)&255U)RE4DC_INV255;
        out.light_green=float((in.argb>>8)&255U)RE4DC_INV255;
        out.light_blue=float(in.argb&255U)RE4DC_INV255;
    }
    // 1 emitted/culled, 0 failed before anything was published, -1 failed after.
    template<class Vertex,class Index>
    int strip(const Vertex* base,const re4dc::room::CompactBatch& batch,
              const Index* index,unsigned count){
        input+=count-2;
        if(count<=limit){
            if(count>limit-used && !flush())return submitted?-1:0;
            unsigned outside=15;
            const float screen_w=RE4DC_SCREEN_WF,screen_h=RE4DC_SCREEN_HF; // RES_MODES: one load per strip, not per corner
            const bool ready=re4dc::render::prepare_direct_strip(dst+used,count,near,far,
                [&](std::uint32_t local,re4dc::render::DirectStripVertex& out){
                    out=re4dc::render::prepare_static_vertex(corner(base[index[local]]),batch,0.0f);
                    out.u=u(out.u);out.v=v(out.v);
                    if(!vertex_alpha)out.argb=(out.argb&0xffffffU)|alpha;
                    outside&=(out.x<0?1U:0U)|(out.x>screen_w?2U:0U)|(out.y<0?4U:0U)|(out.y>screen_h?8U:0U);
                    return true;
                });
            stats.vertices+=count;
            if(ready){
                if(outside)++stats.strips_culled;
#if RE4DC_MESH_DIRECT
                else if(sq){put(count);output+=count-2;++stats.strips;}
#endif
                else {used+=count;output+=count-2;++stats.strips;}
                return 1;
            }
        }
        return clip_strip(base,batch,index,count);
    }
    // Near/far crossing or oversize: the shared clipper, triangle by triangle,
    // keeping strip winding (odd triangles swap their first two corners).
    // input was already counted by the caller.
    template<class Vertex,class Index>
    int clip_strip(const Vertex* base,const re4dc::room::CompactBatch& batch,
                   const Index* index,unsigned count){
        ++stats.strips_clipped;
        float alphas[3]={float(alpha>>24)RE4DC_INV255,float(alpha>>24)RE4DC_INV255,float(alpha>>24)RE4DC_INV255};
#if RE4DC_MESH_CLIP_LEAN && RE4DC_HW_LEAN && defined(__sh__)
        // MESH_CLIP_LEAN (exact in pixels). 1) A strip whose corners are all outside one plane of the
        // frustum {0<=X<=640W, 0<=Y<=480W, near<=W<=far} (homogeneous screen coordinates, W=-z; the
        // test holds behind the camera too, the region being convex) draws nothing: the clipper would
        // only produce triangles off that screen edge or outside near/far. 2) Each corner goes through
        // clip_vertex once, not once per triangle that uses it (the same values, reused).
        {
            const float* pp=p.projection;
            const float screen_w=RE4DC_SCREEN_WF,screen_h=RE4DC_SCREEN_HF,half_w=RE4DC_SCREEN_HALF_WF,half_h=RE4DC_SCREEN_HALF_HF;
            unsigned all=0x3fU;
            for(unsigned i=0;i<count && all;++i){
                const auto c=corner(base[index[i]]);
                const float x=mvq[0]*c.x+mvq[1]*c.y+mvq[2]*c.z+mvq[3];
                const float y=mvq[4]*c.x+mvq[5]*c.y+mvq[6]*c.z+mvq[7];
                const float z=mvq[8]*c.x+mvq[9]*c.y+mvq[10]*c.z+mvq[11];
                const float W=-z;
                const float X=half_w*(pp[1]*x+pp[2]*z)+proj_bx*W, Y=-half_h*(pp[3]*y+pp[4]*z)+proj_by*W;
                all&=(X<0.0f?1U:0U)|(X>screen_w*W?2U:0U)|(Y<0.0f?4U:0U)|(Y>screen_h*W?8U:0U)|
                     (W<near?16U:0U)|(W>far?32U:0U);
            }
            if(all){++stats.strips_culled;return 1;}
        }
#if RE4DC_MESH_CLIP_ACCEPT
        // MESH_CLIP_ACCEPT (game30.mk; the same TA words). Corner i goes through clip_vertex once, into a ring of the
        // strip's last three corners (s2 = i-2, s1 = i-1, s0 = i; any strip length), and is packed at most once the
        // way clip_projected_triangle writes an accepted corner (shade_color, then the alpha byte from the same float).
        // Per triangle (strip winding: odd triangles swap their first two corners), the clipper's own cases:
        // all three corners at depth >= near = its accept (the same beyond-far and triangle_visible_xy tests, then
        // the packed corners, EOL on the third), none = it emits nothing, a crossing = clip_projected_triangle.
        if(RE4DC_CLIP_ACCEPT_ON){
            re4dc::render::RenderVertex ring[3];float ring_alpha[3];
            // A corner is packed (8 words) the first time an accepted triangle uses it; corners of dropped and
            // crossing triangles never are.
            typedef std::uint32_t __attribute__((may_alias)) Word;
            alignas(4) Word packed[3][8];bool is_packed[3];
            const auto pack=[&](unsigned s){
                if(is_packed[s])return;
                is_packed[s]=true;
                // pvr_geometry.cpp's shade_color and alpha byte, inline: static_cast<uint32_t>(std::clamp(f*255, 0, 255)).
                const auto byte=[](float f){const float x=f*255.0f;return static_cast<std::uint32_t>(x<0.0f?0.0f:255.0f<x?255.0f:x);};
                const re4dc::render::RenderVertex& r=ring[s];Word* w=packed[s];
                w[0]=PVR_CMD_VERTEX;w[1]=__builtin_bit_cast(std::uint32_t,r.position.x);w[2]=__builtin_bit_cast(std::uint32_t,r.position.y);
                w[3]=__builtin_bit_cast(std::uint32_t,r.position.z);w[4]=__builtin_bit_cast(std::uint32_t,r.u);w[5]=__builtin_bit_cast(std::uint32_t,r.v);
                w[6]=(byte(ring_alpha[s])<<24U)|(byte(r.light_red)<<16U)|(byte(r.light_green)<<8U)|byte(r.light_blue);
                w[7]=r.offset_color;
            };
            const float near_d=clip.near_distance,far_d=clip.far_distance;
            unsigned s2=0,s1=1,s0=2;
            for(unsigned i=0;i<count;++i){
                {const unsigned t=s2;s2=s1;s1=s0;s0=t;}
                const re4dc::render::StaticCorner c=corner(base[index[i]]);
                re4dc::render::RenderVertex& v=ring[s0];
                clip_vertex(c,batch,v);
                ring_alpha[s0]=vertex_alpha?float(c.argb>>24)RE4DC_INV255:alphas[0];
                is_packed[s0]=false;
                if(i<2)continue;
                const unsigned ia=(i&1)?s1:s2,ib=(i&1)?s2:s1;
                if(limit-used<6 && !flush())return submitted?-1:0;
                const re4dc::render::RenderVertex& va=ring[ia];const re4dc::render::RenderVertex& vb=ring[ib];
                const unsigned inside=(va.position.depth>=near_d?1U:0U)+(vb.position.depth>=near_d?1U:0U)+(v.position.depth>=near_d?1U:0U);
                unsigned emitted=0;
                if(inside==3U){
                    if(!(va.position.depth>far_d && vb.position.depth>far_d && v.position.depth>far_d) &&
                       re4dc::render::triangle_visible_xy(va.position,vb.position,v.position,p.cull,clip.width,clip.height)){
                        pack(ia);pack(ib);pack(s0);
                        Word* o=reinterpret_cast<Word*>(dst+used);
                        for(unsigned k=0;k<8;++k){o[k]=packed[ia][k];o[8+k]=packed[ib][k];o[16+k]=packed[s0][k];}
                        o[16]=PVR_CMD_VERTEX_EOL;
                        emitted=1;
                    }
                }else if(inside){
                    const re4dc::render::RenderVertex tri[3]={va,vb,v};
                    const float ta[3]={ring_alpha[ia],ring_alpha[ib],ring_alpha[s0]};
                    emitted=re4dc::render::clip_projected_triangle(tri,dst+used,p.cull,clip,nullptr,ta);
                }
#if RE4DC_MESH_CLIP_ACCEPT==2
                if(inside==3U || !inside){
                    // The clipper on the same corners into scratch: the same triangle count and words.
                    alignas(32) pvr_vertex_t ref[6];
                    const re4dc::render::RenderVertex tri[3]={va,vb,v};
                    const float ta[3]={ring_alpha[ia],ring_alpha[ib],ring_alpha[s0]};
                    const unsigned n=re4dc::render::clip_projected_triangle(tri,ref,p.cull,clip,nullptr,ta);
                    ++clip_accept_stats[inside?0:1];
                    if((n!=emitted || (n && std::memcmp(ref,dst+used,3*sizeof(pvr_vertex_t)))) && ++clip_accept_stats[2]<=8)
                        re4dc_log("CLIPACC mismatch inside=%u n=%u/%u\n",inside,emitted,n);
                }else ++clip_accept_stats[3];
#endif
#if RE4DC_MESH_DIRECT
                if(sq){if(emitted)put(emitted*3);output+=emitted;stats.triangles_clipped+=emitted;continue;}
#endif
                used+=emitted*3;output+=emitted;stats.triangles_clipped+=emitted;
            }
            return 1;
        }
#endif
        if(count<=kClipOnce){
            re4dc::render::RenderVertex once[kClipOnce];float once_alpha[kClipOnce];
            for(unsigned i=0;i<count;++i){
                const re4dc::render::StaticCorner c=corner(base[index[i]]);
                clip_vertex(c,batch,once[i]);
                once_alpha[i]=vertex_alpha?float(c.argb>>24)RE4DC_INV255:alphas[0];
            }
            for(unsigned i=2;i<count;++i){
                const unsigned ia=i-2+(i&1),ib=i-1-(i&1);
                const re4dc::render::RenderVertex tri[3]={once[ia],once[ib],once[i]};
                const float ta[3]={once_alpha[ia],once_alpha[ib],once_alpha[i]};
                if(limit-used<6 && !flush())return submitted?-1:0;
                const unsigned emitted=re4dc::render::clip_projected_triangle(tri,dst+used,p.cull,clip,nullptr,ta);
#if RE4DC_MESH_DIRECT
                if(sq){if(emitted)put(emitted*3);output+=emitted;stats.triangles_clipped+=emitted;continue;}
#endif
                used+=emitted*3;output+=emitted;stats.triangles_clipped+=emitted;
            }
            return 1;
        }
#endif
        for(unsigned i=2;i<count;++i){
            re4dc::render::RenderVertex tri[3];
            const re4dc::render::StaticCorner corners[3]={corner(base[index[i-2+(i&1)]]),
                corner(base[index[i-1-(i&1)]]),corner(base[index[i]])};
            for(unsigned k=0;k<3;++k){
                clip_vertex(corners[k],batch,tri[k]);
                if(vertex_alpha)alphas[k]=float(corners[k].argb>>24)RE4DC_INV255;
            }
            if(limit-used<6 && !flush())return submitted?-1:0;
            const unsigned emitted=re4dc::render::clip_projected_triangle(tri,dst+used,p.cull,clip,nullptr,alphas);
#if RE4DC_MESH_DIRECT
            if(sq){if(emitted)put(emitted*3);output+=emitted;stats.triangles_clipped+=emitted;continue;}
#endif
            used+=emitted*3;output+=emitted;stats.triangles_clipped+=emitted;
        }
        return 1;
    }
};
struct MeshDraw:Emitter {
    const re4dc::room::MeshPackage& package;const re4dc::room::MeshPart& part;
    const std::uint32_t* lut;re4dc::room::CompactVertex12* gather_pool;
    bool lean_inside=false,lean_part=false;const float* lean_am=nullptr;
    const std::uint8_t* sg=nullptr;unsigned sg_groups=0;
    unsigned pc_mode=0;const float* pc_wq=nullptr;bool pc_all=false,pc_check=false;
    float cull_far=0,lod_scale=0;unsigned part_index=0;
    re4dc::room::CompactBatch batch{};
    re4dc::room::CompactVertex12* gathered=nullptr;
    pvr_vertex_t* cache=nullptr;std::uint8_t* outcodes=nullptr;
    re4dc::vp::Constants k{};unsigned primed=0;
    bool borrow_gather(){
        if(gathered || !package.shared())return true;
        gathered=gather_pool;
        return gathered!=nullptr;
    }
    const re4dc::room::CompactVertex12* corners(const re4dc::room::Meshlet& l){
        const auto* base=package.vertices()+l.first_vertex;
#if RE4DC_SCENERY_DEDUP==3
        const unsigned rep=package.repeat_count(l);
        dd_base=rep?base:nullptr;dd_unique=l.vertex_count-rep;dd_count=l.vertex_count;
#endif
        if(!package.indexed(l))return base;
        // Three word moves per corner: R4IM vertices are 4-byte aligned.
        typedef std::uint32_t __attribute__((may_alias)) Word;
        const std::uint16_t* offsets=package.pool_offsets(l);
        const Word* in=reinterpret_cast<const Word*>(base);Word* out=reinterpret_cast<Word*>(gathered);
        for(unsigned k=0;k<l.vertex_count;++k,out+=3){
            const Word* c=in+3U*offsets[k];
            out[0]=c[0];out[1]=c[1];out[2]=c[2];
        }
        return gathered;
    }
    bool borrow(){
        if(cache)return true;
        if(!lut || limit<re4dc::vp::kCacheSlots+64U)return false; // small slab: per-corner path
        limit-=re4dc::vp::kCacheSlots;
        cache=dst+limit;outcodes=reinterpret_cast<std::uint8_t*>(cache+re4dc::vp::kCacheEntries);
#if RE4DC_WORLD_SCRATCH
        // Outcodes and all 264 packet slots remain in the original RAM tail.
        // The only relocated storage is the projected record array, for PS2 world.
        if(ps2){
            void* selected=cache;
            const int borrowed=re4dc_world_scratch_acquire(cache,&selected);
            if(borrowed<0){re4dc_model_packet_abort();return false;}
            if(borrowed){
                cache=static_cast<pvr_vertex_t*>(selected);scratch_borrowed=true;
                // acquire resets retained prime state on each mode/storage epoch.
                // The unchanged prime below (or lazy per-entry prime) initializes
                // flags and oargb before any projected entry can be consumed.
            }
        }
#endif
#if !RE4DC_MESH_PRIME_LAZY
        re4dc::vp::prime(cache,re4dc::vp::kCacheEntries);
#endif
#if RE4DC_PS2_WORLD_LEAN && RE4DC_MESH_PRIME_LAZY
        if((lean::kMode&4U) && lean_part && cache==lean::prime_at){
            primed=lean::primed;++lean::st.prime_reuse;
            if(lean::kMode&8U)for(unsigned i=0;i<primed;++i)
                if(cache[i].flags!=PVR_CMD_VERTEX || cache[i].oargb!=0){++lean::st.prime_bad;primed=0;break;}
        }
#endif
        // After bind(): packet.u_scale/v_scale are the bound texture's.
        k={part.uv_scale[0],part.uv_bias[0],p.uv_offset[0],packet.u_scale,
           part.uv_scale[1],part.uv_bias[1],p.uv_offset[1],packet.v_scale,near,far,
           vertex_alpha?~0U:0x00ffffffU,vertex_alpha?0U:alpha,lut,{}};
#if RE4DC_PS2_INTERIOR_CULL==2
        if(pc_check){k.and_mask=0;k.or_bits=0xffff00ffU;} // the check run: every corner opaque magenta
#endif
        k.finish();
        return true;
    }
std::uint32_t dd_word(const re4dc::room::Meshlet& l)const{
#if RE4DC_SCENERY_DEDUP==3
        (void)l;
        return (dd_count-dd_unique)<<24;
#else
        return dedup::pkg==static_cast<const void*>(&package)?dedup::lets[&l-package.meshlets()]:0U;
#endif
    }
const std::uint8_t* dd_source(const re4dc::room::Meshlet& l,std::uint32_t dw)const{
#if RE4DC_SCENERY_DEDUP==3
        (void)l;(void)dw;
        return reinterpret_cast<const std::uint8_t*>(dd_base+dd_unique);
#else
        (void)l;return dedup::src+(dw&0xffffffU);
#endif
    }
bool dd_active(std::uint32_t dw)const{
#if RE4DC_SCENERY_DEDUP==3
        (void)dw;return dd_base!=nullptr;
#else
        return dw>>24;
#endif
    }
unsigned dd_unique_count(const re4dc::room::Meshlet& l,std::uint32_t dw)const{
#if RE4DC_SCENERY_DEDUP==3
        (void)l;(void)dw;return dd_unique;
#else
        return l.vertex_count-(dw>>24);
#endif
    }
    void lean_flush(const std::uint8_t* s,const std::uint8_t* mark,std::uint32_t* q,const std::uint32_t* qmark,
                    unsigned culled,unsigned emitted){
        const unsigned strips=culled+emitted,sum=unsigned(s-mark)-strips,v=unsigned(q-qmark)/8U;
        input+=sum-2U*strips;stats.vertices+=sum;stats.strips_culled+=culled;stats.strips+=emitted;
        slots+=v;output+=v-2U*emitted;sq=q;
    }
    const std::uint8_t* strips_lean(const std::uint8_t* s,const std::uint8_t* end,const re4dc::room::CompactVertex12* base,
                                    const re4dc::room::CompactBatch& batch,int& result){
#if defined(RE4DC_CPU_BACKFACE) && RE4DC_CPU_BACKFACE == 2
        if(bf_on())return strips_bf_sq(s,end,base,batch,result);
#elif defined(RE4DC_CPU_BACKFACE) && RE4DC_CPU_BACKFACE
        if(bf_on())return strips_bf(s,end,base,batch,result);
#endif
        for(;;){
            const std::uint8_t* const mark=s;std::uint32_t* q=sq;const std::uint32_t* const qmark=q;
            unsigned culled=0,emitted=0;
            s=re4dc::vp::walk_lean(s,end,outcodes,cache,limit,q,culled,emitted);
#if defined(RE4DC_TA_HASH) && RE4DC_TA_HASH && RE4DC_TA_HASH != 4
            // TA_HASH (test builds): walk_lean writes the store queues itself, so the run is walked again here
            // and every emitted strip's words are hashed as emit_sq() hashes them (EOL in the last flags word).
            // Every strip in [mark, s) was culled or emitted (walk_lean stops before a clip strip).
            for(const std::uint8_t* h=mark;h<s;){
                const unsigned n=*h++;const re4dc::vp::StripCodes c=re4dc::vp::codes(outcodes,h,n);
                if(!(c.all&(re4dc::vp::depth_mask(re4dc::vp::kChecksAll)|re4dc::vp::screen_mask(re4dc::vp::kChecksAll))))
                    for(unsigned k=0;k<n;++k){
                        std::uint32_t w[8];__builtin_memcpy(w,cache+h[k],32);
                        if(k+1==n)w[0]=PVR_CMD_VERTEX_EOL;
                        ::re4dc_ta_hash(w,32);
                    }
                h+=n;
            }
#endif
            lean_flush(s,mark,q,qmark,culled,emitted);
            if(s>=end){result=1;return nullptr;}
            const unsigned n=*s++; // a strip for the clipper: meshlet()'s code
            input+=n-2;
            if(n<=limit)stats.vertices+=n;
            result=clip_strip(base,batch,s,n);
            if(result<=0)return nullptr;
            s+=n;
        }
    }
    struct Pick {
        std::uint16_t let;            // meshlet index in the package
        std::uint8_t nr,gmask,lo,hi;  // nr 0xff: the whole meshlet; else the strip groups left (gmask: group bits)
        std::uint8_t pad[2];
    };
        // Only immutable package input is hinted. No binding, matrix, material or
    // scratch ownership is carried across the next part's bind (which may yield).
    static void emit_prefetch_span(const void* ptr,unsigned bytes){
        const auto* p=static_cast<const std::uint8_t*>(ptr);
        __builtin_prefetch(p);
        if((reinterpret_cast<std::uintptr_t>(p)&31U)+bytes>32U)
            __builtin_prefetch(p+bytes-1U);
    }
    void prefetch_emit_header(const Pick& pk)const{
        // Meshlet has a 28-byte stride; only the first 16 bytes feed emission.
        emit_prefetch_span(package.meshlets()+pk.let,16U);
    }
    void prefetch_emit_payload(const Pick& pk)const{
        if(!pk.nr)return;
        const auto& l=package.meshlets()[pk.let];
        const auto* base=package.vertices()+l.first_vertex;
        const auto* raw=package.strips()+l.first_strip;
        if(package.indexed(l)){
            const auto* offsets=reinterpret_cast<const std::uint16_t*>(raw);
            __builtin_prefetch(offsets);
            // The pool base need not be referenced by this meshlet. Warm the
            // first corner actually gathered, not vertex zero of the part pool.
            emit_prefetch_span(base+offsets[0],sizeof(*base));
            raw+=2U*l.vertex_count;
        }else{
            // The transform already streams three vertices ahead. Seed only
            // its first (at most) three inputs, including a partial pick's lo.
            const unsigned first=pk.nr==0xffU?0U:pk.lo;
            const unsigned count=pk.nr==0xffU?l.vertex_count:unsigned(pk.hi-pk.lo)+1U;
            if(first>=l.vertex_count || count>l.vertex_count-first)return;
            emit_prefetch_span(base+first,(count<3U?count:3U)*sizeof(*base));
        }
        if(pk.nr==0xffU)__builtin_prefetch(raw);
        else if(sg)__builtin_prefetch(sg+16U*sg_groups*pk.let);
    }
    const re4dc::room::CompactVertex12* emit_corners(const re4dc::room::Meshlet& l,const Pick& pk){
        const auto* base=package.vertices()+l.first_vertex;
#if RE4DC_SCENERY_DEDUP==3
        // Match corners(): refresh or clear the decoder before every early return.
        const unsigned rep=package.repeat_count(l);
        dd_base=rep?base:nullptr;dd_unique=l.vertex_count-rep;dd_count=l.vertex_count;
#endif
        if(!package.indexed(l))return base;
        if(!pk.nr)return gathered; // bind/borrow/prime still run; no consumer for this pick
        // Keep the full gather for nonempty partial picks: the runtime R4SG
        // reader has not proved that group lo/hi encloses every clipper input,
        // and DEDUP's fill can read corners outside that interval. Hoist the
        // immutable count before may-alias stores instead of rereading it.
        const unsigned count=l.vertex_count;
        typedef std::uint32_t __attribute__((may_alias)) Word;
        const std::uint16_t* offsets=package.pool_offsets(l);
        const Word* in=reinterpret_cast<const Word*>(base);
        Word* out=reinterpret_cast<Word*>(gathered);
        for(unsigned k=0;k<count;++k,out+=3){
            const Word* c=in+3U*offsets[k];
            out[0]=c[0];out[1]=c[1];out[2]=c[2];
        }
        return gathered;
    }
    
int emit_pick(const Pick& pk){
        namespace vp=re4dc::vp;
        ++stats.groups_visible;
        if(!bind()){++stats.bind_rejects;return submitted?-1:0;}
        ++stats.batches;
        if(!borrow_gather()){++stats.reserve_rejects;return submitted?-1:0;}
        if(!borrow()){++stats.reserve_rejects;return submitted?-1:0;}
        const auto& l=package.meshlets()[pk.let];
#if defined(RE4DC_SCN_CENSUS) && RE4DC_SCN_CENSUS
        struct CenScope {
            const Emitter* e;unsigned n,s0,c0,o0,v0;
            ~CenScope(){
                const unsigned es=stats.strips-s0,cs=stats.strips_culled-c0;
                scn_cen[0]++;scn_cen[1]+=n;if(!es)scn_cen[2]+=n;scn_cen[3]+=es;scn_cen[4]+=cs;scn_cen[5]+=e->output-o0;
                if(!es && cs)scn_cen[6]++;
            }
        } cen{this,l.vertex_count,stats.strips,stats.strips_culled,output,0};
#endif
#if RE4DC_SCENERY_EMIT_PREFETCH
        const auto* base=emit_corners(l,pk);
#else
        const auto* base=corners(l);
#endif
        const auto* in=reinterpret_cast<const vp::Vertex12*>(base);
        if(l.vertex_count>primed){vp::prime(cache+primed,l.vertex_count-primed);primed=l.vertex_count;
            if(lean_part){lean::prime_at=cache;lean::primed=primed;}
        }
        const std::uint8_t* const sb=package.strip_begin(l);
        if(pk.nr!=0xffU){
#if defined(RE4DC_SCN_CENSUS) && RE4DC_SCN_CENSUS
            cen.n=pk.nr?pk.hi-pk.lo+1U:0U;  // corners transformed (the strip groups left)
#endif
            if(!pk.nr)return 1;
            const unsigned vn=pk.hi-pk.lo+1U;
            vp::transform_sched<vp::kChecksAll>(in+pk.lo,vn,cache+pk.lo,outcodes+pk.lo,k);
#if defined(RE4DC_WORLD_METER) && RE4DC_WORLD_METER
            if(ps2)re4dc_wm_corners(outcodes+pk.lo,vn,0x3fU);
#endif
#if RE4DC_SCENERY_DEDUP
            if(const std::uint32_t dw=dd_word(l);dd_active(dw))
                dedup::fill(in,cache,outcodes,dd_unique_count(l,dw),l.vertex_count,dd_source(l,dw),k,pk.lo,pk.hi);
#endif
            const auto* g=reinterpret_cast<const std::uint16_t*>(sg+16U*sg_groups*pk.let);
            unsigned prev=0;
            for(unsigned q=0;q<sg_groups;++q){
                const unsigned gend=g[8*q+6];
                if(gend==prev)continue;
                if((pk.gmask>>q)&1U){
                    int result=1;
                    strips_lean(sb+prev,sb+gend,base,batch,result);
                    if(result<=0)return result;
                }
                prev=gend;
            }
            return 1;
        }
#if RE4DC_SCENERY_DEDUP
        if(const std::uint32_t dw=dd_word(l);dd_active(dw)){
            const unsigned u=dd_unique_count(l,dw);
            vp::transform_sched<vp::kChecksAll>(in,u,cache,outcodes,k);
            dedup::fill(in,cache,outcodes,u,l.vertex_count,dd_source(l,dw),k);
        }else
#endif
        vp::transform_sched<vp::kChecksAll>(in,l.vertex_count,cache,outcodes,k);
#if defined(RE4DC_WORLD_METER) && RE4DC_WORLD_METER
        if(ps2){
            unsigned count=l.vertex_count;
#if RE4DC_SCENERY_DEDUP
            if(const std::uint32_t dw=dd_word(l);dw>>24)count-=dw>>24;
#endif
            re4dc_wm_corners(outcodes,count,0x3fU);
        }
#endif
        int result=1;
        strips_lean(sb,sb+l.strip_bytes,base,batch,result);
#if RE4DC_PS2_PVS
        if(result>0)pvs_observed(l);
#endif
        return result;
    }
    #if RE4DC_SCENERY_REPLAY_LEAN
[[gnu::always_inline]] void chunk_restart(){
        used=input=output=slots=0;
        bound=submitted=false;
        cache=nullptr;primed=0;
#if RE4DC_PS2_PVS
        pvs_pending[0]=pvs_pending[1]=~0U;pvs_pending[2]=0;
#endif
    }
#endif
    __attribute__((noinline)) int chunk_emit(const Pick* pk,unsigned n,const Pick* following=nullptr){
#if RE4DC_SCENERY_EMIT_PREFETCH
        if(n>1U)prefetch_emit_header(pk[1]);
        else if(n && following)prefetch_emit_header(*following);
#endif
#if !RE4DC_SCENERY_REPLAY_LEAN
        streaming=re4dc_model_packet_streaming()!=0;
        set_clip();
        palette=nullptr;
#endif
        batch.uv_bias[0]=part.uv_bias[0];batch.uv_bias[1]=part.uv_bias[1];
        batch.uv_scale[0]=part.uv_scale[0];batch.uv_scale[1]=part.uv_scale[1];
        for(unsigned i=0;i<n;++i){
#if RE4DC_SCENERY_EMIT_PREFETCH
            // Two selected headers ahead; one payload ahead. The current
            // transform plus its strips supplies the lead time. following is
            // the next queued part's first pick, still in this package/run.
            if(i+2U<n)prefetch_emit_header(pk[i+2U]);
            else if(i+2U==n && following)prefetch_emit_header(*following);
            if(i+1U<n)prefetch_emit_payload(pk[i+1U]);
            else if(following)prefetch_emit_payload(*following);
#elif defined(RE4DC_PREF_WALK) && RE4DC_PREF_WALK
            // PREF_WALK (cache20.h): the next pick's corners and first strip bytes while this one is transformed / sent
            if(i+1<n && RE4DC_C20_PREF_ON()){
                const auto& nl=package.meshlets()[pk[i+1].let];
                RE4DC_C20_PREF(package.vertices()+nl.first_vertex);RE4DC_C20_PREF(package.strip_begin(nl));
            }
#endif
            const int r=emit_pick(pk[i]);if(r<=0)return r;}
        if(used)re4dc_model_packet_commit(used);
        re4dc_model_result(0,input,output);
        return 1;
    }
};

// Two meshlets per part, eight vertices and two four-corner strips each.
// v3 additionally exercises indexed gather and preserved gather ownership.
static std::vector<std::uint8_t> make_package(unsigned version){
    using namespace re4dc::room;
    MeshHeader h{};std::memcpy(h.magic,"R4IM",4);h.version=version;
    h.mesh_count=1;h.part_count=8;h.meshlet_count=16;h.vertex_count=128;h.palette_count=1;
    h.strip_bytes=16*(version==3?26U:10U);h.reserved[0]=kColorArgb1555;
    unsigned at=sizeof(h)+(version>=2?sizeof(MeshLodHeader):0);
    const auto section=[&](unsigned count,unsigned bytes){at=(at+3)&~3U;unsigned result=at;at+=count*bytes;return result;};
    h.mesh_offset=section(1,sizeof(MeshRecord));h.part_offset=section(8,sizeof(MeshPart));
    h.meshlet_offset=section(16,sizeof(Meshlet));h.vertex_offset=section(128,sizeof(CompactVertex12));
    h.strip_offset=section(h.strip_bytes,1);h.palette_offset=section(1,4);
    MeshLodHeader lod{};
    if(version>=2){lod.cluster_count=lod.level_count=8;lod.part_lod_offset=section(8,sizeof(MeshPartLod));
        lod.cluster_offset=section(8,sizeof(MeshCluster));lod.level_offset=section(8,sizeof(MeshLevel));}
    h.bytes=at;std::vector<std::uint8_t> data(at);std::memcpy(data.data(),&h,sizeof(h));
    if(version>=2)std::memcpy(data.data()+sizeof(h),&lod,sizeof(lod));
    auto& record=*reinterpret_cast<MeshRecord*>(data.data()+h.mesh_offset);record.part_count=record.source_parts=8;
    record.step[0]=record.step[1]=record.step[2]=1;
    auto* parts=reinterpret_cast<MeshPart*>(data.data()+h.part_offset);
    auto* lets=reinterpret_cast<Meshlet*>(data.data()+h.meshlet_offset);
    auto* vertices=reinterpret_cast<CompactVertex12*>(data.data()+h.vertex_offset);
    const unsigned xyz[8][3]={{0,0,0},{2,0,0},{0,2,2},{2,2,2},{3,3,4},{5,3,4},{3,5,0},{5,5,0}};
    for(unsigned i=0;i<8;++i){auto& p=parts[i];p.first_meshlet=2*i;p.meshlet_count=2;
        p.uv_bias[0]=float(i)*.125f;p.uv_bias[1]=-float(i)*.25f;
        p.uv_scale[0]=(i+1)*.0625f;p.uv_scale[1]=(i+1)*.03125f;
        if(version>=2){auto* pl=reinterpret_cast<MeshPartLod*>(data.data()+lod.part_lod_offset);pl[i]={i,1};
            auto* cl=reinterpret_cast<MeshCluster*>(data.data()+lod.cluster_offset);cl[i].first_level=i;cl[i].level_count=1;
            auto* lv=reinterpret_cast<MeshLevel*>(data.data()+lod.level_offset);lv[i].first_meshlet=2*i;lv[i].meshlet_count=2;}
        for(unsigned m=0;m<2;++m){const unsigned li=2*i+m;auto& l=lets[li];l.first_vertex=version==3?i*16:li*8;
            l.first_strip=li*(version==3?26:10);l.vertex_count=8;l.strip_count=2|(version==3?kIndexedMeshlet:0);l.strip_bytes=10;
            std::uint8_t* s=data.data()+h.strip_offset+l.first_strip;
            if(version==3){auto* offsets=reinterpret_cast<std::uint16_t*>(s);for(unsigned k=0;k<8;++k)offsets[k]=m*8+k;s+=16;}
            const std::uint8_t strip[10]={4,0,1,2,3,4,4,5,6,7};std::memcpy(s,strip,10);
            for(unsigned k=0;k<8;++k)vertices[li*8+k]={std::uint16_t(xyz[k][0]),std::uint16_t(xyz[k][1]),std::uint16_t(xyz[k][2]),
                std::uint16_t(k*16),std::uint16_t(127-k*8),std::uint16_t(0x1000U*i+0x8123U+k*37U)};
        }
    }
    return data;
}
// Synthetic composition sequence only. Production methods are extracted by
// check_composition.py; no game data is embedded in this file.
static bool encoded_part(unsigned i){return i==0||i==4||i==6;}
static std::vector<std::uint8_t> composition_package(){
    using namespace re4dc::room;
    auto data=make_package(3);
    auto& h=*reinterpret_cast<MeshHeader*>(data.data());
    h.reserved[2]=0x12345678;h.reserved[3]=COMPOSITION_DECODED?0:kOfflineDedupMarker;
    auto* lets=reinterpret_cast<Meshlet*>(data.data()+h.meshlet_offset);
    auto* vertices=reinterpret_cast<CompactVertex12*>(data.data()+h.vertex_offset);
    for(unsigned i=0;i<8;++i)for(unsigned m=0;m<2;++m){
        const unsigned li=2*i+m;auto& l=lets[li];
        if(i==3)continue; // Retain real v3 indexed gather, isolated part pool.
        l.first_vertex=li*8;l.first_strip+=16;l.strip_count=2;
        if(!encoded_part(i))continue;
        auto* v=vertices+l.first_vertex;
        const unsigned refs[4]={1,2,3,1};
        for(unsigned j=4;j<8;++j){
            const auto source=v[refs[j-4]];
#if COMPOSITION_DECODED
            v[j].x=source.x;v[j].y=source.y;v[j].z=source.z;
#else
            v[j].x=std::uint16_t(refs[j-4]);v[j].y=kOfflineDedupY;v[j].z=kOfflineDedupZ;
#endif
            // Preserve distinct repeat UV/color: a real seam, not vertex dedup.
            assert(v[j].u!=source.u&&v[j].color!=source.color);
        }
#if !COMPOSITION_DECODED
        l.strip_count|=4U<<7;
#endif
    }
    return data;
}

// Compare only cache records actually consumed by selected strips. Unselected
// entries are intentionally permitted to retain prior scratch bytes.
static void observe_cache(MeshDraw& e,const MeshDraw::Pick* picks,unsigned count,int result){
    queue_events.insert(queue_events.end(),{91,e.part_index,unsigned(result),count});
    if(result<=0||!e.cache)return;
    for(unsigned pi=0;pi<count;++pi){
        const auto& pk=picks[pi];if(pk.nr==0)continue;
        const auto& l=e.package.meshlets()[pk.let];bool used[256]{};
        const auto* sb=e.package.strip_begin(l);
        for(unsigned group=0,prev=0;group<(pk.nr==255?1:e.sg_groups);++group){
            const unsigned end=pk.nr==255?l.strip_bytes:
                reinterpret_cast<const std::uint16_t*>(e.sg+16U*e.sg_groups*pk.let)[8*group+6];
            if(pk.nr==255||((pk.gmask>>group)&1U)){
                const auto* s=sb+prev;
                while(s<sb+end){const unsigned n=*s++;for(unsigned j=0;j<n;++j)used[*s++]=true;}
            }
            prev=end;
        }
        for(unsigned i=0;i<l.vertex_count;++i)if(used[i]){
            std::uint32_t words[8];std::memcpy(words,e.cache+i,32);
            queue_events.insert(queue_events.end(),{92,pk.let,i,e.outcodes[i]});
            queue_events.insert(queue_events.end(),words,words+8);
        }
    }
}

static void queue_case(unsigned id){
    const unsigned variant=id-100,shape=variant%4,failure=variant/4;
    assert(shape<4&&failure<3);
    geometry_low_at=failure==1?2:0;
    if(failure==2){acquire_invalid_at=2;acquire_invalid_kind=1;}
    auto data=composition_package();re4dc::room::MeshPackage package;
    assert(package.adopt(data.data(),unsigned(data.size()),true,true));
    assert(package.offline_dedup()==!COMPOSITION_DECODED);
    const auto& cpkg=package;
    re4dc::vp::build_lut(lut);re4dc::room::CompactVertex12 gather[256]{};
    std::uint16_t groups[16*2*8]{};
    for(unsigned li=0;li<16;++li){
        groups[li*16+6]=5;groups[li*16+7]=0|(3U<<8);
        groups[li*16+14]=10;
        groups[li*16+15]=(encoded_part(li/2)?1U:4U)|((encoded_part(li/2)&&!COMPOSITION_DECODED?3U:7U)<<8);
    }
    assert(package.offline_groups(reinterpret_cast<const std::uint8_t*>(groups),sizeof(groups),2));
    struct {const unsigned* lut;re4dc::room::CompactVertex12* gather;const std::uint8_t* sg;unsigned sg_groups;}
        ps2w{::lut,gather,reinterpret_cast<const std::uint8_t*>(groups),2};
    QueuePart part;part.cull=1;part.projection[1]=part.projection[3]=1;
    part.viewport[2]=640;part.viewport[3]=480;
    part.uv_offset[0]=.125f;part.uv_offset[1]=-.25f;
    const float near=1,far=1000;const unsigned pass=0;
    struct {unsigned native=0,fallback=0,aborts=0;}c;
    struct ChunkPart { float mvq[12]; unsigned key[6]; float cull_far,lod_scale; unsigned index,first,count;
#if RE4DC_SCENERY_UV_SNAPSHOT
                       float uv_offset[2];
#endif
#if RE4DC_PS2_PVS
                       unsigned placement;
#endif
                       std::uint8_t cull; bool marked; std::uint8_t sky; };
    static constexpr unsigned kChunkParts=48,kChunkPicks=320;
    ChunkPart cctx[kChunkParts]{};MeshDraw::Pick cpk[kChunkPicks]{};
    unsigned nctx=8,npk=0;piece::pkg=&cpkg;piece::table=piece_words;
    for(unsigned j=0;j<nctx;++j){
        auto& x=cctx[j];x.index=j;x.cull=j%3;x.sky=j&1;x.marked=j%3==1;
        key_for(j,0,x.cull,x.key);x.first=npk;x.count=j==1?0:2;
        x.cull_far=1000;x.lod_scale=2;
        x.mvq[0]=x.mvq[5]=x.mvq[10]=1;
        x.mvq[3]=shape==3?2000:-3+float(j)*.125f;
        x.mvq[7]=-3+float(j)*.0625f;
        x.mvq[11]=shape==1?-2:shape==2?-1001:-20-float(j);
        for(unsigned m=0;m<x.count;++m){
            const bool subset=j==4||j==6,zero=j==5;
            cpk[npk++]={std::uint16_t(2*j+m),std::uint8_t(zero?0:subset?1:255),
                        std::uint8_t(subset?2:1),std::uint8_t(subset?1:0),std::uint8_t(subset&&!COMPOSITION_DECODED?3:7),{0,0}};
        }
    }
    re4dc_ps2_sky_header=7;
    auto chunk_flush=[&]()->int{
#if RE4DC_SCENERY_REPLAY_LEAN
        if(!nctx){npk=0;return 1;}
#endif
        // The pending selection/ordinary draw references this shared record.
        // Queued emitters borrow its cull; restore the pending part on every exit.
        struct CullScope {
            unsigned& value;unsigned saved;
            ~CullScope(){value=saved;}
        } cull_scope{part.cull,part.cull};
#if RE4DC_SCENERY_UV_SNAPSHOT
        // A capacity drain may run after the next owner's UV was prepared.
        // Restore that pending draw's bits on normal and abort exits alike.
        // Component copies are plain SH4 moves; -Os calls memcpy even for 8 B.
        struct UvScope {
            float* value;float saved[2];
            explicit UvScope(float* p):value(p),saved{p[0],p[1]}{}
            ~UvScope(){value[0]=saved[0];value[1]=saved[1];}
        } uv_scope(part.uv_offset);
#endif
#if RE4DC_SCENERY_SUBMIT_BATCH
        // Only this synchronous replay owns the borrowed lock. Selection,
        // ordinary draws, aborts and returning to the source never retain it.
        struct SubmitScope {
            Re4dcWorldSubmitBatch batch{};
            ~SubmitScope(){re4dc_ps2_world_batch_close(&batch);}
        } submit_scope;
#endif
#if RE4DC_SKY_ANY
        const unsigned sky_now=re4dc_ps2_sky_header; // the placement being selected keeps its own after the run
#endif
#if RE4DC_SCENERY_REPLAY_LEAN
        // One full context per synchronous replay. Only UV fields of MeshPart
        // are read by chunk_emit/borrow; selection/run still use their own part.
        // Keep a stable reference to these four current-part values without
        // changing the shared renderer's part-reference layout or hot methods.
        re4dc::room::MeshPart replay_part{};
        MeshDraw e{{part,{},near,far},cpkg,replay_part,ps2w.lut,ps2w.gather};
        e.alpha=0xff000000U;e.direct=true;e.lean_part=true;
        e.sg=ps2w.sg;e.sg_groups=ps2w.sg_groups;
        e.streaming=re4dc_model_packet_streaming()!=0;e.set_clip();
#if RE4DC_SCENERY_SUBMIT_BATCH
        e.submit_batch=&submit_scope.batch;
#endif
#endif
        for(unsigned j=0;j<nctx;++j){
            const ChunkPart& x=cctx[j];
            part.cull=x.cull;
#if RE4DC_SCENERY_UV_SNAPSHOT
            part.uv_offset[0]=x.uv_offset[0];part.uv_offset[1]=x.uv_offset[1];
#endif
#if RE4DC_SKY_ANY
            re4dc_ps2_sky_header=x.sky;
#endif
#if RE4DC_SCENERY_REPLAY_LEAN
            const auto& active_part=cpkg.parts()[x.index];
            replay_part.uv_bias[0]=active_part.uv_bias[0];replay_part.uv_bias[1]=active_part.uv_bias[1];
            replay_part.uv_scale[0]=active_part.uv_scale[0];replay_part.uv_scale[1]=active_part.uv_scale[1];
            e.chunk_restart();
#if RE4DC_PS2_VERTEX_ALPHA
            e.lut=x.marked&&ps2w.lut?ps2_vertex_alpha_lut():ps2w.lut;
            e.vertex_alpha=x.marked;e.c4444=x.marked;
#endif
            e.part_index=x.index;
#else
#if RE4DC_PS2_VERTEX_ALPHA
            MeshDraw e{{part,{},near,far},cpkg,cpkg.parts()[x.index],x.marked&&ps2w.lut?ps2_vertex_alpha_lut():ps2w.lut,ps2w.gather};
            e.alpha=0xff000000U;e.vertex_alpha=x.marked;e.c4444=x.marked;e.cull_far=x.cull_far;e.direct=true;
#else
            MeshDraw e{{part,{},near,far},cpkg,cpkg.parts()[x.index],ps2w.lut,ps2w.gather};
            e.alpha=0xff000000U;e.vertex_alpha=false;e.cull_far=x.cull_far;e.direct=true;
#endif
            e.part_index=x.index;e.lod_scale=x.lod_scale;e.lean_part=true;
#endif
#if RE4DC_SCENERY_SUBMIT_BATCH && !RE4DC_SCENERY_REPLAY_LEAN
            e.submit_batch=&submit_scope.batch;
#endif
#if RE4DC_PS2_PVS
            e.pvs_placement=x.placement;
#endif
#if !RE4DC_SCENERY_REPLAY_LEAN
            e.sg=ps2w.sg;e.sg_groups=ps2w.sg_groups;
            std::memcpy(e.mvq,x.mvq,sizeof(x.mvq));std::memcpy(e.mv,x.mvq,sizeof(x.mvq));e.ps2=x.key;
#else
            // mv is used by bounds/selection only; emit_pick and the clipper
            // consume mvq. The queued snapshot remains owned by this flush.
            std::memcpy(e.mvq,x.mvq,sizeof(x.mvq));e.ps2=x.key;
#endif
#if RE4DC_SCENERY_PIECE_STATE
            e.piece_slot=piece::pkg==static_cast<const void*>(&cpkg)?piece::table+x.index:nullptr;
#endif
#if RE4DC_SCENERY_EMIT_PREFETCH
            // Picks are packed even when an intervening part has no picks.
            // Never look beyond this flush or change the selected draw order.
            const unsigned next=x.first+x.count;
            const int result=e.chunk_emit(cpk+x.first,x.count,next<npk?cpk+next:nullptr);
#else
            const int result=e.chunk_emit(cpk+x.first,x.count);
            observe_cache(e,cpk+x.first,x.count,result);
#endif
            e.end_direct();
#if RE4DC_SCENERY_SUBMIT_BATCH
            if(result<=0)re4dc_ps2_world_batch_close(&submit_scope.batch);
#endif
#if RE4DC_PS2_PVS
            e.pvs_finish(result>0);
#endif
            if(result>0)++c.native;
            else if(result<0){re4dc_model_packet_abort();++c.aborts;nctx=npk=0;return -1;}
#if RE4DC_WORLD_HOLE_DIAG
            else {++c.fallback;whd::note(pass,x.key);}
#else
            else ++c.fallback;
#endif
        }
        nctx=npk=0;
#if RE4DC_SKY_ANY
        re4dc_ps2_sky_header=sky_now;
#endif
        return 1;
    };
    const int result=chunk_flush();assert(!locked&&!direct_open);
    assert(model_parts>=1); // Every failure follows a successful first part.
    if(failure==0){
        assert(result>0&&c.native==8&&c.fallback==0&&c.aborts==0);
        assert(part.cull==1&&re4dc_ps2_sky_header==7&&nctx==0&&npk==0);
        if(shape==1||shape==2)assert(stats.strips_clipped>0);
    }else if(failure==1){assert(result<0&&c.aborts==1&&acquired==2);}
    else {assert(source_failures>0&&acquired==2&&c.native>=1);assert(c.aborts||c.fallback);}
    returns.push_back(unsigned(result));queue_native=c.native;queue_fallback=c.fallback;queue_aborts=c.aborts;
    queue_events.insert(queue_events.end(),{stats.batches,stats.bind_rejects,stats.groups_visible,stats.reserve_rejects,stats.strips,stats.strips_clipped,stats.strips_culled,stats.triangles_clipped,stats.vertices});
}


static std::uint64_t digest(const std::vector<std::uint32_t>& words){std::uint64_t h=1469598103934665603ULL;for(auto v:words){h^=v;h*=1099511628211ULL;}return h;}
static void report(unsigned id){
    assert(!locked&&!direct_open);assert(unsafe_calls==0);
    std::vector<unsigned> state={model_used,model_pending,frame_pvr_calls,frame_pvr_bytes,stream_model_bytes,stream_peak_bytes,direct_parts,direct_slots,
        model_header_hits,model_header_builds,model_texture_rejects,ps2_hdr_hits,ps2_hdr_fills,ps2_piece_hits,stream_closed_lists,quads_flushed,nquad,mv_receivers,
        source_failures,r11f_failures,loads,logs,missing,acquired,diagbind,hash_calls,ui_flushes,desired_list,stream_list,whd_why,
        unsigned(frame_ready),unsigned(stream_aborted),unsigned(stream_scene),unsigned(world_autosort),unsigned(source_valid),unsigned(r11f_valid),
        model_handle?unsigned(model_handle-entries)+1U:0U};
    for(auto& e:entries)state.push_back(e.frame);
    for(auto v:piece_words)state.push_back(v);
    state.insert(state.end(),returns.begin(),returns.end());state.insert(state.end(),capacities.begin(),capacities.end());
    state.insert(state.end(),u_bits.begin(),u_bits.end());state.insert(state.end(),v_bits.begin(),v_bits.end());
    state.insert(state.end(),queue_events.begin(),queue_events.end());
    state.insert(state.end(),{model_parts,model_empty_parts,model_input,model_output,packet_aborts,pick_calls,lut_calls,screen_loads,
                            queue_native,queue_fallback,queue_aborts,re4dc_ps2_sky_header});
    std::printf("%u words=%zu data=%016llx state=%016llx\n",id,sent.size(),(unsigned long long)digest(sent),(unsigned long long)digest(state));
    // Compare every submitted word and semantic state word, not only a hash.
    std::printf("TA");for(auto word:sent)std::printf(" %08x",word);std::printf("\n");
    std::printf("STATE");for(auto word:state)std::printf(" %08x",word);std::printf("\n");
    std::fprintf(stderr,"%u lock=%u unlock=%u\n",id,lock_calls,unlock_calls);
}

static void prefetch_context_case(){
    auto data=composition_package();re4dc::room::MeshPackage package;
    assert(package.adopt(data.data(),unsigned(data.size()),true,true));
    QueuePart part;re4dc::room::CompactVertex12 gather[256]{};
    MeshDraw e{{part,{},1.0f,1000.0f},package,package.parts()[0],lut,gather};
    e.gathered=gather;
    // Encoded first, ordinary plain, indexed, indexed zero pick, new encoded
    // material and another encoded pick. Every call must set OR clear context.
    const unsigned lets[]={0,4,6,7,8,12},nr[]={255,255,255,0,1,255};
    unsigned material[6]={1,2,128,128,0,0};
    for(unsigned j=0;j<6;++j){
        material[0]=j+1;material[1]=2*j+7;e.ps2=material;
        part.uv_offset[0]=float(j)*.125f;part.cull=j%3;
        const auto& l=package.meshlets()[lets[j]];
        MeshDraw::Pick pk{std::uint16_t(lets[j]),std::uint8_t(nr[j]),2,1,3,{0,0}};
        const auto* got=e.emit_corners(l,pk);
        const unsigned rep=package.repeat_count(l);
        const auto* base=package.vertices()+l.first_vertex;
        assert(e.dd_base==(rep?base:nullptr));
        assert(e.dd_unique==l.vertex_count-rep&&e.dd_count==l.vertex_count);
        assert(e.dd_active(e.dd_word(l))==bool(rep));
        if(!package.indexed(l))assert(got==base);else assert(got==gather);
        assert(e.ps2==material&&part.cull==j%3);
    }
    std::puts("PASS encoded-first/plain/indexed/zero/new-material decoder context");
}

int main(int argc,char** argv){
    const unsigned id=argc>1?unsigned(std::strtoul(argv[1],nullptr,10)):0;
    for(unsigned i=0;i<8;++i)seed(i);
    ps2_hdr_log=frame;
    if(id==200){prefetch_context_case();return 0;}
    if(id>=100){queue_case(id);report(id);return 0;}
    unsigned count=8;
    if(id==1)count=1;
    if(id==4)for(auto& set:ps2_hdr)for(auto& slot:set)slot.mode=0;
    if(id==20||id==21||id==22)count=3;
    if(id==28)stream_scene=false;
    if(id==29)world_autosort=false;
    if(id==33)model_used=kModelPacketBytes/32-16;
    if(id==34)source_group_claimed=true;
    for(unsigned i=0;i<count;++i){
        unsigned index=id==2?0:i,pass=0,cull=2,n=6+i,style=0;
        if(id==37)style=3;
        if(id==38)style=4;
        if(id==3)pass=i%3;
        if(id==13)re4dc_ps2_sky_header=i&1;
        if(id==14)re4dc_mv_receiver=i&1;
        if(id==15)cull=i%3;
        if(id==16)fog=(i&1)!=0;
        if(id==19)n=0;
        if(id==20)n=32767;
        if(id==21)n=i==0?32760:16;
        if(id==22)n=i==0?32768:16;
        if(i==4){
            switch(id){
            case 5:entries[index].package.address+=0x100000;break;
            case 6:entries[index].key.crc^=1;break;
            case 7:entries[index].valid=false;break;
            case 8:frame_ready=false;break;
            case 9:stream_aborted=true;break;
            case 10:source_valid=false;break;
            case 11:r11f_valid=false;break;
            case 12:ui_order=true;nquad=8;break;
            case 17:entries[index].package.texture.width=32;break;
            case 18:entries[index].package.texture.width=32;rect_ok=false;break;
            case 23:frame+=600;break;
            case 24:piece_words[index]=777;break;
            case 25:cull=3;break;
            case 26:pass=3;break;
            case 27:model_packets=nullptr;storage_ok=false;break;
            case 30:owner_cut_stage=1;for(auto& set:ps2_hdr)for(auto& slot:set)slot.mode=0;break;
            case 31:abort_on_select=1;break;
            case 32:stream_list=PVR_LIST_TR_POLY;break;
            case 35:style=1;break;
            case 36:style=2;break;
            case 39:header_dims_ok=false;break;
            case 40:model_packets=nullptr;storage_ok=true;break;
            default:break;
            }
        }
        normal_part(index,pass,cull,n,style);
    }
#if RE4DC_SCENERY_SUBMIT_BATCH
    re4dc_ps2_world_batch_close(&batch);
#endif
    report(id);
}
