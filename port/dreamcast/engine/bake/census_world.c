/* Room census of a NAT3 pack's world and its baked visibility (lane eng-bake1). Host tool; reads only the pack and
   its VIS2 table, links the renderer's own selection (render/native_world.c) so the counts are what the engine
   would select, and prints one key=value line per figure.
   Build: cc -O2 -I../render census_world.c ../render/native_world.c -lm -o census_world
   Usage: census_world <pack> <vis> <cot> [--yaws N] [--pitch DEG] [--eye MM]
     cot: the camera's cot(fovy/2) (the room bake takes it from a recorded camera); aspect 4:3, near 100 and
     far 18,750 are the engine renderer's constants (services/camera/eng_camera.h).
   Whole room: R4IM totals (every level) and level 0 over every non-sky placement (the full-detail room).
   Per baked camera cell (camera at the cell centre, eye at the band's floor + EYE, which is inside the band):
   - pvs: level-0 triangles and vertices of the cluster instances the table leaves visible (every direction);
   - view: N yaws at PITCH degrees, the engine's selection (frustum, distance levels, the cell's masks): meshlets,
     staged vertices (the vertices the transform runs on), strip corners (vertices submitted), triangles;
   - the same views with no table (what the visibility removes).
   Exit 0 with "census ok", 2 when the pack does not open, 3 when the world does not open, 4 when the table does
   not open against the world (a table baked for another pack). */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>
