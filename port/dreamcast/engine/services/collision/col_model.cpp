// col_model.cpp: the native per-model collision response (lane eng-svc4; docs/engine/SERVICES.md section 24).
//
// The layer above the native query cores (col.cpp: hitCheck, hitCheck2, polySphereCk on the baked ColPiece tables):
//   - check / checkAir: a model's bodies (its cAtariInfo and the chain behind m_pList) against the scenery, or the
//     box body's twelve probe lines (checkRect, atck);
//   - scrAtCheckSphere(Air): one body's swept sphere from last tick's centre to this tick's, slid along the walls
//     (wallAdjust), the push applied to every bone (at_pos_calc, native in skel.cpp), then the floor snap (getFloor)
//     for the model and the model it carries (m_pMod);
//   - wallAdjust / adjust: the line test, the swept sphere twice (walls then floors), the line test again;
//   - getFloor: the floor under a point (a vertical hitCheck2), -100000 when none;
//   - the collision piece's set-up from its file (cSat::init, operator=, setCoord, blockInit; cSatMgr::create and
//     destroy) and the room's surface-effect table (cEatMgr).
// Arithmetic: the original's, in its order (contraction off), so the PC reference compares bit for bit. Debug lines
// and spheres are counted, not drawn. The piece pool itself (cManager<cSat>: slot allocation) is still the original
// manager template: the engine's table service replaces it with the other managers (SERVICES.md section 24).
#include "atari.h"
#include "at_sub.h"
#include "em.h"
#include "global.h"
#include "math_sub.h"
#include "main.h"
#include "col_model.h"

extern "C" {
ColModelCounters colm_cnt;
int colm_control;
}
void at_pos_calc(cModel* m, Vec* vec);

namespace {
inline bool in_arena(const void* p) { return (u32) p >= 0x8C000000 && (u32) p <= 0x8CFFFFFF; }
}

// ==== per-model response ====

int cSatMgr::check(cModel* m, int flag)
{
    colm_cnt.checks++;
    cAtariInfo* info = &((cEm*) m)->atari;
    if (!(info->m_flag & 0x100)) return 0;
    if (info->m_flag & 2) return checkRect(m);
    int ret = 0;
    while (info->m_pList) {
        info = info->m_pList;
        if (scrAtCheckSphere(m, info, flag) != 0.0f) ret = 1;
    }
    if (scrAtCheckSphere(m, &((cEm*) m)->atari, flag) != 0.0f) ret = 1;
    return ret;
}

int cSatMgr::checkAir(cModel* m, int flag)
{
    colm_cnt.checks++;
    cAtariInfo* info = &((cEm*) m)->atari;
    int ret = 0;
    if (info->m_flag & 0x100) {
        while (info->m_pList) {
            info = info->m_pList;
            if (scrAtCheckSphereAir(m, info, flag) != 0.0f) ret = 1;
        }
        if (scrAtCheckSphereAir(m, &((cEm*) m)->atari, flag) != 0.0f) ret = 1;
    }
    return ret;
}

f32 cSatMgr::getFloor(Vec* pos, f32 up, f32 down, u32* attr, int flag)
{
    colm_cnt.floors++;
    if (pG->Debug_flg[1] & 0x10000000) return 0.0f;
    Vec top, bottom, hit;
    top.x = pos->x;
    top.y = pos->y + up;
    top.z = pos->z;
    bottom.x = pos->x;
    bottom.y = pos->y - down;
    bottom.z = pos->z;
    if (hitCheck2(&top, &bottom, &hit, attr, 0x40, flag) == 0) return -100000.0f;
    return hit.y;
}

