// Native skeleton service (lane eng-svc): per-actor bone tables laid out for the SH-4's 16 KB operand cache, evaluated
// in one pass in parent order with the matrices batched through SH4ZAM's XMTRX, and a skin palette the renderer reads.
// The behaviour keeps calling the original entry points (MotionSetCore, MotionMove, cModel::partsWorldCalc,
// getPartsPtr, ...): skel.cpp gives them engine bodies on these tables. Write-up: docs/engine/SERVICES.md.
//
// One SkelTable per model with parts, one 32-byte aligned block, carved as below (n bones, cap = n rounded up to 8):
//
//   header        128 B   counts, owner, the record pointers, the IK chains' index
//   world   [n]    64 B   world matrix 3x4 (cCoord::mat) + accumulated scale (r_scale) + flags (MotionParts::flags)
//   lmat    [n]    48 B   local matrix (cCoord::l_mat)
//   pal     [n]    64 B   skin palette: world x bind (3x4) + 16 B pad; written once a tick (skel_publish)
//   prev    [n]    48 B   local matrix of the previous motion (cCoord::prevMat, MotionHokan)
//   soa  [33][cap]  4 B   pose pos xyz, ang xyz, scale xyz | blend-saved pos xyz, rot xyz, scale xyz |
//                         world position xyz (cCoord::world), world_old xyz | world_old2 xyz, bind xyz | addRot xyz
//   ikAng   [cap]   4 B   MotionParts::ikAng
//   hist    [n]    36 B   key history (MotionParts::hist, 6 channels x 3 axes, u16)
//   parent  [cap]   1 B   parent bone (0xFF the model, 0xFE an outside coordinate: extParent)
//   mbox    [cap]   1 B   mailbox: 1 the record is served after every evaluation and read back before (a bone code
//                         outside asked for), 2 served only (its ancestors: reached through pParent, read)
//   mlist   [cap]   1 B   the mailbox bones, in the order they joined
//   ik      [nIk]  96 B   IK chains (IkParts of the root: plane matrix, axis, direction)
//
// The cParts records stay (the behaviour holds pointers to them and walks pList); a record is the mailbox of its
// bone only once code outside the service has asked for it (getPartsPtr / GetPartsAddr, setParent).
#pragma once
#include "types.h"
#include "vec.h"

class cModel;
class cParts;
class cCoord;
struct MotionWork;

#define SKEL_PARENT_MODEL 0xFF
#define SKEL_PARENT_EXT 0xFE
#define SKEL_MAX_IK 8

struct SkelBone {      // 64 B
    f32 m[3][4];
    f32 rs[3];
    u32 flags;
};
struct SkelMat {       // 48 B
    f32 m[3][4];
};
struct SkelPal {       // 64 B
    f32 m[3][4];
    u32 pad[4];
};
struct SkelIk {        // 96 B: IkParts of a chain root
    f32 mat[3][4];
    Vec axis;
    Vec dir;
    u8 root;
    u8 pad[23];
};

// SoA rows of SkelTable::soa (each `cap` floats)
enum {
    SK_PX, SK_PY, SK_PZ, SK_AX, SK_AY, SK_AZ, SK_SX, SK_SY, SK_SZ,
    SK_MPX, SK_MPY, SK_MPZ, SK_MRX, SK_MRY, SK_MRZ, SK_MSX, SK_MSY, SK_MSZ,
    SK_WX, SK_WY, SK_WZ, SK_OX, SK_OY, SK_OZ,
    SK_O2X, SK_O2Y, SK_O2Z, SK_BX, SK_BY, SK_BZ, SK_RX, SK_RY, SK_RZ,
    SK_ROWS
};

struct SkelTable {
    // header: 128 B
    u16 n, cap;
    u16 nIk, serial;
    u32 bytes;
    cModel* model;
    cParts** rec;         // [n] the cParts records, chain order
    SkelBone* world;
    SkelMat* lmat;
    SkelPal* pal;
    SkelMat* prev;
    f32* soa;
    f32* ikAng;
    u16* hist;
    u8* parent;
    u8* mbox;
    SkelIk* ik;
    cCoord* extParent;    // the root's parent when it is not this model (cModel::setParent)
    u8* mlist;            // [nMbox] the mailbox bones
    f32* shadow;          // check build: what each ancestor record was given (21 floats a bone)
    u32 nMbox;
    u32 stamp;            // tick of the last publish
    u8 ikOf[SKEL_MAX_IK]; // unused slots 0xFF
    u32 pad[10];

    f32* row(int r) { return soa + r * cap; }
};

extern "C" {
// engine API
SkelTable* skel_table_of(const cModel* m);           // NULL: no parts
void skel_publish(SkelTable* t);                     // palette = world x bind for every bone (once a tick)
void skel_publish_all(void);                         // every live table
u32 skel_table_count(void);
SkelTable* skel_table_at(u32 i);
// counters (svc census and the cost indicator)
struct SkelCounters {
    u32 mat_local, mat_world, mat_world_slow, xmtrx_loads, add_rot, samples, hokan_bones, blend_bones, ik_chains,
        palette, serve_bones, pull_bones, entries, poison_bones, parent_mismatch, serve_ancestors, lost_writes;
};
extern SkelCounters skel_cnt;
// controls (lane eng-svc: each must make the equivalence check fail)
extern int skel_control_parent;   // >0: bone skel_control_parent's parent taken one bone too low (wrong by one)
extern int skel_control_no_ik;    // skip the IK pass
extern int skel_poison;           // check build: records outside the mailbox hold NaN
}
