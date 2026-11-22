// Native collision queries (lane eng-svc). Tables and the reasons for them: col.h, docs/engine/SERVICES.md.
//
// Replaced (engine bodies here; the originals in game/atari.cpp are not used): cSatMgr::hitCheck2 (the line query:
// floors, walls, the camera, line of sight), cSatMgr::hitCheck (the same with the hit normal in world space) and
// cSatMgr::polySphereCk (the swept sphere pushed out of the polygons). Everything above them in atari.cpp (check,
// checkAir, scrAtCheckSphere, wallAdjust, adjust, getFloor, atck) stays original and calls these.
//
// Each query walks the piece's flattened block tree (one sweep over SoA box rows; a failed box test jumps over the
// subtree) and tests the leaf's triangles from one contiguous run of 96-byte records. Same tests, same operations
// in the same order, same walk order and the same per-query polygon dedupe as the original: the results (hit or
// miss, attribute, normal pointer, hit point, pushed position) are the original's.
#include "col.h"
#include "atari.h"
#include "global.h"
#include "db_log.h"
#include "math_sub.h"
#include "svc_prof.h"

extern "C" void* memset(void* dst, int c, unsigned int n);
extern "C" void* memcpy(void* dst, const void* src, unsigned int n);
extern "C" void* svc_pool_carve_room(u32 bytes);   // host: the room carve (lane eng-skel1: given back when the room is left)
extern "C" u32 svc_pool_room_reset(void* keep);
extern "C" const char* svc_env(const char* name) __attribute__((weak));
extern "C" void host_log(const char* fmt, ...) __attribute__((weak));   // host: room-lifetime engine memory (the skeleton pool's sibling)
f32 GetDistance(Vec* v0, Vec* v1);
void InterVectorXYZ(Vec* out, Vec* a, Vec* b, f32 t);

#ifndef COL_MASK_MIN
#define COL_MASK_MIN 8   // lane eng-svc3: leaves with fewer list entries are tested whole (SERVICES.md section 18)
#endif
extern "C" {
ColCounters col_cnt;
f32 col_control_floor;
int col_control_grid;
int col_verify;
int col_grid_off;
int col_sphere_grid_off;
u32 col_mask_min = COL_MASK_MIN;
}
// how much a polygon's box and a query's box grow before their cells are taken (units): far above the rounding of
// the line test's arithmetic at room coordinates (a float step at 65,536 units is 0.008)
constexpr f32 kColMargin = 1.0f;

#define VALID_PTR(p) ((u32) (p) >= RE4_MEM_LO && (u32) (p) <= RE4_MEM_HI)

