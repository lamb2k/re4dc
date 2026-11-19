/* Offline baked visibility for the bench (E0 step 5). Host tool.
   Build: cc -O2 -I../render bake_vis.c ../render/native_world.c -lm -o bake_vis
   Usage: bake_vis <pack> <out.vis> [--wrong N]
   For every camera cell (CELL mm square in x/z) that the recorded route visits, sample camera positions over the cell
   (a 4 x 4 grid at the route's lowest and highest camera heights there, plus every recorded camera in it) and render
   six 90-degree depth faces of the opaque world from each. A query volume is hidden from the cell when no sample sees
   any of it: world cluster instances (placement x cluster, by their world box) and 2 m actor cubes. Occluders are
   opaque-list materials only; queries are dilated by MARGIN and pass on depth ties, so the table errs toward visible.
   --wrong N writes the control table: in every cell, the N most visible cluster instances are marked hidden. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>
#include "native_world.h"
#define CELL 500.f
#define ACUBE 2000.f
#define MARGIN 60.f
#define RES 192
#define NEARZ 20.f
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
/* Rasterise a face-space triangle (already clipped to z >= NEARZ). mode 0: write min depth; mode 1: return 1 if any
   covered pixel has depth <= stored (+tolerance). Conservative coverage for queries: pixel bounds touched. */
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
            /* perspective-correct depth: interpolate 1/z */
            float iz=w0/p[0][2]+w1/p[1][2]+w2/p[2][2];float z=1.f/iz;
            if(z<depth[y*RES+x])depth[y*RES+x]=z;
        }else{
            /* query: pixel touched by the triangle's box region; use its nearest depth (conservative) */
            float px0=x,px1=x+1,py0=y,py1=y+1;int in=0;
            for(int k=0;k<4 && !in;k++){
                float px=(k&1)?px1:px0,py=(k&2)?py1:py0;
                float w0=((p[1][0]-px)*(p[2][1]-py)-(p[2][0]-px)*(p[1][1]-py))*ia;
                float w1=((p[2][0]-px)*(p[0][1]-py)-(p[0][0]-px)*(p[2][1]-py))*ia;
                float w2=1-w0-w1;in=w0>=-.001f&&w1>=-.001f&&w2>=-.001f;
            }
            if(!in){float cx=x+.5f,cy=y+.5f;   /* triangle vertex inside the pixel */
                for(int k=0;k<3&&!in;k++)in=fabsf(p[k][0]-cx)<=.5f&&fabsf(p[k][1]-cy)<=.5f;}
            if(in && zmin<=depth[y*RES+x]*1.002f+1)return 1;
        }
    }
    return 0;
}
/* Clip a face-space polygon to z >= NEARZ and to the 90-degree pyramid's z side planes (|x|,|y| <= z, padded),
   then fan-rasterise. */
