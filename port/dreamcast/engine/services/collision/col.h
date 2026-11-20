// Native collision queries (lane eng-svc): the room's scenery (SAT) and effect (EAT) collision baked into engine
// tables once, at room load, and the query cores (line, floor, swept sphere) run on them. Write-up:
// docs/engine/SERVICES.md. The behaviour keeps calling the original entry points (cSatMgr::check / getFloor /
// hitCheck / hitCheck2 / polySphereCk, wallAdjust, adjust ...); col.cpp gives the three cores engine bodies, and the
// rest of atari.cpp (the per-model logic: the sphere's speed vector, the wall then floor order) calls them.
//
// One ColPiece per collision piece (cSat), one 32-byte aligned block:
//
//   header             64 B   counts, the piece, its file
//   node SoA  [nNode]  20 B   the block tree flattened in the walk's order: box min x / z, size x / z (f32 rows),
//                             skip (u16: the node after this one's subtree, where a failed test continues) and
//                             leaf (u16: leaf number, 0xFFFF for an inner node)
//   leaf      [nLeaf]  8 B    first index; floors + slopes count; walls count (u16)
//   idx       [nIdx]   2 B    the leaves' polygon lists, leaf after leaf (the file's, copied)
//   hot       [nPoly] 32 B    one line per polygon: the first vertex, the face normal, the attribute word, the normal
//                             index. Every test starts with a plane test on these (the line's ends on one side, the
//                             sphere behind the face or not crossing it): most polygons a query visits end here
//   cold      [nPoly] 64 B    the other two vertices and the three edge vectors, read only by a polygon that passed
//   grid      [nLeaf] 32 B    lane eng-svc2: each leaf's cell grid, COL_GRID_X x COL_GRID_Z cells over the block's
//                             x / z extent and COL_GRID_Y bands over its polygons' heights (origin, inverse cell sizes;
//                             lane eng-svc3: the leaf's first mask, or none)
//   cmask     [nMask]  4 B    the cells each list entry's polygon (its box grown by kColMargin) overlaps, for the
//                             leaves with at least col_mask_min entries (lane eng-svc3: 32 cells, 4 B; a smaller leaf
//                             is tested whole). A line query tests only the entries whose cells meet the cells of its
//                             own grown box, in the list's order. A skipped polygon cannot be hit (the hit point lies
//                             in both boxes), or its only hit is the segment's end (a segment lying exactly in its
//                             plane: the original's test reports that wherever the polygon is), which never replaces
//                             the nearest hit. The swept sphere (lane eng-svc3) takes the cells of the box of its
//                             segment grown by its radius, again after every push (the sphere moves mid-query); a
//                             polygon it skips is marked visited, as the original marks it after a test that cannot
//                             hit (a hit needs the sphere within its radius of the polygon, or the segment through
//                             it), so it is not tested later from another leaf either. The check build tests every
//                             skipped polygon too and counts both kinds
//
// The walk order and the per-query polygon dedupe (a bit per polygon) are the original's, so the order in which
// polygons push a sphere out, and the nearest-hit ties of the line test, are the original's.
#pragma once
#include "types.h"
#include "vec.h"

class cSat;
class cSatFile;

struct ColHot {          // 32 B
    f32 v0[3];
    f32 n[3];
    u32 attr;
    u16 nidx;
    u16 poly;
};
struct ColCold {         // 64 B
    f32 v1[3], v2[3];
    f32 e0[3], e1[3], e2[3];
    u32 pad;
};
struct ColLeaf {         // 8 B
    u32 first;
    u16 nFloor;          // floors + slopes (the 0x40 group)
    u16 nWall;           // walls (the 0x80 group)
};
struct ColGrid {         // 32 B
    f32 x0, z0, y0;      // the grid's origin (the block's min x / z, its polygons' lowest y)
    f32 ix, iz, iy;      // cells per unit (COL_GRID_X / size x, COL_GRID_Z / size z, COL_GRID_Y / height span; 0 flat)
    u32 mask;            // lane eng-svc3: the leaf's first entry in cmask, COL_NO_MASK: the leaf is tested whole
    u32 pad;
};
#define COL_NO_MASK 0xFFFFFFFFu
#ifndef COL_MASK64
typedef u32 ColMask;      // lane eng-svc3: 32 cells (SERVICES.md section 18: masks halved, tests measured)
#ifndef COL_GRID_X
#define COL_GRID_X 2
#define COL_GRID_Z 2
#define COL_GRID_Y 8
#endif
#else
typedef u64 ColMask;      // round 2: 2 x 4 x 8 = 64 cells
#define COL_GRID_X 2
#define COL_GRID_Z 4
#define COL_GRID_Y 8
#endif
struct ColPiece {
    // header: 64 B
    cSat* sat;
    cSatFile* file;
    u16 nNode, nLeaf;
    u32 nTri;            // polygons (records)
    u32 nIdx;            // leaf list entries
    u32 bytes;
    f32* nodeMinX;       // [nNode] rows
    f32* nodeMinZ;
    f32* nodeSizeX;
    f32* nodeSizeZ;
    u16* nodeSkip;
    u16* nodeLeaf;
    ColLeaf* leaf;
    u16* idx;
    ColHot* hot;
    ColCold* cold;
    u32 nPoly;
    ColGrid* grid;       // [nLeaf]
    ColMask* cmask;      // [nMask]
    u32 nMask;
};

extern "C" {
void col_bake_all(void);            // every live piece of SatMgr and EatMgr (room load)
ColPiece* col_piece_of(const cSat* s);
u32 col_piece_count(void);
ColPiece* col_piece_at(u32 i);
u32 col_file_bytes(const ColPiece* pc);
struct ColCounters {
    u32 bakes, late_bakes, line_queries, sphere_queries, nodes_tested, leaves, tris_line, tris_sphere, tri_bytes, cold_line,
        cold_sphere, tris_skipped, filter_miss, filter_end, sphere_skipped, sphere_filter_miss, sphere_recells, leaves_whole;
};
extern ColCounters col_cnt;
extern f32 col_control_floor;       // control: every floor-group triangle raised by this many units in the queries
extern int col_control_grid;        // control (lane eng-svc2): the line query's cells taken one cell to the side
extern int col_verify;              // check build: every skipped polygon is also tested; a hit counts filter_miss
extern int col_grid_off;            // measurement: the grid not used (every list entry tested, as the original)
extern int col_sphere_grid_off;     // measurement (lane eng-svc3): the swept sphere without the grid
extern u32 col_mask_min;            // leaves with fewer list entries get no masks (tested whole; lane eng-svc3)
}
