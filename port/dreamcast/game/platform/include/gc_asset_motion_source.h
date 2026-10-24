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
struct MotionReceipt {unsigned serial[MotionSourceLimit]{},count=0,fault=0;};
// Safe cold boundary BEFORE any in-place relocation/pose/key writes. The exact
// complete span must belong to owner until retirement. A repeated live adoption
// never hashes changed/prepared bytes; replacement without retirement fails.
bool motion_source_adopt(const void* owner,const void* base,unsigned bytes,MotionSourceRole);
// Original source archives only. Validates all spans first, then captures FCV,
// EVD and BIN members; MTC external-key FCVs are unsupported, never blessed by
// their prefix. Directory tags identify layout only, never provenance.
bool motion_source_archive(const void* owner,const void* base,unsigned bytes);
void motion_source_retire(const void* owner); // unlocked, before overwrite/free
void motion_source_retire_base(const void* base);
// Evaluation tracks exact bounded source pointers, without hashing/logging.
// Key bind alone is NOT use; caller notes only when a pose/morph/view is written.
void motion_source_note(const void* subject,const void* source,MotionSourceRole);
void motion_source_reset(const void* subject); // constructor/destructor only
MotionReceipt motion_source_snapshot(const void* model,const void* info=nullptr);
void motion_source_view(const void* subject); // selected CameraMotion only
void motion_source_view_retire(const void* subject);
MotionReceipt motion_source_current();
MotionReceipt motion_source_exchange(const MotionReceipt&);
struct MotionSourceScope {
    MotionReceipt previous;
    explicit MotionSourceScope(const void* model,const void* info=nullptr):previous(motion_source_exchange(motion_source_snapshot(model,info))){}
    explicit MotionSourceScope(const MotionReceipt& receipt):previous(motion_source_exchange(receipt)){}
    ~MotionSourceScope(){motion_source_exchange(previous);}
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
#endif
}
#endif
