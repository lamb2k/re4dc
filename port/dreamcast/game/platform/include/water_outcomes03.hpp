#pragma once
#if defined(RE4DC_NATIVE_DRAW_OUTCOMES) && RE4DC_NATIVE_DRAW_OUTCOMES
#include "native_draw_result.hpp"
// W29's established layer loop continues after individual refusal. Preserve
// that visitation/order while retaining failure and every later owned layer.
// This is call-local accounting, not a second queue or retained receipt.
inline void re4dc_water03_observe(re4dc::NativeDrawProgress& progress,re4dc::NativeDrawResult child){
    if(progress.result.complete()){progress.add(child);return;}
    progress.result.submitted+=child.submitted;progress.result.queued+=child.queued;
    if(progress.result.published() || child.outcome==re4dc::NativeDrawOutcome::PartialAbort)
        progress.result.outcome=re4dc::NativeDrawOutcome::PartialAbort;
}
#endif
