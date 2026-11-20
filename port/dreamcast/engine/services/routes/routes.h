// Native route service (lane eng-svc4; routes.cpp, docs/engine/SERVICES.md section 25): the room's way-point graph
// (the "RTP" sub-file at pG->Rtp: points, links and a next-hop table), the nearest reachable point, the next position
// toward an actor or a position (the partner's follow, the enemies' chase and escape) and the path length. Engine
// bodies for the entry points of the original unit route_ck.cpp; the behaviour keeps calling them by their names.
#pragma once
#include "types.h"

struct RouteCounters {
    u32 near_calls;    // nearest-point searches (getNearPoint, getNearInfo misses)
    u32 near_cached;   // getNearInfo answered from this tick's cache (RckStat bit 0)
    u32 near_lines;    // line tests made by the nearest-point search
    u32 near_none;     // searches that found no reachable point
    u32 steps;         // RouteCkToEm / RouteCkToPos / RouteCkPosToPos calls
    u32 steps_direct;  // of those, answered with the target itself
    u32 lines;         // every line test against the scenery (rckLineHitCheck)
    u32 dists;         // path lengths (RouteCkGetDist, RouteCkPosToPosDis, RouteCkToPos's dist)
    u32 debug_draws;   // debug lines and labels (counted, not drawn)
};

extern "C" {
extern RouteCounters route_cnt;
// Controls (re4ref, RE4_SVC_CONTROL): 1 "routenear": the nearest-point search returns the second reachable point
// when there is one (a wrong sort); 2 "routehop": the way points between two points
// skipped (every reachable destination is its own next hop).
extern int route_control;
}
