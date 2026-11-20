// Native per-model collision response (lane eng-svc4; col_model.cpp, docs/engine/SERVICES.md section 24): the layer
// above the query cores of col.cpp. The behaviour calls the original entry points (cSatMgr::check, checkAir, getFloor,
// wallAdjust, adjust; cEatMgr); col_model.cpp gives them engine bodies.
#pragma once
#include "types.h"

struct ColModelCounters {
    u32 checks;       // check + checkAir
    u32 rects;        // checkRect (box bodies)
    u32 spheres;      // scrAtCheckSphere(Air): one body's slide
    u32 slides;       // wallAdjust + adjust
    u32 floors;       // getFloor
    u32 floor_lost;   // floor snaps refused (no floor within 1000 units)
    u32 pieces;       // collision pieces set up from their files
    u32 debug_draws;  // debug lines and spheres (counted, not drawn)
};

extern "C" {
extern ColModelCounters colm_cnt;
// Controls (re4ref, RE4_SVC_CONTROL): 1 "colfloor": the floor snap 0.5 unit high; 2 "colwall": the wall slide's
// radius 10% larger.
extern int colm_control;
}
