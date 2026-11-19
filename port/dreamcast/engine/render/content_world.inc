/* eng-look: world content step W (render/content.h), included by native_draw.inc.
   A coarser world level past a distance (native_world.c) and a stable ranked cap on world pieces: the selected
   meshlets are ranked by projected size (box half-diagonal in pixels at the box centre's depth); a piece drawn last
   picture ranks 25% higher (hysteresis); only the first N are drawn. Big near pieces (ground, walls) always rank
   first, so the cap removes the smallest far detail. (A cap on placements was tried first: 45 of the 54 placements
   a picture are larger than 4 m, terrain and buildings, and a cap of 32 removed the ground under the pyre.)
     step 1: one level coarser past 20 m
     step 2: two levels coarser past 15 m, at most 192 pieces (cross selects 219 a picture, farm 231)
     step 3: two levels coarser past 10 m, at most 128 pieces
   Step 0 is today's selection. */
#include "content.h"
#include <stdlib.h>
static void content_world_setup(void){
    static const unsigned shift[4]={0,1,2,2};static const float dist[4]={0,20000,15000,10000};
    unsigned step=m1_content[CS_WORLD];
    native_world_lod_shift=shift[step&3];native_world_lod_dist=dist[step&3];
}
static int place_rank(const void* a,const void* b){float x=*(const float*)a,y=*(const float*)b;return (x<y)-(x>y);}
static uint8_t piece_last[8192];
static inline unsigned piece_key(const NativePiece* p){return (p->placement*2654435761u^p->meshlet*40503u)&8191;}
static int content_world_cap(const NativeWorld* w,const float* c,NativePiece* sel,int n){
    static const unsigned caps[4]={0,0,192,128};
    unsigned cap=caps[m1_content[CS_WORLD]&3];
    if(!cap||n<=0)return n;
    static float score[8192][2];
    const uint8_t* m=w->mesh;const uint8_t* meshlets=m+*(const uint32_t*)(m+48);
    for(int i=0;i<n;i++){
        const NativePlacement* pl=w->places+sel[i].placement;const uint16_t* b=(const uint16_t*)(meshlets+28*sel[i].meshlet+16);
        const float* g=pl->grid;float ctr[3],hx=.5f*(b[3]-b[0]),hy=.5f*(b[4]-b[1]),hz=.5f*(b[5]-b[2]),r2=0;
        float lx=.5f*(b[0]+b[3]),ly=.5f*(b[1]+b[4]),lz=.5f*(b[2]+b[5]);
        for(unsigned r=0;r<3;r++){ctr[r]=g[4*r]*lx+g[4*r+1]*ly+g[4*r+2]*lz+g[4*r+3];
            float e=fabsf(g[4*r])*hx+fabsf(g[4*r+1])*hy+fabsf(g[4*r+2])*hz;r2+=e*e;}
        float depth=-(c[8]*ctr[0]+c[9]*ctr[1]+c[10]*ctr[2]+c[11]);
        float sc=sqrtf(r2)/m1_maxf(depth,100.f);if(piece_last[piece_key(sel+i)])sc*=1.25f;
        score[i][0]=sc;score[i][1]=(float)i;
    }
    memset(piece_last,0,sizeof(piece_last));
    if((unsigned)n<=cap){for(int i=0;i<n;i++)piece_last[piece_key(sel+i)]=1;return n;}
    qsort(score,n,sizeof(score[0]),place_rank);
    static uint8_t keep[8192];memset(keep,0,n);
    for(unsigned k=0;k<cap;k++)keep[(unsigned)score[k][1]]=1;
    int out=0;
    for(int i=0;i<n;i++)if(keep[i]){piece_last[piece_key(sel+i)]=1;sel[out++]=sel[i];}
    m1_content_counts[7]+=n-out;
    return out;
}
