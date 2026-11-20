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
// Arithmetic: the original's operations in its order (the same math library calls), so on the PC every value is the
// original's bits when the wind is off. Random numbers (owner 2026-11-19, "Split it"): the cloth is presentation, so
// its draws (the wind phase, the floor jitter) come from the engine's presentation generator, never from the
// behaviour's Rnd. Here that is one xorshift32 state a chain (cloth_rng), seeded from the chain's set-up order: the
// draws of one chain do not depend on any other chain or on behaviour, and cost a shift-xor and a multiply.
#pragma once
#include "types.h"
#include "vec.h"

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
    u32 rng;             // the chain's presentation generator (xorshift32)
    u32 pad[5];
};

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
u32 cloth_chain_count(void);
ClothChain* cloth_chain_at(u32 i);
}
