#include "native_world.h"
#include <math.h>
#include <string.h>
static uint32_t u32(const void* p){uint32_t x;memcpy(&x,p,4);return x;}
static uint16_t u16(const void* p){uint16_t x;memcpy(&x,p,2);return x;}
static float f32(const void* p){float x;memcpy(&x,p,4);return x;}
static int range(unsigned off,unsigned count,unsigned stride,unsigned size){
    return off<=size && count<=(size-off)/stride;
}
int native_world_open(NativeWorld* w,const void* data,size_t size){
    const uint8_t* b=data;
    if(size<28||memcmp(b,"NWR3",4))return 0;
    unsigned n=u32(b+4),c=u32(b+8),ml=u32(b+12),mt=u32(b+16),pl=u32(b+20),cl=u32(b+24);
    if(ml<112 || (uint64_t)28+ml+mt+pl+cl>size || (uint64_t)n*84!=pl || (uint64_t)c*32!=cl)return 0;
    const uint8_t *m=b+28;
    if(memcmp(m,"R4IM",4)||u32(m+4)!=3||u32(m+8)!=ml||u32(m+20)*(uint64_t)8!=mt)return 0;
    const unsigned strides[]={68,36,28,12,1,4};
    for(unsigned k=0;k<6;k++)if(!range(u32(m+40+4*k),u32(m+16+4*k),strides[k],ml))return 0;
    if(!range(u32(m+88),u32(m+20),8,ml)||!range(u32(m+92),u32(m+80),20,ml)||!range(u32(m+96),u32(m+84),12,ml))return 0;
    *w=(NativeWorld){m,m+ml+mt+pl+cl,(const void*)(m+ml),(const void*)(m+ml+mt),(const void*)(m+ml+mt+pl),c,n,size-(28+ml+mt+pl+cl)};
    for(unsigned i=0;i<c;i++)if(!range(w->cells[i].first,w->cells[i].count,1,n))return 0;
    for(unsigned i=0;i<n;i++)if(w->places[i].mesh>=u32(m+16))return 0;
    for(unsigned i=0;i<u32(m+16);i++){
        const uint8_t *r=m+u32(m+40)+68*i;
        if(!range(u32(r+12),u32(r+16),1,u32(m+20)))return 0;
    }
    for(unsigned i=0;i<u32(m+20);i++){
        const uint8_t *r=m+u32(m+88)+8*i;
        if(!range(u32(r),u32(r+4),1,u32(m+80)))return 0;
    }
    for(unsigned i=0;i<u32(m+80);i++){
        const uint8_t *r=m+u32(m+92)+20*i;
        if(!u32(r+16)||!range(u32(r+12),u32(r+16),1,u32(m+84)))return 0;
    }
    for(unsigned i=0;i<u32(m+84);i++){
        const uint8_t *r=m+u32(m+96)+12*i;
        if(!range(u32(r),u32(r+4),1,u32(m+24)))return 0;
    }
    return 1;
}
// Plane equations in object coordinates allow all children to share one transform.
static void compose(NativeFrustum* out,const NativeFrustum* in,const float* m){
    for(unsigned p=0;p<6;p++)for(unsigned j=0;j<4;j++)
        out->p[p][j]=in->p[p][0]*m[j]+in->p[p][1]*m[j+4]+in->p[p][2]*m[j+8]+(j==3?in->p[p][3]:0);
}
static int classify(const NativeFrustum* f,const float* c,const float* h,float* nearest){
    int cls=1;
    for(unsigned i=0;i<6;i++){
        const float* p=f->p[i];
        float s=p[0]*c[0]+p[1]*c[1]+p[2]*c[2]+p[3];
        float r=fabsf(p[0])*h[0]+fabsf(p[1])*h[1]+fabsf(p[2])*h[2];
        if(s+r<0)return 0;
        if(i==0){*nearest=s-r;if(s<r)cls=2;}
    }
    return cls;
}
static int grid_class(const NativeFrustum* f,const uint8_t* r,float* nearest){
    float c[3],h[3];
    for(unsigned i=0;i<3;i++){float a=u16(r+2*i),b=u16(r+6+2*i);c[i]=(a+b)*.5f;h[i]=(b-a)*.5f;}
    return classify(f,c,h,nearest);
}
int native_world_select(const NativeWorld* w,const float* camera,float pixels,NativePiece* out,unsigned capacity){
    const float* p=camera+12;
    float near=p[6]/(p[5]-1),far=camera[25];
    NativeFrustum view={{{0,0,-1,-near},{0,0,1,far},{p[1],0,p[2]-1,0},{-p[1],0,-p[2]-1,0},{0,p[3],p[4]-1,0},{0,-p[3],-p[4]-1,0}}},world;
    compose(&world,&view,camera);
    const uint8_t* m=w->mesh;
    const uint8_t *meshes=m+u32(m+40),*plod=m+u32(m+88),*clusters=m+u32(m+92),*levels=m+u32(m+96),*meshlets=m+u32(m+48);
    unsigned count=0;
    for(unsigned i=0;i<w->cell_count;i++){
        float z;const NativeCell* cell=w->cells+i;
        if(!classify(&world,cell->center,cell->half,&z))continue;
        for(unsigned j=cell->first;j<cell->first+cell->count;j++){
            const NativePlacement* place=w->places+j;
            if(place->sky||!classify(&world,place->center,place->half,&z))continue;
            NativeFrustum local;compose(&local,&world,place->grid);
            const uint8_t* mesh=meshes+68*place->mesh;
            unsigned first=u32(mesh+12),end=first+u32(mesh+16);
            float lod=fabsf(p[1])*320*place->scale/pixels;
            for(unsigned part=first;part<end;part++){
                const uint8_t* span=plod+8*part;
                unsigned a=u32(span),b=a+u32(span+4);
                for(unsigned k=a;k<b;k++){
                    const uint8_t* cl=clusters+20*k;
                    if(!grid_class(&local,cl,&z))continue;
                    unsigned lev=u32(cl+12),last=lev+u32(cl+16);
                    while(lev+1<last && f32(levels+12*(lev+1)+8)*lod<=z+near)++lev;
                    unsigned l=u32(levels+12*lev),stop=l+u32(levels+12*lev+4);
                    for(;l<stop;l++){
                        int cls=grid_class(&local,meshlets+28*l+16,&z);
                        if(!cls)continue;
                        if(count>=capacity)return -1;
                        out[count++]=(NativePiece){j,part,l,w->materials[part].header,cls};
                    }
                }
            }
        }
    }
    return count;
}
