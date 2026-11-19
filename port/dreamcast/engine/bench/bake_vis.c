/* Offline baked visibility, format VIS2 (eng-e0b). Host tool.
   Build: cc -O2 -I../render bake_vis.c ../render/native_world.c -lm -o bake_vis
   Usage: bake_vis <pack> <out.vis> [--cell MM] [--budget BYTES] [--jobs N] [--survey]
          bake_vis <pack> <out.vis> --control <in.vis> [N]   (control table: see below)

   Whole room, not the recorded route. The camera domain is derived from the room's own geometry:
   - floor: at each point, the lowest near-horizontal opaque surface with at least CLEAR of headroom;
   - reachable: cells connected on foot to the recorded route's cells (the seed only; the route's cameras are
     never eyes): neighbouring cell centres join when their floors differ by at most STEP and no opaque
     triangle crosses the straight walk between them at knee or chest height (walls, fences, cliffs);
   - a camera cell (CELL mm square in x/z) is baked when it is reachable, or a neighbour is (one cell of
     dilation: the camera can stand back from the walkable edge);
   - the cell's camera band is [lowest floor + BAND_LO, highest floor + BAND_HI]; the runtime uses the cell's
     masks only when the camera height is inside that band. Any other camera position (outside the grid, an
     unbaked cell, a height outside the band) draws everything (the safe fallback).
   For each baked cell, sample eyes on a 3 x 3 grid that includes the cell's edges, at the band's bottom,
   middle and top (27 eyes), render six 90-degree depth faces of the opaque world from each, and mark a query
   hidden only when no eye sees any of it: world cluster instances (placement x cluster, by their world box) and
   2 m actor cubes. Actor cubes exist only where actors can stand: columns with a floor (reachable on foot or
   not: the barn interior holds props the camera never reaches), from CUBE_BELOW under
   the lowest floor to CUBE_ABOVE over the highest surface (roof tops: birds). The table stores one bit per
   column: hidden when every cube of the column is hidden (an actor is skipped when every column its box touches
   is hidden and its box stays inside those columns' cube range; anything else keeps it visible). Queries are dilated by MARGIN and pass on depth ties, so the table errs toward visible.
   Table size: identical masks are stored once (a dictionary per kind) and cells index them; each mask is stored
   raw or run-length coded, whichever is smaller. When the room
   would exceed the budget, the two dictionary entries (used by neighbouring cells) whose intersection loses
   the fewest hidden bits are merged into that intersection until it fits. An intersection only shows more,
   so merging is always safe; it costs selectivity, which the log reports.
   --control writes the control table: the given table with, in each cell the recorded route visits, the N
   instances the route's cameras see most (forward face) marked hidden. A pixel check must catch it. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>
#include <unistd.h>
#include <sys/mman.h>
#include <sys/wait.h>
#include "native_world.h"
#define ACUBE 2000.f
#define MARGIN 60.f
#define RES 192
#define NEARZ 20.f
#define CLEAR 1700.f       /* headroom above a walkable floor */
#define BAND_LO 700.f      /* camera band above the floor (route survey: see the log) */
#define BAND_HI 2800.f
#define CUBE_BELOW 600.f
#define CUBE_ABOVE 2600.f
#define YUNIT 10.f         /* band heights stored in 10 mm units */
#define STEP 600.f         /* largest floor change between neighbouring cell centres on foot */
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
typedef struct { float v[3][3]; } Tri;
static Tri* tris;static unsigned ntri,captri;
static void add_tri(const float* a,const float* b,const float* c){
    if(ntri==captri){captri=captri?2*captri:65536;tris=realloc(tris,captri*sizeof(Tri));}
    memcpy(tris[ntri].v[0],a,12);memcpy(tris[ntri].v[1],b,12);memcpy(tris[ntri].v[2],c,12);ntri++;
}
static void grid_point(const float* g,float x,float y,float z,float* o){
    for(int r=0;r<3;r++)o[r]=g[4*r]*x+g[4*r+1]*y+g[4*r+2]*z+g[4*r+3];
}
typedef struct { float lo[3],hi[3]; } Box;
/* ---- rasteriser: one 90-degree face, depth = distance along the face axis ---- */
static float depth[RES*RES];
static float basis[3][3];   /* face right, up, forward */
static float eye[3];
static void to_face(const float* p,float* o){
    float d[3]={p[0]-eye[0],p[1]-eye[1],p[2]-eye[2]};
    for(int i=0;i<3;i++)o[i]=basis[i][0]*d[0]+basis[i][1]*d[1]+basis[i][2]*d[2];
}
static int raster(const float* a,const float* b,const float* c,int mode){
    float p[3][3];const float* v[3]={a,b,c};
    for(int i=0;i<3;i++){float iz=1.f/v[i][2];p[i][0]=(v[i][0]*iz*.5f+.5f)*RES;p[i][1]=(v[i][1]*iz*.5f+.5f)*RES;p[i][2]=v[i][2];}
    float minx=fminf(p[0][0],fminf(p[1][0],p[2][0])),maxx=fmaxf(p[0][0],fmaxf(p[1][0],p[2][0]));
    float miny=fminf(p[0][1],fminf(p[1][1],p[2][1])),maxy=fmaxf(p[0][1],fmaxf(p[1][1],p[2][1]));
    int x0=(int)floorf(minx),x1=(int)ceilf(maxx),y0=(int)floorf(miny),y1=(int)ceilf(maxy);
    if(x0<0)x0=0;if(y0<0)y0=0;if(x1>RES)x1=RES;if(y1>RES)y1=RES;
    if(x0>=x1||y0>=y1)return 0;
    float area=(p[1][0]-p[0][0])*(p[2][1]-p[0][1])-(p[2][0]-p[0][0])*(p[1][1]-p[0][1]);
    if(fabsf(area)<1e-9f){
        if(mode==1){for(int y=y0;y<y1;y++)for(int x=x0;x<x1;x++){float z=fminf(p[0][2],fminf(p[1][2],p[2][2]));if(z<=depth[y*RES+x]*1.002f+1)return 1;}}
        return 0;
    }
    float ia=1.f/area;
    float zmin=fminf(p[0][2],fminf(p[1][2],p[2][2]));
    for(int y=y0;y<y1;y++)for(int x=x0;x<x1;x++){
        if(mode==0){
            float px=x+.5f,py=y+.5f;
            float w0=((p[1][0]-px)*(p[2][1]-py)-(p[2][0]-px)*(p[1][1]-py))*ia;
            float w1=((p[2][0]-px)*(p[0][1]-py)-(p[0][0]-px)*(p[2][1]-py))*ia;
            float w2=1-w0-w1;
            if(w0<0||w1<0||w2<0)continue;
            float iz=w0/p[0][2]+w1/p[1][2]+w2/p[2][2];float z=1.f/iz;
            if(z<depth[y*RES+x])depth[y*RES+x]=z;
        }else{
            float px0=x,px1=x+1,py0=y,py1=y+1;int in=0;
            for(int k=0;k<4 && !in;k++){
                float px=(k&1)?px1:px0,py=(k&2)?py1:py0;
                float w0=((p[1][0]-px)*(p[2][1]-py)-(p[2][0]-px)*(p[1][1]-py))*ia;
                float w1=((p[2][0]-px)*(p[0][1]-py)-(p[0][0]-px)*(p[2][1]-py))*ia;
                float w2=1-w0-w1;in=w0>=-.001f&&w1>=-.001f&&w2>=-.001f;
            }
            if(!in){float cx=x+.5f,cy=y+.5f;
                for(int k=0;k<3&&!in;k++)in=fabsf(p[k][0]-cx)<=.5f&&fabsf(p[k][1]-cy)<=.5f;}
            if(in && zmin<=depth[y*RES+x]*1.002f+1)return 1;
        }
    }
    return 0;
}
static int clip_raster(const float* a,const float* b,const float* c,int mode){
    float in[12][3],out[12][3];int n=3;
    memcpy(in[0],a,12);memcpy(in[1],b,12);memcpy(in[2],c,12);
    for(int pl=0;pl<5;pl++){
        int m=0;
        for(int i=0;i<n;i++){
            const float* p=in[i];const float* q=in[(i+1)%n];
            float dp,dq;
            switch(pl){case 0:dp=p[2]-NEARZ;dq=q[2]-NEARZ;break;
                case 1:dp=1.02f*p[2]-p[0];dq=1.02f*q[2]-q[0];break;case 2:dp=1.02f*p[2]+p[0];dq=1.02f*q[2]+q[0];break;
                case 3:dp=1.02f*p[2]-p[1];dq=1.02f*q[2]-q[1];break;default:dp=1.02f*p[2]+p[1];dq=1.02f*q[2]+q[1];}
            if(dp>=0){memcpy(out[m++],p,12);}
            if((dp>=0)!=(dq>=0)){float t=dp/(dp-dq);for(int k=0;k<3;k++)out[m][k]=p[k]+(q[k]-p[k])*t;m++;}
            if(m>=11)break;
        }
        n=m;if(n<3)return 0;memcpy(in,out,sizeof(out));
    }
    for(int i=2;i<n;i++)if(raster(in[0],in[i-1],in[i],mode)&&mode==1)return 1;
    return 0;
}
static void set_face(int f){
    static const float F[6][3][3]={{{0,0,-1},{0,1,0},{1,0,0}},{{0,0,1},{0,1,0},{-1,0,0}},{{1,0,0},{0,0,-1},{0,1,0}},
                                   {{1,0,0},{0,0,1},{0,-1,0}},{{1,0,0},{0,1,0},{0,0,1}},{{-1,0,0},{0,1,0},{0,0,-1}}};
    memcpy(basis,F[f],sizeof(basis));
}
static void render_face(void){
    for(int i=0;i<RES*RES;i++)depth[i]=1e30f;
    for(unsigned t=0;t<ntri;t++){float a[3],b[3],c[3];to_face(tris[t].v[0],a);to_face(tris[t].v[1],b);to_face(tris[t].v[2],c);
        if(a[2]<NEARZ&&b[2]<NEARZ&&c[2]<NEARZ)continue;
        if(a[0]>1.02f*a[2]&&b[0]>1.02f*b[2]&&c[0]>1.02f*c[2])continue;if(-a[0]>1.02f*a[2]&&-b[0]>1.02f*b[2]&&-c[0]>1.02f*c[2])continue;
        if(a[1]>1.02f*a[2]&&b[1]>1.02f*b[2]&&c[1]>1.02f*c[2])continue;if(-a[1]>1.02f*a[2]&&-b[1]>1.02f*b[2]&&-c[1]>1.02f*c[2])continue;
        clip_raster(a,b,c,0);}
}
static int box_visible(const Box* b){
    float lo[3],hi[3];for(int i=0;i<3;i++){lo[i]=b->lo[i]-MARGIN;hi[i]=b->hi[i]+MARGIN;}
    if(eye[0]>=lo[0]&&eye[0]<=hi[0]&&eye[1]>=lo[1]&&eye[1]<=hi[1]&&eye[2]>=lo[2]&&eye[2]<=hi[2])return 1;
    float c[8][3];for(int k=0;k<8;k++){float p[3]={k&1?hi[0]:lo[0],k&2?hi[1]:lo[1],k&4?hi[2]:lo[2]};to_face(p,c[k]);}
    int allbehind=1;for(int k=0;k<8;k++)if(c[k][2]>NEARZ)allbehind=0;
    if(allbehind)return 0;
    static const int Q[6][4]={{0,1,3,2},{4,5,7,6},{0,1,5,4},{2,3,7,6},{0,2,6,4},{1,3,7,5}};
    for(int f=0;f<6;f++){
        if(clip_raster(c[Q[f][0]],c[Q[f][1]],c[Q[f][2]],1))return 1;
        if(clip_raster(c[Q[f][0]],c[Q[f][2]],c[Q[f][3]],1))return 1;
    }
    return 0;
}
/* ---- floors: near-horizontal opaque triangles bucketed over the camera grid ---- */
static float org[2],CELL=1000.f;static int nx,nz;
static unsigned **bucket;static unsigned *bucket_n,*bucket_cap;
static unsigned **wbucket;static unsigned *wbucket_n,*wbucket_cap;
static void floor_index(void){
    bucket=calloc(nx*nz,sizeof(*bucket));bucket_n=calloc(nx*nz,4);bucket_cap=calloc(nx*nz,4);
    wbucket=calloc(nx*nz,sizeof(*wbucket));wbucket_n=calloc(nx*nz,4);wbucket_cap=calloc(nx*nz,4);
    for(unsigned t=0;t<ntri;t++){
        const float (*v)[3]=tris[t].v;
        float lx=fminf(v[0][0],fminf(v[1][0],v[2][0])),hx=fmaxf(v[0][0],fmaxf(v[1][0],v[2][0]));
        float lz=fminf(v[0][2],fminf(v[1][2],v[2][2])),hz=fmaxf(v[0][2],fmaxf(v[1][2],v[2][2]));
        int x0=(int)floorf((lx-org[0])/CELL),x1=(int)floorf((hx-org[0])/CELL),z0=(int)floorf((lz-org[1])/CELL),z1=(int)floorf((hz-org[1])/CELL);
        if(x0<0)x0=0;
        if(z0<0)z0=0;
        if(x1>=nx)x1=nx-1;
        if(z1>=nz)z1=nz-1;
        for(int z=z0;z<=z1;z++)for(int x=x0;x<=x1;x++){unsigned b=z*nx+x;
            if(wbucket_n[b]==wbucket_cap[b]){wbucket_cap[b]=wbucket_cap[b]?2*wbucket_cap[b]:16;wbucket[b]=realloc(wbucket[b],4*wbucket_cap[b]);}
            wbucket[b][wbucket_n[b]++]=t;}
    }
    for(unsigned t=0;t<ntri;t++){
        const float (*v)[3]=tris[t].v;
        float e1[3]={v[1][0]-v[0][0],v[1][1]-v[0][1],v[1][2]-v[0][2]},e2[3]={v[2][0]-v[0][0],v[2][1]-v[0][1],v[2][2]-v[0][2]};
        float n[3]={e1[1]*e2[2]-e1[2]*e2[1],e1[2]*e2[0]-e1[0]*e2[2],e1[0]*e2[1]-e1[1]*e2[0]};
        float len=sqrtf(n[0]*n[0]+n[1]*n[1]+n[2]*n[2]);
        if(!(len>0) || fabsf(n[1])<.5f*len)continue;      /* steeper than 60 degrees: not a floor or ceiling */
        float lx=fminf(v[0][0],fminf(v[1][0],v[2][0])),hx=fmaxf(v[0][0],fmaxf(v[1][0],v[2][0]));
        float lz=fminf(v[0][2],fminf(v[1][2],v[2][2])),hz=fmaxf(v[0][2],fmaxf(v[1][2],v[2][2]));
        int x0=(int)floorf((lx-org[0])/CELL),x1=(int)floorf((hx-org[0])/CELL),z0=(int)floorf((lz-org[1])/CELL),z1=(int)floorf((hz-org[1])/CELL);
        if(x0<0)x0=0;if(z0<0)z0=0;if(x1>=nx)x1=nx-1;if(z1>=nz)z1=nz-1;
        for(int z=z0;z<=z1;z++)for(int x=x0;x<=x1;x++){unsigned b=z*nx+x;
            if(bucket_n[b]==bucket_cap[b]){bucket_cap[b]=bucket_cap[b]?2*bucket_cap[b]:16;bucket[b]=realloc(bucket[b],4*bucket_cap[b]);}
            bucket[b][bucket_n[b]++]=t;}
    }
}
static int fcmp(const void* a,const void* b){float x=*(const float*)a,y=*(const float*)b;return (x>y)-(x<y);}
/* Lowest surface at (x,z) with CLEAR headroom; 0 when none. *top: the highest surface (roofs: actors such as
   birds stand there; the actor cube domain covers up to it). */
