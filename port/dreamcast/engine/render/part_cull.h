#pragma once
/* Per-part frustum class from per-bone spheres (E0 step 2, fixed in eng-e0b). Shared by the renderer
   (native_actor.inc) and the host test bench/test_part_clip.c, so the test runs the shipped loop. */
#include "fastm.h"
typedef struct {uint16_t bone,pad;float c[3],r;} PartSphere;      /* raw position units, model space */

/* Bitmask of frustum planes the sphere lies wholly outside; *inside cleared unless it lies wholly inside all. */
static inline unsigned sphere_planes6(const float (*fr)[4],const float* c,float r,int* inside){
    unsigned out=0;
    for(unsigned j=0;j<6;j++){
        float d=fr[j][0]*c[0]+fr[j][1]*c[1]+fr[j][2]*c[2]+fr[j][3];
        if(d<-r)out|=1u<<j;
        if(d<r)*inside=0;
    }
    return out;
}
/* 0: out (one plane has every sphere wholly outside), 1: fully inside (every sphere inside every plane; its
   strips skip outcodes and near clipping), 2: boundary (per-strip outcodes, near clipping).
   Every sphere is tested while the part can still be out or fully inside. The loop may stop only when both
   are impossible. E0 stopped as soon as the common outside mask was zero, so a part whose first sphere was
   inside kept "inside" even when a later sphere crossed the near plane, and skipped near clipping.
   rows: bone matrices (3x4, row major, the position quantum folded in); scale: per-bone radius scale. */
static inline unsigned part_class(const float (*fr)[4],const PartSphere* sp,unsigned n,const float (*rows)[12],const float* scale){
    unsigned out=63;int inside=1;
#ifdef M1_PART_LOOP_E0          /* the E0 loop, for the test's control only */
    for(unsigned k=0;k<n && out;k++,sp++){
#else
    for(unsigned k=0;k<n && (out||inside);k++,sp++){
#endif
        const float* r=rows[sp->bone];float c[3];
        for(unsigned a=0;a<3;a++)c[a]=r[4*a]*sp->c[0]+r[4*a+1]*sp->c[1]+r[4*a+2]*sp->c[2]+r[4*a+3];
        out&=sphere_planes6(fr,c,sp->r*scale[sp->bone],&inside);
    }
    return out?0:inside?1:2;
}
