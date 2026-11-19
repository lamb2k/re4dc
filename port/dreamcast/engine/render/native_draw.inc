// World drawing (E0 step 3). Included after the shared emit and clip helpers.
#include "native_world.h"
extern volatile uint32_t m1_state[8];
extern volatile uint32_t m1_room_serial;     /* native_open: a new room invalidates every change flag */
volatile uint32_t m1_world_reused,m1_hud_reused;
static shz_mat4x4_t projection_grid(const float* camera,const float* grid){
    const float* p=camera+12,*v=p+7;
    float cx=640*(v[0]+v[2]*.5f)/v[2],cy=480*(v[1]+v[3]*.5f)/v[3];
    shz_mat4x4_t m;
    for(unsigned j=0;j<4;++j){
        float e[3];
        for(unsigned i=0;i<3;i++){
            const float* a=camera+4*i;
            e[i]=a[0]*grid[j]+a[1]*grid[j+4]+a[2]*grid[j+8]+(j==3?a[3]:0);
        }
        m.elem[4*j]=320*p[1]*e[0]+(320*p[2]-cx)*e[2];
        m.elem[4*j+1]=-240*p[3]*e[1]+(-240*p[4]-cy)*e[2];
        m.elem[4*j+2]=0;m.elem[4*j+3]=-e[2];
    }
    return m;
}
/* The stage: one picture-ready TA vertex per selected vertex of the current meshlet (x/w, y/w, 1/w, u, v, argb),
   written once and copied to the store queue for every strip corner that uses it. 256 x 32 bytes = 8 KB. */
static pvr_vertex_t stage_ram[256] __attribute__((aligned(32)));
/* Survey arm (a): the stage in operand-cache RAM (8 KB, half the data cache), selected by /cd/ARMA at boot. */
#include <dc/cache.h>
__ocram static pvr_vertex_t stage_oc[256];
static pvr_vertex_t* stage=stage_ram;
/* 0: one stage loop per vertex (stage_sh4.S); 1: arm (a) OCRAM stage; 2: arm (b) small loops over 32-vertex blocks */
volatile uint32_t m1_arm;
void native_select_arm(unsigned arm){
    m1_arm=arm;
    if(arm==1){dcache_toggle_ocram(true);stage=stage_oc;}else stage=stage_ram;
}
/* Survey arm (b): three short loops over blocks of 32 vertices (transform; divide; attributes) in place of one. */
static void stage_blocks(pvr_vertex_t* st,const uint16_t* r,const int16_t* vtx,const uint32_t* c,unsigned n,const float* uv){
    static shz_vec4_t tmp[32] __attribute__((aligned(32)));
    float u0=uv[0],v0=uv[1],du=uv[2],dv=uv[3];
    for(unsigned b=0;b<n;b+=32,st+=32,r+=32,c+=32){
        unsigned m=n-b<32?n-b:32;
        for(unsigned i=0;i<m;i++){const int16_t* v=vtx+6*r[i];tmp[i]=shz_xmtrx_transform_vec4(shz_vec4_init(v[0],v[1],v[2],1));}
        for(unsigned i=0;i<m;i++){float iw=m1_rcp_pos(tmp[i].w);st[i].x=tmp[i].x*iw;st[i].y=tmp[i].y*iw;st[i].z=iw;}
        for(unsigned i=0;i<m;i++){const int16_t* v=vtx+6*r[i];
            st[i].flags=PVR_CMD_VERTEX;st[i].u=u0+du*v[3];st[i].v=v0+dv*v[4];st[i].argb=c[i];st[i].oargb=0;}
    }
}
static float stage_w[256];
static uint8_t stage_near[256];
static shz_mat4x4_t world_pv __attribute__((aligned(32)));
#define PLACE_LIMIT 512
static shz_mat4x4_t place_matrix[PLACE_LIMIT] __attribute__((aligned(32)));
static unsigned place_stamp[PLACE_LIMIT],world_serial;
volatile unsigned m1_world_counts[300][4];   /* pieces, staged vertices, corners, clipped strips */
static unsigned count_staged,count_corners,count_clipped;

