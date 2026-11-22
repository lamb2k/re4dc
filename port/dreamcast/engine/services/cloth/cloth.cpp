// Native cloth service (lane eng-svc2). Layout and the reasons for it: cloth.h and docs/engine/SERVICES.md section 12.
//
// Engine bodies for game/pendulum.cpp's PenClothSet, PenClothMove, PenClothMove3, PenClothFixSet, PenClothFixClear
// and its static PenClothReset / penClothAtMake, on ClothChain link arrays and the skeleton service's tables. Every
// float operation is the original's, in its order, through the same math library calls; the random-number calls
// come from the chain's presentation generator (cloth.h). What stays original and is called as it is: the link-against-volume tests
// (penClothAtCk, penClothAtCkBorder, penClothAtCkParallel: pure arithmetic on the volume list), PenClothMove2 (the
// enemy weapons' flails) and the global wind (PenWindSet). A chain this service cannot resolve (a parts table outside
// the owner's bones, a neighbour that is not a link of the chain, a link set up from an upper link set up after it)
// runs the original bodies (renamed pen_orig_* in the native build) through the skeleton's mailbox.
#include "cloth.h"
#include "cloth_kernel.h"
#include "skel.h"
#include "pendulum.h"
#include "pl_cloth.h"
#include "model.h"
#include "atari.h"
#include "global.h"
#include "math_sub.h"
#include "rnd.h"
#include "db_log.h"
#include "svc_prof.h"

extern "C" void* memset(void* dst, int c, unsigned int n);
extern "C" float sinf(float);
extern "C" float acosf(float);
extern "C" void* svc_pool_carve(u32 bytes);   // host: the engine's service memory
extern "C" const char* svc_env(const char* name) __attribute__((weak));   // the PC reference's environment
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
int cloth_control_wind;
int cloth_passes;
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
    {   // lane eng-svcspd1: its control on the PC reference (RE4_SVC_CONTROL=clothbound; hostref svc_io.cpp's svc_env)
        static int read;
        if (!read) {
            read = 1;
            const char* e = svc_env ? svc_env("RE4_SVC_CONTROL") : 0;
            if (e && !__builtin_strcmp(e, "clothbound")) cloth_k_control_bound = 1;
        }
    }
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
        pres_seed(&ch->rng, ch->serial);   // the chain's presentation stream (pres_rng.h)
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

// The first part of a step, common to Move and Move3: the floor, the reset, the volumes, the wind phase
struct Step {
    f32 floorY;
    PenAtWork* at;
    u32 n;
    int reset;
};
void step_begin(ClothChain* ch, Step& s)
{
    SvcProf pr(SP_CLOTH_PRE);
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
    if (!(c->Flag & 0x40)) {
        c->WindSin += pres_f01(&ch->rng) * GlobalWindAdd;
        c->WindSin = LIMIT_ANGLE(c->WindSin);
    }
    for (u32 i = 0; i < s.n; i++) ch->link[i].hit = 0;
    cloth_cnt.moves++;
    cloth_cnt.links += s.n;
}

// the step changed its links' bones only (world matrix and position; a reset also their local matrices and the
// root's history): the records of those that are mailbox bones get them
void step_end(ClothChain* ch, int wasReset)
{
    SvcProf pr(SP_CLOTH_POST);
    if (wasReset) {
        skel_leave(ch->t, 7);
        return;
    }
    for (u32 i = 0; i < ch->n; i++) skel_serve_bone(ch->t, ch->link[i].bone, 1);
}

// the chain's tick on the kernel (cloth_kernel.h): one pass over the links, or the original's pass order
f32 g_windAng[256];
void kernel_step(ClothChain* ch, const Step& s, int variant, const Vec& move, f32 spdLen, const Vec& mpos)
{
    SvcProf pr(SP_CLOTH_KERNEL);
    PenCloth* c = ch->c;
    SkelTable* t = ch->t;
    const u32 cap = t->cap;
    ClothKStep k;
    k.link = (ClothKLink*) ch->link;
    k.cold = (const ClothKCold*) ch->cold;
    k.n = s.n;
    k.variant = variant;
    k.flags = c->Flag;
    k.bundle = c->Bundle_num;
    k.stretchy = variant == 3 ? c->Stretchy : 0.0f;
    k.gravity = c->Gravity;
    k.pGravity = c->pGravity;
    k.rate = c->Rate;
    k.pRate = c->pRate;
    k.pMax = c->pMax;
    k.floorY = s.floorY;
    k.move.x = move.x;
    k.move.y = move.y;
    k.move.z = move.z;
    k.integrate = !(c->Flag & 0x20);
    k.noGravity = cloth_control_nogravity;
    k.wind = variant == 1 && (c->Flag & 0x200) && c->pWindRate;
    k.debugWind = (pG->Debug_flg[0] & 0x200) && !(c->Flag & 0x40) && c->pWindRate;
    k.spdLen = spdLen;
    k.mpos.x = mpos.x;
    k.mpos.y = mpos.y;
    k.mpos.z = mpos.z;
    k.windAng = 0;
    if ((k.wind || k.debugWind) && c->pWindSin && k.integrate) {
        for (u32 i = 0; i < s.n && i < 256; i++) g_windAng[i] = sinf(LIMIT_ANGLE(c->WindSin + c->pWindSin[i])) + 1.0f;
        k.windAng = g_windAng;
    }
    k.pWindRate = c->pWindRate;
    k.windScale = cloth_control_wind ? 2.0f : 1.0f;
    k.globalWind.x = GlobalWind.x;
    k.globalWind.y = GlobalWind.y;
    k.globalWind.z = GlobalWind.z;
    k.wx = t->soa + SK_WX * cap;
    k.wy = t->soa + SK_WY * cap;
    k.wz = t->soa + SK_WZ * cap;
    k.boneMat = &t->world[0].m[0][0];
    k.vol = s.at ? (const ClothKVol*) s.at->pAt : 0;
    k.nVol = s.at ? (u32) s.at->num : 0;
    k.rng = &ch->rng;
    if (cloth_passes == 1) cloth_k_step_passes(&k);
    else if (cloth_passes == 2) cloth_k_step_onepass(&k);
    else cloth_k_step(&k);
}

// PenClothMove
void move1(ClothChain* ch)
{
    PenCloth* c = ch->c;
    cModel* m = ch->m;
    SkelTable* t = ch->t;
    Step s;
    Vec a = {0.0f, 0.0f, 0.0f}, mpos = {0.0f, 0.0f, 0.0f};
    f32 spdLen = 0.0f;
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
    }
    kernel_step(ch, s, 1, a, spdLen, mpos);
    step_end(ch, s.reset);
}

// PenClothMove3
void move3(ClothChain* ch)
{
    PenCloth* c = ch->c;
    cModel* m = ch->m;
    SkelTable* t = ch->t;
    Step s;
    Vec a = {0.0f, 0.0f, 0.0f};
    step_begin(ch, s);
    if (!(c->Flag & 0x20)) {
        const Vec rw = wget(t, 0);
        const SkelHist* h = skel_history(t, 0);
        Vec ro;
        ro.x = h->old[0]; ro.y = h->old[1]; ro.z = h->old[2];
        PSVECSubtract((Vec*) &rw, &ro, &a);
        if (!(m->be_flag & 0x00100000)) PSVECScale(&a, &a, c->Move_rate);
    }
    kernel_step(ch, s, 3, a, 0.0f, a);
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
