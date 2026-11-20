// volumes.cpp: the native actor-volume service (lane eng-svc4; volumes.h, docs/engine/SERVICES.md section 23).
//
// What it owns (the original units atariInfo.cpp, at_mod.cpp and at_sub.cpp, every function they link):
//   - the collision body of a character or object (cAtariInfo: a cylinder, or a yaw-aligned box with flag 2, at an
//     offset from the model or one of its parts; radius blending over m_hokan ticks; push priority in flag bits 3-4);
//   - the pushes between bodies (EmAtCheck: every collidable body's world position, then the body against every other
//     character and object by priority: sphere / sphere, sphere / box, box / box);
//   - line tests against the bodies (EmHitCheck, ObjHitCheck, ComnHitCheck, ObaLineHitChk: aiming and the camera);
//   - the hit-box chain set-up (YarareInit, YarareAdd);
//   - the geometry predicates under the collision code (at_sub.cpp: plane, triangle, box, sphere, capsule, quad).
// Debug drawing (cAtariInfo::disp / dispRect, DrawOba, AtCapsuleDisp, AtCubeDisp) draws nothing: the engine's renderer
// has no debug lines; the calls are counted.
//
// Arithmetic: the original's, operation for operation and in its order (single precision, contraction off), so the
// PC reference compares bit for bit; the vector and matrix calls go through the SDK interface (PSVEC / PSMTX), which
// the engine's math layer provides. The bodies live in the actors' records (cEm::atari), which behaviour reads and
// writes directly (m_flag, m_radius, m_pMod): they stay there.
#include "atari.h"
#include "at_mod.h"
#include "at_sub.h"
#include "em.h"
#include "obj.h"
#include "player.h"
#include "global.h"
#include "math_sub.h"
#include "motion.h"
#include "volumes.h"

extern "C" {
VolCounters vol_cnt;
int vol_control;
void yarareInit0(YARARE_INFO* y, f32 x, f32 yy, f32 z, f32 w, f32 h, s16 no, u16 flags);
void YarareInit(cEm* em, f32 x, f32 y, f32 z, f32 w, f32 h, s16 no, u16 flags);
void YarareAdd(cEm* em, YARARE_INFO* box, f32 x, f32 y, f32 z, f32 w, f32 h, s16 no, u16 flags);
void YarareInitCube(cEm* em, f32 x, f32 y, f32 z, f32 w, f32 h, f32 extent, s16 no, u16 flags);
// em_sub.cpp (the enemy unit): the line against an oriented box (the box bodies' line test)
int emLineCubeCrossCk(Vec* a, Vec* b, Mtx m, f32 sx, f32 sy, f32 sz, Vec* ofs, Vec* hit);
}

// at_sub.cpp's scratch box (behaviour fills it for At_box_sphere_ck)
Vec BoxTmp[16];

namespace {

// VECNormalize as the original's macro: a zero vector is reported and zeroed (the destination), else normalised.
inline void vol_normalize(const Vec* test, Vec* src, Vec* dst, int line)
{
    if (0.0f == test->x && 0.0f == test->y && 0.0f == test->z) {
        pLog->err(0, 0, "VECNormalize:[%s/%d]", "volumes", line);
        dst->x = dst->y = dst->z = 0.0f;
    } else {
        PSVECNormalize(src, dst);
    }
}

inline f32 sq_dist(const Vec* a, const Vec* b)
{
    return (a->x - b->x) * (a->x - b->x) + (a->y - b->y) * (a->y - b->y) + (a->z - b->z) * (a->z - b->z);
}

// A push vector scaled for the volpush control (identity otherwise).
inline void push_scale(Vec* d)
{
    if (vol_control == 1) PSVECScale(d, d, 1.1f);
}

}   // namespace

// ==== the body (atariInfo.cpp) ====

void cAtariInfo::init0(int parts, int hokan, int flag, f32 x, f32 y, f32 z, f32 rx, f32 rz, f32 w, f32 hh)
{
    m_offset.x = x;
    m_offset.y = y;
    m_offset.z = z;
    m_radius_n = rx;
    m_radius2_n = rz;
    m_radius = rx;
    m_radius2 = rz;
    m_radius3 = w;
    m_height = hh;
    m_parts_no = parts;
    m_hokan = hokan;
    m_flag = flag | 0x300;
    x48 = 0;
    m_stat = 1;
}

void cAtariInfo::init(int parts, int flag, int hokan, f32 x, f32 y, f32 z, f32 rx, f32 rz, f32 w, f32 hh)
{
    init0(parts, hokan, flag, x, y, z, rx, rz, w, hh);
    m_flag |= 1;
}

// mode < 0: jump to radius 100 and blend to (a, b) over -mode ticks; 0: set at once; > 0: blend over mode ticks.
void cAtariInfo::set(int mode, f32 a, f32 b)
{
    if (mode < 0) {
        m_radius_n = a;
        m_radius2_n = b;
        m_radius2 = 100.0f;
        m_radius = 100.0f;
        mode = -mode;
    } else {
        if (mode == 0) {
            m_radius = a;
            m_radius2 = b;
        }
        m_radius_n = a;
        m_radius2_n = b;
    }
    m_hokan = mode;
}

