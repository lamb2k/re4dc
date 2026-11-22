/* The source's model lighting rule (eng-e0b), included by native_actor.inc.
   1. Selection, as cLightMgr::setModel2 (src/game/light.cpp): the room's lights in array order; a light applies
      to a model when it is alive (be_flag & 3), its kind mask xF meets the model's EnableMask (or, for models
      without EnableMask 0x41, the light's parent is the model), it is not Type 4, its kind is switched on, the
      model's SelectMask lets it through (unless the room status overrides), its colour is not black and it
      reaches the model's light volume (cylinder, sphere or box: lightHitCheck). At most 8, in array order.
   2. Each picked light becomes a GX light by its type xD, as LightSetModel (src/game/trans_lit.cpp): colour =
      DispCol x alpha / 128; brightness with the range fade (constant, linear, quadratic, spot, parallel, spot
      quadratic); type 7 only raises the ambient. Ambient = the larger of the local ambient lights and the room
      ambient the model's EnableMask selects (scenery / effects / enemies), plus AddAmb.
   3. Per vertex, as GX with diffuse clamp and spot attenuation: channel = clamp(ambient + sum colour x
      max(0, n.L) x attenuation); output = channel x material colour x TEV scale (TevScaleGroup). The light
      direction and the distance terms are evaluated once per weight set at the weight set's origin.
   Inputs per picture: the room's lights (state 2, 18 words each) and each model's light record (state 8,
   17 words: the model's light volume and masks, material colour, TEV scale group and AddAmb). */
#include "content.h"
typedef struct {unsigned flags,type,kind,spot;float pos[3],dir[3],radius,intensity;uint8_t rgb[4];
                unsigned index,bits,a0;float a1;unsigned parent;} NativeLamp;
_Static_assert(sizeof(NativeLamp)==72,"lamp record");
typedef struct {unsigned role,index,model,info,select;float offset[3],size[3];uint8_t color[4];unsigned tev,addamb,picked[2],status;} ModelLight;
_Static_assert(sizeof(ModelLight)==68,"model light record");
typedef struct {
    float pos[3],rgb[3],axis[3];   /* world position (parallel: a far point), colour 0..1, spot axis */
    float br,k0,k1,k2,sa0,sa1;      /* GX: angle terms (sa0 + sa1 cos, spot only), distance terms k */
    unsigned spot;
} SrcLight;
typedef struct { unsigned n; SrcLight l[8]; float amb[3],k[3]; } SrcLights;
static uint8_t lamp_order[64];static unsigned lamp_count;   /* this picture's lights in array order */
volatile uint32_t m1_light_pick_mismatch,m1_light_pick_checked;   /* engine pick vs the game's own (test) */
static unsigned src_light_cap;   /* lane eng-draw4 look arm LCAP (E1 boot file): 0 no cap (the default) */

static void lamps_frame(const NativeScene* s){
    const NativeLamp* L=(const void*)s->state[2];unsigned n=s->words[2]*4/sizeof(NativeLamp);
    if(n>64)n=64;
    /* lane eng-draw3 (step 3): only the lights that pass the model-independent tests of source_lights_w (alive, not
       Type 4, kind switched on, not black) are listed, once a picture; the order of those kept is unchanged */
    unsigned k=0;
    for(unsigned i=0;i<n;i++){
        const NativeLamp* l=L+i;
        if((l->flags&3)!=3 || l->type==4 || !(l->bits>>24&1) || !(l->rgb[0]|l->rgb[1]|l->rgb[2]))continue;
        unsigned j=k++;while(j && L[lamp_order[j-1]].index>l->index){lamp_order[j]=lamp_order[j-1];j--;}lamp_order[j]=i;
    }
    lamp_count=k;
}
static const ModelLight* model_light_ri(const NativeScene* s,unsigned role,unsigned index){
    const ModelLight* m=(const void*)s->state[8];unsigned n=s->words[8]*4/sizeof(ModelLight);
    for(unsigned i=0;i<n;i++)if(m[i].role==role && m[i].index==index)return m+i;
    return NULL;
}
static const ModelLight* model_light(const NativeScene* s,const ActorPose* a){return model_light_ri(s,a->role,a->index);}
/* lane eng-e1e: the matrices the rule reads are passed by pointer (model, light-origin part, object position), so the
   E1 actor pass lights from the skeleton's tables in place; the ActorPose form below picks them from its records. */
