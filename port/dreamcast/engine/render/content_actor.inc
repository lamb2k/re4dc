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
#include <malloc.h>
extern volatile uint32_t m1_state[8];
#define CONTENT_MODELS 64
static int content_cards_open(const uint8_t* p,unsigned n,unsigned models);
static uint16_t lod_variant[CONTENT_MODELS][5];   /* [base][0 base, 1-3 PS2 levels, 4 rigid] (0xffff: none) */
static uint8_t lod_last[128];                    /* per actor ordinal: the level last picked */
static uint32_t* lit_cache[128];static unsigned lit_cap[128],lit_key[128],lit_age[128];static uint16_t lit_model[128];
/* lane eng-mem1: the lit caches are kept between pictures and grow to the largest model a slot has lit; a room change
   gives them back (render/native_scene.inc native_release), so a round trip ends with the KOS heap it started with
   (DOOR d4: +200 B after village > farm > village with them kept). */
void content_lit_release(void){
    for(unsigned i=0;i<128;i++){free(lit_cache[i]);lit_cache[i]=NULL;lit_cap[i]=0;lit_model[i]=0xffff;}
}
static uint16_t lod_chosen[128];static uint8_t card_last[128];                 /* per actor ordinal: the model drawn this picture */
volatile uint32_t m1_lod_variants;
volatile uint32_t m1_lod_models[CONTENT_MODELS][6];   /* per base model and window: pictures drawn at level 0-3, rigid, card */
/* Lane eng-draw6 (item 1): each catalogue model's base and level (0 base, 1-3 PS2 levels, 4 rigid), from the 'LODV'
   rows; and, per model, the picture (m1_state[1]) on which a caller's content_pick last returned it and the level that
   pick asked for: the E1 actor pass draws a model its caller picked (the fight's Ganados) as it is, picks the others
   itself (Leon, the partner), and counts the level asked against the level drawn. */
