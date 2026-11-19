#pragma once
#include <stddef.h>
#include <stdint.h>
typedef struct { uint16_t mesh,index,source,sky; float grid[12],center[3],half[3],scale; } NativePlacement;
typedef struct { uint32_t first,count; float center[3],half[3]; } NativeCell;
typedef struct { uint32_t header; uint8_t phase,flags; uint16_t reserved; } NativeMaterial;
typedef struct { uint32_t remap,nonempty; uint8_t count,full,pad[2]; } NativeMeshletRt;
/* Baked visibility (bench/bake_vis.c): per camera cell, cluster instances and actor cubes that cannot be seen. */
typedef struct {
    uint32_t ninst,ncube,ncell,cx,cz,ax,ay,az,nplace,ibytes,cbytes;
    float org[2],cell,alo[3],acube;
    const uint32_t *place_base,*mesh_first; const uint8_t *used,*bits;
} NativeVis;
typedef struct {
    const uint8_t *mesh,*groups;
    const NativeMaterial *materials;
    const NativePlacement *places;
    const NativeCell *cells;
    unsigned cell_count,place_count,group_bytes;
    unsigned group_count,rt_vertices,rt_duplicates,rt_full;
    NativeMeshletRt* rt; uint16_t* rt_remap; uint8_t* rt_range; uint32_t* rt_color; unsigned rt_flag_conflicts;
    const NativeVis* vis; const uint8_t *vis_inst,*vis_cubes;   /* this picture's hidden sets, or NULL */
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
int native_vis_open(NativeVis*,const void*,size_t,const NativeWorld*);
void native_vis_select(NativeWorld*,const float* camera);
void native_world_free(NativeWorld*);
