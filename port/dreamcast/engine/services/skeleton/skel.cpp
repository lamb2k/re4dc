// Native skeleton service (lane eng-svc). Table layout and the reasons for it: skel.h and docs/engine/SERVICES.md.
//
// The original evaluation units (game/motion.cpp MotionSetCore / MotionMove / MotionMoveCore / MotionHokan /
// MotionClear / PartsWorldPosCalc, game/ik.cpp, the parts half of game/model.cpp) are replaced by the bodies below,
// which work on the actor's SkelTable instead of its chain of 472-byte cParts records:
//   - the local pose, the key histories and the motion flags of every bone live in the table (structure of arrays);
//   - partsMatCalc, the world pass, the hokan and the blends run over the table in chain (parent) order, the world
//     pass with the parent matrix in SH4ZAM's XMTRX (kept there while the chain goes parent -> child);
//   - the IK solves on the table;
//   - the palette (world x bind) is written once a tick by skel_publish for the renderer.
// What stays original and is called as it is: the key decoder (HermiteInterpolation, motion.cpp: the motion data
// format), the sequence clock and the root motion (MotionSequenceCtrl, MotionGetSpeed, MotionAddSpeed: MotionWork
// state the behaviour reads), the math library helpers the rare paths use (quaternions, inverses, rotations about
// an axis), and every function of the model record that does not touch a bone.
//
// The behaviour's view: a cParts record is the mailbox of its bone once outside code has asked for it
// (getPartsPtr, GetPartsAddr, setParent's parent). Before every evaluation the table takes the mailbox records' fields
// back (the behaviour may have written them: eyelid angles, waist addRot, cloth matrices), after it the records get
// the table's values. Records outside the mailbox are never written (the check build fills them with NaN).
//
// Arithmetic: every float operation is the original's, in its order (contraction off), so on the PC the tables
// carry the original's bits; XMTRX on the SW back-end forms each element as the C matrix library does (addition
// commutes exactly). On the SH-4, FTRV rounds differently: the PC proof covers the layout and the data flow, the
// SH-4 build's tolerance is the plays-right tolerance.
#include "skel.h"
#include "model.h"
#include "motion.h"
#include "em.h"
#include "global.h"
#include "db_log.h"
#include "math_sub.h"
#include "cam_ctrl.h"
#include "atari.h"
#include "skel_xm.h"
#include "native_motion.h"

extern "C" void* memset(void* dst, int c, unsigned int n);
extern "C" void* memcpy(void* dst, const void* src, unsigned int n);
extern "C" float sinf(float);
extern "C" float cosf(float);
extern "C" float acosf(float);
extern "C" void* svc_pool_base(u32* bytes);   // host: the engine's skeleton and collision pool
extern "C" void calcModelAddr(ModelData* data);
extern const Vec vecZero;

extern "C" {
SkelCounters skel_cnt;
int skel_control_parent;
int skel_control_no_ik;
int skel_poison;
}

#define PTR_OK(p) ((u32) (p) >= RE4_MEM_LO && (u32) (p) <= RE4_MEM_HI)
#define MOT_HIST_W(w, flip, n) ((u16*) ((u8*) (w) + ((flip) * 12 + 8 + (n) * 6)))

