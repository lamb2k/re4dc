#if defined(RE4DC_FALLBACK_AUDIT29) && RE4DC_FALLBACK_AUDIT29
#include "fallback_audit29.h"
#endif
#line 1
// game/atari.cpp: the scenario collision ("atari") system. cSat is one collision piece: a SAT
// file of triangles (floors, slopes, walls; each with a 24-bit attribute word) partitioned into
// XZ blocks, placed by a matrix. SatMgr holds the room's pieces and the ones objects create,
// EatMgr the effect-collision set (what bullets, thrown objects and effects hit). Queries:
// check / checkAir push a character's body out of the scenery (scrAtCheckSphere, at_sub.cpp
// primitives), hitCheck traces a line for the nearest polygon, getFloor probes the floor,
// adjust sweeps a sphere; disp draws the polygons for the debug pages.

#include "atari.h"
#include "re4dc_xm.h" // GAME_SH4ZAM_LOGIC (lane sh4zam-direct)
#include "atariInfo.h"
#include "global.h"
#include "model.h"
#include "em.h"
#include "math_sub.h"
#include "dbmodule.h"
#include "main.h"
#include "gx.h"
#if defined(RE4DC_EL_CENSUS) && RE4DC_EL_CENSUS
#include "el_census.h"   // EL_CENSUS (game30.mk; lane el): the line-query census hooks
#endif

#line 30 "D:/Bio4/Prog/atari.cpp"

extern "C" {
// Dolphin SDK performance monitor registers (base/PPCArch.h)
void PPCMtpmc1(u32 v);
void PPCMtpmc2(u32 v);
void PPCMtpmc3(u32 v);
void PPCMtpmc4(u32 v);
void PPCMtmmcr0(u32 v);
void PPCMtmmcr1(u32 v);
u32 PPCMfpmc1();
void* memcpy(void* dst, const void* src, unsigned int n);
}

// at_sub attribute filter bypass mode (cSatMgr::seCk of the manager running the check)
int SEck;
struct SEckView {
    int v;
};

// game/game.cpp collision profiling counters (debug page 0x14)
extern u32 g_at2_total;
extern u32 g_at2_cnt[];
extern u32 g_at2_cyc[];
extern u32 g_at2_total_cyc;

// pointer to game memory (0x80000000 .. 0x82FFFFFF)
#define VALID_PTR(p) ((u32) (p) >= RE4_MEM_LO && (u32) (p) <= RE4_MEM_HI)

// polygons already tested during one check (one bit per polygon index)
u8 polyBit[0x400];
// the piece the last hitCheck2 hit (hitCheck transforms the normal with its matrix)
static cSat* pBypassAt;
#if defined(RE4DC_LOGIC_WASTE) && RE4DC_LOGIC_WASTE >= 2
void re4dc_lw_sat_epoch();   // LOGIC_WASTE (the block at the end of this file)
#endif
#if defined(RE4DC_LQ_MEMO) && RE4DC_LQ_MEMO
// GAME_LQ_MEMO (game30.mk; lane el; exact): wallAdjust's repeated line query (the block at the end of this file).
static int lqmVecSame(const Vec* a, const Vec* b);
#if RE4DC_LQ_MEMO == 2
static void lqmPairCount(int same, int mis);
#endif
#if defined(RE4DC_DECISION_TRACE) && RE4DC_DECISION_TRACE
#define LQM_NOTES 10                  // decision notes a memo entry keeps (trace builds)
#define LQM_NOTE_OVER 0xFFFFFFFFu
struct LqmNotes {
    u32 n;                            // words recorded (3 per note), LQM_NOTE_OVER when they did not fit
    u32 w[3 * LQM_NOTES];
};
static void lqmNotesBegin(LqmNotes* r);
static void lqmNotesEnd(LqmNotes* r);
static void lqmNotesReplay(const LqmNotes* r);
#endif
#endif

int atck(Vec* vec0, Vec* vec1, cAtariInfo* info, cModel* m, int flag);
int blkPolySphereCk(cSat* sat, cSatBlock* blk, Vec* pos0, Vec* pos1, f32 r, int flag, Vec* nrm, int mask);
int blkPolySphereCkCore(cSat* sat, cSatBlock* blk, Vec* pos0, Vec* pos1, f32 r, int flag, Vec* nrm, int mask);
int blkPolyLineCk(cSat* sat, cSatBlock* blk, Vec* pos0, Vec* pos1, int flag, int mask, Vec* hit, u32* pn);
int blkPolyLineCkCore(cSat* sat, cSatBlock* blk, Vec* pos0, Vec* pos1, int flag, int mask, Vec* hit, u32* pn);
void polyBitSet(u32 no);
int polyBitCk(u32 no);
cSatFile* createSat(Vec* v, u32 attr, f32 h);
cSatFile* createBoxSat(Vec* v, u32 attr, f32 h);
static cSatFile* createFloorSat(Vec* v, u32 attr, f32 h);
void at_pos_calc(cModel* m, Vec* vec);
#if defined(RE4DC_SPHERE_WALK) && RE4DC_SPHERE_WALK
static void spwWallPair(u8* arr, u32 n, u32 size, Vec* p0, Vec* pos, f32 r, int flag, Vec* nrm, int mask);
#endif

// Model-vs-scenario collision for a character (its cAtariInfo, m_flag 0x100 = collision on):
// the rectangle form (m_flag bit1: 12 edge probes, checkRect) or the sphere form for the info
// and every extra info chained on m_pList (scrAtCheckSphere: walls then floor). 1 when the
// model was pushed.
int cSatMgr::check(cModel* m, int flag)
{
    cAtariInfo* info = &((cEm*) m)->atari;
    int ret = 0;

    if (!(info->m_flag & 0x100)) {
        return 0;
    }
    if (info->m_flag & 2) {
        ret = checkRect(m);
    } else {
        while (info->m_pList) {
            info = info->m_pList;
            if (scrAtCheckSphere(m, info, flag) != 0.0f) {
                ret = 1;
            }
        }
        if (scrAtCheckSphere(m, &((cEm*) m)->atari, flag) != 0.0f) {
            ret = 1;
        }
    }
    return ret;
}

// Rectangle collision: 12 horizontal probes from the model centre / its long axis to the box
// corners (m_radius x m_radius2) against the walls at pos.y + 300; each hit pushes the model
// back along the surface normal. 1 when any probe moved it.
int cSatMgr::checkRect(cModel* m)
{
    cAtariInfo* info = &((cEm*) m)->atari;
    Vec a;
    Vec b;
    int ret;

    a.x = 0.0f;
    a.y = 0.0f;
    a.z = info->m_radius2 * 0.9f;
    b.x = info->m_radius;
    b.y = 0.0f;
    b.z = info->m_radius2 * 0.9f;
    ret = atck(&a, &b, info, m, 0);
    a.x = 0.0f;
    a.y = 0.0f;
    a.z = 0.0f;
    b.x = info->m_radius;
    b.y = 0.0f;
    b.z = 0.0f;
    ret |= atck(&a, &b, info, m, 0);
    a.x = 0.0f;
    a.y = 0.0f;
    a.z = -info->m_radius2 * 0.9f;
    b.x = info->m_radius;
    b.y = 0.0f;
    b.z = -info->m_radius2 * 0.9f;
    ret |= atck(&a, &b, info, m, 0);
    a.x = 0.0f;
    a.y = 0.0f;
    a.z = info->m_radius2 * 0.9f;
    b.x = -info->m_radius;
    b.y = 0.0f;
    b.z = info->m_radius2 * 0.9f;
    ret |= atck(&a, &b, info, m, 0);
    a.x = 0.0f;
    a.y = 0.0f;
    a.z = 0.0f;
    b.x = -info->m_radius;
    b.y = 0.0f;
    b.z = 0.0f;
    ret |= atck(&a, &b, info, m, 0);
    a.x = 0.0f;
    a.y = 0.0f;
    a.z = -info->m_radius2 * 0.9f;
    b.x = -info->m_radius;
    b.y = 0.0f;
    b.z = -info->m_radius2 * 0.9f;
    ret |= atck(&a, &b, info, m, 0);
    a.x = info->m_radius * 0.9f;
    a.y = 0.0f;
    a.z = 0.0f;
    b.x = info->m_radius * 0.9f;
    b.y = 0.0f;
    b.z = info->m_radius2;
    ret |= atck(&a, &b, info, m, 0);
    a.x = 0.0f;
    a.y = 0.0f;
    a.z = 0.0f;
    b.x = 0.0f;
    b.y = 0.0f;
    b.z = info->m_radius2;
    ret |= atck(&a, &b, info, m, 0);
    a.x = -info->m_radius * 0.9f;
    a.y = 0.0f;
    a.z = 0.0f;
    b.x = -info->m_radius * 0.9f;
    b.y = 0.0f;
    b.z = info->m_radius2;
    ret |= atck(&a, &b, info, m, 0);
    a.x = info->m_radius * 0.9f;
    a.y = 0.0f;
    a.z = 0.0f;
    b.x = info->m_radius * 0.9f;
    b.y = 0.0f;
    b.z = -info->m_radius2;
    ret |= atck(&a, &b, info, m, 0);
    a.x = 0.0f;
    a.y = 0.0f;
    a.z = 0.0f;
    b.x = 0.0f;
    b.y = 0.0f;
    b.z = -info->m_radius2;
    ret |= atck(&a, &b, info, m, 0);
    a.x = -info->m_radius * 0.9f;
    a.y = 0.0f;
    a.z = 0.0f;
    b.x = -info->m_radius * 0.9f;
    b.y = 0.0f;
    b.z = -info->m_radius2;
    ret |= atck(&a, &b, info, m, 0);
    return ret;
}

// Airborne variant of check(): sphere collision without the floor snap (scrAtCheckSphereAir) for
// the info and its chained infos.
int cSatMgr::checkAir(cModel* m, int flag)
{
    cAtariInfo* info = &((cEm*) m)->atari;
    int ret = 0;

    if (info->m_flag & 0x100) {
        while (info->m_pList) {
            info = info->m_pList;
            if (scrAtCheckSphereAir(m, info, flag) != 0.0f) {
                ret = 1;
            }
        }
        if (scrAtCheckSphereAir(m, &((cEm*) m)->atari, flag) != 0.0f) {
            ret = 1;
        }
    }
    return ret;
}

// Segment a-b (model local, offset by the info position) against the scenario; the model is
// pushed back to the hit point. Returns 1 when it moved by a metre or more.
int atck(Vec* vec0, Vec* vec1, cAtariInfo* info, cModel* m, int flag)
{
    Vec v0;
    Vec v1;
    Vec hit;
    Vec nrm;
    Vec old;

    PSVECAdd(vec0, &info->m_offset, &v0);
    PSVECAdd(vec1, &info->m_offset, &v1);
    RotVector(&v0, &m->ang, &v0);
    RotVector(&v1, &m->ang, &v1);
    PSVECAdd(&v0, &m->pos, &v0);
    PSVECAdd(&v1, &m->pos, &v1);
    v0.y = v1.y = m->pos.y + 300.0f;
    if (SatMgr.hitCheck(&v0, &v1, &hit, &nrm, flag, 0)) {
        old = m->pos;
        PSVECSubtract(&hit, &v1, &v1);
        PSVECAdd(&m->pos, &v1, &m->pos);
        PSVECAdd(&m->pos, &nrm, &m->pos);
        if (fabsf(m->pos.x - old.x) >= 1.0f || fabsf(m->pos.z - old.z) >= 1.0f) {
            return 1;
        }
    }
    return 0;
}

// Sphere of the collision info against the scenario (walls, then the floor). Returns the
// distance the model was pushed.
f32 cSatMgr::scrAtCheckSphere(cModel* m, cAtariInfo* info, int flag)
{
    Vec pos;
    Vec oldPos;
    Vec newPos;
    Vec up;
    f32 mag;
    f32 floor;
    cModel* link;
    u32 c;

    info->getSpeedVector(m, &oldPos, &pos);
    m->Wall_norm.x = 0.0f;
    m->Wall_norm.y = 0.0f;
    m->Wall_norm.z = 0.0f;
    newPos = pos;
    wallAdjust(&m->Wall_norm, &oldPos, &newPos, info->m_radius, info->m_flag, flag);
    PSVECSubtract(&newPos, &pos, &pos);
    mag = PSVECMag(&pos);
    at_pos_calc(m, &pos);
    if (!(info->m_flag & 4)) {
        floor = getFloor(&m->pos, 600.0f, 100000.0f, (u32*) &m->pFloor_norm, flag);
        if (fabsf(floor - m->pos.y) < 1000.0f) {
            m->pos.y = floor;
        } else if (pG->shooting_mode == 0) {
            f32 x = (f32) ((int) m->pos.x / 100) * 100.0f;
            f32 y = (f32) ((int) m->pos.y / 100) * 100.0f;
            f32 z = (f32) ((int) m->pos.z / 100) * 100.0f;
            if (floor == -100000.0f) {
                pLog->warn(6, 1, "FLOOR LOST %.0f %.0f %.0f", x, y, z);
            } else {
                pLog->warn(4, 2, "FLOOR ERR %.0f %.0f %.0f", x, y, z);
            }
            up = m->pos;
            up.y += 50000.0f;
            c = pG->Frame_cnt & 0x3F;
            c <<= 2;
            if (pG->debug_mode != 0) {
                Draw_line3d(&m->pos, &up, 0xFFFF0000 | (c << 8) | c, 0);
            }
        }
    }
    link = info->m_pMod;
    if (link) {
        at_pos_calc(link, &pos);
        if (!(((cEm*) link)->atari.m_flag & 4)) {
            floor = getFloor(&link->pos, 600.0f, 100000.0f, (u32*) &link->pFloor_norm, flag);
            if (fabsf(floor - link->pos.y) < 1000.0f) {
                link->pos.y = floor;
            }
        }
    }
    if (pG->Debug_flg[2] & 0x20000000) {
        Draw_sphere(&newPos, info->m_radius, 0xA0A0A0A0, 1, 1);
    }
    return mag;
}

// Same for a model in the air: walls only, the height is kept.
f32 cSatMgr::scrAtCheckSphereAir(cModel* m, cAtariInfo* info, int flag)
{
    Vec pos;
    Vec oldPos;
    Vec newPos;
    Vec mpos;
    f32 mag = 0.0f;
    f32 y;
    cModel* link;

    if (!(info->m_flag & 0x100)) {
        return 0.0f;
    }
    {
        mpos = m->pos;
        info->getSpeedVector(m, &oldPos, &pos);
        m->Wall_norm.x = 0.0f;
        m->Wall_norm.y = 0.0f;
        m->Wall_norm.z = 0.0f;
        newPos = pos;
        wallAdjust(&m->Wall_norm, &oldPos, &newPos, info->m_radius, ((cEm*) m)->atari.m_flag, flag);
        PSVECSubtract(&newPos, &pos, &pos);
        mag = PSVECMag(&pos);
        at_pos_calc(m, &pos);
        y = m->pos.y;
        PSVECAdd(&m->pos, &pos, &m->pos);
        m->pos.y = y;
        link = info->m_pMod;
        if (link) {
            PSVECSubtract(&m->pos, &mpos, &mpos);
            PSVECAdd(&link->pos, &mpos, &link->pos);
        }
        if (pG->Debug_flg[2] & 0x20000000) {
            Draw_sphere(&newPos, info->m_radius, 0xA0A0A0A0, 1, 1);
        }
    }
    return mag;
}