// One probe line of a box body (a -> b in the body's frame, 300 above the model): a wall hit moves the model back
// to the hit point plus the wall normal. 1 when it moved a unit or more.
int atck(Vec* vec0, Vec* vec1, cAtariInfo* info, cModel* m, int flag)
{
    Vec v0, v1, hit, nrm;
    PSVECAdd(vec0, &info->m_offset, &v0);
    PSVECAdd(vec1, &info->m_offset, &v1);
    RotVector(&v0, &m->ang, &v0);
    RotVector(&v1, &m->ang, &v1);
    PSVECAdd(&v0, &m->pos, &v0);
    PSVECAdd(&v1, &m->pos, &v1);
    v0.y = v1.y = m->pos.y + 300.0f;
    if (!SatMgr.hitCheck(&v0, &v1, &hit, &nrm, flag, 0)) return 0;
    const Vec old = m->pos;
    PSVECSubtract(&hit, &v1, &v1);
    PSVECAdd(&m->pos, &v1, &m->pos);
    PSVECAdd(&m->pos, &nrm, &m->pos);
    return fabsf(m->pos.x - old.x) >= 1.0f || fabsf(m->pos.z - old.z) >= 1.0f;
}

// A box body: twelve probes, three a side (the middle and 0.9 of the half-size either way), from the centre line out.
int cSatMgr::checkRect(cModel* m)
{
    colm_cnt.rects++;
    cAtariInfo* info = &((cEm*) m)->atari;
    const f32 rx = info->m_radius, rz = info->m_radius2;
    // {a.x, a.z, b.x, b.z} in the original's order
    const f32 probe[12][4] = {
        {0.0f, rz * 0.9f, rx, rz * 0.9f},   {0.0f, 0.0f, rx, 0.0f},   {0.0f, -rz * 0.9f, rx, -rz * 0.9f},
        {0.0f, rz * 0.9f, -rx, rz * 0.9f},  {0.0f, 0.0f, -rx, 0.0f},  {0.0f, -rz * 0.9f, -rx, -rz * 0.9f},
        {rx * 0.9f, 0.0f, rx * 0.9f, rz},   {0.0f, 0.0f, 0.0f, rz},   {-rx * 0.9f, 0.0f, -rx * 0.9f, rz},
        {rx * 0.9f, 0.0f, rx * 0.9f, -rz},  {0.0f, 0.0f, 0.0f, -rz},  {-rx * 0.9f, 0.0f, -rx * 0.9f, -rz},
    };
    int ret = 0;
    for (int i = 0; i < 12; i++) {
        Vec a, b;
        a.x = probe[i][0];
        a.y = 0.0f;
        a.z = probe[i][1];
        b.x = probe[i][2];
        b.y = 0.0f;
        b.z = probe[i][3];
        ret |= atck(&a, &b, info, m, 0);
    }
    return ret;
}

// The floor snap of scrAtCheckSphere: within 1000 units the model stands on the floor.
static void snap_floor(cSatMgr* s, cModel* m, int flag, bool report)
{
    const f32 floor = s->getFloor(&m->pos, 600.0f, 100000.0f, (u32*) &m->pFloor_norm, flag);
    if (fabsf(floor - m->pos.y) < 1000.0f) {
        m->pos.y = colm_control == 1 ? floor + 0.5f : floor;
        return;
    }
    if (!report || pG->shooting_mode != 0) return;
    const f32 x = (f32) ((int) m->pos.x / 100) * 100.0f;
    const f32 y = (f32) ((int) m->pos.y / 100) * 100.0f;
    const f32 z = (f32) ((int) m->pos.z / 100) * 100.0f;
    colm_cnt.floor_lost++;
    if (floor == -100000.0f)
        pLog->warn(6, 1, "FLOOR LOST %.0f %.0f %.0f", x, y, z);
    else
        pLog->warn(4, 2, "FLOOR ERR %.0f %.0f %.0f", x, y, z);
    if (pG->debug_mode != 0) colm_cnt.debug_draws++;
}

