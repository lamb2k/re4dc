#include "replay.h"
#include <malloc.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
extern volatile uint32_t m1_state[8];
pvr_ptr_t m1_textures[M1_TEXTURE_LIMIT];
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
    if(s->texture.n>M1_TEXTURE_LIMIT)return 0;
    unsigned palette_bits[M1_TEXTURE_LIMIT]={0};
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
    f->atmosphere=NULL;f->volume=NULL;f->volume_bytes=0;
    if(s->environment.n){
        if(bytes(&s->environment,p[0]))f->atmosphere=row(&s->environment,p[0]);
        f->volume=row(&s->volumes,p[1]);f->volume_bytes=bytes(&s->volumes,p[1]);
    }
}
static int indexed_valid(const IndexedPart *g,unsigned size,unsigned *maximum){
    if(size<sizeof(*g) || g->positions>INDEX_LIMIT || g->normals>INDEX_LIMIT ||
       !g->positions || !g->normals || g->signed_uv>1)return 0;
    unsigned vectors=g->positions+g->normals;
    unsigned left=size-sizeof(*g);
    if(vectors>left/sizeof(SourceVector))return 0;
    const SourceVector *v=(const SourceVector*)(g+1);
    for(unsigned i=0;i<vectors;i++)if(v[i].bone>*maximum)*maximum=v[i].bone;
    const uint8_t *p=(const uint8_t*)(v+vectors);
    left-=vectors*sizeof(*v);
    for(unsigned i=0;i<g->strips;i++){
        if(left<4)return 0;
        unsigned count=*(const uint32_t*)p;
        left-=4;p+=4;
        if(count<3 || count>left/sizeof(IndexCorner))return 0;
        const IndexCorner *c=(const IndexCorner*)p;
        for(unsigned j=0;j<count;j++)
            if(c[j].position>=g->positions || c[j].normal>=g->normals)return 0;
        p+=count*sizeof(*c);left-=count*sizeof(*c);
    }
    return left==0;
}
static int bones_valid(const Scene *s){
    /* Geometry and pose rows are shared across pictures. Check bone indices
       once per unique geometry, then check each binding against its palette. */
    unsigned *maximum=calloc(s->geometry.n,sizeof(*maximum));
    if(!maximum)return 0;
    for(unsigned i=0;i<s->geometry.n;i++){
        const uint8_t *p=row(&s->geometry,i),*end=p+bytes(&s->geometry,i);
        if(end-p>=4 && *(const uint32_t*)p==INDEX_MAGIC){
            if(!indexed_valid((const IndexedPart*)p,end-p,maximum+i)){free(maximum);return 0;}
            continue;
        }
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
        if(n>PALETTE_LIMIT+1)ok=0;
        if(bytes(&s->geometry,d[1])>=4 && *(uint32_t*)row(&s->geometry,d[1])==INDEX_MAGIC)continue;
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
    for(unsigned i=0;i<s->environment.n;i++){
        unsigned size=bytes(&s->environment,i);
        if(size && size!=528)return 0;
    }
    for(unsigned i=0;i<s->volumes.n;i++){
        unsigned left=bytes(&s->volumes,i);
        const uint32_t *v=row(&s->volumes,i);
        while(left){
            if(left<32)return 0;
            unsigned type=v[0]>>24;
            unsigned n=type==0xf0?64:((type&0xfd)==0x81?32:0);
            if(!n || n>left)return 0;
            left-=n;v+=n/4;
        }
    }
    if(s->frame.n!=300)return 0;
    for(unsigned i=0;i<s->geometry.n;i++){
        unsigned left=bytes(&s->geometry,i); const uint8_t *p=row(&s->geometry,i);
        if(left>=4 && *(uint32_t*)p==INDEX_MAGIC)continue;
        while(left){if(left<sizeof(Strip))return 0;const Strip *h=(const Strip*)p;
            unsigned span=sizeof(*h)+h->n*sizeof(Vertex);
            if(h->n<3 || h->n>1024 || span>left)return 0;
            p+=span;left-=span;
        }
    }
    for(unsigned i=0;i<s->draw.n;i++){
        if(bytes(&s->draw,i)!=16 && bytes(&s->draw,i)!=24)return 0;
        const unsigned *p=row(&s->draw,i);
        if(p[0]>=s->header.n || p[1]>=s->geometry.n || p[2]>=s->pose.n || p[3]>=s->light.n)return 0;
        if(bytes(&s->draw,i)==24){
            const IndexedPart *g=row(&s->geometry,p[1]);
            unsigned bones=bytes(&s->pose,p[2])/48;
            bones=bones>1?bones-1:1;
            if(bytes(&s->geometry,p[1])<sizeof(*g) || g->magic!=INDEX_MAGIC ||
               p[4]>8192 || g->positions>8192-p[4] || p[5]>1536 || bones>1536-p[5])return 0;
        }
        if(bytes(&s->pose,p[2])%48 || (bytes(&s->light,p[3]) && bytes(&s->light,p[3])!=500 && bytes(&s->light,p[3])!=136))return 0;
    }
    for(unsigned i=0;i<s->frame.n;i++){
        unsigned left=bytes(&s->frame,i)/4; const unsigned *p=row(&s->frame,i);
        if(left<31)return 0;
        left-=25;p+=25;
        for(int j=0;j<6;j++){if(!left)return 0;unsigned n=*p++;if(n>--left)return 0;
            left-=n;while(n--)if((*p++&0x7fffffff)>=s->draw.n)return 0;}
        if(s->environment.n){if(left!=2 || p[0]>=s->environment.n || p[1]>=s->volumes.n)return 0;}
        else if(left)return 0;
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
    int ok=data && got==size && !memcmp(h,"M1PK",4) && (h[1]==1 || h[1]==2) && h[3]==size-20;
    Table root;
    if(ok){
        m1_state[1]=3;
        ok=crc32(data+20,h[3])==h[4] && table(&root,data+20,h[3]) && root.n==(h[1]==1?7:9);
    }
    Table* sections[]={&s->texture,&s->header,&s->geometry,&s->pose,&s->light,&s->draw,&s->frame,&s->environment,&s->volumes};
    for(int i=0;ok && i<root.n;i++)ok=table(sections[i],row(&root,i),bytes(&root,i));
    if(ok){m1_state[1]=4;ok=validate(s);} if(ok){m1_state[1]=5;ok=uploads(s);}
    printf("M1 pack %s %s\n",path,ok?"loaded":"REFUSED");
    return ok;
}
void close_scene(Scene* s){
    for(unsigned i=0;i<M1_TEXTURE_LIMIT;i++)if(m1_textures[i]){pvr_mem_free(m1_textures[i]);m1_textures[i]=NULL;}
    banks=0;free(s->storage);memset(s,0,sizeof(*s));
}



#ifdef M1_NATIVE
#include "native_scene.inc"
#endif