void cAtariInfo::setPriority(int prio)
{
    m_flag &= ~0x18;
    if (prio >= 1 && prio <= 3) m_flag |= prio << 3;
}

void cAtariInfo::move()
{
    if (m_hokan != 0) {
        const f32 c = (f32) m_hokan;
        m_hokan--;
        m_radius += (m_radius_n - m_radius) / c;
        m_radius2 += (m_radius2_n - m_radius2) / c;
    }
}

// World position of the body: the offset turned by the model's angles, from the model or its part.
void cAtariInfo::getPos(cModel* m, Vec* out)
{
    Vec v;
    RotVector(&m_offset, &m->ang, &v);
    if (m_parts_no != 0) {
        PSVECAdd(&m->getPartsPtr(m_parts_no - 1)->world, &v, out);
    } else {
        PSVECAdd(&m->pos, &v, out);
    }
}

// The body's centre this tick and last tick (a part's centre at the model's height plus the radius).
void cAtariInfo::getSpeedVector(cModel* m, Vec* oldPos, Vec* newPos)
{
    Vec v;
    if (m_parts_no != 0) {
        cModel* p = m->getPartsPtr(m_parts_no - 1);
        v.x = m_offset.x;
        v.y = m_offset.y;
        v.z = m_offset.z;
        RotVector(&v, &m->ang, &v);
        PSVECAdd(&p->world, &v, newPos);
        PSVECAdd(&p->world_old, &v, oldPos);
        newPos->y = m->pos.y + m_radius;
        oldPos->y = m->pos_old.y + m_radius;
    } else {
        v.x = m_offset.x;
        v.y = m_offset.y + m_radius;
        v.z = m_offset.z;
        RotVector(&v, &m->ang, &v);
        PSVECAdd(&m->pos, &v, newPos);
        PSVECAdd(&m->pos_old, &v, oldPos);
    }
}

void cAtariInfo::disp(cModel*) { vol_cnt.debug_draws++; }
void cAtariInfo::dispRect(cModel*) { vol_cnt.debug_draws++; }

// ==== hit boxes (at_mod.cpp) ====

void yarareInit0(YARARE_INFO* y, f32 x, f32 yy, f32 z, f32 w, f32 h, s16 no, u16 flags)
{
    y->ofs.x = x;
    y->ofs.y = yy;
    y->ofs.z = z;
    y->width = w;
    y->height = h;
    y->partsNo = no;
    y->flags = flags;
    y->next = 0;
}

void YarareInit(cEm* em, f32 x, f32 y, f32 z, f32 w, f32 h, s16 no, u16 flags)
{
    yarareInit0(&em->hitInfo, x, y, z, w, h, no, flags);
}

// lane eng-e1e: the box form of the primary hit box (flags bit 3, depth = extent), which the fight image's scenario code
// sets on a shoot-down item (sce_at.cpp SceAtSetShootDownItem); the original's three stores after yarareInit0.
void YarareInitCube(cEm* em, f32 x, f32 y, f32 z, f32 w, f32 h, f32 extent, s16 no, u16 flags)
{
    yarareInit0(&em->hitInfo, x, y, z, w, h, no, flags);
    em->hitInfo.depth = extent;
    em->hitInfo.flags |= 8;
}

void YarareAdd(cEm* em, YARARE_INFO* box, f32 x, f32 y, f32 z, f32 w, f32 h, s16 no, u16 flags)
{
    YARARE_INFO* p = &em->hitInfo;
    yarareInit0(box, x, y, z, w, h, no, flags);
    for (; p->next != 0; p = p->next) {
        if (p == box) {
            pLog->err(0, 0, "YarareAdd() Add same pointer, EM%02x", em->id);
            return;
        }
    }
    if (p == box) {
        pLog->err(0, 0, "YarareAdd() Add same pointer, EM%02x", em->id);
        return;
    }
    p->next = box;
}

// ==== pushes between bodies (at_mod.cpp) ====

namespace {
inline bool collidable(cEm* m) { return (m->atari.m_flag & 0x200) && m->atari.m_radius2 != 0.0f; }
// 1: pMod outranks (or equals a ranked) pMod2: pMod is not pushed by it.
inline bool outranks(cEm* a, cEm* b)
{
    const u8 pa = a->atari.m_flag & 0x18, pb = b->atari.m_flag & 0x18;
    return pa != 0 && pa >= pb;
}
}

void EmAtCheck(cEm* em)
{
    vol_cnt.at_checks++;
    if (!collidable(em)) {
        vol_cnt.at_skipped++;
        em->atari.m_stat |= 1;
        return;
    }
    em->atari.getPos(em, &em->atari.m_Pos);
    // characters, then objects: every collidable body's position, the pushes, then the old positions
    for (int list = 0; list < 2; list++) {
        cEm* head = list == 0 ? (cEm*) EmMgr.pAlive : (cEm*) ObjMgr.pAlive;
        for (cEm* m = head; m != 0; m = (cEm*) m->pNext)
            if (collidable(m)) m->atari.getPos(m, &m->atari.m_Pos);
        for (cEm* m = head; m != 0; m = (cEm*) m->pNext)
            if ((m->atari.m_flag & 0x200) && m != em && m->atari.m_radius2 != 0.0f) __em_at_core(em, m);
        for (cEm* m = head; m != 0; m = (cEm*) m->pNext)
            if (collidable(m)) m->atari.m_oldPos = m->atari.m_Pos;
    }
    PartsWorldPosCalc(em);
    em->atari.m_stat &= ~1;
}