static const ModelLight src_light_fallback={0,0,0,0x100000u,0xffffffffu,{0,0,0},{1000,1000,1000},{0x40,0x40,0x40,0xff},1|2<<8,0,{~0u,~0u},0};
/* Lane eng-e1j (ruling H-016.2): a character of the E1 images is lit from its model record in place (lv, a view of
   addresses: services/light_view.h, filled by services/draw.cpp e1_light_view); the rule reads each input where the
   behaviour keeps it. A record (ml: the pack's, the bench's) is read as before when lv is 0. The bench has no views. */
#ifdef E1_LIGHT_VIEW_H
static inline unsigned lv_flags(const E1LightView* v){
    const unsigned b=*v->be_flag;unsigned f=(b&0x8000?1u:0u)|(b&8?2u:0u)|(v->info->flag&4?8u:0u);
    if(v->data_flags && (*v->data_flags&0x40000000u))f|=4;
    return f;
}
static inline unsigned lv_tev(const E1LightView* v){const unsigned g=*v->tev_group,t=v->tev_table[g];return g|(t?t-1:255u)<<8;}
#define LI_ENABLE(ml,lv) ((lv)?(unsigned)(lv)->info->enable:((ml)->info>>16&255))
#define LI_FLAGS(ml,lv)  ((lv)?lv_flags(lv):((ml)->info>>24))
#define LI_SHAPE(ml,lv)  ((lv)?(unsigned)((lv)->info->flag&3):((ml)->info&3))
#define LI_SELECT(ml,lv) ((lv)?(lv)->info->select:(ml)->select)
#define LI_STATUS(ml,lv) ((lv)?*(lv)->status:(ml)->status)
#define LI_MODEL(ml,lv)  ((lv)?(unsigned)(uintptr_t)(lv)->model:(ml)->model)
#define LI_OFFSET(ml,lv) ((lv)?(lv)->info->offset:(ml)->offset)
#define LI_SIZE(ml,lv)   ((lv)?(lv)->info->size:(ml)->size)
#define LI_COLOR(ml,lv)  ((lv)?(lv)->color:(ml)->color)
#define LI_TEV(ml,lv)    ((lv)?lv_tev(lv):(ml)->tev)
#define LI_ADDAMB(ml,lv) ((lv)?((unsigned)(lv)->addamb[0]|(unsigned)(lv)->addamb[1]<<8|(unsigned)(lv)->addamb[2]<<16):(ml)->addamb)
#else
typedef struct E1LightView E1LightView;
#define LI_ENABLE(ml,lv) ((ml)->info>>16&255)
#define LI_FLAGS(ml,lv)  ((ml)->info>>24)
#define LI_SHAPE(ml,lv)  ((ml)->info&3)
#define LI_SELECT(ml,lv) ((ml)->select)
#define LI_STATUS(ml,lv) ((ml)->status)
#define LI_MODEL(ml,lv)  ((ml)->model)
#define LI_OFFSET(ml,lv) ((ml)->offset)
#define LI_SIZE(ml,lv)   ((ml)->size)
#define LI_COLOR(ml,lv)  ((ml)->color)
#define LI_TEV(ml,lv)    ((ml)->tev)
#define LI_ADDAMB(ml,lv) ((ml)->addamb)
#endif
static float dist3(const float* a,const float* b){float x=a[0]-b[0],y=a[1]-b[1],z=a[2]-b[2];return sqrtf(x*x+y*y+z*z);}
/* rotation part of a 3x4 row-major matrix times v */
static void rot3(const float* m,const float* v,float* o){for(unsigned r=0;r<3;r++)o[r]=m[4*r]*v[0]+m[4*r+1]*v[1]+m[4*r+2]*v[2];}
static int light_hit(const ModelLight* ml,const E1LightView* lv,const float* w0,const float* cw,const NativeLamp* l){
    if(l->radius==0.f)return 1;
    const float* offset=LI_OFFSET(ml,lv);const float* size=LI_SIZE(ml,lv);
    float pos[3];rot3(cw,offset,pos);pos[0]+=cw[3];pos[1]+=cw[7];pos[2]+=cw[11];
    unsigned shape=LI_SHAPE(ml,lv);
    if(shape==2){   /* box: the light in the model's frame against size x scale + radius */
        const float* m=w0;float d[3]={l->pos[0]-pos[0],l->pos[1]-pos[1],l->pos[2]-pos[2]};
        for(unsigned a=0;a<3;a++){
            float ax[3]={m[a],m[4+a],m[8+a]},sc=sqrtf(ax[0]*ax[0]+ax[1]*ax[1]+ax[2]*ax[2]);
            float p=sc>0?(d[0]*ax[0]+d[1]*ax[1]+d[2]*ax[2])/sc:0,half=size[a]*sc;
            if(p-l->radius>half || p+l->radius<-half)return 0;
        }
        return 1;
    }
    if(shape==0){   /* cylinder: spheres of size.x at +-size.y along the parts' up axis */
        for(int sgn=-1;sgn<=1;sgn+=2){
            float up[3]={0,sgn*size[1],0},t[3];rot3(cw,up,t);
            float q[3]={pos[0]+t[0],pos[1]+t[1],pos[2]+t[2]};
            if(dist3(q,l->pos)<size[0]+l->radius)return 1;
        }
        return 0;
    }
    return dist3(pos,l->pos)<size[0]+l->radius;   /* sphere */
}
/* The picked lights of one model, as GX lights; ambient and output scale. */
/* w0: the model's matrix; cw: the light volume's origin (the model or its part ml->info>>8); obj: the object position's
   matrix (part 1 when the model has bones). ml is never NULL here; lv (lane eng-e1j): the model's inputs in place, read
   instead of ml when set. */
