#pragma once
#include "gc_asset_gate.h"
#ifndef RE4DC_GC_ASSET_MOTION_UNKNOWN
#define RE4DC_GC_ASSET_MOTION_UNKNOWN 0
#endif
#if RE4DC_GC_ASSET_MOTION_UNKNOWN != 0 && RE4DC_GC_ASSET_MOTION_UNKNOWN != 1
#error "GC_ASSET_MOTION_UNKNOWN must be 0 or 1"
#endif
#if RE4DC_GC_ASSET_MOTION_UNKNOWN && !RE4DC_GC_ASSET_GATE
#error "GC_ASSET_MOTION_UNKNOWN requires GC_ASSET_GATE=1"
#endif
#if RE4DC_GC_ASSET_MOTION_UNKNOWN
namespace re4dc_gcasset {
// Potential motion-derived accepted input, never an asset identity or N/A.
// ViewTrack is separate from the model/root pose component. Neither current
// null/stopped motion nor a retained geometry proof removes either unknown.
enum MotionUnknownReason : unsigned {
    MotionModelPose=1U, MotionViewTrack=2U, MotionDelayedModel=4U,
    MotionUnclassifiedWorld=8U, MotionMissingRoute=16U
};
unsigned motion_model_reason();
unsigned motion_enter(unsigned reason);
void motion_leave(unsigned previous);
struct MotionUnknownScope {
    unsigned previous;
    explicit MotionUnknownScope(unsigned reason):previous(motion_enter(reason)){}
    ~MotionUnknownScope(){motion_leave(previous);}
    MotionUnknownScope(const MotionUnknownScope&)=delete;
    MotionUnknownScope& operator=(const MotionUnknownScope&)=delete;
};
static_assert(sizeof(MotionUnknownScope)==4,"one saved diagnostic word only");
void motion_prepare(); // freeze context for the next accepted interval
void motion_accept_pending(unsigned records); // packet/direct accepted records
void motion_accept_current(unsigned records); // OneWindow chunk owns its prefix
// Internal OneWindow close/switch marker only, guarded by its accounted flag.
// Zero/invalid incoming reason is UNKNOWN and can never request suppression.
void motion_pending_accounted();
void motion_unknown_flush(); // renderer safe boundary, before old visit END
}
#endif
