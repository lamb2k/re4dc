#include "native_scene.h"
#include "content.h"
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
    for(unsigned k=0;k<9;k++){
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
volatile uint32_t m1_room_serial;
volatile uint32_t m1_load_status[8];
static uint8_t* resident_pack;
static unsigned resident_capacity;
volatile uint32_t m1_texture_bytes[M1_TEXTURE_LIMIT];   /* VRAM bytes of each uploaded texture (memory map) */
/* ---- pack load (eng-e0b): no texture copy stays in main RAM ----
   NAT3 file: 20-byte header, root table (15 sections, 68 bytes), section 0 = textures, sections 1-14 = the rest.
   The texture section is streamed into VRAM one texture at a time through the start of the resident buffer;
   then the rest of the file is read into the resident buffer behind a copy of the root table whose texture
   section is empty (same offsets modulo 32 as the original layout). The CRC covers the whole file as before and
   is computed while reading. The resident buffer is sized once for the larger room's non-texture part. */
static uint32_t crc_lut[256];
static uint32_t crc_update(uint32_t c,const uint8_t* p,unsigned n){
    if(!crc_lut[1])for(unsigned i=0;i<256;i++){unsigned v=i;for(int k=0;k<8;k++)v=(v>>1)^((0-(v&1))&0xedb88320);crc_lut[i]=v;}
    c=~c;while(n--)c=(c>>8)^crc_lut[(c^*p++)&255];return ~c;
}
static int read_crc(file_t f,uint8_t* dst,unsigned n,uint32_t* crc){
    unsigned got=0;
    while(got<n){int r=fs_read(f,dst+got,n-got>65536?65536:n-got);if(r<=0)return 0;got+=r;}
    if(crc)*crc=crc_update(*crc,dst,n);
    return 1;
}
typedef struct { uint32_t head[5],root[17],size,texsize,tn,maxblob,rest; } PackInfo;
static uint32_t tex_offsets[M1_TEXTURE_LIMIT+2];
/* Header, root table and texture table of a pack (f positioned at 0); leaves f after the texture table. */
static int pack_info(file_t f,PackInfo* pi,uint32_t* crc){
    pi->size=fs_total(f);
    if(pi->size<20+68+8||!read_crc(f,(uint8_t*)pi->head,20,NULL)||memcmp(pi->head,"NAT3",4)||pi->head[1]!=4||pi->head[3]!=pi->size-20)return 0;
    if(!read_crc(f,(uint8_t*)pi->root,68,crc)||pi->root[0]!=15||pi->root[1]!=0)return 0;
    for(unsigned k=1;k<=15;k++)if(pi->root[k+1]<pi->root[k]||pi->root[k+1]%4)return 0;
    if(pi->root[16]!=pi->size-88)return 0;
    pi->texsize=pi->root[2];
    uint32_t tn;if(pi->texsize<8||!read_crc(f,(uint8_t*)&tn,4,crc)||tn>M1_TEXTURE_LIMIT||8+4*tn>pi->texsize)return 0;
    pi->tn=tn;
    if(!read_crc(f,(uint8_t*)tex_offsets,4*(tn+1),crc)||tex_offsets[0]!=0||tex_offsets[tn]!=pi->texsize-8-4*tn)return 0;
    pi->maxblob=0;
    for(unsigned i=0;i<tn;i++){if(tex_offsets[i+1]<tex_offsets[i]||tex_offsets[i+1]%4)return 0;
        unsigned b=tex_offsets[i+1]-tex_offsets[i];if(b>pi->maxblob)pi->maxblob=b;}
    pi->rest=pi->size-88-pi->texsize;
    return 1;
}
static unsigned pack_need(const char* path){
    file_t f=fs_open(path,O_RDONLY);if(f<0)return 0;
    PackInfo pi;int ok=pack_info(f,&pi,NULL);fs_close(f);if(!ok)return 0;
    unsigned need=31+68+pi.rest;return need>pi.maxblob?need:pi.maxblob;
}
static unsigned tex_palette_bits[M1_TEXTURE_LIMIT];
/* One texture blob (the format of uploads()) into VRAM. */
static int upload_one(unsigned i,const uint32_t* p,unsigned size){
    if(size<144 || memcmp(p,"RE4DCTX",7) || p[5]!=1 || p[6]>size-96)return 0;
    const uint32_t *t=p+p[6]/4+16;
    unsigned fmt=t[2],at=t[3],len=t[4];
    if(at>size || len>size-at || len==0)return 0;
    const uint8_t *data=(const uint8_t*)p+at;
    tex_palette_bits[i]=0;
    if(fmt==4){
        unsigned tail=t[5]&8?64:32;
        if(len<=tail)return 0;
        len-=tail;
        uint32_t colors[16];
        for(unsigned j=0;j<16;j++){
            if(tail==64) memcpy(colors+j,data+len+4*j,4);
            else {uint16_t c;memcpy(&c,data+len+2*j,2);
                colors[j]=((c>>12)*17u<<24)|(((c>>8)&15)*17u<<16)|(((c>>4)&15)*17u<<8)|((c&15)*17u);}
        }
        unsigned bank=0;
        while(bank<banks && memcmp(colors,palette[bank],64))bank++;
        if(bank==64)return 0;
        if(bank==banks){memcpy(palette[banks++],colors,64);for(unsigned j=0;j<16;j++)pvr_set_pal_entry(bank*16+j,colors[j]);}
        tex_palette_bits[i]=PVR_TXRFMT_4BPP_PAL(bank);
    } else if(fmt>2)return 0;
    m1_texture_bytes[i]=(len+31)&~31u;
    m1_textures[i]=pvr_mem_malloc(m1_texture_bytes[i]);
    if(!m1_textures[i])return 0;
    pvr_txr_load(data,m1_textures[i],len);
    return 1;
}
static int valid_model(const Table* tab,unsigned id,unsigned headers){
    const uint32_t* h=row(tab,id);unsigned size=bytes(tab,id);
    if(size<24||h[0]>256||h[1]>384||h[2]>4000||h[3]>4000)return 0;   /* eng-boss: 384 weight sets (ACTOR_WS_LIMIT) */
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
        if(s->words[0]!=26||s->words[1]%16||s->words[2]%18||s->words[3]%38||
           s->words[4]%5||s->words[5]<4||(s->words[5]-4)%24||s->words[6]%15||s->words[7]!=7||s->words[8]%17)return 0;
        unsigned bone=0;
        for(unsigned i=0;i<s->words[1];i+=16){
            const uint32_t* p=s->state[1]+i;
            if(p[3]==0)bone=0;
            if(p[3]!=bone++ || p[0]>2 || (p[0]==2 && (p[2]<6||p[2]>=s->models.n)))return 0;
        }
        for(unsigned i=0;i<s->words[3];i+=38){
            unsigned h=s->state[3][i+32];if(h!=~0u && h>=s->assets.header.n)return 0;
            h=s->state[3][i+33];if(h!=~0u && h>=s->assets.header.n)return 0;   /* eng-look: the glow header */
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
void native_reset(NativeScene* s){(void)s;m1_room_serial++;}
void native_close(NativeScene* s){
    for(unsigned k=0;k<9;k++)free(s->state[k]);
    native_actor_close(s);native_world_free(&s->world);native_vis_close(&s->vis);free(s->vis_data);
    s->assets.storage=NULL;close_scene(&s->assets);memset(s,0,sizeof(*s));
}
/* lane eng-draw2 (eng-load1's request R3): a room change. native_release gives back everything the renderer holds for the
   room's pack: the scene's tables and runtime (native_close: textures in video memory, palette banks, world runtime,
   visibility, actors, logic state) and the resident pack buffer itself; the next native_open sizes the buffer for the
   pack it opens. native_release_keep (the bench's ROOMKEEP control) keeps one texture in video memory. */
unsigned native_release_keep;
void native_release(NativeScene* s){
    pvr_ptr_t kept=NULL;
    if(native_release_keep){for(unsigned i=0;i<M1_TEXTURE_LIMIT;i++)if(m1_textures[i]){kept=m1_textures[i];m1_textures[i]=NULL;break;}}
    native_close(s);
    free(resident_pack);resident_pack=NULL;resident_capacity=0;
    (void)kept;   /* the control's texture stays allocated: the check must see it */
}
static size_t flip_base;static unsigned scenes_done;
void native_flip_mark(void){pvr_stats_t st;pvr_get_stats(&st);flip_base=st.frame_count;scenes_done=0;}
void native_scene_done(void){scenes_done++;}
int native_wait_shown(void){
    for(unsigned k=0;k<120;k++){pvr_stats_t st;pvr_get_stats(&st);if(st.frame_count>=flip_base+scenes_done)return 1;vid_waitvbl();}
    printf("STILL: the picture was not shown after 120 fields\n");return 0;
}
/* The bench opens two rooms by turns with the buffer kept (native_close): it reserves the larger of them once. */
static unsigned resident_reserved;
void native_reserve(const char* const* names,unsigned n){
    for(unsigned i=0;i<n;i++){unsigned v=pack_need(names[i]);if(v>resident_reserved)resident_reserved=v;}
}
#include "draw_cost.h"
int native_open(NativeScene* s,const char* name){
    dc_lab_open();   /* lane eng-draw1: the E1 lab sets (boot files DLA, DLB), read once before play */
    m1_load_status[0]=1;m1_room_serial++;
    {   /* lane eng-draw2 (R3): the resident buffer covers the pack being opened (and the bench's reservation); a pack
           larger than the buffer replaces it (nothing of the old room is in it: native_open always follows a close) */
        unsigned need=pack_need(name);
        if(!need){printf("M1 pack %s: no size (missing or malformed)\n",name);return 0;}
        if(resident_reserved>need)need=resident_reserved;
        need=(need+31)&~31u;
        if(resident_pack && resident_capacity<need){free(resident_pack);resident_pack=NULL;resident_capacity=0;}
        if(!resident_pack){
            if(need>=13*1024*1024)return 0;
            resident_pack=memalign(32,need);
            if(!resident_pack){printf("M1 pack %s: resident buffer of %u bytes refused\n",name,need);return 0;}
            resident_capacity=need;
        }
    }
    file_t f=fs_open(name,O_RDONLY);
    if(f<0){printf("M1 missing pack %s\n",name);return 0;}
    PackInfo pi;uint32_t crc=0;Table root;
    m1_load_status[0]=2;
    if(!pack_info(f,&pi,&crc)){fs_close(f);return 0;}
    unsigned size=pi.size,tn=pi.tn,pad=(20+pi.texsize)&31;   /* keeps every section's offset modulo 32 */
    m1_load_status[1]=size;m1_load_status[2]=pi.texsize;
    if(pi.maxblob>resident_capacity||pad+68+pi.rest>resident_capacity){fs_close(f);return 0;}
    m1_load_status[0]=6;
    pvr_set_pal_format(PVR_PAL_ARGB8888);
    for(unsigned i=0;i<tn;i++){
        unsigned blob=tex_offsets[i+1]-tex_offsets[i];
        if(!read_crc(f,resident_pack,blob,&crc)||!upload_one(i,(const uint32_t*)resident_pack,blob)){fs_close(f);return 0;}
    }
    uint8_t* data=resident_pack+pad;uint32_t* r=(uint32_t*)data;
    r[0]=15;r[1]=0;for(unsigned k=1;k<=15;k++)r[k+1]=pi.root[k+1]-pi.texsize;
    int ok=read_crc(f,data+68,pi.rest,&crc);
    fs_close(f);s->assets.storage=resident_pack;
    const uint32_t* h=pi.head;
    if(!ok||crc!=h[4]||!table(&root,data,68+pi.rest)||root.n!=15||bytes(&root,0))return 0;
    m1_load_status[0]=3;
    if(bytes(&root,14)<8)return 0;
    memcpy(&s->sky_top,row(&root,14),8);
    if(!table(&s->models,row(&root,13),bytes(&root,13))||s->models.n<6)return 0;
    if(!content_variants_open((const uint8_t*)row(&root,14)+8,bytes(&root,14)-8,s->models.n))return 0;   /* eng-look */
    s->assets.texture=(Table){tn,NULL,NULL};
    Table* assets[]={&s->assets.header,&s->frames};
    unsigned ids[]={1,3};
    for(unsigned i=0;i<2;i++)if(!table(assets[i],row(&root,ids[i]),bytes(&root,ids[i])))return 0;
    if(!native_world_open(&s->world,row(&root,2),bytes(&root,2))||s->frames.n!=300)return 0;
    if(!native_world_runtime(&s->world))return 0;
    for(unsigned i=0;i<((const unsigned*)s->world.mesh)[5];i++)
        if(s->world.materials[i].header>=s->assets.header.n||s->world.materials[i].phase>=3)return 0;
    m1_load_status[0]=4;
    for(unsigned j=0;j<s->models.n;j++)if(!valid_model(&s->models,j,s->assets.header.n))return 0;
    unsigned logic_bytes=0;
    for(unsigned k=0;k<9;k++){
        Table* tab=s->delta+k;unsigned maximum=0;
        if(!table(tab,row(&root,4+k),bytes(&root,4+k)))return 0;
        for(unsigned i=0;i<tab->n;i++)if(!validate_patch(row(tab,i),bytes(tab,i)/4,&maximum))return 0;
        logic_bytes+=maximum*4;s->state[k]=calloc(maximum?maximum:1,4);if(!s->state[k])return 0;
    }
    for(unsigned i=0;i<300;i++){
        const uint32_t* refs=row(&s->frames,i);
        if(bytes(&s->frames,i)!=40)return 0;
        for(unsigned k=0;k<9;k++)if(refs[k+1]>=s->delta[k].n)return 0;
        const unsigned* camera=row(s->delta,refs[1]);
        if(camera[0]!=26)return 0;
    }
    m1_load_status[0]=5;if(!valid_inputs(s))return 0;
    m1_load_status[0]=6;
    for(unsigned i=0;i<s->assets.header.n;i++){   /* bind each material header to its texture in VRAM */
        if(bytes(&s->assets.header,i)!=36)return 0;
        uint32_t *hd=row(&s->assets.header,i);
        if(hd[0]>=tn)return 0;
        hd[4]|=((uintptr_t)m1_textures[hd[0]]&0x7fffff)>>3 | tex_palette_bits[hd[0]];
    }
    m1_load_status[0]=8;if(!native_actor_open(s))return 0;
    m1_load_status[0]=9;
    {   /* baked visibility: <ROOM>.VIS beside the pack, unless /cd/NOVIS (the full-set arm of the pixel check) */
        char vis[32];unsigned n=strlen(name);
        if(n<sizeof(vis)&&n>4){memcpy(vis,name,n-3);memcpy(vis+n-3,"VIS",4);}else vis[0]=0;
        file_t nv=fs_open("/cd/NOVIS",O_RDONLY);
        if(nv>=0){fs_close(nv);vis[0]=0;}
        file_t vf=vis[0]?fs_open(vis,O_RDONLY):-1;
        if(vf>=0){
            unsigned vs=fs_total(vf);s->vis_data=vs?memalign(32,vs):NULL;
            int got=s->vis_data?fs_read(vf,s->vis_data,vs):-1;fs_close(vf);
            if(got!=(int)vs||!native_vis_open(&s->vis,s->vis_data,vs,&s->world))return 0;
            s->world.vis=&s->vis;m1_ram[7]=vs;
        }
    }
    m1_load_status[0]=7;
    struct mallinfo heap=mallinfo();
    m1_ram[0]=size-pi.texsize;m1_ram[1]=logic_bytes;m1_ram[2]=(uintptr_t)end-0x8c010000;
    m1_ram[3]=heap.uordblks;m1_ram[4]=heap.fordblks;m1_ram[5]=pvr_mem_available();m1_ram[6]=resident_capacity;
    return 1;
}