void __em_at_core(cEm* pMod, cEm* pMod2)
{
    vol_cnt.pairs++;
    if (outranks(pMod, pMod2)) {
        vol_cnt.pairs_prio++;
        return;
    }
    int r;
    if ((pMod->atari.m_flag | pMod2->atari.m_flag) & 2) vol_cnt.pairs_box++;
    if (pMod->atari.m_flag & 2)
        r = (pMod2->atari.m_flag & 2) ? At_em_rect_rect_ck(pMod, pMod2) : At_em_sphere_rect_ck(pMod2, pMod);
    else
        r = (pMod2->atari.m_flag & 2) ? At_em_sphere_rect_ck(pMod, pMod2) : At_em_sphere_sphere_ck(pMod, pMod2);
    if (r) vol_cnt.pushes++;
}

// The four corners of a box body in the XZ plane (y at the body's offset), turned by the model's angles.
static void box_corners(cEm* m, Vec* out)
{
    cAtariInfo* ia = &m->atari;
    const f32 rx = ia->m_radius, rz = ia->m_radius2;
    static const f32 sx[4] = {1.0f, 1.0f, -1.0f, -1.0f}, sz[4] = {1.0f, -1.0f, -1.0f, 1.0f};
    for (int i = 0; i < 4; i++) {
        Vec v;
        v.x = sx[i] > 0.0f ? rx : -rx;
        v.y = 0.0f;
        v.z = sz[i] > 0.0f ? rz : -rz;
        PSVECAdd(&v, &ia->m_offset, &v);
        RotVector(&v, &m->ang, &v);
        PSVECAdd(&v, &m->pos, &out[i]);
    }
}

int em_rect2_ck_sub(cEm* pMod, cEm* pMod2)
{
    Vec ra[4];
    Vec rb[4];
    box_corners(pMod, ra);
    box_corners(pMod2, rb);
    if (fabsf(ra[0].y - rb[0].y) > pMod->atari.m_height + pMod2->atari.m_height) return 0;
    return At_rect_rect_ck(ra, rb) != 0 ? 1 : 0;
}

// Box against box: the lower-ranked (or, unranked, the other) box is moved out along the axis the mover moved on.
int At_em_rect_rect_ck(cEm* pMod, cEm* pMod2)
{
    int ret = em_rect2_ck_sub(pMod, pMod2);
    if (ret == 0) return 0;
    const Vec posA = pMod->pos;
    f32 aw, ad, bw, bd;
    Vec ra, rb;
    if (!(Get_ang_dir(pMod->ang.y) & 1)) {
        aw = pMod->atari.m_radius;
        ad = pMod->atari.m_radius2;
    } else {
        aw = pMod->atari.m_radius2;
        ad = pMod->atari.m_radius;
    }
    RotVector(&pMod->atari.m_offset, &pMod->ang, &ra);
    if (!(Get_ang_dir(pMod2->ang.y) & 1)) {
        bw = pMod2->atari.m_radius;
        bd = pMod2->atari.m_radius2;
    } else {
        bw = pMod2->atari.m_radius2;
        bd = pMod2->atari.m_radius;
    }
    RotVector(&pMod2->atari.m_offset, &pMod2->ang, &rb);
    const f32 gap = vol_control == 1 ? 1.1f : 1.0f;
    const u8 pa = pMod->atari.m_flag & 0x18, pb = pMod2->atari.m_flag & 0x18;
    if (pa > pb || (pa == 0 && pb == 0)) {
        if (pMod->pos.x != pMod->pos_old.x) {
            const f32 ax = pMod->pos.x + ra.x, bx = pMod2->pos.x + rb.x;
            pMod2->pos.x = ax < bx ? ax + aw + bw + gap - rb.x : ax - aw - bw - gap - rb.x;
        } else if (pMod->pos.z != pMod->pos_old.z) {
            const f32 az = pMod->pos.z + ra.z, bz = pMod2->pos.z + rb.z;
            pMod2->pos.z = az > bz ? pMod->pos.z + rb.z + ad + bd + gap - rb.z : pMod->pos.z + rb.z - ad - bd - gap - rb.z;
        }
    } else if (pa != pb) {
        if (pMod->pos.x != pMod->pos_old.x) {
            const f32 ax = pMod->pos.x + ra.x, bx = pMod2->pos.x + rb.x;
            pMod->pos.x = ax > bx ? bx + bw + aw + gap - ra.x : bx - bw - aw - gap - ra.x;
        } else if (pMod->pos.z != pMod->pos_old.z) {
            const f32 az = pMod->pos.z + ra.z, bz = pMod2->pos.z + rb.z;
            pMod->pos.z = az > bz ? bz + bd + ad + gap - ra.z : bz - bd - ad - gap - ra.z;
        }
    }
    return fabsf(pMod->pos.x - posA.x) >= 1.0f || fabsf(pMod->pos.z - posA.z) >= 1.0f;
}