namespace {

constexpr u32 kMaxPieces = 32;
ColPiece* g_piece[kMaxPieces];
u32 g_npiece;
u8 g_bits[0x400];      // per-query dedupe, one bit per polygon (the original's polyBit)
cSat* g_bypass;        // the piece the last hitCheck2 hit (hitCheck's normal transform)

u32 align32(u32 x) { return (x + 31u) & ~31u; }

// ---- bake: the piece's block tree and polygons into the tables (room load) ----
struct BakeCount {
    u32 nodes, leaves, idx, masked;   // masked: the list entries of leaves with at least col_mask_min entries
};
void count_tree(cSatBlock* blk, BakeCount* c)
{
    for (; blk; blk = blk->next) {
        c->nodes++;
        if (blk->m_Flag & 1) {
            count_tree((cSatBlock*) blk->idx, c);
        } else {
            c->leaves++;
            const u32 all = blk->m_nFloor + blk->m_nSlope + blk->m_nWall;
            c->idx += all;
            if (all >= col_mask_min) c->masked += all;
        }
    }
}
void fill_tri(ColHot* t, ColCold* u, cSat* sat, u16 no, bool floorGroup)
{
    AtPoly* p = &sat->poly_p[no];
    const Vec* v0 = &sat->vtx[p->v[0]];
    const Vec* v1 = &sat->vtx[p->v[1]];
    const Vec* v2 = &sat->vtx[p->v[2]];
    const f32 dy = floorGroup ? col_control_floor : 0.0f;
    t->v0[0] = v0->x; t->v0[1] = v0->y + dy; t->v0[2] = v0->z;
    u->v1[0] = v1->x; u->v1[1] = v1->y + dy; u->v1[2] = v1->z;
    u->v2[0] = v2->x; u->v2[1] = v2->y + dy; u->v2[2] = v2->z;
    if (dy == 0.0f) {   // exact copies when no control is set (v + 0.0f is v for every finite v but -0)
        t->v0[1] = v0->y; u->v1[1] = v1->y; u->v2[1] = v2->y;
    }
    const Vec* n = &sat->norm_p[p->n];
    t->n[0] = n->x; t->n[1] = n->y; t->n[2] = n->z;
    const Vec* e0 = &sat->edge_p[p->e[0]];
    const Vec* e1 = &sat->edge_p[p->e[1]];
    const Vec* e2 = &sat->edge_p[p->e[2]];
    u->e0[0] = e0->x; u->e0[1] = e0->y; u->e0[2] = e0->z;
    u->e1[0] = e1->x; u->e1[1] = e1->y; u->e1[2] = e1->z;
    u->e2[0] = e2->x; u->e2[1] = e2->y; u->e2[2] = e2->z;
    t->attr = (p->attrHi << 16) | p->attrLo;
    t->poly = no;
    t->nidx = p->n;
}
struct BakeFill {
    ColPiece* pc;
    u32 node, leaf, idx;
};
void fill_tree(cSatBlock* blk, cSat* sat, BakeFill* f)
{
    for (; blk; blk = blk->next) {
        const u32 me = f->node++;
        ColPiece* pc = f->pc;
        pc->nodeMinX[me] = blk->min.x;
        pc->nodeMinZ[me] = blk->min.z;
        pc->nodeSizeX[me] = blk->m_Size.x;
        pc->nodeSizeZ[me] = blk->m_Size.z;
        if (blk->m_Flag & 1) {
            pc->nodeLeaf[me] = 0xFFFF;
            fill_tree((cSatBlock*) blk->idx, sat, f);
        } else {
            const u32 lf = f->leaf++;
            pc->nodeLeaf[me] = (u16) lf;
            ColLeaf& L = pc->leaf[lf];
            L.first = f->idx;
            L.nFloor = (u16) (blk->m_nFloor + blk->m_nSlope);
            L.nWall = blk->m_nWall;
            const u32 all = L.nFloor + L.nWall;
            for (u32 i = 0; i < all; i++) pc->idx[f->idx++] = blk->idx[i];
        }
        pc->nodeSkip[me] = (u16) f->node;   // after this node's subtree
    }
}

// the cells of box [lo, hi] (grown by the margin) in leaf grid g
inline ColMask cells_of(const ColGrid& g, f32 lx, f32 ly, f32 lz, f32 hx, f32 hy, f32 hz, int shift)
{
    int x0 = (int) __builtin_floorf((lx - kColMargin - g.x0) * g.ix), x1 = (int) __builtin_floorf((hx + kColMargin - g.x0) * g.ix);
    int z0 = (int) __builtin_floorf((lz - kColMargin - g.z0) * g.iz), z1 = (int) __builtin_floorf((hz + kColMargin - g.z0) * g.iz);
    int y0 = (int) __builtin_floorf((ly - kColMargin - g.y0) * g.iy), y1 = (int) __builtin_floorf((hy + kColMargin - g.y0) * g.iy);
    x0 += shift; x1 += shift;
    if (x0 < 0) x0 = 0;
    if (z0 < 0) z0 = 0;
    if (y0 < 0) y0 = 0;
    if (x1 > COL_GRID_X - 1) x1 = COL_GRID_X - 1;
    if (z1 > COL_GRID_Z - 1) z1 = COL_GRID_Z - 1;
    if (y1 > COL_GRID_Y - 1) y1 = COL_GRID_Y - 1;
    if (x0 > x1 || z0 > z1 || y0 > y1) return 0;
    const ColMask row = (ColMask) (((1ull << (x1 + 1)) - 1ull) & ~((1ull << x0) - 1ull));
    ColMask m = 0;
    for (int y = y0; y <= y1; y++)
        for (int z = z0; z <= z1; z++) m |= row << ((y * COL_GRID_Z + z) * COL_GRID_X);
    return m;
}
// lane eng-svc2: each leaf's grid and the cells of its list entries (room load)
void bake_grid(ColPiece* pc, cSat* sat)
{
    for (u32 k = 0; k < pc->nNode; k++) {
        const u16 lf = pc->nodeLeaf[k];
        if (lf == 0xFFFF) continue;
        const ColLeaf& L = pc->leaf[lf];
        const u32 all = L.nFloor + L.nWall;
        ColGrid& g = pc->grid[lf];
        f32 ylo = 1e30f, yhi = -1e30f;
        for (u32 i = 0; i < all; i++) {
            const AtPoly* p = &sat->poly_p[pc->idx[L.first + i]];
            for (int v = 0; v < 3; v++) {
                const f32 y = sat->vtx[p->v[v]].y;
                if (y < ylo) ylo = y;
                if (y > yhi) yhi = y;
            }
        }
        g.x0 = pc->nodeMinX[k];
        g.z0 = pc->nodeMinZ[k];
        g.y0 = all ? ylo : 0.0f;
        g.ix = pc->nodeSizeX[k] > 0.0f ? (f32) COL_GRID_X / pc->nodeSizeX[k] : 0.0f;
        g.iz = pc->nodeSizeZ[k] > 0.0f ? (f32) COL_GRID_Z / pc->nodeSizeZ[k] : 0.0f;
        g.iy = all && yhi > ylo ? (f32) COL_GRID_Y / (yhi - ylo) : 0.0f;
        g.mask = COL_NO_MASK;
        if (all < col_mask_min || pc->nMask + all > pc->nIdx) continue;   // tested whole
        g.mask = pc->nMask;
        pc->nMask += all;
        for (u32 i = 0; i < all; i++) {
            const u16 no = pc->idx[L.first + i];
            const ColHot& h = pc->hot[no];
            const ColCold& c = pc->cold[no];
            const f32 xs[3] = {h.v0[0], c.v1[0], c.v2[0]}, ys[3] = {h.v0[1], c.v1[1], c.v2[1]}, zs[3] = {h.v0[2], c.v1[2], c.v2[2]};
            f32 lx = xs[0], hx = xs[0], ly = ys[0], hy = ys[0], lz = zs[0], hz = zs[0];
            for (int v = 1; v < 3; v++) {
                if (xs[v] < lx) lx = xs[v];
                if (xs[v] > hx) hx = xs[v];
                if (ys[v] < ly) ly = ys[v];
                if (ys[v] > hy) hy = ys[v];
                if (zs[v] < lz) lz = zs[v];
                if (zs[v] > hz) hz = zs[v];
            }
            pc->cmask[g.mask + i] = cells_of(g, lx, ly, lz, hx, hy, hz, 0);
        }
    }
}

ColPiece* bake(cSat* sat)
{
    BakeCount c = {0, 0, 0, 0};
    count_tree(sat->block_p, &c);
    const u32 nPoly = sat->polygon_num;
    u32 off = align32(sizeof(ColPiece));
    const u32 oMinX = off; off = align32(off + 4 * c.nodes);
    const u32 oMinZ = off; off = align32(off + 4 * c.nodes);
    const u32 oSzX = off; off = align32(off + 4 * c.nodes);
    const u32 oSzZ = off; off = align32(off + 4 * c.nodes);
    const u32 oSkip = off; off = align32(off + 2 * c.nodes);
    const u32 oLeafN = off; off = align32(off + 2 * c.nodes);
    const u32 oLeaf = off; off = align32(off + sizeof(ColLeaf) * c.leaves);
    const u32 oIdx = off; off = align32(off + 2 * c.idx);
    const u32 oHot = off; off = align32(off + sizeof(ColHot) * nPoly);
    const u32 oCold = off; off = align32(off + sizeof(ColCold) * nPoly);
    const u32 oGrid = off; off = align32(off + sizeof(ColGrid) * c.leaves);
    const u32 oMask = off; off = align32(off + sizeof(ColMask) * c.masked);
    u8* blk = (u8*) svc_pool_carve_room(off);
    if (!blk) return 0;
    memset(blk, 0, off);
    ColPiece* pc = (ColPiece*) blk;
    pc->sat = sat;
    pc->file = sat->pFile;
    pc->nNode = (u16) c.nodes;
    pc->nLeaf = (u16) c.leaves;
    pc->nTri = nPoly;
    pc->nIdx = c.idx;
    pc->bytes = off;
    pc->nPoly = sat->polygon_num;
    pc->nodeMinX = (f32*) (blk + oMinX);
    pc->nodeMinZ = (f32*) (blk + oMinZ);
    pc->nodeSizeX = (f32*) (blk + oSzX);
    pc->nodeSizeZ = (f32*) (blk + oSzZ);
    pc->nodeSkip = (u16*) (blk + oSkip);
    pc->nodeLeaf = (u16*) (blk + oLeafN);
    pc->leaf = (ColLeaf*) (blk + oLeaf);
    pc->idx = (u16*) (blk + oIdx);
    pc->hot = (ColHot*) (blk + oHot);
    pc->cold = (ColCold*) (blk + oCold);
    pc->grid = (ColGrid*) (blk + oGrid);
    pc->cmask = (ColMask*) (blk + oMask);
    pc->nMask = 0;
    BakeFill f = {pc, 0, 0, 0};
    fill_tree(sat->block_p, sat, &f);
    // the floor group: polygons [0, floors + slopes) of the file (cSatFile counts); the control raises them
    const u32 nFloorPolys = (u32) sat->floor_num + sat->slope_num;
    for (u32 i = 0; i < nPoly; i++) fill_tri(&pc->hot[i], &pc->cold[i], sat, (u16) i, i < nFloorPolys);
    bake_grid(pc, sat);
    col_cnt.bakes++;
    col_cnt.tri_bytes += (sizeof(ColHot) + sizeof(ColCold)) * nPoly;
    return pc;
}

ColPiece* piece_for(cSat* sat)
{
    for (u32 i = 0; i < g_npiece; i++)
        if (g_piece[i]->sat == sat && g_piece[i]->file == sat->pFile) return g_piece[i];
    if (g_npiece >= kMaxPieces) return 0;
    ColPiece* pc = bake(sat);
    if (!pc) return 0;
    col_cnt.late_bakes++;
    g_piece[g_npiece++] = pc;
    return pc;
}

// ---- the line test (at_sub.cpp At_poly_line_ck on a table triangle) ----
inline u32 line_tri(const ColHot* t, const ColCold* u, Vec* out, Vec* vert0, Vec* vert1, u32 flag, u32 mask)
{
    Vec d0, d1, c, a, b;
    const Vec* v0 = (const Vec*) t->v0;
    const Vec* nrm = (const Vec*) t->n;
    f32 dp0, dp1, tt, s0, s1;
    u32 attr;

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
    if (dp0 * dp1 > 0.0f) return 0;
    col_cnt.cold_line++;
    const Vec* v1 = (const Vec*) u->v1;
    const Vec* v2 = (const Vec*) u->v2;
    PSVECSubtract(vert1, vert0, &a);
    PSVECSubtract(vert0, v0, &b);
    PSVECCrossProduct((const Vec*) u->e0, &a, &c);
    if (PSVECDotProduct(&c, &b) < 0.0f) return 0;
    PSVECSubtract(vert0, v1, &b);
    PSVECCrossProduct((const Vec*) u->e1, &a, &c);
    if (PSVECDotProduct(&c, &b) < 0.0f) return 0;
    PSVECSubtract(vert0, v2, &b);
    PSVECCrossProduct((const Vec*) u->e2, &a, &c);
    if (PSVECDotProduct(&c, &b) < 0.0f) return 0;
    tt = -dp0 / PSVECDotProduct(&a, nrm);
    if (tt >= 1.0f || tt < 0.0f) return 0;
    s0 = PSVECDotProduct(nrm, vert0) - PSVECDotProduct(nrm, v0);
    s1 = PSVECDotProduct(nrm, vert1) - PSVECDotProduct(nrm, v0);
    if (s0 * s1 < 0.0f) {
        f32 a0 = __builtin_fabsf(s0);
        f32 a1 = __builtin_fabsf(s1);
        InterVectorXYZ(out, vert0, vert1, a1 / (a0 + a1));
    } else if (out) {
        *out = *vert1;
    }
    attr = t->attr;
    if (SEck == 0) {
        if ((flag & 0x1000) && (attr & 0x400000)) return 0;
        if ((flag & 0x2000) && (attr & 0x4000)) return 0;
        if ((flag & 0x4000) && (attr & 0x40)) return 0;
        if ((attr & 0x400) && !(flag & 0x8000)) return 0;
        if ((flag & 0x800) && (attr & 0x8000)) return 0;
        if ((flag & 0x8000) && (attr & 0x800000)) return 0;
    } else {
        if ((flag & 0x400) && (attr & 0x4000)) return 0;
        if ((flag & 0x800) && (attr & 0x400000)) return 0;
    }
    if (mask & attr) return 0;
    return attr | 0x01000000;
}

inline void group(const ColLeaf& L, int flag, u32* a, u32* b)
{
    if (flag & 0x40) {
        *a = L.first;
        *b = L.first + L.nFloor;
    } else if (flag & 0x80) {
        *a = L.first + L.nFloor;
        *b = *a + L.nWall;
    } else {
        *a = L.first;
        *b = L.first + L.nFloor + L.nWall;
    }
}

// blkPolyLineCk + blkPolyLineCkCore over the flattened tree
int line_piece(ColPiece* pc, cSat* sat, Vec* pos0, Vec* pos1, int flag, int mask, Vec* hit, u32* pn)
{
    Vec mid, dir, adir, h;
    int ret = 0;
    PSVECAdd(pos0, pos1, &mid);
    PSVECScale(&mid, &mid, 0.5f);
    PSVECSubtract(pos0, &mid, &dir);
    adir.x = __builtin_fabsf(dir.x);
    adir.y = __builtin_fabsf(dir.y);
    adir.z = __builtin_fabsf(dir.z);
    adir.y = 0.0f;
    dir.y = 0.0f;
    mid.y = 0.0f;
    // the query's own box (lane eng-svc2: the leaf grids' cells it meets)
    const f32 qlx = pos0->x < pos1->x ? pos0->x : pos1->x, qhx = pos0->x < pos1->x ? pos1->x : pos0->x;
    const f32 qly = pos0->y < pos1->y ? pos0->y : pos1->y, qhy = pos0->y < pos1->y ? pos1->y : pos0->y;
    const f32 qlz = pos0->z < pos1->z ? pos0->z : pos1->z, qhz = pos0->z < pos1->z ? pos1->z : pos0->z;
    const u32 nn = pc->nNode;
    for (u32 k = 0; k < nn;) {
        col_cnt.nodes_tested++;
        const f32 sx = pc->nodeSizeX[k], sz = pc->nodeSizeZ[k];
        f32 dx = (mid.x - pc->nodeMinX[k]) - sx * 0.5f;
        f32 dz = (mid.z - pc->nodeMinZ[k]) - sz * 0.5f;
        if (__builtin_fabsf(dx) > adir.x + sx * 0.5f || __builtin_fabsf(dz) > adir.z + sz * 0.5f ||
            __builtin_fabsf(dx * dir.z - dz * dir.x) > (sx * adir.z + sz * adir.x) * 0.5f) {
            k = pc->nodeSkip[k];
            continue;
        }
        const u16 lf = pc->nodeLeaf[k];
        k++;
        if (lf == 0xFFFF) continue;
        col_cnt.leaves++;
        u32 a, b;
        group(pc->leaf[lf], flag, &a, &b);
        int r = 0;
        const ColGrid& g = pc->grid[lf];
        const bool whole = col_grid_off || g.mask == COL_NO_MASK;
        if (whole) col_cnt.leaves_whole++;
        const ColMask q = whole ? (ColMask) ~0ull : cells_of(g, qlx, qly, qlz, qhx, qhy, qhz, col_control_grid);
        const ColMask* cm = whole ? 0 : pc->cmask + g.mask - pc->leaf[lf].first;   // cm[i]: list entry i's cells
        for (u32 i = a; i < b; i++) {
            const u32 no = pc->idx[i];
            const ColHot* t = &pc->hot[no];
            const u32 bit = 1u << (no & 7);
            if (!whole && !(cm[i] & q)) {   // its cells miss the query's: it cannot be hit
                col_cnt.tris_skipped++;
                // the check build tests it anyway: a hit there must be the segment's end (a segment lying exactly in
                // the polygon's plane), which never replaces the nearest hit (its distance is the whole segment's)
                if (col_verify && !(g_bits[no >> 3] & bit) && line_tri(t, &pc->cold[no], &h, pos0, pos1, flag, mask)) {
                    if (h.x == pos1->x && h.y == pos1->y && h.z == pos1->z) col_cnt.filter_end++;
                    else col_cnt.filter_miss++;
                }
                continue;
            }
            if (g_bits[no >> 3] & bit) continue;
            g_bits[no >> 3] |= bit;
            col_cnt.tris_line++;
            u32 at = line_tri(t, &pc->cold[no], &h, pos0, pos1, flag, mask);
            if (at) {
                if (GetDistance(pos0, &h) < GetDistance(pos0, hit)) {
                    *hit = h;
                    r = (int) at;
                    if (pn) *pn = (u32) &sat->norm_p[t->nidx];
                }
            }
        }
        if (r) ret = r;
    }
    return ret;
}

// ---- the swept sphere (at_sub.cpp At_poly_sphere_ck2 on a table triangle) ----
u32 sphere_tri(const ColHot* t, const ColCold* u, Vec* oldPos, Vec* pos, f32 r, u32 flag, u32 mask)
{
    Vec tri[3];
    Vec n, hp, nn;
    f32 d;
    u32 hit, i;
    const u32 attr = t->attr;
    tri[0].x = t->v0[0]; tri[0].y = t->v0[1]; tri[0].z = t->v0[2];
    n.x = t->n[0]; n.y = t->n[1]; n.z = t->n[2];
#define COL_COLD()                                                          \
    do {                                                                    \
        tri[1].x = u->v1[0]; tri[1].y = u->v1[1]; tri[1].z = u->v1[2];      \
        tri[2].x = u->v2[0]; tri[2].y = u->v2[1]; tri[2].z = u->v2[2];      \
        col_cnt.cold_sphere++;                                              \
    } while (0)

    if (PSVECDotProduct(&n, oldPos) - PSVECDotProduct(&n, tri) < 0.0f) return 0;
    d = PSVECDotProduct(&n, pos) - PSVECDotProduct(&n, tri);
    {
        f32 ad = __builtin_fabsf(d);
        hit = 99;
        if (ad > r) {
            Vec hp2;
            if (At_surface_line_ck(&hp, tri, &n, oldPos, pos)) {
                hit = 0;
                nn = n;
                hp2 = hp;
                COL_COLD();
                if (At_poly_point_rel(tri, &nn, &hp2)) hit = 1;
            } else {
                hit = 0;
            }
        } else {
            Vec v, hp2;
            PSVECScale(&n, &hp, d);
            PSVECSubtract(pos, &hp, &hp);
            nn = n;
            hp2 = hp;
            COL_COLD();
            if (At_poly_point_rel(tri, &nn, &hp2) == 0) {
                if (flag & 0x20) {
                    hit = 0;
                } else {
                    for (i = 0; i < 3; i++) {
                        f32 len, dot;
                        if (attr & (1 << (i + 29))) continue;
                        PSVECSubtract(&tri[(i + 1) % 3], &tri[i], &v);
                        PSVECSubtract(pos, &tri[i], &nn);
                        len = PSVECSquareMag(&v);
                        dot = PSVECDotProduct(&nn, &v);
                        if (dot < 0.01f) continue;
                        if (len < dot) continue;
                        PSVECScale(&v, &hp, dot / len);
                        PSVECAdd(&hp, &tri[i], &hp);
                        if (PSVECSquareDistance(pos, &hp) < r * r) {
                            hit = 2;
                            break;
                        }
                    }
                    if (i == 3) hit = 0;
                }
            } else {
                hit = 1;
            }
        }
    }
    if (hit != 0) {
        if (SEck == 0) {
            if ((flag & 0x1000) && (attr & 0x400000)) hit = 0;
            else if ((flag & 0x2000) && (attr & 0x4000)) hit = 0;
            else if ((flag & 0x4000) && (attr & 0x40)) hit = 0;
            else if ((attr & 0x400) && !(flag & 0x8000)) hit = 0;
            else if ((flag & 0x8000) && (attr & 0x800000)) hit = 0;
            else if ((flag & 0x800) && (attr & 0x8000)) hit = 0;
        } else {
            if ((flag & 0x400) && (attr & 0x4000)) hit = 0;
            else if ((flag & 0x800) && (attr & 0x400000)) hit = 0;
        }
        if (mask & attr) hit = 0;
    }
    switch (hit) {
    case 0:
        break;
    case 1:
        PSVECScale(&n, &nn, r);
        PSVECAdd(&hp, &nn, pos);
        break;
    case 2:
        PSVECSubtract(pos, &hp, &nn);
        if (PSVECDotProduct(&nn, &n) > 0.0f) {
            PSVECNormalize(&nn, &nn);
            PSVECScale(&nn, &nn, r * 0.99f);
            PSVECAdd(&hp, &nn, pos);
        }
        break;
    default:
        break;
    }
    return hit;
}

// cSatBlock::hitCheckSphere on a node row (the original's box test, its asymmetric bounds included)
inline int lineCross(Vec* a, Vec* b, Vec* c, Vec* d)
{
    f32 denom = (b->x - a->x) * (d->z - c->z) - (b->z - a->z) * (d->x - c->x);
    f32 ax, az, t, s;
    if (denom == 0.0f) return 0;
    ax = a->x - c->x;
    az = a->z - c->z;
    t = az * (d->x - c->x) - ax * (d->z - c->z);
    if (t < 0.0f) {
        if (denom >= 0.0f) return 0;
        if (t < denom) return 0;
    } else {
        if (denom < 0.0f) return 0;
        if (t > denom) return 0;
    }
    s = az * (b->x - a->x) - ax * (b->z - a->z);
    if (s < 0.0f) {
        if (denom >= 0.0f) return 0;
        if (s < denom) return 0;
    } else {
        if (denom < 0.0f) return 0;
        if (s > denom) return 0;
    }
    return 1;
}
int node_sphere(const ColPiece* pc, u32 k, Vec* pos0, Vec* pos1, f32 r)
{
    Vec c0, c1;
    f32 x0 = pc->nodeMinX[k];
    f32 z0 = pc->nodeMinZ[k];
    const f32 sx = pc->nodeSizeX[k], sz = pc->nodeSizeZ[k];
    f32 cx = (pos0->x + pos1->x) * 0.5f;
    f32 cz = (pos0->z + pos1->z) * 0.5f;
    f32 hx = __builtin_fabsf(pos0->x - pos1->x) * 0.5f + r;
    f32 hz = __builtin_fabsf(pos0->z - pos1->z) * 0.5f + r;
    f32 x1, z1;
    if (x0 + sx < cx - hx) return 0;
    if (x0 - sx > cx + hx) return 0;
    if (z0 + sz < cz - hz) return 0;
    if (z0 - sz > cz + hz) return 0;
    if (!(pos0->x < x0 - r || pos0->x > x0 + sx + r || pos0->z < z0 - r || pos0->z > z0 + sz + r)) return 1;
    if (!(pos1->x < x0 - r || pos1->x > x0 + sx + r || pos1->z < z0 - r || pos1->z > z0 + sz + r)) return 1;
    x1 = x0 + sx + r;
    z1 = z0 + sz + r;
    c0.x = x0; c0.y = 0.0f; c0.z = z0;
    c1.x = x1; c1.y = 0.0f; c1.z = z0;
    if (lineCross(pos0, pos1, &c0, &c1)) return 1;
    c0.z = c1.z = z1;
    if (lineCross(pos0, pos1, &c0, &c1)) return 1;
    c0.z = z0;
    c1.x = x0;
    if (lineCross(pos0, pos1, &c0, &c1)) return 1;
    c1.x = c0.x = x1;
    if (lineCross(pos0, pos1, &c0, &c1)) return 1;
    return 0;
}

// the cells of the swept sphere's box: its segment's box grown by its radius (cells_of adds the margin)
inline ColMask sphere_cells(const ColGrid& g, const Vec* p0, const Vec* p1, f32 r)
{
    const f32 lx = (p0->x < p1->x ? p0->x : p1->x) - r, hx = (p0->x < p1->x ? p1->x : p0->x) + r;
    const f32 ly = (p0->y < p1->y ? p0->y : p1->y) - r, hy = (p0->y < p1->y ? p1->y : p0->y) + r;
    const f32 lz = (p0->z < p1->z ? p0->z : p1->z) - r, hz = (p0->z < p1->z ? p1->z : p0->z) + r;
    return cells_of(g, lx, ly, lz, hx, hy, hz, col_control_grid);
}

// blkPolySphereCk + blkPolySphereCkCore over the flattened tree
int sphere_piece(ColPiece* pc, cSat* sat, Vec* pos0, Vec* pos1, f32 r, int flag, Vec* nrm, int mask)
{
    int ret = 0;
    const u32 nn = pc->nNode;
    for (u32 k = 0; k < nn;) {
        col_cnt.nodes_tested++;
        if (!node_sphere(pc, k, pos0, pos1, r)) {
            k = pc->nodeSkip[k];
            continue;
        }
        const u16 lf = pc->nodeLeaf[k];
        k++;
        if (lf == 0xFFFF) continue;
        col_cnt.leaves++;
        u32 a, b;
        group(pc->leaf[lf], flag, &a, &b);
        // lane eng-svc3: the cells of the sphere's segment box grown by its radius, taken again after every push
        const ColGrid& g = pc->grid[lf];
        const bool whole = col_sphere_grid_off || g.mask == COL_NO_MASK;
        if (whole) col_cnt.leaves_whole++;
        const ColMask* cm = whole ? 0 : pc->cmask + g.mask - pc->leaf[lf].first;
        ColMask q = whole ? (ColMask) ~0ull : sphere_cells(g, pos0, pos1, r);
        for (u32 i = a; i < b; i++) {
            const u32 no = pc->idx[i];
            const ColHot* t = &pc->hot[no];
            if (g_bits[no >> 3] & (1 << (no & 7))) continue;
            g_bits[no >> 3] |= 1 << (no & 7);   // visited: the original tests it here, skipped or not
            if (!whole && !(cm[i] & q)) {
                // its cells miss the sphere's: no hit (the sphere never comes within its radius of the polygon and
                // its segment does not cross it), so the original's test here leaves everything as it is
                col_cnt.sphere_skipped++;
                if (col_verify) {
                    Vec p1 = *pos1;
                    if (sphere_tri(t, &pc->cold[no], pos0, &p1, r, flag, mask)) col_cnt.sphere_filter_miss++;
                }
                continue;
            }
            col_cnt.tris_sphere++;
            if (sphere_tri(t, &pc->cold[no], pos0, pos1, r, flag, mask)) {
                ret = 1;
                if (nrm) *nrm = sat->norm_p[t->nidx];
                if (!whole) {   // the sphere moved: its cells again
                    q = sphere_cells(g, pos0, pos1, r);
                    col_cnt.sphere_recells++;
                }
            }
        }
    }
    return ret;
}

}   // namespace