// One body on the ground: the swept sphere slid along the walls; the push moves every bone; the floor snap.
f32 cSatMgr::scrAtCheckSphere(cModel* m, cAtariInfo* info, int flag)
{
    colm_cnt.spheres++;
    Vec pos, oldPos, newPos;
    info->getSpeedVector(m, &oldPos, &pos);
    m->Wall_norm.x = 0.0f;
    m->Wall_norm.y = 0.0f;
    m->Wall_norm.z = 0.0f;
    newPos = pos;
    wallAdjust(&m->Wall_norm, &oldPos, &newPos, colm_control == 2 ? info->m_radius * 1.1f : info->m_radius, info->m_flag, flag);
    PSVECSubtract(&newPos, &pos, &pos);
    const f32 mag = PSVECMag(&pos);
    at_pos_calc(m, &pos);
    if (!(info->m_flag & 4)) snap_floor(this, m, flag, true);
    if (cModel* link = info->m_pMod) {
        at_pos_calc(link, &pos);
        if (!(((cEm*) link)->atari.m_flag & 4)) snap_floor(this, link, flag, false);
    }
    if (pG->Debug_flg[2] & 0x20000000) colm_cnt.debug_draws++;
    return mag;
}

// One body in the air: the same slide, the push in XZ only (the height is the behaviour's), the carried model along.
f32 cSatMgr::scrAtCheckSphereAir(cModel* m, cAtariInfo* info, int flag)
{
    if (!(info->m_flag & 0x100)) return 0.0f;
    colm_cnt.spheres++;
    Vec pos, oldPos, newPos;
    Vec mpos = m->pos;
    info->getSpeedVector(m, &oldPos, &pos);
    m->Wall_norm.x = 0.0f;
    m->Wall_norm.y = 0.0f;
    m->Wall_norm.z = 0.0f;
    newPos = pos;
    wallAdjust(&m->Wall_norm, &oldPos, &newPos, info->m_radius, ((cEm*) m)->atari.m_flag, flag);
    PSVECSubtract(&newPos, &pos, &pos);
    const f32 mag = PSVECMag(&pos);
    at_pos_calc(m, &pos);
    const f32 y = m->pos.y;
    PSVECAdd(&m->pos, &pos, &m->pos);
    m->pos.y = y;
    if (cModel* link = info->m_pMod) {
        PSVECSubtract(&m->pos, &mpos, &mpos);
        PSVECAdd(&link->pos, &mpos, &link->pos);
    }
    if (pG->Debug_flg[2] & 0x20000000) colm_cnt.debug_draws++;
    return mag;
}

// The line oldPos -> pos against the walls (flag bit 0), the swept sphere (walls 0xA0, then 0x80), the line again.
// adjust() is the same with one sphere pass under the caller's flag.
static void slide(cSatMgr* s, Vec* nrm, Vec* oldPos, Vec* pos, f32 r, int flag, int mask, bool two)
{
    Vec hit, tmp, n, d, p0;
    colm_cnt.slides++;
    if ((flag & 1) && s->hitCheck(oldPos, pos, &hit, &n, flag, mask)) {
        PSVECScale(&n, &tmp, r);
        PSVECAdd(&hit, &tmp, pos);
        if (nrm) *nrm = n;
    }
    PSVECSubtract(pos, oldPos, &d);
    p0 = *oldPos;
    PSVECAdd(oldPos, &d, pos);
    if (two) {
        s->polySphereCk(&p0, pos, r, flag | 0xA0, nrm, mask);
        s->polySphereCk(&p0, pos, r, flag | 0x80, nrm, mask);
    } else {
        s->polySphereCk(&p0, pos, r, flag, nrm, mask);
    }
    if ((flag & 1) && s->hitCheck(oldPos, pos, &hit, &n, flag, mask)) {
        PSVECScale(&n, &tmp, r);
        PSVECAdd(&hit, &tmp, pos);
        if (nrm) *nrm = n;
    }
}

void cSatMgr::wallAdjust(Vec* nrm, Vec* oldPos, Vec* pos, f32 r, int flag, int mask)
{
    slide(this, nrm, oldPos, pos, r, flag, mask, true);
}

void cSatMgr::adjust(Vec* nrm, Vec* oldPos, Vec* pos, f32 r, int flag, int mask)
{
    slide(this, nrm, oldPos, pos, r, flag, mask, false);
}

// ==== the collision piece from its file ====

