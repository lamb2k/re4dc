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
//   soa  [27][cap]  4 B   pose pos xyz, ang xyz, scale xyz | blend-saved pos xyz, rot xyz, scale xyz |
//                         world position xyz (cCoord::world), bind xyz | addRot xyz
//   ikAng   [cap]   4 B   MotionParts::ikAng
//   hist    [n]    36 B   key history (MotionParts::hist, 6 channels x 3 axes, u16): only clips without baked keys
//                         (skel_mk.h) touch it
//   hslot   [cap]   1 B   the bone's history slot (0xFF: none)
//   hlist  [32]     1 B   the history bones, in the order they joined
//   hold   [32]    32 B   world_old xyz, world_old2 xyz (+ 8 B pad) of the history bones: the bones code outside asked
//                         for (lane eng-svc2: the census shows only those bones' history is read; updateOldPos moves
//                         these and nothing else)
//   parent  [cap]   1 B   parent bone (0xFF the model, 0xFE an outside coordinate: extParent)
//   mbox    [cap]   1 B   mailbox: 1 a bone code outside asked for (served after every entry, taken back at the next
//                         entry after it was handed out again), 2 its ancestors (reached through pParent: served
//                         mat, world, r_scale, scale), bit 7 handed out since the last entry
//   mlist   [cap]   1 B   the mailbox bones, in the order they joined
//   handed  [cap]   1 B   the bones handed out since the last entry
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
    SK_WX, SK_WY, SK_WZ, SK_BX, SK_BY, SK_BZ, SK_RX, SK_RY, SK_RZ,
    SK_ROWS
};
#define SKEL_MAX_HIST 32
struct SkelHist {      // 32 B: a history bone's world_old and world_old2
    f32 old[3];
    f32 old2[3];
    u32 pad[2];
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
    u8* handed;           // [nHanded] bones handed out since the last entry (taken back at the next)
    f32* shadow;          // check build: what each mailbox record was given (49 floats a bone)
    u32 nMbox, nHanded;
    u8 nRoot, root[7];    // bones whose parent is the model or an outside coordinate
    u32 stamp;            // tick of the last publish
    u8 ikOf[SKEL_MAX_IK]; // unused slots 0xFF
    SkelHist* hold;       // [SKEL_MAX_HIST] the history bones' world_old / world_old2
    u8* hslot;            // [cap] bone -> history slot, 0xFF none
    u8* hlist;            // [SKEL_MAX_HIST] slot -> bone
    u32 nHist;
    u32 nOld;             // updateOldPos calls so far (a history bone that joins later starts unknown)
    f32* base;            // until the first updateOldPos: every bone's world_old and world_old2 (6 rows x cap), so a
                          // bone that joins the history set during set-up starts with the original's values

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
        palette, serve_bones, pull_bones, entries, poison_bones, parent_mismatch, serve_ancestors, lost_writes,
        samp_int, samp_frac, samp_end, mk_bound, mk_unbound, mk_rows, mk_cold, mk_orig,
        hist_join, hist_moves, hist_full, hist_late;
};
extern SkelCounters skel_cnt;
// controls (lane eng-svc: each must make the equivalence check fail)
extern int skel_control_parent;   // >0: bone skel_control_parent's parent taken one bone too low (wrong by one)
extern int skel_control_no_ik;    // skip the IK pass
extern int skel_poison;           // check build: records outside the mailbox hold NaN
extern int skel_control_mk;       // baked motion keys: the row of the next frame (lane eng-svc2 control)
extern int skel_control_hist;     // 1: no bone keeps its history; 2: the history never moves (lane eng-svc2 controls)
}