extern "C" u32 col_piece_count(void) { return g_npiece; }
extern "C" ColPiece* col_piece_at(u32 i) { return i < g_npiece ? g_piece[i] : 0; }
// the bytes the original walk reads from: the file's vertex, normal, edge, polygon and block tables
extern "C" u32 col_file_bytes(const ColPiece* pc)
{
    const cSat* s = pc->sat;
    return 0x14 + 12u * (s->vertex_num + s->normal_num + s->nEdge) + (u32) sizeof(AtPoly) * s->polygon_num + 0x24u * pc->nNode +
           2u * pc->nIdx;
}

extern "C" ColPiece* col_piece_of(const cSat* s)
{
    for (u32 i = 0; i < g_npiece; i++)
        if (g_piece[i]->sat == s && g_piece[i]->file == s->pFile) return g_piece[i];
    return 0;
}

// Lane eng-skel1 (eng-load1's request R2): the room is left. Every piece is dropped and the room carve their tables took
// is given back (pieces are baked into the room carve only, so nothing else is in it). The next room's col_bake_all bakes
// its own pieces, whatever addresses its cSat records have. Control colkeep (RE4_SVC_CONTROL on the PC reference, or
// col_control_keep = 1): the first piece baked stays, with its tables (a piece kept: the round trip must fail).
extern "C" int col_control_keep;
int col_control_keep;
extern "C" void col_room_release(void)
{
    const char* c = svc_env ? svc_env("RE4_SVC_CONTROL") : 0;
    if (c && !__builtin_strcmp(c, "colkeep")) col_control_keep = 1;
    const u32 dropped = g_npiece;
    if (col_control_keep && g_npiece) {
        // the room carve runs down: the first piece baked is the highest block; keeping it keeps it alone
        ColPiece* keep = g_piece[0];
        svc_pool_room_reset(keep);
        g_npiece = 1;
    } else {
        svc_pool_room_reset(0);
        g_npiece = 0;
    }
    g_bypass = 0;
    col_cnt.releases++;
    col_cnt.released += dropped - g_npiece;
}