namespace {

// ---------------------------------------------------------------------------------------------------------------
// pool and registry
struct PoolBlk {
    u32 size;   // payload bytes
    u32 used;
    u32 pad[6];
};
u8* g_pool;
u32 g_pool_bytes;

void* pool_alloc(u32 bytes)
{
    if (!g_pool) {
        g_pool = (u8*) svc_pool_base(&g_pool_bytes);
        PoolBlk* b = (PoolBlk*) g_pool;
        b->size = g_pool_bytes - sizeof(PoolBlk);
        b->used = 0;
    }
    const u32 need = (bytes + 31u) & ~31u;
    for (u8* p = g_pool; p < g_pool + g_pool_bytes;) {
        PoolBlk* b = (PoolBlk*) p;
        if (!b->used) {
            for (PoolBlk* nx = (PoolBlk*) (p + sizeof(PoolBlk) + b->size); (u8*) nx < g_pool + g_pool_bytes && !nx->used;
                 nx = (PoolBlk*) (p + sizeof(PoolBlk) + b->size))
                b->size += sizeof(PoolBlk) + nx->size;
            if (b->size >= need) {
                if (b->size >= need + sizeof(PoolBlk) + 32) {
                    PoolBlk* r = (PoolBlk*) (p + sizeof(PoolBlk) + need);
                    r->size = b->size - need - sizeof(PoolBlk);
                    r->used = 0;
                    b->size = need;
                }
                b->used = 1;
                memset(p + sizeof(PoolBlk), 0, b->size);
                return p + sizeof(PoolBlk);
            }
        }
        p += sizeof(PoolBlk) + b->size;
    }
    pLog->err(0, 0, "skel: pool exhausted (%u bytes)", bytes);
    return 0;
}
void pool_free(void* q)
{
    if (q) ((PoolBlk*) ((u8*) q - sizeof(PoolBlk)))->used = 0;
}

constexpr u32 kMaxTables = 64;
SkelTable* g_tab[kMaxTables];
u32 g_ntab;
u16 g_serial;
// parts pool slot -> table index + 1 / bone (the mailbox resolver)
u8 g_slot_tab[4096];
u8 g_slot_bone[4096];

SkelTable* find_table(const cModel* m)
{
    for (u32 i = 0; i < g_ntab; i++)
        if (g_tab[i]->model == m) return g_tab[i];
    return 0;
}
int slot_of(const void* rec)
{
    const u32 lo = (u32) PartsMgr.pArray, a = (u32) rec;
    if (!PartsMgr.pArray || a < lo || a >= lo + PartsMgr.size * PartsMgr.nArray) return -1;
    const u32 s = (a - lo) / PartsMgr.size;
    return s < 4096 && (a - lo) % PartsMgr.size == 0 ? (int) s : -1;
}
SkelTable* table_of_record(const void* rec, int* bone)
{
    const int s = slot_of(rec);
    if (s < 0 || !g_slot_tab[s]) return 0;
    *bone = g_slot_bone[s];
    return g_tab[g_slot_tab[s] - 1];
}
void map_slots(u32 ti, SkelTable* t, bool on)
{
    for (u32 b = 0; b < t->n; b++) {
        const int s = slot_of(t->rec[b]);
        if (s < 0) continue;
        g_slot_tab[s] = on ? (u8) (ti + 1) : 0;
        g_slot_bone[s] = on ? (u8) b : 0;
    }
}

u32 align32(u32 x) { return (x + 31u) & ~31u; }

// ---------------------------------------------------------------------------------------------------------------
// mailbox: the records outside code sees
const f32 kNaN = __builtin_nanf("");

void poison_record(cParts* r)
{
    f32* m = &r->mat[0][0];
    for (int i = 0; i < 12; i++) m[i] = kNaN;
    m = &r->l_mat[0][0];
    for (int i = 0; i < 12; i++) m[i] = kNaN;
    m = &r->prevMat[0][0];
    for (int i = 0; i < 12; i++) m[i] = kNaN;
    r->world.x = r->world.y = r->world.z = kNaN;
    r->world_old = r->world;
    r->world_old2 = r->world;
    r->pos = r->world;
    r->ang = r->world;
    r->scale = r->world;
    r->r_scale = r->world;
    r->addRot = r->world;
    skel_cnt.poison_bones++;
}

// the check build's copy of what an ancestor record was given (21 floats a bone): a later difference is a write the
// table would not take back (counted; must stay 0)
void shadow_ancestor(SkelTable* t, u32 b)
{
    if (!t->shadow) return;
    cParts* r = t->rec[b];
    f32* d = t->shadow + 21 * b;
    memcpy(d, r->mat, 48);
    d[12] = r->world.x; d[13] = r->world.y; d[14] = r->world.z;
    d[15] = r->r_scale.x; d[16] = r->r_scale.y; d[17] = r->r_scale.z;
    d[18] = r->scale.x; d[19] = r->scale.y; d[20] = r->scale.z;
}
void check_ancestor(SkelTable* t, u32 b)
{
    if (!t->shadow) return;
    cParts* r = t->rec[b];
    const f32* d = t->shadow + 21 * b;
    f32 now[21];
    memcpy(now, r->mat, 48);
    now[12] = r->world.x; now[13] = r->world.y; now[14] = r->world.z;
    now[15] = r->r_scale.x; now[16] = r->r_scale.y; now[17] = r->r_scale.z;
    now[18] = r->scale.x; now[19] = r->scale.y; now[20] = r->scale.z;
    if (__builtin_memcmp(now, d, sizeof now) != 0) skel_cnt.lost_writes++;
}
void serve_ancestor(SkelTable* t, u32 b)
{
    cParts* r = t->rec[b];
    memcpy(r->mat, t->world[b].m, 48);
    r->r_scale.x = t->world[b].rs[0];
    r->r_scale.y = t->world[b].rs[1];
    r->r_scale.z = t->world[b].rs[2];
    const u32 c = t->cap;
    const f32* s = t->soa;
    r->world.x = s[SK_WX * c + b]; r->world.y = s[SK_WY * c + b]; r->world.z = s[SK_WZ * c + b];
    r->scale.x = s[SK_SX * c + b]; r->scale.y = s[SK_SY * c + b]; r->scale.z = s[SK_SZ * c + b];
    shadow_ancestor(t, b);
    skel_cnt.serve_ancestors++;
}
void serve(SkelTable* t, u32 b)
{
    cParts* r = t->rec[b];
    memcpy(r->mat, t->world[b].m, 48);
    memcpy(r->l_mat, t->lmat[b].m, 48);
    r->r_scale.x = t->world[b].rs[0];
    r->r_scale.y = t->world[b].rs[1];
    r->r_scale.z = t->world[b].rs[2];
    r->motParts.flags = t->world[b].flags;
    const u32 c = t->cap;
    const f32* s = t->soa;
    r->pos.x = s[SK_PX * c + b]; r->pos.y = s[SK_PY * c + b]; r->pos.z = s[SK_PZ * c + b];
    r->ang.x = s[SK_AX * c + b]; r->ang.y = s[SK_AY * c + b]; r->ang.z = s[SK_AZ * c + b];
    r->scale.x = s[SK_SX * c + b]; r->scale.y = s[SK_SY * c + b]; r->scale.z = s[SK_SZ * c + b];
    r->world.x = s[SK_WX * c + b]; r->world.y = s[SK_WY * c + b]; r->world.z = s[SK_WZ * c + b];
    r->world_old.x = s[SK_OX * c + b]; r->world_old.y = s[SK_OY * c + b]; r->world_old.z = s[SK_OZ * c + b];
    r->world_old2.x = s[SK_O2X * c + b]; r->world_old2.y = s[SK_O2Y * c + b]; r->world_old2.z = s[SK_O2Z * c + b];
    r->addRot.x = s[SK_RX * c + b]; r->addRot.y = s[SK_RY * c + b]; r->addRot.z = s[SK_RZ * c + b];
    skel_cnt.serve_bones++;
}
void pull(SkelTable* t, u32 b)
{
    cParts* r = t->rec[b];
    memcpy(t->world[b].m, r->mat, 48);
    memcpy(t->lmat[b].m, r->l_mat, 48);
    t->world[b].rs[0] = r->r_scale.x;
    t->world[b].rs[1] = r->r_scale.y;
    t->world[b].rs[2] = r->r_scale.z;
    t->world[b].flags = r->motParts.flags;
    const u32 c = t->cap;
    f32* s = t->soa;
    s[SK_PX * c + b] = r->pos.x; s[SK_PY * c + b] = r->pos.y; s[SK_PZ * c + b] = r->pos.z;
    s[SK_AX * c + b] = r->ang.x; s[SK_AY * c + b] = r->ang.y; s[SK_AZ * c + b] = r->ang.z;
    s[SK_SX * c + b] = r->scale.x; s[SK_SY * c + b] = r->scale.y; s[SK_SZ * c + b] = r->scale.z;
    s[SK_WX * c + b] = r->world.x; s[SK_WY * c + b] = r->world.y; s[SK_WZ * c + b] = r->world.z;
    s[SK_OX * c + b] = r->world_old.x; s[SK_OY * c + b] = r->world_old.y; s[SK_OZ * c + b] = r->world_old.z;
    s[SK_O2X * c + b] = r->world_old2.x; s[SK_O2Y * c + b] = r->world_old2.y; s[SK_O2Z * c + b] = r->world_old2.z;
    s[SK_RX * c + b] = r->addRot.x; s[SK_RY * c + b] = r->addRot.y; s[SK_RZ * c + b] = r->addRot.z;
    skel_cnt.pull_bones++;
}

void refresh_roots(SkelTable* t);
// Every engine entry: begin() takes the mailbox records back, end() serves them.
struct Scope {
    SkelTable* t;
    explicit Scope(SkelTable* tt) : t(tt)
    {
        skel_cnt.entries++;
        if (!t) return;
        refresh_roots(t);
        for (u32 i = 0; i < t->nMbox; i++) {
            const u32 b = t->mlist[i];
            if (t->mbox[b] == 1) pull(t, b);
            else check_ancestor(t, b);
        }
    }
    ~Scope()
    {
        if (!t) return;
        for (u32 i = 0; i < t->nMbox; i++) {
            const u32 b = t->mlist[i];
            if (t->mbox[b] == 1) serve(t, b);
            else serve_ancestor(t, b);
        }
    }
};

void mailbox_add(SkelTable* t, u32 b)
{
    if (b >= t->n || t->mbox[b] == 1) return;
    if (!t->mbox[b]) t->mlist[t->nMbox++] = (u8) b;
    t->mbox[b] = 1;   // direct: full record both ways
    serve(t, b);
    // its ancestors: code reaches a parent through cCoord::pParent (read)
    for (u32 a = t->parent[b]; a < t->n && !t->mbox[a]; a = t->parent[a]) {
        t->mlist[t->nMbox++] = (u8) a;
        t->mbox[a] = 2;
        serve_ancestor(t, a);
    }
}

// a root bone's parent from its record (cModel::setParent, objWep and the event code write it there)
void refresh_roots(SkelTable* t)
{
    for (u32 b = 0; b < t->n; b++) {
        const u8 p = t->parent[b];
        if (p != SKEL_PARENT_MODEL && p != SKEL_PARENT_EXT) continue;
        cCoord* rp = t->rec[b]->pParent;
        if (rp == (cCoord*) t->model) {
            t->parent[b] = SKEL_PARENT_MODEL;
        } else {
            t->parent[b] = SKEL_PARENT_EXT;
            t->extParent = rp;
        }
    }
}

// ---------------------------------------------------------------------------------------------------------------
// the parent's coordinate (world matrix and accumulated scale) of bone b
struct ParentRef {
    const f32 (*m)[4];
    const f32* rs;
    int bone;   // -1: not a bone of this table
};
ParentRef parent_of(SkelTable* t, u32 b)
{
    ParentRef r;
    u32 p = t->parent[b];
    if (skel_control_parent > 0 && (int) b == skel_control_parent && p != SKEL_PARENT_MODEL && p != SKEL_PARENT_EXT && p > 0)
        p--;   // control: this bone's parent wrong by one
    if (p == SKEL_PARENT_MODEL) {
        r.m = t->model->mat;
        r.rs = &t->model->r_scale.x;
        r.bone = -1;
    } else if (p == SKEL_PARENT_EXT) {
        r.m = t->extParent->mat;
        r.rs = &t->extParent->r_scale.x;
        r.bone = -1;
    } else {
        r.m = t->world[p].m;
        r.rs = t->world[p].rs;
        r.bone = (int) p;
    }
    return r;
}

// ---------------------------------------------------------------------------------------------------------------
// kernels (original arithmetic, original order)
inline void rot_matrix(f32 (*m)[4], f32 ax, f32 ay, f32 az)   // math_sub.cpp RotMatrix
{
    f32 sx = sinf(ax), sy = sinf(ay), sz = sinf(az);
    f32 cx = cosf(ax), cy = cosf(ay), cz = cosf(az);
    f32 szcx = sz * cx, szsx = sz * sx, czsx = cz * sx, czcx = cz * cx;
    m[0][0] = cz * cy;
    m[0][1] = czsx * sy - szcx;
    m[0][2] = czcx * sy + szsx;
    m[0][3] = 0.0f;
    m[1][0] = sz * cy;
    m[1][1] = szsx * sy + czcx;
    m[1][2] = szcx * sy - czsx;
    m[1][3] = 0.0f;
    m[2][0] = -sy;
    m[2][1] = cy * sx;
    m[2][2] = cy * cx;
    m[2][3] = 0.0f;
}

// partsMatCalc: l_mat = R(ang) T(pos) S(scale), copied to mat
void mat_calc(SkelTable* t)
{
    const u32 c = t->cap;
    f32* s = t->soa;
    for (u32 b = 0; b < t->n; b++) {
        f32 (*m)[4] = t->lmat[b].m;
        rot_matrix(m, s[SK_AX * c + b], s[SK_AY * c + b], s[SK_AZ * c + b]);
        m[0][3] = s[SK_PX * c + b];
        m[1][3] = s[SK_PY * c + b];
        m[2][3] = s[SK_PZ * c + b];
        const f32 sx = s[SK_SX * c + b], sy = s[SK_SY * c + b], sz = s[SK_SZ * c + b];
        m[0][0] *= sx; m[0][1] *= sy; m[0][2] *= sz;
        m[1][0] *= sx; m[1][1] *= sy; m[1][2] *= sz;
        m[2][0] *= sx; m[2][1] *= sy; m[2][2] *= sz;
        memcpy(t->world[b].m, m, 48);
    }
    skel_cnt.mat_local += t->n;
}

// The world pass (cModel::partsWorldCalc): one pass in chain order; parent x local through XMTRX. XMTRX keeps the
// last bone's world while the next bone is its child, so a parent -> child run loads nothing.
void world_calc(SkelTable* t)
{
    cModel* mdl = t->model;
    mdl->r_scale = mdl->scale;
    const u32 c = t->cap;
    f32* s = t->soa;
    int inX = -2;   // bone whose world is in XMTRX (-2: none)
    for (u32 b = 0; b < t->n; b++) {
        SkelBone& w = t->world[b];
        if (w.flags & 2) continue;
        ParentRef pr = parent_of(t, b);
        Vec tmp;
        tmp.x = t->lmat[b].m[0][3];
        tmp.y = t->lmat[b].m[1][3];
        tmp.z = t->lmat[b].m[2][3];
        Vec wp;
        PSMTXMultVec(pr.m, &tmp, &wp);
        if (pr.rs[0] != pr.rs[1] || pr.rs[1] != pr.rs[2]) {
            // a non-uniform parent scale: P S^-1 L S (the original's two scale concatenations, as column scales
            // of XMTRX). Blended poses make r_scale's three components differ by rounding, so most bones of a
            // blended pose come here. XMTRX's translation is then not the world position: the next bone reloads.
            Vec sc;
            sc.x = (pr.rs[0] != 0.0f) ? 1.0f / pr.rs[0] : 0.0f;
            sc.y = (pr.rs[1] != 0.0f) ? 1.0f / pr.rs[1] : 0.0f;
            sc.z = (pr.rs[2] != 0.0f) ? 1.0f / pr.rs[2] : 0.0f;
            if (pr.bone < 0 || pr.bone != inX) {
                skel_xm_load_3x4(&pr.m[0][0]);
                skel_cnt.xmtrx_loads++;
            }
            skel_xm_apply_scale(sc.x, sc.y, sc.z);
            skel_xm_apply_3x4(&t->lmat[b].m[0][0]);
            skel_xm_apply_scale(pr.rs[0], pr.rs[1], pr.rs[2]);
            skel_xm_store_3x4(&w.m[0][0]);
            skel_cnt.mat_world_slow++;
            inX = -2;
        } else {
            if (pr.bone < 0 || pr.bone != inX) {
                skel_xm_load_3x4(&pr.m[0][0]);
                skel_cnt.xmtrx_loads++;
            }
            skel_xm_apply_3x4(&t->lmat[b].m[0][0]);
            skel_xm_store_3x4(&w.m[0][0]);
            skel_cnt.mat_world++;
            inX = (int) b;
        }
        if (w.flags & 0x40000000) {
            Mtx m2;
            w.flags &= ~0x40000000;
            PSMTXRotRad(m2, 'x', s[SK_RX * c + b]);
            PSMTXConcat(w.m, m2, w.m);
            PSMTXRotRad(m2, 'z', s[SK_RZ * c + b]);
            PSMTXConcat(w.m, m2, w.m);
            PSMTXRotRad(m2, 'y', s[SK_RY * c + b]);
            PSMTXConcat(m2, w.m, w.m);
            skel_cnt.add_rot++;
            inX = -2;
        }
        s[SK_WX * c + b] = wp.x;
        s[SK_WY * c + b] = wp.y;
        s[SK_WZ * c + b] = wp.z;
        w.m[0][3] = wp.x;
        w.m[1][3] = wp.y;
        w.m[2][3] = wp.z;
        w.rs[0] = pr.rs[0] * s[SK_SX * c + b];
        w.rs[1] = pr.rs[1] * s[SK_SY * c + b];
        w.rs[2] = pr.rs[2] * s[SK_SZ * c + b];
    }
    MOTION(mdl)->Pos_world = mdl->pos;
}

// motion.cpp MotionMoveCore: the pose at the current sequence frame, into the table
void move_core(SkelTable* t, MotionWork* w)
{
    cModel* m = t->model;
    HermitePrm prm;
    HermitePrm* pp = &prm;
    AttachCamera* cam;
    u16* flipTbl = MOTION(m)->flip;
    int n = w->Joint_num;
    int i = 0;
    int flip;
    const u32 c = t->cap;
    f32* s = t->soa;

    if (w->pMot == 0) return;
    if (!(w->Mot_attr & 0x8000)) {
        w->Mot_frame = (f32) (w->Seq.frame >> 6) + (f32) (w->Seq.frame & 0x3F) * 0.015625f;
    } else {
        w->Mot_frame = w->Seq_frame;
    }
    w->Mot_frame_old = w->Mot_frame_sav;
    w->Mot_frame_sav = w->Mot_frame;
    pp->frame = w->Mot_frame;
    pp->maxFrame = w->Mot_frame_max;
    pp->flags = 0;
    if (w->Mot_attr & 4) {
        if (w->pSeq_top == 0) pp->flags = 4;
    }
    if (w->Mot_attr & 2) {
        if (!(w->Mot_attr & 0x1000)) pp->flags |= 2;
        else pp->flags &= ~2;
    } else {
        if (w->Mot_attr & 0x1000) pp->flags |= 2;
        else pp->flags &= ~2;
    }
    if (!(w->Mot_flag & 0x40000000)) {
        RotMatrix(m->mat, &m->ang);
        TransMatrix(m->mat, &m->pos);
        ScaleMatrix(m->mat, &m->scale);
    }
    flip = (w->Mot_flag & 0x08000000) ? 1 : 0;
    w->Mot_flag &= ~0x04000000;
    cam = 0;
    if (w->pAttachCam != 0 && w->pAttachCam->type != 0) cam = w->pAttachCam;
    if ((w->Mot_attr & 0x40) && flipTbl == 0) {
        w->Mot_attr &= ~0x40;
        pLog->err(0, 0, "MotionMoveCore():%d Flip Info Error!", 1067);
    }
    u32* keys = w->pHermite_data;
    Re4dcMotionLease lease(w->pMot, &keys, keys);
    do {
        int kind = w->pJoint_kind[i] & 0xFF;
        u16 info = w->pJoint_kind[i];
        int ch = (info >> 8) & 0xF;
        int pno = w->pJoint_no[i];
        if (ch == 6 || ch == 7) {
            if (cam == 0) continue;
            pp->type = info >> 12;
            pp->key = (u8*) keys[i];
            if (i == cam->parts[0]) {
                HermiteInterpolation(pp, &cam->out[0], cam->hist[0]);
                if (w->Mot_attr & 0x40) cam->out[0].x = -cam->out[0].x;
            } else if (i == cam->parts[1]) {
                HermiteInterpolation(pp, &cam->out[1], cam->hist[1]);
                if (w->Mot_attr & 0x40) cam->out[1].x = -cam->out[1].x;
            } else if (i == cam->parts[2]) {
                HermiteInterpolation(pp, &cam->out[2], cam->hist[2]);
                if (w->Mot_attr & 0x40) cam->out[2].y = -cam->out[2].y;
            } else if (i == cam->parts[3]) {
                HermiteInterpolation(pp, &cam->out[3], cam->hist[3]);
            } else if (i == cam->parts[4]) {
                HermiteInterpolation(pp, &cam->out[4], cam->hist[4]);
                cam->frame = (u8) (cam->out[4].y / 100.0f);
            }
            skel_cnt.samples++;
            continue;
        }
        if (w->Mot_attr & 0x40) {
            u16 fp = flipTbl[pno];
            if (fp != 0xFFFF) pno = (s16) fp;
        }
        if (pno >= m->nParts) {
            pLog->err(0, 0, "MotionMoveCore(): Invalid parts %d.", pno);
        }
        if (pno < 0 || (u32) pno >= t->n) continue;
        u32& fl = t->world[pno].flags;
        if (fl & 0x20000000) continue;
        fl |= 0x10010000;
        if ((s32) w->Mot_flag < 0) fl |= 0x80000000;
        pp->type = w->pJoint_kind[i] >> 12;
        pp->key = (u8*) keys[i];
        if (fl & 0x04000000) pp->flags |= 8;
        else pp->flags &= ~8;
        u16* h = t->hist + pno * 18;
        Vec v;
        int row;
        if (kind & 2) {
            v.x = s[SK_AX * c + pno]; v.y = s[SK_AY * c + pno]; v.z = s[SK_AZ * c + pno];
            HermiteInterpolation(pp, &v, flip ? h + 9 : h + 0);
            VecRadLimit(&v);
            if (w->Mot_attr & 0x40) { v.y = -v.y; v.z = -v.z; }
            row = SK_AX;
        } else if (kind & 4) {
            v.x = s[SK_PX * c + pno]; v.y = s[SK_PY * c + pno]; v.z = s[SK_PZ * c + pno];
            HermiteInterpolation(pp, &v, flip ? h + 12 : h + 3);
            if (w->Mot_attr & 0x40) v.x = -v.x;
            row = SK_PX;
        } else if (kind & 8) {
            v.x = s[SK_SX * c + pno]; v.y = s[SK_SY * c + pno]; v.z = s[SK_SZ * c + pno];
            HermiteInterpolation(pp, &v, flip ? h + 15 : h + 6);
            row = SK_SX;
        } else if (kind & 0x30) {
            v.x = s[SK_AX * c + pno]; v.y = s[SK_AY * c + pno]; v.z = s[SK_AZ * c + pno];
            HermiteInterpolation(pp, &v, flip ? h + 9 : h + 0);
            VecRadLimit(&v);
            if (w->Mot_attr & 0x40) { v.y = -v.y; v.z = -v.z; }
            row = SK_AX;
        } else {
            continue;
        }
        s[row * c + pno] = v.x;
        s[(row + 1) * c + pno] = v.y;
        s[(row + 2) * c + pno] = v.z;
        skel_cnt.samples++;
    } while (++i < n);
}

inline int near_zero(f32 d, f32 eps) { return __builtin_fabsf(d) < eps ? 1 : 0; }

// motion.cpp MotionHokan on the table
void hokan(SkelTable* t, MotionWork* w)
{
    static const int g_scale_cancel = 1;
    static const f32 epsilon = 0.00002f;
    static const f32 EPS = 0.1f;
    cModel* m = t->model;
    const u32 c = t->cap;
    f32* s = t->soa;
    Vec pos, c0, c1, c2;
    Quaternion q0, q1, q2;
    Mtx m0, m1;
    f32 tt, u, s0, s1, s2, n0, n1, n2, sx, sz, sy;

    w->Hokan_cnt--;
    tt = (f32) (w->Hokan_frame - w->Hokan_cnt);
    tt /= (f32) w->Hokan_frame;
    u = 1.0f - tt;
    for (u32 b = 0; b < t->n; b++) {
        u32& fl = t->world[b].flags;
        if (!(MOTION(m)->Mot_attr & 0x2000)) {
            if (!(fl & 0x10000000)) continue;
            fl &= ~0x10000000;
        } else {
            if ((s32) fl >= 0) continue;
        }
        f32 (*P)[4] = t->prev[b].m;
        f32 (*L)[4] = t->lmat[b].m;
        pos.x = P[0][3] * u + L[0][3] * tt;
        pos.y = P[1][3] * u + L[1][3] * tt;
        pos.z = P[2][3] * u + L[2][3] * tt;
        c0.x = P[0][0]; c0.y = P[1][0]; c0.z = P[2][0];
        c1.x = P[0][1]; c1.y = P[1][1]; c1.z = P[2][1];
        c2.x = P[0][2]; c2.y = P[1][2]; c2.z = P[2][2];
        s0 = PSVECMag(&c0); s1 = PSVECMag(&c1); s2 = PSVECMag(&c2);
        if (s0 != 0.0f) PSVECScale(&c0, &c0, 1.0f / s0);
        if (s1 != 0.0f) PSVECScale(&c1, &c1, 1.0f / s1);
        if (s2 != 0.0f) PSVECScale(&c2, &c2, 1.0f / s2);
        m0[0][0] = c0.x; m0[1][0] = c0.y; m0[2][0] = c0.z;
        m0[0][1] = c1.x; m0[1][1] = c1.y; m0[2][1] = c1.z;
        m0[0][2] = c2.x; m0[1][2] = c2.y; m0[2][2] = c2.z;
        c0.x = L[0][0]; c0.y = L[1][0]; c0.z = L[2][0];
        c1.x = L[0][1]; c1.y = L[1][1]; c1.z = L[2][1];
        c2.x = L[0][2]; c2.y = L[1][2]; c2.z = L[2][2];
        n0 = PSVECMag(&c0); n1 = PSVECMag(&c1); n2 = PSVECMag(&c2);
        if (n0 != 0.0f) PSVECScale(&c0, &c0, 1.0f / n0);
        if (n1 != 0.0f) PSVECScale(&c1, &c1, 1.0f / n1);
        if (n2 != 0.0f) PSVECScale(&c2, &c2, 1.0f / n2);
        m1[0][0] = c0.x; m1[1][0] = c0.y; m1[2][0] = c0.z;
        m1[0][1] = c1.x; m1[1][1] = c1.y; m1[2][1] = c1.z;
        m1[0][2] = c2.x; m1[1][2] = c2.y; m1[2][2] = c2.z;
        C_QUATMtx(&q0, m0);
        C_QUATMtx(&q1, m1);
        C_QUATSlerp(&q0, &q1, &q2, tt);
        PSMTXQuat(L, &q2);
        ParentRef pr = parent_of(t, b);
        const f32 bsx = s[SK_SX * c + b], bsy = s[SK_SY * c + b], bsz = s[SK_SZ * c + b];
        if (g_scale_cancel) {
            f32 one = 1.0f;
            if (!(near_zero(one - bsx, epsilon) && near_zero(one - bsy, epsilon) && near_zero(one - bsz, epsilon))) {
                if (near_zero(1.0f - pr.rs[0] * bsx, EPS) && near_zero(1.0f - pr.rs[1] * bsy, EPS) &&
                    near_zero(1.0f - pr.rs[2] * bsz, EPS)) {
                    fl |= 0x20000;
                }
            }
        } else {
            fl &= ~0x20000;
        }
        if (fl & 0x20000) {
            // the parent's own scale (cCoord::scale): a bone parent's is its pose scale, the model's its scale
            const f32* ps;
            Vec mscale;
            if (pr.bone >= 0) {
                mscale.x = s[SK_SX * c + pr.bone]; mscale.y = s[SK_SY * c + pr.bone]; mscale.z = s[SK_SZ * c + pr.bone];
                ps = &mscale.x;
            } else if (t->parent[b] == SKEL_PARENT_MODEL) {
                ps = &m->scale.x;
            } else {
                ps = &t->extParent->scale.x;
            }
            sx = 1.0f / ps[0];
            sy = 1.0f / ps[1];
            sz = 1.0f / ps[2];
        } else {
            sx = s0 * u + n0 * tt;
            sy = s1 * u + n1 * tt;
            sz = s2 * u + n2 * tt;
        }
        fl &= ~0x20000;
        L[0][0] *= sx; L[1][0] *= sx; L[2][0] *= sx;
        L[0][1] *= sy; L[1][1] *= sy; L[2][1] *= sy;
        L[0][2] *= sz; L[1][2] *= sz; L[2][2] *= sz;
        t->world[b].rs[0] = bsx;   // r_scale = scale (the pose scale before the hokan)
        t->world[b].rs[1] = bsy;
        t->world[b].rs[2] = bsz;
        s[SK_SX * c + b] = sx;
        s[SK_SY * c + b] = sy;
        s[SK_SZ * c + b] = sz;
        L[0][3] = pos.x;
        L[1][3] = pos.y;
        L[2][3] = pos.z;
        memcpy(P, L, 48);
        skel_cnt.hokan_bones++;
    }
}

// model.cpp cModel::matBlend on the table
void mat_blend(SkelTable* t, f32 rate)
{
    const u32 c = t->cap;
    f32* s = t->soa;
    Mtx m;
    Quaternion q0, q1, q2;
    Vec pos, len, vx, vy, vz, trans;
    for (u32 b = 0; b < t->n; b++) {
        f32 (*wm)[4] = t->lmat[b].m;
        vx.x = wm[0][0]; vx.y = wm[1][0]; vx.z = wm[2][0];
        len.x = PSVECMag(&vx);
        vy.x = wm[0][1]; vy.y = wm[1][1]; vy.z = wm[2][1];
        len.y = PSVECMag(&vy);
        vz.x = wm[0][2]; vz.y = wm[1][2]; vz.z = wm[2][2];
        len.z = PSVECMag(&vz);
        trans.x = wm[0][3]; trans.y = wm[1][3]; trans.z = wm[2][3];
        if (len.x != 0.0f && len.y != 0.0f && len.z != 0.0f) {
            if (len.x != 1.0f) PSVECScale(&vx, &vx, 1.0f / len.x);
            if (len.y != 1.0f) PSVECScale(&vy, &vy, 1.0f / len.y);
            if (len.z != 1.0f) PSVECScale(&vz, &vz, 1.0f / len.z);
            wm[0][0] = vx.x; wm[1][0] = vx.y; wm[2][0] = vx.z;
            wm[0][1] = vy.x; wm[1][1] = vy.y; wm[2][1] = vy.z;
            wm[0][2] = vz.x; wm[1][2] = vz.y; wm[2][2] = vz.z;
            wm[0][3] = trans.x; wm[1][3] = trans.y; wm[2][3] = trans.z;
        }
        f32 inv = 1.0f - rate;
        Vec sc;
        sc.x = s[SK_SX * c + b]; sc.y = s[SK_SY * c + b]; sc.z = s[SK_SZ * c + b];
        PSVECScale(&len, &len, inv);
        PSVECScale(&sc, &sc, rate);
        PSVECAdd(&sc, &len, &sc);
        s[SK_SX * c + b] = sc.x; s[SK_SY * c + b] = sc.y; s[SK_SZ * c + b] = sc.z;
        pos.x = s[SK_PX * c + b] * rate + wm[0][3] * inv;
        pos.y = s[SK_PY * c + b] * rate + wm[1][3] * inv;
        pos.z = s[SK_PZ * c + b] * rate + wm[2][3] * inv;
        s[SK_PX * c + b] = pos.x; s[SK_PY * c + b] = pos.y; s[SK_PZ * c + b] = pos.z;
        PSMTXIdentity(m);
        rot_matrix(m, s[SK_AX * c + b], s[SK_AY * c + b], s[SK_AZ * c + b]);
        C_QUATMtx(&q0, m);
        C_QUATMtx(&q1, wm);
        C_QUATSlerp(&q0, &q1, &q2, inv);
        PSMTXQuat(wm, &q2);
        wm[0][3] = pos.x; wm[1][3] = pos.y; wm[2][3] = pos.z;
        wm[0][0] *= sc.x; wm[0][1] *= sc.y; wm[0][2] *= sc.z;
        wm[1][0] *= sc.x; wm[1][1] *= sc.y; wm[1][2] *= sc.z;
        wm[2][0] *= sc.x; wm[2][1] *= sc.y; wm[2][2] *= sc.z;
        skel_cnt.blend_bones++;
    }
}

// ---------------------------------------------------------------------------------------------------------------
// IK (game/ik.cpp) on the table. Chain links follow the parts list (joint = the bone after the root, effector the
// one after it), as the original's pParts walk does. The IK bone length aliases addRot.x as in the record
// (IkParts::len at 0x128); the plane matrix, axis and direction live in the chain records.
SkelIk* ik_of(SkelTable* t, u32 root)
{
    for (u32 i = 0; i < t->nIk; i++)
        if (t->ik[i].root == root) return &t->ik[i];
    return 0;
}
inline f32& IKLEN(SkelTable* t, u32 b) { return t->soa[SK_RX * t->cap + b]; }
inline f32 BINDC(SkelTable* t, u32 b, int k) { return t->soa[(SK_BX + k) * t->cap + b]; }
inline f32 (*MAT(SkelTable* t, u32 b))[4] { return t->world[b].m; }
inline f32 (*LM(SkelTable* t, u32 b))[4] { return t->lmat[b].m; }
inline void get_w(SkelTable* t, u32 b, Vec* v)
{
    v->x = t->soa[SK_WX * t->cap + b]; v->y = t->soa[SK_WY * t->cap + b]; v->z = t->soa[SK_WZ * t->cap + b];
}
inline void set_w(SkelTable* t, u32 b, const Vec* v)
{
    t->soa[SK_WX * t->cap + b] = v->x; t->soa[SK_WY * t->cap + b] = v->y; t->soa[SK_WZ * t->cap + b] = v->z;
}
inline void get_p(SkelTable* t, u32 b, Vec* v)
{
    v->x = t->soa[SK_PX * t->cap + b]; v->y = t->soa[SK_PY * t->cap + b]; v->z = t->soa[SK_PZ * t->cap + b];
}
inline void set_p(SkelTable* t, u32 b, const Vec* v)
{
    t->soa[SK_PX * t->cap + b] = v->x; t->soa[SK_PY * t->cap + b] = v->y; t->soa[SK_PZ * t->cap + b] = v->z;
}
inline const f32 (*PMAT(SkelTable* t, u32 b))[4] { return parent_of(t, b).m; }

void ik_init(SkelTable* t, MotionWork* w)
{
    Vec axis;
    Mtx mtx;
    Vec v;
    for (u32 b = 0; b < t->n; b++) t->world[b].flags &= ~(4u | 0x10u | 0x300u);
    t->nIk = 0;
    for (int i = 0; i < w->Joint_num; i++) {
        int kind = w->pJoint_kind[i] & 0xFF;
        if (!(kind & 0x30)) continue;
        u32 root = w->pJoint_no[i];
        if (root >= t->n) { pLog->err(2, 0, "IKInit(): missing Root."); return; }
        u32 joint = root + 1;
        if (joint >= t->n) { pLog->err(2, 0, "IKInit(): missing Joint."); return; }
        u32 eff = joint + 1;
        if (eff >= t->n) { pLog->err(2, 0, "IKInit(): missing Effector."); return; }
        u32& fr = t->world[root].flags;
        fr |= 4;
        switch ((w->pJoint_kind[i] >> 8) & 0xF) {
        case 4: axis.x = 0.0f; axis.y = 0.0f; axis.z = 1.0f; break;
        case 5: axis.x = 0.0f; axis.y = 0.0f; axis.z = -1.0f; break;
        case 0: axis.x = 0.0f; axis.y = 1.0f; axis.z = 0.0f; break;
        case 1: axis.x = 0.0f; axis.y = -1.0f; axis.z = 0.0f; break;
        case 2: axis.x = 1.0f; axis.y = 0.0f; axis.z = 0.0f; break;
        case 3: axis.x = -1.0f; axis.y = 0.0f; axis.z = 0.0f; break;
        }
        if (kind & 0x20) {
            fr |= 0x100;
            if (root + 3 < t->n) t->ikAng[root + 3] = 0.0f;
        }
        if (kind & 0x80) {
            u32 f = fr | 0x210;
            fr = f;
            if (f & 0x100) {
                eff = joint + 2;
                if (eff >= t->n) { pLog->err(2, 0, "IKInit(): missing joint."); return; }
            }
        }
        SkelIk* ik = ik_of(t, root);
        if (!ik) {
            if (t->nIk >= SKEL_MAX_IK) { pLog->err(2, 0, "skel: too many IK chains"); return; }
            ik = &t->ik[t->nIk++];
            ik->root = (u8) root;
        }
        v.x = BINDC(t, joint, 0) - BINDC(t, root, 0);
        v.y = BINDC(t, joint, 1) - BINDC(t, root, 1);
        v.z = BINDC(t, joint, 2) - BINDC(t, root, 2);
        IKLEN(t, root) = PSVECMag(&v);
        if (v.y == 0.0f && v.z == 0.0f) fr |= 0x2000;
        else if (v.x == 0.0f && v.z == 0.0f) fr |= 0x4000;
        else if (v.x == 0.0f && v.y == 0.0f) fr |= 0x8000;
        else fr &= ~0xE000;
        v.x = BINDC(t, eff, 0) - BINDC(t, joint, 0);
        v.y = BINDC(t, eff, 1) - BINDC(t, joint, 1);
        v.z = BINDC(t, eff, 2) - BINDC(t, joint, 2);
        IKLEN(t, joint) = PSVECMag(&v);
        ik->dir.x = BINDC(t, root, 0) - BINDC(t, eff, 0);
        ik->dir.y = BINDC(t, root, 1) - BINDC(t, eff, 1);
        ik->dir.z = BINDC(t, root, 2) - BINDC(t, eff, 2);
        Vec* d = &ik->dir;
        int nn;
        if (d->x == 0.0f && d->y == 0.0f && d->z == 0.0f) goto plane_error;
        nn = 0;
        if (axis.x == 0.0f && d->x == 0.0f) nn++;
        if (axis.y == 0.0f && d->y == 0.0f) nn++;
        if (axis.z == 0.0f && d->z == 0.0f) nn++;
        if (nn > 1) {
        plane_error:
            fr &= ~4;
            pLog->err(2, 0, "IKInit(): IK plane error");
        } else {
            SetOrientationZY(&ik->dir, &axis, mtx);
            PSMTXTranspose(mtx, ik->mat);
            axis.x = 1.0f; axis.y = 0.0f; axis.z = 0.0f;
            PSMTXMultVec(mtx, &axis, &ik->axis);
        }
    }
}

void ik_calc(SkelTable* t, u32 root, u32 joint, u32 eff)
{
    SkelIk* ik = ik_of(t, root);
    Vec dir, axis, rw, ew, jp, jw;
    Mtx m, r1, r2;
    f32 ang2 = 0.0f;
    f32 ang1 = ang2;
    f32 d, la, lb, c1, c2;
    get_w(t, root, &rw);
    get_w(t, eff, &ew);
    d = GetDistance3(&rw, &ew);
    la = IKLEN(t, root);
    lb = IKLEN(t, joint);
    if (d < la + lb) {
        c1 = (la * la + d * d - lb * lb) / ((la + la) * d);
        c2 = (d * d + lb * lb - la * la) / ((d + d) * lb);
        if (c1 < -1.0f) c1 = -1.0f;
        if (c1 > 1.0f) c1 = 1.0f;
        if (c2 < -1.0f) c2 = -1.0f;
        if (c2 > 1.0f) c2 = 1.0f;
        ang1 = acosf(c1);
        ang2 = acosf(c2);
    }
    PSMTXMultVecSR(MAT(t, root), &ik->axis, &axis);
    PSVECSubtract(&ew, &rw, &dir);
    SetOrientationZX(&dir, &axis, m);
    PSMTXConcat(m, ik->mat, m);
    PSMTXRotAxisRad(r1, &ik->axis, -ang1);
    PSMTXConcat(m, r1, MAT(t, root));
    TransMatrix(MAT(t, root), &rw);
    PSMTXRotAxisRad(r2, &ik->axis, ang2);
    PSMTXConcat(m, r2, MAT(t, joint));
    get_p(t, joint, &jp);
    PSMTXMultVec(MAT(t, root), &jp, &jw);
    set_w(t, joint, &jw);
    TransMatrix(MAT(t, joint), &jw);
}

void heel_to_toe(SkelTable* t, f32 (*m)[4], u32 p, Vec* pos)
{
    Mtx inv;
    u32 toe = p + 1;
    if (toe >= t->n) { pLog->err(2, 0, "heel2toe(): missing joint."); return; }
    Vec tp, pw;
    PSMTXConcat(m, LM(t, p), MAT(t, p));
    get_p(t, toe, &tp);
    PSMTXMultVecSR(MAT(t, p), &tp, &pw);
    PSVECSubtract(pos, &pw, &pw);
    set_w(t, p, &pw);
    TransMatrix(MAT(t, p), &pw);
    PSMTXInverse(PMAT(t, p), inv);
    PSMTXConcat(inv, MAT(t, p), LM(t, p));
    t->world[p].flags |= 0x10000000;
    TransMatrix(LM(t, toe), &tp);
    PSMTXConcat(PMAT(t, toe), LM(t, toe), MAT(t, toe));
    Vec tw;
    tw.x = MAT(t, toe)[0][3]; tw.y = MAT(t, toe)[1][3]; tw.z = MAT(t, toe)[2][3];
    set_w(t, toe, &tw);
    t->world[toe].flags |= 0x10000000;
}

void ik_flag_only(SkelTable* t, u32 q, MotionWork* blend)
{
    u32 f = t->world[q].flags;
    t->world[q].flags = f | 0x10000000;
    if (blend != 0 && (s32) blend->Mot_flag < 0) t->world[q].flags = f | 0x90000000;
}
void ik_local(SkelTable* t, u32 q, MotionWork* blend)
{
    Mtx inv;
    PSMTXInverse(PMAT(t, q), inv);
    PSMTXConcat(inv, MAT(t, q), LM(t, q));
    ik_flag_only(t, q, blend);
}
void col_of(Vec* d, const f32 (*mtx)[4], int c)
{
    d->x = mtx[0][c]; d->y = mtx[1][c]; d->z = mtx[2][c];
}

// IK_TWIST_ANGLE / IK_TWIST_APPLY of ik.cpp
f32 twist_angle(SkelTable* t, const f32 (*rel)[4], u32 e)
{
    Vec a, b, c, d;
    Vec up = {0.0f, 1.0f, 0.0f};
    col_of(&a, rel, 0);
    col_of(&b, rel, 2);
    PSVECCrossProduct(&a, &up, &c);
    f32 ang = VecAngle(&c, &b);
    PSVECCrossProduct(&c, &b, &d);
    if (PSVECDotProduct(&d, &a) < 0.0f) {
        ang = -ang;
        if (t->ikAng[e] > 1.5707964f) ang += 6.2831855f;
        else t->ikAng[e] = ang;
    } else {
        if (t->ikAng[e] < -1.5707964f) ang -= 6.2831855f;
        else t->ikAng[e] = ang;
    }
    return ang;
}
void twist_apply(SkelTable* t, u32 q, int col, f32 ang, f32 rate)
{
    Vec ax, tt;
    Mtx rm;
    col_of(&ax, MAT(t, q), col);
    col_of(&tt, MAT(t, q), 3);
    PSMTXRotAxisRad(rm, &ax, ang * rate);
    PSMTXConcat(rm, MAT(t, q), MAT(t, q));
    TransMatrix(MAT(t, q), &tt);
}

void inverse_kinematics(SkelTable* t)
{
    cModel* m = t->model;
    cEm* em = (cEm*) m;
    MotionWork* blend = MOTION(m)->blend;
    Mtx inv;
    Vec target, a;
    f32 floorY;
    for (u32 p = 0; p < t->n; p++) {
        u32 fp = t->world[p].flags;
        if (!(fp & 4)) continue;
        if (fp & 0x80) continue;
        if (p + 2 >= t->n) continue;
        skel_cnt.ik_chains++;
        u32 joint = p + 1;
        u32 eff = joint + 1;
        Vec ep;
        get_p(t, eff, &ep);
        PSMTXMultVec(m->mat, &ep, &target);
        if (!em->checkStatus(EM_STATUS_IK_OFF) && !(t->world[p].flags & 0x200)) {
            if (!(em->atari.m_flag & 0x100)) {
                floorY = target.y - ep.y;
            } else if (t->world[p].flags & 0x800) {
                target.y += 1000.0f;
                floorY = SatMgr.getFloor(&target, 500.0f, 100000.0f, 0, 0);
            } else if (t->world[p].flags & 0x40) {
                floorY = SatMgr.getFloor(&target, 6000.0f, 100000.0f, 0, 0);
            } else {
                floorY = SatMgr.getFloor(&target, 500.0f, 100000.0f, 0, 0);
            }
            if (floorY != -100000.0f) {
                f32 dist, reach;
                Vec pw;
                a.x = target.x;
                a.y = floorY + ep.y;
                a.z = target.z;
                get_w(t, p, &pw);
                dist = GetDistance3(&pw, &a);
                reach = IKLEN(t, p) + IKLEN(t, p + 1);
                const u32 f = t->world[p].flags;
                if (target.y < floorY + ep.y || ((f & 0x400) && dist < reach) || (f & 0x800)) {
                    if ((f & 0x800) && floorY < target.y) a.y = target.y;
                    else target.y = floorY + ep.y;
                }
            }
        }
        if (!(t->world[p].flags & 0x10)) {
            if (t->world[p].flags & 0x100) {
                heel_to_toe(t, m->mat, eff, &target);
            } else {
                PSMTXConcat(m->mat, LM(t, eff), MAT(t, eff));
                TransMatrix(MAT(t, eff), &target);
                Vec ew;
                col_of(&ew, MAT(t, eff), 3);
                set_w(t, eff, &ew);
                ik_local(t, eff, blend);
            }
        } else {
            eff = p + 3;
            if (eff >= t->n) continue;
            PSMTXConcat(m->mat, LM(t, eff), MAT(t, eff));
            Vec ew;
            col_of(&ew, MAT(t, eff), 3);
            set_w(t, eff, &ew);
            ik_local(t, eff, blend);
        }
        if (!(t->world[p].flags & 0x10)) {
            ik_calc(t, p, joint, eff);
            ik_local(t, p, blend);
            ik_local(t, joint, blend);
            if (t->world[p].flags & 0x100) {
                a.x = BINDC(t, joint, 0) - BINDC(t, eff, 0);
                a.y = BINDC(t, joint, 1) - BINDC(t, eff, 1);
                a.z = BINDC(t, joint, 2) - BINDC(t, eff, 2);
                PSMTXMultVec(PMAT(t, eff), &a, &a);
                TransMatrix(MAT(t, eff), &a);
                Vec ew;
                col_of(&ew, MAT(t, eff), 3);
                set_w(t, eff, &ew);
                ik_local(t, eff, blend);
                Vec lp;
                col_of(&lp, LM(t, eff), 3);
                set_p(t, eff, &lp);
            } else {
                PSMTXInverse(PMAT(t, eff), inv);
                PSMTXConcat(inv, MAT(t, eff), LM(t, eff));
            }
            if (t->world[p].flags & 0x100) {
                u32 toe = eff + 1;
                if (toe < t->n) {
                    Vec tp;
                    get_p(t, toe, &tp);
                    rot_matrix(LM(t, toe), t->soa[SK_AX * t->cap + toe], t->soa[SK_AY * t->cap + toe],
                               t->soa[SK_AZ * t->cap + toe]);
                    TransMatrix(LM(t, toe), &tp);
                    PSMTXConcat(PMAT(t, toe), LM(t, toe), MAT(t, toe));
                    Vec tw;
                    col_of(&tw, MAT(t, toe), 3);
                    set_w(t, toe, &tw);
                    ik_flag_only(t, toe, blend);
                }
            }
            if (t->world[p].flags & 0x1000) {
                const u32 f = t->world[p].flags;
                int sel;
                if (f & 0x2000) sel = 0;
                else if (f & 0x4000) sel = 1;
                else if (f & 0x8000) sel = 2;
                else sel = 1;
                u32 j = p + 1, e = j + 1;
                Mtx rel, jinv;
                switch (sel) {
                case 0: {
                    PSMTXInverse(MAT(t, j), jinv);
                    PSMTXConcat(jinv, MAT(t, e), rel);
                    f32 ang = twist_angle(t, rel, e);
                    twist_apply(t, j, 0, ang, 0.5f);
                    twist_apply(t, p, 0, ang, 0.25f);
                    break;
                }
                case 1: {
                    Mtx rr;
                    PSMTXInverse(MAT(t, j), jinv);
                    PSMTXConcat(jinv, MAT(t, e), rel);
                    Vec rot = {-1.5707964f, 1.5707964f, 0.0f};
                    RotMatrix(rr, &rot);
                    PSMTXConcat(rr, rel, rel);
                    f32 ang = twist_angle(t, rel, e);
                    twist_apply(t, j, 1, ang, 0.5f);
                    twist_apply(t, p, 1, ang, 0.25f);
                    break;
                }
                }
                u32 q = p;
                for (int k = 0; k <= 2 && q < t->n; k++, q++) {
                    PSMTXInverse(PMAT(t, q), inv);
                    PSMTXConcat(inv, MAT(t, q), LM(t, q));
                    if (k == 2) {
                        Vec lp;
                        col_of(&lp, LM(t, q), 3);
                        set_p(t, q, &lp);
                    }
                    ik_flag_only(t, q, blend);
                }
            }
        } else if (t->world[p].flags & 0x100) {
            u32 j = p + 1, e = j + 1, toe = e + 1;
            if (toe >= t->n) continue;
            ik_calc(t, p, j, toe);
            PSMTXConcat(MAT(t, j), LM(t, e), MAT(t, e));
            Mtx rel, jinv;
            PSMTXInverse(MAT(t, e), jinv);
            PSMTXConcat(jinv, MAT(t, toe), rel);
            f32 ang = twist_angle(t, rel, toe);
            twist_apply(t, e, 0, ang, 0.5f);
            twist_apply(t, j, 0, ang, 0.25f);
            twist_apply(t, p, 0, ang, 0.125f);
            u32 q = p;
            for (int k = 0; k <= 3 && q < t->n; k++, q++) {
                PSMTXInverse(PMAT(t, q), inv);
                PSMTXConcat(inv, MAT(t, q), LM(t, q));
                if (k == 3) {
                    Vec lp;
                    col_of(&lp, LM(t, q), 3);
                    set_p(t, q, &lp);
                }
                ik_flag_only(t, q, blend);
            }
        }
    }
}

// ---------------------------------------------------------------------------------------------------------------
// table life
SkelTable* table_create(cModel* m)
{
    u32 n = 0;
    for (cParts* p = m->pList; PTR_OK(p) && n < 255; p = p->pList) n++;
    if (!n) return 0;
    const u32 cap = (n + 7u) & ~7u;
    u32 off = align32(sizeof(SkelTable));
    const u32 oRec = off; off = align32(off + 4 * n);
    const u32 oWorld = off; off = align32(off + sizeof(SkelBone) * n);
    const u32 oLmat = off; off = align32(off + sizeof(SkelMat) * n);
    const u32 oPal = off; off = align32(off + sizeof(SkelPal) * n);
    const u32 oPrev = off; off = align32(off + sizeof(SkelMat) * n);
    const u32 oSoa = off; off = align32(off + 4 * SK_ROWS * cap);
    const u32 oIkAng = off; off = align32(off + 4 * cap);
    const u32 oHist = off; off = align32(off + 36 * n);
    const u32 oParent = off; off = align32(off + cap);
    const u32 oMbox = off; off = align32(off + cap);
    const u32 oMlist = off; off = align32(off + cap);
    const u32 oShadow = off; off = align32(off + (skel_poison ? 4 * 21 * n : 0));
    const u32 oIk = off; off = align32(off + sizeof(SkelIk) * SKEL_MAX_IK);
    u8* blk = (u8*) pool_alloc(off);
    if (!blk) return 0;
    SkelTable* t = (SkelTable*) blk;
    t->n = (u16) n;
    t->cap = (u16) cap;
    t->bytes = off;
    t->model = m;
    t->serial = ++g_serial;
    t->rec = (cParts**) (blk + oRec);
    t->world = (SkelBone*) (blk + oWorld);
    t->lmat = (SkelMat*) (blk + oLmat);
    t->pal = (SkelPal*) (blk + oPal);
    t->prev = (SkelMat*) (blk + oPrev);
    t->soa = (f32*) (blk + oSoa);
    t->ikAng = (f32*) (blk + oIkAng);
    t->hist = (u16*) (blk + oHist);
    t->parent = blk + oParent;
    t->mbox = blk + oMbox;
    t->mlist = blk + oMlist;
    t->shadow = skel_poison ? (f32*) (blk + oShadow) : 0;
    t->ik = (SkelIk*) (blk + oIk);
    for (u32 i = 0; i < SKEL_MAX_IK; i++) t->ikOf[i] = 0xFF;
    u32 b = 0;
    for (cParts* p = m->pList; b < n; p = p->pList) t->rec[b++] = p;
    // the record's own state at creation (cParts::cParts: identity matrices, unit scale) is the table's
    for (b = 0; b < n; b++) {
        cParts* r = t->rec[b];
        memcpy(t->world[b].m, r->mat, 48);
        memcpy(t->lmat[b].m, r->l_mat, 48);
        memcpy(t->prev[b].m, r->prevMat, 48);
        t->world[b].rs[0] = r->r_scale.x; t->world[b].rs[1] = r->r_scale.y; t->world[b].rs[2] = r->r_scale.z;
        t->world[b].flags = r->motParts.flags;
        f32* s = t->soa;
        s[SK_PX * cap + b] = r->pos.x; s[SK_PY * cap + b] = r->pos.y; s[SK_PZ * cap + b] = r->pos.z;
        s[SK_AX * cap + b] = r->ang.x; s[SK_AY * cap + b] = r->ang.y; s[SK_AZ * cap + b] = r->ang.z;
        s[SK_SX * cap + b] = r->scale.x; s[SK_SY * cap + b] = r->scale.y; s[SK_SZ * cap + b] = r->scale.z;
        s[SK_WX * cap + b] = r->world.x; s[SK_WY * cap + b] = r->world.y; s[SK_WZ * cap + b] = r->world.z;
        s[SK_OX * cap + b] = r->world_old.x; s[SK_OY * cap + b] = r->world_old.y; s[SK_OZ * cap + b] = r->world_old.z;
        s[SK_O2X * cap + b] = r->world_old2.x; s[SK_O2Y * cap + b] = r->world_old2.y; s[SK_O2Z * cap + b] = r->world_old2.z;
        s[SK_RX * cap + b] = r->addRot.x; s[SK_RY * cap + b] = r->addRot.y; s[SK_RZ * cap + b] = r->addRot.z;
        s[SK_MPX * cap + b] = r->motParts.pos.x; s[SK_MPY * cap + b] = r->motParts.pos.y; s[SK_MPZ * cap + b] = r->motParts.pos.z;
        s[SK_MRX * cap + b] = r->motParts.rot.x; s[SK_MRY * cap + b] = r->motParts.rot.y; s[SK_MRZ * cap + b] = r->motParts.rot.z;
        s[SK_MSX * cap + b] = r->motParts.scale.x; s[SK_MSY * cap + b] = r->motParts.scale.y; s[SK_MSZ * cap + b] = r->motParts.scale.z;
        t->ikAng[b] = r->motParts.ikAng;
        memcpy(t->hist + b * 18, r->motParts.hist, 36);
        t->parent[b] = SKEL_PARENT_MODEL;
        if (r->pParent != (cCoord*) m) {
            u32 k;
            for (k = 0; k < n && (cCoord*) t->rec[k] != r->pParent; k++) {
            }
            if (k < n) {
                t->parent[b] = (u8) k;
            } else {
                t->parent[b] = SKEL_PARENT_EXT;
                t->extParent = r->pParent;
            }
        }
    }
    if (g_ntab >= kMaxTables) {
        pLog->err(0, 0, "skel: too many tables");
        pool_free(blk);
        return 0;
    }
    g_tab[g_ntab] = t;
    map_slots(g_ntab, t, true);
    g_ntab++;
    if (skel_poison)
        for (b = 0; b < n; b++) poison_record(t->rec[b]);
    return t;
}

void table_release(SkelTable* t)
{
    for (u32 i = 0; i < g_ntab; i++) {
        if (g_tab[i] != t) continue;
        map_slots(i, t, false);
        g_tab[i] = g_tab[--g_ntab];
        if (i < g_ntab) map_slots(i, g_tab[i], true);
        pool_free(t);
        return;
    }
}

// the table of model m, created on first use once m has parts; refreshed when the chain changed (new parts)
SkelTable* table_for(cModel* m)
{
    SkelTable* t = find_table(m);
    if (t && (!PTR_OK(m->pList) || t->rec[0] != m->pList)) {
        table_release(t);
        t = 0;
    }
    if (!t && PTR_OK(m->pList)) t = table_create(m);
    return t;
}

}   // namespace

