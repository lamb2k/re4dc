// Native garment service (lane eng-svc5): the player characters' garments on the native cloth (services/cloth). The
// engine bodies for the entry points of the original unit pl_cloth.cpp: each garment's chain (its links, neighbours,
// swing limits, wind phase and rate, collision volumes) as one engine table, the set-up of a garment's chain from it,
// the per-tick dispatch to the cloth service (PenClothMove / PenClothMove3), and the procedural pose of Ashley's
// alternate-costume lapels (girlLapelMove). The behaviour keeps calling them by their original names (include/pl_cloth.h).
// Write-up: docs/engine/SERVICES.md section 33.
//
// No random draw here: the chains' wind and sway are the cloth service's, on the engine's presentation generator.
#pragma once
#include "types.h"

struct GarmentCounters {
    u32 sets;         // chains set up (PenClothSet calls)
    u32 moves;        // chain steps dispatched (PenClothMove + PenClothMove3)
    u32 lapels;       // girlLapelMove calls (two lapels each)
    u32 skipped;      // garments a costume leaves out (jacket without costume 0, holster without costume 1)
};

extern "C" {
extern GarmentCounters garment_cnt;
// Controls (re4ref, RE4_SVC_CONTROL): 1 "garmenthair": Leon's hair chain is not stepped on odd ticks; 2 "garmentskirt":
// Ashley's skirt always as stiff as when she is carried (Move_rate 0.9); 3 "lapelrate": the lapels' lift rate 1.4, not
// 1.3.
extern int garment_control;
}
