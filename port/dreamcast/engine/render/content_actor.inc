/* eng-look: content steps for characters and props (render/content.h), included by native_actor.inc.
   Character distance levels (CS_LEVELS): the pack's catalogue carries, after the base models, the PS2 levels that
   exist (Leon lg65 / bd70 / u70, Ganado g85 / g70 / g55) and rigid far variants (each vertex on its strongest bone,
   small bones folded into the nearest kept one), listed in section 14's tail ('LODV' rows). An actor's level comes
   from its projected size: the radius of its bone-sphere box in pixels at its depth, with 10% hysteresis per actor.
     step 1: level 1 under 160 px, level 2 under 60 px
     step 2: level 1 under 320 px, level 2 under 120 px, level 3 under 50 px
     step 3: level 1 under 480 px, level 2 under 160 px, level 3 under 70 px; the rigid variant under 100 px
   Step 0 draws the base model (today). */
#include "content.h"
#define CONTENT_MODELS 64
static uint16_t lod_variant[CONTENT_MODELS][5];   /* [base][0 base, 1-3 PS2 levels, 4 rigid] (0xffff: none) */
static uint8_t lod_last[128];                    /* per actor ordinal: the level last picked */
static uint16_t lod_chosen[128];                 /* per actor ordinal: the model drawn this picture */
volatile uint32_t m1_lod_variants;
int content_variants_open(const uint8_t* p,unsigned n,unsigned models){
    for(unsigned i=0;i<CONTENT_MODELS;i++){lod_variant[i][0]=i;for(unsigned k=1;k<5;k++)lod_variant[i][k]=0xffff;}
    m1_lod_variants=0;
    if(n){
        if(n<8||memcmp(p,"LODV",4))return 0;
        unsigned rows=*(const uint32_t*)(p+4);
        if(rows>256||8+8*rows!=n)return 0;
        const uint16_t* r=(const uint16_t*)(p+8);
        for(unsigned i=0;i<rows;i++,r+=4){
            if(r[0]>=CONTENT_MODELS||r[0]>=models||r[1]<1||r[1]>4||r[2]>=models||r[3])return 0;
            lod_variant[r[0]][r[1]]=r[2];
        }
        m1_lod_variants=rows;
    }
    for(unsigned i=0;i<CONTENT_MODELS;i++)for(unsigned k=1;k<4;k++)if(lod_variant[i][k]==0xffff)lod_variant[i][k]=lod_variant[i][k-1];
    return 1;
}
static const float lod_thresholds[4][3]={{0,0,0},{160,60,0},{320,120,50},{480,160,70}};
static void content_actor_frame(void){
    extern volatile uint32_t m1_state[8];
    if(m1_state[1]==1)memset(lod_last,0,sizeof(lod_last));   /* a new window starts from full detail */
}
/* The model to draw for an actor whose whole-actor box (bone spheres, world space) is lo..hi. */
static unsigned content_pick(const NativeScene* s,unsigned base,const float* lo,const float* hi,unsigned ordinal){
    unsigned step=m1_content[CS_LEVELS];
    if(!step||base>=CONTENT_MODELS){lod_chosen[ordinal]=base;return base;}
    const float* c=(const float*)s->state[0];
    float cx=.5f*(lo[0]+hi[0]),cy=.5f*(lo[1]+hi[1]),cz=.5f*(lo[2]+hi[2]);
    float dx=hi[0]-lo[0],dy=hi[1]-lo[1],dz=hi[2]-lo[2],r=.5f*sqrtf(dx*dx+dy*dy+dz*dz);
    float depth=-(c[8]*cx+c[9]*cy+c[10]*cz+c[11]);
    float px=depth>1.f?320.f*fabsf(c[13])*r/depth:1e9f;
    const float* t=lod_thresholds[step];unsigned level=0;
    for(unsigned k=0;k<3;k++)if(t[k]>0 && px<t[k]*(lod_last[ordinal]>k?1.1f:.9f))level=k+1;
    lod_last[ordinal]=level;
    unsigned v=lod_variant[base][level];
    if(step==3 && lod_variant[base][4]!=0xffff && px<100.f*(lod_chosen[ordinal]==lod_variant[base][4]?1.1f:.9f)){v=lod_variant[base][4];m1_content_counts[4]++;}
    else m1_content_counts[level]++;
    lod_chosen[ordinal]=v;
    return v;
}
