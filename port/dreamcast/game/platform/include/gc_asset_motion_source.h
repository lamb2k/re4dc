#pragma once
#include "gc_asset_gate.h"
#ifndef RE4DC_GC_ASSET_MOTION_SOURCE
#define RE4DC_GC_ASSET_MOTION_SOURCE 0
#endif
#if RE4DC_GC_ASSET_MOTION_SOURCE != 0 && RE4DC_GC_ASSET_MOTION_SOURCE != 1
#error "GC_ASSET_MOTION_SOURCE must be 0 or 1"
#endif
#if RE4DC_GC_ASSET_MOTION_SOURCE && (!RE4DC_GC_ASSET_GATE || !RE4DC_GC_ASSET_MOTION_UNKNOWN)
#error "GC_ASSET_MOTION_SOURCE requires GC_ASSET_GATE and GC_ASSET_MOTION_UNKNOWN"
#endif
#if RE4DC_GC_ASSET_MOTION_SOURCE
namespace re4dc_gcasset {
enum MotionSourceRole : unsigned { MotionFcv=1,MotionEvd=2,MotionShape=3,MotionBind=4 };
// Fixed metadata only. This is a contributor receipt, never a completeness
// certificate. Existing UNKNOWN accounting stays active for unproved ancestry.
constexpr unsigned MotionSourceLimit=8;
constexpr unsigned MotionStorageBytes=12288,MotionStorageAlignment=32;
// Root supplies this fixed partition of the existing common slab at cold
// startup. Bind once; never free/reset the common allocation at room teardown.
// No allocation, hashing or catalog work. A second different backing fails.
bool motion_source_storage_bind(void*,unsigned bytes);
bool motion_source_idle(); // finite scopes/accepted-latches witness AFTER real producer stop
struct MotionReceipt {
    unsigned serial[MotionSourceLimit]{},count=0,fault=0;
    const void* model=nullptr;const void* info=nullptr;const void* view=nullptr;
    unsigned model_generation=0,info_generation=0,view_generation=0;
};
// Safe cold boundary BEFORE any in-place relocation/pose/key writes. The exact
// complete span must belong to owner until retirement. A repeated live adoption
// never hashes changed/prepared bytes; replacement without retirement fails.
bool motion_source_adopt(const void* owner,const void* base,unsigned bytes,MotionSourceRole);
// Original source archives only. Validates all spans first, then captures FCV,
// EVD/EVS and BIN members. MTC FCV prefixes receive no identity; external
// sources require their complete cold capture below. Tags never imply origin.
bool motion_source_archive(const void* owner,const void* base,unsigned bytes);
void motion_source_retire(const void* owner); // unlocked, before overwrite/free
void motion_source_retire_base(const void* base);
// Evaluation tracks exact bounded source pointers, without hashing/logging.
// Key bind alone is NOT use; caller notes only when a pose/morph/view is written.
void motion_source_note(const void* subject,const void* source,MotionSourceRole);
// Actual evaluated key pointers must belong to the authenticated original FCV,
// including all three bounded Hermite axis blocks; header membership is not
// sufficient authority for external/rebound keys.
void motion_source_note_key(const void* subject,const void* header,const void* key,unsigned type,MotionSourceRole=MotionFcv);
// Cold external load: compute SHA only after successful complete read/checks,
// before pointer writes. No catalog IO/log/allocation while motion mutex held.
unsigned motion_source_external_capture(const void* owner,const void* proxy,unsigned proxy_bytes,const void* original,unsigned bytes);
unsigned motion_source_external_serial(const void* owner,const void* data,const void* proxy); // fixed metadata, under lease mutex
bool motion_source_external_publish(const void* owner,unsigned serial); // AFTER acquire unlock, while pinned
void motion_source_external_invalidate(const void* owner); // memory only, BEFORE overwrite/free
void motion_source_reset(const void* subject); // constructor/destructor only
MotionReceipt motion_source_snapshot(const void* model,const void* info=nullptr);
void motion_source_view(const void* subject); // selected CameraMotion only
void motion_source_view_retire(const void* subject);
MotionReceipt motion_source_current();
MotionReceipt motion_source_exchange(const MotionReceipt&);
// Real ordinary evaluator stacks, including early returns and blocked callees.
// The fixed counter shares funded State, with short IRQ-protected updates only.
bool motion_producer_enter();
void motion_producer_leave(bool entered);
struct MotionProducerScope {
    bool entered=motion_producer_enter();
    ~MotionProducerScope(){motion_producer_leave(entered);}
    MotionProducerScope()=default;
    MotionProducerScope(const MotionProducerScope&)=delete;
    MotionProducerScope& operator=(const MotionProducerScope&)=delete;
};
bool motion_source_replay_active();
MotionReceipt motion_source_scope_enter(const void* model,const void* info);
MotionReceipt motion_source_replay_enter(const MotionReceipt&);
void motion_source_restore(const MotionReceipt&,bool frozen);
struct MotionSourceScope {
    MotionProducerScope producer;
    bool previous_frozen;
    MotionReceipt previous;
    explicit MotionSourceScope(const void* model,const void* info=nullptr):previous_frozen(motion_source_replay_active()),previous(motion_source_scope_enter(model,info)){}
    explicit MotionSourceScope(const MotionReceipt& receipt):previous_frozen(motion_source_replay_active()),previous(motion_source_replay_enter(receipt)){}
    ~MotionSourceScope(){motion_source_restore(previous,previous_frozen);}
    MotionSourceScope(const MotionSourceScope&)=delete;
    MotionSourceScope& operator=(const MotionSourceScope&)=delete;
};
void motion_source_prepare();
void motion_source_accept_pending(unsigned records);
void motion_source_accept_current(unsigned records);
void motion_source_pending_accounted();
void motion_source_accept(const MotionReceipt&,unsigned records);
void motion_source_flush(); // unlocked; accepted original identities only
#if defined(RE4DC_GC_ASSET_TEST) && RE4DC_GC_ASSET_TEST
void motion_source_test_serial(unsigned);
unsigned motion_source_test_storage_bytes();
void motion_source_test_depth(unsigned,bool overflow);
#endif
}
#endif