// A point in the box's frame (y ignored) pushed out of the box grown by rad: faces first, then the four corners.
static int sphere_box(cAtariInfo* info, Vec* p, f32 rad)
{
    const f32 rx = info->m_radius, rz = info->m_radius2;
    int hit = 0;
    if (p->z > -rz && p->z < rz) {
        if (p->x > 0.0f) {
            if (p->x < rx + rad) {
                p->x = rx + rad;
                hit = 1;
            }
        } else if (p->x > -(rx + rad)) {
            p->x = -(rx + rad);
            hit = 1;
        }
    }
    if (p->x > -rx && p->x < rx) {
        if (p->z > 0.0f) {
            if (p->z < rz + rad) {
                p->z = rz + rad;
                hit = 1;
            }
        } else if (p->z > -(rz + rad)) {
            p->z = -(rz + rad);
            hit = 1;
        }
    }
    if (hit) return 1;
    p->y = 0.0f;
    const f32 rr = rad * rad;
    static const f32 cx[4] = {1.0f, -1.0f, 1.0f, -1.0f}, cz[4] = {1.0f, 1.0f, -1.0f, -1.0f};
    static const int line[4] = {788, 797, 806, 815};
    for (int k = 0; k < 4; k++) {
        Vec corner, d;
        corner.x = cx[k] > 0.0f ? rx : -rx;
        corner.y = 0.0f;
        corner.z = cz[k] > 0.0f ? rz : -rz;
        if (GetDistance(&corner, p) < rr) {
            PSVECSubtract(p, &corner, &d);
            vol_normalize(&d, &d, &d, line[k]);
            PSVECScale(&d, &d, rad);
            PSVECAdd(&corner, &d, p);
            return 1;
        }
    }
    return 0;
}

// Cylinder body (sph) against a box body (rect): the cylinder's path since last tick, in the box's frame, in steps
// of at most its radius (radius >= 200), is pushed out of the box; the cylinder's model takes the push (XZ).
int At_em_sphere_rect_ck(cEm* sph, cEm* rect)
{
    Vec ps = sph->atari.m_Pos, pr = rect->atari.m_Pos;
    Mtx m, inv;
    Vec c, step, p, q;
    if (ps.y + sph->atari.m_height < pr.y - rect->atari.m_height) return 0;
    if (ps.y - sph->atari.m_height > pr.y + rect->atari.m_height) return 0;
    cAtariInfo* ir = &rect->atari;
    if (ir->m_parts_no != 0) {
        cModel* pm = rect->getPartsPtr(ir->m_parts_no - 1);
        PSMTXRotRad(m, 'y', pm->ang.y);
        PSMTXMultVecSR(m, &ir->m_offset, &c);
        PSVECAdd(&c, &pr, &c);
        TransMatrix(m, &c);
    } else {
        PSMTXRotRad(m, 'y', rect->ang.y);
        TransMatrix(m, &rect->pos);
        PSMTXMultVec(m, &ir->m_offset, &c);
        m[0][3] = c.x;
        m[1][3] = c.y;
        m[2][3] = c.z;
    }
    PSMTXInverse(m, inv);
    c = sph->atari.m_Pos;
    const f32 rad = sph->atari.m_radius;
    int n;
    if (!(sph->atari.m_stat & 1)) {
        PSMTXMultVec(inv, &sph->atari.m_Pos, &step);
        PSMTXMultVec(inv, &sph->atari.m_oldPos, &p);
        n = rad >= 200.0f ? (int) (GetDistance3(&step, &p) / rad) + 1 : 1;
        PSVECSubtract(&step, &p, &step);
        PSVECScale(&step, &step, 1.0f / (f32) n);
    } else {
        PSMTXMultVec(inv, &sph->atari.m_Pos, &p);
        n = 1;
        step.x = step.y = step.z = 0.0f;
    }
    int hit = 0;
    for (int i = 0; i < n && !hit; i++) {
        PSVECAdd(&p, &step, &p);
        hit = sphere_box(ir, &p, rad);
    }
    if (hit) {
        p.y = c.y;
        PSMTXMultVec(m, &p, &q);
        PSVECSubtract(&q, &c, &q);
        q.y = 0.0f;
        push_scale(&q);
        PSVECAdd(&sph->pos, &q, &sph->pos);
        sph->atari.getPos(sph, &sph->atari.m_Pos);
    }
    return hit;
}