static void source_lights_w(const NativeScene* s,const float* w0,const float* cw,const float* obj,const ModelLight* ml,
                            const E1LightView* lv,SrcLights* out){
    const ModelLight* const fallback=&src_light_fallback;
    const NativeLamp* L=(const void*)s->state[2];
    unsigned enable=LI_ENABLE(ml,lv),flags=LI_FLAGS(ml,lv),select=LI_SELECT(ml,lv),status=LI_STATUS(ml,lv);
    const unsigned owner=LI_MODEL(ml,lv);const float* size=LI_SIZE(ml,lv);
    float obj_pos[3]={obj[3],obj[7],obj[11]};
    float obj_size=m1_maxf(size[0],size[1]);int obj_flag=LI_SHAPE(ml,lv)!=2;
    const NativeLamp* pick[8];unsigned n=0,game[8],gn=0;
    const unsigned wrong=m1_content[CS_PICK_CONTROL];   /* eng-look: the test's control walks the lights backwards */
    for(unsigned o=0;o<lamp_count && !(flags&1);o++){
        const NativeLamp* l=L+lamp_order[wrong?lamp_count-1-o:o];
        if((l->flags&3)!=3)continue;
        unsigned xf=l->bits&255;
        if(!((xf&enable) || (!(enable&0x41) && l->parent==owner)))continue;
        if(l->type==4 || !(l->bits>>24&1))continue;
        if(l->index<=31 && !((1u<<l->index)&select) && !(status&0x01000000) && !(status&0x04000000))continue;
        if(!(l->rgb[0]|l->rgb[1]|l->rgb[2]))continue;
        if(!light_hit(ml,lv,w0,cw,l))continue;
        if(n==8)break;
        pick[n++]=l;
    }
    /* test only: the game's own pick from its last draw (array indices), where recorded (a record, not a live model) */
    if(!lv)for(unsigned i=0;i<8;i++){unsigned k=ml->picked[i>>2]>>(8*(i&3))&255;if(k!=255)game[gn++]=k;}
    if(!lv && ml!=fallback && ml->picked[0]!=~0u){
        m1_light_pick_checked++;
        unsigned same=gn==n;for(unsigned i=0;same && i<n;i++)same=pick[i]->index==game[i];
        m1_light_pick_mismatch+=!same;
    }
    const uint8_t* env=(const uint8_t*)s->state[7];   /* scenery, enemies, effects ambient */
    const uint8_t* ea=enable&0x10?env:enable&8?env+8:env+4;
    float amb[3]={0,0,0};
    out->n=0;
    for(unsigned i=0;i<n;i++){
        const NativeLamp* l=pick[i];float d=dist3(obj_pos,l->pos),range=l->radius+obj_size,I=l->intensity;
        unsigned type=l->spot;
        if(type==7){   /* local ambient */
            float f=(d<range-l->dir[0]||!obj_flag||l->radius==0.f)?1.f:d<range?(range-d)/l->dir[0]:0.f;
            for(unsigned c=0;c<3;c++)amb[c]=m1_maxf(amb[c],(float)(int)(f*l->rgb[c]));
            continue;
        }
        SrcLight* g=out->l+out->n++;
        float a=(float)l->rgb[3]*(1.f/128);
        for(unsigned c=0;c<3;c++)g->rgb[c]=m1_minf(255.f,l->rgb[c]*a)*(1.f/255);
        for(unsigned c=0;c<3;c++){g->pos[c]=l->pos[c];g->axis[c]=l->dir[c];}
        g->spot=0;g->sa0=1;g->sa1=0;g->k0=1;g->k1=g->k2=0;
        float fade=(type==0||type==2)?l->dir[0]:l->a1,br;
        if(d<range-fade||!obj_flag||l->radius==0.f)br=I;else if(d<range)br=I*(range-d)/fade;else br=type==0?0.f:.001f;
        if(type==1)br=l->radius!=0.f?I*(l->radius-d)/l->radius:I;
        float A0;memcpy(&A0,&l->a0,4);
        if(type==3||type==6){   /* spot, GX_SP_COS with cut-off A0 degrees */
            g->spot=1;
            if(A0>0.f && A0<=90.f){float cr=cosf(A0*.017453293f);g->sa0=-cr/(1-cr);g->sa1=1.f/(1-cr);}
            if(type==3){   /* GXInitLightDistAttn(5000, br, GX_DA_MEDIUM) */
                if(br>0.f && br<1.f){g->k1=.5f*(1-br)/(br*5000.f);g->k2=.5f*(1-br)/(br*5000.f*5000.f);}
                g->br=1;
            }else{         /* GXInitLightAttnK(1/br, 0, k2) */
                float k2=l->radius!=0.f?(I-.1f)/.1f/(l->radius*l->radius)/br:0.f;
                g->k0=1.f/br;g->k2=k2;g->br=1;
            }
        }else if(type==2){
            g->br=m1_maxf(0,br);g->k2=l->radius!=0.f?(I-.1f)/.1f/(l->radius*l->radius):0.f;
        }else if(type==5){   /* parallel: placed at the object plus the normal (view space when flags bit 0) */
            float v[3]={l->dir[0],l->dir[1],l->dir[2]};
            if(l->a0&1){const float* cam=(const float*)s->state[0];   /* inverse view rotation: transpose */
                for(unsigned c=0;c<3;c++)v[c]=cam[c]*l->dir[0]+cam[4+c]*l->dir[1]+cam[8+c]*l->dir[2];}
            for(unsigned c=0;c<3;c++)g->pos[c]=obj_pos[c]+v[c];
            g->br=m1_maxf(0,br);
        }else g->br=m1_maxf(0,br);
    }
    if(src_light_cap && out->n>src_light_cap){   /* lane eng-draw4 look arm LCAP: the strongest at the object, in order */
        float st[8];unsigned keep=0;
        for(unsigned i=0;i<out->n;i++){const SrcLight* g=out->l+i;const float d=dist3(obj_pos,g->pos);
            st[i]=(g->rgb[0]+g->rgb[1]+g->rgb[2])*g->br/(g->k0+g->k1*d+g->k2*d*d);}
        for(unsigned i=0;i<out->n;i++){unsigned rank=0;
            for(unsigned j=0;j<out->n;j++)rank+=st[j]>st[i]||(st[j]==st[i]&&j<i);
            if(rank<src_light_cap)out->l[keep++]=out->l[i];}
        out->n=keep;
    }
    for(unsigned c=0;c<3;c++)amb[c]=m1_maxf(amb[c],ea[c]);
    if(flags&2){const unsigned aa=LI_ADDAMB(ml,lv);amb[0]+=aa&255;amb[1]+=aa>>8&255;amb[2]+=aa>>16&255;}
    const unsigned tev=LI_TEV(ml,lv);const uint8_t* color=LI_COLOR(ml,lv);
    unsigned group=tev&255,cs=tev>>8&255;
    float S=group<=1?(cs==1?2.f:cs==2?4.f:1.f):group==5?2.f:group==6?4.f:1.f;
    for(unsigned c=0;c<3;c++){out->amb[c]=amb[c]*(1.f/255);out->k[c]=color[c]*(1.f/255)*S*255.f;}
    DC_ADD(DC_A_LIGHTS,out->n);   /* lane eng-draw1: lights per character, summed */
}
/* The ActorPose form (E0 bench, content and native passes): the same rule on the records' matrices. */
static void source_lights(const NativeScene* s,const ActorPose* actor,unsigned bones,const ModelLight* ml,SrcLights* out){
    if(!ml)ml=&src_light_fallback;   /* no record: a scenery-lit cylinder, material 0x40, TEV x4 */
    unsigned parts=ml->info>>8&255;const ActorPose* c=parts && parts<=bones?actor+parts:actor;
    source_lights_w(s,actor->world,c->world,bones?actor[1].world:actor[0].world,ml,0,out);
}
/* Per weight set: each light's direction in the set's model space (scaled for raw s16 normals) and its colour
   times the attenuation at the set's origin. Lane eng-draw3 (C1): one record a light, in the order the normal kernel
   reads it (direction, then colour), and the colour stored halved: the kernel adds (d + |d|) x colour / 2, which is
   d x colour exactly when d > 0 and exactly 0 otherwise, so no light needs a branch (the tier ends a block at every
   conditional branch and charges the next block's first memory reads again). Same products, same sums, same order. */
