// Native actor-volume service (lane eng-svc4): the characters' collision bodies (cAtariInfo), the pushes between them
// by priority, the line tests against them (aiming, camera) and the geometry predicates under the collision code.
// Engine bodies for the entry points of the original units atariInfo.cpp, at_mod.cpp and at_sub.cpp; the behaviour
// keeps calling them by their original names. Write-up: docs/engine/SERVICES.md section 23.
#pragma once
#include "types.h"

struct VolCounters {
    u32 at_checks;      // EmAtCheck calls
    u32 at_skipped;     // EmAtCheck calls on a body without collision (m_stat bit 0 only)
    u32 pairs;          // body pairs tested (__em_at_core)
    u32 pairs_prio;     // pairs skipped by priority
    u32 pushes;         // pairs that pushed (sphere / sphere, sphere / box, box / box)
    u32 pairs_box;      // pairs tested with a box body on either side
    u32 line_tests;     // EmHitCheck + ObjHitCheck calls
    u32 line_bodies;    // bodies a line was tested against (ComnHitCheck)
    u32 line_hits;      // line tests that hit a body
    u32 capsule_tests;  // AtSphereCapsuleCk + AtBoxCapsuleCk3 calls
    u32 box_sphere;     // At_box_sphere_ck calls
    u32 debug_draws;    // disp / dispRect / DrawOba / AtCapsuleDisp / AtCubeDisp (draw nothing natively)
};

extern "C" {
extern VolCounters vol_cnt;
// Controls (re4ref, RE4_SVC_CONTROL): 1 "volpush": every push between two bodies 10% longer; 2 "volline": a line
// tests the cylinder bodies whatever its flag (the flag's bit 1 filter lost).
extern int vol_control;
}
