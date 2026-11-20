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

static void lamps_frame(const NativeScene* s){
    const NativeLamp* L=(const void*)s->state[2];unsigned n=s->words[2]*4/sizeof(NativeLamp);
    if(n>64)n=64;
    for(unsigned i=0;i<n;i++){unsigned j=i;while(j && L[lamp_order[j-1]].index>L[i].index){lamp_order[j]=lamp_order[j-1];j--;}lamp_order[j]=i;}
    lamp_count=n;
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
static float dist3(const float* a,const float* b){float x=a[0]-b[0],y=a[1]-b[1],z=a[2]-b[2];return sqrtf(x*x+y*y+z*z);}
/* rotation part of a 3x4 row-major matrix times v */
static void rot3(const float* m,const float* v,float* o){for(unsigned r=0;r<3;r++)o[r]=m[4*r]*v[0]+m[4*r+1]*v[1]+m[4*r+2]*v[2];}
static int light_hit(const ModelLight* ml,const float* w0,const float* cw,const NativeLamp* l){
    if(l->radius==0.f)return 1;
    float pos[3];rot3(cw,ml->offset,pos);pos[0]+=cw[3];pos[1]+=cw[7];pos[2]+=cw[11];
    unsigned shape=ml->info&3;
    if(shape==2){   /* box: the light in the model's frame against size x scale + radius */
        const float* m=w0;float d[3]={l->pos[0]-pos[0],l->pos[1]-pos[1],l->pos[2]-pos[2]};
        for(unsigned a=0;a<3;a++){
            float ax[3]={m[a],m[4+a],m[8+a]},sc=sqrtf(ax[0]*ax[0]+ax[1]*ax[1]+ax[2]*ax[2]);
            float p=sc>0?(d[0]*ax[0]+d[1]*ax[1]+d[2]*ax[2])/sc:0,half=ml->size[a]*sc;
            if(p-l->radius>half || p+l->radius<-half)return 0;
        }
        return 1;
    }
    if(shape==0){   /* cylinder: spheres of size.x at +-size.y along the parts' up axis */
        for(int sgn=-1;sgn<=1;sgn+=2){
            float up[3]={0,sgn*ml->size[1],0},t[3];rot3(cw,up,t);
            float q[3]={pos[0]+t[0],pos[1]+t[1],pos[2]+t[2]};
            if(dist3(q,l->pos)<ml->size[0]+l->radius)return 1;
        }
        return 0;
    }
    return dist3(pos,l->pos)<ml->size[0]+l->radius;   /* sphere */
}
/* The picked lights of one model, as GX lights; ambient and output scale. */
/* w0: the model's matrix; cw: the light volume's origin (the model or its part ml->info>>8); obj: the object position's
   matrix (part 1 when the model has bones). ml is never NULL here. */
static void source_lights_w(const NativeScene* s,const float* w0,const float* cw,const float* obj,const ModelLight* ml,SrcLights* out){
    const ModelLight* const fallback=&src_light_fallback;
    const NativeLamp* L=(const void*)s->state[2];
    unsigned enable=ml->info>>16&255,flags=ml->info>>24,select=ml->select,status=ml->status;
    float obj_pos[3]={obj[3],obj[7],obj[11]};
    float obj_size=m1_maxf(ml->size[0],ml->size[1]);int obj_flag=(ml->info&3)!=2;
    const NativeLamp* pick[8];unsigned n=0,game[8],gn=0;
    const unsigned wrong=m1_content[CS_PICK_CONTROL];   /* eng-look: the test's control walks the lights backwards */
    for(unsigned o=0;o<lamp_count && !(flags&1);o++){
        const NativeLamp* l=L+lamp_order[wrong?lamp_count-1-o:o];
        if((l->flags&3)!=3)continue;
        unsigned xf=l->bits&255;
        if(!((xf&enable) || (!(enable&0x41) && l->parent==ml->model)))continue;
        if(l->type==4 || !(l->bits>>24&1))continue;
        if(l->index<=31 && !((1u<<l->index)&select) && !(status&0x01000000) && !(status&0x04000000))continue;
        if(!(l->rgb[0]|l->rgb[1]|l->rgb[2]))continue;
        if(!light_hit(ml,w0,cw,l))continue;
        if(n==8)break;
        pick[n++]=l;
    }
    /* test only: the game's own pick from its last draw (array indices), where recorded */
    for(unsigned i=0;i<8;i++){unsigned k=ml->picked[i>>2]>>(8*(i&3))&255;if(k!=255)game[gn++]=k;}
    if(ml!=fallback && ml->picked[0]!=~0u){
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
    for(unsigned c=0;c<3;c++)amb[c]=m1_maxf(amb[c],ea[c]);
    if(flags&2){amb[0]+=ml->addamb&255;amb[1]+=ml->addamb>>8&255;amb[2]+=ml->addamb>>16&255;}
    unsigned group=ml->tev&255,cs=ml->tev>>8&255;
    float S=group<=1?(cs==1?2.f:cs==2?4.f:1.f):group==5?2.f:group==6?4.f:1.f;
    for(unsigned c=0;c<3;c++){out->amb[c]=amb[c]*(1.f/255);out->k[c]=ml->color[c]*(1.f/255)*S*255.f;}
}
/* The ActorPose form (E0 bench, content and native passes): the same rule on the records' matrices. */
static void source_lights(const NativeScene* s,const ActorPose* actor,unsigned bones,const ModelLight* ml,SrcLights* out){
    if(!ml)ml=&src_light_fallback;   /* no record: a scenery-lit cylinder, material 0x40, TEV x4 */
    unsigned parts=ml->info>>8&255;const ActorPose* c=parts && parts<=bones?actor+parts:actor;
    source_lights_w(s,actor->world,c->world,bones?actor[1].world:actor[0].world,ml,out);
}
/* Per weight set: each light's direction in the set's model space (scaled for raw s16 normals) and its colour
   times the attenuation at the set's origin. */
static float ws_dirs[ACTOR_WS_LIMIT][8][3],ws_cols[ACTOR_WS_LIMIT][8][3];
static SrcLights cur_lights;
static void ws_light(unsigned i,const float* m){
    const float inv=1.f/(16384.f*.0625f);
    float o[3]={m[3],m[7],m[11]};
    for(unsigned j=0;j<cur_lights.n;j++){
        const SrcLight* g=cur_lights.l+j;
        float L[3]={g->pos[0]-o[0],g->pos[1]-o[1],g->pos[2]-o[2]},d=sqrtf(L[0]*L[0]+L[1]*L[1]+L[2]*L[2]);
        float id=d>0?1.f/d:0;for(unsigned c=0;c<3;c++)L[c]*=id;
        float att=g->br;
        if(g->spot){float cs=-(L[0]*g->axis[0]+L[1]*g->axis[1]+L[2]*g->axis[2]);att*=m1_maxf(0,g->sa0+g->sa1*cs);}
        att/=g->k0+g->k1*d+g->k2*d*d;
        for(unsigned c=0;c<3;c++){ws_dirs[i][j][c]=(m[c]*L[0]+m[4+c]*L[1]+m[8+c]*L[2])*inv;ws_cols[i][j][c]=g->rgb[c]*att;}
    }
}
static void light_normals_source(const SourceVector* v,unsigned n,uint32_t* out){
    const unsigned nl=cur_lights.n;const float ar=cur_lights.amb[0],ag=cur_lights.amb[1],ab=cur_lights.amb[2];
    const float kr=cur_lights.k[0],kg=cur_lights.k[1],kb=cur_lights.k[2];
    for(unsigned i=0;i<n;i++,v++){
        const float (*D)[3]=ws_dirs[v->bone];const float (*C)[3]=ws_cols[v->bone];
        float x=v->xyz[0],y=v->xyz[1],z=v->xyz[2],r=ar,g=ag,b=ab;
        for(unsigned j=0;j<nl;j++){
            float d=x*D[j][0]+y*D[j][1]+z*D[j][2];
            if(d>0){r+=d*C[j][0];g+=d*C[j][1];b+=d*C[j][2];}
        }
        out[i]=0xff000000|m1_byte(kr*m1_minf(1.f,r))<<16|m1_byte(kg*m1_minf(1.f,g))<<8|m1_byte(kb*m1_minf(1.f,b));
    }
}