typedef struct { float d[3],hc[3]; } WsLamp;
static WsLamp ws_lamp[ACTOR_WS_LIMIT][8] __attribute__((aligned(32)));
static SrcLights cur_lights;
static void ws_light(unsigned i,const float* m){
    const float inv=1.f/(16384.f*.0625f);
    float o[3]={m[3],m[7],m[11]};
    WsLamp* w=ws_lamp[i];
    for(unsigned j=0;j<cur_lights.n;j++,w++){
        const SrcLight* g=cur_lights.l+j;
        float L[3]={g->pos[0]-o[0],g->pos[1]-o[1],g->pos[2]-o[2]},d=sqrtf(L[0]*L[0]+L[1]*L[1]+L[2]*L[2]);
        float id=d>0?1.f/d:0;for(unsigned c=0;c<3;c++)L[c]*=id;
        float att=g->br;
        if(g->spot){float cs=-(L[0]*g->axis[0]+L[1]*g->axis[1]+L[2]*g->axis[2]);att*=m1_maxf(0,g->sa0+g->sa1*cs);}
        att/=g->k0+g->k1*d+g->k2*d*d;
        w->d[0]=(m[0]*L[0]+m[4]*L[1]+m[8]*L[2])*inv;w->d[1]=(m[1]*L[0]+m[5]*L[1]+m[9]*L[2])*inv;
        w->d[2]=(m[2]*L[0]+m[6]*L[1]+m[10]*L[2])*inv;
        const float c0=g->rgb[0]*att,c1=g->rgb[1]*att,c2=g->rgb[2]*att;
        w->hc[0]=c0*.5f;w->hc[1]=c1*.5f;w->hc[2]=c2*.5f;
    }
}
/* Lane eng-draw4 (step 3c): the colour byte without a branch. Before: m1_byte(k x min(1, r)), a float compare and two
   integer compares a channel, nine conditional branches a normal (the tier ends a block at each and charges the next
   block's first memory reads again). The same value, exactly: k >= 0 (material colour x TEV scale), so
   k x min(1, r) = min(k, k x r) (k x 1 = k; the product is monotone), truncation is monotone, so the byte is
   clamp(min(trunc(k), trunc(k x r)), 0, 255) = max(0, min(trunc(k x r), ck)) with ck = min(trunc(k), 255) once a call.
   When r < 1 the product k x r is the one the old form multiplied; when r >= 1 both give ck. */
