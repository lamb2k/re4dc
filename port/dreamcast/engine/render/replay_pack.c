#include "replay.h"
#include <malloc.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
extern volatile uint32_t m1_state[8];
pvr_ptr_t m1_textures[256];
static uint32_t crc32(const uint8_t* p,unsigned n) {
    uint32_t lut[256];
    for(unsigned i=0;i<256;i++){ unsigned c=i; for(int k=0;k<8;k++) c=(c>>1)^((0-(c&1))&0xedb88320); lut[i]=c; }
    unsigned c=~0u;
    while(n--) c=(c>>8)^lut[(c^*p++)&255];
    return ~c;
}
static int table(Table* t,void* data,unsigned size){
    if(size<8)return 0;
    unsigned* w=data, n=w[0];
    if(n>(size-8)/4 || w[1]!=0)return 0;
    unsigned header=8+4*n;
    for(unsigned i=0;i<n;i++)if(w[i+1]>w[i+2] || w[i+2]>size-header || w[i+2]%4)return 0;
    t->n=n;t->offset=w+1;t->base=(uint8_t*)data+header;
    return w[n+1]==size-header;
}
static uint32_t palette[64][16];
static unsigned banks;
static int uploads(Scene* s) {
    if(s->texture.n>256)return 0;
    unsigned palette_bits[256]={0};
    pvr_set_pal_format(PVR_PAL_ARGB8888);
    for(unsigned i=0;i<s->texture.n;i++){
        const uint32_t *p=row(&s->texture,i);
        unsigned size=bytes(&s->texture,i);
        if(size<144 || memcmp(p,"RE4DCTX",7) || p[5]!=1 || p[6]>size-96)return 0;
        const uint32_t *t=p+p[6]/4+16;
        unsigned fmt=t[2],at=t[3],len=t[4];
        if(at>size || len>size-at || len==0)return 0;
        const uint8_t *data=(const uint8_t*)p+at;
        if(fmt==4){
            unsigned tail=t[5]&8?64:32;
            if(len<=tail)return 0;
            len-=tail;
            uint32_t colors[16];
            for(unsigned j=0;j<16;j++){
                if(tail==64) memcpy(colors+j,data+len+4*j,4);
                else {
                    uint16_t c;memcpy(&c,data+len+2*j,2);
                    colors[j]=((c>>12)*17u<<24)|(((c>>8)&15)*17u<<16)|(((c>>4)&15)*17u<<8)|((c&15)*17u);
                }
            }
            unsigned bank=0;
            while(bank<banks && memcmp(colors,palette[bank],64))bank++;
            if(bank==64)return 0;
            if(bank==banks){memcpy(palette[banks++],colors,64); for(unsigned j=0;j<16;j++)pvr_set_pal_entry(bank*16+j,colors[j]);}
            palette_bits[i]=PVR_TXRFMT_4BPP_PAL(bank);
        } else if(fmt>2)return 0;
        m1_textures[i]=pvr_mem_malloc((len+31)&~31u);
        if(!m1_textures[i])return 0;
        pvr_txr_load(data,m1_textures[i],len);
    }
    for(unsigned i=0;i<s->header.n;i++){
        if(bytes(&s->header,i)!=36)return 0;
        uint32_t *h=row(&s->header,i);
        if(h[0]>=s->texture.n)return 0;
        h[4]|=((uintptr_t)m1_textures[h[0]]&0x7fffff)>>3 | palette_bits[h[0]];
    }
    return 1;
}
void open_picture(const Scene *s,unsigned i,Picture* f){
    const unsigned *p=row(&s->frame,i);
    f->camera=(const float*)p;p+=25;
    for(int j=0;j<6;j++){ f->count[j]=*p++;f->ids[j]=p;p+=f->count[j];}
}
static int bones_valid(const Scene *s){
    /* Geometry and pose rows are shared across pictures. Check bone indices
       once per unique geometry, then check each binding against its palette. */
    unsigned *maximum=calloc(s->geometry.n,sizeof(*maximum));
    if(!maximum)return 0;
    for(unsigned i=0;i<s->geometry.n;i++){
        const uint8_t *p=row(&s->geometry,i),*end=p+bytes(&s->geometry,i);
        while(p<end){
            const Strip *strip=(const Strip*)p;
            const Vertex *v=(const Vertex*)(strip+1);
            for(unsigned j=0;j<strip->n;j++){
                if(v[j].bone>maximum[i])maximum[i]=v[j].bone;
                if(strip->bone!=65535 && strip->bone!=v[j].bone){free(maximum);return 0;}
            }
            p=(const uint8_t*)(v+strip->n);
        }
    }
    int ok=1;
    for(unsigned i=0;ok && i<s->draw.n;i++){
        const unsigned *d=row(&s->draw,i);
        unsigned n=bytes(&s->pose,d[2])/48;
        if((n<=1 && maximum[d[1]]!=0) || (n>1 && maximum[d[1]]>=n-1))ok=0;
        if(n>1 && bytes(&s->light,d[3])){
            const uint8_t *p=row(&s->geometry,d[1]),*end=p+bytes(&s->geometry,d[1]);
            while(p<end && ok){
                const Strip *strip=(const Strip*)p;const Vertex *v=(const Vertex*)(strip+1);
                for(unsigned j=0;j<strip->n;j++)if((v[j].color&255)>=n-1){ok=0;break;}
                p=(const uint8_t*)(v+strip->n);
            }
        }
    }
    free(maximum);return ok;
}
static int validate(Scene* s){
    if(s->frame.n!=300)return 0;
    for(unsigned i=0;i<s->geometry.n;i++){
        unsigned left=bytes(&s->geometry,i); const uint8_t *p=row(&s->geometry,i);
        while(left){if(left<sizeof(Strip))return 0;const Strip *h=(const Strip*)p;
            unsigned span=sizeof(*h)+h->n*sizeof(Vertex);
            if(h->n<3 || h->n>1024 || span>left)return 0;
            p+=span;left-=span;
        }
    }
    for(unsigned i=0;i<s->draw.n;i++){
        if(bytes(&s->draw,i)!=16)return 0;
        const unsigned *p=row(&s->draw,i);
        if(p[0]>=s->header.n || p[1]>=s->geometry.n || p[2]>=s->pose.n || p[3]>=s->light.n)return 0;
        if(bytes(&s->pose,p[2])%48 || (bytes(&s->light,p[3]) && bytes(&s->light,p[3])!=500))return 0;
    }
    for(unsigned i=0;i<s->frame.n;i++){
        unsigned left=bytes(&s->frame,i)/4; const unsigned *p=row(&s->frame,i);
        if(left<31)return 0;
        left-=25;p+=25;
        for(int j=0;j<6;j++){if(!left)return 0;unsigned n=*p++;if(n>--left)return 0;
            left-=n;while(n--)if(*p++>=s->draw.n)return 0;}
        if(left)return 0;
    }
    return bones_valid(s);
}
int open_scene(Scene* s,const char* path){
    m1_state[1]=1;
    file_t f=fs_open(path,O_RDONLY);
    if(f<0){printf("M1 missing pack %s\n",path);return 0;}
    size_t size=fs_total(f);
    uint8_t *data=NULL;
    if(size>=20 && size<14*1024*1024) data=memalign(32,size+32);
    s->storage=data;
    size_t got=0;
    while(data && got<size){
        m1_state[1]=100+got/65536;
        unsigned n=size-got>65536?65536:size-got;
        ssize_t r=fs_read(f,data+got,n);if(r<=0)break;
        got+=r;
    }
    fs_close(f);
    const uint32_t *h=(const uint32_t*)data;
    int ok=data && got==size && !memcmp(h,"M1PK",4) && h[1]==1 && h[3]==size-20;
    Table root;
    if(ok){
        m1_state[1]=3;
        ok=crc32(data+20,h[3])==h[4] && table(&root,data+20,h[3]) && root.n==7;
    }
    Table* sections[]={&s->texture,&s->header,&s->geometry,&s->pose,&s->light,&s->draw,&s->frame};
    for(int i=0;ok && i<7;i++)ok=table(sections[i],row(&root,i),bytes(&root,i));
    if(ok){m1_state[1]=4;ok=validate(s);} if(ok){m1_state[1]=5;ok=uploads(s);}
    printf("M1 pack %s %s\n",path,ok?"loaded":"REFUSED");
    return ok;
}
void close_scene(Scene* s){
    for(unsigned i=0;i<256;i++)if(m1_textures[i]){pvr_mem_free(m1_textures[i]);m1_textures[i]=NULL;}
    banks=0;free(s->storage);memset(s,0,sizeof(*s));
}