/* stage_sh4.S: stages an even count (one vertex of overrun into the next range, which is staged later or unused). */
extern void m1_stage_world(pvr_vertex_t* out,const uint16_t* remap,const int16_t* vertices,const uint32_t* color,unsigned pairs,const float* uvp);
static void stage_range(const uint16_t* vertices,const uint16_t* remap,const uint32_t* color,unsigned first,unsigned n,
                        const float* uv,float near,int boundary){
    pvr_vertex_t* st=stage+first;const uint16_t* r=remap+first;const uint32_t* c=color+first;
    float u0=uv[0],v0=uv[1],du=uv[2],dv=uv[3];
    count_staged+=n;
    if(!boundary){
        if(m1_arm==2)stage_blocks(st,r,(const int16_t*)vertices,c,n,uv);
        else m1_stage_world(st,r,(const int16_t*)vertices,c,(n+1)/2,uv);
        return;
    }
    for(unsigned i=0;i<n;i++,st++){
        const int16_t* v=(const int16_t*)vertices+6*r[i];
        shz_vec4_t q=shz_xmtrx_transform_vec4(shz_vec4_init(v[0],v[1],v[2],1));
        float iw=m1_rcp_pos(q.w);
        float x=q.x*iw,y=q.y*iw,tu=u0+du*v[3],tv=v0+dv*v[4];
        uint32_t* o=(uint32_t*)&st->argb;
        o[0]=c[i];o[1]=0;st->flags=PVR_CMD_VERTEX;
        /* five float stores by pre-decrement from argb back to x: one instruction each (fmov has no displacement form) */
        __asm__("fmov.s %2,@-%0\n\tfmov.s %3,@-%0\n\tfmov.s %4,@-%0\n\tfmov.s %5,@-%0\n\tfmov.s %6,@-%0"
                :"+r"(o),"=m"(*st):"f"(tv),"f"(tu),"f"(iw),"f"(y),"f"(x));
        if(boundary){stage_w[first+i]=q.w;stage_near[first+i]=q.w<near;}
    }
}
/* One staged vertex to the store queue as four 64-bit FPU moves (FPSCR.SZ=1 inside the asm only): 8 load/store
   slots instead of 16. Stage and store-queue lines are 32-byte aligned. */
static inline pvr_vertex_t* copy_vertex(pvr_vertex_t* sq,const pvr_vertex_t* s){
    const pvr_vertex_t* src=s;pvr_vertex_t* end=sq+1;
    __asm__("fschg\n\t"
            "fmov @%1+,dr0\n\tfmov @%1+,dr2\n\tfmov @%1+,dr4\n\tfmov @%1+,dr6\n\t"
            "fmov dr6,@-%0\n\tfmov dr4,@-%0\n\tfmov dr2,@-%0\n\tfmov dr0,@-%0\n\t"
            "fschg"
            :"+r"(end),"+r"(src),"=m"(*(SqLine*)sq):"m"(*(const SqLine*)s)
            :"fr0","fr1","fr2","fr3","fr4","fr5","fr6","fr7");
    return sq;
}
static inline pvr_vertex_t* sq_next(pvr_vertex_t* sq){
    __asm__ __volatile__("pref @%1"::"m"(*(const SqLine*)sq),"r"(sq));
    return (pvr_vertex_t*)((uintptr_t)sq^32);
}
/* Strips of one group, all corners in front of the near plane. The stage's flags word is PVR_CMD_VERTEX; the last
   corner of each strip gets the end-of-strip flag. */