// =================================================================================================================
// engine API
extern "C" SkelTable* skel_table_of(const cModel* m) { return find_table(m); }
extern "C" u32 skel_table_count(void) { return g_ntab; }
extern "C" SkelTable* skel_table_at(u32 i) { return i < g_ntab ? g_tab[i] : 0; }

// palette = world x bind (bind: identity with the rest translation negated, cParts::lt_inv_mat): XMTRX holds the
// bone's world, the bind translation goes through it as a point. Once a tick, after the behaviour.
extern "C" void skel_publish(SkelTable* t)
{
    if (skel_poison) {
        for (u32 b = 0; b < t->n; b++) {
            const u8 p = t->parent[b];
            const cCoord* want = p == SKEL_PARENT_MODEL ? (cCoord*) t->model : p == SKEL_PARENT_EXT ? t->extParent : (cCoord*) t->rec[p];
            if (t->rec[b]->pParent != want) skel_cnt.parent_mismatch++;
        }
    }
    const u32 c = t->cap;
    const f32* s = t->soa;
    for (u32 b = 0; b < t->n; b++) {
        const SkelBone& w = t->world[b];
        SkelPal& p = t->pal[b];
        skel_xm_load_3x4(&w.m[0][0]);
        const f32 bt[3] = {s[SK_BX * c + b], s[SK_BY * c + b], s[SK_BZ * c + b]};
        f32 tr3[3];
        skel_xm_point3(bt, tr3);
        const Vec tr = {tr3[0], tr3[1], tr3[2]};
        for (int i = 0; i < 3; i++) {
            p.m[i][0] = w.m[i][0];
            p.m[i][1] = w.m[i][1];
            p.m[i][2] = w.m[i][2];
        }
        p.m[0][3] = tr.x;
        p.m[1][3] = tr.y;
        p.m[2][3] = tr.z;
    }
    skel_cnt.palette += t->n;
}
extern "C" void skel_publish_all(void)
{
    for (u32 i = 0; i < g_ntab; i++) skel_publish(g_tab[i]);
}

