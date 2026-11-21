#include <stdlib.h>
#include <dc/pvr/pvr_fog.h>
static const float identity_grid[]={1,0,0,0,0,1,0,0,0,0,1,0};
/* Two-dimensional layers record their TA words here when recording is on (HUD), else submit directly. */
static uint32_t* layer_record;static unsigned layer_words,layer_capacity;
static void layer_prim(const void* p){
    if(layer_record && layer_words+8<=layer_capacity){memcpy(layer_record+layer_words,p,32);layer_words+=8;}
    else pvr_prim((void*)p,32);
}
static void submit_header(const Scene* s,unsigned index){
    pvr_poly_hdr_t header __attribute__((aligned(32)));
    memcpy(&header,(const unsigned*)row(&s->header,index)+1,32);layer_prim(&header);
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
        p.u=uv[j&1?2:0];p.v=uv[j&2?3:1];p.argb=color;layer_prim(&p);
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
typedef struct {uint32_t slot,id,texture,type,anim,flags,tool;float pos[3],angle[3],size[3],rgba[4],parent[12];uint32_t hdr,fnv,pattern,width,height,blend;} NativeEffect;
typedef struct {float x,y,iw,rx,ry,angle;unsigned hdr,color;} Billboard;
static Billboard particles[1024];
#include "content_fx.inc"
static int depth_sort(const void* a,const void* b){
    float x=((const Billboard*)a)->iw,y=((const Billboard*)b)->iw;return (x>y)-(x<y);
}
void native_effects(NativeScene* s){
    const NativeEffect* e=(const void*)s->state[3];const float* c=(const float*)s->state[0];
    shz_mat4x4_t screen=projection_grid(c,identity_grid);shz_xmtrx_load_4x4(&screen);
    float near=c[18]/(c[17]-1);unsigned count=0;fx_frame();
    for(unsigned i=0;i<s->words[3]*4/sizeof(*e);i++){
        const NativeEffect* v=e+i;const float* a=v->parent;const float* b=v->pos;
        if(v->id==0x46){if(v->rgba[3]>0)fx_glow_driver(v);continue;}   /* eng-look: the glow filter's driver */
        if(v->hdr==~0u || !(v->rgba[3]>0))continue;
        float w[3];for(unsigned k=0;k<3;k++,a+=4)w[k]=a[0]*b[0]+a[1]*b[1]+a[2]*b[2]+a[3];
        shz_vec4_t q=shz_xmtrx_transform_vec4(shz_vec4_init(w[0],w[1],w[2],1));
        if(q.w<near || q.w>c[25])continue;
        float iw=1.f/q.w,x=q.x*iw,y=q.y*iw;
        float rx=fabsf(160*c[13]*v->size[0]*v->size[2]*iw),ry=fabsf(120*c[15]*v->size[1]*v->size[2]*iw);
        if(x+rx<0||y+ry<0||x-rx>640||y-ry>480||count==1024)continue;
        particle_slot[count]=v->slot;
        particles[count]=(Billboard){x,y,iw,rx,ry,v->angle[2]*.017453293f,v->hdr,fx_color(v)};   /* eng-look: TEV scale */
        fx_glow_note(v,particles+count);count++;
    }
    count=fx_cap(particles,count);   /* eng-look: density cap (CS_EFFECTS) */
    qsort(particles,count,sizeof(Billboard),depth_sort);
    static const float uv[]={0,0,1,1};unsigned last=~0u;
    for(unsigned i=0;i<count;i++){Billboard* b=particles+i;if(last!=b->hdr){last=b->hdr;submit_header(&s->assets,last);}
        rectangle(b->x,b->y,b->iw,b->rx,b->ry,b->angle,uv,b->color);}
    fx_glow_draw(s);   /* eng-look: the frame-alpha glow */
}
typedef struct {unsigned identity,tree,shape,hidden,hdr,fnv,mask[2];float pos[3],rot[3],w,h,color[4],uv[4];} Widget;
/* lane eng-e1h: each widget's own blend. The capture keeps the unit's blend_type in shape bits 8-15 (bench/r3_inputs.inc);
   id_sys.cpp IdCommonTrans sets GXSetBlendMode from its table: 0 (src alpha, 1 - src alpha), 1 (src alpha, one: the
   additive glows), 2 (one, one), 3 (destination colour, one), 4 (destination colour, zero: the darkening multiply). The
   pack bakes every widget's header with one blend (phase 5), so the additive gauge rings and the multiplied LCD
   backdrops were drawn as ordinary alpha blends: the gauge came out dim and the unlit digit segments showed ("10" as
   "88"). GX and PVR share the factor codes 0-7, so the header's TSP word takes the pair as it is. */
static const uint8_t hud_blend[5][2]={{4,5},{4,1},{1,1},{2,1},{2,0}};
/* Control and still pair (run-time lab arm, the E1 images' boot file HUDOLD): every widget with blend 0, the look before
   this lane, so one image gives both stills of the pair. */
int hud_blend_control;
static void submit_hud_header(const Scene* s,unsigned index,unsigned blend_type){
    pvr_poly_hdr_t header __attribute__((aligned(32)));
    memcpy(&header,(const unsigned*)row(&s->header,index)+1,32);
    if(blend_type<5){
        uint32_t* word=(uint32_t*)&header;   /* word 2: the TSP instruction, source factor bits 31-29, destination 28-26 */
        word[2]=(word[2]&~(0x3Fu<<26))|((uint32_t)hud_blend[blend_type][0]<<29)|((uint32_t)hud_blend[blend_type][1]<<26);
    }
    layer_prim(&header);
}
/* lane eng-e1i: the ammo digits (render/native_scene.h); lane eng-e1n: made here, once a picture, from the live count */
int (*hud_magazine_live)(unsigned*);
uint8_t hud_ammo_drawn[3]={0xff,0xff,0xff};
static int hud_digits_live;            /* this picture: the digit widgets draw the live digits */
static uint8_t hud_digit[3],hud_digit_shown;
static void hud_widget(const Scene* a,const Widget* q,float cx,float cy,float angle,float z){
    unsigned anchor=q->shape&15,hdr=q->hdr;
    if(anchor>=1 && anchor<=4){
        float ox=(anchor==1||anchor==4?.5f:-.5f)*q->w;
        float oy=(anchor<=2?-.5f:.5f)*q->h;
        float ca=cosf(angle),sa=sinf(angle);
        cx+=ca*ox-sa*oy;cy+=sa*ox+ca*oy;
    }
    /* lane eng-e1i: a digit widget (bake/hud_fix.py: mask[1] = the '0' picture's header + 1) draws the live digit */
    if(q->mask[1] && hud_digits_live){
        unsigned mark=(q->identity>>16)&255,cell=mark==0x0B?0:mark==0x0A?1:mark==0x17?2:3;
        if(cell<3){
            if(!(hud_digit_shown>>cell&1))return;
            hdr=q->mask[1]-1+hud_digit[cell];hud_ammo_drawn[cell]=hud_digit[cell];
        }
    }
    submit_hud_header(a,hdr,hud_blend_control?0:(q->shape>>8)&255);
    rectangle(320+cx,240-cy,z,.5f*q->w,.5f*q->h,-angle,q->uv,argb4(q->color));
}
/* The HUD is laid out every picture: its widget state changes every picture in both scenes, so a layout change
   flag (tried in e0s4a: record and compare) cost more than it saved.
   Lane eng-e1i, as id_sys.cpp does it: a unit's rot is in degrees (IDSystem converts rot * PI / 180; read as radians
   the lens sphere's light turned to the wrong side and the green ring's quarters pointed the wrong way); a unit takes
   its parent's matrix only when the parent is a group (type 1); and the draw order is the source's: IDSystem::unitTrans
   queues each visible root's children (by unit number, groups recursing) before the unit itself, and the order table
   draws the queue last-in first (so the name plates lie over the gauge frame and the digits over the lens backdrop).
   HUDOLD (the control and the "before" still) keeps the old reading: radians, every parent, deepest level first. */
void native_hud(NativeScene* s){
    const Widget* w=(const void*)(s->state[5]+4);
    unsigned count=(s->words[5]-4)*4/sizeof(*w);
    unsigned char visible[256]={0},group[256]={0};
    float x[256]={0},y[256]={0},angle[256]={0};
    const float unit=hud_blend_control?1.f:.017453293f;
    hud_ammo_drawn[0]=hud_ammo_drawn[1]=hud_ammo_drawn[2]=0xff;
    /* lane eng-e1n: the ammo digits from the live magazine count, split here (ones, tens, hundreds; the hundreds only
       when not 0), for this picture */
    hud_digits_live=hud_magazine_live && !hud_blend_control;
    if(hud_digits_live){
        unsigned n=0;
        const int shows=hud_magazine_live(&n);
        hud_digit[0]=(uint8_t)(n%10);hud_digit[1]=(uint8_t)(n/10%10);hud_digit[2]=(uint8_t)(n/100%10);
        hud_digit_shown=shows?(uint8_t)(hud_digit[2]?7:3):0;
    }
    /* layout: parents before children */
    for(unsigned lv=0;lv<12;lv++)for(unsigned i=0;i<count;i++){
        const Widget* q=w+i;if(((q->tree>>8)&255)!=lv)continue;
        unsigned parent=q->tree&255,id=q->identity&255;
        int inherit=parent!=255 && (hud_blend_control || group[parent]);
        visible[id]=(!q->hidden && (q->shape&0x80000) && (parent==255 || visible[parent]));
        group[id]=(q->tree>>16)==1;
        float a=inherit?angle[parent]:0,sn=sinf(a),cs=cosf(a);
        x[id]=(inherit?x[parent]:0)+cs*q->pos[0]-sn*q->pos[1];
        y[id]=(inherit?y[parent]:0)+sn*q->pos[0]+cs*q->pos[1];
        angle[id]=a+q->rot[2]*unit;
    }
    float z=.98f;
    if(!hud_blend_control){
        /* the source's order: post-order from the roots, drawn in reverse (depth rises with draw order) */
        unsigned char queue[256],slot[256],stack[256],next[256];unsigned n=0;
        for(unsigned i=0;i<256;i++)slot[i]=255;
        for(unsigned i=0;i<count;i++)slot[w[i].identity&255]=i;
        for(unsigned r=0;r<count && n<256;r++){
            const Widget* root=w+r;
            if((root->tree&255)!=255 || root->hidden || !(root->shape&0x80000))continue;
            unsigned depth=0;stack[0]=root->identity&255;next[0]=0;
            while(depth<255){
                unsigned u=stack[depth],c=next[depth];
                /* the next visible child of a group, by unit number */
                while(c<count && !(group[u] && (w[c].tree&255)==u && !w[c].hidden && (w[c].shape&0x80000)))c++;
                if(c<count){next[depth]=c+1;stack[++depth]=w[c].identity&255;next[depth]=0;continue;}
                if(n<256)queue[n++]=u;
                if(!depth)break;
                depth--;
            }
        }
        while(n--){
            unsigned id=queue[n];if(slot[id]==255)continue;
            const Widget* q=w+slot[id];
            if(group[id] || !visible[id] || q->hdr==~0u || !(q->color[3]>0))continue;
            hud_widget(&s->assets,q,x[id],y[id],angle[id],z);z+=1e-4f;
        }
    } else {
        /* HUDOLD: masked backdrops first, then every other widget deepest level first */
        for(unsigned pass=1;pass<3;pass++)
        for(unsigned lv=0;lv<12;lv++)for(unsigned i=0;i<count;i++){
            const Widget* q=w+i;if(((q->tree>>8)&255)!=11-lv)continue;
            unsigned id=q->identity&255;
            if((q->mask[0]!=0)!=(pass==1))continue;
            if(group[id] || !visible[id] || q->hdr==~0u || !(q->color[3]>0))continue;
            hud_widget(&s->assets,q,x[id],y[id],angle[id],z);z+=1e-4f;
        }
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