cSat* cSatMgr::create(void* data, int flag, Vec* pos, Vec* rot, u8 type)
{
    cSat* sat = cManager<cSat>::create();
    cSatHeader* hdr = (cSatHeader*) data;
    if (!in_arena(sat)) return 0;
    sat->x5C = 0;
    if (hdr->m_Version != 0xFF && (hdr->m_Version & 0x80)) data = hdr->getSat(type);
    sat->init((cSatFile*) data, pos ? pos : (Vec*) &vecZero, rot ? rot : (Vec*) &vecZero);
    colm_cnt.pieces++;
    return sat;
}

void cSatMgr::destroy(cSat* p)
{
    if (!in_arena(p)) {
        pLog->err(0, 0, "cSatMgr::destroy() PTR ERR 0x%08x", p);
        return;
    }
    if (p->m_Flag & 2) Mem_free(p->pFile);
    cManager<cSat>::destroy(p);
}

void cSat::init(cSatFile* f, Vec* pos, Vec* rot)
{
    if (!in_arena(f)) {
        pLog->err(0, 0, "cSat::init() PTR ERR %08X", f);
        return;
    }
    if (!f->dataCheck()) pLog->err(0, 0, "ATARI DATA ERROR 0x%08x", f);
    m_Flag = 4;
    *this = f;
    setCoord(pos, rot);
    blockInit(block_p);
}

// The file's block tree: child and next links are offsets in the file; turned into pointers once (a block whose
// next is already a pointer has been done).
void cSat::blockInit(cSatBlock* blk)
{
    if (!in_arena(blk)) {
        pLog->err(0, 0, "cSat::blockInit() INVALID PTR 0x%08x", blk);
        return;
    }
    if (in_arena(blk->next)) return;
    do {
        if (blk->m_Flag & 1) blockInit((cSatBlock*) blk->idx);
        const u32 ofs = (u32) blk->next;
        if (ofs != 0) {
            cSatBlock* p = (cSatBlock*) ((u8*) blk + ofs);
            if (p != 0 && !in_arena(p)) {
                pLog->err(0, 0, "cSat::blockInit() INVALID PTR 0x%08x ( %08x )", p, ofs);
                return;
            }
            blk->next = p;
        }
        blk = blk->next;
    } while (blk);
}

// The file's tables, one after the other: vertices, normals, edges, polygons, blocks.
cSat& cSat::operator=(cSatFile* f)
{
    vertex_num = f->m_nVertex;
    polygon_num = f->m_nPolygon;
    normal_num = f->m_nNormal;
    nEdge = f->m_nEdge;
    floor_num = f->m_nFloor;
    slope_num = f->m_nSlope;
    wall_num = f->m_nWall;
    bb_num = f->m_nBlock;
    Vec* v = f->getVertexPtr();
    pFile = f;
    x5C = 0;
    vtx = v;
    norm_p = v + vertex_num;
    edge_p = norm_p + normal_num;
    poly_p = (AtPoly*) (edge_p + nEdge);
    block_p = (cSatBlock*) (poly_p + polygon_num);
    return *this;
}

void cSat::setCoord(Vec* pos, Vec* rot)
{
    RotMatrix(mat, rot);
    TransMatrix(mat, pos);
    PSMTXInverse(mat, imat);
}

// ==== the room's surface-effect table (eight surface types; 0xD2: no effect) ====

void cEatMgr::initEffInfo()
{
    for (int i = 0; i < 8; i++) {
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

AtEffInfo* cEatMgr::getEffInfo(int type)
{
    return effOn[type] != 0 ? &effInfo[type] : 0;
}

void cEatMgr::registEffInfo(int type, AtEffInfo* src)
{
    effOn[type] = 1;
    effInfo[type].flag = src->flag;
    const bool all = src->eff0[1] == 1;
#define EFF(f)                                       \
    if (src->f[0] != 0xD2 || all) {                  \
        effInfo[type].f[0] = src->f[0];              \
        effInfo[type].f[1] = src->f[1];              \
    }
    EFF(eff0) EFF(eff13) EFF(eff16) EFF(eff17) EFF(effGun) EFF(eff5) EFF(eff6) EFF(eff0D)
#undef EFF
}