// Cylinder against cylinder: pMod moves out by the overlap (XZ); an unranked pMod2 above pMod in memory gives 30%.
// A body's m_pMod (a carried model) moves with it.
int At_em_sphere_sphere_ck(cEm* pMod, cEm* pMod2)
{
    const Vec pa = pMod->atari.m_Pos, pb = pMod2->atari.m_Pos;
    const f32 hh = pMod->atari.m_height + pMod2->atari.m_height;
    if (pa.y < pb.y - hh) return 0;
    if (pa.y > pb.y + hh) return 0;
    Vec d;
    PSVECSubtract(&pb, &pa, &d);
    d.y = 0.0f;
    const f32 dist = RootSumSquare3(&d);
    const f32 rr = pMod->atari.m_radius2 + pMod2->atari.m_radius2;
    if (!(dist < rr)) return 0;
    if (dist < 0.1f) d.x += 0.1f;
    vol_normalize(&d, &d, &d, 869);
    PSVECScale(&d, &d, rr - dist);
    push_scale(&d);
    PSVECSubtract(&pMod->pos, &d, &pMod->pos);
    pMod->atari.getPos(pMod, &pMod->atari.m_Pos);
    if (cModel* m = pMod->atari.m_pMod) {
        PSVECSubtract(&m->pos, &d, &m->pos);
        ((cEm*) m)->atari.getPos(m, &((cEm*) m)->atari.m_Pos);
    }
    if ((pMod2->atari.m_flag & 0x18) == 0 && (u32) pMod2 > (u32) pMod) {
        PSVECScale(&d, &d, 0.3f);
        PSVECAdd(&pMod2->pos, &d, &pMod2->pos);
        pMod2->atari.getPos(pMod2, &pMod2->atari.m_Pos);
        if (cModel* m = pMod2->atari.m_pMod) {
            PSVECAdd(&m->pos, &d, &m->pos);
            ((cEm*) m)->atari.getPos(m, &((cEm*) m)->atari.m_Pos);
        }
    }
    return 1;
}

// ==== line tests against the bodies (at_mod.cpp) ====

// Nearest body hit by the segment pos0 -> pos1 among the characters (Leon only with flag 4).
int EmHitCheck(Vec* hit, Vec* nrm, Vec* pos0, Vec* pos1, int flag)
{
    vol_cnt.line_tests++;
    Vec h, n;
    f32 dist = 100000.0f;
    int ret = 0;
    if (hit != 0) *hit = *pos1;
    for (cEm* m = EmMgr.pAlive; m != 0; m = (cEm*) m->pNext) {
        if (!(m->atari.m_flag & 0x200)) continue;
        if (!(flag & 4) && m == pPL) continue;
        if (ComnHitCheck(&h, &n, m, pos0, pos1, flag) == 0) continue;
        const f32 d = GetDistance3(pos0, &h);
        if (d < dist) {
            dist = d;
            if (hit != 0) *hit = h;
            if (nrm != 0) *nrm = n;
            ret = 1;
        }
    }
    if (ret) vol_cnt.line_hits++;
    return ret;
}

// Nearest body hit among the objects that are on and solid (be_flag 0x201 == 1), the weapon (id 2) excepted.
int ObjHitCheck(Vec* hit, Vec* nrm, Vec* pos0, Vec* pos1, int flag)
{
    vol_cnt.line_tests++;
    Vec h, n;
    f32 dist = 10000000000.0f;
    int ret = 0;
    if (hit != 0) *hit = *pos1;
    for (cObj* o = ObjMgr.pAlive; o != 0; o = (cObj*) o->pNext) {
        if ((o->be_flag & 0x201) != 1) continue;
        if (o->id == 2) continue;
        if (ComnHitCheck(&h, &n, (cEm*) o, pos0, pos1, flag) == 0) continue;
        const f32 d = (pos0->x - h.x) * (pos0->x - h.x) + (pos0->y - h.y) * (pos0->y - h.y) + (pos0->z - h.z) * (pos0->z - h.z);
        if (d < dist) {
            dist = d;
            if (hit != 0) *hit = h;
            if (nrm != 0) *nrm = n;
            ret = 1;
        }
    }
    if (ret) vol_cnt.line_hits++;
    return ret;
}

// One body: a box body (flag 2) only with flag 1, against its part's (or model's) matrix; a cylinder only with flag 2.
int ComnHitCheck(Vec* hit, Vec* nrm, cEm* m, Vec* pos0, Vec* pos1, int flag)
{
    vol_cnt.line_bodies++;
    if (m->atari.m_flag & 2) {
        if (!(flag & 1)) return 0;
        Mtx mat;
        if (m->atari.m_parts_no > 0)
            PSMTXCopy(m->getPartsPtr(m->atari.m_parts_no - 1)->mat, mat);
        else
            PSMTXCopy(m->mat, mat);
        if (emLineCubeCrossCk(pos0, pos1, mat, m->atari.m_radius, m->atari.m_height, m->atari.m_radius2, &m->atari.m_offset, hit))
            return 1;
    } else if ((flag & 2) || vol_control == 2) {
        if (ObaLineHitChk(m, &m->atari, pos0, pos1, hit, nrm)) return 1;
    }
    if (hit != 0) *hit = *pos1;
    return 0;
}

void DrawOba(cEm*) { vol_cnt.debug_draws++; }

