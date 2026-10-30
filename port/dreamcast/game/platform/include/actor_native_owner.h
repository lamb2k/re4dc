#pragma once
#include "native_actor.hpp"
#include "actor_resource_lease.h"

// All handles are values. Skin backups belong to the current primitive owner.
// No pointer returned by these APIs may outlive its source FrameLedger ticket.
struct Re4dcActorSkinBinding {
    const void* info;
    Re4dcActorSource source;
    const float* palette;
    unsigned entries;
};
struct Re4dcActorSkinBackup {
    unsigned index;
    const void* info;
    const void* positions;
    const float* palette;
    unsigned entries,materialized;
};
#ifndef RE4DC_ACTOR_PL08
#define RE4DC_ACTOR_PL08 0
#endif
#ifndef RE4DC_LEON_HEADLESS
#define RE4DC_LEON_HEADLESS 0  // LEON_HEADLESS (crowd.mk): appearance 0x109, Leon after setHead(0)
#endif
#ifndef RE4DC_ACTOR_SKIN_RESERVE
#define RE4DC_ACTOR_SKIN_RESERVE 0
#endif
#if RE4DC_ACTOR_SKIN_RESERVE && (!RE4DC_ACTOR_TRANSACTION || !RE4DC_NATIVE_ACTOR_FAST || !RE4DC_NATIVE_ACTOR_SKIN_LAZY)
#error ACTOR_SKIN_RESERVE requires actor transactions and the fast lazy skin registry
#endif
#if RE4DC_ACTOR_SKIN_RESERVE
// Shared reservation batch limit; this does not enlarge any per-owner lease.
constexpr unsigned kRe4dcActorSkinKeys=64;
#endif
// Role-indexed infos per owner plan. ACTOR_PL08=1 (crowd.mk): the nine-info no-jacket Leon (pl08) is the widest
// plan; every other appearance keeps its exact count. Its one extra (role 8) run follows the 21 Leon runs.
constexpr unsigned kRe4dcActorRoles=RE4DC_ACTOR_PL08?9u:8u;
struct Re4dcActorSkinLease {
    unsigned serial=0,frame=0,count=0;
    Re4dcActorSkinBackup old[kRe4dcActorRoles]{};
};
// Material identity is independent of the source info / its one skin palette.
// All textures are leased together before the actor can emit its first header.
// PS2_ASHLEY (native_model_registry.mk, RE4DC_ACTOR_MATERIALS=4 in every object): Ashley's descriptors carry her one PS2
// atlas plus three mask pairs (head, hair, extra 9), four materials; every other build keeps three.
#ifndef RE4DC_ACTOR_MATERIALS
#define RE4DC_ACTOR_MATERIALS 3
#endif
constexpr unsigned kRe4dcActorMaterials=RE4DC_ACTOR_MATERIALS,kRe4dcActorRuns=RE4DC_ACTOR_PL08?22u:21u;
struct Re4dcActorOwnedMaterial {
    Re4dcUiImage image{},mask{};
    unsigned crc=0,fnv=0,material_flags=0,blend=0,depth_mode=0;
    unsigned mask_ref=256,mask_same_uv=0,wrap_s=0,wrap_t=0;
};
struct Re4dcActorDrawRun { Re4dcActorChunk chunk; unsigned material; };
extern "C" {
int re4dc_actor_workspace_acquire(unsigned,Re4dcActorWorkspaceLease*);
int re4dc_actor_workspace_validate(const Re4dcActorWorkspaceLease*);
void re4dc_actor_workspace_release(Re4dcActorWorkspaceLease*);
#if RE4DC_ACTOR_SKIN_RESERVE
// Source-plan storage priority only. Up to 64 unique nominee main-info keys
// get inert slots in the existing 64/80-entry table; no palette, geometry or owner is admitted.
// A full/invalid current table declines atomically. Source registrations fill
// their own placeholders; all other deferrals keep the usual eager fallback.
int re4dc_actor_skin_reserve(unsigned source_frame,const void* const* infos,unsigned count);
#endif
#if defined(RE4DC_ACTOR_PRESENTATION32) && RE4DC_ACTOR_PRESENTATION32
// Initialize a direct image's source-frame authority through the existing
// reservation API. An already current frame retains any other live owners.
int re4dc_actor_skin_presentation32_frame(unsigned,const void* const*,unsigned);
#endif
int re4dc_actor_skin_acquire(unsigned,const Re4dcActorSkinBinding*,unsigned,Re4dcActorSkinLease*);
int re4dc_actor_skin_validate(const Re4dcActorSkinLease*);
int re4dc_actor_skin_release(Re4dcActorSkinLease*);
#if defined(RE4DC_SKIN_RECIPE32) && RE4DC_SKIN_RECIPE32
// Call only after the definitive final native pass, before ordinary release.
int re4dc_actor_skin_finish_owner(Re4dcActorSkinLease*);
#endif
int re4dc_actor_owned_source(const void*,unsigned,Re4dcActorSource*);
void re4dc_actor_owner_retire();
int re4dc_actor_stream_state(Re4dcActorStreamState*);
int re4dc_actor_texture_material_validate(const Re4dcModelPart*,const Re4dcActorTextureLease*);
int re4dc_actor_preflight_owned_runs(Re4dcModelPart*,const Re4dcActorDrawRun*,unsigned,
    const Re4dcActorOwnedMaterial*,unsigned,const Re4dcActorWorkspaceLease*,const Re4dcActorSkinLease*,const Re4dcActorTextureLease*);
int re4dc_actor_submit_owned_runs(Re4dcModelPart*,const Re4dcActorDrawRun*,unsigned,
    const Re4dcActorOwnedMaterial*,unsigned,const Re4dcActorWorkspaceLease*,const Re4dcActorSkinLease*,const Re4dcActorTextureLease*);
#if defined(RE4DC_ACTOR_PLAN) && RE4DC_ACTOR_PLAN
// ACTOR_PLAN: only for the runs of the transaction call that acquired the actor and preflighted all its runs, while
// ACTOR_PROOF_LEAN's lifetime token holds (native_actor_owner_runs.inc).
int re4dc_actor_submit_preflighted_runs(Re4dcModelPart*,const Re4dcActorDrawRun*,unsigned,
    const Re4dcActorOwnedMaterial*,unsigned,const Re4dcActorWorkspaceLease*,const Re4dcActorSkinLease*,const Re4dcActorTextureLease*);
#endif
int re4dc_actor_preflight_owned(Re4dcModelPart*,const Re4dcActorChunk*,unsigned,
    const Re4dcActorWorkspaceLease*,const Re4dcActorSkinLease*,const Re4dcActorTextureLease*);
// 0 is decline before any owned call, 1 complete synchronously, -1 frame failed.
int re4dc_actor_submit_owned(Re4dcModelPart*,const Re4dcActorChunk*,unsigned,
    const Re4dcActorWorkspaceLease*,const Re4dcActorSkinLease*,const Re4dcActorTextureLease*);
}

