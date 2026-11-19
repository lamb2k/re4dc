#pragma once
#include <stddef.h>
#include <stdint.h>
typedef struct { uint16_t mesh,index,source,sky; float grid[12],center[3],half[3],scale; } NativePlacement;
typedef struct { uint32_t first,count; float center[3],half[3]; } NativeCell;
typedef struct { uint32_t header; uint8_t phase,flags; uint16_t reserved; } NativeMaterial;
typedef struct {
    const uint8_t *mesh,*groups;
    const NativeMaterial *materials;
    const NativePlacement *places;
    const NativeCell *cells;
    unsigned cell_count,place_count,group_bytes;
} NativeWorld;
typedef struct { unsigned placement,part,meshlet,header,near_class,groups; } NativePiece;
typedef struct { float p[6][4]; } NativeFrustum;
int native_world_open(NativeWorld*,const void*,size_t);
int native_world_select(const NativeWorld*,const float*,float,NativePiece*,unsigned);
void native_world_frustum(const float* camera,NativeFrustum* world);