// The segment a -> b against the body's capsule (its axis offset -> offset + height in the part's or model's matrix,
// radius 0.75 of the body's): closest points of the two segments; on a hit, the entry point and the XZ normal.
int ObaLineHitChk(cEm* m, cAtariInfo* info, Vec* a, Vec* b, Vec* hit, Vec* nrm)
{
    Vec p0 = info->m_offset, p1 = info->m_offset;
    p0.y += info->m_height;
    cModel* pm = info->m_parts_no != 0 ? m->getPartsPtr(info->m_parts_no - 1) : m;
    const f32 rad = info->m_radius * 0.75f;
    Vec w0, w1, d, e, f, g, h, q, r, n;
    PSMTXMultVec(pm->mat, &p0, &w0);
    PSMTXMultVec(pm->mat, &p1, &w1);
    PSVECSubtract(&w1, &w0, &d);
    PSVECSubtract(b, a, &e);
    PSVECSubtract(a, &w0, &f);
    const f32 dd = PSVECSquareMag(&d);
    const f32 ee = PSVECSquareMag(&e);
    const f32 df = PSVECDotProduct(&d, &f);
    const f32 ef = PSVECDotProduct(&e, &f);
    const f32 de = PSVECDotProduct(&d, &e);
    const f32 den = dd * ee - de * de;
    const f32 t = (ee * df - de * ef) / den;
    f32 s = (de * df - dd * ef) / den;
    const f32 tc = t < 0.0f ? 0.0f : (t > 1.0f ? 1.0f : t);
    s = s < 0.0f ? 0.0f : (s > 1.0f ? 1.0f : s);
    PSVECScale(&w0, &g, 1.0f - tc);
    const f32 rr = rad * rad;
    PSVECScale(&w1, &h, tc);
    PSVECAdd(&g, &h, &q);
    PSVECScale(a, &g, 1.0f - s);
    PSVECScale(b, &h, s);
    PSVECAdd(&g, &h, &r);
    if (!(PSVECSquareDistance(&q, &r) <= rr)) return 0;
    PSVECSubtract(&q, &r, &n);
    const f32 mag = PSVECMag(&n);
    const f32 depth = SQRTF(rr - mag * mag);
    vol_normalize(&e, &e, &n, 1434);   // the original tests e and zeroes n
    PSVECScale(&n, &n, -depth);
    PSVECAdd(&r, &n, hit);
    PSVECSubtract(hit, &p1, nrm);
    nrm->y = 0.0f;
    vol_normalize(nrm, nrm, nrm, 1440);
    return 1;
}

// ==== geometry predicates (at_sub.cpp) ====

f32 At_surface_point_rel(Vec* a, Vec* n, Vec* p)
{
    return PSVECDotProduct(n, p) - PSVECDotProduct(n, a);
}

int At_surface_line_ck(Vec* out, Vec* a, Vec* n, Vec* point1, Vec* point2)
{
    const f32 d0 = At_surface_point_rel(a, n, point1);
    const f32 d1 = At_surface_point_rel(a, n, point2);
    if (d0 * d1 < 0.0f) {
        const f32 a0 = fabsf(d0), a1 = fabsf(d1);
        InterVectorXYZ(out, point1, point2, a1 / (a0 + a1));
        return 1;
    }
    if (out) *out = *point2;
    return 0;
}

int At_poly_point_rel(Vec* poly, Vec* nrm, Vec* p)
{
    static const int next[3] = {1, 2, 0};
    for (int i = 0; i < 3; i++) {
        Vec a, b, c;
        PSVECSubtract(&poly[next[i]], &poly[i], &a);
        PSVECSubtract(p, &poly[i], &b);
        PSVECCrossProduct(&a, &b, &c);
        if (PSVECDotProduct(&c, nrm) < 0.0f) return 0;
    }
    return 1;
}

void Get_normal(Vec* tri, Vec* out)
{
    Vec a, b;
    PSVECSubtract(&tri[2], &tri[0], &a);
    PSVECSubtract(&tri[1], &tri[0], &b);
    PSVECCrossProduct(&a, &b, out);
    PSVECNormalize(out, out);
}

// The sphere (p, r) against the box of eight corners: no face plane has the centre further than r outside.
int At_box_sphere_ck(Vec* box, Vec* p, f32 r)
{
    static const int face[6][3] = {{0, 2, 1}, {4, 5, 6}, {2, 6, 3}, {0, 1, 4}, {1, 3, 5}, {2, 0, 6}};
    vol_cnt.box_sphere++;
    for (int i = 0; i < 6; i++) {
        Vec tri[3], n;
        tri[0] = box[face[i][0]];
        tri[1] = box[face[i][1]];
        tri[2] = box[face[i][2]];
        Get_normal(tri, &n);
        if (PSVECDotProduct(&n, p) - PSVECDotProduct(&n, &tri[0]) > r) return 0;
    }
    return 1;
}

// A capsule as spheres along its axis, at most 2r apart: against a box (corners) ...
u32 AtBoxCapsuleCk3(Vec* box, Vec* p0, f32 r, Vec* p1)
{
    vol_cnt.capsule_tests++;
    if (At_box_sphere_ck(box, p0, r)) return 1;
    if (At_box_sphere_ck(box, p1, r)) return 1;
    Vec dir, p;
    PSVECSubtract(p0, p1, &dir);
    f32 len = RootSumSquare3(&dir);
    u32 n = (u32) (len / (r + r)) + 2;
    len = len / (f32) n;
    if (len < 0.01f) return 0;
    vol_normalize(&dir, &dir, &dir, 301);
    PSVECScale(&dir, &dir, len);
    p = *p1;
    for (n--; n-- != 0;) {
        PSVECAdd(&p, &dir, &p);
        if (At_box_sphere_ck(box, &p, r)) return 1;
    }
    return 0;
}

