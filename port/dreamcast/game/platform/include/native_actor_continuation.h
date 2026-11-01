#pragma once
#include "native_draw_result.hpp"
struct Re4dcModelPart;
namespace re4dc_source { struct ChunkInput; }
#if defined(RE4DC_NATIVE_FE_CONTINUATION) && RE4DC_NATIVE_FE_CONTINUATION
extern "C" {
int re4dc_actor_native_pose_acquire(Re4dcModelPart*,unsigned immutable_asset,
    const re4dc_source::ChunkInput*,const float* palette,unsigned palette_bytes,unsigned source_frame);
void re4dc_actor_native_pose_release(const Re4dcModelPart*);
void re4dc_actor_native_pose_retire();
re4dc::NativeDrawResult re4dc_actor_native_submit_result(const Re4dcModelPart*,unsigned queued_replay);
// Zero means immediate; one supplies the ACTUAL queue/refusal outcome.
int re4dc_model_defer_native_result(const Re4dcModelPart*,re4dc::NativeDrawResult*);
}
#endif