// =================================================================================================================
// the original entry points, engine bodies

// model.cpp: parts `no` (-1 the model); the record becomes its bone's mailbox
cModel* cModel::getPartsPtr(int no)
{
    cModel* p = pParts;
    int cnt;
    if (no < 0) return this;
    cnt = no;
    if (!PTR_OK(p)) return 0;
    if (be_flag & 0x2000) {
        p = (cModel*) ((cParts*) p + no);
    } else if (no--) {
        do {
            cModel* next = p->pParts;
            if (!PTR_OK(next)) {
                pLog->err(0, 0, "cModel::getPartsPtr() cParts NO ERROR %d", cnt);
                return 0;
            }
            p = next;
        } while (no--);
    }
    int b;
    SkelTable* t = table_of_record(p, &b);
    if (t) mailbox_add(t, (u32) b);
    return p;
}

extern "C" cModel* GetPartsAddr(cModel* parts, int no)
{
    int cnt = no;
    if (!PTR_OK(parts)) {
        pLog->err(0, 0, "GetPartsAddr() PTR ERROR %08X", parts);
        return 0;
    }
    if (no--) {
        do {
            cModel* next = parts->pParts;
            if (!PTR_OK(next)) {
                pLog->err(0, 0, "GetPartsAddr() cParts NO ERROR %d", cnt);
                break;
            }
            parts = next;
        } while (no--);
    }
    int b;
    SkelTable* t = table_of_record(parts, &b);
    if (t) mailbox_add(t, (u32) b);
    return parts;
}

