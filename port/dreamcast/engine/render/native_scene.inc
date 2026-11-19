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
__attribute__((optimize("O2"))) void native_update(NativeScene* s,unsigned frame){
    const uint32_t* refs=row(&s->frames,frame);
    for(unsigned k=0;k<8;k++){
        const uint32_t* p=row(s->delta+k,refs[k+1]);
        const uint32_t* end=p+bytes(s->delta+k,refs[k+1])/4;
        unsigned next=*p++;
        unsigned used=frame?s->words[k]:0;
        if(next>used)memset(s->state[k]+used,0,4*(next-used));
        s->words[k]=next;
        while(p<end){
            uint32_t* dest=s->state[k]+*p++;unsigned bits=*p++;
            for(;bits;bits>>=1,dest++)if(bits&1)*dest=*p++;
        }
    }
}
volatile uint32_t m1_ram[8];
volatile uint32_t m1_load_status[8];
static uint8_t* resident_pack;
static unsigned resident_capacity;
static unsigned file_size(const char* path){
    file_t f=fs_open(path,O_RDONLY);if(f<0)return 0;
    unsigned bytes=fs_total(f);fs_close(f);return bytes;
}
static int valid_model(const Table* tab,unsigned id,unsigned headers){
    const uint32_t* h=row(tab,id);unsigned size=bytes(tab,id);
    if(size<24||h[0]>256||h[1]>256||h[2]>4000||h[3]>4000)return 0;
    uint64_t static_bytes=24+(uint64_t)48*h[0]+16*h[1]+8*(h[2]+h[3])+16*(uint64_t)h[4];
    if(static_bytes+h[5]!=size)return 0;
    const uint8_t* weights=(const uint8_t*)(h+6)+48*h[0];
    for(unsigned i=0;i<h[1];i++){
        const uint8_t* w=weights+16*i;
        if(w[3]>3)return 0;
        for(unsigned j=0;j<w[3];j++)if(w[j]>=h[0])return 0;
    }
    const uint16_t* vec=(const void*)(weights+16*h[1]);
    for(unsigned i=0;i<h[2]+h[3];i++)if(vec[4*i+3]>=h[1])return 0;
    const unsigned* parts=(const void*)(vec+4*(h[2]+h[3]));
    const uint8_t* strips=(const void*)(parts+4*h[4]);
    for(unsigned i=0;i<h[4];i++){
        const unsigned* r=parts+4*i;
        if(r[1]>=headers ||r[2]>h[5]||r[3]>h[5]-r[2])return 0;
        const uint8_t* p=strips+r[2],*end=p+r[3];
        while(p<end){if(end-p<4)return 0;unsigned n=*(const unsigned*)p;p+=4;
            if(n<3 || n>(end-p)/8)return 0;
            const uint16_t* c=(const void*)p;
            for(unsigned j=0;j<n;j++,c+=4)if(c[0]>=h[2]||c[1]>=h[3])return 0;
            p+=8*n;
        }
    }
    return 1;
}
static int valid_inputs(NativeScene* s){
    for(unsigned frame=0;frame<300;frame++){
        native_update(s,frame);
        if(s->words[0]!=26||s->words[1]%16||s->words[2]%13||s->words[3]%37||
           s->words[4]%5||s->words[5]<4||(s->words[5]-4)%24||s->words[6]%15||s->words[7]!=7)return 0;
        unsigned bone=0;
        for(unsigned i=0;i<s->words[1];i+=16){
            const uint32_t* p=s->state[1]+i;
            if(p[3]==0)bone=0;
            if(p[3]!=bone++ || p[0]>2 || (p[0]==2 && (p[2]<6||p[2]>=s->models.n)))return 0;
        }
        for(unsigned i=0;i<s->words[3];i+=37){
            unsigned h=s->state[3][i+32];if(h!=~0u && h>=s->assets.header.n)return 0;
        }
        for(unsigned i=4;i<s->words[5];i+=24){
            unsigned h=s->state[5][i+4];if(h!=~0u && h>=s->assets.header.n)return 0;
        }
        for(unsigned i=0;i<s->words[6];i+=15){
            const uint32_t* t=s->state[6]+i;
            if(t[7]!=~0u && (t[7]>=s->assets.header.n || !t[11] || t[9]<t[11] || !t[10]))return 0;
        }
    }
    return 1;
}
void native_close(NativeScene* s){
    for(unsigned k=0;k<8;k++)free(s->state[k]);
    native_actor_close(s);native_world_free(&s->world);
    s->assets.storage=NULL;close_scene(&s->assets);memset(s,0,sizeof(*s));
}
int native_open(NativeScene* s,const char* name){
    m1_load_status[0]=1;
    if(!resident_pack){
        unsigned a=file_size("/cd/CROSS.PAK"),b=file_size("/cd/FARM.PAK");
        if(!a||!b)return 0;
        resident_capacity=a>b?a:b;
        if(resident_capacity>=13*1024*1024)return 0;
        resident_pack=memalign(32,resident_capacity);
        if(!resident_pack)return 0;
    }
    file_t f=fs_open(name,O_RDONLY);
    if(f<0){printf("M1 missing pack %s\n",name);return 0;}
    unsigned size=fs_total(f),got=0;
    uint8_t* data=size>=20 && size<=resident_capacity ? resident_pack:NULL;
    while(data && got<size){
        int n=fs_read(f,data+got,size-got>65536?65536:size-got);if(n<=0)break;got+=n;
    }
    fs_close(f);s->assets.storage=data;
    const unsigned* h=(const void*)data;Table root;
    m1_load_status[0]=2;m1_load_status[1]=size;m1_load_status[2]=got;
    if(!data||got!=size||memcmp(data,"NAT3",4)||h[1]!=3||h[3]!=size-20 ||
       crc32(data+20,size-20)!=h[4]||!table(&root,data+20,size-20)||root.n!=14)return 0;
    m1_load_status[0]=3;
    if(bytes(&root,13)!=8)return 0;
    memcpy(&s->sky_top,row(&root,13),8);
    if(!table(&s->models,row(&root,12),bytes(&root,12))||s->models.n<6)return 0;
    Table* assets[]={&s->assets.texture,&s->assets.header,&s->frames};
    unsigned ids[]={0,1,3};
    for(unsigned i=0;i<3;i++)if(!table(assets[i],row(&root,ids[i]),bytes(&root,ids[i])))return 0;
    if(!native_world_open(&s->world,row(&root,2),bytes(&root,2))||s->frames.n!=300)return 0;
    if(!native_world_runtime(&s->world))return 0;
    for(unsigned i=0;i<((const unsigned*)s->world.mesh)[5];i++)
        if(s->world.materials[i].header>=s->assets.header.n||s->world.materials[i].phase>=3)return 0;
    m1_load_status[0]=4;
    for(unsigned j=0;j<s->models.n;j++)if(!valid_model(&s->models,j,s->assets.header.n))return 0;
    unsigned logic_bytes=0;
    for(unsigned k=0;k<8;k++){
        Table* tab=s->delta+k;unsigned maximum=0;
        if(!table(tab,row(&root,4+k),bytes(&root,4+k)))return 0;
        for(unsigned i=0;i<tab->n;i++)if(!validate_patch(row(tab,i),bytes(tab,i)/4,&maximum))return 0;
        logic_bytes+=maximum*4;s->state[k]=calloc(maximum?maximum:1,4);if(!s->state[k])return 0;
    }
    for(unsigned i=0;i<300;i++){
        const uint32_t* refs=row(&s->frames,i);
        if(bytes(&s->frames,i)!=36)return 0;
        for(unsigned k=0;k<8;k++)if(refs[k+1]>=s->delta[k].n)return 0;
        const unsigned* camera=row(s->delta,refs[1]);
        if(camera[0]!=26)return 0;
    }
    m1_load_status[0]=5;if(!valid_inputs(s))return 0;
    m1_load_status[0]=6;if(!uploads(&s->assets))return 0;
    m1_load_status[0]=8;if(!native_actor_open(s))return 0;
    m1_load_status[0]=7;
    struct mallinfo heap=mallinfo();
    m1_ram[0]=size;m1_ram[1]=logic_bytes;m1_ram[2]=(uintptr_t)end-0x8c010000;
    m1_ram[3]=heap.uordblks;m1_ram[4]=heap.fordblks;m1_ram[5]=pvr_mem_available();m1_ram[6]=resident_capacity;
    return 1;
}