// ... and against a sphere (c, r): the capsule's spheres of radius r2 (r2 < 0.01: its two ends and one more).
u32 AtSphereCapsuleCk(Vec* c, Vec* p0, f32 r, f32 r2, Vec* p1)
{
    vol_cnt.capsule_tests++;
    const f32 rr = (r + r2) * (r + r2);
    if (sq_dist(c, p0) < rr) return 1;
    if (sq_dist(c, p1) < rr) return 1;
    Vec dir, p;
    PSVECSubtract(p0, p1, &dir);
    f32 len = RootSumSquare3(&dir);
    u32 n = (u32) (len / (r2 + r2)) + 2;
    len = len / (f32) n;
    if (len < 0.01f) return 0;
    vol_normalize(&dir, &dir, &dir, 366);
    PSVECScale(&dir, &dir, len);
    if (r2 < 0.01f) n = 2;
    p = *p1;
    for (n--; n-- != 0;) {
        PSVECAdd(&p, &dir, &p);
        if (sq_dist(c, &p) < rr) return 1;
    }
    return 0;
}

void AtCapsuleDisp(Vec*, Vec*, f32, u32) { vol_cnt.debug_draws++; }
void AtCubeDisp(Mtx, f32, f32, f32, Vec*, u32) { vol_cnt.debug_draws++; }

u32 Get_poly_attr(AtPoly* poly)
{
    return (poly->attrHi << 16) | poly->attrLo;
}

// The polygon classes a query's flag (and the scenario-effect mode SEck) skips; 1 when the attribute passes.
static int attr_pass(u32 attr, u32 flag, u32 mask, bool sphere)
{
    if (SEck == 0) {
        if ((flag & 0x1000) && (attr & 0x400000)) return 0;
        if ((flag & 0x2000) && (attr & 0x4000)) return 0;
        if ((flag & 0x4000) && (attr & 0x40)) return 0;
        if ((attr & 0x400) && !(flag & 0x8000)) return 0;
        if (sphere) {
            if ((flag & 0x8000) && (attr & 0x800000)) return 0;
            if ((flag & 0x800) && (attr & 0x8000)) return 0;
        } else {
            if ((flag & 0x800) && (attr & 0x8000)) return 0;
            if ((flag & 0x8000) && (attr & 0x800000)) return 0;
        }
    } else {
        if ((flag & 0x400) && (attr & 0x4000)) return 0;
        if ((flag & 0x800) && (attr & 0x400000)) return 0;
    }
    return (mask & attr) ? 0 : 1;
}

// The segment against one collision triangle (plane, three edges, the crossing): its attribute | 0x01000000, or 0.
u32 At_poly_line_ck(AtPolyData* pd, Vec* out, AtPoly* poly, Vec* vert0, Vec* vert1, u32 flag, u32 mask)
{
    Vec d0, d1, c, a, b;
    Vec* vtx = pd->vtx;
    Vec* v0 = &vtx[poly->v[0]];
    Vec* nrm = &pd->nrm[poly->n];
    d0.x = vert0->x - v0->x;
    d0.y = vert0->y - v0->y;
    d0.z = vert0->z - v0->z;
    d1.x = vert1->x - v0->x;
    d1.y = vert1->y - v0->y;
    d1.z = vert1->z - v0->z;
    f32 dp0 = d0.x * nrm->x + d0.y * nrm->y;
    dp0 += d0.z * nrm->z;
    f32 dp1 = d1.x * nrm->x + d1.y * nrm->y;
    dp1 += d1.z * nrm->z;
    if (dp0 * dp1 > 0.0f) return 0;
    PSVECSubtract(vert1, vert0, &a);
    for (int k = 0; k < 3; k++) {
        PSVECSubtract(vert0, &vtx[poly->v[k]], &b);
        PSVECCrossProduct(&pd->edge[poly->e[k]], &a, &c);
        if (PSVECDotProduct(&c, &b) < 0.0f) return 0;
    }
    const f32 t = -dp0 / PSVECDotProduct(&a, nrm);
    if (t >= 1.0f || t < 0.0f) return 0;
    const f32 s0 = PSVECDotProduct(nrm, vert0) - PSVECDotProduct(nrm, v0);
    const f32 s1 = PSVECDotProduct(nrm, vert1) - PSVECDotProduct(nrm, v0);
    if (s0 * s1 < 0.0f) {
        const f32 a0 = fabsf(s0), a1 = fabsf(s1);
        InterVectorXYZ(out, vert0, vert1, a1 / (a0 + a1));
    } else if (out) {
        *out = *vert1;
    }
    const u32 attr = Get_poly_attr(poly);
    return attr_pass(attr, flag, mask, false) ? attr | 0x01000000 : 0;
}

u32 At_poly_sphere_ck(AtPolyData* pd, AtPoly* poly, Vec* oldPos, Vec* pos, f32 r, u32 flag, u32 mask)
{
    Vec tri[3], n;
    for (int k = 0; k < 3; k++) tri[k] = pd->vtx[poly->v[k]];
    n = pd->nrm[poly->n];
    return At_poly_sphere_ck2(tri, &n, Get_poly_attr(poly), oldPos, pos, r, flag, mask);
}