void cModel::partsMatCalc()
{
    SkelTable* t = table_for(this);
    if (!t) return;
    Scope sc(t);
    mat_calc(t);
}

void cModel::partsWorldCalc()
{
    r_scale = scale;
    if (!PTR_OK(pList)) {
        pLog->err(2, 0, "partsWorldCalc() MODEL HAS NO PARTS");
        return;
    }
    if (!PTR_OK(pList->pParent)) {
        pLog->err(2, 0, "partsWorldCalc() PARENT ADDR ERR %08x", pList->pParent);
        return;
    }
    SkelTable* t = table_for(this);
    if (!t) return;
    Scope sc(t);
    world_calc(t);
}

void cModel::matBlend(f32 rate)
{
    SkelTable* t = table_for(this);
    if (!t) return;
    Scope sc(t);
    mat_blend(t, rate);
}

void cModel::matUpdate()
{
    cCoord::matUpdate();
    if (pParts != NULL) {
        SkelTable* t = table_for(this);
        if (t) {
            Scope sc(t);
            mat_calc(t);
            world_calc(t);
        }
    }
    LightInfo.updateMatrix(this);
}

void cModel::updateOldPos()
{
    pos_old = pos;
    SkelTable* t = table_for(this);
    if (!t) return;
    Scope sc(t);
    const u32 c = t->cap;
    f32* s = t->soa;
    memcpy(s + SK_O2X * c, s + SK_OX * c, 4 * 3 * c);   // world_old2 = world_old (three rows)
    memcpy(s + SK_OX * c, s + SK_WX * c, 4 * 3 * c);    // world_old = world
}

