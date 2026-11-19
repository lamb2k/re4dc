/* Host test for the per-part sphere class (render/part_cull.h) against the strip-checked path.
   Build and run:  cc -O2 -I../render test_part_clip.c -lm -o test_part_clip && ./test_part_clip
   Control:        cc -O2 -I../render -DM1_PART_LOOP_E0 test_part_clip.c -lm -o test_part_clip_e0 && ./test_part_clip_e0
                   (the E0 loop) must fail.
   The strip-checked path is the boundary emitter: per-corner outcodes from the projected positions, near
   clipping for any strip with a corner behind the near plane. A part classed "inside" skips both, so every
   corner of an inside part must be in front of every plane; a part classed "out" must have one plane with
   every corner outside. Corners are sampled inside each bone's sphere, as the load-time spheres bound them. */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <math.h>
#include "part_cull.h"

static float fr[6][4];
/* Camera at the origin looking down -z, 90 degree field, near 20, far 30000 (planes normalised, inside >= 0). */
static void frustum_setup(float near,float far){
    const float s=0.70710678f;
    float p[6][4]={{0,0,-1,-near},{0,0,1,far},{s,0,-s,0},{-s,0,-s,0},{0,s,-s,0},{0,-s,-s,0}};
    for(int i=0;i<6;i++)for(int k=0;k<4;k++)fr[i][k]=p[i][k];
}
/* Strip-checked path: outcode of one corner (bit j: behind plane j; bit 0 = near). */
static unsigned outcode(const float* v){
    unsigned c=0;
    for(int j=0;j<6;j++)if(fr[j][0]*v[0]+fr[j][1]*v[1]+fr[j][2]*v[2]+fr[j][3]<0)c|=1u<<j;
    return c;
}
static float rnd(float a,float b){return a+(b-a)*(float)rand()/(float)RAND_MAX;}

/* One part: nb bones (identity rotation, translation per bone, quantum 1), one sphere per bone, corners inside
   the spheres. Returns 1 when the class agrees with the strip-checked corners. */
static int check(unsigned nb,const float (*centre)[3],const float* radius,unsigned corners_per_bone,unsigned* got_state,unsigned* near_corners){
    float rows[8][12];float scale[8];PartSphere sp[8];
    for(unsigned b=0;b<nb;b++){
        float r[12]={1,0,0,centre[b][0],0,1,0,centre[b][1],0,0,1,centre[b][2]};
        for(int k=0;k<12;k++)rows[b][k]=r[k];
        scale[b]=1;sp[b].bone=b;sp[b].c[0]=sp[b].c[1]=sp[b].c[2]=0;sp[b].r=radius[b];
    }
    unsigned st=part_class((const float (*)[4])fr,sp,nb,(const float (*)[12])rows,scale);
    unsigned all=63,any=0,nearc=0;
    for(unsigned b=0;b<nb;b++)for(unsigned i=0;i<corners_per_bone;i++){
        float v[3],d;
        do{for(int a=0;a<3;a++)v[a]=rnd(-radius[b],radius[b]);d=v[0]*v[0]+v[1]*v[1]+v[2]*v[2];}while(d>radius[b]*radius[b]);
        if(i<6){for(int a=0;a<3;a++)v[a]=0;v[i>>1]=(i&1?-1:1)*radius[b]*0.999f;}   /* the sphere's extreme points */
        for(int a=0;a<3;a++)v[a]+=centre[b][a];
        unsigned c=outcode(v);all&=c;any|=c;nearc+=c&1;
    }
    *got_state=st;*near_corners=nearc;
    if(st==1 && any)return 0;            /* inside, yet a corner is outside a plane (near: skips near clipping) */
    if(st==0 && !all)return 0;           /* out, yet no single plane has every corner outside */
    return 1;
}
int main(void){
    frustum_setup(20,30000);
    int fail=0;
    /* 1. The audit's case: a two-bone part, first sphere wholly inside, second straddling the near plane. */
    {
        const float c[2][3]={{0,0,-600},{0,0,-25}};const float r[2]={80,60};unsigned st,nc;
        int ok=check(2,c,r,64,&st,&nc);
        printf("straddle: first sphere inside, second across the near plane: class %u (%s), %u corners behind near -> %s\n",
               st,st==0?"out":st==1?"inside":"boundary",nc,ok?"PASS":"FAIL");
        if(!ok||st!=2)fail++;
        /* same part, spheres in the other order: both loops must class it boundary */
        const float c2[2][3]={{0,0,-25},{0,0,-600}};const float r2[2]={60,80};
        ok=check(2,c2,r2,64,&st,&nc);
        printf("straddle, reversed order: class %u -> %s\n",st,ok&&st==2?"PASS":"FAIL");
        if(!ok||st!=2)fail++;
    }
    /* 2. Random multi-bone parts around the near plane and the side planes. */
    srand(12345);
    unsigned n=20000,bad=0,inside=0,boundary=0,out=0,bad_near=0;
    for(unsigned t=0;t<n;t++){
        unsigned nb=2+rand()%5;float c[8][3],r[8];
        for(unsigned b=0;b<nb;b++){
            c[b][2]=b==0?rnd(-2000,-200):rnd(-400,60);c[b][0]=rnd(-150,150);c[b][1]=rnd(-150,150);r[b]=rnd(10,90);
        }
        unsigned st,nc;
        if(!check(nb,(const float (*)[3])c,r,24,&st,&nc)){bad++;bad_near+=nc!=0;}
        inside+=st==1;boundary+=st==2;out+=st==0;
    }
    printf("random multi-bone parts: %u, classes inside %u / boundary %u / out %u, disagreements with the strip check %u (%u with corners behind near)\n",
           n,inside,boundary,out,bad,bad_near);
    if(bad)fail++;
#ifdef M1_PART_LOOP_E0
    printf("loop: E0 (control)\n");
#else
    printf("loop: eng-e0b\n");
#endif
    printf("%s\n",fail?"FAIL":"PASS");
    return fail?1:0;
}