static uint8_t lod_base_of[256],lod_level_of[256],lod_asked[256];
static uint16_t lod_stamp[256];
static int lod_mark_on=1;   /* 0 while the E1 actor pass makes its own pick (not a caller's) */
static void lod_mark(unsigned v,unsigned asked){if(lod_mark_on && v<256){lod_stamp[v]=(uint16_t)m1_state[1];lod_asked[v]=(uint8_t)asked;}}
int content_variants_open(const uint8_t* p,unsigned n,unsigned models){
    for(unsigned i=0;i<CONTENT_MODELS;i++){lod_variant[i][0]=i;for(unsigned k=1;k<5;k++)lod_variant[i][k]=0xffff;}
    for(unsigned i=0;i<256;i++){lod_base_of[i]=(uint8_t)i;lod_level_of[i]=0;lod_stamp[i]=0;}
    m1_lod_variants=0;
    if(n){
        if(n<8||memcmp(p,"LODV",4))return 0;
        unsigned rows=*(const uint32_t*)(p+4);
        if(rows>256||8+8*rows>n)return 0;
        const uint16_t* r=(const uint16_t*)(p+8);
        for(unsigned i=0;i<rows;i++,r+=4){
            if(r[0]>=CONTENT_MODELS||r[0]>=models||r[1]<1||r[1]>4||r[2]>=models||r[3])return 0;
            lod_variant[r[0]][r[1]]=r[2];
            if(r[2]<256){lod_base_of[r[2]]=(uint8_t)r[0];lod_level_of[r[2]]=(uint8_t)r[1];}
        }
        m1_lod_variants=rows;
        if(!content_cards_open(p+8+8*rows,n-8-8*rows,models))return 0;
    }
    for(unsigned i=0;i<CONTENT_MODELS;i++)for(unsigned k=1;k<4;k++)if(lod_variant[i][k]==0xffff)lod_variant[i][k]=lod_variant[i][k-1];
    return 1;
}
static unsigned card_n;
static const float lod_thresholds[4][3]={{0,0,0},{160,60,0},{320,120,50},{480,160,70}};
static void content_actor_frame(void){
    extern volatile uint32_t m1_state[8];
    if(m1_state[1]==1){memset((void*)m1_lod_models,0,sizeof(m1_lod_models));memset(lod_last,0,sizeof(lod_last));memset(lit_model,0xff,sizeof(lit_model));memset(card_last,0,sizeof(card_last));}   /* a new window starts afresh */
    card_n=0;
}
/* The model to draw for an actor whose whole-actor box (bone spheres, world space) is lo..hi. */
static unsigned content_pick(const NativeScene* s,unsigned base,const float* lo,const float* hi,unsigned ordinal){
    unsigned step=m1_content[CS_LEVELS];
    if(!step||base>=CONTENT_MODELS){lod_chosen[ordinal]=base;lod_mark(base,0);return base;}
    const float* c=(const float*)s->state[0];
    float cx=.5f*(lo[0]+hi[0]),cy=.5f*(lo[1]+hi[1]),cz=.5f*(lo[2]+hi[2]);
    float dx=hi[0]-lo[0],dy=hi[1]-lo[1],dz=hi[2]-lo[2],r=.5f*sqrtf(dx*dx+dy*dy+dz*dz);
    float depth=-(c[8]*cx+c[9]*cy+c[10]*cz+c[11]);
    float px=depth>1.f?320.f*fabsf(c[13])*r/depth:1e9f;
    const float* t=lod_thresholds[step];unsigned level=0;
    for(unsigned k=0;k<3;k++)if(t[k]>0 && px<t[k]*(lod_last[ordinal]>k?1.1f:.9f))level=k+1;
    lod_last[ordinal]=level;
    unsigned v=lod_variant[base][level];
    unsigned asked=level;
    if(step==3 && lod_variant[base][4]!=0xffff && px<100.f*(lod_chosen[ordinal]==lod_variant[base][4]?1.1f:.9f)){v=lod_variant[base][4];m1_content_counts[4]++;asked=4;}
    else m1_content_counts[level]++;
    lod_mark(v,asked);
    m1_lod_models[base][v==lod_variant[base][4]&&step==3&&lod_variant[base][4]!=0xffff?4:level]++;
    lod_chosen[ordinal]=v;
    return v;
}
/* Baked static lighting (CS_BAKED). The world is drawn with its baked vertex colours already; the per-part runtime
   lights are the props' and characters'. A cacheable actor keeps its lit normal colours per actor (all parts) and
   reuses them while its key holds:
     step 1: props (catalogue role-2 models) whose pose has not changed; key = pose + the room's lights (exact)
     step 2: the same, lights frozen at first sight (key = pose only: a flickering light no longer re-lights them)
     step 3: step 2, and every actor under 100 px re-lit every 4th picture only (moving or not)
   Step 0 lights every visible part every picture (today). */
static uint32_t lights_hash;
static int ws_light_off;
static uint32_t fnv_words(uint32_t h,const uint32_t* p,unsigned n){for(unsigned i=0;i<n;i++)h=(h^p[i])*16777619u;return h;}
static void content_light_frame(const NativeScene* s){
    if(m1_content[CS_BAKED]!=1)return;
    lights_hash=fnv_words(2166136261u,s->state[2],s->words[2]);
    lights_hash=fnv_words(lights_hash,s->state[7],s->words[7]);
}
static float actor_px(const NativeScene* s,const float* lo,const float* hi){
    const float* c=(const float*)s->state[0];
    float cx=.5f*(lo[0]+hi[0]),cy=.5f*(lo[1]+hi[1]),cz=.5f*(lo[2]+hi[2]);
    float dx=hi[0]-lo[0],dy=hi[1]-lo[1],dz=hi[2]-lo[2],r=.5f*sqrtf(dx*dx+dy*dy+dz*dz);
    float depth=-(c[8]*cx+c[9]*cy+c[10]*cz+c[11]);
    return depth>1.f?320.f*fabsf(c[13])*r/depth:1e9f;
}
/* The cached colours for this actor (cache hit: skip lighting), or NULL (light as usual). *fill: light every part
   into the returned buffer now. */
