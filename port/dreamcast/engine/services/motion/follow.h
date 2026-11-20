// Native root-motion follower (lane eng-svc4; follow.cpp, docs/engine/SERVICES.md section 26): cMotBase, the pose an
// actor's animation says it should be at (integrated from the motion's root speed in model space), and the blend of
// the model onto it over a count of ticks, or the pin to it. Engine bodies for the entry points of the original unit
// cMotBase.cpp; the behaviour keeps calling them by their names, and the follower stays in the actor's record.
#pragma once
#include "types.h"

struct FollowCounters {
    u32 sets;      // followers started (cMotBase::set)
    u32 moves;     // active follower ticks (cMotBase::move with cnt != 0xFF)
    u32 blends;    // of those, blending ticks (cnt counting down)
    u32 pins;      // of those, pinned ticks (cnt 0)
    u32 ends;      // blends that finished (the motion moves the model itself again)
    u32 adjusts;   // active cMotBase::adjust calls
};

extern "C" {
extern FollowCounters follow_cnt;
// Control (re4ref, RE4_SVC_CONTROL): 1 "followslow": every blend step one tick longer (1 / (cnt + 1)).
extern int follow_control;
}