extern "C" void col_bake_all(void)
{
    cSatMgr* mgr[2] = {&SatMgr, &EatMgr};
    for (int m = 0; m < 2; m++)
        for (u32 i = 0; i < mgr[m]->nArray; i++) {
            cSat* sat = (cSat*) ((u8*) mgr[m]->pArray + mgr[m]->size * i);
            if (!sat->isAlive() || !VALID_PTR(sat->block_p)) continue;
            if (col_piece_of(sat)) continue;
            ColPiece* pc = bake(sat);
            if (pc && g_npiece < kMaxPieces) g_piece[g_npiece++] = pc;
        }
}

// lane eng-svcspd1 (the account): queries made again in the same tick with the same inputs (the last 8 kept a kind)
namespace {
struct QKey {
    u32 w[8];
};
QKey g_qk[2][8];
u32 g_qn[2], g_qtick[2];
void count_repeat(int kind, const Vec* a, const Vec* b, u32 x, u32 y)
{
    QKey k;
    memcpy(&k.w[0], a, 12);
    memcpy(&k.w[3], b, 12);
    k.w[6] = x;
    k.w[7] = y;
    const u32 tick = (u32) pG->Frame_cnt;
    if (g_qtick[kind] != tick) {
        g_qtick[kind] = tick;
        g_qn[kind] = 0;
    }
    const u32 n = g_qn[kind] < 8 ? g_qn[kind] : 8;
    for (u32 i = 0; i < n; i++)
        if (!__builtin_memcmp(&g_qk[kind][i], &k, sizeof k)) {
            if (kind) col_cnt.sphere_repeats++;
            else col_cnt.line_repeats++;
            return;
        }
    g_qk[kind][g_qn[kind]++ & 7] = k;
}
}

