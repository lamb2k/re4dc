#include "replay.h"
#include <sh4zam/shz_xmtrx.h>
#include <dc/sq.h>
#include <math.h>
#include <string.h>
typedef struct {float x,y,w,u,v; unsigned color;} Corner;
static Corner clip_cache[1024];
typedef struct {
    shz_mat4x4_t m;
    const float *pose,*camera,*bone_rows;
    unsigned bones,current;
    float near;
} Transform;
static void matrix(Transform *x,unsigned bone) {
    if(x->current==bone)return;
    x->current=bone;const float *a=x->pose,*p=x->camera+12,*v=p+7;
    float cx=640*(v[0]+.5f*v[2])/v[2],cy=480*(v[1]+.5f*v[3])/v[3];
    const float *b=x->bones?x->bone_rows+12*bone:NULL;
    for(unsigned c=0;c<4;c++){
        float ex=a[c],ey=a[4+c],ez=a[8+c];
        if(b){
            const float *k=b+3*c;
            ex=a[0]*k[0]+a[1]*k[1]+a[2]*k[2]+(c==3?a[3]:0);
            ey=a[4]*k[0]+a[5]*k[1]+a[6]*k[2]+(c==3?a[7]:0);
            ez=a[8]*k[0]+a[9]*k[1]+a[10]*k[2]+(c==3?a[11]:0);
        }
        x->m.elem[c*4]=320*p[1]*ex+(320*p[2]-cx)*ez;
        x->m.elem[c*4+1]=-240*p[3]*ey+(-240*p[4]-cy)*ez;
        x->m.elem[c*4+2]=ez;x->m.elem[c*4+3]=-ez;
    }
    shz_xmtrx_load_4x4(&x->m);
}
typedef struct {uint32_t ambient;float gain[3];unsigned enabled;} Light;
static Light lighting(const uint8_t *p,unsigned n){
    Light l={0xffffff,{0,0,0},0};
    if(!n)return l;
    const unsigned char *ambient=p+464,*mat=p+468;
    const unsigned *flags=(const unsigned*)(p+472);
    const float scale=*(const float*)(p+496);
    unsigned rgb[3];
    for(unsigned c=0;c<3;c++){
        float value=(flags[1]?ambient[c]/255.f:1.f)*mat[c]*scale;
        rgb[c]=(unsigned)fminf(255,value);
        for(unsigned i=0;flags[1] && i<8;i++)
            if(flags[0]&(1u<<i))l.gain[c]+=p[52*i+48+c]*(mat[c]/255.f)*scale;
    }
    l.ambient=(rgb[0]<<16)|(rgb[1]<<8)|rgb[2];l.enabled=flags[1] && flags[0];return l;
}
static inline unsigned shade(const Vertex *v,const Light* l){
    unsigned rgb=l->ambient;
    if(l->enabled){
        float d=fmaxf(0,v->normal[1]/32767.f);
        unsigned r=fminf(255,(rgb>>16)+d*l->gain[0]);
        unsigned g=fminf(255,((rgb>>8)&255)+d*l->gain[1]);
        unsigned b=fminf(255,(rgb&255)+d*l->gain[2]);rgb=(r<<16)|(g<<8)|b;
    }
    return (v->color&0xff000000)|rgb;
}
static inline Corner transform(const Vertex* v,const Light* light){
    shz_vec4_t q=shz_xmtrx_transform_vec4(shz_vec4_init(v->x,v->y,v->z,1));
    return (Corner){q.x,q.y,q.w,v->u,v->v,light?shade(v,light):v->color};
}
static inline void advance(pvr_vertex_t **sq){
    sq_flush(*sq);*sq=(pvr_vertex_t*)((uintptr_t)*sq^32);
}
static inline void emit(pvr_vertex_t **sq,Corner v,int end){
    pvr_vertex_t *dst=*sq;float iw=1.f/v.w;
    dst->flags=end?PVR_CMD_VERTEX_EOL:PVR_CMD_VERTEX;
    dst->x=v.x*iw;dst->y=v.y*iw;dst->z=iw;dst->u=v.u;dst->v=v.v;
    dst->argb=v.color;dst->oargb=0;advance(sq);
}
static Corner intersect(Corner a,Corner b,float near){
    float t=(near-a.w)/(b.w-a.w);
    Corner out={a.x+(b.x-a.x)*t,a.y+(b.y-a.y)*t,near,a.u+(b.u-a.u)*t,a.v+(b.v-a.v)*t,0};
    for(unsigned shift=0;shift<32;shift+=8){
        float start=(a.color>>shift)&255,stop=(b.color>>shift)&255;
        out.color|=(unsigned)(start+(stop-start)*t)<<shift;
    }
    return out;
}
static void clipped(pvr_vertex_t **sq,Corner a,Corner b,Corner c,float near){
    Corner out[4],tri[]={a,b,c};unsigned n=0;
    for(int i=0;i<3;i++){
        Corner prev=tri[(i+2)%3],cur=tri[i];int p=prev.w>=near,q=cur.w>=near;
        if(p!=q)out[n++]=intersect(prev,cur,near);
        if(q)out[n++]=cur;
    }
    if(n<3)return;
    emit(sq,out[0],0);emit(sq,out[1],0);
    if(n==4){emit(sq,out[3],0);emit(sq,out[2],1);}else emit(sq,out[2],1);
}
static void strips(pvr_vertex_t **sq,Transform *x,const uint8_t* begin,unsigned size,const Light* light,int screen){
    const uint8_t* end=begin+size;
    while(begin<end){
        const Strip *s=(const Strip*)begin;
        const Vertex *v=(const Vertex*)(s+1);begin=(const uint8_t*)(v+s->n);
        if(screen){
            for(unsigned i=0;i<s->n;i++){
                pvr_vertex_t* dest=*sq;dest->flags=i+1==s->n?PVR_CMD_VERTEX_EOL:PVR_CMD_VERTEX;
                dest->x=v[i].x;dest->y=v[i].y;dest->z=v[i].z;dest->u=v[i].u;dest->v=v[i].v;
                dest->argb=v[i].color;dest->oargb=0;advance(sq);
            }
            continue;
        }
        int front=0;
        if(s->bone!=65535){
            matrix(x,s->bone);
            float min=x->m.elem[15],max=min;
            for(unsigned j=0;j<3;j++){float w=x->m.elem[j*4+3],a=s->low[j]*w,b=s->high[j]*w;
                min+=fminf(a,b);max+=fmaxf(a,b);}
            if(max<x->near)continue;
            front=min>=x->near;
        }
        if(front){
            for(unsigned i=0;i<s->n;i++){
                __builtin_prefetch(v+i+2);
                emit(sq,transform(v+i,light),i+1==s->n);
            }
        }else{
            for(unsigned i=0;i<s->n;i++){
                if(s->bone==65535)matrix(x,v[i].bone);
                clip_cache[i]=transform(v+i,light);
            }
            for(unsigned i=2;i<s->n;i++){
                unsigned a=i-2,b=i-1;
                clipped(sq,clip_cache[i&1?b:a],clip_cache[i&1?a:b],clip_cache[i],x->near);
            }
        }
    }
}
void render_phase(const Scene* scene,const Picture* pic,unsigned phase){
    pvr_vertex_t *sq=(pvr_vertex_t*)sq_lock((void*)PVR_TA_INPUT);
    unsigned last=~0u,last_pose=~0u;
    const float* p=pic->camera+12;
    Transform x={.camera=pic->camera,.current=~0u,.near=p[6]/(p[5]-1.f)};
    for(unsigned i=0;i<pic->count[phase];i++){
        const unsigned* draw=row(&scene->draw,pic->ids[phase][i]);
        if(draw[0]!=last){
            last=draw[0];const unsigned *hdr=(unsigned*)row(&scene->header,last)+1;
            memcpy(sq,hdr,32);advance(&sq);
        }
        if(last_pose!=draw[2]){
            last_pose=draw[2];x.pose=row(&scene->pose,last_pose);x.bone_rows=x.pose+12;
            x.bones=bytes(&scene->pose,last_pose)/48;x.bones-=x.bones!=0;x.current=~0u;
        }
        unsigned lbytes=bytes(&scene->light,draw[3]);Light light=lighting(row(&scene->light,draw[3]),lbytes);
        strips(&sq,&x,row(&scene->geometry,draw[1]),bytes(&scene->geometry,draw[1]),lbytes?&light:NULL,!bytes(&scene->pose,draw[2]));
    }
    sq_wait();sq_unlock();
}
