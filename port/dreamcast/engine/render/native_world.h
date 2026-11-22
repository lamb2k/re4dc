#pragma once
#include <stddef.h>
#include <stdint.h>
typedef struct { uint16_t mesh,index,source,sky; float grid[12],center[3],half[3],scale; } NativePlacement;
typedef struct { uint32_t first,count; float center[3],half[3]; } NativeCell;
typedef struct { uint32_t header; uint8_t phase,flags; uint16_t reserved; } NativeMaterial;
typedef struct { uint32_t remap,nonempty; uint8_t count,full,pad[2]; } NativeMeshletRt;
/* Baked visibility, format VIS2 (bench/bake_vis.c): per camera cell of the whole room, a camera height band and
   the cluster instances and actor cubes that cannot be seen from anywhere in the cell and band. Masks are stored
   once each, run-length coded, and decoded when the camera's cell changes. Every camera position the table does
   not cover (outside the grid, an unbaked cell, a height outside the cell's band) draws everything. */
typedef struct { uint16_t imask,cmask; int16_t ylo,yhi; } NativeVisCell;
typedef struct { uint16_t bit; uint8_t y0,ny; } NativeVisColumn;   /* actor column: mask bit, cube range */
typedef struct {
    uint32_t ninst,nplace,nx,nz,ncells,ni,ibytes,ax,ay,az,nbits,cbytes,nc;
    float org[2],cell,alo[3],acube,yunit;
    const uint32_t *place_base,*mesh_first,*rows,*ioff,*coff;
    const NativeVisCell* cells; const NativeVisColumn* cols; const uint8_t* rle;
    uint8_t *ibits,*cbits; unsigned cur_i,cur_c;   /* decoded masks of the current cell */
} NativeVis;
enum { VIS_NONE, VIS_OUTSIDE, VIS_UNBAKED, VIS_HEIGHT, VIS_MASK };
typedef struct {
    const uint8_t *mesh,*groups;
    const NativeMaterial *materials;
    const NativePlacement *places;
    const NativeCell *cells;
    unsigned cell_count,place_count,group_bytes;
    unsigned group_count,rt_vertices,rt_duplicates,rt_full;
    NativeMeshletRt* rt; uint16_t* rt_remap; uint8_t* rt_range; uint32_t* rt_color; unsigned rt_flag_conflicts;
    /* lane eng-draw2, step E2: one facing record a strip (native_world_facing), and per meshlet and group the ordinal
       of the group's first strip in that array */
    uint32_t* rt_facing; uint32_t* rt_gstrip; unsigned rt_strips,rt_facing_on;
    NativeVis* vis; const uint8_t *vis_inst,*vis_cubes;   /* this picture's hidden sets, or NULL */
} NativeWorld;
typedef struct { unsigned placement,part,meshlet,header,near_class,groups; } NativePiece;
typedef struct { float p[6][4]; } NativeFrustum;
static inline uint32_t world_color(uint32_t c,unsigned flags){
    if(flags&1)return (((c&15)|((c&240)<<4)|((c&3840)<<8)|((c&61440)<<12))*17);
    uint32_t rgb=((c&31)<<3)|((c&992)<<6)|((c&31744)<<9);
    return 0xff000000|rgb|((rgb>>5)&0x070707);
}
int native_world_open(NativeWorld*,const void*,size_t);
int native_world_select(const NativeWorld*,const float*,float,NativePiece*,unsigned);
void native_world_frustum(const float* camera,NativeFrustum* world);
int native_world_runtime(NativeWorld*);
/* The facing record of a strip (lane eng-draw2, step E2): bytes 0-2 a direction q (int8 x, y, z; n = q / 127), byte 3 a
   code (0: never dropped; else bits 0-3 dq, bits 4-7 rq). For every triangle i of the strip in its drawing order, with unit
   normal n_i (corner 1 - corner 0 cross corner 2 - corner 0, staged coordinates) and first corner p_i, and the strip's
   first corner p0: |n_i - n| <= native_facing_delta[dq] / 127 and |n_i . (p_i - p0)| <= native_facing_rho[rq] / 127. So
   for an eye e, with v = p0 - e: n_i . (p_i - e) >= (q . v - delta[dq] |v|_1 - rho[rq]) / 127, and the strip lies wholly on
   the positive side of every one of its triangles when q . v > delta[dq] |v|_1 + rho[rq]. Both bounds carry a margin
   (0.01 in the normal, 1 unit in the offset) beyond the exact maxima. */
extern const float native_facing_delta[16],native_facing_rho[16];
int native_vis_open(NativeVis*,const void*,size_t,const NativeWorld*);
void native_vis_close(NativeVis*);
unsigned native_vis_select(NativeWorld*,const float* camera);
void native_world_free(NativeWorld*);
/* eng-look content step W (native_world.c): coarser cluster levels past a distance */
extern unsigned native_world_lod_shift;extern float native_world_lod_dist;