// Sphere moving from oldPos to pos against the walls (flag bit0: the segment too); pos is
// pushed out, nrm receives the wall normal.
void cSatMgr::wallAdjust(Vec* nrm, Vec* oldPos, Vec* pos, f32 r, int flag, int mask)
{
    Vec hit;
    Vec tmp;
    Vec n;
    Vec d;
    Vec p0;
#if defined(RE4DC_LQ_MEMO) && RE4DC_LQ_MEMO
    Vec lqP;          // the first line query's pos (its oldPos stays: see below)
    int lqH;          // its answer
#if defined(RE4DC_DECISION_TRACE) && RE4DC_DECISION_TRACE
    LqmNotes lqN;
#endif
#endif

    if (flag & 1) {
#if defined(RE4DC_LQ_MEMO) && RE4DC_LQ_MEMO
        lqP = *pos;
#if defined(RE4DC_DECISION_TRACE) && RE4DC_DECISION_TRACE
        lqmNotesBegin(&lqN);
#endif
        lqH = hitCheck(oldPos, pos, &hit, &n, flag, mask);
#if defined(RE4DC_DECISION_TRACE) && RE4DC_DECISION_TRACE
        lqmNotesEnd(&lqN);
#endif
        if (lqH) {
#else
        if (hitCheck(oldPos, pos, &hit, &n, flag, mask)) {
#endif
            PSVECScale(&n, &tmp, r);
            PSVECAdd(&hit, &tmp, pos);
            if (nrm) {
                *nrm = n;
            }
        }
    }
    PSVECSubtract(pos, oldPos, &d);
    p0 = *oldPos;
    PSVECAdd(oldPos, &d, pos);
#if defined(RE4DC_SPHERE_WALK) && RE4DC_SPHERE_WALK
    if (pG->debug_mode != 0x14) {
        spwWallPair((u8*) pArray, nArray, size, &p0, pos, r, flag, nrm, mask);
    } else
#endif
    {
        polySphereCk(&p0, pos, r, flag | 0xA0, nrm, mask);
        polySphereCk(&p0, pos, r, flag | 0x80, nrm, mask);
    }
    if (flag & 1) {
#if defined(RE4DC_LQ_MEMO) && RE4DC_LQ_MEMO
        // GAME_LQ_MEMO: after a first query that hit nothing, with pos unmoved since (bit for bit), this query asks
        // the same question. oldPos is the callers' own local (scrAtCheckSphere, scrAtCheckSphereAir; t_atari
        // passes flag 0) that nothing here writes: hitCheck2 moves only pos1, and only on a hit; the sphere pass
        // gets the copy p0 and writes no piece, flag, mask or seCk. It hits nothing again and writes only SEck
        // (the same value) and hit (a dead local here).
        int lqSame = lqH == 0 && lqmVecSame(pos, &lqP);
#if defined(RE4DC_DECISION_TRACE) && RE4DC_DECISION_TRACE
        lqSame = lqSame && lqN.n != LQM_NOTE_OVER;
#endif
#if defined(RE4DC_FALLBACK_AUDIT29) && RE4DC_FALLBACK_AUDIT29
        if(!lqSame)re4dc::fa29::hit(re4dc::fa29::CollisionMemo);
#endif
#line 435
#if RE4DC_LQ_MEMO == 2
        const int lqR = hitCheck(oldPos, pos, &hit, &n, flag, mask);
        lqmPairCount(lqSame, lqSame && lqR != 0);
        if (lqR) {
#else
        if (lqSame) {
            ((SEckView*) &SEck)->v = seCk;
#if defined(RE4DC_DECISION_TRACE) && RE4DC_DECISION_TRACE
            lqmNotesReplay(&lqN);
#endif
        } else if (hitCheck(oldPos, pos, &hit, &n, flag, mask)) {
#endif
#else
        if (hitCheck(oldPos, pos, &hit, &n, flag, mask)) {
#endif
            PSVECScale(&n, &tmp, r);
            PSVECAdd(&hit, &tmp, pos);
            if (nrm) {
                *nrm = n;
            }
        }
    }
}

// Moves a sphere of radius `r` from oldPos to pos through the scenario: with flag bit0 a line
// hit is resolved first (pos pushed r along the normal), then the swept-sphere polygon check
// (polySphereCk) and a final line hit. The last contact normal is returned in *nrm (zero when
// nothing was hit). Used by rolling / thrown objects.
void cSatMgr::adjust(Vec* nrm, Vec* oldPos, Vec* pos, f32 r, int flag, int mask)
{
    Vec hit;
    Vec tmp;
    Vec n;
    Vec d;
    Vec p0;

    if (flag & 1) {
        if (hitCheck(oldPos, pos, &hit, &n, flag, mask)) {
            PSVECScale(&n, &tmp, r);
            PSVECAdd(&hit, &tmp, pos);
            if (nrm) {
                *nrm = n;
            }
        }
    }
    PSVECSubtract(pos, oldPos, &d);
    p0 = *oldPos;
    PSVECAdd(oldPos, &d, pos);
    polySphereCk(&p0, pos, r, flag, nrm, mask);
    if (flag & 1) {
        if (hitCheck(oldPos, pos, &hit, &n, flag, mask)) {
            PSVECScale(&n, &tmp, r);
            PSVECAdd(&hit, &tmp, pos);
            if (nrm) {
                *nrm = n;
            }
        }
    }
}

// Floor height under `pos`: casts from pos.y + up to pos.y - down against floor polygons
// (0x40) and returns the hit y with its attribute word in *attr; -100000 when nothing is below
// (0 when Debug_flg[1] 0x10000000 disables scenery).
f32 cSatMgr::getFloor(Vec* pos, f32 up, f32 down, u32* attr, int flag)
{
    Vec top;
    Vec bottom;
    Vec hit;
#if defined(RE4DC_EL_CENSUS) && RE4DC_EL_CENSUS
    ELC_RA(re4dc_elc_ra1);
#endif

    if (pG->Debug_flg[1] & 0x10000000) {
        return 0.0f;
    }
    top.x = pos->x;
    top.y = pos->y + up;
    top.z = pos->z;
    bottom.x = pos->x;
    bottom.y = pos->y - down;
    bottom.z = pos->z;
    if (hitCheck2(&top, &bottom, &hit, attr, 0x40, flag) == 0) {
        return -100000.0f;
    }
    return hit.y;
}

// cManager log hook: warnings through pLog.
void cSatMgr::log(const char* fmt, ...)
{
    va_list ap;

    va_start(ap, fmt);
    pLog->vwarn(0, 0, fmt, ap);
}

// Marks polygon `no` as already tested in this query (polyBit, 0x2000 polygons).
void polyBitSet(u32 no)
{
    polyBit[no >> 3] |= 1 << (no & 7);
}

// Non-zero when polygon `no` was already tested in this query.
int polyBitCk(u32 no)
{
    return polyBit[no >> 3] & (1 << (no & 7));
}

#if defined(RE4DC_COL_PREFETCH) && RE4DC_COL_PREFETCH
// GAME_COL_PREFETCH: cache hints for the collision walks (no stores, same answers).
#define COL_PREFETCH(p) do { if (p) __builtin_prefetch(p); } while (0)
// Polygon record of list entry i+4 and the vertex / normal of entry i+2 (its record was asked for two steps ago).
static inline void colPrefetchPoly(cSat* sat, u16* idx, u16* end)
{
    if (idx + 4 < end) {
        __builtin_prefetch(&sat->poly_p[idx[4]]);
    }
    if (idx + 2 < end) {
        AtPoly* p = &sat->poly_p[idx[2]];
        __builtin_prefetch(&sat->vtx[p->v[0]]);
        __builtin_prefetch(&sat->norm_p[p->n]);
    }
}
#else
#define COL_PREFETCH(p) ((void) 0)
#define colPrefetchPoly(sat, idx, end) ((void) 0)
#endif

// Segment (centre p, half direction dir, |dir| absDir) against the block's XZ box.
int cSatBlock::lineOverlap(Vec* p, Vec* dir, Vec* absDir)
{
    Vec d;
    Vec ad;

    d.x = (p->x - min.x) - m_Size.x * 0.5f;
    d.z = (p->z - min.z) - m_Size.z * 0.5f;
    ad.x = fabsf(d.x);
    ad.z = fabsf(d.z);
    if (ad.x > absDir->x + m_Size.x * 0.5f) {
        return 0;
    }
    if (ad.z > absDir->z + m_Size.z * 0.5f) {
        return 0;
    }
    if (fabsf(d.x * dir->z - d.z * dir->x) > (m_Size.x * absDir->z + m_Size.z * absDir->x) * 0.5f) {
        return 0;
    }
    return 1;
}

// XZ segment a-b against segment c-d.
static inline int lineCross(Vec* a, Vec* b, Vec* c, Vec* d)
{
    f32 denom = (b->x - a->x) * (d->z - c->z) - (b->z - a->z) * (d->x - c->x);
    f32 ax;
    f32 az;
    f32 t;
    f32 s;

    if (denom == 0.0f) {
        return 0;
    }
    ax = a->x - c->x;
    az = a->z - c->z;
    t = az * (d->x - c->x) - ax * (d->z - c->z);
    if (t < 0.0f) {
        if (denom >= 0.0f) {
            return 0;
        }
        if (t < denom) {
            return 0;
        }
    } else {
        if (denom < 0.0f) {
            return 0;
        }
        if (t > denom) {
            return 0;
        }
    }
    s = az * (b->x - a->x) - ax * (b->z - a->z);
    if (s < 0.0f) {
        if (denom >= 0.0f) {
            return 0;
        }
        if (s < denom) {
            return 0;
        }
    } else {
        if (denom < 0.0f) {
            return 0;
        }
        if (s > denom) {
            return 0;
        }
    }
    return 1;
}

// Sphere of radius r sweeping from a to b against the block's XZ box (expanded by r).
int cSatBlock::hitCheckSphere(Vec* pos0, Vec* pos1, f32 r)
{
    Vec c0;
    Vec c1;
    f32 x0 = min.x;
    f32 z0 = min.z;
    f32 cx = (pos0->x + pos1->x) * 0.5f;
    f32 cz = (pos0->z + pos1->z) * 0.5f;
    f32 hx = fabsf(pos0->x - pos1->x) * 0.5f + r;
    f32 hz = fabsf(pos0->z - pos1->z) * 0.5f + r;
    f32 x1;
    f32 z1;

    if (x0 + m_Size.x < cx - hx) {
        return 0;
    }
    if (x0 - m_Size.x > cx + hx) {
        return 0;
    }
    if (z0 + m_Size.z < cz - hz) {
        return 0;
    }
    if (z0 - m_Size.z > cz + hz) {
        return 0;
    }
    if (!(pos0->x < x0 - r || pos0->x > x0 + m_Size.x + r || pos0->z < z0 - r || pos0->z > z0 + m_Size.z + r)) {
        return 1;
    }
    if (!(pos1->x < x0 - r || pos1->x > x0 + m_Size.x + r || pos1->z < z0 - r || pos1->z > z0 + m_Size.z + r)) {
        return 1;
    }
    x1 = x0 + m_Size.x + r;
    z1 = z0 + m_Size.z + r;
    c0.x = x0;
    c0.y = 0.0f;
    c0.z = z0;
    c1.x = x1;
    c1.y = 0.0f;
    c1.z = z0;
    if (lineCross(pos0, pos1, &c0, &c1)) {
        return 1;
    }
    c0.z = c1.z = z1;
    if (lineCross(pos0, pos1, &c0, &c1)) {
        return 1;
    }
    c0.z = z0;
    c1.x = x0;
    if (lineCross(pos0, pos1, &c0, &c1)) {
        return 1;
    }
    c1.x = c0.x = x1;
    if (lineCross(pos0, pos1, &c0, &c1)) {
        return 1;
    }
    return 0;
}

// The room scenario collision manager (SatMgr): a pool of cSat pieces.
cSatMgr::cSatMgr() : cManager<cSat>(sizeof(cSat), 2)
{
    setName("cSatMgr");
}

// The effect collision manager (EatMgr): the pieces bullets, thrown objects and effects test.
cEatMgr::cEatMgr()
{
    setName("cEatMgr");
}

// Clears the 8 surface effect tables (AtEffInfo per attribute type): every effect pair set to
// "none" (0xD2), all types off.
void cEatMgr::initEffInfo()
{
    int i;

    for (i = 0; i < 8; i++) {
        memclr_asm(&effInfo[i], sizeof(AtEffInfo));
        effInfo[i].eff0[0] = 0xD2;
        effInfo[i].eff13[0] = 0xD2;
        effInfo[i].eff16[0] = 0xD2;
        effInfo[i].eff17[0] = 0xD2;
        effInfo[i].effGun[0] = 0xD2;
        effInfo[i].eff5[0] = 0xD2;
        effInfo[i].eff6[0] = 0xD2;
        effInfo[i].eff0D[0] = 0xD2;
        effOn[i] = 0;
    }
}

// Register the effect ids of one type; pairs left at the (0xD2, 1) default are not copied.
void cEatMgr::registEffInfo(int type, AtEffInfo* src)
{
    effOn[type] = 1;
    effInfo[type].flag = src->flag;
    if (src->eff0[0] != 0xD2 || src->eff0[1] == 1) {
        effInfo[type].eff0[0] = src->eff0[0];
        effInfo[type].eff0[1] = src->eff0[1];
    }
    if (src->eff13[0] != 0xD2 || src->eff0[1] == 1) {
        effInfo[type].eff13[0] = src->eff13[0];
        effInfo[type].eff13[1] = src->eff13[1];
    }
    if (src->eff16[0] != 0xD2 || src->eff0[1] == 1) {
        effInfo[type].eff16[0] = src->eff16[0];
        effInfo[type].eff16[1] = src->eff16[1];
    }
    if (src->eff17[0] != 0xD2 || src->eff0[1] == 1) {
        effInfo[type].eff17[0] = src->eff17[0];
        effInfo[type].eff17[1] = src->eff17[1];
    }
    if (src->effGun[0] != 0xD2 || src->eff0[1] == 1) {
        effInfo[type].effGun[0] = src->effGun[0];
        effInfo[type].effGun[1] = src->effGun[1];
    }
    if (src->eff5[0] != 0xD2 || src->eff0[1] == 1) {
        effInfo[type].eff5[0] = src->eff5[0];
        effInfo[type].eff5[1] = src->eff5[1];
    }
    if (src->eff6[0] != 0xD2 || src->eff0[1] == 1) {
        effInfo[type].eff6[0] = src->eff6[0];
        effInfo[type].eff6[1] = src->eff6[1];
    }
    if (src->eff0D[0] != 0xD2 || src->eff0[1] == 1) {
        effInfo[type].eff0D[0] = src->eff0D[0];
        effInfo[type].eff0D[1] = src->eff0D[1];
    }
}

// The surface effect table of attribute type `type` (bullet hit sparks, footsteps, splashes);
// NULL when the room registered none.
AtEffInfo* cEatMgr::getEffInfo(int type)
{
    if (effOn[type] != 0) {
        return &effInfo[type];
    }
    return 0;
}

// cManager log hook: warnings through pLog.
void cEatMgr::log(const char* fmt, ...)
{
    va_list ap;

    va_start(ap, fmt);
    pLog->vwarn(0, 0, fmt, ap);
}

// Creates a collision piece from SAT file data (a multi-SAT header selects entry `type`) placed
// at pos / rot; NULL when the pool is full.
cSat* cSatMgr::create(void* data, int flag, Vec* pos, Vec* rot, u8 type)
{
    cSat* sat = cManager<cSat>::create();
    cSatHeader* hdr = (cSatHeader*) data;

    if (!VALID_PTR(sat)) {
        return 0;
    }
    sat->x5C = 0;
    if (hdr->m_Version != 0xFF && (hdr->m_Version & 0x80)) {
        data = hdr->getSat(type);
    }
    sat->init((cSatFile*) data, pos ? pos : (Vec*) &vecZero, rot ? rot : (Vec*) &vecZero);
    return sat;
}

// Creates a collision piece from a quad: a floor slab (flag 0x200), a closed box of height h
// (flag 0x100) or open side walls (else), all with attribute `attr`; the built file is freed
// with the piece (m_Flag bit1).
cSat* cSatMgr::create(Vec* pos, Vec* rot, Vec* poly, int attr, int flag, f32 h)
{
    cSatFile* f;
    cSat* sat;

    if (flag & 0x200) {
        f = createFloorSat(poly, attr, h);
    } else if (flag & 0x100) {
        f = createBoxSat(poly, attr, h);
    } else {
        f = createSat(poly, attr, h);
    }
    if (f == 0) {
        return 0;
    }
    sat = create(f, flag, pos, rot, 0);
    if (sat) {
        sat->m_Flag |= 2;
    } else {
        Mem_free(f);
    }
    return sat;
}

#if defined(RE4DC_SPHERE_WALK) && RE4DC_SPHERE_WALK
// GAME_SPHERE_WALK (game30.mk; G, collision traversal; exact): polySphereCk's block walk (blkPolySphereCk:
// hitCheckSphere on every block of a chain, recursion into the overlapped nodes) in platform/spw_sh4.S with
// hitCheckSphere's float operations on the same operands. A leaf's polygon test can move the sphere's end and
// the recursive walk tests every later block against the moved end, so the kernel returns the overlapped
// leaves one at a time (in the recursive walk's order) and resumes with the ends read again. Each piece is
// walked first with the x and z rows of both ends (MTXMultVec's contract-off dataflow and operand roles, as
// GAME_LINE_PIECE; the walk reads nothing else); a piece without an overlapped leaf ends there (its polyBit
// clear and full transforms have no reader then). A node 16 chains deep walks its child chain recursively.
// wallAdjust's two calls (same p0, pos and r; the flag only picks the polygons a leaf tests) share one walk:
// the first records its leaves, and when it hit nothing (so pos, every lp and every piece are unchanged) the
// second runs them without a walk; a hit there moves lp, so that piece re-walks to the hit leaf with the
// unmoved end (the recorded walk) and goes on with the moved one, and the later pieces walk as usual.
// =2 (check build): the original loop runs first on copies of pos and nrm and the answers are compared, every
// kernel step is compared with a C walk from the same state that calls hitCheckSphere, a re-walk with the
// record, and the piece entry's x / z with PSMTXMultVec's ("SPW" lines).
struct SphereWalkQ {
    f32 (*m)[4];         // 0x00  the piece's inverse matrix (piece entry)
    Vec* p0;             // 0x04  the world ends (piece entry)
    Vec* p1;             // 0x08
    f32 r;               // 0x0C
    Vec* lo;             // 0x10  the piece-space ends (resume)
    Vec* lp;             // 0x14
    cSatBlock* cur;      // 0x18  the block to test next
    cSatBlock** sp;      // 0x1C  the continuation stack's top
    f32 box[4];          // 0x20  kernel scratch (the swept box)
    f32 kx[4];           // 0x30  the ends' x / z in use (lo.x, lo.z, lp.x, lp.z)
    cSatBlock* stk[16];  // 0x40  continuations
};
static_assert(__builtin_offsetof(SphereWalkQ, r) == 0x0C && __builtin_offsetof(SphereWalkQ, lo) == 0x10 &&
                  __builtin_offsetof(SphereWalkQ, cur) == 0x18 && __builtin_offsetof(SphereWalkQ, box) == 0x20 &&
                  __builtin_offsetof(SphereWalkQ, kx) == 0x30 && __builtin_offsetof(SphereWalkQ, stk) == 0x40 &&
                  sizeof(SphereWalkQ) == 0x80,
              "platform/spw_sh4.S reads these offsets");
static_assert(__builtin_offsetof(cSatBlock, min) == 0x00 && __builtin_offsetof(cSatBlock, m_Size) == 0x0C &&
                  __builtin_offsetof(cSatBlock, m_Flag) == 0x1E && __builtin_offsetof(cSatBlock, next) == 0x20 &&
                  __builtin_offsetof(cSatBlock, idx) == 0x24,
              "platform/spw_sh4.S reads these offsets");
extern "C" cSatBlock* re4dc_sphere_piece(SphereWalkQ* q, cSatBlock* blk);
extern "C" cSatBlock* re4dc_sphere_walk(SphereWalkQ* q);
// The entries one call met (leaves, or node | 1), with their pieces: wallAdjust's second call replays them.
#define SPW_REC_MAX 64
struct SpwRec {
    int n;  // -1: more than SPW_REC_MAX
    u32 piece[SPW_REC_MAX];
    cSatBlock* leaf[SPW_REC_MAX];
};
static SpwRec spwRec;
#if RE4DC_SPHERE_WALK == 2
extern "C" void re4dc_log(const char* fmt, ...);
static u32 spwCalls, spwPieces, spwLeaves, spwDeep, spwReplays, spwDiverge, spwXzMis, spwStepMis, spwRwMis, spwEndMis;
static int spwBits(const void* a, const void* b, int n)
{
    return __builtin_memcmp(a, b, n) != 0;
}
// A walk state: the block to test next and the continuations.
struct SpwState {
    cSatBlock* cur;
    int depth;
    cSatBlock* stk[16];
};
// The recursive walk's next step from state s, with hitCheckSphere: the next overlapped leaf, node | 1 at
// 16 chains deep, 0 at the end; s moves past it.
static cSatBlock* spwRefStep(SpwState* s, Vec* lo, Vec* lp, f32 r)
{
    cSatBlock* blk = s->cur;
    for (;;) {
        if (blk == 0) {
            if (s->depth == 0) {
                s->cur = 0;
                return 0;
            }
            blk = s->stk[--s->depth];
            continue;
        }
        cSatBlock* nx = blk->next;
        if (blk->hitCheckSphere(lo, lp, r)) {
            if (blk->m_Flag & 1) {
                if (s->depth == 16) {
                    s->cur = nx;
                    return (cSatBlock*) ((u32) blk | 1);
                }
                s->stk[s->depth++] = nx;
                blk = (cSatBlock*) blk->idx;
                continue;
            }
            s->cur = nx;
            return blk;
        }
        blk = nx;
    }
}
static void spwSave(SpwState* s, const SphereWalkQ* q)
{
    s->cur = q->cur;
    s->depth = q->sp - q->stk;
    for (int k = 0; k < s->depth; k++) {
        s->stk[k] = q->stk[k];
    }
}
// A kernel step (its answer `got` and the state it left in q) against the reference step from `from`.
static void spwCheckStep(const SpwState* from, cSatBlock* got, const SphereWalkQ* q, Vec* lo, Vec* lp)
{
    SpwState s = *from;
    cSatBlock* want = spwRefStep(&s, lo, lp, q->r);
    int bad = want != got;
    if (!bad && got) {
        const int depth = q->sp - q->stk;
        bad = s.cur != q->cur || s.depth != depth;
        for (int k = 0; !bad && k < depth; k++) {
            bad = s.stk[k] != q->stk[k];
        }
    }
    if (bad) {
        ++spwStepMis;
    }
    if (got) {
        if ((u32) got & 1) {
            ++spwDeep;
        } else {
            ++spwLeaves;
        }
    }
}
// The original piece loop (the reference), on the caller's copies of pos and nrm.
static int spwOrig(u8* arr, u32 n, u32 size, Vec* oldPos, Vec* pos, f32 r, int flag, Vec* nrm, int mask)
{
    int ret = 0;
    for (u32 i = 0; i < n; i++) {
        cSat* sat = (cSat*) (arr + size * i);
        if (sat->isAlive()) {
            Vec lo;
            Vec lp;
            memclr_asm(polyBit, (sat->polygon_num + 7) / 8);
            RE4DC_XM_LOAD(sat->imat);
            RE4DC_XM_POINT(sat->imat, oldPos, &lo);
            RE4DC_XM_POINT(sat->imat, pos, &lp);
            if (blkPolySphereCk(sat, sat->block_p, &lo, &lp, r, flag, nrm, mask)) {
                PSMTXMultVec(sat->mat, &lp, pos);
                if (nrm) {
                    PSMTXMultVecSR(sat->mat, nrm, nrm);
                }
                ret = 1;
            }
        }
    }
    return ret;
}
// The reference answer of one call (run before it) and its compare (after it).
struct SpwEnd {
    Vec pos;
    Vec nrm;
    int ret;
};
static void spwRefBegin(SpwEnd* e, u8* arr, u32 n, u32 size, Vec* oldPos, Vec* pos, f32 r, int flag, Vec* nrm, int mask)
{
    e->pos = *pos;
    if (nrm) {
        e->nrm = *nrm;
    }
    e->ret = spwOrig(arr, n, size, oldPos, &e->pos, r, flag, nrm ? &e->nrm : 0, mask);
}
static void spwRefEnd(const SpwEnd* e, int ret, Vec* pos, Vec* nrm)
{
    if (ret != e->ret || spwBits(pos, &e->pos, 12) || (nrm && spwBits(nrm, &e->nrm, 12))) {
        ++spwEndMis;
    }
    if (++spwCalls % 8192 == 0) {
        re4dc_log("SPW calls=%u pieces=%u leaves=%u deep=%u replay=%u diverge=%u xzmis=%u stepmis=%u rwmis=%u "
                  "endmis=%u\n", spwCalls, spwPieces, spwLeaves, spwDeep, spwReplays, spwDiverge, spwXzMis,
                  spwStepMis, spwRwMis, spwEndMis);
    }
}
#endif
// One entry of the walk: a leaf's polygons, or a deep node's child chain the recursive way. 1 on a hit.
static inline int spwLeaf(cSat* sat, cSatBlock* lf, Vec* lo, Vec* lp, f32 r, int flag, Vec* nrm, int mask)
{
    if ((u32) lf & 1) {
        cSatBlock* node = (cSatBlock*) ((u32) lf & ~1u);
#if defined(RE4DC_FALLBACK_AUDIT29) && RE4DC_FALLBACK_AUDIT29
        re4dc::fa29::hit(re4dc::fa29::CollisionSphereWalk);
#endif
#line 1007
        return blkPolySphereCk(sat, (cSatBlock*) node->idx, lo, lp, r, flag, nrm, mask) != 0;
    }
    return blkPolySphereCkCore(sat, lf, lo, lp, r, flag, nrm, mask) != 0;
}
// The rest of a piece's walk after entry `lf` (state in q, lo / lp set), running each entry. 1 on a hit.
static int spwFinish(SphereWalkQ* q, cSat* sat, Vec* lo, Vec* lp, int flag, Vec* nrm, int mask, SpwRec* rec, u32 i)
{
    int hit = 0;
    for (;;) {
#if RE4DC_SPHERE_WALK == 2
        SpwState from;
        spwSave(&from, q);
#endif
        cSatBlock* lf = re4dc_sphere_walk(q);
#if RE4DC_SPHERE_WALK == 2
        spwCheckStep(&from, lf, q, lo, lp);
#endif
        if (lf == 0) {
            return hit;
        }
        if (rec) {
            if (rec->n >= 0 && rec->n < SPW_REC_MAX) {
                rec->piece[rec->n] = i;
                rec->leaf[rec->n] = lf;
                rec->n++;
            } else {
                rec->n = -1;
            }
        }
        if (spwLeaf(sat, lf, lo, lp, q->r, flag, nrm, mask)) {
            hit = 1;
        }
    }
}
// polySphereCk's piece loop from piece i0 with the kernel walk; rec (when given) receives the entries met.
static int spwRun(u8* arr, u32 n, u32 size, u32 i0, Vec* oldPos, Vec* pos, f32 r, int flag, Vec* nrm, int mask,
                  SpwRec* rec)
{
    int ret = 0;
    SphereWalkQ q;

    q.p0 = oldPos;
    q.p1 = pos;
    q.r = r;
    if (rec) {
        rec->n = 0;
    }
    for (u32 i = i0; i < n; i++) {
        cSat* sat = (cSat*) (arr + size * i);
        if (!sat->isAlive()) {
            continue;
        }
        Vec lo;
        Vec lp;
        q.m = sat->imat;
        cSatBlock* lf = re4dc_sphere_piece(&q, sat->block_p);
#if RE4DC_SPHERE_WALK == 2
        {
            Vec ra;
            Vec rb;
            RE4DC_XM_LOAD(sat->imat);
            RE4DC_XM_POINT(sat->imat, oldPos, &ra);
            RE4DC_XM_POINT(sat->imat, pos, &rb);
            if (spwBits(&q.kx[0], &ra.x, 4) || spwBits(&q.kx[1], &ra.z, 4) || spwBits(&q.kx[2], &rb.x, 4) ||
                spwBits(&q.kx[3], &rb.z, 4)) {
                ++spwXzMis;
            }
            SpwState from;
            from.cur = sat->block_p;
            from.depth = 0;
            spwCheckStep(&from, lf, &q, &ra, &rb);
            ++spwPieces;
        }
#endif
        if (lf == 0) {
            continue;
        }
        memclr_asm(polyBit, (sat->polygon_num + 7) / 8);
        RE4DC_XM_LOAD(sat->imat);
        RE4DC_XM_POINT(sat->imat, oldPos, &lo);
        RE4DC_XM_POINT(sat->imat, pos, &lp);
        q.lo = &lo;
        q.lp = &lp;
        if (rec) {
            if (rec->n >= 0 && rec->n < SPW_REC_MAX) {
                rec->piece[rec->n] = i;
                rec->leaf[rec->n] = lf;
                rec->n++;
            } else {
                rec->n = -1;
            }
        }
        int hit = spwLeaf(sat, lf, &lo, &lp, r, flag, nrm, mask);
        if (spwFinish(&q, sat, &lo, &lp, flag, nrm, mask, rec, i)) {
            hit = 1;
        }
        if (hit) {
            PSMTXMultVec(sat->mat, &lp, pos);
            if (nrm) {
                PSMTXMultVecSR(sat->mat, nrm, nrm);
            }
            ret = 1;
        }
    }
    return ret;
}
// wallAdjust's second call after a first call that hit nothing, from that call's record (see above).
static int spwReplay(u8* arr, u32 n, u32 size, Vec* oldPos, Vec* pos, f32 r, int flag, Vec* nrm, int mask,
                     const SpwRec* rec)
{
    int k = 0;

#if RE4DC_SPHERE_WALK == 2
    ++spwReplays;
#endif
    while (k < rec->n) {
        const u32 i = rec->piece[k];
        cSat* sat = (cSat*) (arr + size * i);
        Vec lo;
        Vec lp;
        memclr_asm(polyBit, (sat->polygon_num + 7) / 8);
        RE4DC_XM_LOAD(sat->imat);
        RE4DC_XM_POINT(sat->imat, oldPos, &lo);
        RE4DC_XM_POINT(sat->imat, pos, &lp);
        const int k0 = k;
        for (; k < rec->n && rec->piece[k] == i; k++) {
            if (spwLeaf(sat, rec->leaf[k], &lo, &lp, r, flag, nrm, mask)) {
                SphereWalkQ q;
                Vec lp0;
#if RE4DC_SPHERE_WALK == 2
                ++spwDiverge;
#endif
                // the walk's state after entry k (the recorded walk: the unmoved end), then on with the moved one
                PSMTXMultVec(sat->imat, pos, &lp0);
                q.r = r;
                q.lo = &lo;
                q.lp = &lp0;
                q.cur = sat->block_p;
                q.sp = q.stk;
                for (int j = k0; j <= k; j++) {
                    cSatBlock* w = re4dc_sphere_walk(&q);
#if RE4DC_SPHERE_WALK == 2
                    if (w != rec->leaf[j]) {
                        ++spwRwMis;
                    }
#else
                    (void) w;
#endif
                }
                q.lp = &lp;
                spwFinish(&q, sat, &lo, &lp, flag, nrm, mask, 0, i);
                PSMTXMultVec(sat->mat, &lp, pos);
                if (nrm) {
                    PSMTXMultVecSR(sat->mat, nrm, nrm);
                }
                spwRun(arr, n, size, i + 1, oldPos, pos, r, flag, nrm, mask, 0);
                return 1;
            }
        }
    }
    return 0;
}
// wallAdjust's two polySphereCk calls (walls and slopes with flag 0x20, then walls) with one walk.
static void spwWallPair(u8* arr, u32 n, u32 size, Vec* p0, Vec* pos, f32 r, int flag, Vec* nrm, int mask)
{
#if RE4DC_SPHERE_WALK == 2
    SpwEnd e;
    spwRefBegin(&e, arr, n, size, p0, pos, r, flag | 0xA0, nrm, mask);
#endif
    const int r1 = spwRun(arr, n, size, 0, p0, pos, r, flag | 0xA0, nrm, mask, &spwRec);
#if RE4DC_SPHERE_WALK == 2
    spwRefEnd(&e, r1, pos, nrm);
    spwRefBegin(&e, arr, n, size, p0, pos, r, flag | 0x80, nrm, mask);
#endif
    int r2;
    if (r1 == 0 && spwRec.n >= 0) {
        r2 = spwReplay(arr, n, size, p0, pos, r, flag | 0x80, nrm, mask, &spwRec);
    } else {
        r2 = spwRun(arr, n, size, 0, p0, pos, r, flag | 0x80, nrm, mask, 0);
    }
#if RE4DC_SPHERE_WALK == 2
    spwRefEnd(&e, r2, pos, nrm);
#else
    (void) r2;
#endif
}
#endif

// Sphere of radius r moving from oldPos to pos against every active piece; pos is pushed out
// of the polygons, nrm (when given) receives the last hit normal. Returns 1 on a hit.
int cSatMgr::polySphereCk(Vec* oldPos, Vec* pos, f32 r, int flag, Vec* nrm, int mask)
{
    int ret;
    u32 idx = 0;
    u32 i;

    if (pG->debug_mode == 0x14) {
        Vec d;
        PSVECSubtract(oldPos, pos, &d);
        idx = (u32) (PSVECMag(&d) / 1000.0f);
        if (idx > 0x14) {
            idx = 0x13;
        }
        g_at2_total++;
        g_at2_cnt[idx]++;
        PPCMtpmc1(0);
        PPCMtpmc2(0);
        PPCMtpmc3(0);
        PPCMtpmc4(0);
        PPCMtmmcr1(0x78000000);
        PPCMtmmcr0(0x42);
    }
    ret = 0;
#if defined(RE4DC_SPHERE_WALK) && RE4DC_SPHERE_WALK
    (void) i;
    {
#if RE4DC_SPHERE_WALK == 2
        SpwEnd e;
        spwRefBegin(&e, (u8*) pArray, nArray, size, oldPos, pos, r, flag, nrm, mask);
#endif
        ret = spwRun((u8*) pArray, nArray, size, 0, oldPos, pos, r, flag, nrm, mask, 0);
#if RE4DC_SPHERE_WALK == 2
        spwRefEnd(&e, ret, pos, nrm);
#endif
    }
#else
    for (i = 0; i < nArray; i++) {
        cSat* sat = (cSat*) ((u8*) pArray + size * i);
        if (sat->isAlive()) {
            Vec lo;
            Vec lp;
            cSatBlock* blk = sat->block_p;
            memclr_asm(polyBit, (sat->polygon_num + 7) / 8);
            RE4DC_XM_LOAD(sat->imat);
            RE4DC_XM_POINT(sat->imat, oldPos, &lo);
            RE4DC_XM_POINT(sat->imat, pos, &lp);
            if (blkPolySphereCk(sat, blk, &lo, &lp, r, flag, nrm, mask)) {
                PSMTXMultVec(sat->mat, &lp, pos);
                if (nrm) {
                    PSMTXMultVecSR(sat->mat, nrm, nrm);
                }
                ret = 1;
            }
        }
    }
#endif
    if (pG->debug_mode == 0x14) {
        PPCMtmmcr0(0);
        PPCMtmmcr1(0);
        g_at2_cyc[idx] += PPCMfpmc1() / 1000;
        g_at2_total_cyc += PPCMfpmc1() / 1000;
    }
    return ret;
}

// Swept sphere through the block chain: recurses into child blocks (m_Flag bit0) whose box the
// sweep overlaps, tests the polygons of leaf blocks; pos1 is pushed out of every hit polygon.
// 1 when anything was hit.
int blkPolySphereCk(cSat* sat, cSatBlock* blk, Vec* pos0, Vec* pos1, f32 r, int flag, Vec* nrm, int mask)
{
    int ret = 0;
    int hit;

    while (blk) {
        COL_PREFETCH(blk->next);
        if (blk->hitCheckSphere(pos0, pos1, r)) {
            if (blk->m_Flag & 1) {
                hit = blkPolySphereCk(sat, (cSatBlock*) blk->idx, pos0, pos1, r, flag, nrm, mask);
            } else {
                hit = blkPolySphereCkCore(sat, blk, pos0, pos1, r, flag, nrm, mask);
            }
            if (hit) {
                ret = 1;
            }
        }
        blk = blk->next;
    }
    return ret;
}

// Sphere test of one block's polygons: floors + slopes (flag 0x40), walls (flag 0x80) or all;
// every polygon is tested once per query (polyBit); a hit adjusts pos1 and returns the polygon's
// normal; Debug_flg[0] 0x08000000 highlights hit polygons.
int blkPolySphereCkCore(cSat* sat, cSatBlock* blk, Vec* pos0, Vec* pos1, f32 r, int flag, Vec* nrm, int mask)
{
    int ret = 0;
    int start;
    int end;
    int i;
    u16* idx;

    if (flag & 0x40) {
        start = 0;
        end = blk->m_nFloor + blk->m_nSlope;
    } else if (flag & 0x80) {
        start = blk->m_nFloor + blk->m_nSlope;
        end = start + blk->m_nWall;
    } else {
        start = 0;
        end = blk->m_nFloor + blk->m_nSlope + blk->m_nWall;
    }
    idx = &blk->idx[start];
#if defined(RE4DC_COL_PREFETCH) && RE4DC_COL_PREFETCH
    u16* idxEnd = &blk->idx[end];
    if (start < end) {
        for (int k = 0; k < 4 && start + k < end; k++) {
            __builtin_prefetch(&sat->poly_p[idx[k]]);
        }
    }
#endif
    for (i = start; i < end; i++, idx++) {
        colPrefetchPoly(sat, idx, idxEnd);
        AtPoly* poly = &sat->poly_p[*idx];
        if (polyBitCk(*idx)) {
            continue;
        }
        polyBitSet(*idx);
        if (At_poly_sphere_ck((AtPolyData*) sat, poly, pos0, pos1, r, flag, mask)) {
            ret = 1;
            if (nrm) {
                *nrm = sat->norm_p[sat->poly_p[*idx].n];
            }
            if (pG->Debug_flg[0] & 0x08000000) {
                sat->disp(*idx, 0x40FF0000, 1);
            }
        }
    }
    return ret;
}

// Line pos0 -> pos1 against every live piece: the nearest hit in *hit, its world normal in
// *nrm; returns the hit polygon's attribute word (0 = no hit). flag selects floors / walls,
// `mask` attribute bits to ignore.
#if defined(RE4DC_DECISION_TRACE) && RE4DC_DECISION_TRACE == 2
extern "C" int re4dc_dt_window(void);
extern "C" void re4dc_log(const char* fmt, ...);
#endif
int cSatMgr::hitCheck(Vec* pos0, Vec* pos1, Vec* hit, Vec* nrm, int flag, int mask)
{
    u32 pn;
    int ret;
#if defined(RE4DC_EL_CENSUS) && RE4DC_EL_CENSUS
    ELC_RA(re4dc_elc_ra1);
#endif

#if defined(RE4DC_DECISION_TRACE) && RE4DC_DECISION_TRACE == 2
    if (re4dc_dt_window() >= 0) {
        re4dc_log("LQH ra=%08x\n", (u32) __builtin_return_address(0));
    }
#endif
    ret = hitCheck2(pos0, pos1, hit, &pn, flag, mask);
    if (nrm && ret) {
        PSMTXMultVecSR(pBypassAt->mat, (Vec*) pn, nrm);
    }
    return ret;
}

#if defined(RE4DC_LINE_WALK) && RE4DC_LINE_WALK
// GAME_LINE_WALK (game30.mk; G, collision traversal; exact): blkPolyLineCk's block walk (lineOverlap on
// every block of a chain, recursion into the overlapped nodes) in platform/lnw_sh4.S: an explicit stack and
// lineOverlap's float operations on the same operands. The overlapped leaves come out in the recursive
// walk's order and run blkPolyLineCkCore in that order (the walk reads no state the leaves write).
// hitCheck2 walks each piece first, and a piece without an overlapped leaf ends there (its polyBit clear
// and hit transform have no reader then). A walk more than 16 chains deep or with more than 64 leaves
// takes the recursive walk. =2 (check build): the recursive walk also collects its leaves and the lists
// are compared ("LNW" lines).
struct LineWalkQ {
    f32 mx;         // 0x00  mid.x
    f32 mz;         // 0x04  mid.z
    f32 dx;         // 0x08  dir.x
    f32 dz;         // 0x0C  dir.z
    f32 ax;         // 0x10  |dir.x|
    f32 az;         // 0x14  |dir.z|
};
static_assert(__builtin_offsetof(cSatBlock, m_Flag) == 0x1E && __builtin_offsetof(cSatBlock, next) == 0x20 &&
                  __builtin_offsetof(cSatBlock, idx) == 0x24,
              "platform/lnw_sh4.S reads these offsets");
extern "C" int re4dc_line_walk(const LineWalkQ* q, cSatBlock* blk, cSatBlock** out, int max);
#define LNW_MAX 64
#if defined(RE4DC_LINE_WALK_PF) && RE4DC_LINE_WALK_PF
// GAME_LINE_WALK_PF (game30.mk; G, collision traversal; exact; needs GAME_LINE_WALK=1): the walk and piece
// entry of platform/lnw2_sh4.S, lnw_sh4.S's with three prefetches added (the next block's `next` line, an
// overlapped node's child's `next` line, the root block's lines at a piece's start); nothing else changes.
// =2 (check build): lnw_sh4.S's entries also run and the leaves (and the piece's ends) are compared ("LWP").
extern "C" int re4dc_line_walk2(const LineWalkQ* q, cSatBlock* blk, cSatBlock** out, int max);
#if RE4DC_LINE_WALK_PF == 2
extern "C" void re4dc_log(const char* fmt, ...);
static u32 lwpCalls, lwpLeaves, lwpMis;
static void lwpCheck(int nl, const cSatBlock* const* leaf, int nr, const cSatBlock* const* ref, int endsMis)
{
    int m = endsMis || nr != nl;
    for (int i = 0; !m && i < nl; i++) {
        m = ref[i] != leaf[i];
    }
    lwpMis += m;
    if (nl > 0) {
        lwpLeaves += nl;
    }
    if (++lwpCalls % 8192 == 0) {
        re4dc_log("LWP calls=%u leaves=%u mismatch=%u\n", lwpCalls, lwpLeaves, lwpMis);
    }
}
#endif
#endif
#if RE4DC_LINE_WALK == 2
extern "C" void re4dc_log(const char* fmt, ...);
static u32 lnwCalls, lnwLeaves, lnwMis, lnwFull;
// The recursive walk's leaves in its order (leaves past `max` are counted, not stored).
static int lnwRef(cSatBlock* blk, Vec* mid, Vec* dir, Vec* adir, cSatBlock** out, int n, int max)
{
    for (; blk; blk = blk->next) {
        if (blk->lineOverlap(mid, dir, adir)) {
            if (blk->m_Flag & 1) {
                n = lnwRef((cSatBlock*) blk->idx, mid, dir, adir, out, n, max);
            } else {
                if (n < max) {
                    out[n] = blk;
                }
                n++;
            }
        }
    }
    return n;
}
#endif
// The overlapped leaves of the chain at blk for the segment (mid, dir, |dir|) as blkPolyLineCk computes
// them; -1: take the recursive walk.
static int lineWalkLeaves(cSatBlock* blk, Vec* mid, Vec* dir, Vec* adir, cSatBlock** leaf)
{
    LineWalkQ q;

    q.mx = mid->x;
    q.mz = mid->z;
    q.dx = dir->x;
    q.dz = dir->z;
    q.ax = adir->x;
    q.az = adir->z;
#if defined(RE4DC_LINE_WALK_PF) && RE4DC_LINE_WALK_PF
    const int nl = re4dc_line_walk2(&q, blk, leaf, LNW_MAX);
#if RE4DC_LINE_WALK_PF == 2
    {
        cSatBlock* ref[LNW_MAX];
        const int nr = re4dc_line_walk(&q, blk, ref, LNW_MAX);
        lwpCheck(nl, leaf, nr, ref, 0);
    }
#endif
#else
    const int nl = re4dc_line_walk(&q, blk, leaf, LNW_MAX);
#endif
#if RE4DC_LINE_WALK == 2
    {
        cSatBlock* ref[LNW_MAX];
        const int nr = lnwRef(blk, mid, dir, adir, ref, 0, LNW_MAX);
        if (nl < 0) {
            ++lnwFull;
        } else if (nr != nl) {
            ++lnwMis;
        } else {
            for (int i = 0; i < nl; i++) {
                if (ref[i] != leaf[i]) {
                    ++lnwMis;
                    break;
                }
            }
            lnwLeaves += nl;
        }
        if (++lnwCalls % 8192 == 0) {
            re4dc_log("LNW calls=%u leaves=%u mismatch=%u full=%u\n", lnwCalls, lnwLeaves, lnwMis, lnwFull);
        }
    }
#endif
#if defined(RE4DC_FALLBACK_AUDIT29) && RE4DC_FALLBACK_AUDIT29
    if(nl<0)re4dc::fa29::hit(re4dc::fa29::CollisionLineWalk);
#endif
#line 1478
    return nl;
}
// hitCheck2's walk of one piece: mid, dir and |dir| as blkPolyLineCk computes them (its y components are
// zeroed there and lineOverlap reads x and z only; its new_line_check is a constant 1).
static int lineWalkPiece(cSatBlock* blk, Vec* pos0, Vec* pos1, cSatBlock** leaf)
{
    Vec mid;
    Vec dir;
    Vec adir;

    PSVECAdd(pos0, pos1, &mid);
    PSVECScale(&mid, &mid, 0.5f);
    PSVECSubtract(pos0, &mid, &dir);
    adir.x = fabsf(dir.x);
    adir.y = 0.0f;
    adir.z = fabsf(dir.z);
    dir.y = 0.0f;
    mid.y = 0.0f;
    return lineWalkLeaves(blk, &mid, &dir, &adir, leaf);
}
#if defined(RE4DC_LINE_PIECE) && RE4DC_LINE_PIECE
// GAME_LINE_PIECE (game30.mk; G, collision traversal; exact): hitCheck2's per-piece segment transform and
// walk setup in platform/lnw_sh4.S (re4dc_line_piece): the x and z rows of both ends with MTXMultVec's
// contract-off dataflow and operand roles, mid / dir / |dir| as hitCheck2 compiles lineWalkPiece, then the
// walk. Only a piece with an overlapped leaf (or a walk too deep for the kernel) transforms both ends in full,
// as before. =2 (check build): the kernel's ends and leaves are compared with PSMTXMultVec's and
// lineWalkPiece's ("LNP" lines).
struct LinePieceQ {
    f32 (*m)[4];    // 0x00  the piece's inverse matrix
    Vec* p0;        // 0x04  the world segment
    Vec* p1;        // 0x08
    f32 lax;        // 0x0C  written by the kernel: the ends' x and z
    f32 laz;        // 0x10
    f32 lbx;        // 0x14
    f32 lbz;        // 0x18
};
static_assert(__builtin_offsetof(LinePieceQ, lax) == 0x0C && __builtin_offsetof(LinePieceQ, lbz) == 0x18,
              "platform/lnw_sh4.S writes these offsets");
extern "C" int re4dc_line_piece(LinePieceQ* q, cSatBlock* blk, cSatBlock** out, int max);
#if defined(RE4DC_LINE_WALK_PF) && RE4DC_LINE_WALK_PF
extern "C" int re4dc_line_piece2(LinePieceQ* q, cSatBlock* blk, cSatBlock** out, int max);
#endif
#if RE4DC_LINE_PIECE == 2
extern "C" void re4dc_log(const char* fmt, ...);
static u32 lnpCalls, lnpMis, lnpLeafMis;
static int lnpBits(const f32* a, const f32* b)
{
    u32 x;
    u32 y;
    __builtin_memcpy(&x, a, 4);
    __builtin_memcpy(&y, b, 4);
    return x != y;
}
#endif
#if defined(RE4DC_LINE_YROW) && RE4DC_LINE_YROW
// GAME_LINE_YROW (game30.mk; G, line queries; exact; needs GAME_LINE_PIECE=1): a piece with an overlapped
// leaf took three full PSMTXMultVec (both ends and the current end). re4dc_line_piece has already written
// both ends' x and z rows (MTXMultVec's contract-off dataflow, checked by LNP), so only the y rows are
// computed, with MTXMultVec's expression (m13 + (m12 z + (m10 x + m11 y))). The current end equals pos1
// bit for bit until a hit is taken (cur = *pos1 at entry, both written only there), so its transform is
// lb's; and the hit test's re-transform of cur (unchanged since) is the transform taken before the leaf
// tests. =2 (check build): every such vector compared with PSMTXMultVec ("LYR" lines).
static inline f32 lyrRow1(f32 (*m)[4], const Vec* p)
{
    return m[1][3] + ((m[1][2] * p->z) + ((m[1][0] * p->x) + (m[1][1] * p->y)));
}
#if RE4DC_LINE_YROW == 2
extern "C" void re4dc_log(const char* fmt, ...);
static u32 lyrCalls, lyrMis, lyrCurMis, lyrTmpMis;
#endif
#endif
static int linePieceWalk(LinePieceQ* q, cSatBlock* blk, cSatBlock** leaf)
{
#if defined(RE4DC_LINE_WALK_PF) && RE4DC_LINE_WALK_PF
    const int nl = re4dc_line_piece2(q, blk, leaf, LNW_MAX);
#if RE4DC_LINE_WALK_PF == 2
    {
        LinePieceQ c = *q;
        cSatBlock* ref[LNW_MAX];
        const int nr = re4dc_line_piece(&c, blk, ref, LNW_MAX);
        lwpCheck(nl, leaf, nr, ref,
                 __builtin_memcmp(&c.lax, &q->lax, 4) || __builtin_memcmp(&c.laz, &q->laz, 4) ||
                     __builtin_memcmp(&c.lbx, &q->lbx, 4) || __builtin_memcmp(&c.lbz, &q->lbz, 4));
    }
#endif
#else
    const int nl = re4dc_line_piece(q, blk, leaf, LNW_MAX);
#endif
#if RE4DC_LINE_PIECE == 2
    {
        Vec ra;
        Vec rb;
        cSatBlock* ref[LNW_MAX];
        RE4DC_XM_LOAD(q->m);
        RE4DC_XM_POINT(q->m, q->p0, &ra);
        RE4DC_XM_POINT(q->m, q->p1, &rb);
        if (lnpBits(&q->lax, &ra.x) || lnpBits(&q->laz, &ra.z) || lnpBits(&q->lbx, &rb.x) || lnpBits(&q->lbz, &rb.z)) {
            ++lnpMis;
        }
        const int nr = lineWalkPiece(blk, &ra, &rb, ref);
        if (nr != nl) {
            ++lnpLeafMis;
        } else {
            for (int i = 0; i < nl; i++) {
                if (ref[i] != leaf[i]) {
                    ++lnpLeafMis;
                    break;
                }
            }
        }
        if (++lnpCalls % 8192 == 0) {
            re4dc_log("LNP calls=%u mismatch=%u leafmis=%u\n", lnpCalls, lnpMis, lnpLeafMis);
        }
    }
#endif
#if defined(RE4DC_FALLBACK_AUDIT29) && RE4DC_FALLBACK_AUDIT29
    if(nl<0)re4dc::fa29::hit(re4dc::fa29::CollisionLineWalk);
#endif
#line 1593
    return nl;
}
#endif
#if defined(RE4DC_LINE_RESUME) && RE4DC_LINE_RESUME
#include "line_resume29.h"

// Consume one entry already returned at piece admission, then resume at the
// exact next block. A deep node's child chain has not been touched yet; the
// existing polygon walk handles it with this piece's current polyBit/hit state.
static int lineResume29Run(cSat* sat, LineResume29* q, int kind, cSatBlock* step, Vec* a, Vec* b,
                           int flag, int mask, Vec* hit, u32* pn)
{
    int ret = 0;
    do {
        int r;
        if (kind == 1) {
            r = blkPolyLineCkCore(sat, step, a, b, flag, mask, hit, pn);
        } else {
#if defined(RE4DC_FALLBACK_AUDIT29) && RE4DC_FALLBACK_AUDIT29
            re4dc::fa29::hit(re4dc::fa29::CollisionLineWalk);
#endif
            r = blkPolyLineCk(sat, (cSatBlock*) step->idx, a, b, flag, mask, hit, pn);
        }
        if (r) {
            ret = r;
        }
        kind = lineResume29Next(q, &step);
    } while (kind);
    return ret;
}
#endif
#endif

// Segment a-b against every active piece. The nearest hit goes to hit (world) and `attr`
// receives the address of the hit polygon's normal in the piece's space; b is moved onto the
// piece's grid (mat * inv * b). Returns the attribute word of the hit polygon or 0.
#if defined(RE4DC_DECISION_TRACE) && RE4DC_DECISION_TRACE
// GAME_DECISION_TRACE (test builds): every line query's answer (attribute word and winning piece)
// and, separately, its hit point bits (logic_trace.cpp).
extern "C" unsigned re4dc_dt_note(unsigned kind, unsigned a, unsigned b);
#if RE4DC_DECISION_TRACE == 2
extern "C" int re4dc_dt_window(void);
extern "C" void re4dc_log(const char* fmt, ...);
#endif
#endif
int cSatMgr::hitCheck2(Vec* pos0, Vec* pos1, Vec* hit, u32* attr, int flag, int mask)
{
#if defined(RE4DC_DECISION_TRACE) && RE4DC_DECISION_TRACE
    u32 dtWin = 0xFFFFFFFF;
#endif
    Vec cur;
    Vec la;
    Vec lb;
    Vec lcur;
    Vec tmp;
    u32 pn;
    int ret = 0;
    u32 i;

#if defined(RE4DC_EL_CENSUS) && RE4DC_EL_CENSUS
    elcQueryBegin(this, pos0, pos1, flag, mask, seCk, (u32) __builtin_return_address(0));
#endif
    // stored through a struct view: keeps the `cur = *b` loads below the store like the original
    ((SEckView*) &SEck)->v = seCk;
    cur = *pos1;
#if defined(RE4DC_LINE_PIECE) && RE4DC_LINE_PIECE
    LinePieceQ pq;
    pq.p0 = pos0;
    pq.p1 = pos1;
#if defined(RE4DC_LINE_YROW) && RE4DC_LINE_YROW
    int curP1 = 1;
    Vec lcur0;
#endif
    u8* satp = (u8*) pArray;
    const u32 satSize = size;
    for (i = 0; i < nArray; i++, satp += satSize) {
        cSat* sat = (cSat*) satp;
#else
    for (i = 0; i < nArray; i++) {
        cSat* sat = (cSat*) ((u8*) pArray + size * i);
#endif
        if (sat->isAlive()) {
            cSatBlock* blk = sat->block_p;
            int r;
#if defined(RE4DC_EL_CENSUS) && RE4DC_EL_CENSUS
            ELC_W(ELC_W_ALIVE, 1);
#endif
#if defined(RE4DC_LINE_WALK) && RE4DC_LINE_WALK
#if defined(RE4DC_LINE_RESUME) && RE4DC_LINE_RESUME
            LineResume29 walk;
            cSatBlock* first;
            int firstKind;
#if defined(RE4DC_LINE_PIECE) && RE4DC_LINE_PIECE
            // The piece kernel's x/z rows suffice for early rejection. Keep
            // YROW's full-end and current-end work below for admitted pieces.
            Vec qa;
            Vec qb;
            pq.m = sat->imat;
            lineResume29XZ(sat->imat, pos0, &pq.lax, &pq.laz);
            lineResume29XZ(sat->imat, pos1, &pq.lbx, &pq.lbz);
            qa.x = pq.lax;
            qa.y = 0.0f;
            qa.z = pq.laz;
            qb.x = pq.lbx;
            qb.y = 0.0f;
            qb.z = pq.lbz;
            lineResume29Begin(&walk, blk, &qa, &qb);
#else
            RE4DC_XM_LOAD(sat->imat);
            RE4DC_XM_POINT(sat->imat, pos0, &la);
            RE4DC_XM_POINT(sat->imat, pos1, &lb);
            lineResume29Begin(&walk, blk, &la, &lb);
#endif
            firstKind = lineResume29Next(&walk, &first);
            if (firstKind == 0) {
                continue;
            }
#if defined(RE4DC_EL_CENSUS) && RE4DC_EL_CENSUS
            ELC_W(ELC_W_WALKED, 1);
#endif
#if defined(RE4DC_LINE_PIECE) && RE4DC_LINE_PIECE
#if defined(RE4DC_LINE_YROW) && RE4DC_LINE_YROW
            la.x = pq.lax;
            la.y = lyrRow1(sat->imat, pos0);
            la.z = pq.laz;
            lb.x = pq.lbx;
            lb.y = lyrRow1(sat->imat, pos1);
            lb.z = pq.lbz;
#if RE4DC_LINE_YROW == 2
            {
                Vec ra;
                Vec rb;
                RE4DC_XM_LOAD(sat->imat);
                RE4DC_XM_POINT(sat->imat, pos0, &ra);
                RE4DC_XM_POINT(sat->imat, pos1, &rb);
                if (__builtin_memcmp(&ra, &la, 12) != 0 || __builtin_memcmp(&rb, &lb, 12) != 0) {
                    ++lyrMis;
                }
                if (++lyrCalls % 8192 == 0) {
                    re4dc_log("LYR calls=%u mismatch=%u curmis=%u tmpmis=%u\n", lyrCalls, lyrMis, lyrCurMis, lyrTmpMis);
                }
            }
#endif
#else
            RE4DC_XM_LOAD(sat->imat);
            RE4DC_XM_POINT(sat->imat, pos0, &la);
            RE4DC_XM_POINT(sat->imat, pos1, &lb);
#endif
#endif
#else
#if defined(RE4DC_LINE_PIECE) && RE4DC_LINE_PIECE
            cSatBlock* leaf[LNW_MAX];
            pq.m = sat->imat;
            const int nl = linePieceWalk(&pq, blk, leaf);
            if (nl == 0) {
                continue;
            }
#if defined(RE4DC_EL_CENSUS) && RE4DC_EL_CENSUS
            ELC_W(ELC_W_WALKED, 1);
            ELC_W(ELC_W_LEAVES, nl > 0 ? nl : 0);
#endif
#if defined(RE4DC_LINE_YROW) && RE4DC_LINE_YROW
            la.x = pq.lax;
            la.y = lyrRow1(sat->imat, pos0);
            la.z = pq.laz;
            lb.x = pq.lbx;
            lb.y = lyrRow1(sat->imat, pos1);
            lb.z = pq.lbz;
#if RE4DC_LINE_YROW == 2
            {
                Vec ra;
                Vec rb;
                RE4DC_XM_LOAD(sat->imat);
                RE4DC_XM_POINT(sat->imat, pos0, &ra);
                RE4DC_XM_POINT(sat->imat, pos1, &rb);
                if (__builtin_memcmp(&ra, &la, 12) != 0 || __builtin_memcmp(&rb, &lb, 12) != 0) {
                    ++lyrMis;
                }
                if (++lyrCalls % 8192 == 0) {
                    re4dc_log("LYR calls=%u mismatch=%u curmis=%u tmpmis=%u\n", lyrCalls, lyrMis, lyrCurMis, lyrTmpMis);
                }
            }
#endif
#else
            RE4DC_XM_LOAD(sat->imat);
            RE4DC_XM_POINT(sat->imat, pos0, &la);
            RE4DC_XM_POINT(sat->imat, pos1, &lb);
#endif
#else
            RE4DC_XM_LOAD(sat->imat);
            RE4DC_XM_POINT(sat->imat, pos0, &la);
            RE4DC_XM_POINT(sat->imat, pos1, &lb);
            cSatBlock* leaf[LNW_MAX];
            const int nl = lineWalkPiece(blk, &la, &lb, leaf);
            if (nl == 0) {
                continue;
            }
#endif
#endif
            memclr_asm(polyBit, (sat->polygon_num >> 3) + 1);
#if defined(RE4DC_LINE_PIECE) && RE4DC_LINE_PIECE && defined(RE4DC_LINE_YROW) && RE4DC_LINE_YROW
            if (curP1) {
                lcur = lb;
            } else {
                PSMTXMultVec(sat->imat, &cur, &lcur);
            }
            lcur0 = lcur;
#if RE4DC_LINE_YROW == 2
            {
                Vec rc;
                PSMTXMultVec(sat->imat, &cur, &rc);
                if (__builtin_memcmp(&rc, &lcur, 12) != 0) {
                    ++lyrCurMis;
                }
            }
#endif
#else
            PSMTXMultVec(sat->imat, &cur, &lcur);
#endif
#if defined(RE4DC_LINE_RESUME) && RE4DC_LINE_RESUME
            r = lineResume29Run(sat, &walk, firstKind, first, &la, &lb, flag, mask, &lcur, &pn);
#else
            if (nl > 0) {
                r = 0;
                for (int k = 0; k < nl; k++) {
                    const int rk = blkPolyLineCkCore(sat, leaf[k], &la, &lb, flag, mask, &lcur, &pn);
                    if (rk) {
                        r = rk;
                    }
                }
            } else {
                r = blkPolyLineCk(sat, blk, &la, &lb, flag, mask, &lcur, &pn);
            }
#endif
#else
            memclr_asm(polyBit, (sat->polygon_num >> 3) + 1);
            RE4DC_XM_LOAD(sat->imat);
            RE4DC_XM_POINT(sat->imat, pos0, &la);
            RE4DC_XM_POINT(sat->imat, pos1, &lb);
            RE4DC_XM_POINT(sat->imat, &cur, &lcur);
            r = blkPolyLineCk(sat, blk, &la, &lb, flag, mask, &lcur, &pn);
#endif
            if (r) {
#if defined(RE4DC_LINE_PIECE) && RE4DC_LINE_PIECE && defined(RE4DC_LINE_YROW) && RE4DC_LINE_YROW
                tmp = lcur0;
#if RE4DC_LINE_YROW == 2
                {
                    Vec rt;
                    PSMTXMultVec(sat->imat, &cur, &rt);
                    if (__builtin_memcmp(&rt, &tmp, 12) != 0) {
                        ++lyrTmpMis;
                    }
                }
#endif
#else
                PSMTXMultVec(sat->imat, &cur, &tmp);
#endif
                if (GetDistance(&la, &lcur) < GetDistance(&la, &tmp)) {
                    PSMTXMultVec(sat->mat, &lb, pos1);
                    ret = r;
                    PSMTXMultVec(sat->mat, &lcur, &cur);
#if defined(RE4DC_LINE_PIECE) && RE4DC_LINE_PIECE && defined(RE4DC_LINE_YROW) && RE4DC_LINE_YROW
                    curP1 = 0;
#endif
                    pBypassAt = sat;
#if defined(RE4DC_DECISION_TRACE) && RE4DC_DECISION_TRACE
                    dtWin = i;
#endif
                }
            }
        }
    }
    if (hit) {
        *hit = cur;
    }
    if (ret && attr) {
        *attr = pn;
    }
#if defined(RE4DC_DECISION_TRACE) && RE4DC_DECISION_TRACE
    {
        u32 b[3];
        __builtin_memcpy(b, &cur, 12);
        re4dc_dt_note(4, (u32) flag ^ ((u32) mask << 1), (u32) ret);
        re4dc_dt_note(4, dtWin, 0);
        re4dc_dt_note(5, b[0] ^ b[2], b[1]);
#if RE4DC_DECISION_TRACE == 2
        const int fw = re4dc_dt_window();
        if (fw >= 0) {
            u32 a0[3], a1[3];
            __builtin_memcpy(a0, pos0, 12);
            __builtin_memcpy(a1, pos1, 12);
            re4dc_log("LQ f=%d ra=%08x fl=%x m=%x r=%x w=%x p0=%08x,%08x,%08x p1=%08x,%08x,%08x\n", fw,
                      (u32) __builtin_return_address(0), flag, mask, ret, dtWin, a0[0], a0[1], a0[2], a1[0], a1[1], a1[2]);
        }
#endif
    }
#endif
#if defined(RE4DC_EL_CENSUS) && RE4DC_EL_CENSUS
    elcQueryEnd(ret, &cur, pn, pos1, pBypassAt);
#endif
    return ret;
}

// Line test through the block chain: descends into blocks whose box the segment overlaps and
// keeps the nearest hit (position, normal pointer in *pn). Returns the attribute of that hit.
int blkPolyLineCk(cSat* sat, cSatBlock* blk, Vec* pos0, Vec* pos1, int flag, int mask, Vec* hit, u32* pn)
{
    static int new_line_check = 1;
    Vec mid;
    Vec dir;
    Vec adir;
    int ret = 0;
    int r;

    PSVECAdd(pos0, pos1, &mid);
    PSVECScale(&mid, &mid, 0.5f);
    PSVECSubtract(pos0, &mid, &dir);
    adir.x = fabsf(dir.x);
    adir.y = fabsf(dir.y);
    adir.z = fabsf(dir.z);
    adir.y = 0.0f;
    dir.y = 0.0f;
    mid.y = 0.0f;
#if defined(RE4DC_LINE_WALK) && RE4DC_LINE_WALK
    if (new_line_check != 0) {
#if defined(RE4DC_LINE_RESUME) && RE4DC_LINE_RESUME
        LineResume29 walk;
        cSatBlock* first;
        lineResume29BeginBounds(&walk, blk, &mid, &dir, &adir);
        const int firstKind = lineResume29Next(&walk, &first);
        if (firstKind == 0) {
            return 0;
        }
        return lineResume29Run(sat, &walk, firstKind, first, pos0, pos1, flag, mask, hit, pn);
#else
        cSatBlock* leaf[LNW_MAX];
        const int nl = lineWalkLeaves(blk, &mid, &dir, &adir, leaf);
        if (nl >= 0) {
            for (int i = 0; i < nl; i++) {
                r = blkPolyLineCkCore(sat, leaf[i], pos0, pos1, flag, mask, hit, pn);
                if (r) {
                    ret = r;
                }
            }
            return ret;
        }
#endif
    }
#endif
    while (blk) {
        COL_PREFETCH(blk->next);
        if (new_line_check == 0) {
            if (blk->hitCheckSphere(pos0, pos1, 0.0f)) {
                if (blk->m_Flag & 1) {
                    r = blkPolyLineCk(sat, (cSatBlock*) blk->idx, pos0, pos1, flag, mask, hit, pn);
                    if (r) {
                        ret = r;
                    }
                } else {
                    r = blkPolyLineCkCore(sat, blk, pos0, pos1, flag, mask, hit, pn);
                    if (r) {
                        ret = r;
                    }
                }
            }
        } else {
            if (blk->lineOverlap(&mid, &dir, &adir)) {
                if (blk->m_Flag & 1) {
                    r = blkPolyLineCk(sat, (cSatBlock*) blk->idx, pos0, pos1, flag, mask, hit, pn);
                    if (r) {
                        ret = r;
                    }
                } else {
                    r = blkPolyLineCkCore(sat, blk, pos0, pos1, flag, mask, hit, pn);
                    if (r) {
                        ret = r;
                    }
                }
            }
        }
        blk = blk->next;
    }
    return ret;
}

#if defined(RE4DC_LINE_LEAF) && RE4DC_LINE_LEAF
// GAME_LINE_LEAF (game30.mk; G, collision traversal; exact): a leaf's polygons run the dedup on polyBit
// and At_poly_line_ck's first four tests (the plane crossing, the three edge sides) in
// platform/lnk_sh4.S, with the same float operations on the same operands; only the polygons passing
// all four reach At_poly_line_ck and the hit compare, in index order, so every result, distance
// compare and normal is the loop's. =2 (check build): each chunk's untested polygons are listed
// first, and every verdict is compared with the four tests in C and with At_poly_line_ck ("LNK" lines).
struct LineLeafQ {
    Vec p0;         // 0x00  vert0
    Vec p1;         // 0x0C  vert1
    Vec a;          // 0x18  vert1 - vert0 (At_poly_line_ck's a)
    Vec* vtx;       // 0x24
    Vec* nrm;       // 0x28
    Vec* edge;      // 0x2C
    AtPoly* poly;   // 0x30
    u8* bits;       // 0x34  polyBit
};
static_assert(__builtin_offsetof(LineLeafQ, vtx) == 0x24 && __builtin_offsetof(LineLeafQ, bits) == 0x34,
              "platform/lnk_sh4.S reads these offsets");
extern "C" int re4dc_line_leaf(const LineLeafQ* q, const u16* idx, int n, u16* out);
#define LNK_CHUNK 64
#if defined(RE4DC_LINE_LEAF2) && RE4DC_LINE_LEAF2
// GAME_LINE_LEAF2 (game30.mk; G, collision traversal; exact; needs GAME_LINE_LEAF=1): platform/lnk2_sh4.S's
// re4dc_line_leaf2, lnk_sh4.S's passes software-pipelined (the vertex and normal lines of the polygon two
// ahead prefetched during a plane test, the next polygon's and the next edge's lines during an edge test)
// with every float operation and compare of lnk_sh4.S; the survivor list gets one sentinel entry, so surv
// holds LNK_CHUNK + 1. =2 (check build): lnk_sh4.S runs first on the chunk (polyBit put back), then
// lnk2_sh4.S; survivors and polyBit compared ("LK2" lines).
extern "C" int re4dc_line_leaf2(const LineLeafQ* q, const u16* idx, int n, u16* out);
#if RE4DC_LINE_LEAF2 == 2
extern "C" void re4dc_log(const char* fmt, ...);
static u32 lk2Calls, lk2Tested, lk2Surv, lk2Mis, lk2Bits;
#endif
#endif
#if defined(RE4DC_LINE_TAIL) && RE4DC_LINE_TAIL
// GAME_LINE_TAIL (game30.mk; G, collision traversal; exact; needs GAME_LINE_LEAF=1): a leaf kernel survivor
// has passed At_poly_line_ck's plane test and three edge tests with the same operations, so the loop calls
// At_poly_line_tail (at_sub.cpp): At_poly_line_ck from t on (dp0 and a recomputed as there), with the same
// decision-trace note. =2 (check build): each call compared with At_poly_line_ck ("LTL" lines).
extern "C" u32 At_poly_line_tail(AtPolyData* pd, Vec* out, AtPoly* poly, Vec* vert0, Vec* vert1, u32 flag, u32 mask);
#endif
#if RE4DC_LINE_LEAF == 2
extern "C" void re4dc_log(const char* fmt, ...);
static u32 lnkCalls, lnkTested, lnkSurv, lnkBad, lnkLoose, lnkLost, lnkOrder;
// At_poly_line_ck's first four tests (at_sub.cpp), as written there: 1 when all four pass.
static int lnkPass4(AtPolyData* pd, AtPoly* poly, Vec* vert0, Vec* vert1)
{
    Vec d0;
    Vec d1;
    Vec c;
    Vec a;
    Vec b;
    Vec* vtx = pd->vtx;
    Vec* v0 = &vtx[poly->v[0]];
    Vec* v1;
    Vec* v2;
    Vec* nrm = &pd->nrm[poly->n];
    f32 dp0;
    f32 dp1;

    d0.x = vert0->x - v0->x;
    d0.y = vert0->y - v0->y;
    d0.z = vert0->z - v0->z;
    d1.x = vert1->x - v0->x;
    d1.y = vert1->y - v0->y;
    d1.z = vert1->z - v0->z;
    dp0 = d0.x * nrm->x + d0.y * nrm->y;
    dp0 += d0.z * nrm->z;
    dp1 = d1.x * nrm->x + d1.y * nrm->y;
    dp1 += d1.z * nrm->z;
    if (dp0 * dp1 > 0.0f) {
        return 0;
    }
    v1 = &vtx[poly->v[1]];
    PSVECSubtract(vert1, vert0, &a);
    PSVECSubtract(vert0, v0, &b);
    PSVECCrossProduct(&pd->edge[poly->e[0]], &a, &c);
    if (PSVECDotProduct(&c, &b) < 0.0f) {
        return 0;
    }
    v2 = &vtx[poly->v[2]];
    PSVECSubtract(vert0, v1, &b);
    PSVECCrossProduct(&pd->edge[poly->e[1]], &a, &c);
    if (PSVECDotProduct(&c, &b) < 0.0f) {
        return 0;
    }
    PSVECSubtract(vert0, v2, &b);
    PSVECCrossProduct(&pd->edge[poly->e[2]], &a, &c);
    if (PSVECDotProduct(&c, &b) < 0.0f) {
        return 0;
    }
    return 1;
}
#endif
static int lineLeaf(cSat* sat, u16* idx, int n, Vec* pos0, Vec* pos1, int flag, int mask, Vec* hit, u32* pn)
{
    LineLeafQ q;
#if defined(RE4DC_LINE_LEAF2) && RE4DC_LINE_LEAF2
    u16 surv[LNK_CHUNK + 1];
#else
    u16 surv[LNK_CHUNK];
#endif
    Vec h;
    int ret = 0;

    q.p0 = *pos0;
    q.p1 = *pos1;
    PSVECSubtract(pos1, pos0, &q.a);
    q.vtx = sat->vtx;
    q.nrm = sat->norm_p;
    q.edge = sat->edge_p;
    q.poly = sat->poly_p;
    q.bits = polyBit;
    while (n > 0) {
        const int c = n < LNK_CHUNK ? n : LNK_CHUNK;
#if RE4DC_LINE_LEAF == 2
        u16 cand[LNK_CHUNK];
        int nc = 0;
        for (int i = 0; i < c; i++) {
            const u32 no = idx[i];
            const u32 bit = 1 << (no & 7);
            if ((polyBit[no >> 3] & bit) == 0) {
                polyBit[no >> 3] |= bit;
                cand[nc++] = no;
            }
        }
        for (int j = 0; j < nc; j++) {
            polyBit[cand[j] >> 3] &= ~(1 << (cand[j] & 7));
        }
#endif
#if defined(RE4DC_LINE_LEAF2) && RE4DC_LINE_LEAF2
#if RE4DC_LINE_LEAF2 == 2
        u16 lk2c[LNK_CHUNK];
        u16 lk2s[LNK_CHUNK + 1];
        int lk2n = 0;
        for (int i = 0; i < c; i++) {
            const u32 no = idx[i];
            const u32 bit = 1 << (no & 7);
            if ((polyBit[no >> 3] & bit) == 0) {
                polyBit[no >> 3] |= bit;
                lk2c[lk2n++] = no;
            }
        }
        for (int j = 0; j < lk2n; j++) {
            polyBit[lk2c[j] >> 3] &= ~(1 << (lk2c[j] & 7));
        }
        const int lk2k = re4dc_line_leaf(&q, idx, c, lk2s);
        for (int j = 0; j < lk2n; j++) {
            polyBit[lk2c[j] >> 3] &= ~(1 << (lk2c[j] & 7));
        }
#endif
#if defined(RE4DC_EL_CENSUS) && RE4DC_EL_CENSUS
        elcLeafPolys(sat, idx, c, pos0, pos1, polyBit);
#endif
        const int k = re4dc_line_leaf2(&q, idx, c, surv);
#if defined(RE4DC_EL_CENSUS) && RE4DC_EL_CENSUS
        ELC_W(ELC_W_SURV, k);
#endif
#if RE4DC_LINE_LEAF2 == 2
        {
            int m = k != lk2k;
            for (int i = 0; !m && i < k; i++) {
                m = surv[i] != lk2s[i];
            }
            lk2Mis += m;
            for (int i = 0; i < c; i++) {
                if ((polyBit[idx[i] >> 3] & (1 << (idx[i] & 7))) == 0) {
                    ++lk2Bits;
                    break;
                }
            }
            lk2Tested += lk2n;
            lk2Surv += k;
            if (++lk2Calls % 8192 == 0) {
                re4dc_log("LK2 calls=%u tested=%u surv=%u mismatch=%u bits=%u\n", lk2Calls, lk2Tested, lk2Surv,
                          lk2Mis, lk2Bits);
            }
        }
#endif
#else
        const int k = re4dc_line_leaf(&q, idx, c, surv);
#endif
#if RE4DC_LINE_LEAF == 2
        {
            int s = 0;
            for (int j = 0; j < nc; j++) {
                AtPoly* poly = &sat->poly_p[cand[j]];
                const int kept = s < k && surv[s] == cand[j];
                const int p4 = lnkPass4((AtPolyData*) sat, poly, pos0, pos1);
                if (kept) {
                    s++;
                }
                if (p4 && !kept) {
                    ++lnkBad;
                }
                if (!p4 && kept) {
                    ++lnkLoose;
                }
                if (!kept && At_poly_line_ck((AtPolyData*) sat, &h, poly, pos0, pos1, flag, mask) != 0) {
                    ++lnkLost;
                }
                if ((polyBit[cand[j] >> 3] & (1 << (cand[j] & 7))) == 0) {
                    ++lnkOrder;
                }
            }
            if (s != k) {
                ++lnkOrder;
            }
            lnkTested += nc;
            lnkSurv += k;
            if (++lnkCalls % 8192 == 0) {
                re4dc_log("LNK calls=%u tested=%u surv=%u bad=%u loose=%u lost=%u order=%u\n", lnkCalls, lnkTested,
                          lnkSurv, lnkBad, lnkLoose, lnkLost, lnkOrder);
            }
        }
#endif
        for (int i = 0; i < k; i++) {
            AtPoly* poly = &sat->poly_p[surv[i]];
#if defined(RE4DC_LINE_TAIL) && RE4DC_LINE_TAIL
            const u32 attr = At_poly_line_tail((AtPolyData*) sat, &h, poly, pos0, pos1, flag, mask);
#else
            const u32 attr = At_poly_line_ck((AtPolyData*) sat, &h, poly, pos0, pos1, flag, mask);
#endif
            if (attr) {
#if defined(RE4DC_EL_CENSUS) && RE4DC_EL_CENSUS
                ELC_W(ELC_W_HITS, 1);
#endif
                if (GetDistance(pos0, &h) < GetDistance(pos0, hit)) {
#if defined(RE4DC_EL_CENSUS) && RE4DC_EL_CENSUS
                    ELC_W(ELC_W_TAKEN, 1);
#endif
                    *hit = h;
                    ret = attr;
                    if (pn) {
                        *pn = (u32) &sat->norm_p[poly->n];
                    }
                }
            }
        }
        idx += c;
        n -= c;
    }
    return ret;
}
#endif

// Line test of one block's polygons (floor / wall subset by flag), each once per query; keeps
// the hit closest to pos0 and its normal.
int blkPolyLineCkCore(cSat* sat, cSatBlock* blk, Vec* pos0, Vec* pos1, int flag, int mask, Vec* hit, u32* pn)
{
    Vec h;
    int ret = 0;
    int start;
    int end;
    int n;
    u16* idx;

    if (flag & 0x40) {
        start = 0;
        end = blk->m_nFloor + blk->m_nSlope;
    } else if (flag & 0x80) {
        start = blk->m_nFloor + blk->m_nSlope;
        end = start + blk->m_nWall;
    } else {
        start = 0;
        end = blk->m_nFloor + blk->m_nSlope + blk->m_nWall;
    }
    n = end - start;
    idx = &blk->idx[start];
#if defined(RE4DC_LINE_LEAF) && RE4DC_LINE_LEAF
    return n > 0 ? lineLeaf(sat, idx, n, pos0, pos1, flag, mask, hit, pn) : 0;
#else
#if defined(RE4DC_COL_PREFETCH) && RE4DC_COL_PREFETCH
    u16* idxEnd = &blk->idx[end];
    if (n > 0) {
        for (int k = 0; k < 4 && k < n; k++) {
            __builtin_prefetch(&sat->poly_p[idx[k]]);
        }
    }
#endif
    idx--;
    while (n--) {
        u32 no;
        AtPoly* poly;
        u32 bit;
        u32 attr;
        idx++;
        colPrefetchPoly(sat, idx, idxEnd);
        no = *idx;
        poly = &sat->poly_p[no];
        bit = 1 << (no & 7);
        if (polyBit[no >> 3] & bit) {
            continue;
        }
        polyBit[no >> 3] |= bit;
        attr = At_poly_line_ck((AtPolyData*) sat, &h, poly, pos0, pos1, flag, mask);
        if (attr) {
            if (GetDistance(pos0, &h) < GetDistance(pos0, hit)) {
                *hit = h;
                ret = attr;
                if (pn) {
                    *pn = (u32) &sat->norm_p[sat->poly_p[*idx].n];
                }
            }
        }
    }
    return ret;
#endif
}

// Releases a piece (freeing a file built by create(poly)); an invalid pointer is an error.
void cSatMgr::destroy(cSat* p)
{
    if (!VALID_PTR(p)) {
        pLog->err(0, 0, "cSatMgr::destroy() PTR ERR 0x%08x", p);
        return;
    }
    if (p->m_Flag & 2) {
        Mem_free(p->pFile);
    }
#if defined(RE4DC_LOGIC_WASTE) && RE4DC_LOGIC_WASTE >= 2
    re4dc_lw_sat_epoch();
#endif
    cManager<cSat>::destroy(p);
}

// cManager hook: constructs a fresh cSat in the pool slot.
int cSatMgr::construct(cSat* p, u32 id)
{
    // the alive flag before, the active flag after the constructor: keeps the vptr store last
    p->be_flag = 1;
    new (p) cSat();
    p->m_Flag = 0;
#if defined(RE4DC_LOGIC_WASTE) && RE4DC_LOGIC_WASTE >= 2
    re4dc_lw_sat_epoch();
#endif
    return 1;
}

// Debug draw: flag low nibble selects the polygon group, bits 24-31 an attribute bit to highlight.
void cSatMgr::disp(int flag)
{
    u32 i;
    u32 sel;

    GXSetLineWidth(6, 0);
    sel = (flag >> 8) & 0xFF0000;
    for (i = 0; i < nArray; i++) {
        cSat* sat = (cSat*) ((u8*) pArray + size * i);
        int s;
        int e;
        int j;
        if (!VALID_PTR(sat)) {
            continue;
        }
        if (!sat->isAlive()) {
            continue;
        }
        s = 0;
        e = 0;
        switch ((u32) flag & 0xF) {
        case 0:
            s = 0;
            e = sat->polygon_num;
            break;
        case 1:
            s = 0;
            e = sat->floor_num;
            break;
        case 2:
            s = sat->floor_num;
            e = s + sat->slope_num;
            break;
        case 3:
            s = sat->polygon_num - sat->wall_num;
            e = sat->polygon_num;
            break;
        }
        for (j = s; j < e; j++) {
            AtPoly* poly = (AtPoly*) (j * sizeof(AtPoly) + (u32) sat->poly_p);
            u32 attr = (poly->attrHi & 0xFF) << 16;
            attr |= poly->attrLo;
            u32 color;
            int z;
            if (attr != 0) {
                color = attr | 0x40000000;
                if (sel != 0) {
                    color = 0;
                    if (attr & (1 << sel)) {
                        color = 0x80808080;
                    }
                }
                z = 1;
            } else {
                color = 0xA0A0A0A0;
                if (sel == 0) {
                    color = 0xFFFFFFFF;
                }
                z = 0;
            }
            sat->disp(j, color, z);
        }
    }
}

// Binds the piece to SAT file `f` (table pointers via operator=), places it and links the block
// tree; m_Flag bit2 (active) set.
void cSat::init(cSatFile* f, Vec* pos, Vec* rot)
{
    if (!VALID_PTR(f)) {
        pLog->err(0, 0, "cSat::init() PTR ERR %08X", f);
        return;
    }
    if (!f->dataCheck()) {
        pLog->err(0, 0, "ATARI DATA ERROR 0x%08x", f);
    }
    m_Flag = 4;
    *this = f;
#if defined(RE4DC_LOGIC_WASTE) && RE4DC_LOGIC_WASTE >= 2
    re4dc_lw_sat_epoch();
#endif
    setCoord(pos, rot);
    blockInit(block_p);
}

// Places the piece: mat from rot / pos and its inverse for world -> local queries.
void cSat::setCoord(Vec* pos, Vec* rot)
{
    RotMatrix(mat, rot);
    TransMatrix(mat, pos);
    PSMTXInverse(mat, imat);
}

// Places the piece with a full matrix (and its inverse).
void cSat::setMatrix(Mtx m)
{
    memcpy(mat, m, sizeof(Mtx));
    PSMTXInverse(mat, imat);
}

cSat& cSat::operator=(cSatFile* f)
{
    Vec* v;

    vertex_num = f->m_nVertex;
    polygon_num = f->m_nPolygon;
    normal_num = f->m_nNormal;
    nEdge = f->m_nEdge;
    floor_num = f->m_nFloor;
    slope_num = f->m_nSlope;
    wall_num = f->m_nWall;
    bb_num = f->m_nBlock;
    v = f->getVertexPtr();
    pFile = f;
    x5C = 0;
    vtx = v;
    norm_p = v + vertex_num;
    edge_p = norm_p + normal_num;
    poly_p = (AtPoly*) (edge_p + nEdge);
    block_p = (cSatBlock*) (poly_p + polygon_num);
    return *this;
}

// Turn the relative block links of the file into pointers (once).
void cSat::blockInit(cSatBlock* blk)
{
    if (!VALID_PTR(blk)) {
        pLog->err(0, 0, "cSat::blockInit() INVALID PTR 0x%08x", blk);
        return;
    }
    if (VALID_PTR(blk->next)) {
        return;
    }
    do {
        if (blk->m_Flag & 1) {
            blockInit((cSatBlock*) blk->idx);
        }
        {
            u32 ofs = (u32) blk->next;
            if (ofs != 0) {
                cSatBlock* p = (cSatBlock*) ((u8*) blk + ofs);
                if (p != 0 && !VALID_PTR(p)) {
                    pLog->err(0, 0, "cSat::blockInit() INVALID PTR 0x%08x ( %08x )", p, ofs);
                    return;
                }
                blk->next = p;
            }
        }
        blk = blk->next;
    } while (blk);
}

// Debug draw of polygon `no`: outline (zupd bits 0-1 == 0, edges flagged in e[0] bits 13-15
// in grey) or filled (== 1), plus the face normal (white when it faces the camera).
void cSat::disp(int no, u32 color, int zupd)
{
    Vec p[3];
    Mtx m;
    Vec n;
    Vec w;
    AtPoly* pt = poly_p;
    Vec* vt = vtx;
    u16 i;

    PSMTXConcat(pG->Cam.v_mat, mat, m);
    for (i = 0; i < 3; i++) {
        AtPoly* pl = (AtPoly*) (no * sizeof(AtPoly) + (u32) pt);
        Vec* v = (Vec*) (*(u16*) (i * 2 + (u32) pl) * sizeof(Vec) + (u32) vt);
        p[i].x = v->x;
        p[i].y = v->y;
        p[i].z = v->z;
    }
    switch (zupd & 3) {
    case 0: {
        AtPoly* pl = (AtPoly*) (no * sizeof(AtPoly) + (u32) pt);
        Draw_line3d_local(&p[0], &p[1], m, (pl->e[0] & 0x2000) ? 0x80808080 : color, 0);
        Draw_line3d_local(&p[1], &p[2], m, (pl->e[0] & 0x4000) ? 0x80808080 : color, 0);
        Draw_line3d_local(&p[0], &p[2], m, (pl->e[0] & 0x8000) ? 0x80808080 : color, 0);
        break;
    }
    case 1:
        Draw_poly_local(p, m, color, 1);
        break;
    }
    PSVECAdd(&p[0], &p[1], &p[0]);
    color = 0xFF;
    PSVECAdd(&p[0], &p[2], &p[0]);
    PSVECScale(&p[0], &p[0], 1.0f / 3.0f);
    {
        AtPoly* pl = (AtPoly*) (no * sizeof(AtPoly) + (u32) poly_p);
        n.x = norm_p[pl->n].x;
        n.y = norm_p[pl->n].y;
        n.z = norm_p[pl->n].z;
    }
    PSVECScale(&n, &p[1], 100.0f);
    PSVECAdd(&p[0], &p[1], &p[1]);
    PSMTXMultVec(mat, &p[0], &w);
    PSVECSubtract(&w, &pG->Cam.param.pos, &w);
    PSMTXMultVecSR(mat, &n, &n);
    if (PSVECDotProduct(&n, &w) > 0.0f) {
        color = 0xFFFFFFFF;
    }
    Draw_line3d_local(&p[0], &p[1], m, color, 0);
}

// The vertex table right after the file header.
Vec* cSatFile::getVertexPtr()
{
    return (Vec*) (this + 1);
}

// Sanity check: at most 0x1FFF polygons (the polyBit table size).
int cSatFile::dataCheck()
{
    return m_nPolygon <= 0x1FFF;
}

// SAT `no` of a multi-SAT archive (offset table after the header).
cSatFile* cSatHeader::getSat(int no)
{
    u32* tbl = ofs;

    return (cSatFile*) ((u8*) this + *(u32*) (no * 4 + (u32) tbl));
}

// The three builders below with precomputed normals were dead-stripped by the linker; their
// tables, strings and constant pools stayed in .rodata.
static cSatFile* createSat2(cSat* sat, Vec* v, u32 attr, f32 h)
{
    static const AtPoly poly0[8] = {
        { { 5, 4, 1 }, 0, { 0, 1, 2 } },
        { { 4, 0, 1 }, 0, { 3, 4, 5 } },
        { { 6, 7, 3 }, 1, { 6, 7, 8 } },
        { { 3, 2, 6 }, 1, { 9, 10, 11 } },
        { { 7, 5, 1 }, 2, { 12, 13, 14 } },
        { { 1, 3, 7 }, 2, { 15, 16, 17 } },
        { { 4, 6, 2 }, 3, { 18, 19, 20 } },
        { { 2, 0, 4 }, 3, { 21, 22, 23 } },
    };
    static const Vec norm0[6] = {
        { 0.0f, 0.0f, 1.0f }, { 0.0f, 0.0f, -1.0f }, { -1.0f, 0.0f, 0.0f },
        { 1.0f, 0.0f, 0.0f }, { 0.0f, 1.0f, 0.0f },  { 0.0f, -1.0f, 0.0f },
    };
    cSatFile* f;
    Vec* vtx;
    Vec* nrm;
    u32 i;

    if (!VALID_PTR(sat)) {
        pLog->err(0, 0, "createSat() INVALID PTR %08X", sat);
        return 0;
    }
    f = (cSatFile*) MEM_ALLOC(0x298, 1, 13);
    if (h == 0.0f) {
        return 0;
    }
    vtx = (Vec*) (f + 1);
    nrm = &vtx[8];
    for (i = 0; i < 6; i++) {
        nrm[i].x = norm0[i].x * 1.1f;
        nrm[i].y = norm0[i].y * 0.1f;
        nrm[i].z = norm0[i].z * 2.2f;
    }
    memcpy(&nrm[6], poly0, sizeof(poly0));
    return f;
}

// Dead-stripped variant of createBoxSat with precomputed (scaled) normals; only its tables
// survive in .rodata.
static cSatFile* createBoxSat2(cSat* sat, Vec* v, u32 attr, f32 h)
{
    static const AtPoly poly0[12] = {
        { { 1, 0, 2 }, 4, { 0, 1, 2 } },
        { { 3, 1, 2 }, 4, { 3, 4, 5 } },
        { { 5, 4, 1 }, 0, { 6, 7, 8 } },
        { { 4, 0, 1 }, 0, { 9, 10, 11 } },
        { { 6, 7, 3 }, 1, { 12, 13, 14 } },
        { { 3, 2, 6 }, 1, { 15, 16, 17 } },
        { { 7, 5, 1 }, 2, { 18, 19, 20 } },
        { { 1, 3, 7 }, 2, { 21, 22, 23 } },
        { { 4, 6, 2 }, 3, { 24, 25, 26 } },
        { { 2, 0, 4 }, 3, { 27, 28, 29 } },
        { { 4, 5, 6 }, 5, { 30, 31, 32 } },
        { { 7, 6, 5 }, 5, { 33, 34, 35 } },
    };
    static const Vec norm0[6] = {
        { 0.0f, 0.0f, 1.0f }, { 0.0f, 0.0f, -1.0f }, { -1.0f, 0.0f, 0.0f },
        { 1.0f, 0.0f, 0.0f }, { 0.0f, 1.0f, 0.0f },  { 0.0f, -1.0f, 0.0f },
    };
    cSatFile* f;
    Vec* vtx;
    Vec* nrm;
    u32 i;

    if (!VALID_PTR(sat)) {
        pLog->err(0, 0, "createSat() INVALID PTR %08X", sat);
        return 0;
    }
    f = (cSatFile*) MEM_ALLOC(0x398, 1, 13);
    if (h == 0.0f) {
        return 0;
    }
    vtx = (Vec*) (f + 1);
    nrm = &vtx[8];
    for (i = 0; i < 6; i++) {
        nrm[i].x = norm0[i].x * 1.1f;
        nrm[i].y = norm0[i].y * 0.1f;
        nrm[i].z = norm0[i].z * 2.2f;
    }
    memcpy(&nrm[6], poly0, sizeof(poly0));
    return f;
}

// Dead-stripped variant of createFloorSat; only its tables survive.
static cSatFile* createFloorSat2(cSat* sat, Vec* v, u32 attr, f32 h)
{
    static const AtPoly poly0[2] = {
        { { 1, 0, 2 }, 0, { 0, 1, 2 } },
        { { 3, 1, 2 }, 0, { 3, 4, 5 } },
    };
    static const Vec norm0[1] = {
        { 0.0f, 1.0f, 0.0f },
    };
    static int floor_check = 0;
    cSatFile* f;
    Vec* vtx;
    Vec* nrm;
    u32 i;

    if (!VALID_PTR(sat)) {
        pLog->err(0, 0, "createSat() INVALID PTR %08X", sat);
        return 0;
    }
    f = (cSatFile*) MEM_ALLOC(0xE8, 1, 13);
    if (h == 0.0f || floor_check) {
        return 0;
    }
    vtx = (Vec*) (f + 1);
    nrm = &vtx[4];
    for (i = 0; i < 1; i++) {
        nrm[i].x = norm0[i].x * 1.1f;
        nrm[i].y = norm0[i].y * 0.1f;
        nrm[i].z = norm0[i].z * 2.2f;
    }
    memcpy(&nrm[1], poly0, sizeof(poly0));
    return f;
}

// Wall piece over the 4-corner polygon v (closed side box of height h, no top/bottom).
cSatFile* createSat(Vec* v, u32 attr, f32 h)
{
    static const AtPoly poly0[8] = {
        { { 5, 2, 1 }, 0, { 0, 1, 2 } },
        { { 2, 5, 6 }, 0, { 3, 4, 5 } },
        { { 3, 4, 0 }, 1, { 6, 7, 8 } },
        { { 3, 7, 4 }, 1, { 9, 10, 11 } },
        { { 0, 4, 1 }, 2, { 12, 13, 14 } },
        { { 1, 4, 5 }, 2, { 15, 16, 17 } },
        { { 2, 7, 3 }, 3, { 18, 19, 20 } },
        { { 2, 6, 7 }, 3, { 21, 22, 23 } },
    };
    cSatFile* f;
    Vec* vtx;
    Vec* nrm;
    Vec* e;
    AtPoly* poly;
    cSatBlock* blk;
    const AtPoly* p;
    u32 i;

#line 2621 "D:/Bio4/Prog/atari.cpp"
    f = (cSatFile*) MEM_ALLOC(0x298, 1, 13);
    if (!VALID_PTR(f)) {
        pLog->err(0, 0, "createSat() memory alloc failed.");
        return 0;
    }
    f->m_Version = 0xFF;
    f->m_nVertex = 8;
    f->m_nNormal = 4;
    f->m_nEdge = 24;
    f->m_nPolygon = 8;
    f->m_nFloor = 0;
    f->m_nSlope = 0;
    f->m_nWall = 8;
    f->m_nBlock = 1;
    vtx = (Vec*) (f + 1);
    vtx[0] = v[0];
    vtx[1] = v[1];
    vtx[2] = v[2];
    vtx[3] = v[3];
    vtx[4] = v[0];
    vtx[4].y += h;
    vtx[5] = v[1];
    vtx[5].y += h;
    vtx[6] = v[2];
    vtx[6].y += h;
    vtx[7] = v[3];
    vtx[7].y += h;
    nrm = &vtx[8];
    for (i = 0; i < 4; i++) {
        Vec d0;
        Vec d1;
        Vec* v0;
        p = &poly0[i * 2];
        v0 = &vtx[p->v[0]];
        PSVECSubtract(&vtx[p->v[1]], v0, &d0);
        PSVECSubtract(&vtx[p->v[2]], v0, &d1);
        PSVECCrossProduct(&d0, &d1, &nrm[i]);
#line 2661 "D:/Bio4/Prog/atari.cpp"
        VECNormalize(&nrm[i], &nrm[i]);
    }
    e = &nrm[4];
    for (i = 0; i < 8; i++) {
        Vec* v1 = (Vec*) (poly0[i].v[1] * sizeof(Vec) + (u32) vtx);
        Vec* v0 = (Vec*) (poly0[i].v[0] * sizeof(Vec) + (u32) vtx);
        Vec* v2 = (Vec*) (poly0[i].v[2] * sizeof(Vec) + (u32) vtx);
        e->x = v1->x - v0->x;
        e->y = v1->y - v0->y;
        e->z = v1->z - v0->z;
        e++;
        e->x = v2->x - v1->x;
        e->y = v2->y - v1->y;
        e->z = v2->z - v1->z;
        e++;
        e->x = v0->x - v2->x;
        e->y = v0->y - v2->y;
        e->z = v0->z - v2->z;
        e++;
    }
    poly = (AtPoly*) e;
    memcpy(poly, poly0, sizeof(poly0));
    for (i = 0; i < 8; i++) {
        poly[i].attr = attr;
    }
    blk = (cSatBlock*) (poly + 8);
    blk->min = vtx[0];
    blk->m_Size = vtx[0];
    for (i = 1; i < 4; i++) {
        if (vtx[i].x < blk->min.x) {
            blk->min.x = vtx[i].x - 10.0f;
        }
        if (vtx[i].z < blk->min.z) {
            blk->min.z = vtx[i].z - 10.0f;
        }
        if (vtx[i].x > blk->m_Size.x) {
            blk->m_Size.x = vtx[i].x + 10.0f;
        }
        if (vtx[i].z > blk->m_Size.z) {
            blk->m_Size.z = vtx[i].z + 10.0f;
        }
    }
    blk->m_Size.x -= blk->min.x;
    blk->m_Size.z -= blk->min.z;
    blk->m_nFloor = 0;
    blk->m_nSlope = 0;
    blk->m_nWall = 8;
    blk->m_Flag = 0;
    blk->next = 0;
    for (i = 0; i < 8; i++) {
        blk->idx[i] = i;
    }
    return f;
}

// Closed box piece over the 4-corner polygon v (height h): floor, walls and ceiling groups.
cSatFile* createBoxSat(Vec* v, u32 attr, f32 h)
{
    static const AtPoly poly0[12] = {
        { { 4, 6, 5 }, 0, { 0, 1, 2 } },
        { { 6, 4, 7 }, 0, { 3, 4, 5 } },
        { { 0, 1, 2 }, 1, { 6, 7, 8 } },
        { { 0, 2, 3 }, 1, { 9, 10, 11 } },
        { { 5, 2, 1 }, 2, { 12, 13, 14 } },
        { { 2, 5, 6 }, 2, { 15, 16, 17 } },
        { { 3, 4, 0 }, 3, { 18, 19, 20 } },
        { { 3, 7, 4 }, 3, { 21, 22, 23 } },
        { { 0, 4, 1 }, 4, { 24, 25, 26 } },
        { { 1, 4, 5 }, 4, { 27, 28, 29 } },
        { { 2, 7, 3 }, 5, { 30, 31, 32 } },
        { { 2, 6, 7 }, 5, { 33, 34, 35 } },
    };
    cSatFile* f;
    Vec* vtx;
    Vec* nrm;
    Vec* e;
    AtPoly* poly;
    cSatBlock* blk;
    const AtPoly* p;
    u32 i;

#line 2757 "D:/Bio4/Prog/atari.cpp"
    f = (cSatFile*) MEM_ALLOC(0x398, 1, 13);
    if (!VALID_PTR(f)) {
        pLog->err(0, 0, "createSat() memory alloc failed.");
        return 0;
    }
    f->m_Version = 0xFF;
    f->m_nVertex = 8;
    f->m_nNormal = 6;
    f->m_nEdge = 36;
    f->m_nPolygon = 12;
    f->m_nFloor = 0;
    f->m_nSlope = 4;
    f->m_nWall = 8;
    f->m_nBlock = 1;
    vtx = (Vec*) (f + 1);
    vtx[0] = v[0];
    vtx[1] = v[1];
    vtx[2] = v[2];
    vtx[3] = v[3];
    vtx[4] = v[0];
    vtx[4].y += h;
    vtx[5] = v[1];
    vtx[5].y += h;
    vtx[6] = v[2];
    vtx[6].y += h;
    vtx[7] = v[3];
    vtx[7].y += h;
    nrm = &vtx[8];
    for (i = 0; i < 6; i++) {
        Vec d0;
        Vec d1;
        Vec* v0;
        p = &poly0[i * 2];
        v0 = &vtx[p->v[0]];
        PSVECSubtract(&vtx[p->v[1]], v0, &d0);
        PSVECSubtract(&vtx[p->v[2]], v0, &d1);
        PSVECCrossProduct(&d0, &d1, &nrm[i]);
#line 2797 "D:/Bio4/Prog/atari.cpp"
        VECNormalize(&nrm[i], &nrm[i]);
    }
    e = &nrm[6];
    for (i = 0; i < 12; i++) {
        Vec* v1 = (Vec*) (poly0[i].v[1] * sizeof(Vec) + (u32) vtx);
        Vec* v0 = (Vec*) (poly0[i].v[0] * sizeof(Vec) + (u32) vtx);
        Vec* v2 = (Vec*) (poly0[i].v[2] * sizeof(Vec) + (u32) vtx);
        e->x = v1->x - v0->x;
        e->y = v1->y - v0->y;
        e->z = v1->z - v0->z;
        e++;
        e->x = v2->x - v1->x;
        e->y = v2->y - v1->y;
        e->z = v2->z - v1->z;
        e++;
        e->x = v0->x - v2->x;
        e->y = v0->y - v2->y;
        e->z = v0->z - v2->z;
        e++;
    }
    poly = (AtPoly*) e;
    memcpy(poly, poly0, sizeof(poly0));
    for (i = 0; i < 12; i++) {
        poly[i].attr = attr;
    }
    blk = (cSatBlock*) (poly + 12);
    blk->min = vtx[0];
    blk->m_Size = vtx[0];
    for (i = 1; i < 4; i++) {
        if (vtx[i].x < blk->min.x) {
            blk->min.x = vtx[i].x - 10.0f;
        }
        if (vtx[i].z < blk->min.z) {
            blk->min.z = vtx[i].z - 10.0f;
        }
        if (vtx[i].x > blk->m_Size.x) {
            blk->m_Size.x = vtx[i].x + 10.0f;
        }
        if (vtx[i].z > blk->m_Size.z) {
            blk->m_Size.z = vtx[i].z + 10.0f;
        }
    }
    blk->m_Size.x -= blk->min.x;
    blk->m_Size.z -= blk->min.z;
    blk->m_nFloor = 0;
    blk->m_nSlope = 4;
    blk->m_nWall = 8;
    blk->m_Flag = 0;
    blk->next = 0;
    for (i = 0; i < 12; i++) {
        blk->idx[i] = i;
    }
    return f;
}

// Floor piece: the 4-corner polygon v as two triangles.
static cSatFile* createFloorSat(Vec* v, u32 attr, f32 h)
{
    static const AtPoly poly0[2] = {
        { { 0, 2, 1 }, 0, { 0, 1, 2 } },
        { { 2, 0, 3 }, 0, { 3, 4, 5 } },
    };
    cSatFile* f;
    Vec* vtx;
    Vec* nrm;
    Vec* e;
    AtPoly* poly;
    cSatBlock* blk;
    const AtPoly* p;
    u32 i;

#line 2873 "D:/Bio4/Prog/atari.cpp"
    f = (cSatFile*) MEM_ALLOC(0xE8, 1, 13);
    if (!VALID_PTR(f)) {
        pLog->err(0, 0, "createSat() memory alloc failed.");
        return 0;
    }
    f->m_Version = 0xFF;
    f->m_nVertex = 4;
    f->m_nNormal = 1;
    f->m_nEdge = 6;
    f->m_nPolygon = 2;
    f->m_nFloor = 2;
    f->m_nSlope = 0;
    f->m_nWall = 0;
    f->m_nBlock = 1;
    vtx = (Vec*) (f + 1);
    vtx[0] = v[0];
    vtx[1] = v[1];
    vtx[2] = v[2];
    vtx[3] = v[3];
    nrm = &vtx[4];
    for (i = 0; i < 1; i++) {
        Vec d0;
        Vec d1;
        Vec* v0;
        p = &poly0[i * 2];
        v0 = &vtx[p->v[0]];
        PSVECSubtract(&vtx[p->v[1]], v0, &d0);
        PSVECSubtract(&vtx[p->v[2]], v0, &d1);
        PSVECCrossProduct(&d0, &d1, &nrm[i]);
#line 2910 "D:/Bio4/Prog/atari.cpp"
        VECNormalize(&nrm[i], &nrm[i]);
    }
    e = &nrm[1];
    for (i = 0; i < 2; i++) {
        Vec* v1 = (Vec*) (poly0[i].v[1] * sizeof(Vec) + (u32) vtx);
        Vec* v0 = (Vec*) (poly0[i].v[0] * sizeof(Vec) + (u32) vtx);
        Vec* v2 = (Vec*) (poly0[i].v[2] * sizeof(Vec) + (u32) vtx);
        e->x = v1->x - v0->x;
        e->y = v1->y - v0->y;
        e->z = v1->z - v0->z;
        e++;
        e->x = v2->x - v1->x;
        e->y = v2->y - v1->y;
        e->z = v2->z - v1->z;
        e++;
        e->x = v0->x - v2->x;
        e->y = v0->y - v2->y;
        e->z = v0->z - v2->z;
        e++;
    }
    poly = (AtPoly*) e;
    memcpy(poly, poly0, sizeof(poly0));
    for (i = 0; i < 2; i++) {
        poly[i].attr = attr;
    }
    blk = (cSatBlock*) (poly + 2);
    blk->min = vtx[0];
    blk->m_Size = vtx[0];
    for (i = 1; i < 4; i++) {
        if (vtx[i].x < blk->min.x) {
            blk->min.x = vtx[i].x - 10.0f;
        }
        if (vtx[i].z < blk->min.z) {
            blk->min.z = vtx[i].z - 10.0f;
        }
        if (vtx[i].x > blk->m_Size.x) {
            blk->m_Size.x = vtx[i].x + 10.0f;
        }
        if (vtx[i].z > blk->m_Size.z) {
            blk->m_Size.z = vtx[i].z + 10.0f;
        }
    }
    blk->m_Size.x -= blk->min.x;
    blk->m_Size.z -= blk->min.z;
    blk->m_nFloor = 2;
    blk->m_nSlope = 0;
    blk->m_nWall = 0;
    blk->m_Flag = 0;
    blk->next = 0;
    for (i = 0; i < 2; i++) {
        blk->idx[i] = i;
    }
    return f;
}

// Move the model (and its parts' world matrices) by d after a collision push.
void at_pos_calc(cModel* m, Vec* vec)
{
    cModel* c = m->pParts;

    if (PSVECMag(vec) != 0.0f) {
        PSVECAdd(&m->pos, vec, &m->pos);
        while (c) {
            PSVECAdd(&c->world, vec, &c->world);
            c->mat[0][3] += vec->x;
            c->mat[1][3] += vec->y;
            c->mat[2][3] += vec->z;
            c = c->pParts;
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

cSatMgr SatMgr;
cEatMgr EatMgr;

#if defined(RE4DC_LQ_MEMO) && RE4DC_LQ_MEMO
// GAME_LQ_MEMO (game30.mk; lane el 2026-10-05; enemy logic, line queries; exact): wallAdjust (above) asks its line
// question twice, around the sphere pass. When the first query hit nothing and neither end has moved since (bit for
// bit), the second is the same question about the same pieces (the sphere pass writes no piece, flag, mask or seCk)
// and gets the same answer, nothing, without a walk; it then writes what that walk writes that anyone reads: SEck.
// Trace builds record the first walk's decision notes (logic_trace.cpp re4dc_dt_note -> re4dc_lqm_note) and give
// them again for the second, so the LX hashes and counts stay those of two walks; when the notes do not fit
// (LQM_NOTES) the second query walks.
// =2 (check build): the second query always walks; "LQM pair= pairsame= pairmis=" counts the queries, those the memo
// would have answered and the answers that differed from the walk's (must be 0).
extern "C" void re4dc_log(const char* fmt, ...);

static int lqmVecSame(const Vec* a, const Vec* b)
{
    const u32* x = (const u32*) a;
    const u32* y = (const u32*) b;
    return x[0] == y[0] && x[1] == y[1] && x[2] == y[2];
}

#if defined(RE4DC_DECISION_TRACE) && RE4DC_DECISION_TRACE
static LqmNotes* lqmRec;      // the recording in progress (wallAdjust's first query)
extern "C" void re4dc_lqm_note(unsigned kind, unsigned a, unsigned b)
{
    LqmNotes* r = lqmRec;
    if (!r || r->n == LQM_NOTE_OVER) {
        return;
    }
    if (r->n + 3 > 3 * LQM_NOTES) {
        r->n = LQM_NOTE_OVER;
        return;
    }
    r->w[r->n] = kind;
    r->w[r->n + 1] = a;
    r->w[r->n + 2] = b;
    r->n += 3;
}
static void lqmNotesBegin(LqmNotes* r)
{
    r->n = 0;
    lqmRec = r;
}
static void lqmNotesEnd(LqmNotes* r)
{
    (void) r;
    lqmRec = 0;
}
static void lqmNotesReplay(const LqmNotes* r)
{
    for (u32 i = 0; i < r->n; i += 3) {
        re4dc_dt_note(r->w[i], r->w[i + 1], r->w[i + 2]);
    }
}
#endif

#if RE4DC_LQ_MEMO == 2
static u32 lqmPairN, lqmPairHit, lqmPairMis;
static void lqmPairCount(int same, int mis)
{
    lqmPairN++;
    lqmPairHit += same != 0;
    lqmPairMis += mis != 0;
    if ((lqmPairN & 0x3FFF) == 0) {
        re4dc_log("LQM pair=%u pairsame=%u pairmis=%u\n", lqmPairN, lqmPairHit, lqmPairMis);
    }
}
#endif
#endif

#if defined(RE4DC_LOGIC_WASTE) && RE4DC_LOGIC_WASTE
// LOGIC_WASTE (game30.mk; logic waste census LOGIC-WASTE-CENSUS-20261015.md; exact): re4dc_logic_waste_mask is a
// data word (LOGIC_WASTE_MASK, default 0), so every bit shares one code layout. Bits:
//   0x01 cAtariInfo::getPos keeps each body's rotated offset (atariInfo.cpp)
//   0x02 Ps2fxClass verdicts per effect recipe (esp_sub.cpp; render only)
//   0x08 camera obstruction lines: SatMgr's answer reused when the line, flags and room collision are unchanged
//   0x100 check mode: every reused answer is also computed and compared ("LWM" / "LWF" lines, mismatches must be 0;
//         not for trace builds: the extra queries add decision notes)
// (Census item 6, the wall check reuse, was built and measured: 0 of 7,632 wallAdjust queries at the r101 cross
// repeated their inputs bit for bit, since the bodies follow animated parts; it was removed.)
// The room collision (SatMgr's pieces) is proved unchanged at every lookup: lwSceneGen compares each slot's
// alive state and, for alive pieces, its file, block root, polygon count and both matrices with a snapshot, and
// the piece hooks (construct / destroy / init) bump an epoch, so a piece rebuilt on reused memory is new too.
// A line query reads only those pieces and its own arguments (seCk is copied to SEck first); it writes its outputs
// (pos1 moves on a hit), SEck, pBypassAt (read only by hitCheck right after a hit) and polyBit (scratch, cleared
// per piece before each use). Trace builds record the decision notes of the computed answer and give them again
// with a reused one.
extern "C" void re4dc_log(const char* fmt, ...);
#if defined(RE4DC_DECISION_TRACE) && RE4DC_DECISION_TRACE
extern "C" unsigned re4dc_dt_note(unsigned kind, unsigned a, unsigned b);
#endif
extern "C" {
u32 __attribute__((section(".data"))) re4dc_logic_waste_mask = RE4DC_LOGIC_WASTE_MASK;
// Both words are kept in .data (a 0 mask would otherwise go to .bss and move the layout).
// LOGIC_APPROX_MASK (game30.mk; census approximation arms, user 10-15 "I'm good with approximations"; NOT exact,
// gated by gameplay equivalence): 0x01 Leon's jacket constraints at half rate (pendulum.cpp PenClothMove3),
// 0x02 sound surround / occlusion slots at half rate, interleaved (snd.cpp sndSurroundCalc).
u32 __attribute__((section(".data"))) re4dc_logic_approx_mask = RE4DC_LOGIC_APPROX_MASK;
}
// LOGIC_WASTE=2 keeps the closed census memos (getPos, camera lines, sound half rate; measured no net gain,
// lane logicwaste 2026-10-15) for re-measurement; LOGIC_WASTE=1 compiles only the kept bits and the mask words.
#if RE4DC_LOGIC_WASTE >= 2
static u32 lwEpoch = 1;
void re4dc_lw_sat_epoch()
{
    ++lwEpoch;
}
#define LW_SAT_MAX 32
struct LwSatSnap {
    u32 alive;
    void* file;
    void* blk;
    u32 npoly;
    u32 m[24];   // mat, imat
};
static LwSatSnap lwSnap[LW_SAT_MAX];
static u32 lwSnapEpoch, lwSnapN, lwSnapSize, lwGen = 1;
static void* lwSnapArr;
// The generation of the room collision now (0: not provable, no reuse).
static u32 lwSceneGen(cSatMgr* mgr)
{
    const u32 n = mgr->nArray;
    if (mgr != &SatMgr || n > LW_SAT_MAX) {
        return 0;
    }
    int same = lwSnapEpoch == lwEpoch && lwSnapArr == (void*) mgr->pArray && lwSnapN == n && lwSnapSize == mgr->size;
    u8* p = (u8*) mgr->pArray;
    for (u32 i = 0; i < n; i++, p += mgr->size) {
        cSat* sat = (cSat*) p;
        LwSatSnap& s = lwSnap[i];
        const u32 alive = sat->isAlive();
        if (!alive) {
            if (s.alive) {
                s.alive = 0;
                same = 0;
            }
            continue;
        }
        const u32* m = (const u32*) sat->mat;   // mat 0x60, imat 0x90: contiguous
        int d = !s.alive || s.file != (void*) sat->pFile || s.blk != (void*) sat->block_p || s.npoly != sat->polygon_num;
        for (u32 k = 0; k < 24; k++) {
            if (s.m[k] != m[k]) {
                d = 1;
                s.m[k] = m[k];
            }
        }
        if (d) {
            s.alive = 1;
            s.file = (void*) sat->pFile;
            s.blk = (void*) sat->block_p;
            s.npoly = sat->polygon_num;
            same = 0;
        }
    }
    if (!same) {
        lwSnapEpoch = lwEpoch;
        lwSnapArr = (void*) mgr->pArray;
        lwSnapN = n;
        lwSnapSize = mgr->size;
        if (++lwGen == 0) {
            lwGen = 1;
        }
    }
    return lwGen;
}

static inline int lwSame(const u32* a, const u32* b, u32 n)
{
    for (u32 i = 0; i < n; i++) {
        if (a[i] != b[i]) {
            return 0;
        }
    }
    return 1;
}
static inline void lwCopy(u32* d, const void* s, u32 n)
{
    const u32* q = (const u32*) s;
    for (u32 i = 0; i < n; i++) {
        d[i] = q[i];
    }
}

#if defined(RE4DC_DECISION_TRACE) && RE4DC_DECISION_TRACE
#define LW_NOTES 48
struct LwNotes {
    u32 n;   // words (3 per note); LQM_NOTE_OVER style overflow: 0xFFFFFFFF
    u32 w[3 * LW_NOTES];
};
static LwNotes* lwRec;
extern "C" void re4dc_lw_note(unsigned kind, unsigned a, unsigned b)
{
    LwNotes* r = lwRec;
    if (!r || r->n == 0xFFFFFFFFu) {
        return;
    }
    if (r->n + 3 > 3 * LW_NOTES) {
        r->n = 0xFFFFFFFFu;
        return;
    }
    r->w[r->n] = kind;
    r->w[r->n + 1] = a;
    r->w[r->n + 2] = b;
    r->n += 3;
}
static void lwReplay(const LwNotes* r)
{
    for (u32 i = 0; i < r->n; i += 3) {
        re4dc_dt_note(r->w[i], r->w[i + 1], r->w[i + 2]);
    }
}
#endif

static u32 lwStat[8];   // [0] camera lookups, [1] reuses, [4] check-mode mismatches, [7] log pacing
static void lwStatLog()
{
    if ((++lwStat[7] & 0x3FF) == 0) {
        re4dc_log("LWM cam=%u/%u mis=%u gen=%u n=%u\n", lwStat[1], lwStat[0], lwStat[4], lwGen, SatMgr.nArray);
    }
}

// Bit 0x08: SatMgr.hitCheck for cameraHitCheck (cam_ctrl.cpp).
struct LwLine {
    u32 k[12];   // p0, p1, flag, mask, seCk, SEck in, gen, 0
    u32 ret;
    u32 p1[3];
    u32 hit[3];
    u32 nrm[3];
    cSat* bypass;
#if defined(RE4DC_DECISION_TRACE) && RE4DC_DECISION_TRACE
    LwNotes notes;
#endif
};
static LwLine lwLine[8];
static u32 lwLineNext;
extern "C" int re4dc_lw_cam_hitcheck(Vec* pos0, Vec* pos1, Vec* hit, Vec* nrm, int flag, int mask)
{
    if (!(re4dc_logic_waste_mask & 0x08)) {
        return SatMgr.hitCheck(pos0, pos1, hit, nrm, flag, mask);
    }
    const u32 gen = lwSceneGen(&SatMgr);
    u32 k[12];
    lwCopy(k, pos0, 3);
    lwCopy(k + 3, pos1, 3);
    k[6] = (u32) flag;
    k[7] = (u32) mask;
    k[8] = (u32) SatMgr.seCk;
    k[9] = (u32) SEck;
    k[10] = gen;
    k[11] = 0;
    lwStat[0]++;
    lwStatLog();
    if (gen) {
        for (u32 i = 0; i < 8; i++) {
            LwLine& e = lwLine[i];
            if (!lwSame(e.k, k, 12)) {
                continue;
            }
            lwStat[1]++;
            if (re4dc_logic_waste_mask & 0x100) {
                Vec h, nn;
                Vec p1 = *pos1;
                const int r = SatMgr.hitCheck(pos0, &p1, &h, &nn, flag, mask);
                int bad = (u32) r != e.ret || !lwSame((const u32*) &p1, e.p1, 3) || !lwSame((const u32*) &h, e.hit, 3) ||
                          (r && !lwSame((const u32*) &nn, e.nrm, 3));
                if (bad) {
                    lwStat[4]++;
                    re4dc_log("LWM cam mismatch ret %u/%u\n", (u32) r, e.ret);
                }
            }
            ((SEckView*) &SEck)->v = SatMgr.seCk;
            lwCopy((u32*) pos1, e.p1, 3);
            if (hit) {
                lwCopy((u32*) hit, e.hit, 3);
            }
            if (e.ret) {
                pBypassAt = e.bypass;
                if (nrm) {
                    lwCopy((u32*) nrm, e.nrm, 3);
                }
            }
#if defined(RE4DC_DECISION_TRACE) && RE4DC_DECISION_TRACE
            lwReplay(&e.notes);
#endif
            return (int) e.ret;
        }
    }
    Vec h, nn;
#if defined(RE4DC_DECISION_TRACE) && RE4DC_DECISION_TRACE
    LwNotes rec;
    rec.n = 0;
    LwNotes* outer = lwRec;
    lwRec = &rec;
#endif
    const int r = SatMgr.hitCheck(pos0, pos1, &h, &nn, flag, mask);
#if defined(RE4DC_DECISION_TRACE) && RE4DC_DECISION_TRACE
    lwRec = outer;
#endif
    if (hit) {
        *hit = h;
    }
    if (r && nrm) {
        *nrm = nn;
    }
    if (gen && hit && nrm) {
#if defined(RE4DC_DECISION_TRACE) && RE4DC_DECISION_TRACE
        if (rec.n == 0xFFFFFFFFu) {
            return r;
        }
#endif
        LwLine& e = lwLine[lwLineNext++ & 7];
        lwCopy(e.k, k, 12);
        e.ret = (u32) r;
        lwCopy(e.p1, pos1, 3);
        lwCopy(e.hit, &h, 3);
        lwCopy(e.nrm, &nn, 3);
        e.bypass = pBypassAt;
#if defined(RE4DC_DECISION_TRACE) && RE4DC_DECISION_TRACE
        e.notes = rec;
#endif
    }
    return r;
}

#endif
#endif
