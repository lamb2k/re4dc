// warp_late.h - test-only late activation for same-binary A/B arms (DBG_WARP=1 builds only).
//
// warp.txt line `late <mask> [tick] [room]` (dbgwarp_bridge.cpp): from global tick `tick` (pG->Frame_cnt,
// default 1400) while the current room is `room` (default 0x100), RE4DC_WARP_LATE(bits) returns the mask's
// bits. Every arm of a pair runs the same ELF and the same prelude; only the mask differs (keep the line the
// same length in every arm, e.g. `late 0x00` / `late 0x04`). tools/d367/README.md "Late activation".
//
// Bits (diagnostic switches, none of them a production option):
//   0x01  world LOD error 20 px (quality.cpp re4dc_quality lod_px)
//   0x02  actor LOD threshold 8 px outside the mid-crowd rule (native_actor_fast.cpp)
//   0x04  Fast pacing from activation (pace.cpp); in the trace emulator nearly every image is dropped, so the
//         arm keeps the source ticks without drawing: a G diagnostic, not a playable mode
//   0x08  ACT_CAP only after activation (act_cap.cpp; ACT_CAP builds only; a gameplay change)
//   0x10  Leon keeps the per-part source path (coarse_actor_owner_leon.inc: no native plan), the old-path arm of
//         the WP2 Leon pair
//
// With DBG_WARP=0 the macro is the constant 0 and every hook compiles out (knob-off identity).
#pragma once

#define RE4DC_LATE_WORLD_LOD20 0x01u
#define RE4DC_LATE_ACTOR_LOD8 0x02u
#define RE4DC_LATE_NODRAW 0x04u
#define RE4DC_LATE_ACT_CAP 0x08u
#define RE4DC_LATE_LEON_SOURCE 0x10u
// Private scratch QA only: exactly one bit; requires reviewed final-image admission.
#define RE4DC_LATE_SCRATCH_A 0x80u
#define RE4DC_LATE_SCRATCH_B 0x100u
#define RE4DC_LATE_SCRATCH_C 0x200u

#if defined(RE4DC_DBG_WARP) && RE4DC_DBG_WARP
#ifdef __cplusplus
extern "C" {
#endif
// The mask's bits while the late window is open, else 0.
unsigned re4dc_warp_late(void);
// 1 when warp.txt has a `late` line (the arm is a late-activation arm).
int re4dc_warp_late_set(void);
// 1 only inside the configured room/tick window, even when the mask is0. No side effects.
int re4dc_warp_late_open(void);
// Validated target/current room while open, else0; independent of the mask.
unsigned re4dc_warp_late_room(void);
#ifdef __cplusplus
}
#endif
#define RE4DC_WARP_LATE(bits) (re4dc_warp_late() & (bits))
#define RE4DC_WARP_LATE_SET() (re4dc_warp_late_set())
#define RE4DC_WARP_LATE_OPEN() (re4dc_warp_late_open())
#define RE4DC_WARP_LATE_ROOM() (re4dc_warp_late_room())
#else
#define RE4DC_WARP_LATE(bits) 0u
#define RE4DC_WARP_LATE_SET() 0
#define RE4DC_WARP_LATE_OPEN() 0
#define RE4DC_WARP_LATE_ROOM() 0u
#endif
