#pragma once
/* RAM and VRAM map of the bench (eng-e0b step 5). Included once, by main.c.
   - Every malloc/calloc/memalign/realloc/free of the program goes through a wrapper (-Wl,--wrap) that keeps the
     live blocks with the load stage that made them (m1_load_status[0] while a room loads, else 0 = system).
   - The kernel stack (64 KB under arch_stack_16m) is painted at boot; the high-water mark is the deepest word
     that changed, and the lowest 1 KB is a guard band that must stay painted.
   - memmap_sample(room), after the room's load (the low point: nothing is allocated while pictures run), writes
     m1_mem[room]: the static image, every live block sorted by address with an overlap check, the heap top, the
     free gap to the stack, the stack's high water, and the VRAM map from the PVR's own registers (vertex buffer,
     object pointer buffer, tile matrix, frame buffers, both sets) and the texture allocations. Serial: "MEM ...".
   - memmap_check() after every window: the guard band and the heap invariants; a break stops the run (stage 93). */
#include <malloc.h>
#include <unistd.h>
#include <dc/pvr.h>
extern volatile uint32_t m1_load_status[8];
extern volatile uint32_t m1_state[8];
extern volatile uint32_t m1_texture_bytes[];
extern pvr_ptr_t m1_textures[];
extern uintptr_t arch_stack_16m;

void* __real_malloc(size_t);void* __real_calloc(size_t,size_t);void* __real_memalign(size_t,size_t);
void* __real_realloc(void*,size_t);void __real_free(void*);
#define MM_BLOCKS 1024
typedef struct { uintptr_t lo,hi; uint32_t tag; } MmBlock;
static MmBlock mm_live[MM_BLOCKS];static unsigned mm_n,mm_lost;
static uint32_t mm_tag(void){return m1_state[5]==2?m1_load_status[0]:0;}
static void mm_add(void* p,size_t n){
    if(!p)return;
    if(mm_n<MM_BLOCKS)mm_live[mm_n++]=(MmBlock){(uintptr_t)p,(uintptr_t)p+n,mm_tag()};else mm_lost++;
}
static void mm_del(void* p){
    if(!p)return;
    for(unsigned i=0;i<mm_n;i++)if(mm_live[i].lo==(uintptr_t)p){mm_live[i]=mm_live[--mm_n];return;}
}
void* __wrap_malloc(size_t n){void* p=__real_malloc(n);mm_add(p,n);return p;}
void* __wrap_calloc(size_t a,size_t b){void* p=__real_calloc(a,b);mm_add(p,a*b);return p;}
void* __wrap_memalign(size_t a,size_t n){void* p=__real_memalign(a,n);mm_add(p,n);return p;}
void* __wrap_realloc(void* q,size_t n){void* p=__real_realloc(q,n);if(p||!n){mm_del(q);mm_add(p,n);}return p;}
void __wrap_free(void* p){mm_del(p);__real_free(p);}

#define STACK_PAINT 0x5a5aa5a5u
static uintptr_t stack_lo,stack_hi;
static void memmap_boot(void){
    stack_hi=arch_stack_16m;stack_lo=stack_hi-64*1024;
    uintptr_t sp;__asm__ volatile("mov r15,%0":"=r"(sp));
    for(uintptr_t a=stack_lo;a+512<sp;a+=4)*(volatile uint32_t*)a=STACK_PAINT;
}
static unsigned stack_high_water(void){
    uintptr_t a=stack_lo;while(a<stack_hi && *(volatile uint32_t*)a==STACK_PAINT)a+=4;
    return stack_hi-a;
}
static int stack_guard_ok(void){
    for(uintptr_t a=stack_lo;a<stack_lo+1024;a+=4)if(*(volatile uint32_t*)a!=STACK_PAINT)return 0;
    return 1;
}
/* per room: 0 image lo, 1 image hi (_end), 2 heap blocks, 3 heap first, 4 heap last end, 5 sbrk top, 6 overlaps,
   7 bytes by tag 0 system, 8 tag 1 pack, 9 tag 3 world runtime, 10 tag 4 logic, 11 tag 8 actors, 12 tag 9 vis,
   13 other tags, 14 free to stack, 15 stack lo, 16 stack hi, 17 stack high water, 18 guard ok, 19 mallinfo arena,
   20 uordblks, 21 fordblks, 22 lost entries,
   VRAM (texture/64-bit addressing, bytes): 23 vertex set0 lo, 24 hi, 25 vertex set1 lo, 26 hi, 27 OPB set0 lo, 28 hi,
   29 OPB set1 lo, 30 hi, 31 tile set0, 32 tile set1, 33 fb0, 34 fb1, 35 PVR buffers end (64-bit), 36 textures lo,
   37 textures hi, 38 texture bytes, 39 textures, 40 pvr_mem_available, 41 VRAM overlaps, 42 stage (OCRAM) lo, 43 hi */