static int clip_raster(const float* a,const float* b,const float* c,int mode){
    float in[12][3],out[12][3];int n=3;
    memcpy(in[0],a,12);memcpy(in[1],b,12);memcpy(in[2],c,12);
    /* planes: z>=NEARZ, x<=1.02z, -x<=1.02z, y<=1.02z, -y<=1.02z */
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
int main(int argc,char** argv){
    if(argc<3){fprintf(stderr,"usage: bake_vis pack out [--wrong N]\n");return 1;}
    int wrong=argc>4&&!strcmp(argv[3],"--wrong")?atoi(argv[4]):0;
    FILE* f=fopen(argv[1],"rb");if(!f)return 1;fseek(f,0,SEEK_END);long size=ftell(f);fseek(f,0,SEEK_SET);
    uint8_t* data=malloc(size);if(fread(data,1,size,f)!=(size_t)size)return 1;fclose(f);
    Table root,frames,delta[8];if(!table(&root,data+20,size-20)||root.n!=14)return 2;
    NativeWorld w;if(!native_world_open(&w,row(&root,2),bytes(&root,2)))return 3;
    table(&frames,row(&root,3),bytes(&root,3));
    for(int k=0;k<8;k++)table(delta+k,row(&root,4+k),bytes(&root,4+k));
    Table hdrs;table(&hdrs,row(&root,1),bytes(&root,1));
    const uint8_t* m=w.mesh;
    const uint8_t *meshes=m+u32(m+40),*plod=m+u32(m+88),*clusters=m+u32(m+92),*levels=m+u32(m+96),*meshlets=m+u32(m+48);
    unsigned nplace=w.place_count;
    /* cluster instances: placement x cluster of its mesh (clusters of a mesh's parts are contiguous) */
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
    /* occluders and instance boxes */
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
    /* actor cubes over the room box */
    int adim[3];for(int i=0;i<3;i++){adim[i]=(int)ceilf((rhi[i]-rlo[i])/ACUBE);if(adim[i]<1)adim[i]=1;}
    unsigned ncube=adim[0]*adim[1]*adim[2];
    /* route cameras, and the actor cubes the route's bones pass through (with one cube of margin): only those are
       tested; every other cube stays visible in the table */
    static uint32_t state[2][65536];static unsigned words1;
    float* cams=malloc(frames.n*12);float* camrot=malloc(frames.n*48);
    uint8_t* relevant=calloc(ncube,1);
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
        for(unsigned a=0;a<words1/16;a++){
            const float* wm=(const float*)(state[1]+16*a+4);
            int ci[3];for(int i=0;i<3;i++)ci[i]=(int)floorf(((i==0?wm[3]:i==1?wm[7]:wm[11])-rlo[i])/ACUBE);
            for(int dz=-1;dz<=1;dz++)for(int dy=-1;dy<=1;dy++)for(int dx=-1;dx<=1;dx++){
                int x=ci[0]+dx,y=ci[1]+dy,z=ci[2]+dz;
                if(x>=0&&y>=0&&z>=0&&x<adim[0]&&y<adim[1]&&z<adim[2])relevant[x+adim[0]*(y+adim[1]*z)]=1;
            }
        }
    }
    unsigned nrel=0;for(unsigned q=0;q<ncube;q++)nrel+=relevant[q];
    float cmin[2]={1e30f,1e30f};for(unsigned fr=0;fr<frames.n;fr++){cmin[0]=fminf(cmin[0],cams[3*fr]);cmin[1]=fminf(cmin[1],cams[3*fr+2]);}
    float org[2]={floorf(cmin[0]/CELL)*CELL,floorf(cmin[1]/CELL)*CELL};
    int cx_n=0,cz_n=0;
    for(unsigned fr=0;fr<frames.n;fr++){int a=(int)((cams[3*fr]-org[0])/CELL),b=(int)((cams[3*fr+2]-org[1])/CELL);if(a+1>cx_n)cx_n=a+1;if(b+1>cz_n)cz_n=b+1;}
    unsigned ncell=cx_n*cz_n;
    uint8_t* used=calloc(ncell,1);
    unsigned ibytes=(ninst+7)/8,cbytes=(ncube+7)/8;
    uint8_t* hidden_i=malloc(ncell*ibytes);uint8_t* hidden_c=malloc(ncell*cbytes);
    memset(hidden_i,0xff,ncell*ibytes);memset(hidden_c,0,ncell*cbytes);
    for(unsigned cell=0;cell<ncell;cell++)for(unsigned q=0;q<ncube;q++)if(relevant[q])hidden_c[cell*cbytes+(q>>3)]|=1u<<(q&7);
    unsigned* seen=calloc(ninst,4);
    fprintf(stderr,"occluder triangles %u, cluster instances %u, actor cubes %u (%dx%dx%d, %u tested), camera cells %dx%d\n",ntri,ninst,ncube,adim[0],adim[1],adim[2],nrel,cx_n,cz_n);
    for(unsigned cell=0;cell<ncell;cell++){
        float ylo=1e30f,yhi=-1e30f;unsigned route=0;
        for(unsigned fr=0;fr<frames.n;fr++){int a=(int)((cams[3*fr]-org[0])/CELL),b=(int)((cams[3*fr+2]-org[1])/CELL);
            if((unsigned)(b*cx_n+a)==cell){route++;ylo=fminf(ylo,cams[3*fr+1]);yhi=fmaxf(yhi,cams[3*fr+1]);}}
        if(!route)continue;
        used[cell]=1;memset(seen,0,4*ninst);
        float x0=org[0]+(cell%cx_n)*CELL,z0=org[1]+(cell/cx_n)*CELL;
        unsigned nsamples=32+route;float (*S)[3]=malloc(nsamples*12);unsigned ns=0;
        for(int i=0;i<4;i++)for(int k=0;k<4;k++)for(int h=0;h<2;h++){S[ns][0]=x0+CELL*(i+.5f)/4;S[ns][2]=z0+CELL*(k+.5f)/4;S[ns][1]=(h?yhi+100:ylo-100);ns++;}
        for(unsigned fr=0;fr<frames.n;fr++){int a=(int)((cams[3*fr]-org[0])/CELL),b=(int)((cams[3*fr+2]-org[1])/CELL);
            if((unsigned)(b*cx_n+a)==cell)memcpy(S[ns++],cams+3*fr,12);}
        uint8_t* hi_=hidden_i+cell*ibytes;uint8_t* hc=hidden_c+cell*cbytes;
        for(unsigned s=0;s<ns;s++){
            memcpy(eye,S[s],12);
            for(int face=0;face<6;face++){
                set_face(face);
                for(int i=0;i<RES*RES;i++)depth[i]=1e30f;
                for(unsigned t=0;t<ntri;t++){float a[3],b[3],c[3];to_face(tris[t].v[0],a);to_face(tris[t].v[1],b);to_face(tris[t].v[2],c);
                    if(a[2]<NEARZ&&b[2]<NEARZ&&c[2]<NEARZ)continue;
                    if(a[0]>1.02f*a[2]&&b[0]>1.02f*b[2]&&c[0]>1.02f*c[2])continue;if(-a[0]>1.02f*a[2]&&-b[0]>1.02f*b[2]&&-c[0]>1.02f*c[2])continue;
                    if(a[1]>1.02f*a[2]&&b[1]>1.02f*b[2]&&c[1]>1.02f*c[2])continue;if(-a[1]>1.02f*a[2]&&-b[1]>1.02f*b[2]&&-c[1]>1.02f*c[2])continue;
                    clip_raster(a,b,c,0);}
                for(unsigned q=0;q<ninst;q++){
                    if(!(hi_[q>>3]>>(q&7)&1) && !wrong)continue;
                    if(box_visible(inst+q)){hi_[q>>3]&=~(1u<<(q&7));seen[q]++;}
                }
                for(unsigned q=0;q<ncube;q++){
                    if(!(hc[q>>3]>>(q&7)&1))continue;
                    int ix=q%adim[0],iy=(q/adim[0])%adim[1],iz=q/(adim[0]*adim[1]);
                    Box b={{rlo[0]+ix*ACUBE,rlo[1]+iy*ACUBE,rlo[2]+iz*ACUBE},{rlo[0]+(ix+1)*ACUBE,rlo[1]+(iy+1)*ACUBE,rlo[2]+(iz+1)*ACUBE}};
                    if(box_visible(&b))hc[q>>3]&=~(1u<<(q&7));
                }
            }
        }
        unsigned hid=0,hcub=0;for(unsigned q=0;q<ninst;q++)hid+=hi_[q>>3]>>(q&7)&1;for(unsigned q=0;q<ncube;q++)hcub+=hc[q>>3]>>(q&7)&1;
        if(wrong){
            /* the control must hide something the route actually shows: count, per instance, the route cameras whose
               forward 90-degree face (along the view direction) sees it */
            memset(seen,0,4*ninst);
            for(unsigned fr=0;fr<frames.n;fr++){
                int a=(int)((cams[3*fr]-org[0])/CELL),b=(int)((cams[3*fr+2]-org[1])/CELL);
                if((unsigned)(b*cx_n+a)!=cell)continue;
                memcpy(eye,cams+3*fr,12);const float* c=camrot+12*fr;
                for(int i=0;i<3;i++){basis[0][i]=c[i];basis[1][i]=c[4+i];basis[2][i]=-c[8+i];}
                for(int i=0;i<RES*RES;i++)depth[i]=1e30f;
                for(unsigned t=0;t<ntri;t++){float a3[3],b3[3],c3[3];to_face(tris[t].v[0],a3);to_face(tris[t].v[1],b3);to_face(tris[t].v[2],c3);
                    if(a3[2]<NEARZ&&b3[2]<NEARZ&&c3[2]<NEARZ)continue;clip_raster(a3,b3,c3,0);}
                for(unsigned q=0;q<ninst;q++)if(box_visible(inst+q))seen[q]++;
            }
            for(int k=0;k<wrong;k++){unsigned best=0,bq=0;for(unsigned q=0;q<ninst;q++)if(seen[q]>best&&!(hi_[q>>3]>>(q&7)&1)){best=seen[q];bq=q;}
                if(best){hi_[bq>>3]|=1u<<(bq&7);fprintf(stderr,"  control: cell %u instance %u (seen %u) marked hidden\n",cell,bq,best);}}
        }
        fprintf(stderr,"cell %u (%d,%d) route cameras %u samples %u: hidden instances %u/%u, hidden actor cubes %u/%u\n",cell,cell%cx_n,cell/cx_n,route,ns,hid,ninst,hcub,ncube);
        free(S);
    }
    /* file: 'VIS1', counts, grids, then per cell: used flag, instance bits, cube bits */
    FILE* o=fopen(argv[2],"wb");
    uint32_t head[16]={0x31534956,ninst,ncube,ncell,(uint32_t)cx_n,(uint32_t)cz_n,(uint32_t)adim[0],(uint32_t)adim[1],(uint32_t)adim[2],nplace,ibytes,cbytes,0,0,0,0};
    float fh[8]={org[0],org[1],CELL,rlo[0],rlo[1],rlo[2],ACUBE,0};
    fwrite(head,4,16,o);fwrite(fh,4,8,o);fwrite(place_base,4,nplace+1,o);
    for(unsigned j=0;j<nplace;j++){unsigned mf=w.places[j].sky?0:mesh_first[w.places[j].mesh];fwrite(&mf,4,1,o);}
    fwrite(used,1,ncell,o);
    for(unsigned cell=0;cell<ncell;cell++){fwrite(hidden_i+cell*ibytes,1,ibytes,o);fwrite(hidden_c+cell*cbytes,1,cbytes,o);}
    fclose(o);
    return 0;
}
