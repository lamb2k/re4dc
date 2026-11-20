// Native cloth service (lane eng-svc2). Layout and the reasons for it: cloth.h and docs/engine/SERVICES.md section 12.
//
// Engine bodies for game/pendulum.cpp's PenClothSet, PenClothMove, PenClothMove3, PenClothFixSet, PenClothFixClear
// and its static PenClothReset / penClothAtMake, on ClothChain link arrays and the skeleton service's tables. Every
// float operation is the original's, in its order, through the same math library calls; the random-number calls
// are the original's, in its order. What stays original and is called as it is: the link-against-volume tests
// (penClothAtCk, penClothAtCkBorder, penClothAtCkParallel: pure arithmetic on the volume list), PenClothMove2 (the
// enemy weapons' flails) and the global wind (PenWindSet). A chain this service cannot resolve (a parts table outside
// the owner's bones, a neighbour that is not a link of the chain, a link set up from an upper link set up after it)
// runs the original bodies (renamed pen_orig_* in the native build) through the skeleton's mailbox.
#include "cloth.h"
#include "skel.h"
#include "pendulum.h"
#include "pl_cloth.h"
#include "model.h"
#include "atari.h"
#include "global.h"
#include "math_sub.h"
#include "rnd.h"
#include "db_log.h"

extern "C" void* memset(void* dst, int c, unsigned int n);
extern "C" float sinf(float);
extern "C" float acosf(float);
extern "C" void* svc_pool_carve(u32 bytes);   // host: the engine's service memory
// the original bodies, renamed in the native build (svc/svc.mk): the fallback for chains this service cannot serve
extern "C" void pen_orig_Set(cModel* m, PenCloth* c, f32 len);
extern "C" void pen_orig_Move(cModel* m, PenCloth* c);
extern "C" void pen_orig_Move3(cModel* m, PenCloth* c);
extern "C" void pen_orig_FixSet(cModel* m, PenCloth* c, int no, Vec* pos);
extern "C" void pen_orig_FixClear(cModel* m, PenCloth* c, int no);

extern "C" {
ClothCounters cloth_cnt;
int cloth_control_short;
int cloth_control_nogravity;
int cloth_control_droprng;
}