static int lb_ck[3];
static inline uint32_t light_byte(float kr,int ck){
    int v=(int)kr;
    v&=~(v>>31);                  /* below 0: 0 */
    const int d=ck-v;             /* v >= 0 and ck in 0..255: no overflow */
    return (uint32_t)(v+(d&(d>>31)));   /* above ck: ck */
}
/* One normal with NL lights (NL a constant after inlining: the light loop unrolls into one block). */
static inline __attribute__((always_inline)) uint32_t light_one(const SourceVector* v,const unsigned NL){
    const WsLamp* L=ws_lamp[v->bone];
    float x=v->xyz[0],y=v->xyz[1],z=v->xyz[2],r=cur_lights.amb[0],g=cur_lights.amb[1],b=cur_lights.amb[2];
#pragma GCC unroll 8
    for(unsigned j=0;j<NL;j++){
        const float d=x*L[j].d[0]+y*L[j].d[1]+z*L[j].d[2],t=d+shz_fabsf(d);
        r+=t*L[j].hc[0];g+=t*L[j].hc[1];b+=t*L[j].hc[2];
    }
    return 0xff000000|light_byte(cur_lights.k[0]*r,lb_ck[0])<<16|light_byte(cur_lights.k[1]*g,lb_ck[1])<<8
                     |light_byte(cur_lights.k[2]*b,lb_ck[2]);
}
/* idx NULL: normals base[0..n) into out[0..n); else base[idx[i]] into out[idx[i]] (lane eng-draw3, E3) */
#define LIGHT_RUN(NL) case NL: \
    if(idx)for(unsigned i=0;i<n;i++){const unsigned q=idx[i];out[q]=light_one(base+q,NL);} \
    else for(unsigned i=0;i<n;i++)out[i]=light_one(base+i,NL); \
    break;