void cModel::setPos(Vec* p)
{
    Vec d;
    PSVECSubtract(p, &this->pos, &d);
    SkelTable* t = table_for(this);
    if (PSVECMag(&d) != 0.0f) {
        PSVECAdd(&this->pos, &d, &this->pos);
        PSVECAdd(&pos_old, &d, &pos_old);
        if (t) {
            Scope sc(t);
            const u32 c = t->cap;
            f32* s = t->soa;
            for (u32 b = 0; b < t->n; b++) {
                Vec w;
                w.x = s[SK_WX * c + b]; w.y = s[SK_WY * c + b]; w.z = s[SK_WZ * c + b];
                PSVECAdd(&w, &d, &w);
                s[SK_WX * c + b] = w.x; s[SK_WY * c + b] = w.y; s[SK_WZ * c + b] = w.z;
                s[SK_OX * c + b] = w.x; s[SK_OY * c + b] = w.y; s[SK_OZ * c + b] = w.z;
                t->world[b].m[0][3] += d.x;
                t->world[b].m[1][3] += d.y;
                t->world[b].m[2][3] += d.z;
            }
        }
        mat[0][3] = this->pos.x;
        mat[1][3] = this->pos.y;
        mat[2][3] = this->pos.z;
    }
    LightInfo.updateMatrix(this);
    atari.m_stat |= 1;
}

void cModel::partsFixMemory(int no)
{
    if (pParts == NULL) {
        Fix_parts = 0;
        return;
    }
    SkelTable* t = table_for(this);
    if (!t || no < 0 || (u32) no >= t->n) return;
    Scope sc(t);
    Fix_pos.x = t->soa[SK_WX * t->cap + no];
    Fix_pos.y = t->soa[SK_WY * t->cap + no];
    Fix_pos.z = t->soa[SK_WZ * t->cap + no];
    Fix_parts = no + 1;
}

void cModel::partsFixAdjust()
{
    Vec d;
    if (Fix_parts == 0) return;
    SkelTable* t = table_for(this);
    if (!t) return;
    {
        Scope sc(t);
        const u32 b = Fix_parts - 1;
        d.x = t->soa[SK_WX * t->cap + b] - Fix_pos.x;
        d.z = t->soa[SK_WZ * t->cap + b] - Fix_pos.z;
    }
    pos.x -= d.x;
    pos.z -= d.z;
    PartsWorldPosCalc(this);
    Fix_parts = 0;
}

void cModel::setParent(cModel* parent, Vec* p, Vec* rot)
{
    cParts* r = pList;
    r->pParent = parent;
    r->pos = *p;
    r->ang = *rot;
    SkelTable* t = table_for(this);
    if (!t) return;
    Scope sc(t);
    t->parent[0] = SKEL_PARENT_EXT;
    t->extParent = parent;
    if ((cModel*) parent == this) t->parent[0] = SKEL_PARENT_MODEL;
    const u32 c = t->cap;
    t->soa[SK_PX * c] = p->x; t->soa[SK_PY * c] = p->y; t->soa[SK_PZ * c] = p->z;
    t->soa[SK_AX * c] = rot->x; t->soa[SK_AY * c] = rot->y; t->soa[SK_AZ * c] = rot->z;
}

void cModel::setParent(cModel* parent, int partsNo, Vec* p, Vec* rot)
{
    setParent(parent->getPartsPtr(partsNo), p, rot);
}

// model.cpp setPartsOffset: rest pose from the model data, bind translations, then the pose at the model's position
void cModel::setPartsOffset(void* bin)
{
    calcModelAddr((ModelData*) bin);
    SkelTable* t = table_for(this);
    if (!t) return;
    Scope sc(t);
    ModelDataHead* rec = ((ModelData*) bin)->pHead;
    const u32 c = t->cap;
    f32* s = t->soa;
    for (u32 i = 0; i < nParts && i < t->n; i++) {
        s[SK_PX * c + i] = rec->center.x;
        s[SK_PY * c + i] = rec->center.y;
        s[SK_PZ * c + i] = rec->center.z;
        rec++;
    }
    Vec p0 = this->pos;
    PSMTXIdentity(mat);
    PSMTXTrans(mat, 0.0f, 0.0f, 0.0f);
    mat_calc(t);
    world_calc(t);
    this->pos = p0;
    for (u32 b = 0; b < t->n; b++) {
        s[SK_BX * c + b] = -t->world[b].m[0][3];
        s[SK_BY * c + b] = -t->world[b].m[1][3];
        s[SK_BZ * c + b] = -t->world[b].m[2][3];
        // the record's lt_inv_mat stays what the original has there (bind matrix): code outside reads it
        cParts* r = t->rec[b];
        PSMTXIdentity(r->lt_inv_mat);
        r->lt_inv_mat[0][3] = s[SK_BX * c + b];
        r->lt_inv_mat[1][3] = s[SK_BY * c + b];
        r->lt_inv_mat[2][3] = s[SK_BZ * c + b];
    }
    PSMTXTrans(mat, this->pos.x, this->pos.y, this->pos.z);
    mat_calc(t);
    world_calc(t);
    memcpy(s + SK_OX * c, s + SK_WX * c, 4 * 3 * c);
    memcpy(s + SK_O2X * c, s + SK_WX * c, 4 * 3 * c);
}

