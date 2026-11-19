/* Host replay of the bench's world selection over a NAT3 pack: per-picture meshlet, vertex and corner counts.
   Build: cc -O2 -I../render host_world.c ../render/native_world.c -lm -o host_world
   Usage: host_world <pack> [csv]   (private pack; nothing here embeds game data) */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include "native_world.h"
typedef struct { uint32_t n; const unsigned* offset; uint8_t* base; } Table;
static void* row(const Table* t,unsigned i){return t->base+t->offset[i];}
static unsigned bytes(const Table* t,unsigned i){return t->offset[i+1]-t->offset[i];}
static int table(Table* t,void* data,unsigned size){
    if(size<8)return 0;unsigned* w=data,n=w[0];
    if(n>(size-8)/4||w[1]!=0)return 0;
    t->n=n;t->offset=w+1;t->base=(uint8_t*)data+8+4*n;return w[n+1]==size-8-4*n;
}
int main(int argc,char** argv){
    FILE* f=fopen(argv[1],"rb");if(!f)return 1;fseek(f,0,SEEK_END);long size=ftell(f);fseek(f,0,SEEK_SET);
    uint8_t* data=malloc(size);if(fread(data,1,size,f)!=(size_t)size)return 1;fclose(f);
    Table root,frames,delta[8];if(!table(&root,data+20,size-20)||root.n!=14)return 2;
    NativeWorld w;if(!native_world_open(&w,row(&root,2),bytes(&root,2)))return 3;
    if(!native_world_runtime(&w))return 4;
    printf("runtime vertices %u (duplicates %u, whole-staged meshlets %u)\n",w.rt_vertices,w.rt_duplicates,w.rt_full);
    table(&frames,row(&root,3),bytes(&root,3));
    for(int k=0;k<8;k++)table(delta+k,row(&root,4+k),bytes(&root,4+k));
    static uint32_t state[8][32768];
    static NativePiece out[8192];
    const uint8_t* m=w.mesh;const uint32_t* h=(const void*)m;
    FILE* csv=argc>2?fopen(argv[2],"w"):NULL;
    if(csv)fprintf(csv,"picture,meshlets,boundary,vertices,corners,boundary_vertices,boundary_corners,strips\n");
    double sum[7]={0};
    for(unsigned frame=0;frame<frames.n;frame++){
        const uint32_t* refs=row(&frames,frame);
        for(int k=0;k<8;k++){
            const uint32_t* p=row(delta+k,refs[k+1]);const uint32_t* end=p+bytes(delta+k,refs[k+1])/4;
            unsigned next=*p++;(void)next;
            while(p<end){uint32_t* dest=state[k]+*p++;unsigned bits=*p++;for(;bits;bits>>=1,dest++)if(bits&1)*dest=*p++;}
        }
        int n=native_world_select(&w,(const float*)state[0],2.f,out,8192);
        unsigned bnd=0,verts=0,corners=0,bverts=0,bcorners=0,strips=0;
        unsigned groups=w.group_bytes?((const unsigned*)w.groups)[3]:1;
        for(int i=0;i<n;i++){
            const uint8_t* let=m+h[12]+28*out[i].meshlet;const uint32_t* l=(const void*)let;const uint16_t* desc=(const void*)(let+12);
            const uint8_t* strip=m+h[14]+l[1];if(desc[1]&32768)strip+=2*desc[0];
            unsigned c=0,before=0;
            for(unsigned g=0;g<groups;g++){
                unsigned after=w.group_bytes?*(const uint16_t*)(w.groups+32+16*(out[i].meshlet*groups+g)+12):l[2];
                const uint8_t* s=strip+before,*e=strip+after;before=after;
                if(!(out[i].groups&(1u<<g)))continue;
                while(s<e){unsigned k=*s++;c+=k;s+=k;strips++;}
            }
            unsigned staged=0;const uint8_t* rg=w.rt_range+2*groups*out[i].meshlet;
            if(w.rt[out[i].meshlet].full)staged=w.rt[out[i].meshlet].count;else for(unsigned g=0;g<groups;g++)if(out[i].groups>>g&1)staged+=rg[2*g+1];
            verts+=staged;corners+=c;
            if(out[i].near_class!=1){bnd++;bverts+=staged;bcorners+=c;}
        }
        if(csv)fprintf(csv,"%u,%d,%u,%u,%u,%u,%u,%u\n",frame+1,n,bnd,verts,corners,bverts,bcorners,strips);
        double v[7]={n,bnd,verts,corners,bverts,bcorners,strips};for(int k=0;k<7;k++)sum[k]+=v[k];
    }
    printf("mean per picture: meshlets %.1f boundary %.1f vertices %.0f corners %.0f boundary_vertices %.0f boundary_corners %.0f strips %.0f\n",
        sum[0]/frames.n,sum[1]/frames.n,sum[2]/frames.n,sum[3]/frames.n,sum[4]/frames.n,sum[5]/frames.n,sum[6]/frames.n);
    unsigned hist[9]={0};unsigned nm=h[6];
    for(unsigned i=0;i<nm;i++){unsigned v=((const uint16_t*)(m+h[12]+28*i+12))[0];hist[v>=256?8:v/32]++;}
    printf("meshlets %u, vertex-count histogram by 32:",nm);for(int i=0;i<9;i++)printf(" %u",hist[i]);printf("\n");
    return 0;
}
