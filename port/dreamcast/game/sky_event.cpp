// SKY_EVENT=1 (lane fix60b-26, GitHub #60 item 2; render only, default 0): the room's sky / backdrop rows (native_static.cpp
// ps2_sky_row: r100 sky dome + treeline cards, r101 cloud dome + treeline) also draw while a scripted scene owns the
// camera, even under look A (sky 0 = culled at the view-distance cut). Play cameras rarely face the sky, so look A
// culls it for speed; the r100 radio-call lift (Leon raises the radio after the s40 movie, a low camera looking up)
// then showed only the clear colour behind Leon: the white background of #60 item 2. Reads game state only.
#include "global.h"
#include "player.h"
#include "sce.h"
#include "sce_sys.h"
#include "sscrn.h"
#include "re4dc_platform.h"
extern "C" void re4dc_log(const char* fmt, ...);
static unsigned s_last = 0xFFFFFFFFu;
extern "C" unsigned re4dc_sky_event(void)
{
    if (!pG) return 0;
    const unsigned ev = (pG->Status_flg[1] & 0x10000000) ? 1U : 0U;
    const unsigned sce = SceSys.event_start_cnt ? 2U : 0U;
    const unsigned ss = SubScreenWk.type ? 4U : 0U;
    const unsigned st = ev | sce | ss;
    if (st != s_last) {
        s_last = st;
        re4dc_log("sky event: state=%u (event %u sce %u subscreen %u) room=%03x\n", st, ev, sce >> 1, ss >> 2,
                  (unsigned) pG->room_id);
    }
    return st ? 2U : 0U;   // 2: drawn unfogged (1 = table fog: at 60-240 m the near fog table paints it the fog colour)
}
#if defined(RE4DC_SKY_EVENT) && RE4DC_SKY_EVENT >= 2
// SKY_EVENT=2: re4dc_sky_event() latched once per frame (coarse.cpp re4dc_coarse_draw, before the world and the fog
// far are noted), so re4dc_view_far / re4dc_far_cap / the sky rows read one word instead of the flags per call.
extern "C" { unsigned re4dc_sky_event_now; }
extern "C" void re4dc_sky_event_latch(void) { re4dc_sky_event_now = re4dc_sky_event(); }
#endif