namespace re4dc_actor {
// Reservation reduces only transient-conversion capacity. Existing skin table
// allocations still use the high end and reuse it per info as before.
class WorkspaceReservations {
public:
    // Every actual actor skin acquisition already holds one of these leases.
    // The isolated skin pool derives its maximum from this existing bound.
    static constexpr unsigned MaxOwners=64;
private:
    struct Slot { unsigned serial=0,bytes=0;
#if RE4DC_NATIVE_FE_CONTINUATION
        const void* allocation=nullptr;unsigned allocation_bytes=0;
#endif
    };
    Slot slots_[MaxOwners]{};
    unsigned serial_=0,maximum_=0;
public:
    unsigned maximum()const{return maximum_;}
    bool acquire(unsigned bytes,unsigned epoch,Re4dcActorWorkspaceLease& out){
        if(!bytes || (bytes&31) || out.serial || out.slot || serial_==UINT32_MAX)return false;
        for(unsigned i=0;i<MaxOwners;++i)if(!slots_[i].serial){
            slots_[i]={++serial_,bytes};out={i+1,serial_,epoch,bytes};
            if(bytes>maximum_)maximum_=bytes;return true;
        }
        return false;
    }
    bool valid(const Re4dcActorWorkspaceLease& t,unsigned epoch)const{
        return t.slot && t.slot<=MaxOwners && t.serial && t.epoch==epoch &&
            slots_[t.slot-1].serial==t.serial && slots_[t.slot-1].bytes==t.bytes;
    }
#if RE4DC_NATIVE_FE_CONTINUATION
    // The existing primitive owner supplies this exact allocation. Its value
    // ticket is checked before any snapshot header/palette can be read.
    bool bind(const Re4dcActorWorkspaceLease& t,unsigned epoch,const void* p,unsigned bytes){
        if(!valid(t,epoch) || !p || bytes!=t.bytes || slots_[t.slot-1].allocation)return false;
        slots_[t.slot-1].allocation=p;slots_[t.slot-1].allocation_bytes=bytes;return true;
    }
    bool bound(const Re4dcActorWorkspaceLease& t,unsigned epoch,const void* p)const{
        return valid(t,epoch) && p && slots_[t.slot-1].allocation==p && slots_[t.slot-1].allocation_bytes==t.bytes;
    }
    void retire_bound(){
        for(auto& s:slots_)if(s.allocation)s={};
        maximum_=0;for(const auto& s:slots_)if(s.serial && s.bytes>maximum_)maximum_=s.bytes;
    }
#endif
    void release(Re4dcActorWorkspaceLease& t){
        if(t.slot && t.slot<=MaxOwners && t.serial && slots_[t.slot-1].serial==t.serial){
            slots_[t.slot-1]={};maximum_=0;
            for(const auto& s:slots_)if(s.serial && s.bytes>maximum_)maximum_=s.bytes;
        }
        t={};
    }
    void retire(){for(auto& s:slots_)s={};maximum_=0;}
};
}