void cModel::releasePartsList(int no)
{
    cParts* p;
    cParts* prev;
    SkelTable* t = find_table(this);
    if (t) table_release(t);
    p = (cParts*) getPartsPtr(no);
    if (!PTR_OK(p)) {
        if (no != 0) pLog->err(0, 0, "releasePartsList() idx INVALID. %d", no);
        return;
    }
    while (p) {
        cParts* dead = p;
        p = p->pList;
        pm->destroy(dead);
    }
    if (no == 0) {
        pParts = 0;
        nParts = 0;
        return;
    }
    prev = (cParts*) getPartsPtr(no - 1);
    prev->pList = 0;
}

// motion.cpp -----------------------------------------------------------------------------------------------------
extern "C" void PartsWorldPosCalc(cModel* m)
{
    Vec d;
    PSVECSubtract(&m->pos, &MOTION(m)->Pos_world, &d);
    m->mat[0][3] += d.x;
    m->mat[1][3] += d.y;
    m->mat[2][3] += d.z;
    if (PSVECMag(&d) != 0.0f) {
        SkelTable* t = table_for(m);
        if (t) {
            Scope sc(t);
            const u32 c = t->cap;
            f32* s = t->soa;
            for (u32 b = 0; b < t->n; b++) {
                Vec w;
                w.x = s[SK_WX * c + b]; w.y = s[SK_WY * c + b]; w.z = s[SK_WZ * c + b];
                PSVECAdd(&w, &d, &w);
                s[SK_WX * c + b] = w.x; s[SK_WY * c + b] = w.y; s[SK_WZ * c + b] = w.z;
                t->world[b].m[0][3] += d.x;
                t->world[b].m[1][3] += d.y;
                t->world[b].m[2][3] += d.z;
            }
        }
        MOTION(m)->Pos_world = m->pos;
    }
}

extern "C" void MotionClear(cModel* m, int flag)
{
    MotionWork* w = MOTION(m);
    SkelTable* t = table_for(m);
    if (t) {
        Scope sc(t);
        const u32 c = t->cap;
        f32* s = t->soa;
        for (u32 b = 0; b < t->n; b++) {
            Mtx tmp, inv, bind, pbind;
            PSMTXIdentity(bind);
            bind[0][3] = s[SK_BX * c + b]; bind[1][3] = s[SK_BY * c + b]; bind[2][3] = s[SK_BZ * c + b];
            if (t->parent[b] != SKEL_PARENT_MODEL) {
                // PARTS_BIND_MAT(p->pParent): a bone parent's bind, an outside parent's record
                if (t->parent[b] < t->n) {
                    PSMTXIdentity(pbind);
                    const u32 q = t->parent[b];
                    pbind[0][3] = s[SK_BX * c + q]; pbind[1][3] = s[SK_BY * c + q]; pbind[2][3] = s[SK_BZ * c + q];
                } else {
                    memcpy(pbind, PARTS_BIND_MAT(t->extParent), 48);
                }
                PSMTXInverse(bind, tmp);
                PSMTXConcat(pbind, tmp, inv);
            } else {
                PSMTXInverse(bind, inv);
            }
            s[SK_PX * c + b] = inv[0][3];
            s[SK_PY * c + b] = inv[1][3];
            s[SK_PZ * c + b] = inv[2][3];
            s[SK_AX * c + b] = 0.0f; s[SK_AY * c + b] = 0.0f; s[SK_AZ * c + b] = 0.0f;
            if (!(flag & 1)) {
                s[SK_SX * c + b] = 1.0f; s[SK_SY * c + b] = 1.0f; s[SK_SZ * c + b] = 1.0f;
            }
        }
    }
    if (w->pAttachCam != 0) {
        for (int i = 0; i < 5; i++) w->pAttachCam->parts[i] = 0xFF;
        w->pAttachCam->type = 0;
        for (int j = 0; j < 5; j++) memclr_asm(&w->pAttachCam->out[j], sizeof(Vec));
    }
    MOTION(m)->pMot = 0;
}

void MotionSetCore(cModel* m, void* w_, void* data_, int seq_, int hokan, int flags, int frame)
{
    MotionWork* w = (MotionWork*) w_;
    MotionData* data = (MotionData*) data_;
    u16* seq = (u16*) seq_;
    HermitePrm prm;
    HermitePrm* pp = &prm;
    u16 hist0[3] = {0, 0, 0};
    u16 hist1[3] = {0, 0, 0};
    Vec v0, v1, v2;
    u32* tbl;
    AttachCamera* cam;
    int f;
    int i;
    SkelTable* t = table_for(m);
    Scope sc(t);

    if (!(w->Mot_flag & 0x20000000)) MOTION(m)->blend = 0;
    w->Pos_old = vecZero;
    w->Pos = w->Pos_old;
    w->Pos_dist = vecZero;
    w->Ang_old = vecZero;
    w->Ang = w->Ang_old;
    w->Ang_dist = vecZero;
    w->pMot = data;
    w->Mot_attr = flags;
    w->Mot_state = 0;
    w->Mot_flag = (w->Mot_flag & 0x7FFFFFFF) | 0x04000000;
    if (data == 0) {
        if ((s32) pG->Debug_flg[0] >= 0) pLog->err(0, 0, "MotionSetCore():%d pMot == NULL", 273);
        return;
    }
    if (seq == 0) {
        w->pSeq_top = 0;
        w->Seq_frame_num = data->maxFrame & 0x3FFF;
        if (!(flags & 4)) w->Seq_frame_num++;
        if ((u32) frame >= w->Seq_frame_num) frame = (u16) (w->Seq_frame_num - 1);
        w->Seq.Se = 0;
        w->Seq.Free = 0;
        w->Seq_frame = (f32) (u16) frame;
        w->Seq_old.Se = 0;
        w->Seq_old.Free = 0;
        w->Seq_old2.Se = 0;
        w->Seq_old2.Free = 0;
    } else {
        w->pSeq_top = (MotionSeqKey*) (seq + 2);
        w->Seq_frame_num = seq[0];
        if ((u32) frame >= w->Seq_frame_num) frame = (u16) (w->Seq_frame_num - 1);
        w->Seq_frame = (f32) (u16) frame;
        w->Mot_attr = (((u8*) seq)[2] & 1) ? (flags | 0x1000) : (flags & 0xEFFF);
    }
    if (w->pSeq_top == 0) {
        w->Seq.frame = (u16) (w->Seq_frame * 64.0f);
        w->Seq_old.frame = (u16) (w->Seq_frame * 64.0f);
    } else {
        MotionSeqKey k = w->pSeq_top[(u16) w->Seq_frame];
        w->Seq = k;
        w->Seq_old = k;
        w->Seq_old2 = k;
        w->Seq_old2.Se = 0;
        w->Seq_old2.Free = 0;
    }
    w->Mot_frame_max = (f32) w->pMot->maxFrame;
    w->Joint_num = w->pMot->nParts;
    w->pJoint_kind = (u16_un*) ((u8*) w->pMot + 3);
    w->pJoint_no = (u8*) w->pMot + (w->Joint_num * 2 + 3);
    if (!(w->Mot_flag & 0x10000000) && t) ik_init(t, w);
    tbl = (u32*) ((u32) w->pJoint_no + w->Joint_num);
    tbl = (u32*) (((u32) tbl + 3) & ~3);
    tbl++;
    u32* keys = tbl;
    Re4dcMotionLease lease(data, &keys, tbl);
    if (!lease.external())
        if ((s32) tbl[0] >= 0) {
            for (i = 0; i < w->Joint_num; i++) tbl[i] += (u32) w->pMot;
        }
    w->pHermite_data = tbl;
    w->Null_rot = 0xFFFF;
    w->Null_pos = 0xFFFF;
    if (w->pAttachCam != 0) {
        for (i = 0; i < 5; i++) w->pAttachCam->parts[i] = 0xFF;
        w->pAttachCam->type = 0;
        for (i = 0; i < 5; i++) memclr_asm(&w->pAttachCam->out[i], sizeof(Vec));
    }
    for (i = 0; i < w->Joint_num; i++) {
        u16 info = w->pJoint_kind[i];
        int kind = info & 0xFF;
        int ch = (info >> 8) & 0xF;
        u8 pno;
        if (kind == 1) { w->Null_pos = i; continue; }
        if (kind == 0x40) { w->Null_rot = i; continue; }
        if (w->pAttachCam == 0) continue;
        if (ch != 6 && ch != 7) continue;
        if (w->Mot_attr & 0x100) continue;
        if (ch == 6) w->pAttachCam->type = 1;
        else if (ch == 7) w->pAttachCam->type = 2;
        pno = w->pJoint_no[i];
        if (kind == 4) {
            if (pno == 0) w->pAttachCam->parts[0] = i;
            else if (pno == 1) w->pAttachCam->parts[1] = i;
            else if (pno == 4) w->pAttachCam->parts[4] = i;
        } else if (kind == 2) {
            if (pno == 2) w->pAttachCam->parts[2] = i;
            else if (pno == 3) w->pAttachCam->parts[3] = i;
        }
    }
    if (t) {
        for (u32 b = 0; b < t->n; b++) {
            if (t->world[b].flags & 0x04000000) continue;
            memset(t->hist + b * 18, 0, 36);
        }
    }
    w->Key_hist[0][0][0] = w->Key_hist[0][0][1] = w->Key_hist[0][0][2] = 0;
    w->Key_hist[0][1][0] = w->Key_hist[0][1][1] = w->Key_hist[0][1][2] = 0;
    w->Key_hist[1][0][0] = w->Key_hist[1][0][1] = w->Key_hist[1][0][2] = 0;
    w->Key_hist[1][1][0] = w->Key_hist[1][1][1] = w->Key_hist[1][1][2] = 0;
    if (w->pAttachCam != 0) {
        memclr_asm(w->pAttachCam->hist[0], 6);
        memclr_asm(w->pAttachCam->hist[1], 6);
        memclr_asm(w->pAttachCam->hist[2], 6);
        memclr_asm(w->pAttachCam->hist[3], 6);
        memclr_asm(w->pAttachCam->hist[4], 6);
    }
    if (hokan != 0) {
        w->Hokan_frame = hokan;
        w->Hokan_cnt = hokan;
        if (t)
            for (u32 b = 0; b < t->n; b++) memcpy(t->prev[b].m, t->lmat[b].m, 48);
    } else {
        w->Hokan_frame = 0;
        w->Hokan_cnt = 0;
    }
    w->Mot_state = 0;
    if (w->Mot_attr & 2) {
        f = frame + 1;
        if (f >= w->Seq_frame_num) f = w->Seq_frame_num - 1;
    } else {
        f = frame - 1;
        if (f < 0) f = 0;
    }
    pp->flags = 0;
    pp->maxFrame = w->Mot_frame_max;
    if (w->Mot_attr & 2) {
        if (!(w->Mot_attr & 0x1000)) pp->flags = 2;
    } else {
        pp->flags = (w->Mot_attr & 0x1000) ? 2 : 0;
    }
    if (w->pSeq_top == 0) {
        w->Mot_frame = (f32) f;
    } else {
        u16 k = w->pSeq_top[f].frame;
        w->Mot_frame = (f32) (k >> 6) + (f32) (k & 0x3F) * 0.0015625f;
    }
    w->Mot_frame_sav = w->Mot_frame;
    w->Mot_frame_old = w->Mot_frame;
    pp->frame = w->Mot_frame;
    if (w->Null_pos != 0xFFFF) {
        pp->type = w->pJoint_kind[w->Null_pos] >> 12;
        pp->key = (u8*) keys[w->Null_pos];
        HermiteInterpolation(pp, &w->Pos, hist0);
        w->Pos_old = w->Pos;
    }
    if (w->Null_rot != 0xFFFF) {
        pp->type = w->pJoint_kind[w->Null_rot] >> 12;
        pp->key = (u8*) keys[w->Null_rot];
        HermiteInterpolation(pp, &w->Ang, hist1);
        w->Ang_old = w->Ang;
    }
    if (w->Null_pos != 0xFFFF) {
        pp->frame = 0.0f;
        pp->type = w->pJoint_kind[w->Null_pos] >> 12;
        pp->key = (u8*) keys[w->Null_pos];
        HermiteInterpolation(pp, &v0, hist0);
        pp->frame = w->Mot_frame_max;
        pp->flags |= 2;
        HermiteInterpolation(pp, &v1, hist0);
        PSVECSubtract(&v1, &v0, &w->Pos_dist);
    }
    if (w->Null_rot != 0xFFFF) {
        pp->frame = 0.0f;
        pp->type = w->pJoint_kind[w->Null_rot] >> 12;
        pp->key = (u8*) keys[w->Null_rot];
        HermiteInterpolation(pp, &v0, hist1);
        pp->frame = w->Mot_frame_max;
        pp->flags |= 2;
        HermiteInterpolation(pp, &v1, hist1);
        PSVECSubtract(&v1, &v0, &w->Ang_dist);
        VecRadLimit(&w->Ang_dist);
    }
    cam = w->pAttachCam;
    if (cam != 0) {
        if (cam->type != 0) {
            if (cam->parts[4] != 0xFF) {
                pp->frame = 0.0f;
                pp->type = w->pJoint_kind[cam->parts[4]] >> 12;
                pp->key = (u8*) keys[cam->parts[4]];
                HermiteInterpolation(pp, &v2, hist0);
            }
            cam->frame = 0;
            if (cam->type == 1) {
                cam->pMat = &m->mat;
            } else if (cam->type == 2) {
                memcpy(cam->mat, m->mat, sizeof(Mtx));
                cam->pMat = &cam->mat;
            }
        }
        if (w->pAttachCam != 0) {
            if (w->pAttachCam->type != 0) CamCtrl.registAttachCamera(w->pAttachCam, m);
            else CamCtrl.deleteAttachCamera(w->pAttachCam, m);
        }
    }
}