static float floor_top;
static int floor_at(float x,float z,float* out){
    int cx=(int)floorf((x-org[0])/CELL),cz=(int)floorf((z-org[1])/CELL);
    if(cx<0||cz<0||cx>=nx||cz>=nz)return 0;
    unsigned b=cz*nx+cx;float h[512];unsigned n=0;
    for(unsigned i=0;i<bucket_n[b] && n<512;i++){
        const float (*v)[3]=tris[bucket[b][i]].v;
        float d=(v[1][0]-v[0][0])*(v[2][2]-v[0][2])-(v[2][0]-v[0][0])*(v[1][2]-v[0][2]);
        if(fabsf(d)<1e-6f)continue;
        float w1=((x-v[0][0])*(v[2][2]-v[0][2])-(v[2][0]-v[0][0])*(z-v[0][2]))/d;
        float w2=((v[1][0]-v[0][0])*(z-v[0][2])-(x-v[0][0])*(v[1][2]-v[0][2]))/d;
        if(w1<0||w2<0||w1+w2>1)continue;
        h[n++]=v[0][1]+w1*(v[1][1]-v[0][1])+w2*(v[2][1]-v[0][1]);
    }
    if(!n)return 0;
    qsort(h,n,4,fcmp);floor_top=h[n-1];
    for(unsigned i=0;i<n;i++){
        unsigned j=i+1;while(j<n && h[j]-h[i]<50.f)j++;     /* coincident layers count once */
        if(j==n || h[j]-h[i]>=CLEAR){*out=h[i];return 1;}
        i=j-1;
    }
    return 0;
}
/* Segment p..q against a triangle (Moller-Trumbore). */
static int seg_tri(const float* p,const float* q,const float (*v)[3]){
    float d[3]={q[0]-p[0],q[1]-p[1],q[2]-p[2]},e1[3],e2[3],h[3],s[3],qq[3];
    for(int i=0;i<3;i++){e1[i]=v[1][i]-v[0][i];e2[i]=v[2][i]-v[0][i];}
    h[0]=d[1]*e2[2]-d[2]*e2[1];h[1]=d[2]*e2[0]-d[0]*e2[2];h[2]=d[0]*e2[1]-d[1]*e2[0];
    float a=e1[0]*h[0]+e1[1]*h[1]+e1[2]*h[2];if(fabsf(a)<1e-9f)return 0;
    float fi=1.f/a;for(int i=0;i<3;i++)s[i]=p[i]-v[0][i];
    float u=fi*(s[0]*h[0]+s[1]*h[1]+s[2]*h[2]);if(u<0||u>1)return 0;
    qq[0]=s[1]*e1[2]-s[2]*e1[1];qq[1]=s[2]*e1[0]-s[0]*e1[2];qq[2]=s[0]*e1[1]-s[1]*e1[0];
    float vv=fi*(d[0]*qq[0]+d[1]*qq[1]+d[2]*qq[2]);if(vv<0||u+vv>1)return 0;
    float t=fi*(e2[0]*qq[0]+e2[1]*qq[1]+e2[2]*qq[2]);return t>=0&&t<=1;
}
/* Walk between two neighbouring cell centres (floor heights fa, fb) is blocked by an opaque triangle. */
static int blocked(int ax,int az,float fa,int bx,int bz,float fb){
    for(int k=0;k<2;k++){
        float hgt=k?1400.f:700.f;
        float p[3]={org[0]+(ax+.5f)*CELL,fa+hgt,org[1]+(az+.5f)*CELL},q[3]={org[0]+(bx+.5f)*CELL,fb+hgt,org[1]+(bz+.5f)*CELL};
        for(int c=0;c<2;c++){unsigned b=c?bz*nx+bx:az*nx+ax;
            for(unsigned i=0;i<wbucket_n[b];i++)if(seg_tri(p,q,tris[wbucket[b][i]].v))return 1;}
    }
    return 0;
}
typedef struct { float fmin,fmax,centre,top; int core,reach,baked,has_centre; float ylo,yhi; } CamCell;
/* ---- dictionaries and merging ---- */
static unsigned popc(const uint8_t* a,unsigned n){unsigned c=0;for(unsigned i=0;i<n;i++)c+=__builtin_popcount(a[i]);return c;}
static unsigned and_popc(const uint8_t* a,const uint8_t* b,unsigned n){unsigned c=0;for(unsigned i=0;i<n;i++)c+=__builtin_popcount(a[i]&b[i]);return c;}
/* Run-length size of a bitset: alternating runs (first run of zeros, may be empty), lengths as u8 with 255 meaning
   "255 and continue": the stored form of every mask. */