static uint32_t* content_lit(const NativeScene* s,const ActorPose* actor,unsigned bones,unsigned base,unsigned variant,
                             const RtModel* m,unsigned ordinal,float px,int* fill){
    unsigned step=m1_content[CS_BAKED];*fill=0;
    if(!step)return NULL;
    int prop=base>=6;
    int far=step==3 && px<100.f;
    if(!prop && !far)return NULL;
    unsigned key=fnv_words(2166136261u,(const uint32_t*)actor,16*(bones+1));
    if(step==1)key^=lights_hash;
    const RtPart* last=m->parts+m->h[4]-1;unsigned n=last->nrm_first+last->nrm_count;
    if(lit_cap[ordinal]<n){free(lit_cache[ordinal]);lit_cache[ordinal]=memalign(32,4*n+32);lit_cap[ordinal]=lit_cache[ordinal]?n:0;lit_model[ordinal]=0xffff;}
    if(!lit_cache[ordinal])return NULL;
    int hit=lit_model[ordinal]==variant && (far&&!prop?(m1_state[1]-lit_age[ordinal])%600<4:lit_key[ordinal]==key);
    if(!hit){*fill=1;lit_key[ordinal]=key;lit_model[ordinal]=variant;lit_age[ordinal]=m1_state[1];}
    return lit_cache[ordinal];
}
/* Far props as flat cards (CS_CARDS): a prop with a baked card (bake/native_cards.py: 8 views around its root's
   vertical axis) whose projected size is under the step's threshold is drawn as one punch-through cylindrical
   billboard of the nearest view, lit by one colour (the actor's picked lights at the card centre), instead of its
   model. Thresholds (projected radius, 10% hysteresis): step 1 under 24 px, step 2 under 48 px, step 3 under 96 px. */