namespace {

// ---------------------------------------------------------------------------------------------------------------
// memory: one carve from the service region (chains live as long as their owner; a chain set up again reuses its
// block when its size has not changed)
constexpr u32 kPool = 0x8000;
constexpr u32 kMaxChains = 32;
constexpr u32 kAtWork = 0x800;   // the tick's collision volumes (PenAtWork: 8 B + 0x84 a volume)
u8* g_pool;
u32 g_used;
PenAtWork* g_atwk;
ClothChain* g_ch[kMaxChains];
u32 g_nch;
u32 g_serial;
int g_dropped;

void* alloc(u32 bytes)
{
    if (!g_pool) {
        g_pool = (u8*) svc_pool_carve(kPool + kAtWork);
        if (!g_pool) return 0;
        g_atwk = (PenAtWork*) (g_pool + kPool);
    }
    bytes = (bytes + 31u) & ~31u;
    if (g_used + bytes > kPool) {
        pLog->err(0, 0, "cloth: pool exhausted");
        return 0;
    }
    void* p = g_pool + g_used;
    g_used += bytes;
    memset(p, 0, bytes);
    return p;
}

ClothChain* find(const PenCloth* c)
{
    for (u32 i = 0; i < g_nch; i++)
        if (g_ch[i]->c == c) return g_ch[i];
    return 0;
}
void forget(const PenCloth* c)
{
    for (u32 i = 0; i < g_nch; i++)
        if (g_ch[i]->c == c) {
            g_ch[i] = g_ch[--g_nch];
            return;
        }
}

// ---------------------------------------------------------------------------------------------------------------
// bones
inline Vec wget(SkelTable* t, u32 b)
{
    const u32 c = t->cap;
    Vec v;
    v.x = t->soa[SK_WX * c + b];
    v.y = t->soa[SK_WY * c + b];
    v.z = t->soa[SK_WZ * c + b];
    return v;
}
inline void wput(SkelTable* t, u32 b, const Vec& v)
{
    const u32 c = t->cap;
    t->soa[SK_WX * c + b] = v.x;
    t->soa[SK_WY * c + b] = v.y;
    t->soa[SK_WZ * c + b] = v.z;
}
inline f32 (*MAT(SkelTable* t, u32 b))[4] { return t->world[b].m; }

// a parts number of the chain (through the owner's parts table when it gave one) -> bone
int parts_bone(cModel* m, PenCloth* c, SkelTable* t, int no)
{
    if (c->pPtbl) return skel_record_bone(t, c->pPtbl[no]);
    return skel_parts_bone(m, no);
}

// ---------------------------------------------------------------------------------------------------------------
// set-up: resolve the chain once (0: this service cannot serve it)
ClothChain* build(cModel* m, PenCloth* c)
{
    SkelTable* t = skel_table_for(m);
    if (!t || c->Num <= 0 || c->Num > 255) return 0;
    const u32 n = (u32) c->Num;
    cModel* am = c->pEm_at ? c->pEm_at : m;
    SkelTable* ta = 0;
    u32 nAt = 0;
    if (c->pAtset && c->At_num > 0) {
        ta = skel_table_for(am);
        if (!ta) return 0;
        nAt = (u32) c->At_num;
    }
    u8 bone[256], linkOf[256];
    memset(linkOf, CLOTH_NONE, sizeof linkOf);
    for (u32 i = 0; i < n; i++) {
        if (c->pCloth[i] == 0xFF) return 0;
        const int b = parts_bone(m, c, t, c->pCloth[i]);
        if (b < 0 || b > 254 || linkOf[b] != CLOTH_NONE) return 0;
        bone[i] = (u8) b;
        linkOf[b] = (u8) i;
    }
    // neighbours: parts numbers -> links of this chain
    const u8* const tabs[5] = {c->pParent, c->pLeft, c->pRight, c->pUpLeft, c->pUpRight};
    u8 nb[5][256];
    for (int k = 0; k < 5; k++)
        for (u32 i = 0; i < n; i++) {
            nb[k][i] = CLOTH_NONE;
            if (!tabs[k] || tabs[k][i] == 0xFF) continue;
            const int b = parts_bone(m, c, t, tabs[k][i]);
            if (b < 0 || linkOf[b] == CLOTH_NONE) return 0;   // a neighbour outside the chain
            nb[k][i] = linkOf[b];
        }
    u8 childBone[256];
    for (u32 i = 0; i < n; i++) {
        childBone[i] = CLOTH_NONE;
        if (c->pChild[i] == 0xFF) {
            // set up from its upper link's rest values: that link must be set up first
            if (c->pParent[i] != 0xFF && nb[0][i] > i) return 0;
            continue;
        }
        const int b = skel_parts_bone(m, c->pChild[i]);
        if (b < 0) return 0;
        childBone[i] = (u8) b;
    }
    u8 atBone[64];
    if (nAt > 32) return 0;
    for (u32 k = 0; k < nAt; k++) {
        const int b0 = skel_parts_bone(am, c->pAtset[k].P1);
        const int b1 = skel_parts_bone(am, c->pAtset[k].P2);
        if (b0 < 0 || b1 < 0) return 0;
        atBone[2 * k] = (u8) b0;
        atBone[2 * k + 1] = (u8) b1;
    }
    const int root = skel_parts_bone(m, 0);
    if (root != 0 || !skel_history(t, 0)) return 0;   // the root's world_old: the skeleton keeps bone 0's
    ClothChain* ch = find(c);
    const u32 bytes = 64 + 64 * n + 48 * n + ((2 * nAt + 31u) & ~31u);
    if (!ch || ch->bytes != bytes || ch->m != m) {
        forget(c);
        if (g_nch >= kMaxChains) return 0;
        u8* blk = (u8*) alloc(bytes);
        if (!blk) return 0;
        ch = (ClothChain*) blk;
        ch->bytes = bytes;
        ch->link = (ClothLink*) (blk + 64);
        ch->cold = (ClothCold*) (blk + 64 + 64 * n);
        ch->atBone = blk + 64 + 112 * n;
        ch->serial = ++g_serial;
        g_ch[g_nch++] = ch;
    }
    ch->c = c;
    ch->m = m;
    ch->t = t;
    ch->tAt = ta;
    ch->n = (u16) n;
    ch->nAt = (u16) nAt;
    for (u32 i = 0; i < n; i++) {
        ClothLink& L = ch->link[i];
        L.bone = bone[i];
        L.up = nb[0][i];
        for (int k = 0; k < 4; k++) L.side[k] = nb[1 + k][i];
        L.pad = childBone[i];
    }
    for (u32 k = 0; k < 2 * nAt; k++) ch->atBone[k] = atBone[k];
    cloth_cnt.chains++;
    return ch;
}

// ---------------------------------------------------------------------------------------------------------------
// penClothAtMake on the volumes' bones
PenAtWork* at_make(ClothChain* ch)
{
    PenCloth* cl = ch->c;
    CLOTH_AT_SET* at = cl->pAtset;
    const int n = cl->At_num;
    cModel* am = cl->pEm_at ? cl->pEm_at : ch->m;
    if (at == 0 || n == 0 || am == 0 || !ch->tAt) return 0;
    SkelTable* ta = ch->tAt;
    PenAtWork* wk = g_atwk;
    PenAt* a = wk->at;
    Vec v0, v1, cc, ax, d, up;
    wk->num = n;
    wk->pAt = a;
    for (int i = 0; i < n; i++, at++, a++) {
        f32 rate = at->Weight;
        PSMTXMultVec(MAT(ta, ch->atBone[2 * i]), &at->Ofs1, &v0);
        PSMTXMultVec(MAT(ta, ch->atBone[2 * i + 1]), &at->Ofs2, &v1);
        switch (at->Type) {
        case 0:
        default:
            a->type = 0;
            PosToPos(&v1, &v0, &cc, rate);
            a->p0 = cc;
            a->r = at->R;
            break;
        case 1:
            a->type = 1;
            a->r = at->R;
            a->p0 = v0;
            a->p1 = v1;
            a->len = GetDistance3(&v0, &v1);
            PSVECSubtract(&v1, &v0, &d);
            ax.x = fabsf(d.x);
            ax.z = fabsf(d.z);
            if (ax.x < ax.z) {
                up.x = 1.0f;
                up.y = 0.0f;
                up.z = 0.0f;
            } else {
                up.x = 0.0f;
                up.y = 0.0f;
                up.z = 1.0f;
            }
            PSVECCrossProduct(&d, &up, &ax);
            PSVECCrossProduct(&ax, &d, &up);
            VECNormalize(&ax, &ax);
            VECNormalize(&d, &d);
            VECNormalize(&up, &up);
            a->mat[0][0] = ax.x;
            a->mat[1][0] = ax.y;
            a->mat[2][0] = ax.z;
            a->mat[0][1] = d.x;
            a->mat[1][1] = d.y;
            a->mat[2][1] = d.z;
            a->mat[0][2] = up.x;
            a->mat[1][2] = up.y;
            a->mat[2][2] = up.z;
            TransMatrix(a->mat, &v0);
            PSMTXInverse(a->mat, a->inv);
            break;
        }
    }
    cloth_cnt.at_volumes += n;
    return wk;
}

// PenClothReset: every link back to its rest pose (the model was warped, be_flag 0x00200000)
void reset(ClothChain* ch)
{
    SkelTable* t = ch->t;
    const u32 cap = t->cap;
    for (u32 i = 0; i < ch->n; i++) {
        ClothLink& L = ch->link[i];
        const u32 b = L.bone;
        Vec ang, pos, scale, w;
        ang.x = t->soa[SK_AX * cap + b]; ang.y = t->soa[SK_AY * cap + b]; ang.z = t->soa[SK_AZ * cap + b];
        pos.x = t->soa[SK_PX * cap + b]; pos.y = t->soa[SK_PY * cap + b]; pos.z = t->soa[SK_PZ * cap + b];
        scale.x = t->soa[SK_SX * cap + b]; scale.y = t->soa[SK_SY * cap + b]; scale.z = t->soa[SK_SZ * cap + b];
        f32 (*pm)[4] = (f32 (*)[4]) skel_parent_mat(t, b);
        f32 (*lm)[4] = t->lmat[b].m;
        RotMatrix(lm, &ang);
        TransMatrix(lm, &pos);
        ScaleMatrix(lm, &scale);
        PSMTXConcat(pm, lm, MAT(t, b));
        PSMTXMultVec(pm, &pos, &w);
        wput(t, b, w);
        PSMTXMultVec(MAT(t, b), &ch->cold[i].dir, &L.pos);
        L.oldPos = L.pos;
        L.speed.x = 0.0f;
        L.speed.y = 0.0f;
        L.speed.z = 0.0f;
    }
    SkelHist* h = skel_history(t, 0);
    const Vec r = wget(t, 0);
    h->old[0] = h->old2[0] = r.x;
    h->old[1] = h->old2[1] = r.y;
    h->old[2] = h->old2[2] = r.z;
    cloth_cnt.resets++;
}

inline void fix(ClothChain* ch, u32 i)
{
    if (ch->link[i].fix & 1) ch->link[i].pos = ch->cold[i].fixPos;
}
// PEN_FLOOR_CK: above the floor; a link landed under its upper link is jittered (two generator draws)
inline void floor_ck(PenCloth* c, ClothChain* ch, u32 i, f32 floorY)
{
    if (c->Flag & 0x100) return;
    ClothLink& L = ch->link[i];
    if (L.pos.y < floorY) {
        L.pos.y = floorY;
        if (L.up != CLOTH_NONE) {
            const ClothLink& U = ch->link[L.up];
            if (L.pos.x == U.pos.x && L.pos.z == U.pos.z) {
                L.pos.x += fRand1_1();
                L.pos.z += fRand1_1();
            }
        }
    }
}
// PEN_FLOOR_CK3: both ends of a constraint
inline void floor_ck3(PenCloth* c, ClothLink& L, ClothLink& U, f32 floorY)
{
    if (c->Flag & 0x100) return;
    if (L.pos.y < floorY) {
        L.pos.y = floorY;
        if (L.pos.x == U.pos.x && L.pos.z == U.pos.z) {
            L.pos.x += fRand1_1();
            L.pos.z += fRand1_1();
        }
    }
    if (U.pos.y < floorY) U.pos.y = floorY;
}
inline int at_ck(PenCloth* c, Vec* p, Vec* up, PenAtWork* at)
{
    return (c->Flag & 0x80) ? penClothAtCkBorder(p, up, at) : penClothAtCk(p, up, at);
}

// The first part of a step, common to Move and Move3: the floor, the reset, the volumes, the wind phase
struct Step {
    f32 floorY;
    PenAtWork* at;
    Vec wind;
    u32 n;
    int reset;
};
void step_begin(ClothChain* ch, Step& s)
{
    PenCloth* c = ch->c;
    cModel* m = ch->m;
    SkelTable* t = ch->t;
    skel_enter(t);
    if (ch->tAt && ch->tAt != t) skel_enter(ch->tAt);
    s.n = cloth_control_short ? ch->n - 1 : ch->n;
    s.floorY = -100000.0f;
    if (!(c->Flag & 0x100)) {
        Vec r = wget(t, 0);
        s.floorY = SatMgr.getFloor(&r, 600.0f, 100000.0f, 0, 0) + 30.0f;
    }
    s.reset = (m->be_flag & 0x00200000) != 0;
    if (s.reset) reset(ch);
    s.at = 0;
    if (!(c->Flag & 1)) s.at = at_make(ch);
    f32 ang = 1.0f;
    if (!(c->Flag & 0x40)) {
        f32 r;
        if (cloth_control_droprng && !g_dropped) {   // control: one generator call dropped
            g_dropped = 1;
            r = 0.0f;
        } else {
            r = fRand0_1();
        }
        c->WindSin += r * GlobalWindAdd;
        c->WindSin = LIMIT_ANGLE(c->WindSin);
        PSVECScale(&GlobalWind, &s.wind, sinf(c->WindSin) + ang);
    }
    for (u32 i = 0; i < s.n; i++) ch->link[i].hit = 0;
    cloth_cnt.moves++;
    cloth_cnt.links += s.n;
}

// the angle limit against the upper link (Move and Move3 alike)
void angle_limit(ClothChain* ch, const Step& s)
{
    PenCloth* c = ch->c;
    SkelTable* t = ch->t;
    Mtx mtx;
    Vec a, b, v;
    f32 d, ang, spdRate;
    for (u32 i = 0; i < s.n; i++) {
        ClothLink& L = ch->link[i];
        const u32 pb = L.bone;
        if (L.fix & 1) continue;
        if (L.up != CLOTH_NONE) {
            ClothLink& U = ch->link[L.up];
            wput(t, pb, U.pos);
            const Vec nw = wget(t, U.bone);
            PSVECSubtract(&U.pos, (Vec*) &nw, &a);
            if (a.x == 0.0f && a.y == 0.0f && a.z == 0.0f) {
                a = L.nrm;
            } else {
                VECNormalize(&a, &a);
            }
        } else {
            PSMTXMultVecSR(MAT(t, pb), &L.nrm, &a);
            VECNormalize(&a, &a);
        }
        Vec pw = wget(t, pb);
        PSVECSubtract(&L.pos, &pw, &b);
        d = SQRTF(b.x * b.x + b.y * b.y + b.z * b.z);
        if (b.x == 0.0f && b.y == 0.0f && b.z == 0.0f) {
            b = L.nrm;
        } else {
            VECNormalize(&b, &b);
        }
        ang = acosf(PSVECDotProduct(&a, &b));
        spdRate = c->pMax[i];
        if (ang > spdRate && ang < PI - 0.01f) {
            spdRate = ang * 0.2f + spdRate * 0.8f;
            PSVECCrossProduct(&a, &b, &v);
            PSMTXRotAxisRad(mtx, &v, spdRate);
            PSMTXMultVecSR(mtx, &a, &L.pos);
            PSVECScale(&L.pos, &L.pos, d);
            PSVECAdd(&L.pos, &pw, &L.pos);
        }
    }
}

// the matrices: every link's bone looks along its link (Move and Move3 alike)
void matrices(ClothChain* ch, const Step& s)
{
    PenCloth* c = ch->c;
    SkelTable* t = ch->t;
    Mtx mtx;
    Vec a, b, v;
    f32 ang, spdRate;
    int hit;
    for (u32 i = 0; i < s.n; i++) {
        ClothLink& L = ch->link[i];
        const u32 pb = L.bone;
        ClothLink* U = 0;
        if (L.up != CLOTH_NONE) {
            U = &ch->link[L.up];
            wput(t, pb, U->pos);
        }
        Vec pw = wget(t, pb);
        if (!(c->Flag & 8)) {
            PSVECSubtract(&L.pos, &pw, &v);
            if (v.x == 0.0f && v.y == 0.0f && v.z == 0.0f) {
                v = L.nrm;
            } else {
                VECNormalize(&v, &v);
            }
            PSVECScale(&v, &v, L.len);
            PSVECAdd(&pw, &v, &L.pos);
        }
        if (U) {
            hit = at_ck(c, &L.pos, &U->pos, s.at);
        } else {
            hit = at_ck(c, &L.pos, &pw, s.at);
            wput(t, pb, pw);
        }
        if (hit) L.hit |= 1;
        if (!(c->Flag & 0x100)) {   // PEN_FLOOR_CK2
            if (L.pos.y < s.floorY) {
                L.pos.y = s.floorY;
                if (U && L.pos.x == U->pos.x && L.pos.z == U->pos.z) {
                    L.pos.x += fRand1_1();
                    L.pos.z += fRand1_1();
                }
            }
        }
        fix(ch, i);
        spdRate = c->pRate ? c->pRate[i] : c->Rate;
        if (L.hit & 1) spdRate *= 0.3f;
        PSVECSubtract(&L.pos, &L.oldPos, &L.speed);
        PSVECScale(&L.speed, &L.speed, spdRate);
        PSMTXMultVecSR(MAT(t, pb), &L.nrm, &a);
        PSVECSubtract(&L.pos, &pw, &b);
        if (b.x == 0.0f && b.y == 0.0f && b.z == 0.0f) {
            b = L.nrm;
        } else {
            VECNormalize(&b, &b);
        }
        ang = acosf(PSVECDotProduct(&a, &b));
        if (ang > 0.01f && ang < PI - 0.01f) {
            PSVECCrossProduct(&a, &b, &a);
            PSMTXRotAxisRad(mtx, &a, ang);
            PSMTXConcat(mtx, MAT(t, pb), MAT(t, pb));
        }
        TransMatrix(MAT(t, pb), &pw);
    }
}

// the step changed its links' bones only (world matrix and position; a reset also their local matrices and the
// root's history): the records of those that are mailbox bones get them
void step_end(ClothChain* ch, int wasReset)
{
    if (wasReset) {
        skel_leave(ch->t, 7);
        return;
    }
    for (u32 i = 0; i < ch->n; i++) skel_serve_bone(ch->t, ch->link[i].bone, 1);
}

// the debug wind (pG->Debug_flg[0] & 0x200), both variants
inline void debug_wind(PenCloth* c, ClothLink& L, u32 i, Vec* wind)
{
    if ((pG->Debug_flg[0] & 0x200) && !(c->Flag & 0x40) && c->pWindRate) {
        f32 ang = 0.0f;
        if (c->pWindSin) {
            ang = sinf(LIMIT_ANGLE(c->WindSin + c->pWindSin[i])) + 1.0f;
            PSVECScale(&GlobalWind, wind, ang);
        }
        if (c->pWindRate) {
            PSVECScale(&GlobalWind, wind, ang);
            PSVECScale(wind, wind, c->pWindRate[i]);
        }
        PSVECAdd(&L.pos, wind, &L.pos);
    }
}

// PenClothMove
void move1(ClothChain* ch)
{
    PenCloth* c = ch->c;
    cModel* m = ch->m;
    SkelTable* t = ch->t;
    Step s;
    Vec v, a, mpos;
    f32 spdLen, ang, d;
    int hit;
    step_begin(ch, s);
    if (!(c->Flag & 0x20)) {
        const Vec rw = wget(t, 0);
        const SkelHist* h = skel_history(t, 0);
        Vec ro;
        ro.x = h->old[0]; ro.y = h->old[1]; ro.z = h->old[2];
        mpos = rw;
        PSVECSubtract((Vec*) &rw, &ro, &a);
        spdLen = SQRTF(a.x * a.x + a.z * a.z);
        if (spdLen > 100.0f) spdLen = 100.0f;
        spdLen *= 0.01f * 5.0f;
        if (m->be_flag & 0x00100000) {
            spdLen = 0.0f;
        } else {
            PSVECScale(&a, &a, c->Move_rate);
        }
        for (u32 i = 0; i < s.n; i++) {
            ClothLink& L = ch->link[i];
            PSVECAdd(&L.pos, &a, &L.pos);
            L.oldPos = L.pos;
            if (!cloth_control_nogravity) {
                if (c->pGravity) {
                    L.speed.y -= c->pGravity[i];
                } else {
                    L.speed.y -= c->Gravity;
                }
            }
            PSVECAdd(&L.pos, &L.speed, &L.pos);
            if ((c->Flag & 0x200) && c->pWindRate) {
                PSVECSubtract(&L.pos, &mpos, &v);
                v.y = 0.0f;
                if (v.x != 0.0f && v.z != 0.0f) {
                    PSVECNormalize(&v, &v);
                    PSVECScale(&v, &v, spdLen);
                    ang = 1.0f;
                    if (c->pWindSin) {
                        ang = sinf(LIMIT_ANGLE(c->WindSin + c->pWindSin[i])) + 1.0f;
                        PSVECScale(&v, &v, ang);
                    }
                    if (c->pWindRate) {
                        PSVECScale(&v, &v, ang);
                        PSVECScale(&v, &v, c->pWindRate[i]);
                    }
                    PSVECAdd(&L.pos, &v, &L.pos);
                }
            }
            debug_wind(c, L, i, &s.wind);
            floor_ck(c, ch, i, s.floorY);
            fix(ch, i);
        }
    }
    if (!(c->Flag & 0x10) && c->pMax) angle_limit(ch, s);
    if (!(c->Flag & 2)) {
        const u8* const tabs[4] = {c->pLeft, c->pRight, c->pUpLeft, c->pUpRight};
        for (u32 k = 0; k < c->Bundle_num; k++) {
            for (u32 i = 0; i < s.n; i++) {
                ClothLink& L = ch->link[i];
                const ClothCold& C = ch->cold[i];
                if (!(c->Flag & 4)) {
                    for (int q = 0; q < 4; q++) {
                        if (!(tabs[q] && tabs[q][i] < 0xFF)) continue;
                        ClothLink& U = ch->link[L.side[q]];
                        PSVECSubtract(&U.pos, &L.pos, &v);
                        d = SQRTF(v.x * v.x + v.y * v.y + v.z * v.z);
                        PSVECScale(&v, &v, (C.dist[q]) / d - 0.5f);
                        PSVECSubtract(&L.pos, &v, &L.pos);
                        PSVECAdd(&U.pos, &v, &U.pos);
                    }
                }
                if (L.up != CLOTH_NONE) {
                    ClothLink& U = ch->link[L.up];
                    PSVECSubtract(&U.pos, &L.pos, &v);
                    d = SQRTF(v.x * v.x + v.y * v.y + v.z * v.z);
                    PSVECScale(&v, &v, 0.5f / d * (L.len - d));
                    PSVECAdd(&U.pos, &v, &U.pos);
                    PSVECSubtract(&L.pos, &v, &L.pos);
                    hit = at_ck(c, &L.pos, &U.pos, s.at);
                    if (hit) L.hit |= 1;
                    floor_ck(c, ch, i, s.floorY);
                    fix(ch, i);
                    fix(ch, L.up);
                } else {
                    Vec pw = wget(t, L.bone);
                    PSVECSubtract(&pw, &L.pos, &v);
                    d = SQRTF(v.x * v.x + v.y * v.y + v.z * v.z);
                    PSVECScale(&v, &v, 0.5f / d * (L.len - d));
                    PSVECSubtract(&L.pos, &v, &L.pos);
                    hit = at_ck(c, &L.pos, &pw, s.at);
                    wput(t, L.bone, pw);
                    if (hit) L.hit |= 1;
                    floor_ck(c, ch, i, s.floorY);
                    fix(ch, i);
                }
            }
        }
    }
    matrices(ch, s);
    step_end(ch, s.reset);
}

// PenClothMove3
void move3(ClothChain* ch)
{
    PenCloth* c = ch->c;
    cModel* m = ch->m;
    SkelTable* t = ch->t;
    Step s;
    Vec v, a;
    f32 d;
    int hit;
    step_begin(ch, s);
    if (!(c->Flag & 0x20)) {
        const Vec rw = wget(t, 0);
        const SkelHist* h = skel_history(t, 0);
        Vec ro;
        ro.x = h->old[0]; ro.y = h->old[1]; ro.z = h->old[2];
        if (m->be_flag & 0x00100000) {
            PSVECSubtract((Vec*) &rw, &ro, &a);
        } else {
            PSVECSubtract((Vec*) &rw, &ro, &a);
            PSVECScale(&a, &a, c->Move_rate);
        }
        for (u32 i = 0; i < s.n; i++) {
            ClothLink& L = ch->link[i];
            PSVECAdd(&L.pos, &a, &L.pos);
            L.oldPos = L.pos;
            if (!cloth_control_nogravity) {
                if (c->pGravity) {
                    L.speed.y -= c->pGravity[i];
                } else {
                    L.speed.y -= c->Gravity;
                }
            }
            PSVECAdd(&L.pos, &L.speed, &L.pos);
            debug_wind(c, L, i, &s.wind);
            floor_ck(c, ch, i, s.floorY);
            fix(ch, i);
        }
    }
    if (!(c->Flag & 0x10) && c->pMax) angle_limit(ch, s);
    if (!(c->Flag & 2)) {
        for (u32 k = 0; k < c->Bundle_num; k++) {
            for (u32 i = 0; i < s.n; i++) {
                ClothLink& L = ch->link[i];
                const ClothCold& C = ch->cold[i];
                if (!(c->Flag & 4)) {
                    if (c->pUpLeft && c->pUpLeft[i] < 0xFF) {
                        ClothLink& U = ch->link[L.side[2]];
                        penClothAtCkParallel(&L.pos, &U.pos, s.at);
                        floor_ck3(c, L, U, s.floorY);
                        fix(ch, i);
                        fix(ch, L.side[2]);
                    }
                    if (c->pUpRight && c->pUpRight[i] < 0xFF) {
                        ClothLink& U = ch->link[L.side[3]];
                        penClothAtCkParallel(&L.pos, &U.pos, s.at);
                        floor_ck3(c, L, U, s.floorY);
                        fix(ch, i);
                        fix(ch, L.side[3]);
                    }
                    for (int q = 0; q < 2; q++) {
                        const u8* tbl = q == 0 ? c->pLeft : c->pRight;
                        if (!(tbl && tbl[i] < 0xFF)) continue;
                        ClothLink& U = ch->link[L.side[q]];
                        penClothAtCkParallel(&L.pos, &U.pos, s.at);
                        PSVECSubtract(&U.pos, &L.pos, &v);
                        d = SQRTF(v.x * v.x + v.y * v.y + v.z * v.z);
                        PSVECScale(&v, &v, (d * 0.5f - (C.dist[q])) * c->Stretchy / d);
                        PSVECAdd(&L.pos, &v, &L.pos);
                        PSVECSubtract(&U.pos, &v, &U.pos);
                        floor_ck3(c, L, U, s.floorY);
                        fix(ch, i);
                        fix(ch, L.side[q]);
                    }
                }
                if (L.up != CLOTH_NONE) {
                    ClothLink& U = ch->link[L.up];
                    penClothAtCkParallel(&L.pos, &U.pos, s.at);
                    PSVECSubtract(&U.pos, &L.pos, &v);
                    d = SQRTF(v.x * v.x + v.y * v.y + v.z * v.z);
                    PSVECScale(&v, &v, (d - L.len) * 0.5f * c->Stretchy / d);
                    PSVECAdd(&L.pos, &v, &L.pos);
                    PSVECSubtract(&U.pos, &v, &U.pos);
                    floor_ck3(c, L, U, s.floorY);
                    fix(ch, i);
                    fix(ch, L.up);
                } else {
                    Vec pw = wget(t, L.bone);
                    hit = at_ck(c, &L.pos, &pw, s.at);
                    wput(t, L.bone, pw);
                    if (hit) L.hit |= 1;
                    PSVECSubtract(&pw, &L.pos, &v);
                    d = SQRTF(v.x * v.x + v.y * v.y + v.z * v.z);
                    PSVECScale(&v, &v, (d - L.len) * 0.5f * c->Stretchy / d);
                    PSVECAdd(&L.pos, &v, &L.pos);
                    if (!(c->Flag & 0x100)) {
                        if (L.pos.y < s.floorY) L.pos.y = s.floorY;
                    }
                    fix(ch, i);
                }
            }
        }
    }
    matrices(ch, s);
    step_end(ch, s.reset);
}

}   // namespace