static unsigned rle_encode(const uint8_t* a,unsigned nbits,uint8_t* out){
    unsigned n=0,i=0,bit=0;
    while(i<nbits){
        unsigned run=0;while(i<nbits && ((a[i>>3]>>(i&7))&1)==bit){run++;i++;}
        while(run>=255){if(out)out[n]=255;n++;run-=255;}
        if(out)out[n]=run;n++;bit^=1;
    }
    return n;
}
/* Unique masks: index[k] for each of n rows. Returns entry count; entries packed in out. */
static unsigned dict_build(const uint8_t* rows,unsigned n,unsigned nb,uint8_t** out,unsigned* index){
    uint8_t* e=malloc((size_t)n*nb+1);unsigned ne=0;
    unsigned hsize=1;while(hsize<4*n+4)hsize<<=1;int* h=malloc(4*hsize);memset(h,0xff,4*hsize);
    for(unsigned k=0;k<n;k++){
        const uint8_t* r=rows+(size_t)k*nb;uint32_t x=2166136261u;for(unsigned i=0;i<nb;i++)x=(x^r[i])*16777619u;
        unsigned s=x&(hsize-1);
        while(h[s]>=0 && memcmp(e+(size_t)h[s]*nb,r,nb))s=(s+1)&(hsize-1);
        if(h[s]<0){h[s]=ne;memcpy(e+(size_t)ne*nb,r,nb);ne++;}
        index[k]=h[s];
    }
    free(h);*out=e;return ne;
}
static void rle_decode(const uint8_t* p,unsigned nbits,uint8_t* out){
    memset(out,0,(nbits+7)/8);unsigned at=0,bit=0;
    while(at<nbits){unsigned run=0;for(;;){unsigned r=*p++;run+=r;if(r!=255)break;}
        if(bit)for(unsigned i=at;i<at+run;i++)out[i>>3]|=1u<<(i&7);
        at+=run;bit^=1;}
}
/* Stored mask: one mode byte (0 raw, 1 run-length) and the smaller of the two forms. */
static unsigned mask_encode(const uint8_t* a,unsigned nbits,uint8_t* out){
    unsigned raw=(nbits+7)/8,rle=rle_encode(a,nbits,NULL);
    if(rle<raw){if(out){out[0]=1;rle_encode(a,nbits,out+1);}return 1+rle;}
    if(out){out[0]=0;memcpy(out+1,a,raw);}return 1+raw;
}
static size_t rle_total(const uint8_t* e,unsigned n,unsigned nb,unsigned nbits){
    size_t t=0;for(unsigned k=0;k<n;k++)t+=mask_encode(e+(size_t)k*nb,nbits,NULL);return t;
}
/* Merge dictionary entries until at most 'limit' remain. Candidates are the entry pairs used by neighbouring
   cells (x/z); the cheapest pair (hidden bits lost, weighted by the cells using each entry) is merged into its
   intersection first. Lazy heap: a popped pair whose entries changed since it was costed is re-costed. */
typedef struct { double cost; int a,b; unsigned va,vb; } Pair;
static Pair* heap;static unsigned nheap,capheap;
static void hpush(Pair x){if(nheap==capheap){capheap=capheap?2*capheap:4096;heap=realloc(heap,capheap*sizeof(Pair));}
    unsigned i=nheap++;while(i){unsigned p=(i-1)/2;if(heap[p].cost<=x.cost)break;heap[i]=heap[p];i=p;}heap[i]=x;}
