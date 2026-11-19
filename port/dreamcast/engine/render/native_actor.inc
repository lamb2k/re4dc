#include "native_scene.h"
typedef struct {unsigned role,index,identity,bone; float world[12];} ActorPose;
typedef struct {unsigned flags,type,kind,spot;float pos[3],dir[3],radius,intensity;uint8_t rgb[4];} NativeLamp;
typedef struct {uint8_t bone[3],count;float w[3];} SkinWeight;
typedef struct {unsigned role,hdr,at,size;} NativePart;
typedef struct {float dir[3],rgb[3];} Incident;
static shz_mat4x4_t skin_project[256] __attribute__((aligned(32)));
static float skin_world[256][12] __attribute__((aligned(32)));
static Corner projected_pool[2][4000] __attribute__((aligned(32)));
static uint32_t colors_pool[2][4000] __attribute__((aligned(32)));
static Corner* pool;
static uint32_t* lit_pool;
static uint8_t outcode_pool[2][4000],*outcodes;
volatile unsigned m1_part_counts[300][2];
extern volatile uint32_t m1_state[8];
static void multiply34(float* out,const float* a,const float* b){
    for(unsigned i=0;i<3;i++)for(unsigned j=0;j<4;j++)
        out[i*4+j]=a[4*i]*b[j]+a[4*i+1]*b[j+4]+a[4*i+2]*b[j+8]+(j==3?a[4*i+3]:0);
}
static unsigned model_lights(const NativeScene* s,const ActorPose* pose,Incident* lamps){
    unsigned used=0;float strength[3]={};
    const NativeLamp* source=(const void*)s->state[2];
    unsigned n=s->words[2]*4/sizeof(*source);
    for(unsigned i=0;i<n;i++){
        const NativeLamp* l=source+i;float dx=l->pos[0]-pose->world[3],dy=l->pos[1]-pose->world[7],dz=l->pos[2]-pose->world[11];
        float dd=dx*dx+dy*dy+dz*dz;
        if(!(l->radius>0) || dd>=l->radius*l->radius)continue;
        float d=sqrtf(fmaxf(dd,.001f)),gain=fmaxf(0,(1-d/l->radius)*l->intensity);
        float value=gain*(l->rgb[0]+l->rgb[1]+l->rgb[2]);
        unsigned k=0;while(k<used && strength[k]>=value)++k;
        if(k==3||value<=0)continue;
        if(used<3)++used;
        for(unsigned t=used-1;t>k;t--){lamps[t]=lamps[t-1];strength[t]=strength[t-1];}
        strength[k]=value;
        lamps[k]=(Incident){{dx/d,dy/d,dz/d},{gain*l->rgb[0],gain*l->rgb[1],gain*l->rgb[2]}};
    }
    return used;
}
static void model_pools(const NativeScene* s,const ActorPose* pose,const float* bind,const SkinWeight* w,
                        const SourceVector* pos,const SourceVector* norm,const unsigned* header){
    float (*bone)[12]= (float (*)[12])pose_matrix;
    for(unsigned b=0;b<header[0];b++)multiply34(bone[b],pose[b+1].world,bind+b*12);
    for(unsigned i=0;i<header[1];i++){
        float* m=skin_world[i];
        for(unsigned j=0;j<12;j++){
            float sum=0;for(unsigned k=0;k<w[i].count;k++)sum+=w[i].w[k]*bone[w[i].bone[k]][j];m[j]=sum;
        }
        skin_project[i]=projection_grid((const float*)s->state[0],m);
    }
    const float* camera=(const float*)s->state[0];float near=camera[18]/(camera[17]-1);
    unsigned last=~0u;
    for(unsigned i=0;i<header[2];i++){
        const SourceVector* v=pos+i;
        if(last!=v->bone){last=v->bone;shz_xmtrx_load_4x4(&skin_project[last]);}
        __builtin_prefetch(v+4);
        shz_vec4_t q=shz_xmtrx_transform_vec4(shz_vec4_init(v->xyz[0]*.0625f,v->xyz[1]*.0625f,v->xyz[2]*.0625f,1));
        pool[i]=(Corner){q.x,q.y,q.w,0,0,0};
        outcodes[i]=(q.x<0)|((q.y<0)<<1)|((q.x>640*q.w)<<2)|((q.y>480*q.w)<<3)|((q.w<near)<<4)|((q.w>camera[25])<<5);
    }
    Incident lamps[3];unsigned n=model_lights(s,pose,lamps);
    const uint8_t* ambient=(const uint8_t*)s->state[7]+4;
    // Fold the three incident colours into the bone's RGB matrix once. SH4ZAM then
    // evaluates all three channels together for each source normal in its pool.
    for(unsigned i=0;i<header[1];i++){
        const float* m=skin_world[i];shz_mat4x4_t* f=&skin_project[i];
        memset(f,0,sizeof(*f));f->elem[15]=1;
        for(unsigned channel=0;channel<3;channel++)f->elem[12+channel]=ambient[channel];
        for(unsigned j=0;j<n;j++){
            const float* d=lamps[j].dir;
            for(unsigned channel=0;channel<3;channel++){
                float color=lamps[j].rgb[channel];
                f->elem[12+channel]+=color*(pose->role==0?.57f:.3f);
                for(unsigned k=0;k<3;k++)
                    f->elem[4*k+channel]+=color*.3f*(m[k]*d[0]+m[k+4]*d[1]+m[k+8]*d[2])/16384.f;
            }
        }
    }
    last=~0u;
    for(unsigned i=0;i<header[3];i++){
        const SourceVector* v=norm+i;__builtin_prefetch(v+4);
        if(last!=v->bone){last=v->bone;shz_xmtrx_load_4x4(&skin_project[last]);}
        shz_vec4_t rgb=shz_xmtrx_transform_vec4(shz_vec4_init(v->xyz[0],v->xyz[1],v->xyz[2],1));
        unsigned r=(unsigned)fminf(255,fmaxf(0,rgb.x)),g=(unsigned)fminf(255,fmaxf(0,rgb.y)),b=(unsigned)fminf(255,fmaxf(0,rgb.z));
        lit_pool[i]=0xff000000|r<<16|g<<8|b;
    }
}
static Corner model_corner(const IndexCorner* v){
    Corner out=pool[v->position];out.u=v->u/32768.f;out.v=v->v/32768.f;out.color=lit_pool[v->normal];return out;
}
static unsigned model_index(const ActorPose* a){
    if(!a->role)return 0;
    if(a->role==2)return a->identity;
    unsigned type=a->identity>>8;
    if((a->identity&255)==0x12 && type==1)return 1;
    switch(type){case 3:return 3;case 4:return 4;case 11:return 5;default:return 2;}
}
void native_actor_pass(NativeScene* s,unsigned translucent){
    const ActorPose* pose=(const void*)s->state[1];const ActorPose* end=pose+s->words[1]/16;
    const float* camera=(const float*)s->state[0];float near=camera[18]/(camera[17]-1);
    pvr_vertex_t* sq=(pvr_vertex_t*)sq_lock((void*)PVR_TA_INPUT);
    volatile unsigned* census=m1_part_counts[(m1_state[1]-1)%300];
    if(!translucent)census[0]=census[1]=0;
    while(pose<end){
        const ActorPose* next=pose+1;while(next<end && next->bone)next++;
        unsigned model=model_index(pose);
        const unsigned* h=row(&s->models,model);
        if(next-pose<h[0]+1 || (translucent && model)){pose=next;continue;}
        const float* bind=(const void*)(h+6);
        const SkinWeight* w=(const void*)(bind+12*h[0]);
        const SourceVector* pos=(const void*)(w+h[1]),*norm=pos+h[2];
        const NativePart* parts=(const void*)(norm+h[3]);
        const uint8_t* data=(const void*)(parts+h[4]);
        outcodes=outcode_pool[model!=0];pool=projected_pool[model!=0];lit_pool=colors_pool[model!=0];
        if(!translucent)model_pools(s,pose,bind,w,pos,norm,h);
        for(unsigned i=0;i<h[4];i++){
            const NativePart* part=parts+i;
            if((part->role==7)!=translucent)continue;
            census[0]++;
            unsigned emitted=0;
            const uint8_t* p=data+part->at,*stop=p+part->size;
            while(p<stop){
                unsigned n=*(const unsigned*)p;const IndexCorner* v=(const void*)(p+4);
                unsigned common=63,combined=0;
                for(unsigned j=0;j<n;j++){unsigned code=outcodes[v[j].position];common&=code;combined|=code;}
                if(common){p=(const uint8_t*)(v+n);continue;}
                if(!emitted){
            const unsigned* hdr=(const unsigned*)row(&s->assets.header,part->hdr)+1;
            for(unsigned j=0;j<8;j++)((volatile unsigned*)sq)[j]=hdr[j];
            advance(&sq);
                    emitted=1;
                }
                int crosses=combined&16;
                if(!crosses){for(unsigned j=0;j<n;j++)emit(&sq,model_corner(v+j),j+1==n);}
                else for(unsigned j=2;j<n;j++)clipped(&sq,model_corner(v+j-2+(j&1)),model_corner(v+j-1-(j&1)),model_corner(v+j),near);
                p=(const uint8_t*)(v+n);
            }
            if(!emitted)census[1]++;
        }
        pose=next;
    }
    sq_wait();sq_unlock();
}