volatile uint32_t m1_mem[2][48];
static int blk_cmp(const void* a,const void* b){uintptr_t x=((const MmBlock*)a)->lo,y=((const MmBlock*)b)->lo;return (x>y)-(x<y);}
static uint32_t to64(uint32_t a32){return ((a32&0x3ffffc)<<1)|(a32&3);}   /* 32-bit-area offset to 64-bit-area offset */
static void memmap_sample(unsigned room){
    volatile uint32_t* m=m1_mem[room];
    static MmBlock b[MM_BLOCKS];unsigned n=mm_n;memcpy(b,mm_live,n*sizeof(MmBlock));
    qsort(b,n,sizeof(MmBlock),blk_cmp);
    unsigned overlaps=0;uint32_t tag_bytes[7]={0};
    for(unsigned i=0;i<n;i++){
        if(i && b[i].lo<b[i-1].hi)overlaps++;
        if(b[i].lo<(uintptr_t)&end)overlaps++;
        unsigned t=b[i].tag,k=t==0?0:t==1?1:t==3?2:t==4?3:t==8?4:t==9?5:6;tag_bytes[k]+=b[i].hi-b[i].lo;
    }
    struct mallinfo mi=mallinfo();
    uintptr_t top=(uintptr_t)sbrk(0);
    if(n && b[n-1].hi>top)overlaps++;
    if(top>stack_lo)overlaps++;
    uint32_t v[48]={0x8c010000,(uint32_t)(uintptr_t)&end,n,n?b[0].lo:0,n?b[n-1].hi:0,top,overlaps,
                    tag_bytes[0],tag_bytes[1],tag_bytes[2],tag_bytes[3],tag_bytes[4],tag_bytes[5],tag_bytes[6],
                    stack_lo-top,stack_lo,stack_hi,stack_high_water(),stack_guard_ok(),mi.arena,mi.uordblks,mi.fordblks,mm_lost};
    /* VRAM: both buffer sets from the PVR registers (two pictures), textures from the allocations */
    uint32_t vb[2][2]={{0}},ob[2][2]={{0}},tm[2]={0},fb[2]={0};
    for(unsigned k=0;k<4;k++){
        pvr_wait_ready();pvr_scene_begin();pvr_scene_finish();pvr_wait_render_done();
        unsigned set=(PVR_GET(PVR_TA_VERTBUF_START)>=0x400000),rset=(PVR_GET(PVR_RENDER_ADDR)>=0x400000);
        vb[set][0]=PVR_GET(PVR_TA_VERTBUF_START);vb[set][1]=PVR_GET(PVR_TA_VERTBUF_END);
        ob[set][0]=PVR_GET(PVR_TA_OPB_START);ob[set][1]=PVR_GET(PVR_TA_OPB_END);
        uint32_t t=PVR_GET(PVR_ISP_TILEMAT_ADDR);tm[t>=0x400000]=t;fb[rset]=PVR_GET(PVR_RENDER_ADDR);
    }
    uint32_t pvr_end=0;
    for(unsigned s=0;s<2;s++){uint32_t e=(fb[s]&0x3fffff)+640*480*2;e=to64(e);if(e>pvr_end)pvr_end=e;}
    uint32_t tlo=~0u,thi=0,tbytes=0,tcount=0;
    for(unsigned i=0;i<M1_TEXTURE_LIMIT;i++)if(m1_textures[i]){uint32_t a=(uintptr_t)m1_textures[i]&0x7fffff;
        if(a<tlo)tlo=a;if(a+m1_texture_bytes[i]>thi)thi=a+m1_texture_bytes[i];tbytes+=m1_texture_bytes[i];tcount++;}
    uint32_t vo=0;
    if(tcount && tlo<pvr_end)vo++;
    if(thi>8*1024*1024)vo++;
    for(unsigned s=0;s<2;s++){if(!(vb[s][0]<vb[s][1]&&vb[s][1]<=ob[s][0]&&ob[s][1]<=tm[s]&&tm[s]<fb[s]))vo++;}
    uint32_t vv[21]={vb[0][0],vb[0][1],vb[1][0],vb[1][1],ob[0][0],ob[0][1],ob[1][0],ob[1][1],tm[0],tm[1],fb[0],fb[1],
                     pvr_end,tcount?tlo:0,thi,tbytes,tcount,pvr_mem_available(),vo,0x7c001000,0x7c003000};   /* arm a's stage: operand-cache RAM, not main RAM */
    for(unsigned k=0;k<21;k++)v[23+k]=vv[k];
    for(unsigned k=0;k<48;k++)m[k]=v[k];
    printf("MEM %s image %08lx-%08lx heap blocks %u %08lx-%08lx sbrk %08lx overlaps %lu | system %lu pack %lu world %lu logic %lu actors %lu vis %lu other %lu | "
           "free to stack %lu stack %08lx-%08lx high water %lu guard %s | mallinfo arena %lu used %lu free %lu\n",
           room?"FARM":"CROSS",(unsigned long)v[0],(unsigned long)v[1],n,(unsigned long)v[3],(unsigned long)v[4],(unsigned long)top,(unsigned long)overlaps,
           (unsigned long)tag_bytes[0],(unsigned long)tag_bytes[1],(unsigned long)tag_bytes[2],(unsigned long)tag_bytes[3],(unsigned long)tag_bytes[4],
           (unsigned long)tag_bytes[5],(unsigned long)tag_bytes[6],(unsigned long)(stack_lo-top),(unsigned long)stack_lo,(unsigned long)stack_hi,
           (unsigned long)v[17],v[18]?"intact":"BROKEN",(unsigned long)mi.arena,(unsigned long)mi.uordblks,(unsigned long)mi.fordblks);
    printf("VRAM %s vertex %06lx-%06lx %06lx-%06lx opb %06lx-%06lx %06lx-%06lx tiles %06lx %06lx frame %06lx %06lx (32-bit area offsets); "
           "PVR buffers end %06lx, textures %06lx-%06lx %lu bytes in %lu, available %lu (64-bit area); overlaps %lu\n",
           room?"FARM":"CROSS",(unsigned long)vb[0][0],(unsigned long)vb[0][1],(unsigned long)vb[1][0],(unsigned long)vb[1][1],
           (unsigned long)ob[0][0],(unsigned long)ob[0][1],(unsigned long)ob[1][0],(unsigned long)ob[1][1],(unsigned long)tm[0],(unsigned long)tm[1],
           (unsigned long)fb[0],(unsigned long)fb[1],(unsigned long)pvr_end,(unsigned long)vv[13],(unsigned long)thi,(unsigned long)tbytes,
           (unsigned long)tcount,(unsigned long)vv[17],(unsigned long)vo);
    for(unsigned i=0;i<n;i++)printf("MEMBLK %s %08lx %lu tag %lu\n",room?"FARM":"CROSS",(unsigned long)b[i].lo,(unsigned long)(b[i].hi-b[i].lo),(unsigned long)b[i].tag);
}
static void memmap_check(void){
    if(!stack_guard_ok()){printf("STACK GUARD BROKEN\n");m1_state[5]=93;for(;;)thd_sleep(100);}
}