static __attribute__((noinline)) pvr_vertex_t* copy_strips(pvr_vertex_t* sq,const uint8_t* s,const uint8_t* end){
    unsigned corners=0;
    while(s<end){
        unsigned n=*s++;corners+=n;
        for(unsigned k=1;k<n;k++){sq=sq_next(copy_vertex(sq,stage+*s++));}
        copy_vertex(sq,stage+*s++);((uint32_t*)sq)[0]=PVR_CMD_VERTEX_EOL;sq=sq_next(sq);
    }
    count_corners+=corners;
    return sq;
}
static inline Corner stage_corner(unsigned i){
    const pvr_vertex_t* s=stage+i;float w=stage_w[i],mag=w<0?-w:w;
    return (Corner){s->x*mag,s->y*mag,w,s->u,s->v,s->argb};
}
/* Strips of one group in a meshlet that crosses the near plane: strips wholly in front are copied, the others
   are clipped triangle by triangle. */
static __attribute__((noinline)) pvr_vertex_t* clip_strips(pvr_vertex_t* sq,const uint8_t* s,const uint8_t* end,float near){
    while(s<end){
        unsigned n=*s;unsigned any=0;
        for(unsigned k=1;k<=n;k++)any|=stage_near[s[k]];
        if(!any){sq=copy_strips(sq,s,s+1+n);s+=1+n;continue;}
        s++;count_clipped++;count_corners+=n;
        Corner a=stage_corner(s[0]),b=stage_corner(s[1]);
        for(unsigned k=2;k<n;k++){Corner c=stage_corner(s[k]);clipped(&sq,k&1?b:a,k&1?a:b,c,near);a=b;b=c;}
        s+=n;
    }
    return sq;
}
static __attribute__((noinline)) pvr_vertex_t* native_piece(pvr_vertex_t* sq,const NativeWorld* w,const NativePiece* piece,float near){
    const uint8_t* mesh=w->mesh;const uint32_t* h=(const void*)mesh;
    const uint8_t* let=mesh+h[12]+28*piece->meshlet;
    const uint32_t* l=(const void*)let;const uint16_t* desc=(const void*)(let+12);
    const uint8_t* strip=mesh+h[14]+l[1];
    if(desc[1]&32768)strip+=2*desc[0];
    const uint16_t* vertices=(const void*)(mesh+h[13]+12*l[0]);
    const float* uv=(const void*)(mesh+h[11]+36*piece->part+20);
    const NativeMeshletRt* rt=w->rt+piece->meshlet;const uint16_t* remap=w->rt_remap+rt->remap;
    const uint32_t* color=w->rt_color+rt->remap;
    unsigned G=w->group_count;const uint8_t* range=w->rt_range+2*G*piece->meshlet;
    int boundary=piece->near_class!=1;
    unsigned sel=piece->groups;
    if(rt->full)stage_range(vertices,remap,color,0,rt->count,uv,near,boundary);
    else for(unsigned g=0;g<G;g++)if(sel>>g&1)stage_range(vertices,remap,color,range[2*g],range[2*g+1],uv,near,boundary);
    if(!w->group_bytes)
        return boundary?clip_strips(sq,strip,strip+l[2],near):copy_strips(sq,strip,strip+l[2]);
    const uint16_t* group=(const uint16_t*)(w->groups+32+16*(piece->meshlet*G)+12);
    unsigned before=0;
    for(unsigned g=0;g<G;g++,group+=8){
        unsigned after=*group;
        if(sel>>g&1)sq=boundary?clip_strips(sq,strip+before,strip+after,near):copy_strips(sq,strip+before,strip+after);
        before=after;
    }
    return sq;
}
static NativePiece selected[8192], ordered[8192];
static unsigned offsets[1025], list_offsets[4];
static uint8_t header_list[1024];
static unsigned lists_for=~0u;
int native_prepare_world(const NativeWorld* w,const float* camera,unsigned materials){
    if(materials>1024 || w->place_count>PLACE_LIMIT)return 0;
    if(lists_for!=m1_room_serial){   /* per room (the scene struct and pack buffer are reused across rooms) */
        memset(header_list,0,sizeof(header_list));
        for(unsigned i=0;i<((const uint32_t*)w->mesh)[5];i++)header_list[w->materials[i].header]=w->materials[i].phase;
        lists_for=m1_room_serial;
    }
    /* Change flag: an unmoved camera keeps last picture's selection, order and placement matrices. */
    static uint32_t last_camera[26];static unsigned last_room=~0u;
    if(last_room==m1_room_serial && !memcmp(last_camera,camera,sizeof(last_camera))){
        count_staged=count_corners=count_clipped=0;m1_world_reused++;
        return 1;
    }
    int n=native_world_select(w,camera,2.f,selected,8192);
    if(n<0)return 0;
    memcpy(last_camera,camera,sizeof(last_camera));last_room=m1_room_serial;
    static const float identity[]={1,0,0,0,0,1,0,0,0,0,1,0};
    world_pv=projection_grid(camera,identity);++world_serial;
    count_staged=count_corners=count_clipped=0;
    unsigned start=0;
    // Stable counting sort by list then material, retaining cell order for ties.
    memset(offsets,0,4*materials);
    for(int i=0;i<n;i++)offsets[selected[i].header]++;
    for(unsigned phase=0;phase<3;phase++){
        list_offsets[phase]=start;
        for(unsigned k=0;k<materials;k++)if(header_list[k]==phase){unsigned v=offsets[k];offsets[k]=start;start+=v;}
    }
    list_offsets[3]=start;
    for(int i=0;i<n;i++)ordered[offsets[selected[i].header]++]=selected[i];
    return 1;
}
static void load_place(const NativeWorld* w,unsigned place){
    shz_mat4x4_t* m=place_matrix+place;
    if(place_stamp[place]!=world_serial){
        const float* g=w->places[place].grid;
        shz_xmtrx_load_4x4(&world_pv);
        float bias[3];   /* staged coordinates are value-32768 (load-time bias) */
        for(unsigned r=0;r<3;r++)bias[r]=g[4*r+3]+32768.f*(g[4*r]+g[4*r+1]+g[4*r+2]);
        for(unsigned c=0;c<4;c++){
            shz_vec4_t v=c<3?shz_xmtrx_transform_vec4(shz_vec4_init(g[c],g[4+c],g[8+c],0.f))
                            :shz_xmtrx_transform_vec4(shz_vec4_init(bias[0],bias[1],bias[2],1.f));
            m->elem[4*c]=v.x;m->elem[4*c+1]=v.y;m->elem[4*c+2]=v.z;m->elem[4*c+3]=v.w;
        }
        place_stamp[place]=world_serial;
    }
    shz_xmtrx_load_4x4(m);
}
void native_world_pass(Scene* s,const NativeWorld* w,const float* camera,unsigned phase){
    unsigned last_place=~0u,last_header=~0u;
    float near=camera[18]/(camera[17]-1);
    pvr_vertex_t *sq=(pvr_vertex_t*)sq_lock((void*)PVR_TA_INPUT);
    for(unsigned k=list_offsets[phase];k<list_offsets[phase+1];k++){
        NativePiece* p=ordered+k;
        if(last_header!=p->header){
            last_header=p->header;const unsigned* hdr=(const unsigned*)row(&s->header,last_header)+1;
            for(unsigned j=0;j<8;j++)((volatile unsigned*)sq)[j]=hdr[j];
            advance(&sq);
        }
        if(last_place!=p->placement){last_place=p->placement;load_place(w,last_place);}
        sq=native_piece(sq,w,p,near);
    }
    sq_wait();sq_unlock();
    if(phase==2){
        volatile unsigned* c=m1_world_counts[(m1_state[1]-1)%300];
        c[0]=list_offsets[3];c[1]=count_staged;c[2]=count_corners;c[3]=count_clipped;
    }
}
