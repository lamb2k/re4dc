#include "native_scene.h"
// A patch is an output length followed by (first word, mask, changed values) groups.
static int validate_patch(const uint32_t* p,unsigned n,unsigned *maximum){
    if(!n||p[0]>96*1024)return 0;
    if(*maximum<p[0])*maximum=p[0];
    unsigned size=*p++,used=1;
    while(used<n){
        if(n-used<2)return 0;
        unsigned start=*p++,bits=*p++;used+=2;
        if(!bits||start>=size || 32u-__builtin_clz(bits)>size-start)return 0;
        unsigned count=__builtin_popcount(bits);
        if(count>n-used)return 0;
        p+=count;used+=count;
    }
    return 1;
}
void native_update(NativeScene* s,unsigned frame){
    const uint32_t* refs=row(&s->frames,frame);
    for(unsigned k=0;k<8;k++){
        const uint32_t* p=row(s->delta+k,refs[k+1]);
        const uint32_t* end=p+bytes(s->delta+k,refs[k+1])/4;
        s->words[k]=*p++;
        while(p<end){
            uint32_t* dest=s->state[k]+*p++;unsigned bits=*p++;
            while(bits){unsigned bit=__builtin_ctz(bits);dest[bit]=*p++;bits&=bits-1;}
        }
    }
}
void native_close(NativeScene* s){
    for(unsigned k=0;k<8;k++)free(s->state[k]);
    close_scene(&s->assets);memset(s,0,sizeof(*s));
}
int native_open(NativeScene* s,const char* name){
    file_t f=fs_open(name,O_RDONLY);
    if(f<0){printf("M1 missing pack %s\n",name);return 0;}
    unsigned size=fs_total(f),got=0;
    uint8_t* data=size>=20 && size<13*1024*1024 ? memalign(32,size):NULL;
    while(data && got<size){
        int n=fs_read(f,data+got,size-got>65536?65536:size-got);if(n<=0)break;got+=n;
    }
    fs_close(f);s->assets.storage=data;
    const unsigned* h=(const void*)data;Table root;
    if(!data||got!=size||memcmp(data,"NAT3",4)||h[1]!=3||h[3]!=size-20 ||
       crc32(data+20,size-20)!=h[4]||!table(&root,data+20,size-20)||root.n!=12)return 0;
    Table* assets[]={&s->assets.texture,&s->assets.header,&s->frames};
    unsigned ids[]={0,1,3};
    for(unsigned i=0;i<3;i++)if(!table(assets[i],row(&root,ids[i]),bytes(&root,ids[i])))return 0;
    if(!native_world_open(&s->world,row(&root,2),bytes(&root,2))||s->frames.n!=300)return 0;
    for(unsigned i=0;i<((const unsigned*)s->world.mesh)[5];i++)
        if(s->world.materials[i].header>=s->assets.header.n||s->world.materials[i].phase>=3)return 0;
    for(unsigned k=0;k<8;k++){
        Table* tab=s->delta+k;unsigned maximum=0;
        if(!table(tab,row(&root,4+k),bytes(&root,4+k)))return 0;
        for(unsigned i=0;i<tab->n;i++)if(!validate_patch(row(tab,i),bytes(tab,i)/4,&maximum))return 0;
        s->state[k]=calloc(maximum?maximum:1,4);if(!s->state[k])return 0;
    }
    for(unsigned i=0;i<300;i++){
        const uint32_t* refs=row(&s->frames,i);
        if(bytes(&s->frames,i)!=36)return 0;
        for(unsigned k=0;k<8;k++)if(refs[k+1]>=s->delta[k].n)return 0;
        const unsigned* camera=row(s->delta,refs[1]);
        if(camera[0]!=26)return 0;
    }
    return uploads(&s->assets);
}
