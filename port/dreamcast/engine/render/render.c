#include "replay.h"
#include "fastm.h"
#include <sh4zam/shz_xmtrx.h>
#include <dc/sq.h>
#include <math.h>
#include <string.h>
typedef struct {float x,y,w,u,v; unsigned color;} Corner;
#ifndef M1_NATIVE /* the M1 recorded-draw path; the native bench keeps only the shared emit and clip helpers */

typedef struct {
    shz_mat4x4_t m;
    const float *pose,*camera,*bone_rows;
    unsigned bones,current;
    float near;
} Transform;
/* Design B retains the last two corners of the current strip to end or
   restart it at a near-plane crossing. Reuse composed bone transforms until
   the pose changes. Design A instead expands mixed strips through triangles. */
#ifndef M1_STREAM_STRIPS
#define M1_STREAM_STRIPS 1
#endif
#if M1_STREAM_STRIPS
static shz_mat4x4_t pose_matrix[256] __attribute__((aligned(32)));
static unsigned matrix_stamp[256],generation;
#endif
#if !M1_STREAM_STRIPS
static Corner clip_cache[1024];
#endif
static void matrix(Transform *x,unsigned bone) {
    if(x->current==bone)return;
    x->current=bone;
#if M1_STREAM_STRIPS
    if(bone<256 && matrix_stamp[bone]==generation){
        x->m=pose_matrix[bone];shz_xmtrx_load_4x4(&x->m);return;
    }
#endif
    const float *a=x->pose,*p=x->camera+12,*v=p+7;
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
#if M1_STREAM_STRIPS
    if(bone<256){pose_matrix[bone]=x->m;matrix_stamp[bone]=generation;}
#endif
    shz_xmtrx_load_4x4(&x->m);
}
typedef struct { float dir[3],rgb[3]; } Lamp;
typedef struct {
    const float *bones;
    unsigned n;
    float ambient[3],limit[3];
    Lamp lamp[8];
} Light;
static Light lighting(const uint8_t *p,unsigned bytes,const Transform *x){
    Light out={0};
    if(!bytes)return out;
    out.bones=x->bones?x->bone_rows:NULL;
    const unsigned *flags=(const unsigned*)(p+472);
    const float scale=*(const float*)(p+496);
    for(unsigned c=0;c<3;c++){
        out.limit[c]=p[468+c]*scale;
        out.ambient[c]=out.limit[c]*(flags[1]?p[464+c]/255.f:1.f);
    }
    const float *normal=(const float*)(p+416);
    if(normal[3]>1e29f)normal=x->pose;
    for(unsigned i=0;flags[1] && i<8;i++){
        if(!(flags[0]&(1u<<i)))continue;
        const float *l=(const float*)(p+52*i);
        float dx=l[0]-x->pose[3],dy=l[1]-x->pose[7],dz=l[2]-x->pose[11];
        float d2=dx*dx+dy*dy+dz*dz,d=sqrtf(d2),inv=d>0?1.f/d:0;
        dx*=inv;dy*=inv;dz*=inv;
        float gain=1;
        if(flags[5]==1){
            float cos=fmaxf(0,dx*l[3]+dy*l[4]+dz*l[5]);
            float den=l[9]+l[10]*d+l[11]*d2;
            gain=den>0?fmaxf(0,l[6]+cos*(l[7]+cos*l[8]))/den:0;
        }
        if(gain<=0)continue;
        Lamp *lamp=&out.lamp[out.n];
        for(unsigned c=0;c<3;c++){
            lamp->dir[c]=(normal[c]*dx+normal[4+c]*dy+normal[8+c]*dz)/32767.f;
            lamp->rgb[c]=out.limit[c]*p[52*i+48+c]*(gain/255.f);
            if(!flags[4])out.ambient[c]+=lamp->rgb[c];
        }
        if(flags[4])out.n++;
    }
    return out;
}
static inline unsigned shade(const Vertex *v,const Light* l){
    float rgb[3]={l->ambient[0],l->ambient[1],l->ambient[2]};
    float nx=v->normal[0],ny=v->normal[1],nz=v->normal[2];
    if(l->n && l->bones){
        const float *b=l->bones+12*(v->color&255U);
        float a=b[0]*nx+b[3]*ny+b[6]*nz,c=b[1]*nx+b[4]*ny+b[7]*nz;
        nz=b[2]*nx+b[5]*ny+b[8]*nz;nx=a;ny=c;
    }
    for(unsigned i=0;i<l->n;i++){
        const Lamp *p=&l->lamp[i];
        float dot=fmaxf(0,nx*p->dir[0]+ny*p->dir[1]+nz*p->dir[2]);
        for(unsigned c=0;c<3;c++)rgb[c]+=dot*p->rgb[c];
    }
    unsigned packed=0xff;
    for(unsigned c=0;c<3;c++)packed=(packed<<8)|(unsigned)fminf(255,fminf(l->limit[c],rgb[c]));
    return packed;
}
static inline Corner transform(const Vertex* v,const Light* light){
    shz_vec4_t q=shz_xmtrx_transform_vec4(shz_vec4_init(v->x,v->y,v->z,1));
    return (Corner){q.x,q.y,q.w,v->u,v->v,light?shade(v,light):v->color};
}
#endif
/* Store-queue burst of the 32 bytes just written. The asm names those bytes as its input instead of clobbering all
   memory (KOS sq_flush), so the compiler keeps pointers and loop state in registers across corners. */