static Pair hpop(void){Pair top=heap[0],x=heap[--nheap];unsigned i=0;
    for(;;){unsigned l=2*i+1,r=l+1,m=i;double mc=x.cost;
        if(l<nheap&&heap[l].cost<mc){m=l;mc=heap[l].cost;}if(r<nheap&&heap[r].cost<mc){m=r;}
        if(m==i)break;heap[i]=heap[m];i=m;}
    if(nheap)heap[i]=x;return top;}
static unsigned dict_merge(uint8_t* e,unsigned ne,unsigned nb,unsigned* cell_index,unsigned ncell,const int* nbr4,unsigned limit,double* lost){
    unsigned* weight=calloc(ne,4);int* alias=malloc(4*ne);unsigned* pc=malloc(4*ne);unsigned* ver=calloc(ne,4);
    for(unsigned k=0;k<ncell;k++)weight[cell_index[k]]++;
    for(unsigned i=0;i<ne;i++){alias[i]=i;pc[i]=popc(e+(size_t)i*nb,nb);}
#define FIND(x) ({int _x=(x);while(alias[_x]!=_x)_x=alias[_x];_x;})
#define COST(a,b) ({unsigned _in=and_popc(e+(size_t)(a)*nb,e+(size_t)(b)*nb,nb);(double)(pc[a]-_in)*weight[a]+(double)(pc[b]-_in)*weight[b];})
    nheap=0;
    for(unsigned k=0;k<ncell;k++)for(int d=0;d<4;d++){int o=nbr4[4*k+d];if(o<0||(unsigned)o<k)continue;
        int a=cell_index[k],b=cell_index[o];if(a==b)continue;hpush((Pair){COST(a,b),a,b,0,0});}
    unsigned live=ne;*lost=0;
    while(live>limit && nheap){
        Pair x=hpop();int a=FIND(x.a),b=FIND(x.b);if(a==b)continue;
        if(a!=x.a||b!=x.b||ver[a]!=x.va||ver[b]!=x.vb){hpush((Pair){COST(a,b),a,b,ver[a],ver[b]});continue;}
        uint8_t* A=e+(size_t)a*nb;const uint8_t* B=e+(size_t)b*nb;
        for(unsigned i=0;i<nb;i++)A[i]&=B[i];
        pc[a]=popc(A,nb);weight[a]+=weight[b];alias[b]=a;ver[a]++;live--;*lost+=x.cost;
    }
    while(live>limit){   /* no neighbouring pairs left: fold the remaining entries pairwise (rare) */
        int a=-1,b=-1;for(unsigned i=0;i<ne;i++)if(alias[i]==(int)i){if(a<0)a=i;else{b=i;break;}}
        if(b<0)break;uint8_t* A=e+(size_t)a*nb;for(unsigned i=0;i<nb;i++)A[i]&=e[(size_t)b*nb+i];
        pc[a]=popc(A,nb);weight[a]+=weight[b];alias[b]=a;live--;
    }
    int* remap=malloc(4*ne);unsigned n2=0;
    for(unsigned i=0;i<ne;i++)if(alias[i]==(int)i){if(n2!=i)memmove(e+(size_t)n2*nb,e+(size_t)i*nb,nb);remap[i]=n2++;}
    for(unsigned k=0;k<ncell;k++)cell_index[k]=remap[FIND(cell_index[k])];
#undef FIND
#undef COST
    free(weight);free(alias);free(pc);free(remap);free(ver);
    return n2;
}
/* The VIS2 file. Layout (little endian): u32 header[32] (floats from word 16), place_base[nplace+1],
   mesh_first[nplace], rows[nz] {u16 x0,u16 n,u32 first cell}, cells[ncells] {u16 imask,u16 cmask,i16 ylo,i16 yhi},
   columns[ax*az] {u16 base,u8 y0,u8 ny}, u32 ioff[ni+1], u32 coff[nc+1], run-length mask bytes. */
