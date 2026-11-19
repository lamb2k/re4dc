// Included with the bench strip clipper. Transforms quantized coordinates directly.
#include "native_world.h"
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
static uint32_t world_color(uint16_t c,unsigned flags){
    if(flags&1)return (((c&15)|((c&240)<<4)|((c&3840)<<8)|((unsigned)(c&61440)<<12))*17);
    unsigned rgb=((c&31)<<3)|((c&992)<<6)|((c&31744)<<9);
    return 0xff000000|rgb|((rgb>>5)&0x070707);
}
static Corner unique_world[256] __attribute__((aligned(32)));
static void native_piece(pvr_vertex_t** sq,const NativeWorld* w,const NativePiece* piece,float near){
    const uint8_t* mesh=w->mesh;const uint32_t* h=(const void*)mesh;
    const uint8_t* let=mesh+h[12]+28*piece->meshlet;
    const uint32_t* l=(const void*)let;const uint16_t* desc=(const void*)(let+12);
    const uint8_t* strip=mesh+h[14]+l[1];const uint16_t* remap=NULL;
    if(desc[1]&32768){remap=(const void*)strip;strip+=2*desc[0];}
    const uint16_t* vertices=(const void*)(mesh+h[13]+12*l[0]);
    const float* uv=(const void*)(mesh+h[11]+36*piece->part+20);
    unsigned flags=w->materials[piece->part].flags;
    for(unsigned i=0;i<desc[0];i++){
        const uint16_t* v=vertices+6*(remap?remap[i]:i);
        __builtin_prefetch(v+16);
        shz_vec4_t q=shz_xmtrx_transform_vec4(shz_vec4_init(v[0],v[1],v[2],1));
        unique_world[i]=(Corner){q.x,q.y,q.w,uv[0]+uv[2]*v[3],uv[1]+uv[3]*v[4],world_color(v[5],flags)};
    }
    const uint8_t* end=strip+l[2];
    while(strip<end){
        unsigned n=*strip++;
        if(piece->near_class==1){
            for(unsigned k=0;k<n;k++)emit(sq,unique_world[strip[k]],k+1==n);
        }else{
            for(unsigned k=2;k<n;k++)clipped(sq,unique_world[strip[k-2+(k&1)]],
              unique_world[strip[k-1-(k&1)]],unique_world[strip[k]],near);
        }
        strip+=n;
    }
}
static NativePiece selected[8192], ordered[8192];
static unsigned offsets[1025], list_offsets[4];
int native_prepare_world(const NativeWorld* w,const float* camera,unsigned materials){
    if(materials>1024)return 0;
    int n=native_world_select(w,camera,2.f,selected,8192);
    if(n<0)return 0;
    unsigned start=0;
    // Stable counting sort by list then material, retaining cell order for ties.
    memset(offsets,0,sizeof(offsets));
    for(int i=0;i<n;i++)offsets[selected[i].header]++;
    unsigned lists[1024]={0};
    for(unsigned i=0;i<((const uint32_t*)w->mesh)[5];i++)lists[w->materials[i].header]=w->materials[i].phase;
    for(unsigned phase=0;phase<3;phase++){
        list_offsets[phase]=start;
        for(unsigned k=0;k<materials;k++)if(lists[k]==phase){unsigned v=offsets[k];offsets[k]=start;start+=v;}
    }
    list_offsets[3]=start;
    for(int i=0;i<n;i++)ordered[offsets[selected[i].header]++]=selected[i];
    return 1;
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
        if(last_place!=p->placement){
            last_place=p->placement;
            shz_mat4x4_t m=projection_grid(camera,w->places[last_place].grid);
            shz_xmtrx_load_4x4(&m);
        }
        native_piece(&sq,w,p,near);
    }
    sq_wait();sq_unlock();
}
