#include "include/gc_asset_motion_unknown.h"
#if RE4DC_GC_ASSET_MOTION_UNKNOWN
extern "C" void re4dc_log(const char*,...);
namespace re4dc_gcasset {
namespace {
constexpr unsigned ValidReasons=MotionModelPose|MotionViewTrack|MotionDelayedModel|MotionUnclassifiedWorld|MotionMissingRoute;
constexpr unsigned Accounted=0x80000000U;
struct UnknownState {
    unsigned context,pending,reasons,events,records,overflow;
} motion{};
static_assert(sizeof(UnknownState)==24,"bounded renderer-thread state; no caches or owners");
unsigned sanitize(unsigned reason){return reason && !(reason&~ValidReasons)?reason:unsigned(MotionMissingRoute);}
void add(unsigned& value,unsigned amount){
    if(amount>~0U-value){value=~0U;motion.overflow=1;}else value+=amount;
}
void accept(unsigned reason,unsigned records){
    if(!records)return;
    motion.reasons|=sanitize(reason);add(motion.events,1);add(motion.records,records);
}
}
unsigned motion_model_reason(){return MotionModelPose|MotionViewTrack|(motion.context&MotionDelayedModel);}
unsigned motion_enter(unsigned reason){const unsigned previous=motion.context;motion.context=sanitize(reason);return previous;}
void motion_leave(unsigned previous){motion.context=previous;}
void motion_prepare(){
#if RE4DC_GC_ASSET_MOTION_SOURCE
    motion_source_prepare();
#endif
    // World/impostor callers have no model scope. This fixed UNKNOWN receipt
    // does not inspect or borrow their geometry owner/token or last model.
    motion.pending=motion.context?sanitize(motion.context):unsigned(MotionUnclassifiedWorld|MotionViewTrack);
}
void motion_accept_pending(unsigned records){
#if RE4DC_GC_ASSET_MOTION_SOURCE
    motion_source_accept_pending(records);
#endif
    if(!records)return;
    if(motion.pending==Accounted){motion.pending=MotionMissingRoute;return;}
    accept(motion.pending,records);
}
void motion_accept_current(unsigned records){
#if RE4DC_GC_ASSET_MOTION_SOURCE
    motion_source_accept_current(records);
#endif
    accept(motion.context,records);
}
void motion_pending_accounted(){
#if RE4DC_GC_ASSET_MOTION_SOURCE
    motion_source_pending_accounted();
#endif
    motion.pending=Accounted;
}
void motion_unknown_flush(){
#if RE4DC_GC_ASSET_MOTION_SOURCE
    motion_source_flush();
#endif
    if(!motion.events)return;
    // Called only after SQ/LH/G2 release, while the old diagnostic visit is live.
    unresolved(Motion,"motion-unknown-accepted-records");
    re4dc_log("GC-MOTION-UNKNOWN reasons=%08x events=%u accepted_records=%u overflow=%u\n",
        motion.reasons,motion.events,motion.records,motion.overflow);
    motion.reasons=motion.events=motion.records=motion.overflow=0;
}
}
#endif