// =================================================================================================================
// the original entry points, engine bodies
extern "C" void PenClothSet(cModel* m, PenCloth* c, f32 len)
{
    if (c->Num == 0) return;
    ClothChain* ch = build(m, c);
    if (!ch) {
        forget(c);
        cloth_cnt.fallback++;
        pen_orig_Set(m, c, len);
        return;
    }
    SkelTable* t = ch->t;
    skel_enter(t);
    Vec v;
    for (u32 i = 0; i < ch->n; i++) {
        ClothLink& L = ch->link[i];
        ClothCold& C = ch->cold[i];
        const u32 b = L.bone;
        t->world[b].flags |= 0x06000000;   // PenParts::x1C0 is MotionParts::flags: no key history, no blend
        if (c->pChild[i] == 0xFF) {
            if (c->pParent[i] == 0xFF) {
                L.len = len;
                C.dir.x = 0.0f;
                C.dir.y = -len;
                C.dir.z = 0.0f;
                L.nrm.x = 0.0f;
                L.nrm.y = -1.0f;
                L.nrm.z = 0.0f;
                PSMTXMultVec(MAT(t, b), &C.dir, &L.pos);
            } else {
                const ClothLink& U = ch->link[L.up];
                L.len = U.len;
                C.dir = ch->cold[L.up].dir;
                L.nrm = U.nrm;
                L.pos = wget(t, b);
                PSMTXMultVecSR(m->mat, &C.dir, &v);
                PSVECAdd(&L.pos, &v, &L.pos);
            }
        } else {
            Vec cw = wget(t, L.pad), pw = wget(t, b);
            L.pos = cw;
            L.len = GetDistance3(&pw, &cw);
            PSVECSubtract(&cw, &pw, &C.dir);
            VECNormalize(&C.dir, &L.nrm);
        }
        L.speed.x = 0.0f;
        L.speed.y = 0.0f;
        L.speed.z = 0.0f;
    }
    const u8* const tabs[4] = {c->pLeft, c->pRight, c->pUpLeft, c->pUpRight};
    for (u32 i = 0; i < ch->n; i++) {
        ClothLink& L = ch->link[i];
        for (int q = 0; q < 4; q++)
            if (tabs[q] && tabs[q][i] < 0xFF) ch->cold[i].dist[q] = GetDistance3(&L.pos, &ch->link[L.side[q]].pos) * 0.5f;
    }
    for (u32 i = 0; i < ch->n; i++) skel_serve_bone(t, ch->link[i].bone, 1);
}

