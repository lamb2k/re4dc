// boss_svc.h (lane eng-e2c): El Gigante's service entry points made native (services/boss/). The hosted boss (src/em2b)
// and its arena (src/st1/r119) call them by their original names; the hosted copies are made weak (game/boss.mk), so
// these bodies are reached. docs/engine/lanes/eng-e2c.md lists, per function, its class and how it differs from the
// original.
#pragma once
#include "types.h"

extern "C" {
// Counters: the boss image's report (boss/boss_fx.cpp, "E2C" line) and the PC check's log.
struct BossSvcCounters {
    u32 cam_moves[4];   // event cameras: blow, stamp, escape, parasite attack
    u32 cam_pulls;      // escape camera pulled in to a scenery hit
    u32 quakes;         // em2bQuakeSet calls
    u32 quake_sets;     // of those, a quake requested (within 20000 of the camera)
    u32 feet;           // em2bFootSe calls that landed a foot
    u32 screen_tests;   // em2bInScreenCk calls
    u32 necks;          // em2bNeckMove calls
    u32 blends;         // em2bBlendMotSet and plBlendMotSet calls
    u32 squashes;       // em2bScaleCompress calls that squashed
    u32 giant_releases; // cEm2b destructor calls (the pool released a giant)
    u32 held_released;  // objects a giant held, released with it
    u32 empty_releases; // the tree's and the torch's destructors (nothing to release)
    u32 oba_made;       // SetObaModel: oba collision objects made
    u32 oba_refused;    // SetObaModel: refused (object pool full, or the model not set up)
    u32 oba_moves;      // cObjObaModel::move calls
    u32 oba_orphans;    // oba objects released because their parent died
    u32 push_tests;     // em2bObaHitCk calls
    u32 pushes;         // giants pushed apart
    u32 cloths;         // em2bClothSet: arm cloths handed to the cloth service
    u32 chains;         // chain objects asked for (rope, arm chains)
    u32 texrender_refused;   // room 224's texture-render manager: none (the renderer has none yet)
    u32 thunder_draws;  // the thunder's interval draws (the presentation generator)
    u32 thunders;       // thunders requested (flash effect and sound)
    u32 thunder_flashes;// hut-light flashes set by the effect tool's callback
};
extern BossSvcCounters boss_cnt;
// Controls (set only by the PC check, hostref svc/e2c_dump.cpp RE4_SVC_CONTROL; each must make the comparison fail):
// 1 "bosscam": the event cameras' eye 1% further from the target; 2 "bossquake": the quake's nearest band 4500 instead
// of 5000; 3 "bossneck": the neck's damping 0.85 instead of 0.9; 4 "bossblend": the blend weight |Blend| / 255;
// 5 "bossheld": a giant's destructor keeps its third chain object; 6 "bossoba": an oba object's ground clamp 1500
// instead of 2000 above the parent; 7 "bosspush": giants pushed apart to 2900 instead of 3000; 8 "bossrope": the rope's
// constraint iterations 99 instead of 100; 9 "bossthunder": the thunder's interval 5 ticks longer.
extern int boss_control;
}