typedef struct { uint32_t w[8]; } SqLine;
static inline void advance(pvr_vertex_t **sq){
    pvr_vertex_t* p=*sq;
    __asm__ __volatile__("pref @%1"::"m"(*(const SqLine*)p),"r"(p));
    *sq=(pvr_vertex_t*)((uintptr_t)p^32);
}
static inline void emit(pvr_vertex_t **sq,Corner v,int end){
    pvr_vertex_t *dst=*sq;float iw=m1_rcp_pos(v.w);
    dst->flags=end?PVR_CMD_VERTEX_EOL:PVR_CMD_VERTEX;
    dst->x=v.x*iw;dst->y=v.y*iw;dst->z=iw;dst->u=v.u;dst->v=v.v;
    dst->argb=v.color;dst->oargb=0;advance(sq);
}
static Corner intersect(Corner a,Corner b,float near){
    float t=(near-a.w)/(b.w-a.w);
    Corner out={a.x+(b.x-a.x)*t,a.y+(b.y-a.y)*t,near,a.u+(b.u-a.u)*t,a.v+(b.v-a.v)*t,0};
    for(unsigned shift=0;shift<32;shift+=8){
        float start=(a.color>>shift)&255,stop=(b.color>>shift)&255;
        out.color|=(uint32_t)(int)(start+(stop-start)*t)<<shift;
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
#ifndef M1_NATIVE
#if M1_STREAM_STRIPS
static void stream_clipped(pvr_vertex_t **sq, Transform *x, const Strip *s, const Vertex *v, const Light *light){
    Corner a={0},b={0};
    int open=0;
    for(unsigned i=0;i<s->n;i++){
        __builtin_prefetch(v+i+2);
        if(s->bone==65535)matrix(x,v[i].bone);
        Corner c=transform(v+i,light);
        if(i>=2){
            int inside=a.w>=x->near && b.w>=x->near && c.w>=x->near;
            if(inside){
                if(!open){
                    if(i&1)emit(sq,a,0);
                    emit(sq,a,0);
                }
                emit(sq,b,0);open=1;
            }else{
                if(open){emit(sq,b,1);open=0;}
                if(a.w>=x->near || b.w>=x->near || c.w>=x->near)
                    clipped(sq,i&1?b:a,i&1?a:b,c,x->near);
            }
        }
        a=b;b=c;
    }
    if(open)emit(sq,b,1);
}
#endif
static void strips(pvr_vertex_t **sq,Transform *x,const uint8_t* begin,unsigned size,const Light* light,int screen,int whole){
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
        int front=whole;
        if(s->bone!=65535){
            matrix(x,s->bone);
            if(!whole){float min=x->m.elem[15],max=min;
            for(unsigned j=0;j<3;j++){float w=x->m.elem[j*4+3],a=s->low[j]*w,b=s->high[j]*w;
                if(w>=0){min+=a;max+=b;}else{min+=b;max+=a;}}
            if(max<x->near)continue;
            front=min>=x->near;}
        }
        if(front){
            for(unsigned i=0;i<s->n;i++){
                __builtin_prefetch(v+i+2);
                emit(sq,transform(v+i,light),i+1==s->n);
            }
        }else{
#if M1_STREAM_STRIPS
            stream_clipped(sq,x,s,v,light);
#else
            for(unsigned i=0;i<s->n;i++){
                if(s->bone==65535)matrix(x,v[i].bone);
                clip_cache[i]=transform(v+i,light);
            }
            for(unsigned i=2;i<s->n;i++){
                unsigned a=i-2,b=i-1;
                clipped(sq,clip_cache[i&1?b:a],clip_cache[i&1?a:b],clip_cache[i],x->near);
            }
#endif
        }
    }
}
#include "indexed.inc"

void render_phase(const Scene* scene,const Picture* pic,unsigned phase){
    static const unsigned *last_env;
    if(phase==0)++picture_serial;
    if(phase==0 && pic->atmosphere && (pic->atmosphere!=last_env || pic->camera==row(&scene->frame,0))){
        const unsigned *env=pic->atmosphere;last_env=env;
        PVR_SET(PVR_FOG_TABLE_COLOR,env[1]);PVR_SET(PVR_FOG_DENSITY,env[2]);
        for(unsigned j=0;j<128;j++)PVR_SET(PVR_FOG_TABLE_BASE+4*j,env[4+j]);
    }
    pvr_vertex_t *sq=(pvr_vertex_t*)sq_lock((void*)PVR_TA_INPUT);
    unsigned last=~0u,last_pose=~0u;
    const float* p=pic->camera+12;
    Transform x={.camera=pic->camera,.current=~0u,.near=p[6]/(p[5]-1.f)};
    for(unsigned i=0;i<pic->count[phase];i++){
        unsigned id=pic->ids[phase][i];
        const unsigned* draw=row(&scene->draw,id&0x7fffffff);
        if(draw[0]!=last){
            last=draw[0];const unsigned *hdr=(unsigned*)row(&scene->header,last)+1;
            memcpy(sq,hdr,32);advance(&sq);
        }
        if(last_pose!=draw[2]){
            #if M1_STREAM_STRIPS
            ++generation;
#endif
            last_pose=draw[2];x.pose=row(&scene->pose,last_pose);x.bone_rows=x.pose+12;
            x.bones=bytes(&scene->pose,last_pose)/48;x.bones-=x.bones!=0;x.current=~0u;
        }
        unsigned lbytes=bytes(&scene->light,draw[3]);Light light;
        if(lbytes==500)light=lighting(row(&scene->light,draw[3]),lbytes,&x);
        const IndexedPart *g=row(&scene->geometry,draw[1]);
        if(bytes(&scene->geometry,draw[1])>=4 && g->magic==INDEX_MAGIC){indexed_part(&sq,&x,g,lbytes==500?&light:NULL,lbytes==136?row(&scene->light,draw[3]):NULL,bytes(&scene->draw,id&0x7fffffff)==24?draw+4:NULL);continue;}
        strips(&sq,&x,row(&scene->geometry,draw[1]),bytes(&scene->geometry,draw[1]),lbytes?&light:NULL,!bytes(&scene->pose,draw[2]),id>>31);
    }
    sq_wait();sq_unlock();
}

void draw_shadows(const Picture *pic){
    if(!pic->volume_bytes)return;
    pvr_list_begin(PVR_LIST_OP_MOD);
    pvr_vertex_t *sq=(pvr_vertex_t*)sq_lock((void*)PVR_TA_INPUT);
    for(unsigned i=0;i<pic->volume_bytes/4;i+=8){
        memcpy(sq,pic->volume+i,32);advance(&sq);
    }
    sq_wait();sq_unlock();pvr_list_finish();
}
#endif
#ifdef M1_NATIVE
#include "native_draw.inc"
#include "native_actor.inc"
#include "native_layers.inc"
#endif
