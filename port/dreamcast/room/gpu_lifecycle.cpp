#include "gpu_lifecycle.hpp"
#include <dc/pvr.h>
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
#include "../game/platform/include/world_census24.h"
#endif
namespace re4dc::gpu {
FenceResult quiesce() {
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
    // The census rejects non-owner threads (including the optional presenter).
    re4dc::wc24::WaitScope wc24_wait(re4dc::wc24::PvrWait);
#endif
    if(pvr_wait_ready() < 0) return FenceResult::ta_timeout;
    if(pvr_wait_render_done() < 0) return FenceResult::render_timeout;
    return FenceResult::ready;
}
}
