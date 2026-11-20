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
//   tri       [nPoly] 96 B    one record per polygon: the three vertices, the face normal, the three edge vectors,
//                             the attribute word, the polygon number and its normal's index (one record read per
//                             polygon test, where the file needs the polygon, three vertices, a normal and three
//                             edges from five tables)
//
// The walk order and the per-query polygon dedupe (a bit per polygon) are the original's, so the order in which
// polygons push a sphere out, and the nearest-hit ties of the line test, are the original's.
#pragma once
#include "types.h"
#include "vec.h"

class cSat;
class cSatFile;

struct ColTri {          // 96 B
    f32 v0[3], v1[3], v2[3];
    f32 n[3];
    f32 e0[3], e1[3], e2[3];
    u32 attr;
    u16 poly;
    u16 nidx;
    u32 pad;
};
struct ColLeaf {         // 8 B
    u32 first;
    u16 nFloor;          // floors + slopes (the 0x40 group)
    u16 nWall;           // walls (the 0x80 group)
};
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
    ColTri* tri;
    u32 nPoly;
};

extern "C" {
void col_bake_all(void);            // every live piece of SatMgr and EatMgr (room load)
ColPiece* col_piece_of(const cSat* s);
struct ColCounters {
    u32 bakes, late_bakes, line_queries, sphere_queries, nodes_tested, leaves, tris_line, tris_sphere, tri_bytes;
};
extern ColCounters col_cnt;
extern f32 col_control_floor;       // control: every floor-group triangle raised by this many units in the queries
}