// ---- the three cores, engine bodies ----
int cSatMgr::hitCheck2(Vec* pos0, Vec* pos1, Vec* hit, u32* attr, int flag, int mask)
{
    Vec cur, la, lb, lcur, tmp;
    u32 pn = 0;
    int ret = 0;
    SvcProfUnless pr(SP_COL_LINE, SP_COL_FLOOR);   // the account (svc_prof.h): a floor query's line is the floor's
    count_repeat(0, pos0, pos1, (u32) flag, (u32) mask);
    SEck = seCk;
    cur = *pos1;
    col_cnt.line_queries++;
    for (u32 i = 0; i < nArray; i++) {
        cSat* sat = (cSat*) ((u8*) pArray + size * i);
        if (!sat->isAlive()) continue;
        ColPiece* pc = piece_for(sat);
        if (!pc) continue;
        memset(g_bits, 0, (sat->polygon_num >> 3) + 1);
        PSMTXMultVec(sat->imat, pos0, &la);
        PSMTXMultVec(sat->imat, pos1, &lb);
        PSMTXMultVec(sat->imat, &cur, &lcur);
        int r = line_piece(pc, sat, &la, &lb, flag, mask, &lcur, &pn);
        if (r) {
            PSMTXMultVec(sat->imat, &cur, &tmp);
            if (GetDistance(&la, &lcur) < GetDistance(&la, &tmp)) {
                PSMTXMultVec(sat->mat, &lb, pos1);
                ret = r;
                PSMTXMultVec(sat->mat, &lcur, &cur);
                g_bypass = sat;
            }
        }
    }
    if (hit) *hit = cur;
    if (ret && attr) *attr = pn;
    return ret;
}

