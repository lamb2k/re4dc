#include "world_draw_meter.h"
extern "C" unsigned world_meter_off_fixture(unsigned value) {
#if defined(BASELINE)
    return value*3+7;
#else
    // Undefined pass/view tokens must be fully absent in an off build.
    return RE4DC_WORLD_MEASURE(UndefinedPass,undefined_view(),value*3+7);
#endif
}
