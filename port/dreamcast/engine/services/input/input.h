// Native input service (lane eng-svc4; input.cpp, docs/engine/SERVICES.md section 29): the pads read once a tick into
// Joy[] (buttons, sticks as direction bits, triggers, edges, repeats), the game's 64-bit Key word through the key-type
// table, the key stop, and the rumble mixer. Engine bodies for every function of the original unit pad.cpp; the
// behaviour keeps calling them by their names.
//
// Rumble is presentation (owner 2026-11-19, "Split it"; E1 audit section 3): a random-strength rumble slot (type bit 15)
// draws its strength from the engine's presentation generator (eng_pres_u8), never from the behaviour's Rnd, so a
// rumble can never move a later gameplay decision.
#pragma once
#include "types.h"

struct InputCounters {
    u32 reads;          // PadRead calls
    u32 vib_ticks;      // active rumble slot ticks (VibControl)
    u32 vib_random;     // of those, random-strength draws (presentation generator)
    u32 vib_queued;     // rumble slots started (VibSet, VibSetDataCore)
    u32 motor_changes;  // motor commands sent
    u32 debug_prints;   // Pad_test (the debug key display: counted, not drawn)
};

extern "C" {
extern InputCounters input_cnt;
// The engine's presentation generator, one byte a draw (the image: host/e1_wraps.cpp; re4ref: host_present.cpp).
unsigned char eng_pres_u8(void);
// Controls (re4ref, RE4_SVC_CONTROL): 1 "padstick": the stick's direction bits need 81 units instead of 30 (a full push, 80, no longer counts); 2
// "rumblernd": the random rumble strength drawn from the behaviour generator (Rnd), the fault the split removes.
extern int input_control;
}