extern "C" void PenClothMove(cModel* m, PenCloth* c)
{
    if (c->Num == 0) return;
    ClothChain* ch = find(c);
    if (!ch || ch->m != m) {
        pen_orig_Move(m, c);
        return;
    }
    move1(ch);
}

extern "C" void PenClothMove3(cModel* m, PenCloth* c)
{
    if (c->Num == 0) return;
    ClothChain* ch = find(c);
    if (!ch || ch->m != m) {
        pen_orig_Move3(m, c);
        return;
    }
    move3(ch);
}

extern "C" void PenClothFixSet(cModel* m, PenCloth* c, int no, Vec* pos)
{
    ClothChain* ch = find(c);
    if (!ch || ch->m != m) {
        pen_orig_FixSet(m, c, no, pos);
        return;
    }
    if (c->pCloth[no] != 0xFF) {
        ch->cold[no].fixPos = *pos;
        ch->link[no].fix |= 1;
    }
}

extern "C" void PenClothFixClear(cModel* m, PenCloth* c, int no)
{
    ClothChain* ch = find(c);
    if (!ch || ch->m != m) {
        pen_orig_FixClear(m, c, no);
        return;
    }
    if (c->pCloth[no] != 0xFF) ch->link[no].fix &= ~1;
}

extern "C" u32 cloth_chain_count(void) { return g_nch; }
extern "C" ClothChain* cloth_chain_at(u32 i) { return i < g_nch ? g_ch[i] : 0; }