// The swept sphere against a front-facing triangle: 1 a face contact (pushed along the normal), 2 a rim contact
// (pushed from the nearest edge point), 0 none; *pos adjusted in place.
u32 At_poly_sphere_ck2(Vec* tri, Vec* n, u32 attr, Vec* oldPos, Vec* pos, f32 r, u32 flag, u32 mask)
{
    Vec hp, nn;
    u32 hit;
    if (PSVECDotProduct(n, oldPos) - PSVECDotProduct(n, tri) < 0.0f) return 0;
    const f32 d = PSVECDotProduct(n, pos) - PSVECDotProduct(n, tri);
    if (fabsf(d) > r) {
        hit = 0;
        if (At_surface_line_ck(&hp, tri, n, oldPos, pos)) {
            nn = *n;
            Vec hp2 = hp;
            if (At_poly_point_rel(tri, &nn, &hp2)) hit = 1;
        }
    } else {
        PSVECScale(n, &hp, d);
        PSVECSubtract(pos, &hp, &hp);
        nn = *n;
        Vec hp2 = hp;
        if (At_poly_point_rel(tri, &nn, &hp2)) {
            hit = 1;
        } else if (flag & 0x20) {
            hit = 0;
        } else {
            hit = 0;
            for (u32 i = 0; i < 3; i++) {
                Vec v;
                if (attr & (1 << (i + 29))) continue;
                PSVECSubtract(&tri[(i + 1) % 3], &tri[i], &v);
                PSVECSubtract(pos, &tri[i], &nn);
                const f32 len = PSVECSquareMag(&v);
                const f32 dot = PSVECDotProduct(&nn, &v);
                if (dot < 0.01f) continue;
                if (len < dot) continue;
                PSVECScale(&v, &hp, dot / len);
                PSVECAdd(&hp, &tri[i], &hp);
                if (PSVECSquareDistance(pos, &hp) < r * r) {
                    hit = 2;
                    break;
                }
            }
        }
    }
    if (hit != 0 && !attr_pass(attr, flag, mask, true)) hit = 0;
    if (hit == 1) {
        PSVECScale(n, &nn, r);
        PSVECAdd(&hp, &nn, pos);
    } else if (hit == 2) {
        PSVECSubtract(pos, &hp, &nn);
        if (PSVECDotProduct(&nn, n) > 0.0f) {
            PSVECNormalize(&nn, &nn);
            PSVECScale(&nn, &nn, r * 0.99f);
            PSVECAdd(&hp, &nn, pos);
        }
    }
    return hit;
}

// 1 when p is inside the XZ quad rect[0..3] (edge tests from corners 0 and 2).
int At_rect_point_ck(Vec* rect, Vec* p)
{
    const f32 px = p->x, pz = p->z;
    const f32 x1 = rect[1].x, z1 = rect[1].z, x3 = rect[3].x, z3 = rect[3].z;
    f32 x0 = rect[0].x, z0 = rect[0].z;
    f32 dx = px - x0, dz = pz - z0;
    f32 ex1 = x1 - x0, ez1 = z1 - z0, ex3 = x3 - x0, ez3 = z3 - z0;
    if (ex1 * dz > ez1 * dx || ex3 * dz < ez3 * dx) return 0;
    x0 = rect[2].x;
    z0 = rect[2].z;
    dx = px - x0;
    dz = pz - z0;
    ex1 = x1 - x0;
    ez1 = z1 - z0;
    ex3 = x3 - x0;
    ez3 = z3 - z0;
    if (ex1 * dz < ez1 * dx || ex3 * dz > ez3 * dx) return 0;
    return 1;
}

// Two XZ quads overlap: a corner of one inside the other, or ra's centre inside rb.
int At_rect_rect_ck(Vec* ra, Vec* rb)
{
    for (int i = 0; i < 4; i++)
        if (At_rect_point_ck(ra, &rb[i])) return 1;
    for (int i = 0; i < 4; i++)
        if (At_rect_point_ck(rb, &ra[i])) return 1;
    Vec c;
    c.x = c.y = c.z = 0.0f;
    for (int i = 0; i < 4; i++) PSVECAdd(&c, ra, &c);   // the original adds corner 0 four times
    PSVECScale(&c, &c, 0.25f);
    return At_rect_point_ck(rb, &c) ? 1 : 0;
}

// Quadrant of a relative angle: 0 front (within 45 degrees), 1 left, 3 right, 2 behind.
int Get_ang_dir(f32 ang)
{
    if (ang > 2.3561945f || ang < -2.3561945f) return 2;
    if (ang > 0.78539819f) return 1;
    return ang < -0.78539819f ? 3 : 0;
}

void InterVectorXYZ(Vec* out, Vec* a, Vec* b, f32 t)
{
    Vec tmp;
    const f32 s = 1.0f - t;
    PSVECScale(a, &tmp, t);
    PSVECScale(b, out, s);
    PSVECAdd(out, &tmp, out);
}

int EatGetEffectType(u32 attr)
{
    int type = 0;
    if (attr & 0x800000) type = 1;
    if (attr & 0x8000) type += 2;
    if (attr & 0x80) type += 4;
    return type;
}