int cSatMgr::hitCheck(Vec* pos0, Vec* pos1, Vec* hit, Vec* nrm, int flag, int mask)
{
    u32 pn;
    int ret = hitCheck2(pos0, pos1, hit, &pn, flag, mask);
    if (nrm && ret) PSMTXMultVecSR(g_bypass->mat, (Vec*) pn, nrm);
    return ret;
}

int cSatMgr::polySphereCk(Vec* oldPos, Vec* pos, f32 r, int flag, Vec* nrm, int mask)
{
    int ret = 0;
    SvcProf pr(SP_COL_SPHERE);
    {
        u32 rb;
        memcpy(&rb, &r, 4);
        count_repeat(1, oldPos, pos, rb, (u32) flag ^ ((u32) mask << 16));
    }
    col_cnt.sphere_queries++;
    for (u32 i = 0; i < nArray; i++) {
        cSat* sat = (cSat*) ((u8*) pArray + size * i);
        if (!sat->isAlive()) continue;
        ColPiece* pc = piece_for(sat);
        if (!pc) continue;
        Vec lo, lp;
        memset(g_bits, 0, (sat->polygon_num + 7) / 8);
        PSMTXMultVec(sat->imat, oldPos, &lo);
        PSMTXMultVec(sat->imat, pos, &lp);
        if (sphere_piece(pc, sat, &lo, &lp, r, flag, nrm, mask)) {
            PSMTXMultVec(sat->mat, &lp, pos);
            if (nrm) PSMTXMultVecSR(sat->mat, nrm, nrm);
            ret = 1;
        }
    }
    return ret;
}