typedef struct { uint16_t model,hdr; float c[3],rw,hh; } PropCard;
static PropCard prop_card[CONTENT_MODELS];static uint8_t has_card[CONTENT_MODELS];
typedef struct { float c[3],right[3],up[3],rw,hh; unsigned view,hdr,color; } CardDraw;
static CardDraw card_draw[64];
static int content_cards_open(const uint8_t* p,unsigned n,unsigned models){
    memset(has_card,0,sizeof(has_card));
    if(!n)return 1;
    if(n<8||memcmp(p,"CARD",4))return 0;
    unsigned rows=*(const uint32_t*)(p+4);
    if(rows>CONTENT_MODELS||8+24*rows!=n)return 0;
    for(unsigned i=0;i<rows;i++){
        PropCard c;memcpy(&c,p+8+24*i,24);
        if(c.model>=CONTENT_MODELS||c.model>=models||!(c.rw>0)||!(c.hh>0))return 0;
        prop_card[c.model]=c;has_card[c.model]=1;
    }
    return 1;
}
/* The actor becomes a card this picture (1) or draws its model (0). */
static int content_card(const NativeScene* s,const ActorPose* actor,unsigned bones,unsigned base,unsigned ordinal,float px,unsigned hdr_limit){
    static const float thr[4]={0,24,48,96};
    unsigned step=m1_content[CS_CARDS];
    if(!step||base>=CONTENT_MODELS||!has_card[base]||card_n==64){card_last[ordinal]=0;return 0;}
    const PropCard* pc=prop_card+base;
    if(pc->hdr>=hdr_limit || !(px<thr[step]*(card_last[ordinal]?1.1f:.9f))){card_last[ordinal]=0;return 0;}
    const float* m=actor[0].world;const float* cam=(const float*)s->state[0];
    CardDraw* d=card_draw+card_n;
    for(unsigned r=0;r<3;r++)d->c[r]=m[4*r]*pc->c[0]+m[4*r+1]*pc->c[1]+m[4*r+2]*pc->c[2]+m[4*r+3];
    /* the camera position, then the view direction in the root's frame */
    float e[3]={-(cam[0]*cam[3]+cam[4]*cam[7]+cam[8]*cam[11]),-(cam[1]*cam[3]+cam[5]*cam[7]+cam[9]*cam[11]),-(cam[2]*cam[3]+cam[6]*cam[7]+cam[10]*cam[11])};
    float v[3]={e[0]-d->c[0],e[1]-d->c[1],e[2]-d->c[2]};
    float lx=m[0]*v[0]+m[4]*v[1]+m[8]*v[2],lz=m[2]*v[0]+m[6]*v[1]+m[10]*v[2];
    int k=(int)floorf(atan2f(lx,lz)*(4.f/3.14159265f)+.5f);k&=7;
    float yaw=k*(3.14159265f/4),sn=sinf(yaw),cs=cosf(yaw);
    for(unsigned r=0;r<3;r++){d->right[r]=(m[4*r]*cs-m[4*r+2]*sn);d->up[r]=m[4*r+1];}
    d->rw=pc->rw;d->hh=pc->hh;
    d->view=k;d->hdr=pc->hdr;
    /* one colour: the picked lights at the card centre, as the per-vertex rule with a half-lit normal */
    source_lights(s,actor,bones,model_light(s,actor),&cur_lights);
    float rgb[3]={cur_lights.amb[0],cur_lights.amb[1],cur_lights.amb[2]};
    for(unsigned j=0;j<cur_lights.n;j++){
        const SrcLight* g=cur_lights.l+j;
        float L[3]={g->pos[0]-d->c[0],g->pos[1]-d->c[1],g->pos[2]-d->c[2]},dd=sqrtf(L[0]*L[0]+L[1]*L[1]+L[2]*L[2]);
        float att=g->br;
        if(g->spot&&dd>0){float c2=-(L[0]*g->axis[0]+L[1]*g->axis[1]+L[2]*g->axis[2])/dd;att*=m1_maxf(0,g->sa0+g->sa1*c2);}
        att/=g->k0+g->k1*dd+g->k2*dd*dd;
        for(unsigned c=0;c<3;c++)rgb[c]+=.5f*g->rgb[c]*att;
    }
    d->color=0xff000000|m1_byte(cur_lights.k[0]*m1_minf(1.f,rgb[0]))<<16|m1_byte(cur_lights.k[1]*m1_minf(1.f,rgb[1]))<<8|m1_byte(cur_lights.k[2]*m1_minf(1.f,rgb[2]));
    card_n++;card_last[ordinal]=1;m1_content_counts[5]++;m1_lod_models[base][5]++;
    return 1;
}
/* Called in the punch-through list (bench main.c, k == 2). */
void native_cards(NativeScene* s){
    if(!card_n)return;
    const float* cam=(const float*)s->state[0];float near=cam[18]/(cam[17]-1);
    static const float grid[]={1,0,0,0,0,1,0,0,0,0,1,0};
    shz_mat4x4_t pm=projection_grid(cam,grid);shz_xmtrx_load_4x4(&pm);
    unsigned last=~0u;
    for(unsigned i=0;i<card_n;i++){
        const CardDraw* d=card_draw+i;pvr_vertex_t q[4] __attribute__((aligned(32)));int ok=1;
        for(unsigned j=0;j<4;j++){
            float a=(j&1)?d->rw:-d->rw,b=(j&2)?-d->hh:d->hh;
            shz_vec4_t r=shz_xmtrx_transform_vec4(shz_vec4_init(d->c[0]+a*d->right[0]+b*d->up[0],d->c[1]+a*d->right[1]+b*d->up[1],d->c[2]+a*d->right[2]+b*d->up[2],1));
            if(r.w<near){ok=0;break;}
            float iw=1.f/r.w;
            q[j].flags=j==3?PVR_CMD_VERTEX_EOL:PVR_CMD_VERTEX;q[j].x=r.x*iw;q[j].y=r.y*iw;q[j].z=iw;
            q[j].u=((d->view&3)+((j&1)?.99f:.01f))*.25f;q[j].v=((d->view>>2)+((j&2)?.99f:.01f))*.5f;
            q[j].argb=d->color;q[j].oargb=0;
        }
        if(!ok)continue;
        if(last!=d->hdr){last=d->hdr;pvr_poly_hdr_t hd __attribute__((aligned(32)));memcpy(&hd,(const unsigned*)row(&s->assets.header,last)+1,32);pvr_prim(&hd,32);}
        for(unsigned j=0;j<4;j++)pvr_prim(q+j,32);
    }
    card_n=0;
}