extern "C" void MotionMoveCore(cModel* m, MotionWork* w, int flag)
{
    (void) flag;
    SkelTable* t = table_for(m);
    if (!t) return;
    Scope sc(t);
    move_core(t, w);
}

extern "C" void MotionHokan(cModel* m, MotionWork* w)
{
    SkelTable* t = table_for(m);
    if (!t) return;
    Scope sc(t);
    hokan(t, w);
}

extern "C" u16 MotionMoveSub(cModel* m, MotionWork* w)
{
    SkelTable* t = table_for(m);
    Scope sc(t);
    if (t) move_core(t, w);
    MotionSequenceCtrl(w);
    if (w->Hokan_cnt != 0 && t) hokan(t, w);
    return w->Mot_state;
}

extern "C" u16 MotionMove(cModel* m)
{
    static int new_add = 1;
    Vec spd, rot, spd2, rot2;
    f32 rate, inv;
    SkelTable* t = table_for(m);
    Scope sc(t);
    MotionWork* W = MOTION(m);

    if (W->blend != 0) W->blend->Seq_speed = W->Seq_speed;
    if (W->Mot_attr & 1) {
        MotionGetSpeed(m, W, 0, &spd, &rot);
        if (W->blend != 0) {
            W->blend->Mot_flag |= 0x08000000;
            rate = W->blend->Brate;
            if (!(W->blend->Mot_flag & 0x80000000)) {
                if (rate != 0.0f) {
                    W->blend->Hokan_cnt = 0;
                    MotionGetSpeed(m, W->blend, 0, &spd2, &rot2);
                    inv = 1.0f - rate;
                    VecLinearCombination(&spd2, &spd, rate, inv, &spd);
                    VecLinearCombination(&rot2, &rot, rate, inv, &rot);
                }
            } else {
                if (rate != 0.0f) {
                    W->blend->Hokan_cnt = 0;
                    MotionGetSpeed(m, W->blend, 0, &spd2, &rot2);
                    VecLinearCombination(&spd2, &spd, rate, 1.0f, &spd);
                    VecLinearCombination(&rot2, &rot, rate, 1.0f, &rot);
                }
            }
        }
        MotionAddSpeed(m, W, &spd, &rot);
    }
    if (!t) {
        // a model without parts: the root and the clock only
        if (W->pMot != 0 && !(W->Mot_flag & 0x40000000)) {
            RotMatrix(m->mat, &m->ang);
            TransMatrix(m->mat, &m->pos);
            ScaleMatrix(m->mat, &m->scale);
        }
        MotionSequenceCtrl(W);
        m->ang.y = LIMIT_ANGLE(m->ang.y);
        return W->Mot_state;
    }
    move_core(t, W);
    MotionSequenceCtrl(W);
    mat_calc(t);
    W->Mot_attr &= ~0x2000;
    const u32 c = t->cap;
    f32* s = t->soa;
    if (W->blend != 0) {
        W->blend->Mot_flag |= 0x08000000;
        rate = W->blend->Brate;
        if ((s32) W->blend->Mot_flag >= 0) {
            if (rate != 0.0f) {
                move_core(t, W->blend);
                MotionSequenceCtrl(W->blend);
                mat_blend(t, W->blend->Brate);
            } else {
                MotionSequenceCtrl(W->blend);
            }
        } else {
            W->Mot_attr |= 0x2000;
            for (u32 b = 0; b < t->n; b++) {
                if (t->world[b].flags & 0x03000000) continue;
                for (int k = 0; k < 9; k++) s[(SK_MPX + k) * c + b] = s[(SK_PX + k) * c + b];
                s[SK_AX * c + b] = 0.0f; s[SK_AY * c + b] = 0.0f; s[SK_AZ * c + b] = 0.0f;
                s[SK_PX * c + b] = 0.0f; s[SK_PY * c + b] = 0.0f; s[SK_PZ * c + b] = 0.0f;
                if (new_add) { s[SK_SX * c + b] = 0.0f; s[SK_SY * c + b] = 0.0f; s[SK_SZ * c + b] = 0.0f; }
            }
            move_core(t, W->blend);
            MotionSequenceCtrl(W->blend);
            for (u32 b = 0; b < t->n; b++) {
                if (t->world[b].flags & 0x03000000) continue;
                if (new_add) {
                    for (int k = 0; k < 9; k++) s[(SK_PX + k) * c + b] = s[(SK_MPX + k) * c + b] + s[(SK_PX + k) * c + b];
                }
            }
            if (new_add) mat_blend(t, W->blend->Brate);
        }
    }
    {
        Mtx tmp, save;
        memcpy(save, m->mat, sizeof(Mtx));
        if (m->scale.x != 0.0f || m->scale.y != 0.0f || m->scale.z != 0.0f) {
            PSMTXScale(tmp, 1.0f / m->scale.x, 1.0f / m->scale.y, 1.0f / m->scale.z);
        } else {
            PSMTXIdentity(tmp);
        }
        PSMTXConcat(m->mat, tmp, tmp);
        memcpy(m->mat, tmp, sizeof(Mtx));
        m->r_scale = m->scale;
        world_calc(t);
        if (!skel_control_no_ik) inverse_kinematics(t);
        memcpy(m->mat, save, sizeof(Mtx));
        m->r_scale = m->scale;
        world_calc(t);
    }
    if (W->Hokan_cnt != 0) {
        hokan(t, W);
        m->r_scale = m->scale;
        world_calc(t);
    }
    if (W->blendTbl != 0) {
        int nb = *(s32*) W->blendTbl;
        u16* tb = W->blendTbl + 2;
        Mtx m0, m1, mq, inv2;
        Quaternion q0, q1, q2;
        for (int i = 0; i < nb; i++) {
            u32 dst = *tb++;
            u32 a = *tb++;
            u32 cc = *tb++;
            int per = *tb++;
            f32 r = (f32) per / 100.0f;
            if (dst >= t->n || a >= t->n || cc >= t->n) continue;
            u32& fd = t->world[dst].flags;
            if (fd & 0x10000) {
                fd &= ~0x10000;
                continue;
            }
            fd &= ~0x10000000;
            f32 (*A)[4] = t->world[a].m;
            f32 (*C)[4] = t->world[cc].m;
            f32 (*D)[4] = t->world[dst].m;
            PSMTXIdentity(m0);
            for (int ii = 0; ii < 3; ii++)
                for (int jj = 0; jj < 3; jj++) m0[ii][jj] = A[ii][jj];
            C_QUATMtx(&q0, m0);
            PSMTXIdentity(m1);
            for (int ii = 0; ii < 3; ii++)
                for (int jj = 0; jj < 3; jj++) m1[ii][jj] = C[ii][jj];
            C_QUATMtx(&q1, m1);
            C_QUATSlerp(&q1, &q0, &q2, r);
            PSMTXQuat(mq, &q2);
            for (int ii = 0; ii < 3; ii++)
                for (int jj = 0; jj < 3; jj++) D[ii][jj] = mq[ii][jj];
            f32* rd = t->world[dst].rs;
            const f32* ra = t->world[a].rs;
            const f32* rc = t->world[cc].rs;
            rd[0] = rc[0] * (1.0f - r) + ra[0] * r;
            rd[1] = rc[1] * (1.0f - r) + ra[1] * r;
            rd[2] = rc[2] * (1.0f - r) + ra[2] * r;
            D[0][0] *= rd[0]; D[0][1] *= rd[1]; D[0][2] *= rd[2];
            D[1][0] *= rd[0]; D[1][1] *= rd[1]; D[1][2] *= rd[2];
            D[2][0] *= rd[0]; D[2][1] *= rd[1]; D[2][2] *= rd[2];
            PSMTXInverse(parent_of(t, dst).m, inv2);
            PSMTXConcat(inv2, D, t->lmat[dst].m);
        }
    }
    m->ang.y = LIMIT_ANGLE(m->ang.y);
    return W->Mot_state;
}

extern "C" void IKInit(cModel* m, MotionWork* w)
{
    SkelTable* t = table_for(m);
    if (!t) return;
    Scope sc(t);
    ik_init(t, w);
}

extern "C" void InverseKinematics(cModel* m, int flag)
{
    (void) flag;
    SkelTable* t = table_for(m);
    if (!t) return;
    Scope sc(t);
    if (!skel_control_no_ik) inverse_kinematics(t);
}

// atari.cpp at_pos_calc: a collision push moves the model and every bone's world position and matrix translation
// (the collision unit's only write to the bones; it walked the parts records)
void at_pos_calc(cModel* m, Vec* vec)
{
    if (PSVECMag(vec) != 0.0f) {
        PSVECAdd(&m->pos, vec, &m->pos);
        SkelTable* t = table_for(m);
        if (t) {
            Scope sc(t);
            const u32 c = t->cap;
            f32* s = t->soa;
            for (u32 b = 0; b < t->n; b++) {
                Vec w;
                w.x = s[SK_WX * c + b]; w.y = s[SK_WY * c + b]; w.z = s[SK_WZ * c + b];
                PSVECAdd(&w, vec, &w);
                s[SK_WX * c + b] = w.x; s[SK_WY * c + b] = w.y; s[SK_WZ * c + b] = w.z;
                t->world[b].m[0][3] += vec->x;
                t->world[b].m[1][3] += vec->y;
                t->world[b].m[2][3] += vec->z;
            }
        }
        m->mat[0][3] = m->pos.x;
        m->mat[1][3] = m->pos.y;
        m->mat[2][3] = m->pos.z;
        ((cEm*) m)->satPos = m->pos;
    } else {
        m->mat[0][3] = m->pos.x;
        m->mat[1][3] = m->pos.y;
        m->mat[2][3] = m->pos.z;
    }
}
