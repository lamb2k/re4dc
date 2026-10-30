#pragma once
#ifndef RE4DC_STATIC_OBJ_SPANS10
#define RE4DC_STATIC_OBJ_SPANS10 0
#endif
#if RE4DC_STATIC_OBJ_SPANS10
#if !RE4DC_STATIC_OBJ_BATCH || !RE4DC_STATIC_OBJ_LIFETIME05 || !RE4DC_MODEL_DRAW_PLANS || \
    !RE4DC_PLAN_OWNER_SCOPED || !RE4DC_D349_RENDERER_STACK
#error STATIC_OBJ_SPANS10 requires the existing SOB lifetime and scoped native draw plans
#endif
struct Re4dcModelPart;
// Only ordered immutable topology is shared. The bridge supplies this draw's
// transform/material/lighting, and its existing pending-cell lifetime fence.
struct Re4dcModelSpan10 {
    const void* part;
    const unsigned char* stream;
    unsigned bytes;
};
// Zero declines before output; one consumed the complete run (including an
// ordinary bounded failure). Never replay a partially published run.
extern "C" int re4dc_model_submit_spans10(const Re4dcModelPart*,
    const Re4dcModelSpan10*,unsigned,bool (*current)(const void*),const void*);
#endif
