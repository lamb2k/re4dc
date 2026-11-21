// Native cloth service (lane eng-svc2): the pendulum chains (Leon's hair and jacket, Ashley's hair, skirt and sweater,
// enemy coats and hair) simulated on compact link arrays and the skeleton service's bone tables. The behaviour keeps
// calling the original entry points (PenClothSet, PenClothMove, PenClothMove3, PenClothFixSet / FixClear: pl_cloth,
// em_cloth, obj units); cloth.cpp gives them engine bodies. Write-up: docs/engine/SERVICES.md section 12.
//
// What the original does per link and per tick: PEN_PARTS(m, c, no) -> cModel::getPartsPtr walks the model's parts
// list to the link (O(no) records of 472 B) for every link in every pass (wind, angle limit, Bundle_num constraint
// passes, matrices) and every neighbour lookup, and keeps the link's state (PenParts) inside the parts record. Here a
// chain is resolved once (PenClothSet): every link's bone, its upper and side neighbours as link indices, the
// collision volumes' bones; the state of a link is one 64-byte record (two operand-cache lines) and the bones are
// read and written in the skeleton's tables (world matrix, world position, the root's kept history).
//
// One ClothChain per PenCloth, one 32-byte aligned block from the cloth pool:
//   header      64 B   owner model, its table, the PenCloth, counts
//   link [n]    64 B   pos, oldPos, speed, nrm (Vec each), len, bone, upper link, hit, fix flag, side links
//   cold [n]    48 B   rest direction (PenClothReset), half distances to the four side links, fixed position
//   atBone [2 x volumes] the collision volumes' two bones
// Arithmetic (lane eng-svc3): the chain's tick is one SH4ZAM kernel (cloth_kernel.h), one pass over the links; the
// same stages in the original's pass order give the original's bits on the PC (cloth_passes). Random numbers (owner
// 2026-11-19, "Split it"): the cloth is presentation, so its draws (the wind phase, the floor jitter) come from the
// engine's presentation generator (pres_rng.h), one stream a chain seeded from the chain's set-up order, never from
// the behaviour's Rnd.
#pragma once
#include "types.h"
#include "vec.h"
#include "pres_rng.h"

class cModel;
struct PenCloth;
struct SkelTable;

#define CLOTH_NONE 0xFF

struct ClothLink {       // 64 B
    Vec pos;             // 0x00 link end (PenParts::pos)
    Vec oldPos;          // 0x0C
    Vec speed;           // 0x18
    Vec nrm;             // 0x24 unit rest direction in parts space
    f32 len;             // 0x30
    u8 bone;             // 0x34 the link's bone in the owner's table
    u8 up;               // 0x35 upper link (pParent), CLOTH_NONE: a root link
    u8 hit;              // 0x36
    u8 fix;              // 0x37 bit0: pinned at cold.fixPos (PenClothFixSet)
    u8 side[4];          // 0x38 left, right, up-left, up-right links (CLOTH_NONE)
    u32 pad;
};
struct ClothCold {       // 48 B
    Vec dir;             // rest direction (PenParts::dir)
    f32 dist[4];         // half distances to the side links (distL, distR, distUL, distUR)
    Vec fixPos;
    u32 pad[2];
};
struct ClothChain {      // 64 B header
    PenCloth* c;
    cModel* m;
    SkelTable* t;
    SkelTable* tAt;      // the table the collision volumes hang on (PenCloth::pEm_at or the owner)
    ClothLink* link;
    ClothCold* cold;
    u8* atBone;          // [2 * nAt]
    u16 n, nAt;
    u32 serial;
    u32 bytes;
    PresRng rng;         // the chain's presentation stream (pres_rng.h)
    u8 skirt;            // lane eng-cloth1: the chain is Ashley's skirt (48 links, 11 volumes): the look arms' chain
    u8 phase;            // lane eng-cloth1: ticks since the chain's last full step (look arms c and d)
    u16 pad16;
    u32 pad[4];
};
// Lane eng-cloth1: the look options, run-time lab arms (boot files, read once at the first set-up; on the PC reference
// RE4_SVC_CLOTH_ARM=cap|pass2|half|far|far0). Each changes Ashley's skirt only, alone; none is the default (the owner
// chooses from clips). 0 none, 1 CLOTHCAP (the leg spheres as three capsules), 2 CLOTHPASS2 (two constraint passes
// instead of four), 3 CLOTHHALF (stepped every other tick, the pose held between), 4 CLOTHFAR (stepped every fourth
// tick, pose held between, when the skirt is more than 6 m from the camera or behind it), 5 CLOTHFAR0 (the far rule
// with its distance 0: every fourth tick always; the far arm's control and the far look up close).
extern "C" int cloth_arm;

extern "C" {
// counters (svc census and the cost indicator)
struct ClothCounters {
    u32 chains, fallback, moves, links, at_volumes, resets;
};
extern ClothCounters cloth_cnt;
// controls (lane eng-svc2: each must make the equivalence check fail)
extern int cloth_control_short;      // the last link of every chain left out (wrong chain length)
extern int cloth_control_nogravity;  // gravity off
extern int cloth_control_wind;       // the wind's push twice as strong (the statistics check must fail)
extern int cloth_passes;             // 1: the kernel in the original's pass order (the exactness proof); 2: in one pass
                                     // (measured, rejected); 0: fused (lane eng-svc3)
u32 cloth_chain_count(void);
ClothChain* cloth_chain_at(u32 i);
}
