#include <stdlib.h>
#include <dc/pvr/pvr_fog.h>
static const float identity_grid[]={1,0,0,0,0,1,0,0,0,0,1,0};
static void submit_header(const Scene* s,unsigned index){
    pvr_poly_hdr_t header __attribute__((aligned(32)));
    memcpy(&header,(const unsigned*)row(&s->header,index)+1,32);pvr_prim(&header,32);
}
static uint32_t argb4(const float* c){
    uint32_t v=0;
    for(unsigned i=0;i<4;i++)v=(v<<8)|m1_byte(c[(i+3)&3]);
    return v;
}
static void rectangle(float x,float y,float z,float dx,float dy,float angle,const float uv[4],unsigned color){
    pvr_vertex_t p __attribute__((aligned(32)))={0};
    float sn=sinf(angle),cs=cosf(angle);
    for(unsigned j=0;j<4;j++){
        float a=(j&1)?dx:-dx,b=(j&2)?dy:-dy;
        p.flags=j==3?PVR_CMD_VERTEX_EOL:PVR_CMD_VERTEX;
        p.x=x+cs*a-sn*b;p.y=y+sn*a+cs*b;p.z=z;
        p.u=uv[j&1?2:0];p.v=uv[j&2?3:1];p.argb=color;pvr_prim(&p,32);
    }
}
void native_sky(NativeScene* s){
    const float* c=(const float*)s->state[0];
    const float* env=(const float*)s->state[7];
    const uint8_t* rgba=(const uint8_t*)(env+6);
    static float saved[3];static unsigned saved_color;
    if(saved[0]!=env[4]||saved[1]!=env[5]||saved[2]!=c[25]||saved_color!=s->state[7][6]){
        float table[129];float far=c[25];
        for(unsigned j=0;j<129;j++){
            float d=j<128?(float)(1u<<(j>>4))*(1.f+(j&15)/16.f):256.f;
            float z=far/d;
            float f=m1_clampf((z-env[4])/m1_maxf(1,env[5]-env[4]),0,1);
            float ramp=m1_clampf((z/far-.78f)/.22f,0,1);
            table[j]=f+(1-f)*ramp*ramp*(3-2*ramp);
        }
        pvr_fog_table_color(1,rgba[0]/255.f,rgba[1]/255.f,rgba[2]/255.f);
        pvr_fog_far_depth(far);pvr_fog_table_custom(table);
        saved[0]=env[4];saved[1]=env[5];saved[2]=far;saved_color=s->state[7][6];
    }
    submit_header(&s->assets,0);
    pvr_vertex_t v __attribute__((aligned(32)))={0};float first=0;
    for(unsigned j=0;j<4;j++){
        float xc=((j&1?1.f:-1.f)+c[14])/c[13],yc=((j&2?-1.f:1.f)+c[16])/c[15];
        float dx=c[0]*xc+c[4]*yc-c[8],dy=c[1]*xc+c[5]*yc-c[9],dz=c[2]*xc+c[6]*yc-c[10];
        float u=atan2f(dx,dz)*.15915494f;
        if(!j){first=u;}else{u-=floorf(u-first+.5f);}
        float angle=atan2f(dy,sqrtf(dx*dx+dz*dz))*57.29578f;
        v.flags=j==3?PVR_CMD_VERTEX_EOL:PVR_CMD_VERTEX;v.x=j&1?640:0;v.y=j&2?480:0;v.z=1.f/c[25];
        v.argb=0xffffffff;v.u=u;v.v=(s->sky_top-angle)/(s->sky_top-s->sky_bottom);pvr_prim(&v,32);
    }
}
typedef struct {uint32_t slot,id,texture,type,anim,flags,tool;float pos[3],angle[3],size[3],rgba[4],parent[12];uint32_t hdr,fnv,pattern,width,height;} NativeEffect;
typedef struct {float x,y,iw,rx,ry,angle;unsigned hdr,color;} Billboard;
static Billboard particles[1024];
static int depth_sort(const void* a,const void* b){
    float x=((const Billboard*)a)->iw,y=((const Billboard*)b)->iw;return (x>y)-(x<y);
}
void native_effects(NativeScene* s){
    const NativeEffect* e=(const void*)s->state[3];const float* c=(const float*)s->state[0];
    shz_mat4x4_t screen=projection_grid(c,identity_grid);shz_xmtrx_load_4x4(&screen);
    float near=c[18]/(c[17]-1);unsigned count=0;
    for(unsigned i=0;i<s->words[3]*4/sizeof(*e);i++){
        const NativeEffect* v=e+i;const float* a=v->parent;const float* b=v->pos;
        if(v->hdr==~0u || !(v->rgba[3]>0) || v->id==0x46)continue;
        float w[3];for(unsigned k=0;k<3;k++,a+=4)w[k]=a[0]*b[0]+a[1]*b[1]+a[2]*b[2]+a[3];
        shz_vec4_t q=shz_xmtrx_transform_vec4(shz_vec4_init(w[0],w[1],w[2],1));
        if(q.w<near || q.w>c[25])continue;
        float iw=1.f/q.w,x=q.x*iw,y=q.y*iw;
        float rx=fabsf(160*c[13]*v->size[0]*v->size[2]*iw),ry=fabsf(120*c[15]*v->size[1]*v->size[2]*iw);
        if(x+rx<0||y+ry<0||x-rx>640||y-ry>480||count==1024)continue;
        particles[count++]=(Billboard){x,y,iw,rx,ry,v->angle[2]*.017453293f,v->hdr,argb4(v->rgba)};
    }
    qsort(particles,count,sizeof(Billboard),depth_sort);
    static const float uv[]={0,0,1,1};unsigned last=~0u;
    for(unsigned i=0;i<count;i++){Billboard* b=particles+i;if(last!=b->hdr){last=b->hdr;submit_header(&s->assets,last);}
        rectangle(b->x,b->y,b->iw,b->rx,b->ry,b->angle,uv,b->color);}
}
typedef struct {unsigned identity,tree,shape,hidden,hdr,fnv,mask[2];float pos[3],rot[3],w,h,color[4],uv[4];} Widget;
void native_hud(NativeScene* s){
    const Widget* w=(const void*)(s->state[5]+4);
    unsigned count=(s->words[5]-4)*4/sizeof(*w);
    unsigned char visible[256]={0};
    float x[256]={0},y[256]={0},angle[256]={0};
    for(unsigned level=0;level<12;level++)for(unsigned i=0;i<count;i++){
        const Widget* q=w+i;if(((q->tree>>8)&255)!=level)continue;
        unsigned parent=q->tree&255,id=q->identity&255;
        visible[id]=(!q->hidden && (q->shape&0x80000) && (parent==255 || visible[parent]));
        float a=parent==255?0:angle[parent],sn=sinf(a),cs=cosf(a);
        x[id]=(parent==255?0:x[parent])+cs*q->pos[0]-sn*q->pos[1];
        y[id]=(parent==255?0:y[parent])+sn*q->pos[0]+cs*q->pos[1];
        angle[id]=a+q->rot[2];
        if((q->tree>>16)==1 || !visible[id] || q->hdr==~0u || !(q->color[3]>0))continue;
        float cx=x[id],cy=y[id];unsigned anchor=q->shape&15;
        if(anchor>=1 && anchor<=4){
            float ox=(anchor==1||anchor==4?.5f:-.5f)*q->w;
            float oy=(anchor<=2?-.5f:.5f)*q->h;
            float ca=cosf(angle[id]),sa=sinf(angle[id]);
            cx+=ca*ox-sa*oy;cy+=sa*ox+ca*oy;
        }
        submit_header(&s->assets,q->hdr);
        rectangle(320+cx,240-cy,.99f,.5f*q->w,.5f*q->h,-angle[id],q->uv,argb4(q->color));
    }
    const uint32_t* text=s->state[6];unsigned prior=~0u;
    float pen=0,baseline=0;
    for(unsigned i=0;i<s->words[6]/15;i++,text+=15){
        if(text[1]!=prior){prior=text[1];pen=(int)text[2];baseline=(int)text[3];}
        if(text[7]==~0u)continue;
        unsigned cols=text[9]/text[11];
        float left=(int)text[13],right=(int)text[14];
        float u=(text[0]%cols)*text[11],v=(text[0]/cols)*text[12];
        float uv[]={(u+left)/text[9],v/text[10],(u+right)/text[9],(v+text[12])/text[10]};
        submit_header(&s->assets,text[7]);float w=text[4],h=text[5];
        unsigned color=(text[6]>>8)|(text[6]<<24);
        rectangle(pen+.5f*w,baseline+.5f*h,.999f,.5f*w,.5f*h,0,uv,color);
        pen+=w;
    }
}
typedef struct {uint32_t role,index;float xyz[3];} ShadowSource;
typedef struct {float x,y,w;} VolumePoint;
typedef struct {VolumePoint p[3];} VolumeTri;
static void volume_tri(VolumeTri* list,unsigned* n,VolumePoint a,VolumePoint b,VolumePoint c){
    list[(*n)++]=(VolumeTri){{a,b,c}};
}
static VolumePoint cut_at(VolumePoint a,VolumePoint b,float near){
    float t=(near-a.w)/(b.w-a.w);return (VolumePoint){a.x+t*(b.x-a.x),a.y+t*(b.y-a.y),near};
}
static void volume_face(VolumeTri* tri,unsigned* n,const VolumePoint* points,const unsigned* indices,unsigned count,float near,VolumePoint* cap,unsigned* nc){
    VolumePoint polygon[12];unsigned size=0;VolumePoint a=points[indices[count-1]];
    for(unsigned j=0;j<count;j++){
        VolumePoint b=points[indices[j]];
        if((a.w>=near)!=(b.w>=near)){
            VolumePoint q=cut_at(a,b,near);polygon[size++]=q;
            unsigned i=0;while(i<*nc && (fabsf(q.x-cap[i].x)>.5f||fabsf(q.y-cap[i].y)>.5f))++i;
            if(i==*nc && i<16)cap[(*nc)++]=q;
        }
        if(b.w>=near)polygon[size++]=b;
        a=b;
    }
    for(unsigned j=2;j<size;j++)volume_tri(tri,n,polygon[0],polygon[j-1],polygon[j]);
}
void native_shadows(NativeScene* s){
    static pvr_mod_hdr_t normal,last;static int ready;
    if(!ready){pvr_mod_compile(&normal,PVR_LIST_OP_MOD,PVR_MODIFIER_OTHER_POLY,PVR_CULLING_NONE);
        pvr_mod_compile(&last,PVR_LIST_OP_MOD,PVR_MODIFIER_INCLUDE_LAST_POLY,PVR_CULLING_NONE);ready=1;}
    const float* c=(const float*)s->state[0];shz_mat4x4_t m=projection_grid(c,identity_grid);shz_xmtrx_load_4x4(&m);
    const ShadowSource* caster=(const void*)s->state[4];unsigned n=s->words[4]/5;
    pvr_list_begin(PVR_LIST_OP_MOD);
    for(unsigned i=0;i<n;i++){
        const float* p=caster[i].xyz;
        VolumePoint pts[16];float near=c[18]/(c[17]-1);unsigned front=0,distant=0;
        ActorPose origin={0};origin.world[3]=p[0];origin.world[7]=p[1];origin.world[11]=p[2];
        Incident incident[3];unsigned lit=model_lights(s,&origin,incident);
        float sx=0,sz=0;
        if(lit && incident[0].dir[1]>.03f){float scale=fminf(1800,1700/incident[0].dir[1]);sx=-incident[0].dir[0]*scale;sz=-incident[0].dir[2]*scale;}
        float radius=caster[i].role?420:378;
        for(unsigned j=0;j<16;j++){
            float a=(j&7)*.78539816f,x=cosf(a)*radius,z=sinf(a)*radius;
            if(x*sx+z*sz>0){x+=sx;z+=sz;}
            shz_vec4_t q=shz_xmtrx_transform_vec4(shz_vec4_init(p[0]+x,p[1]+(j<8?250:-1200),p[2]+z,1));
            pts[j]=(VolumePoint){q.x,q.y,q.w};front+=q.w>=near;distant+=q.w>15000;
        }
        if(!front||distant==16)continue;
        VolumeTri triangles[80];VolumePoint cap[16];unsigned ntri=0,nc=0;
        for(unsigned face=0;face<10;face++){
            unsigned ix[8],count=face<2?8:4;
            if(face<2)for(unsigned j=0;j<8;j++)ix[j]=face?15-j:j;
            else{unsigned j=face-2,k=(j+1)&7;ix[0]=j;ix[1]=j+8;ix[2]=k+8;ix[3]=k;}
            volume_face(triangles,&ntri,pts,ix,count,near,cap,&nc);
        }
        if(nc>=3){
            float cx=0,cy=0,angles[16];
            for(unsigned j=0;j<nc;j++){cx+=cap[j].x;cy+=cap[j].y;}cx/=nc;cy/=nc;
            for(unsigned j=0;j<nc;j++){
                VolumePoint v=cap[j];float a=atan2f(v.y-cy,v.x-cx);unsigned k=j;
                for(;k && angles[k-1]>a;k--){cap[k]=cap[k-1];angles[k]=angles[k-1];}
                cap[k]=v;angles[k]=a;
            }
            for(unsigned j=2;j<nc;j++)volume_tri(triangles,&ntri,cap[0],cap[j-1],cap[j]);
        }
        if(!ntri)continue;
        pvr_prim(&normal,32);
        for(unsigned t=0;t<ntri;t++){
            if(t+1==ntri)pvr_prim(&last,32);
            pvr_modifier_vol_t v __attribute__((aligned(32)))={0};v.flags=PVR_CMD_VERTEX_EOL;
            float* out=&v.ax;
            for(unsigned j=0;j<3;j++){VolumePoint p=triangles[t].p[j];float iw=1.f/p.w;
                *out++=p.x*iw;*out++=p.y*iw;*out++=iw;}
            pvr_prim(&v,64);
        }
    }
    pvr_list_finish();
}