#include "native_world.h"
typedef struct { uint32_t n; const unsigned* offset; uint8_t* base; } Table;
static void* row(const Table* t,unsigned i){return t->base+t->offset[i];}
static unsigned bytes(const Table* t,unsigned i){return t->offset[i+1]-t->offset[i];}
static int table(Table* t,void* data,unsigned size){
    if(size<8)return 0;unsigned* w=data,n=w[0];
    if(n>(size-8)/4||w[1]!=0)return 0;
    t->n=n;t->offset=w+1;t->base=(uint8_t*)data+8+4*n;return w[n+1]==size-8-4*n;
}
static uint32_t u32(const void* p){uint32_t x;memcpy(&x,p,4);return x;}
static uint16_t u16(const void* p){uint16_t x;memcpy(&x,p,2);return x;}
static uint8_t* load(const char* path,long* size){
    FILE* f=fopen(path,"rb");if(!f)return NULL;fseek(f,0,SEEK_END);*size=ftell(f);fseek(f,0,SEEK_SET);
    uint8_t* d=malloc(*size+32);if(fread(d,1,*size,f)!=(size_t)*size){fclose(f);return NULL;}fclose(f);return d;
}
typedef struct { double meshlets,verts,corners,tris,strips; } Count;
static void count_meshlet(const uint8_t* m,unsigned l,Count* c){
    const uint8_t* info=m+u32(m+48)+28*l;unsigned start=u32(info+4),span=u32(info+8),verts=u16(info+12);
    const uint8_t* s=m+u32(m+56)+start;if(u16(info+14)&32768)s+=2*verts;
    c->meshlets++;c->verts+=verts;
    for(unsigned q=0;q<span;){unsigned len=s[q++];c->corners+=len;c->tris+=len-2;c->strips++;q+=len;}
}
static NativePiece out[16384];
/* the selection's counts for one camera, as bench/host_world.c counts them */
static void count_view(NativeWorld* w,const float* cam,Count* c){
    memset(c,0,sizeof(*c));
    int n=native_world_select(w,cam,2.f,out,16384);
    if(n<0){c->meshlets=-1;return;}
    const uint8_t* m=w->mesh;unsigned G=w->group_count;
    for(int i=0;i<n;i++){
        const uint8_t* info=m+u32(m+48)+28*out[i].meshlet;unsigned span=u32(info+8),verts=u16(info+12);
        const uint8_t* strip=m+u32(m+56)+u32(info+4);if(u16(info+14)&32768)strip+=2*verts;
        unsigned before=0;
        for(unsigned g=0;g<G;g++){
            unsigned after=w->group_bytes?u16(w->groups+32+16*(out[i].meshlet*G+g)+12):span;
            const uint8_t* s=strip+before,*e=strip+after;before=after;
            if(!(out[i].groups>>g&1))continue;
            while(s<e){unsigned k=*s++;c->corners+=k;c->tris+=k-2;c->strips++;s+=k;}
        }
        const uint8_t* rg=w->rt_range+2*G*out[i].meshlet;unsigned staged=0;
        if(w->rt[out[i].meshlet].full)staged=w->rt[out[i].meshlet].count;else for(unsigned g=0;g<G;g++)if(out[i].groups>>g&1)staged+=rg[2*g+1];
        c->verts+=staged;c->meshlets++;
    }
}
static void camera(float* cam,const float* eye,float yaw,float pitch,float cot){
    float f[3]={sinf(yaw)*cosf(pitch),sinf(pitch),cosf(yaw)*cosf(pitch)};   /* forward */
    float look[3]={-f[0],-f[1],-f[2]};
    float r[3]={look[2],0,-look[0]};float rl=sqrtf(r[0]*r[0]+r[2]*r[2]);r[0]/=rl;r[2]/=rl;
    float up[3]={look[1]*r[2]-look[2]*r[1],look[2]*r[0]-look[0]*r[2],look[0]*r[1]-look[1]*r[0]};
    const float* rows[3]={r,up,look};
    memset(cam,0,26*4);
    for(int i=0;i<3;i++){for(int j=0;j<3;j++)cam[4*i+j]=rows[i][j];cam[4*i+3]=-(rows[i][0]*eye[0]+rows[i][1]*eye[1]+rows[i][2]*eye[2]);}
    const float n=100.f,fa=18750.f,k=1.f/(fa-n);
    cam[12]=0;cam[13]=cot/1.33333333f;cam[14]=0;cam[15]=cot;cam[16]=0;cam[17]=-n*k;cam[18]=-(fa*n)*k;
    cam[19]=0;cam[20]=0;cam[21]=640;cam[22]=480;cam[23]=0;cam[24]=1;cam[25]=fa;
}
int cmpf(const void* a,const void* b){float x=*(const float*)a,y=*(const float*)b;return (x>y)-(x<y);}
int main(int argc,char** argv){
    if(argc<4){fprintf(stderr,"usage: census_world pack vis cot [--yaws N] [--pitch DEG] [--eye MM]\n");return 1;}
    float cot=atof(argv[3]),pitch_deg=-10.f,eye_up=2000.f;int yaws=16;
    for(int i=4;i<argc;i++){
        if(!strcmp(argv[i],"--yaws")&&i+1<argc)yaws=atoi(argv[++i]);
        else if(!strcmp(argv[i],"--pitch")&&i+1<argc)pitch_deg=atof(argv[++i]);
        else if(!strcmp(argv[i],"--eye")&&i+1<argc)eye_up=atof(argv[++i]);
    }
    long size,vsize;uint8_t* data=load(argv[1],&size);if(!data)return 2;
    Table root;if(size<20||memcmp(data,"NAT3",4)||!table(&root,data+20,size-20)||root.n!=15)return 2;
    NativeWorld w;if(!native_world_open(&w,row(&root,2),bytes(&root,2)))return 3;
    const uint8_t* m=w.mesh;
    unsigned nmesh=u32(m+16),nparts=u32(m+20),nlets=u32(m+24),nverts=u32(m+28),nclusters=u32(m+80),nlevels=u32(m+84);
    const uint8_t *meshes=m+u32(m+40),*plod=m+u32(m+88),*clusters=m+u32(m+92),*levels=m+u32(m+96);
    Count all={0};for(unsigned l=0;l<nlets;l++)count_meshlet(m,l,&all);
    printf("r4im meshes=%u parts=%u meshlets=%u vertices=%u clusters=%u levels=%u strips=%.0f triangles=%.0f corners=%.0f\n",
           nmesh,nparts,nlets,nverts,nclusters,nlevels,all.strips,all.tris,all.corners);
    /* level 0 per cluster instance (placement x cluster), in bake_vis's instance order */
    unsigned nplace=w.place_count,ninst=0,sky=0;
    unsigned* mesh_first=calloc(nmesh+1,4);unsigned* mesh_count=calloc(nmesh+1,4);
    for(unsigned me=0;me<nmesh;me++){const uint8_t* mh=meshes+68*me;unsigned first=u32(mh+12),end=first+u32(mh+16),lo=~0u,hi=0;
        for(unsigned p=first;p<end;p++){unsigned a=u32(plod+8*p),b=a+u32(plod+8*p+4);if(b>a){if(a<lo)lo=a;if(b>hi)hi=b;}}
        if(lo==~0u)lo=hi=0;mesh_first[me]=lo;mesh_count[me]=hi-lo;}
    for(unsigned j=0;j<nplace;j++){if(w.places[j].sky){sky++;continue;}ninst+=mesh_count[w.places[j].mesh];}
    float* itri=calloc(ninst+1,4);float* ivert=calloc(ninst+1,4);Count l0={0};
    {unsigned q=0;for(unsigned j=0;j<nplace;j++){if(w.places[j].sky)continue;
        for(unsigned k=mesh_first[w.places[j].mesh];k<mesh_first[w.places[j].mesh]+mesh_count[w.places[j].mesh];k++,q++){
            const uint8_t* cl=clusters+20*k;unsigned lev=u32(cl+12);Count c={0};
            for(unsigned l=u32(levels+12*lev);l<u32(levels+12*lev)+u32(levels+12*lev+4);l++)count_meshlet(m,l,&c);
            itri[q]=c.tris;ivert[q]=c.verts;l0.meshlets+=c.meshlets;l0.verts+=c.verts;l0.tris+=c.tris;l0.strips+=c.strips;l0.corners+=c.corners;}}}
    printf("level0 placements=%u sky_placements=%u instances=%u meshlets=%.0f vertices=%.0f triangles=%.0f strips=%.0f corners=%.0f cells=%u groups=%u\n",
           nplace-sky,sky,ninst,l0.meshlets,l0.verts,l0.tris,l0.strips,l0.corners,w.cell_count,w.group_bytes?u32(w.groups+12):0);
    if(!native_world_runtime(&w))return 3;
    unsigned G=w.group_count;
    printf("runtime staged_vertices=%u duplicates=%u whole_meshlets=%u bytes=%u\n",w.rt_vertices,w.rt_duplicates,w.rt_full,
           (unsigned)(nlets*sizeof(NativeMeshletRt)+(2*nlets*G+2)+(2*w.rt_vertices+2)+(4*w.rt_vertices+8)));
    uint8_t* vdata=load(argv[2],&vsize);if(!vdata)return 4;
    NativeVis vis;if(!native_vis_open(&vis,vdata,vsize,&w))return 4;w.vis=&vis;
    printf("vis bytes=%ld cells_in_rows=%u instance_masks=%u column_masks=%u decode_bytes=%u\n",vsize,vis.ncells,vis.ni,vis.nc,vis.ibytes+vis.cbytes);
    float cam[26];Count best={0},bestn={0},sum={0},sumn={0};double pvs_max_t=0,pvs_max_v=0,pvs_t=0,pvs_v=0;unsigned cells=0,views=0,outside=0;
    int bx=-1,bz=-1;double best_yaw=0;float* vv=malloc(sizeof(float)*(size_t)(vis.ncells+1)*yaws);unsigned nvv=0;
    for(unsigned z=0;z<vis.nz;z++){unsigned x0=vis.rows[2*z]&0xffff,n=vis.rows[2*z]>>16,first=vis.rows[2*z+1];
        for(unsigned x=x0;x<x0+n;x++){const NativeVisCell* c=vis.cells+first+(x-x0);if(c->imask==0xffff)continue;
            float ylo=c->ylo*vis.yunit,yhi=c->yhi*vis.yunit;
            float eye[3]={vis.org[0]+(x+.5f)*vis.cell,fminf(ylo-700.f+eye_up,yhi),vis.org[1]+(z+.5f)*vis.cell};
            camera(cam,eye,0,0,cot);
            if(native_vis_select(&w,cam)!=VIS_MASK){outside++;continue;}
            double pt=0,pv=0;for(unsigned q=0;q<ninst;q++)if(!(w.vis_inst[q>>3]>>(q&7)&1)){pt+=itri[q];pv+=ivert[q];}
            pvs_t+=pt;pvs_v+=pv;if(pt>pvs_max_t)pvs_max_t=pt;if(pv>pvs_max_v)pvs_max_v=pv;cells++;
            for(int y=0;y<yaws;y++){float yaw=6.2831853f*y/yaws;Count a,b;
                camera(cam,eye,yaw,pitch_deg*3.1415927f/180.f,cot);
                native_vis_select(&w,cam);count_view(&w,cam,&a);
                w.vis_inst=NULL;w.vis_cubes=NULL;count_view(&w,cam,&b);
                if(a.meshlets<0||b.meshlets<0){fprintf(stderr,"selection over capacity\n");return 5;}
                views++;vv[nvv++]=a.verts;sum.meshlets+=a.meshlets;sum.verts+=a.verts;sum.corners+=a.corners;sum.tris+=a.tris;sum.strips+=a.strips;
                sumn.verts+=b.verts;sumn.tris+=b.tris;sumn.corners+=b.corners;sumn.meshlets+=b.meshlets;
                if(a.verts>best.verts){best=a;bx=x;bz=z;best_yaw=360.*y/yaws;}
                if(b.verts>bestn.verts)bestn=b;
            }
        }}
    {   /* the pack's own pictures (a game pack: the recorded route; a world pack: its entry points), with the table;
           the recorded view and field of view, the engine renderer's near and far planes */
        Table frames,d0;table(&frames,row(&root,3),bytes(&root,3));table(&d0,row(&root,4),bytes(&root,4));
        static uint32_t st[32768];Count rb={0},rs={0};unsigned rn=0,rm=0;
        for(unsigned fr=0;fr<frames.n;fr++){
            const uint32_t* refs=row(&frames,fr);const uint32_t* p=row(&d0,refs[1]);const uint32_t* end=p+bytes(&d0,refs[1])/4;p++;
            while(p<end){uint32_t* dest=st+*p++;unsigned bits=*p++;for(;bits;bits>>=1,dest++)if(bits&1)*dest=*p++;}
            float rc[26];const float* sf=(const float*)st;float eye[3]={0,0,0};
            camera(rc,eye,0,0,sf[15]>0?sf[15]:cot);memcpy(rc,sf,48);
            Count a;rm+=native_vis_select(&w,rc)==VIS_MASK;count_view(&w,rc,&a);
            if(a.meshlets<0)return 5;rn++;rs.verts+=a.verts;rs.tris+=a.tris;rs.corners+=a.corners;
            if(a.verts>rb.verts)rb=a;
        }
        if(rn)printf("route pictures=%u with_mask=%u max_staged_vertices=%.0f max_triangles=%.0f mean_staged_vertices=%.0f mean_triangles=%.0f mean_corners=%.0f\n",
                     rn,rm,rb.verts,rb.tris,rs.verts/rn,rs.tris/rn,rs.corners/rn);
    }
    if(!cells){printf("cells baked=0\n");printf("census ok\n");return 0;}
    printf("pvs cells=%u unbaked_at_centre=%u max_triangles=%.0f max_vertices=%.0f mean_triangles=%.0f mean_vertices=%.0f\n",cells,outside,pvs_max_t,pvs_max_v,pvs_t/cells,pvs_v/cells);
    printf("view yaws=%d pitch=%.0f eye=%.0f views=%u max_staged_vertices=%.0f max_corners=%.0f max_triangles=%.0f max_meshlets=%.0f max_strips=%.0f max_cell=%d,%d max_yaw=%.1f mean_staged_vertices=%.0f mean_corners=%.0f mean_triangles=%.0f mean_meshlets=%.1f mean_strips=%.0f\n",
           yaws,pitch_deg,eye_up,views,best.verts,best.corners,best.tris,best.meshlets,best.strips,bx,bz,best_yaw,sum.verts/views,sum.corners/views,sum.tris/views,sum.meshlets/views,sum.strips/views);
    qsort(vv,nvv,sizeof(float),cmpf);
    printf("viewpct p50_staged_vertices=%.0f p90_staged_vertices=%.0f p99_staged_vertices=%.0f\n",vv[nvv/2],vv[nvv*9/10],vv[nvv*99/100]);
    printf("novis max_staged_vertices=%.0f max_triangles=%.0f mean_staged_vertices=%.0f mean_triangles=%.0f\n",bestn.verts,bestn.tris,sumn.verts/views,sumn.tris/views);
    printf("census ok\n");
    return 0;
}