typedef struct {
    uint32_t head[32];const uint32_t *place_base,*mesh_first;unsigned nplace,nz,ncells,ncol;
    const uint32_t* rows;const uint16_t* cells;const uint8_t* cols;
    unsigned ninst,ni,ibytes,nbits,nc,cbytes;const uint8_t *ei,*ec;
} VisOut;
static size_t vis_write(const char* path,VisOut* v){
    size_t ri=rle_total(v->ei,v->ni,v->ibytes,v->ninst),rc=rle_total(v->ec,v->nc,v->cbytes,v->nbits);
    size_t fixed=128+4*(2*v->nplace+1)+8*v->nz+8*(size_t)v->ncells+4*(size_t)v->ncol;
    size_t total=fixed+4*(v->ni+1)+4*(v->nc+1)+ri+rc;total=(total+3)&~(size_t)3;
    v->head[0]=0x32534956;v->head[6]=v->ni;v->head[13]=v->nc;v->head[14]=total;
    uint8_t* buf=calloc(total,1);uint8_t* q=buf;
    memcpy(q,v->head,128);q+=128;memcpy(q,v->place_base,4*(v->nplace+1));q+=4*(v->nplace+1);memcpy(q,v->mesh_first,4*v->nplace);q+=4*v->nplace;
    memcpy(q,v->rows,8*v->nz);q+=8*v->nz;memcpy(q,v->cells,8*(size_t)v->ncells);q+=8*(size_t)v->ncells;memcpy(q,v->cols,4*(size_t)v->ncol);q+=4*(size_t)v->ncol;
    uint32_t* ioff=(uint32_t*)q;q+=4*(v->ni+1);uint32_t* coff=(uint32_t*)q;q+=4*(v->nc+1);uint8_t* r0=q;
    for(unsigned k=0;k<v->ni;k++){ioff[k]=q-r0;q+=mask_encode(v->ei+(size_t)k*v->ibytes,v->ninst,q);}ioff[v->ni]=q-r0;
    for(unsigned k=0;k<v->nc;k++){coff[k]=q-r0;q+=mask_encode(v->ec+(size_t)k*v->cbytes,v->nbits,q);}coff[v->nc]=q-r0;
    FILE* o=fopen(path,"wb");fwrite(buf,1,total,o);fclose(o);free(buf);
    fprintf(stderr,"wrote %zu B: header+placements %u, rows %u, cells %zu (8 B each), columns %zu, offsets %u, instance masks %zu, column masks %zu\n",
            total,128+4*(2*v->nplace+1),8*v->nz,8*(size_t)v->ncells,4*(size_t)v->ncol,4*(v->ni+v->nc+2),ri,rc);
    return total;
}
int main(int argc,char** argv){
    if(argc<3){fprintf(stderr,"usage: bake_vis pack out [--cell MM] [--budget B] [--jobs N] [--survey] | --control in.vis [N]\n");return 1;}
    unsigned budget=256*1024,jobs=6,survey=0,wrong=0;const char* control=NULL;const char* from_raw=NULL;
    for(int i=3;i<argc;i++){
        if(!strcmp(argv[i],"--cell")&&i+1<argc)CELL=atof(argv[++i]);
        else if(!strcmp(argv[i],"--budget")&&i+1<argc)budget=atoi(argv[++i]);
        else if(!strcmp(argv[i],"--jobs")&&i+1<argc)jobs=atoi(argv[++i]);
        else if(!strcmp(argv[i],"--survey"))survey=1;
        else if(!strcmp(argv[i],"--from-raw")&&i+1<argc)from_raw=argv[++i];
        else if(!strcmp(argv[i],"--control")&&i+1<argc){control=argv[++i];wrong=1;if(i+1<argc&&argv[i+1][0]!='-')wrong=atoi(argv[++i]);}
    }
    FILE* f=fopen(argv[1],"rb");if(!f)return 1;fseek(f,0,SEEK_END);long size=ftell(f);fseek(f,0,SEEK_SET);
    uint8_t* data=malloc(size);if(fread(data,1,size,f)!=(size_t)size)return 1;fclose(f);
    Table root,frames,delta[9];if(!table(&root,data+20,size-20)||(root.n!=14&&root.n!=15))return 2;
    NativeWorld w;if(!native_world_open(&w,row(&root,2),bytes(&root,2)))return 3;
    table(&frames,row(&root,3),bytes(&root,3));
    for(int k=0;k<8;k++)table(delta+k,row(&root,4+k),bytes(&root,4+k));
    const uint8_t* m=w.mesh;
    const uint8_t *meshes=m+u32(m+40),*plod=m+u32(m+88),*clusters=m+u32(m+92),*levels=m+u32(m+96),*meshlets=m+u32(m+48);
    unsigned nplace=w.place_count;
    unsigned* place_base=calloc(nplace+1,4);unsigned* mesh_first=calloc(u32(m+16),4);unsigned* mesh_count=calloc(u32(m+16),4);
    for(unsigned me=0;me<u32(m+16);me++){
        const uint8_t* mh=meshes+68*me;unsigned first=u32(mh+12),end=first+u32(mh+16);
        unsigned lo=~0u,hi=0;
        for(unsigned part=first;part<end;part++){unsigned a=u32(plod+8*part),b=a+u32(plod+8*part+4);if(b>a){if(a<lo)lo=a;if(b>hi)hi=b;}}
        unsigned total=0;for(unsigned part=first;part<end;part++)total+=u32(plod+8*part+4);
        if(lo==~0u){lo=0;hi=0;}
        if(hi-lo!=total){fprintf(stderr,"mesh %u clusters not contiguous\n",me);return 4;}
        mesh_first[me]=lo;mesh_count[me]=hi-lo;
    }
    for(unsigned j=0;j<nplace;j++)place_base[j+1]=place_base[j]+(w.places[j].sky?0:mesh_count[w.places[j].mesh]);
    unsigned ninst=place_base[nplace];
    Box* inst=malloc(ninst*sizeof(Box));
    uint8_t* opaque_part=calloc(u32(m+20),1);
    for(unsigned part=0;part<u32(m+20);part++)opaque_part[part]=w.materials[part].phase==0;
    float rlo[3]={1e30f,1e30f,1e30f},rhi[3]={-1e30f,-1e30f,-1e30f};
    for(unsigned j=0;j<nplace;j++){
        const NativePlacement* pl=w.places+j;if(pl->sky)continue;
        const uint8_t* mh=meshes+68*pl->mesh;unsigned first=u32(mh+12),end=first+u32(mh+16);
        for(unsigned part=first;part<end;part++){
            unsigned a=u32(plod+8*part),b=a+u32(plod+8*part+4);
            for(unsigned k=a;k<b;k++){
                const uint8_t* cl=clusters+20*k;Box* bx=inst+place_base[j]+(k-mesh_first[pl->mesh]);
                for(int i=0;i<3;i++){bx->lo[i]=1e30f;bx->hi[i]=-1e30f;}
                for(int c=0;c<8;c++){float o[3];grid_point(pl->grid,u16(cl+(c&1?6:0)),u16(cl+2+(c&2?6:0)),u16(cl+4+(c&4?6:0)),o);
                    for(int i=0;i<3;i++){bx->lo[i]=fminf(bx->lo[i],o[i]);bx->hi[i]=fmaxf(bx->hi[i],o[i]);}}
                for(int i=0;i<3;i++){rlo[i]=fminf(rlo[i],bx->lo[i]);rhi[i]=fmaxf(rhi[i],bx->hi[i]);}
                if(!opaque_part[part])continue;
                unsigned lev=u32(cl+12);unsigned l=u32(levels+12*lev),stop=l+u32(levels+12*lev+4);
                for(;l<stop;l++){
                    const uint8_t* info=meshlets+28*l;
                    unsigned base=u32(info),start=u32(info+4),span=u32(info+8),verts=u16(info+12);int indexed=u16(info+14)&32768;
                    const uint8_t* strip=m+u32(m+56)+start;const uint8_t* remap=indexed?strip:NULL;if(indexed)strip+=2*verts;
                    const uint8_t* vtx=m+u32(m+52)+12*base;
                    float P[256][3];
                    for(unsigned i=0;i<verts;i++){unsigned idx=remap?u16(remap+2*i):i;const uint8_t* v=vtx+12*idx;
                        grid_point(pl->grid,u16(v),u16(v+2),u16(v+4),P[i]);}
                    for(unsigned q=0;q<span;){unsigned len=strip[q++];
                        for(unsigned t=2;t<len;t++)add_tri(P[strip[q+t-2]],P[strip[q+t-1]],P[strip[q+t]]);
                        q+=len;}
                }
            }
        }
    }
    /* recorded route (survey and control only; the bake does not use it) */
    static uint32_t state[2][65536];unsigned words1=0;
    float* cams=malloc(frames.n*12);float* camrot=malloc(frames.n*48);
    float (*roots)[3]=malloc(frames.n*64*12);unsigned* nroots=calloc(frames.n,4);
    for(unsigned fr=0;fr<frames.n;fr++){
        const uint32_t* refs=row(&frames,fr);
        for(int k=0;k<2;k++){
            const uint32_t* p=row(delta+k,refs[1+k]);const uint32_t* end=p+bytes(delta+k,refs[1+k])/4;
            unsigned next=*p++;if(k==1)words1=next;
            while(p<end){uint32_t* dest=state[k]+*p++;unsigned bits=*p++;for(;bits;bits>>=1,dest++)if(bits&1)*dest=*p++;}
        }
        const float* c=(const float*)state[0];
        for(int j=0;j<3;j++)cams[3*fr+j]=-(c[j]*c[3]+c[4+j]*c[7]+c[8+j]*c[11]);
        memcpy(camrot+12*fr,c,48);
        for(unsigned a=0;a<words1/16 && nroots[fr]<64;a++){
            if(state[1][16*a+3]!=0)continue;    /* actor roots only */
            const float* wm=(const float*)(state[1]+16*a+4);
            float* r=roots[64*fr+nroots[fr]++];r[0]=wm[3];r[1]=wm[7];r[2]=wm[11];
        }
    }
    /* camera grid over the room box */
    org[0]=floorf(rlo[0]/CELL)*CELL;org[1]=floorf(rlo[2]/CELL)*CELL;
    nx=(int)ceilf((rhi[0]-org[0])/CELL);nz=(int)ceilf((rhi[2]-org[1])/CELL);
    floor_index();
    CamCell* cc=calloc(nx*nz,sizeof(CamCell));unsigned ncore=0;
    for(int z=0;z<nz;z++)for(int x=0;x<nx;x++){
        CamCell* c=cc+z*nx+x;c->fmin=1e30f;c->fmax=-1e30f;c->top=-1e30f;
        for(int i=0;i<3;i++)for(int k=0;k<3;k++){float h;
            if(floor_at(org[0]+(x+(i+.5f)/3)*CELL,org[1]+(z+(k+.5f)/3)*CELL,&h)){c->core=1;c->fmin=fminf(c->fmin,h);c->fmax=fmaxf(c->fmax,h);c->top=fmaxf(c->top,floor_top);
                if(i==1&&k==1){c->has_centre=1;c->centre=h;}}}
        ncore+=c->core;
    }
    /* reachable on foot from the recorded route's camera cells (flood fill over cell centres) */
    unsigned nreach=0;{
        int* queue=malloc(4*nx*nz);unsigned qh=0,qt=0;
        for(unsigned fr=0;fr<frames.n;fr++){int x=(int)floorf((cams[3*fr]-org[0])/CELL),z=(int)floorf((cams[3*fr+2]-org[1])/CELL);
            if(x<0||z<0||x>=nx||z>=nz)continue;CamCell* c=cc+z*nx+x;if(!c->has_centre||c->reach)continue;c->reach=1;queue[qt++]=z*nx+x;}
        while(qh<qt){int k=queue[qh++],x=k%nx,z=k/nx;const CamCell* c=cc+k;
            static const int d[4][2]={{1,0},{-1,0},{0,1},{0,-1}};
            for(int i=0;i<4;i++){int a=x+d[i][0],b=z+d[i][1];if(a<0||b<0||a>=nx||b>=nz)continue;CamCell* o=cc+b*nx+a;
                if(o->reach||!o->has_centre||fabsf(o->centre-c->centre)>STEP||blocked(x,z,c->centre,a,b,o->centre))continue;
                o->reach=1;queue[qt++]=b*nx+a;}}
        nreach=qt;free(queue);
    }
    unsigned nbaked=0;
    for(int z=0;z<nz;z++)for(int x=0;x<nx;x++){
        CamCell* c=cc+z*nx+x;float lo=1e30f,hi=-1e30f;int any=0;
        for(int dz=-1;dz<=1;dz++)for(int dx=-1;dx<=1;dx++){int a=x+dx,b=z+dz;if(a<0||b<0||a>=nx||b>=nz)continue;
            const CamCell* o=cc+b*nx+a;if(!o->reach)continue;lo=fminf(lo,o->fmin);hi=fmaxf(hi,o->fmax);any=1;}
        if(c->reach){lo=c->fmin;hi=c->fmax;}
        if(any){c->baked=1;c->ylo=floorf((lo+BAND_LO)/YUNIT)*YUNIT;c->yhi=ceilf((hi+BAND_HI)/YUNIT)*YUNIT;nbaked++;}
    }
    /* actor cube domain: 2 m columns with a floor */
    int adim[3];for(int i=0;i<3;i++){adim[i]=(int)ceilf((rhi[i]-rlo[i])/ACUBE);if(adim[i]<1)adim[i]=1;}
    unsigned ncol=adim[0]*adim[2],ucol=0;uint8_t* col_y0=calloc(ncol,1);uint8_t* col_ny=calloc(ncol,1);uint16_t* col_base=calloc(ncol,2);unsigned nbits=0;
    uint16_t* col_bit=calloc(ncol,2);
    if(adim[1]>255){fprintf(stderr,"room too tall for the cube domain\n");return 5;}
    for(int z=0;z<adim[2];z++)for(int x=0;x<adim[0];x++){
        float lo=1e30f,hi=-1e30f;
        float x0=rlo[0]+x*ACUBE,z0=rlo[2]+z*ACUBE;
        int cx0=(int)floorf((x0-org[0])/CELL),cx1=(int)floorf((x0+ACUBE-1-org[0])/CELL),cz0=(int)floorf((z0-org[1])/CELL),cz1=(int)floorf((z0+ACUBE-1-org[1])/CELL);
        for(int b=cz0;b<=cz1;b++)for(int a=cx0;a<=cx1;a++){if(a<0||b<0||a>=nx||b>=nz)continue;const CamCell* o=cc+b*nx+a;
            if(o->core){lo=fminf(lo,o->fmin);hi=fmaxf(hi,o->top);}}   /* any floor: actors stand where cameras cannot walk (the barn) */
        unsigned c=z*adim[0]+x;
        if(lo>hi)continue;
        int y0=(int)floorf((lo-CUBE_BELOW-rlo[1])/ACUBE),y1=(int)floorf((hi+CUBE_ABOVE-rlo[1])/ACUBE);
        if(y0<0)y0=0;if(y1>=adim[1])y1=adim[1]-1;if(y1<y0)continue;
        col_y0[c]=y0;col_ny[c]=y1-y0+1;col_base[c]=nbits;nbits+=y1-y0+1;col_bit[c]=ucol;ucol++;
        if(nbits>65535){fprintf(stderr,"cube domain too large\n");return 5;}
    }
    Box* cube=malloc((nbits+1)*sizeof(Box));
    for(unsigned c=0;c<ncol;c++)for(unsigned k=0;k<col_ny[c];k++){
        int x=c%adim[0],z=c/adim[0],y=col_y0[c]+k;Box* b=cube+col_base[c]+k;
        b->lo[0]=rlo[0]+x*ACUBE;b->lo[1]=rlo[1]+y*ACUBE;b->lo[2]=rlo[2]+z*ACUBE;
        for(int i=0;i<3;i++)b->hi[i]=b->lo[i]+ACUBE;
    }
    /* query groups for speed: 4 x 4 columns; a group box no eye-face sees keeps all its cubes hidden */
    unsigned gx=(adim[0]+3)/4,gz=(adim[2]+3)/4,ngroup=gx*gz;unsigned* gfirst=calloc(ngroup+1,4);unsigned* gmem=malloc(4*nbits+4);Box* gbox=malloc(ngroup*sizeof(Box));
    {unsigned at=0;for(unsigned g=0;g<ngroup;g++){gfirst[g]=at;Box* b=gbox+g;for(int i=0;i<3;i++){b->lo[i]=1e30f;b->hi[i]=-1e30f;}
        for(int dz=0;dz<4;dz++)for(int dx=0;dx<4;dx++){int x=(g%gx)*4+dx,z=(g/gx)*4+dz;if(x>=adim[0]||z>=adim[2])continue;unsigned c=z*adim[0]+x;
            for(unsigned k=0;k<col_ny[c];k++){unsigned q=col_base[c]+k;gmem[at++]=q;for(int i=0;i<3;i++){b->lo[i]=fminf(b->lo[i],cube[q].lo[i]);b->hi[i]=fmaxf(b->hi[i],cube[q].hi[i]);}}}}
     gfirst[ngroup]=at;}
    fprintf(stderr,"room box x %.0f..%.0f y %.0f..%.0f z %.0f..%.0f; occluder triangles %u, cluster instances %u\n",rlo[0],rhi[0],rlo[1],rhi[1],rlo[2],rhi[2],ntri,ninst);
    fprintf(stderr,"camera grid %dx%d cells of %.0f mm: %u with a floor, %u reachable on foot, %u baked (with one cell of dilation); actor domain %u cubes in %u of %u columns (%dx%dx%d grid)\n",
            nx,nz,CELL,ncore,nreach,nbaked,nbits,ucol,ncol,adim[0],adim[1],adim[2]);
    {   /* route survey: does the derived domain cover the recorded route (cameras and actor roots)? */
        unsigned in=0,band=0,acin=0,actors=0;float hmin=1e30f,hmax=-1e30f;
        for(unsigned fr=0;fr<frames.n;fr++){
            const float* p=cams+3*fr;int x=(int)floorf((p[0]-org[0])/CELL),z=(int)floorf((p[2]-org[1])/CELL);
            if(x>=0&&z>=0&&x<nx&&z<nz&&cc[z*nx+x].baked){in++;const CamCell* c=cc+z*nx+x;
                if(p[1]>=c->ylo&&p[1]<=c->yhi)band++;
                if(c->reach){hmin=fminf(hmin,p[1]-c->fmax);hmax=fmaxf(hmax,p[1]-c->fmin);}}
            for(unsigned a=0;a<nroots[fr];a++){const float* r=roots[64*fr+a];actors++;
                int ax_=(int)floorf((r[0]-rlo[0])/ACUBE),ay=(int)floorf((r[1]-rlo[1])/ACUBE),az_=(int)floorf((r[2]-rlo[2])/ACUBE);
                if(ax_>=0&&az_>=0&&ax_<adim[0]&&az_<adim[2]){unsigned c=az_*adim[0]+ax_;if(col_ny[c]&&ay>=col_y0[c]&&ay<col_y0[c]+col_ny[c])acin++;
                    else if(fr==0)fprintf(stderr,"  actor root outside the cube domain: %.0f %.0f %.0f (cube y %d, column y %u+%u)\n",r[0],r[1],r[2],ay,col_y0[c],col_ny[c]);}}
        }
        fprintf(stderr,"route: %u pictures, camera in a baked cell %u, inside its band %u; camera height above floor %.0f..%.0f mm; actor roots in the cube domain %u/%u\n",
                frames.n,in,band,hmin,hmax,acin,actors);
        const float* p=cams;fprintf(stderr,"route first camera %.0f %.0f %.0f\n",p[0],p[1],p[2]);
    }
    if(survey)return 0;
    unsigned ibytes=(ninst+7)/8,cbytes=(nbits+7)/8;
    unsigned* cell_of=malloc(4*nx*nz);unsigned nb=0;
    for(int k=0;k<nx*nz;k++)cell_of[k]=cc[k].baked?nb++:~0u;
    unsigned* pos=malloc(4*nb+4);for(int k=0;k<nx*nz;k++)if(cc[k].baked)pos[cell_of[k]]=k;
    if(control){
        /* control: read the table, then hide route-visible instances in the route's cells (one new entry each) */
        FILE* in=fopen(control,"rb");if(!in)return 6;fseek(in,0,SEEK_END);long vs=ftell(in);fseek(in,0,SEEK_SET);
        uint8_t* v=malloc(vs);if(fread(v,1,vs,in)!=(size_t)vs)return 6;fclose(in);
        VisOut o={0};memcpy(o.head,v,128);uint32_t* h=o.head;
        if(h[0]!=0x32534956||h[1]!=ninst||h[3]!=(unsigned)nx||h[4]!=(unsigned)nz||h[14]!=(uint32_t)vs)return 7;
        o.nplace=nplace;o.nz=nz;o.ncells=h[5];o.ncol=h[8]*h[10];o.ninst=ninst;o.ni=h[6];o.ibytes=h[7];o.nbits=h[11];o.cbytes=h[12];o.nc=h[13];
        uint8_t* q=v+128;o.place_base=(void*)q;q+=4*(nplace+1);o.mesh_first=(void*)q;q+=4*nplace;
        o.rows=(void*)q;q+=8*nz;uint16_t* cells=(void*)q;o.cells=cells;q+=8*(size_t)o.ncells;o.cols=q;q+=4*(size_t)o.ncol;
        uint32_t* ioff=(void*)q;q+=4*(o.ni+1);uint32_t* coff=(void*)q;q+=4*(o.nc+1);uint8_t* r0=q;
        uint8_t* ei=malloc((size_t)(o.ni+o.ncells)*o.ibytes+1);uint8_t* ec=malloc((size_t)o.nc*o.cbytes+1);
        for(unsigned k=0;k<o.ni;k++){const uint8_t* m0=r0+ioff[k];if(*m0)rle_decode(m0+1,ninst,ei+(size_t)k*o.ibytes);else memcpy(ei+(size_t)k*o.ibytes,m0+1,o.ibytes);}
        for(unsigned k=0;k<o.nc;k++){const uint8_t* m0=r0+coff[k];if(*m0)rle_decode(m0+1,o.nbits,ec+(size_t)k*o.cbytes);else memcpy(ec+(size_t)k*o.cbytes,m0+1,o.cbytes);}
        unsigned* seen=calloc(ninst,4);unsigned touched=0;
        for(int k=0;k<nx*nz;k++){
            int x=k%nx,z=k/nx;unsigned x0=o.rows[2*z]&0xffff,n=o.rows[2*z]>>16,first=o.rows[2*z+1];
            if((unsigned)x<x0||(unsigned)x>=x0+n)continue;
            uint16_t* cr=cells+4*(first+x-x0);unsigned im=cr[0];if(im==0xffff)continue;
            memset(seen,0,4*ninst);unsigned route=0;
            for(unsigned fr=0;fr<frames.n;fr++){
                int a=(int)floorf((cams[3*fr]-org[0])/CELL),b=(int)floorf((cams[3*fr+2]-org[1])/CELL);if(b*nx+a!=k)continue;route++;
                memcpy(eye,cams+3*fr,12);const float* c=camrot+12*fr;
                for(int i=0;i<3;i++){basis[0][i]=c[i];basis[1][i]=c[4+i];basis[2][i]=-c[8+i];}
                render_face();
                for(unsigned t=0;t<ninst;t++)if(box_visible(inst+t))seen[t]++;
            }
            if(!route)continue;
            uint8_t* e=ei+(size_t)(o.ni+touched)*o.ibytes;memcpy(e,ei+(size_t)im*o.ibytes,o.ibytes);
            for(unsigned t=0;t<wrong;t++){unsigned best=0,bq=0;for(unsigned i=0;i<ninst;i++)if(seen[i]>best&&!(e[i>>3]>>(i&7)&1)){best=seen[i];bq=i;}
                if(best){e[bq>>3]|=1u<<(bq&7);fprintf(stderr,"  control: cell (%d,%d) instance %u (seen by %u of %u route cameras) marked hidden\n",x,z,bq,best,route);}}
            cr[0]=o.ni+touched;touched++;
        }
        o.ni+=touched;o.ei=ei;o.ec=ec;
        fprintf(stderr,"control table: %u route cells changed\n",touched);
        vis_write(argv[2],&o);
        return 0;
    }
    uint8_t* hid_i=mmap(NULL,(size_t)nb*ibytes+1,PROT_READ|PROT_WRITE,MAP_SHARED|MAP_ANONYMOUS,-1,0);
    uint8_t* hid_c=mmap(NULL,(size_t)nb*cbytes+1,PROT_READ|PROT_WRITE,MAP_SHARED|MAP_ANONYMOUS,-1,0);
    memset(hid_i,0xff,(size_t)nb*ibytes);memset(hid_c,0xff,(size_t)nb*cbytes);
    for(unsigned k=0;k<nb;k++){   /* clear padding bits beyond the counts */
        for(unsigned q=ninst;q<8*ibytes;q++)hid_i[(size_t)k*ibytes+(q>>3)]&=~(1u<<(q&7));
        for(unsigned q=nbits;q<8*cbytes;q++)hid_c[(size_t)k*cbytes+(q>>3)]&=~(1u<<(q&7));
    }
    if(from_raw){
        FILE* r=fopen(from_raw,"rb");uint32_t hh[3];
        if(!r||fread(hh,4,3,r)!=3||hh[0]!=nb||hh[1]!=ibytes||hh[2]!=cbytes){fprintf(stderr,"raw bake does not match\n");return 9;}
        if(fread(hid_i,1,(size_t)nb*ibytes,r)!=(size_t)nb*ibytes||fread(hid_c,1,(size_t)nb*cbytes,r)!=(size_t)nb*cbytes)return 9;
        fclose(r);fprintf(stderr,"loaded the raw bake %s\n",from_raw);
    }else{
    fprintf(stderr,"baking %u cells x 27 eyes in %u jobs\n",nb,jobs);
    for(unsigned j=0;j<jobs;j++){
        if(fork()==0){
            for(unsigned k=j;k<nb;k+=jobs){
                const CamCell* c=cc+pos[k];int x=pos[k]%nx,z=pos[k]/nx;
                uint8_t* hi_=hid_i+(size_t)k*ibytes;uint8_t* hc=hid_c+(size_t)k*cbytes;
                for(int s=0;s<27;s++){
                    eye[0]=org[0]+(x+.5f*(s%3))*CELL;eye[2]=org[1]+(z+.5f*((s/3)%3))*CELL;
                    eye[1]=c->ylo+(c->yhi-c->ylo)*.5f*(s/9);
                    for(int face=0;face<6;face++){
                        set_face(face);render_face();
                        for(unsigned q=0;q<ninst;q++)if((hi_[q>>3]>>(q&7)&1) && box_visible(inst+q))hi_[q>>3]&=~(1u<<(q&7));
                        for(unsigned g=0;g<ngroup;g++){
                            unsigned any=0;for(unsigned i=gfirst[g];i<gfirst[g+1] && !any;i++){unsigned q=gmem[i];any=hc[q>>3]>>(q&7)&1;}
                            if(!any || !box_visible(gbox+g))continue;
                            for(unsigned i=gfirst[g];i<gfirst[g+1];i++){unsigned q=gmem[i];if((hc[q>>3]>>(q&7)&1) && box_visible(cube+q))hc[q>>3]&=~(1u<<(q&7));}
                        }
                    }
                }
                if(j==0 && k%(100*jobs)==0)fprintf(stderr,"  cell %u/%u\n",k,nb);
            }
            _exit(0);
        }
    }
    for(unsigned j=0;j<jobs;j++)wait(NULL);
    {char rp[512];snprintf(rp,sizeof(rp),"%s.raw",argv[2]);FILE* r=fopen(rp,"wb");uint32_t hh[3]={nb,ibytes,cbytes};
     fwrite(hh,4,3,r);fwrite(hid_i,1,(size_t)nb*ibytes,r);fwrite(hid_c,1,(size_t)nb*cbytes,r);fclose(r);}
    }
    /* column masks: a column is hidden when every cube of it is hidden */
    unsigned colbytes=(ucol+7)/8;uint8_t* hid_col=calloc((size_t)nb*colbytes+1,1);
    for(unsigned k=0;k<nb;k++)for(unsigned c=0;c<ncol;c++){
        if(!col_ny[c])continue;int all=1;
        for(unsigned y=0;y<col_ny[c];y++){unsigned q=col_base[c]+y;if(!(hid_c[(size_t)k*cbytes+(q>>3)]>>(q&7)&1)){all=0;break;}}
        if(all){unsigned b=col_bit[c];hid_col[(size_t)k*colbytes+(b>>3)]|=1u<<(b&7);}
    }
    hid_c=hid_col;cbytes=colbytes;nbits=ucol;
    uint8_t *ei,*ec;unsigned* ii=malloc(4*nb+4);unsigned* ic=malloc(4*nb+4);
    unsigned ni=dict_build(hid_i,nb,ibytes,&ei,ii),nc=dict_build(hid_c,nb,cbytes,&ec,ic);
    double hidden_i=0,hidden_c=0;for(unsigned k=0;k<nb;k++){hidden_i+=popc(hid_i+(size_t)k*ibytes,ibytes);hidden_c+=popc(hid_c+(size_t)k*cbytes,cbytes);}
    int* nbr=malloc(16*nb+16);
    for(unsigned k=0;k<nb;k++){int x=pos[k]%nx,z=pos[k]/nx;int d[4][2]={{1,0},{-1,0},{0,1},{0,-1}};
        for(int i=0;i<4;i++){int a=x+d[i][0],b=z+d[i][1];nbr[4*k+i]=(a<0||b<0||a>=nx||b>=nz||cell_of[b*nx+a]==~0u)?-1:(int)cell_of[b*nx+a];}}
    unsigned* rx0=calloc(nz,4);unsigned* rn=calloc(nz,4);unsigned ncells=0;
    for(int z=0;z<nz;z++){int a=-1,b=-1;for(int x=0;x<nx;x++)if(cc[z*nx+x].baked){if(a<0)a=x;b=x;}
        if(a>=0){rx0[z]=a;rn[z]=b-a+1;ncells+=rn[z];}}
    size_t fixed=128+4*(2*nplace+1)+8*nz+8*(size_t)ncells+4*ncol;
    size_t ri=rle_total(ei,ni,ibytes,ninst),rc=rle_total(ec,nc,cbytes,nbits);
    fprintf(stderr,"before merge: %u instance masks (%zu B stored), %u column masks (%zu B stored); fixed part %zu B; total %zu B (budget %u)\n",
            ni,ri,nc,rc,fixed,fixed+4*(ni+nc+2)+ri+rc,budget);
    double lost_i=0,lost_c=0,l;
    while(fixed+4*(ni+nc+2)+ri+rc+3>budget){
        if(fixed+64>=budget){fprintf(stderr,"fixed part alone exceeds the budget\n");return 8;}
        if(rc+4*nc>=ri+4*ni && nc>1){nc=dict_merge(ec,nc,cbytes,ic,nb,nbr,nc-(nc/16>1?nc/16:1),&l);lost_c+=l;rc=rle_total(ec,nc,cbytes,nbits);}
        else if(ni>1){ni=dict_merge(ei,ni,ibytes,ii,nb,nbr,ni-(ni/16>1?ni/16:1),&l);lost_i+=l;ri=rle_total(ei,ni,ibytes,ninst);}
        else break;
    }
    double kept_i=0,kept_c=0;for(unsigned k=0;k<nb;k++){kept_i+=popc(ei+(size_t)ii[k]*ibytes,ibytes);kept_c+=popc(ec+(size_t)ic[k]*cbytes,cbytes);}
    fprintf(stderr,"after merge: %u instance masks, %u column masks; hidden instance bits kept %.1f%% (mean %.1f of %u per cell), hidden column bits kept %.1f%% (mean %.1f of %u)\n",
            ni,nc,hidden_i?100*kept_i/hidden_i:100,kept_i/nb,ninst,hidden_c?100*kept_c/hidden_c:100,kept_c/nb,nbits);
    {   /* hidden instances at the route's cells, after the merge (the route is only reported, never baked) */
        unsigned n=0;double sum=0,sumc=0;
        for(unsigned fr=0;fr<frames.n;fr++){int x=(int)floorf((cams[3*fr]-org[0])/CELL),z=(int)floorf((cams[3*fr+2]-org[1])/CELL);
            if(x<0||z<0||x>=nx||z>=nz||cell_of[z*nx+x]==~0u)continue;n++;sum+=popc(ei+(size_t)ii[cell_of[z*nx+x]]*ibytes,ibytes);
            sumc+=popc(ec+(size_t)ic[cell_of[z*nx+x]]*cbytes,cbytes);}
        fprintf(stderr,"route pictures in baked cells %u: hidden per picture %.1f of %u instances, %.1f of %u actor columns\n",n,n?sum/n:0,ninst,n?sumc/n:0,nbits);
    }
    uint32_t* rows=malloc(8*nz);uint16_t* cells=malloc(8*(size_t)ncells+8);uint8_t* cols=malloc(4*(size_t)ncol+4);
    unsigned at=0;
    for(int z=0;z<nz;z++){rows[2*z]=rx0[z]|rn[z]<<16;rows[2*z+1]=at;at+=rn[z];}
    at=0;
    for(int z=0;z<nz;z++)for(unsigned x=rx0[z];x<rx0[z]+rn[z];x++,at++){
        unsigned k=z*nx+x;uint16_t* r=cells+4*at;r[0]=r[1]=0xffff;r[2]=r[3]=0;
        if(cc[k].baked){r[0]=ii[cell_of[k]];r[1]=ic[cell_of[k]];int16_t lo=(int16_t)(cc[k].ylo/YUNIT),hi=(int16_t)(cc[k].yhi/YUNIT);memcpy(r+2,&lo,2);memcpy(r+3,&hi,2);}
    }
    for(unsigned c=0;c<ncol;c++){memcpy(cols+4*c,col_bit+c,2);cols[4*c+2]=col_y0[c];cols[4*c+3]=col_ny[c];}
    uint32_t* mf=malloc(4*nplace+4);for(unsigned j=0;j<nplace;j++)mf[j]=w.places[j].sky?0:mesh_first[w.places[j].mesh];
    VisOut o={{0,ninst,nplace,(uint32_t)nx,(uint32_t)nz,ncells,ni,ibytes,(uint32_t)adim[0],(uint32_t)adim[1],(uint32_t)adim[2],nbits,cbytes,nc,0},
              place_base,mf,nplace,(unsigned)nz,ncells,ncol,rows,cells,cols,ninst,ni,ibytes,nbits,nc,cbytes,ei,ec};
    float fh[8]={org[0],org[1],CELL,rlo[0],rlo[1],rlo[2],ACUBE,YUNIT};memcpy(o.head+16,fh,32);
    vis_write(argv[2],&o);
    return 0;
}