static void light_normals_run(const SourceVector* base,const uint16_t* idx,unsigned n,uint32_t* out){
    for(unsigned c=0;c<3;c++){const int v=(int)cur_lights.k[c];lb_ck[c]=v>255?255:v;}   /* k >= 0: v >= 0 */
    switch(cur_lights.n){LIGHT_RUN(0) LIGHT_RUN(1) LIGHT_RUN(2) LIGHT_RUN(3) LIGHT_RUN(4) LIGHT_RUN(5) LIGHT_RUN(6)
                        LIGHT_RUN(7) LIGHT_RUN(8)}
}
#undef LIGHT_RUN
/* lane eng-draw1: counted per call; lab arm DL_LIGHT2 lights the normals twice */
static void light_normals_source(const SourceVector* v,unsigned n,uint32_t* out){
    DC_ADD(DC_A_NRM,n);DC_ADD(DC_A_NRMLIGHTS,n*cur_lights.n);
    light_normals_run(v,NULL,n,out);
    if(DC_ARM(DL_LIGHT2))light_normals_run(v,NULL,n,out);
}
/* lane eng-draw3 (E3): the normals a boundary part's kept strips use (idx: indices into base and out) */
static void light_normals_list(const SourceVector* base,const uint16_t* idx,unsigned n,uint32_t* out){
    DC_ADD(DC_A_NRM,n);DC_ADD(DC_A_NRMLIGHTS,n*cur_lights.n);
    light_normals_run(base,idx,n,out);
    if(DC_ARM(DL_LIGHT2))light_normals_run(base,idx,n,out);
}
