#include "native_model.h"
#include "native_draw_owner_stamp.hpp"
#include "re4dc_platform.h"
#include "../../room/native_draw_plan.hpp"
#ifndef RE4DC_MODEL_DRAW_PLANS
#define RE4DC_MODEL_DRAW_PLANS 0
#endif
#ifndef RE4DC_PLAN_ADMIT_LEAN
#define RE4DC_PLAN_ADMIT_LEAN 0 // obj/scenery30.h (D367 scenery30 D1)
#endif
#ifndef RE4DC_FRONT_LEAN
#define RE4DC_FRONT_LEAN 0 // obj/frontend30.h (D367 frontend30)
#endif
#if RE4DC_MODEL_STREAM_FIX
#include "native_actor.hpp"
#endif
#if RE4DC_MODEL_DRAW_PLANS
#include "../../room/room_storage.hpp"
#include <cstdlib>
#include <cstdint>
#include <cstring>
#include <new>
#include <cmath>
#include <algorithm>

namespace {
constexpr unsigned kEntries=256, kOwners=44;
struct Owner { const void* key; std::uintptr_t start; unsigned bytes,transient;
#if RE4DC_PLAN_OWNER_SCOPED
    unsigned incarnation=0;
#endif
} owners[kOwners]{};
struct Entry {
    const void* stream=nullptr;
    unsigned bytes=0;
    std::uint16_t positions=0,normals=0;
    std::uint8_t colored=0,bound_stride=0,bound_shift=0,reserved=0;
    const re4dc::render::NativeDrawPlan* plan=nullptr;
    const re4dc::render::DrawLocalPlan* locals=nullptr;
    const re4dc::render::DrawPlanBounds* bounds=nullptr;
    const void* bound_positions=nullptr;
#if RE4DC_PLAN_OWNER_SCOPED
    unsigned topology_incarnation=0,position_incarnation=0;
    std::uint8_t topology_owner=255,position_owner=255;
#endif
};
Entry* entries=nullptr;
re4dc::storage::Arena arena, local_arena;
constexpr unsigned kLocalMetadataBytes=8192;
unsigned leases=0; bool reset_pending=false, free_pending=false;
#if RE4DC_PLAN_OWNER_SCOPED
// Dead metadata is retained while any caller holds a plan/local/bounds lease.
// Repack only at the existing no-lease asset-registration boundary.
bool retired_metadata=false;
constexpr unsigned kNoOwner=255,kTombstone=254;
#endif
Re4dcDrawPlanStats stats{}, previous{};
unsigned previous_walk_bytes=0,bounds_bytes=0;
bool assets_dirty=true, asset_update_active=false, local_admission_dirty=true;
#if RE4DC_PLAN_ADMIT_LEAN
unsigned stats_assets_changed=0,stats_admissions=0;
#endif
const re4dc::render::DrawPlanBounds* acquired_bounds=nullptr;
const re4dc::render::DrawLocalPlan* acquired_locals=nullptr;
bool contains(const Owner& o,const void* p,unsigned bytes) {
    auto a=reinterpret_cast<std::uintptr_t>(p);
    return o.key && a>=o.start && a-o.start<=o.bytes && bytes<=o.bytes-(a-o.start);
}
void reset_now() {
    if(entries)for(unsigned i=0;i<kEntries;++i)entries[i]={};
    arena.reset();local_arena.reset();acquired_locals=nullptr;stats.used=entries?((sizeof(Entry)*kEntries+31)&~31U):0;bounds_bytes=0;acquired_bounds=nullptr;
#if RE4DC_PLAN_OWNER_SCOPED
    retired_metadata=false;
#endif
    reset_pending=false;assets_dirty=true;asset_update_active=false;local_admission_dirty=true;++stats.resets;
    if(free_pending){arena.init(nullptr,0);entries=nullptr;stats.capacity=stats.used=0;free_pending=false;}
}
#if RE4DC_PLAN_OWNER_SCOPED
Re4dcDrawOwnerStamp owner_stamp(const void* p,unsigned bytes){
    Re4dcDrawOwnerStamp result;
    for(unsigned i=0;i<kOwners;++i)if(contains(owners[i],p,bytes)){
        if(result.valid())return {}; // overlapping publishers cannot prove one immutable incarnation
        result={i,owners[i].incarnation};
    }
    return result;
}
bool owner_current(unsigned slot,unsigned incarnation){
    return slot<kOwners && owners[slot].key && owners[slot].incarnation==incarnation;
}
void tombstone(Entry& e){
    if(e.plan || e.bounds)retired_metadata=true;
    e={};e.topology_owner=kTombstone;
}
void invalidate_owner(unsigned slot){
    if(entries)for(unsigned i=0;i<kEntries;++i){auto& e=entries[i];
        if(e.stream && e.topology_owner==slot)tombstone(e);
        else if(e.bounds && e.position_owner==slot){
            e.bounds=nullptr;e.bound_positions=nullptr;e.position_owner=kNoOwner;
            e.position_incarnation=0;retired_metadata=true;
        }
    }
    assets_dirty=local_admission_dirty=true;
}
bool overlap(const void* a,unsigned an,const void* b,unsigned bn){
    if(!a || !b || !an || !bn)return false;
    const auto x=reinterpret_cast<std::uintptr_t>(a),y=reinterpret_cast<std::uintptr_t>(b);
    return x<=y?y-x<an:x-y<bn;
}
void invalidate_overlapping(const void* archive,unsigned bytes){
    if(entries)for(unsigned i=0;i<kEntries;++i){auto& e=entries[i];
        if(e.stream && overlap(e.stream,e.bytes,archive,bytes))tombstone(e);
        else if(e.bounds && overlap(e.bound_positions,(unsigned(e.positions)+1)*e.bound_stride,archive,bytes)){
            e.bounds=nullptr;e.bound_positions=nullptr;e.position_owner=kNoOwner;
            e.position_incarnation=0;retired_metadata=true;
        }
    }
}
void clear_owner(Owner& o){o.key=nullptr;o.start=0;o.bytes=o.transient=0;}
void compact_metadata(){
    if(!retired_metadata || !entries || leases || reset_pending)return;
    // Self-relative plans and bounds can move without decoding source bytes.
    // Select the next source block in address order: <=512 fixed blocks, no
    // scratch allocation, per-draw compaction or change to the fixed arena.
    auto* destination=arena.base();auto cursor=reinterpret_cast<std::uintptr_t>(arena.base());
    for(;;){
        Entry* selected=nullptr;bool bound=false;std::uintptr_t first=~std::uintptr_t(0);
        for(unsigned i=0;i<kEntries;++i){auto& e=entries[i];
            const auto p=reinterpret_cast<std::uintptr_t>(e.plan),b=reinterpret_cast<std::uintptr_t>(e.bounds);
            if(p>=cursor && p<first){first=p;selected=&e;bound=false;}
            if(b>=cursor && b<first){first=b;selected=&e;bound=true;}
        }
        if(!selected)break;
        const unsigned bytes=bound?sizeof(re4dc::render::DrawPlanBounds)+selected->bounds->primitive_count*sizeof(re4dc::render::PrimitiveSphere)
            :sizeof(re4dc::render::NativeDrawPlan)+selected->plan->primitive_count*sizeof(re4dc::render::DrawPrimitive);
        const unsigned aligned=(bytes+31U)&~31U;
        std::memmove(destination,reinterpret_cast<const void*>(first),bytes);
        if(bound)selected->bounds=reinterpret_cast<const re4dc::render::DrawPlanBounds*>(destination);
        else selected->plan=reinterpret_cast<const re4dc::render::NativeDrawPlan*>(destination);
        destination+=aligned;cursor=first+aligned;
    }
    arena.rewind(unsigned(destination-arena.base()));bounds_bytes=0;
    for(unsigned i=0;i<kEntries;++i)if(entries[i].bounds)bounds_bytes+=sizeof(re4dc::render::DrawPlanBounds)+
        entries[i].bounds->primitive_count*sizeof(re4dc::render::PrimitiveSphere);
    stats.used=((sizeof(Entry)*kEntries+31)&~31U)+arena.used()+local_arena.used();
    retired_metadata=false;
}
void prepare_owner_bounds(Entry& e,const Re4dcModelPart& p){
    if(!p.static_geometry || p.position_stride>255)return;
    const auto owner=re4dc_model_draw_array_owner(p.positions,p.position_count,p.position_stride);
    if(!owner.valid())return;
    if(e.bounds && e.bound_positions==p.positions && e.bound_stride==p.position_stride && e.bound_shift==p.shift &&
       e.position_owner==owner.slot && e.position_incarnation==owner.incarnation)return;
    if(e.bounds){e.bounds=nullptr;e.bound_positions=nullptr;retired_metadata=true;}
    unsigned size=sizeof(re4dc::render::DrawPlanBounds)+e.plan->primitive_count*sizeof(re4dc::render::PrimitiveSphere);
    const bool primitives=size<=8192-bounds_bytes;
    if(!primitives)size=sizeof(re4dc::render::DrawPlanBounds);
    if(size>8192-bounds_bytes)return;
    const auto mark=arena.mark();void* memory=arena.allocate(size);
    if(!memory)return;
    e.bounds=re4dc::render::prepare_draw_bounds(memory,size,*e.plan,p.stream,bool(e.colored),p.positions,
        p.position_stride,std::ldexp(1.f,-int(p.shift)),primitives);
    if(!e.bounds){arena.rewind(mark);return;}
    bounds_bytes+=size;e.bound_positions=p.positions;e.bound_stride=p.position_stride;e.bound_shift=p.shift;
    e.position_owner=std::uint8_t(owner.slot);e.position_incarnation=owner.incarnation;
}
#endif
}
#if RE4DC_PLAN_OWNER_SCOPED
extern "C" Re4dcDrawOwnerStamp re4dc_model_draw_owner_stamp(const void* p,unsigned bytes){return owner_stamp(p,bytes);}
#endif
extern "C" void re4dc_model_reset_draw_plans() {
#if RE4DC_PLAN_OWNER_SCOPED
    for(auto& o:owners)if(o.key && ++o.incarnation==0)o.incarnation=1;
#endif
    re4dc_model_invalidate_pending();
    if(leases) reset_pending=true; else reset_now();
}
extern "C" void re4dc_model_bind_draw_owner(const void* key,void* archive,unsigned bytes,unsigned transient) {
#if RE4DC_PLAN_OWNER_SCOPED
    if(!key)return;
    re4dc_model_invalidate_pending(); // keep source-view/queue lifetime fencing
    invalidate_overlapping(archive,bytes); // aliased publishers are related, not independent owners
#else
    re4dc_model_reset_draw_plans();
#endif
    Owner* slot=nullptr;
    for(auto& o:owners) { if(o.key==key) { slot=&o;break; } if(!o.key && !slot) slot=&o; }
    if(!slot) { re4dc_log("native draw plans: owner capacity exhausted\n"); return; }
#if RE4DC_PLAN_OWNER_SCOPED
    invalidate_owner(unsigned(slot-owners));
    if(++slot->incarnation==0){slot->incarnation=1;re4dc_model_reset_draw_plans();}
    slot->key=archive && bytes?key:nullptr;slot->start=reinterpret_cast<std::uintptr_t>(archive);
    slot->bytes=bytes;slot->transient=transient;
#else
    *slot={archive && bytes?key:nullptr,reinterpret_cast<std::uintptr_t>(archive),bytes,transient};
#endif
}
extern "C" void re4dc_model_retire_draw_plans() {
    for(auto& o:owners)if(o.transient){
#if RE4DC_PLAN_OWNER_SCOPED
        clear_owner(o);
#else
        o={};
#endif
    }
    free_pending=true;re4dc_model_reset_draw_plans();
}
extern "C" void re4dc_model_unbind_draw_owner(const void* key) {
#if RE4DC_PLAN_OWNER_SCOPED
    if(!key)return;
    re4dc_model_invalidate_pending();
    for(auto& o:owners)if(o.key==key){invalidate_owner(unsigned(&o-owners));clear_owner(o);}
#else
    re4dc_model_reset_draw_plans();
    for(auto& o:owners) if(o.key==key) o={};
#endif
}
static const re4dc::render::NativeDrawPlan* acquire_plan(const Re4dcModelPart* p,int* invalid,bool install) {
    *invalid=0;acquired_bounds=nullptr;acquired_locals=nullptr;
#if RE4DC_MODEL_STREAM_FIX
    // Actor conversion replaces GX commands in place without changing the
    // stream address/size. Neither cached topology nor local ranges survive it.
    if(re4dc_actor_stream_encoded(p->stream,p->stream_bytes)){++stats.uncovered;return nullptr;}
#endif
    if(reset_pending) { ++stats.uncovered;return nullptr; }
#if RE4DC_PLAN_OWNER_SCOPED
    const auto topology=owner_stamp(p->part,32),stream_owner=owner_stamp(p->stream,p->stream_bytes);
    const bool owned=topology.valid() && topology==stream_owner;
#else
    bool owned=false;
    for(const auto& o:owners) if(contains(o,p->part,32) && contains(o,p->stream,p->stream_bytes)) {owned=true;break;}
#endif
    if(!owned) {++stats.owner_misses;++stats.uncovered;return nullptr;}
    const unsigned colored=bool(p->flags&0x80000000U);
    if(!entries && !install){++stats.uncovered;return nullptr;}
    if(!entries) {
        unsigned capacity=0;
        auto* memory=static_cast<std::uint8_t*>(re4dc_model_metadata_storage(&capacity));
        const unsigned table_bytes=(sizeof(Entry)*kEntries+31)&~31U;
        if(!memory || capacity<=table_bytes+kLocalMetadataBytes) {++stats.capacity_rejects;++stats.uncovered;return nullptr;}
        // Entries AND spans replace part of the existing packet slab. No new
        // allocation, corner copy, or source-arena reservation is involved.
        entries=reinterpret_cast<Entry*>(memory);
        for(unsigned i=0;i<kEntries;++i)new(entries+i) Entry{};
        arena.init(memory+table_bytes,capacity-table_bytes-kLocalMetadataBytes);
        local_arena.init(memory+capacity-kLocalMetadataBytes,kLocalMetadataBytes);stats.capacity=capacity;
        stats.used=table_bytes;stats.peak=std::max(stats.peak,table_bytes);
        re4dc_log("native draw plans: shared slab metadata=%u table=%u source_heap=%d\n",capacity,table_bytes,re4dc_ui_heap_free());
    }
    unsigned slot=(reinterpret_cast<std::uintptr_t>(p->stream)>>5)&(kEntries-1);
    Entry* entry=nullptr;
    for(unsigned n=0;n<kEntries;++n,slot=(slot+1)&(kEntries-1)) {
        auto& e=entries[slot];
#if RE4DC_PLAN_OWNER_SCOPED
        if(!e.stream){
            if(!entry)entry=&e;
            if(e.topology_owner!=kTombstone)break;
            continue;
        }
#else
        if(!e.stream) {entry=&e;break;}
#endif
        if(e.stream==p->stream && e.bytes==p->stream_bytes && e.positions==p->position_count-1 &&
           e.normals==p->normal_count-1 && e.colored==colored
#if RE4DC_PLAN_OWNER_SCOPED
           && e.topology_owner==topology.slot && e.topology_incarnation==topology.incarnation
#endif
           ) {
            if(install && asset_update_active && e.reserved<255)++e.reserved;
            if(!e.plan) {++stats.capacity_rejects;++stats.uncovered;return nullptr;}
#if RE4DC_PLAN_OWNER_SCOPED
            if(install)prepare_owner_bounds(e,*p);
#endif
            ++stats.hits;++leases;acquired_locals=e.locals;
            // Topology can be shared; bounds cannot survive a changed source
            // position binding, deformation eligibility or quantization scale.
            if(p->static_geometry && e.bound_positions==p->positions && e.bound_stride==p->position_stride && e.bound_shift==p->shift
#if RE4DC_PLAN_OWNER_SCOPED
               && owner_current(e.position_owner,e.position_incarnation)
#endif
               )acquired_bounds=e.bounds;
            return e.plan;
        }
    }
    if(!entry) {++stats.capacity_rejects;++stats.uncovered;return nullptr;}
    if(!install){++stats.uncovered;return nullptr;}
    if(!p->position_count || p->position_count>65536 || !p->normal_count || p->normal_count>65536){++stats.uncovered;return nullptr;}
    *entry={};entry->stream=p->stream;entry->bytes=p->stream_bytes;
    entry->positions=std::uint16_t(p->position_count-1);entry->normals=std::uint16_t(p->normal_count-1);entry->colored=colored;
    entry->reserved=asset_update_active?1:0;
#if RE4DC_PLAN_OWNER_SCOPED
    entry->topology_owner=std::uint8_t(topology.slot);entry->topology_incarnation=topology.incarnation;
#endif
    // Stable negative admission avoids re-decoding an uncacheable part on every
    // lookup. Such parts use the explicit reference path; no LRU disc/CPU churn.
    re4dc::render::DrawPlanRequirements requirements;
    stats.source_bytes+=p->stream_bytes;
    if(!re4dc::render::inspect_draw_plan(p->stream,p->stream_bytes,colored,
             p->position_count,p->normal_count,requirements)) {

#if RE4DC_PLAN_OWNER_SCOPED
        tombstone(*entry);
#else
        *entry={};
#endif
        ++stats.invalid;*invalid=1;return nullptr;
    }
    const auto mark=arena.mark();
    void* memory=arena.allocate(requirements.bytes);
    if(!memory) {++stats.capacity_rejects;++stats.uncovered;return nullptr;}
    stats.source_bytes+=p->stream_bytes;
    entry->plan=re4dc::render::prepare_draw_plan(memory,requirements.bytes,p->stream,
                                               p->stream_bytes,colored,requirements);
    if(!entry->plan) {arena.rewind(mark);
#if RE4DC_PLAN_OWNER_SCOPED
        tombstone(*entry);
#else
        *entry={};
#endif
        ++stats.invalid;*invalid=1;return nullptr;}
    // Local descriptors are admitted after the complete source OT walk, so a
    // first-arriving part cannot consume the entire independent local budget.
    local_admission_dirty=true;
#if RE4DC_PLAN_OWNER_SCOPED
    prepare_owner_bounds(*entry,*p);
#else
    bool positions_owned=false;
    for(const auto& o:owners)if(contains(o,p->positions,p->position_count*p->position_stride))positions_owned=true;
    if(p->static_geometry && positions_owned){
        // Optional bounds share the same slab, capped at 8 KiB including group
        // bounds. Command metadata never acquires an unbounded companion table.
        unsigned size=sizeof(re4dc::render::DrawPlanBounds)+requirements.primitives*sizeof(re4dc::render::PrimitiveSphere);
        bool primitives=size<=8192-bounds_bytes;
        if(!primitives)size=sizeof(re4dc::render::DrawPlanBounds);
        if(size<=8192-bounds_bytes){
            const auto bound_mark=arena.mark();void* data=arena.allocate(size);
            if(data){entry->bounds=re4dc::render::prepare_draw_bounds(data,size,*entry->plan,p->stream,colored,
                p->positions,p->position_stride,std::ldexp(1.f,-int(p->shift)),primitives);
                if(entry->bounds){bounds_bytes+=size;entry->bound_positions=p->positions;
                    entry->bound_stride=p->position_stride;entry->bound_shift=p->shift;}else arena.rewind(bound_mark);}
        }
    }
#endif
    acquired_bounds=entry->bounds;
    const unsigned table_bytes=(sizeof(Entry)*kEntries+31)&~31U;
    ++stats.installs;++leases;stats.used=table_bytes+arena.used()+local_arena.used();
    if(table_bytes+arena.high_water()+local_arena.high_water()>stats.peak)stats.peak=table_bytes+arena.high_water()+local_arena.high_water();
    return entry->plan;
}
#if RE4DC_PLAN_ADMIT_LEAN
// D1: a model-info creation (model.cpp) marks the assets for the next registration walk only.
// The local admission is rebuilt when that walk really installs a plan (acquire_plan) or after a
// reset, not on every creation: each gunshot's shell/effect model otherwise re-ran the full
// visit_draw_locals + qsort pass (~470 ms Flycast frames) with nothing new to admit.
extern "C" void re4dc_model_assets_changed(){assets_dirty=true;++stats_assets_changed;}
#else
extern "C" void re4dc_model_assets_changed(){assets_dirty=true;local_admission_dirty=true;}
#endif
#if RE4DC_FRONT_LEAN
// model_asset_bridge.cpp: 1 when a registration walk over an unchanged OT
// would install nothing and change no admission state (no pending reset,
// asset change or local admission, table allocated, no update or lease open).
extern "C" int re4dc_model_asset_update_idle(){
    return entries && !assets_dirty && !local_admission_dirty && !reset_pending && !asset_update_active && !leases;
}
#endif
extern "C" int re4dc_model_begin_asset_update(){
    if(asset_update_active || leases || reset_pending)return 0;
#if RE4DC_PLAN_OWNER_SCOPED
    compact_metadata();
#endif
    asset_update_active=true;
    if(entries)for(unsigned i=0;i<kEntries;++i)entries[i].reserved=0;
    const bool changed=assets_dirty;assets_dirty=false;return changed;
}
namespace {
// Reuse the local arena as installation scratch. Every candidate is at least
// the maximum aligned cost of its final header + descriptor (32 B); serialization
// therefore fits the same 8 KiB even if all candidates belong to different parts.
struct LocalCandidate {
    re4dc::render::LocalBatch batch;
    std::uint16_t owner,padding;
    unsigned weight,reserved;
};
static_assert(sizeof(LocalCandidate)==32);
bool better_local(const LocalCandidate& a,const LocalCandidate& b){
    if(a.weight!=b.weight)return a.weight>b.weight;
    if(a.batch.reuse_score!=b.batch.reuse_score)return a.batch.reuse_score>b.batch.reuse_score;
    if(a.batch.corner_count!=b.batch.corner_count)return a.batch.corner_count>b.batch.corner_count;
    if(a.owner!=b.owner)return reinterpret_cast<std::uintptr_t>(entries[a.owner].stream)<
        reinterpret_cast<std::uintptr_t>(entries[b.owner].stream);
    return a.batch.first_corner<b.batch.first_corner;
}
struct LocalAdmission {LocalCandidate* values;unsigned count=0,visited=0,owner=0,demand=0;};
void consider_local(void* context,const re4dc::render::LocalBatch& batch){
    auto& out=*static_cast<LocalAdmission*>(context);++out.visited;
    const LocalCandidate candidate{batch,std::uint16_t(out.owner),0,batch.reuse_score*out.demand,0};
    constexpr unsigned capacity=kLocalMetadataBytes/sizeof(LocalCandidate);
    if(out.count<capacity){out.values[out.count++]=candidate;
        std::push_heap(out.values,out.values+out.count,better_local);
    }else if(better_local(candidate,out.values[0])){
        std::pop_heap(out.values,out.values+out.count,better_local);
        out.values[out.count-1]=candidate;std::push_heap(out.values,out.values+out.count,better_local);
    }
}
}
extern "C" void re4dc_model_finish_asset_update(){
    if(!asset_update_active)return;
    asset_update_active=false;
    // Demand is sampled when assets/plans are installed. Camera-only changes
    // do not reparse source streams or churn descriptors each frame.
    if(!local_admission_dirty || !entries || leases || reset_pending)return;
    // No native draw may retain a descriptor through a replacement. The source
    // registration boundary and lease test qualify this installation lifetime.
    re4dc_model_invalidate_static_lighting();acquired_locals=nullptr;
    for(unsigned i=0;i<kEntries;++i)entries[i].locals=nullptr;
    local_arena.reset();
    auto* scratch=reinterpret_cast<LocalCandidate*>(local_arena.allocate(kLocalMetadataBytes));
    if(!scratch)return;
    LocalAdmission admission{scratch};unsigned streams=0;
    for(unsigned i=0;i<kEntries;++i){auto& e=entries[i];
        if(!e.plan || !e.reserved)continue;
        ++streams;admission.owner=i;admission.demand=e.reserved;stats.source_bytes+=e.bytes;
        re4dc::render::visit_draw_locals(*e.plan,static_cast<const std::uint8_t*>(e.stream),
            e.colored,&admission,consider_local);
    }
    // qsort is already linked by the recovered game. Reuse it for this cold
    // installation step rather than instantiate another full introsort family.
    std::qsort(scratch,admission.count,sizeof(LocalCandidate),[](const void* lhs,const void* rhs){
        const auto& a=*static_cast<const LocalCandidate*>(lhs);
        const auto& b=*static_cast<const LocalCandidate*>(rhs);
        if(a.owner!=b.owner)return a.owner<b.owner?-1:1;
        return a.batch.first_corner<b.batch.first_corner?-1:a.batch.first_corner>b.batch.first_corner?1:0;
    });
    local_arena.reset();unsigned admitted_streams=0;
    for(unsigned first=0;first<admission.count;){
        // Read the first record before the compacted header overwrites its
        // scratch slot. Later destination records never overtake unread input.
        const LocalCandidate saved=scratch[first];unsigned end=first+1;
        while(end<admission.count && scratch[end].owner==saved.owner)++end;
        const unsigned count=end-first;
        const unsigned bytes=sizeof(re4dc::render::DrawLocalPlan)+count*sizeof(re4dc::render::LocalBatch);
        void* memory=local_arena.allocate(bytes);
        if(!memory){
            for(unsigned i=0;i<kEntries;++i)entries[i].locals=nullptr;
            local_arena.reset();re4dc_log("native local admission: bounded serialization failed\n");return;
        }
        auto* plan=new(memory) re4dc::render::DrawLocalPlan{count,0,bytes};
        auto* output=const_cast<re4dc::render::LocalBatch*>(plan->entries());
        for(unsigned i=first;i<end;++i){
            const auto batch=i==first?saved.batch:scratch[i].batch;
            output[i-first]=batch;plan->qualified_corners+=batch.corner_count;
        }
        entries[saved.owner].locals=plan;++admitted_streams;first=end;
    }
    local_admission_dirty=false;
#if RE4DC_PLAN_ADMIT_LEAN
    ++stats_admissions;
#endif
    stats.used=((sizeof(Entry)*kEntries+31)&~31U)+arena.used()+local_arena.used();
    stats.peak=std::max(stats.peak,unsigned(((sizeof(Entry)*kEntries+31)&~31U)+arena.high_water()+local_arena.high_water()));
    re4dc_log("native local admission: streams=%u candidates=%u admitted_streams=%u batches=%u bytes=%u cap=%u source_heap=%d\n",
        streams,admission.visited,admitted_streams,admission.count,unsigned(local_arena.used()),kLocalMetadataBytes,re4dc_ui_heap_free());
}
extern "C" int re4dc_model_owned_source(const void* data,unsigned bytes){
    for(const auto& o:owners)if(contains(o,data,bytes))return 1;
    return 0;
}
extern "C" int re4dc_model_prepare_draw_plan(const Re4dcModelPart* p){
    const bool implicit=!asset_update_active;
    if(implicit)re4dc_model_begin_asset_update();
#if RE4DC_PLAN_OWNER_SCOPED
    if(implicit && !asset_update_active)return 0;
#endif
    int invalid=0;const auto* plan=acquire_plan(p,&invalid,true);
    if(plan)re4dc_model_release_draw_plan();
    if(implicit)re4dc_model_finish_asset_update();
    return invalid?-1:plan?1:0;
}
extern "C" const re4dc::render::NativeDrawPlan* re4dc_model_acquire_draw_plan(const Re4dcModelPart* p,int* invalid){
    // Draw-time lookup never parses a command or allocates metadata. An asset
    // missed by registration is an explicit reference-path fallback this frame.
    return acquire_plan(p,invalid,false);
}
extern "C" void re4dc_model_release_draw_plan() {
    if(!leases) {re4dc_missing("native draw plan lease underflow");return;}
    if(--leases==0 && reset_pending)reset_now();
}
extern "C" void re4dc_model_draw_plan_frame(unsigned frame) {
    const unsigned walk_bytes=re4dc_model_work_stats()->gx_walk_bytes;
    if(stats.installs!=previous.installs || (stats.hits!=previous.hits && frame%30==0))
        re4dc_log("native draw plans: frame=%u hits=%u installs=%u install_decoded=%u reference_walk=%u uncovered=%u capacity_rejects=%u owner_misses=%u invalid=%u used=%u cap=%u peak=%u resets=%u\n",
          frame,stats.hits-previous.hits,stats.installs-previous.installs,
          stats.source_bytes-previous.source_bytes,walk_bytes-previous_walk_bytes,stats.uncovered-previous.uncovered,
          stats.capacity_rejects-previous.capacity_rejects,stats.owner_misses-previous.owner_misses,
          stats.invalid-previous.invalid,stats.used,stats.capacity,stats.peak,stats.resets);
    if(stats.installs!=previous.installs)re4dc_log("native local indices: used=%u cap=%u source_heap=%d workspace_slots=%u\n",
        unsigned(local_arena.used()),kLocalMetadataBytes,re4dc_ui_heap_free(),re4dc::render::kLocalSlots);
#if RE4DC_PLAN_ADMIT_LEAN
    if(frame%120==0)re4dc_log("native plan admission: frame=%u assets_changed=%u admissions=%u\n",frame,stats_assets_changed,stats_admissions);
#endif
    previous=stats;previous_walk_bytes=walk_bytes;
}
extern "C" const re4dc::render::DrawPlanBounds* re4dc_model_acquired_bounds(){return acquired_bounds;}
extern "C" const re4dc::render::DrawLocalPlan* re4dc_model_acquired_locals(){return acquired_locals;}
extern "C" const Re4dcDrawPlanStats* re4dc_model_draw_plan_stats(){return &stats;}
#else
#if RE4DC_FRONT_LEAN
extern "C" int re4dc_model_asset_update_idle(){return 0;}
#endif
extern "C" void re4dc_model_assets_changed(){}
extern "C" int re4dc_model_begin_asset_update(){return 0;}
extern "C" void re4dc_model_finish_asset_update(){}
extern "C" int re4dc_model_owned_source(const void*,unsigned){return 0;}
extern "C" int re4dc_model_prepare_draw_plan(const Re4dcModelPart*){return 0;}
extern "C" void re4dc_model_bind_draw_owner(const void*,void*,unsigned,unsigned) {}
extern "C" void re4dc_model_retire_draw_plans() {}
extern "C" void re4dc_model_unbind_draw_owner(const void*) {}
#if RE4DC_PLAN_OWNER_SCOPED
extern "C" Re4dcDrawOwnerStamp re4dc_model_draw_owner_stamp(const void*,unsigned){return {};}
#endif
extern "C" void re4dc_model_reset_draw_plans() {
    re4dc_model_invalidate_pending();}
extern "C" const re4dc::render::NativeDrawPlan* re4dc_model_acquire_draw_plan(const Re4dcModelPart*,int* invalid) {*invalid=0;return nullptr;}
extern "C" const re4dc::render::DrawPlanBounds* re4dc_model_acquired_bounds(){return nullptr;}
extern "C" const re4dc::render::DrawLocalPlan* re4dc_model_acquired_locals(){return nullptr;}
extern "C" void re4dc_model_release_draw_plan() {}
extern "C" void re4dc_model_draw_plan_frame(unsigned) {}
extern "C" const Re4dcDrawPlanStats* re4dc_model_draw_plan_stats(){static Re4dcDrawPlanStats empty{};return &empty;}
#endif
