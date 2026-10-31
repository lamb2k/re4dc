// game/main_mem: heap management over OSAlloc (D:/Bio4/Prog/main_mem.cpp). The main RAM map is
// fixed (SystemMemMap: ELF, DVD, sound, FIFO, XFB, core/option/player/weapon archives, then the
// heap up to 0x817F4000). Thirteen logical heaps (Heap[], MEM_HEAP_NUM) live in that range: 0
// system, 1 game, 2 stage, 3 DLL, 4 room ... created with MemCreateHeap / carved off the end of
// another with MemReplaceHeap; heaps can be suspended (descriptor backed up) and resumed.
// mem_alloc tags every block with "MAD" + file(line) for MemCheckUsedHeap; Debug_alloc serves
// the tools from the current debug heap. operator new/delete route here.
#if defined(RE4DC_GAME) && !defined(__PPC__)
#include "actor_lifetime.h"
#endif
#include "types.h"
#include "global.h"
#include "main_mem.h"
#include "db_log.h"
#if defined(RE4DC_MOTION_CAPACITY) && RE4DC_MOTION_CAPACITY
#include "native_motion.h"
#endif
#include "joy.h"
#include "eprintf.h"
#include "file.h"
#include "libgpu.h"
#if !defined(__PPC__)
#include "re4dc_platform.h"
#if (defined(RE4DC_MOVIE_WORLD_ARENA) && RE4DC_MOVIE_WORLD_ARENA) || (defined(RE4DC_CABIN_SOURCE) && RE4DC_CABIN_SOURCE)
#include "movie_world_arena.h"
#endif
#endif

#if defined(RE4DC_WORLD_VALID_MEMO31) && RE4DC_WORLD_VALID_MEMO31
// WORLD_VALID_MEMO31 (k45fix31.mk): any heap create / destroy / suspend / resume moves the world validity epoch.
extern "C" void re4dc_world_heap_changed(void);
#define RE4DC_WORLD_HEAP_CHANGED() re4dc_world_heap_changed()
#else
#define RE4DC_WORLD_HEAP_CHANGED() ((void)0)
#endif
extern "C" {
void OSReport(const char* fmt, ...);
void* OSGetArenaLo();
void* OSGetArenaHi();
void OSSetArenaLo(void* lo);
void OSSetArenaHi(void* hi);
void* OSInitAlloc(void* lo, void* hi, int maxHeaps);
int OSCreateHeap(void* start, void* end);
void OSDestroyHeap(int heap);
void OSSetCurrentHeap(int heap);
void* OSAllocFromHeap(int heap, u32 size);
void OSFreeToHeap(int heap, void* p);
s32 OSCheckHeap(int heap);
void OSSetSaveRegion(void* start, void* end);
#if defined(RE4DC_FAR_SHELL) && RE4DC_FAR_SHELL
int re4dc_far_shell_shortfall(unsigned need, const char* site);   // port platform/far_shell.inc
#endif
extern int __OSCurrHeap;
int strcmp(const char* a, const char* b);
char* strcpy(char* dst, const char* src);
char* strrchr(const char* s, int c);
int sprintf(char* buf, const char* fmt, ...);
void* memset(void* dst, int c, unsigned int n);
#if defined(RE4DC_GAME) && !defined(__PPC__) && defined(RE4DC_SS11_PRELOAD) && RE4DC_SS11_PRELOAD
void re4dc_ui_room_preload_again(void);  // native_ui.cpp (SS11_PRELOAD)
#endif
}

extern char* pRK;

// Fixed memory map of the debug build.
struct SystemMemMap {
    u32 x0;         // 0x00
    u32 elf_end;    // 0x04
    u32 dvd;        // 0x08
    u32 sound;      // 0x0C
    u32 fifo;       // 0x10
    u32 xfb;        // 0x14
    u32 core;       // 0x18
    u32 option;     // 0x1C
    u32 player;     // 0x20
    u32 weapon;     // 0x24  start of the main heap
    u32 heap_end;   // 0x28
    u32 arena_lo;   // 0x2C  OSGetArenaLo() at boot
    u32 usb;        // 0x30
    u32 debug;      // 0x34
};

#define HALT()                                                    \
    {                                                             \
        OSReport("HALT %s(%d)\n", __FILE__, __LINE__);            \
        RE4DC_HALT_STORE();                                       \
    }


MemHeap Heap[MEM_HEAP_NUM];
static SystemMemMap SysMem;
OSHeapDescriptor heap_backup[MEM_HEAP_NUM];  // OSAlloc descriptors of suspended heaps

OSHeapCell* cell_main = NULL;
OSHeapCell* cell_game = NULL;
static OSHeapCell* cell_stage = NULL;
OSHeapCell* cell_dll = NULL;
static u8 Dalloc_flg = 0;
u32 _epy_base = 40;

static OSHeapDescriptor* HeapHead;
u32 arenaLo;
u32 arenaHi;
u8 CurrentHeap;
static u8 CurrentDbgHeap;
void* pMemTile;
static u32 _epy;

#if defined(RE4DC_GAME) && !defined(__PPC__) && (RE4DC_PS2_WORLD_SOURCE_OWNER || RE4DC_PS2_WORLD_R11F_OWNER)
#include "ps2_source_world.h"
#include "source_world_retained.inc"
#endif

// Zeroed allocation from the current heap.
void* operator new(unsigned int size)
{
    return mem_calloc(size, "operator new", 0, 1, MEM_HEAP_CURRENT);
}

// Zeroed array allocation from the current heap.
void* operator new[](unsigned int size)
{
    return mem_calloc(size, "operator new", 0, 1, MEM_HEAP_CURRENT);
}

// Frees to the current heap.
void operator delete(void* p)
{
    Mem_free(p);
}

// Frees to the current heap.
void operator delete[](void* p)
{
    Mem_free(p);
}

// Boot: fixes the memory map, inits OSAlloc over [weapon archive end, heap_end/arena hi), creates
// heap 0 over the whole range and allocates the reset-keep block pRK (a 0x40-byte save region
// tagged "_reset_keep_" that survives soft resets).
void SystemMemInit()
{
#if defined(__PPC__)
    SysMem.heap_end = 0x817F4000;
    SysMem.elf_end = 0x80350000;
    SysMem.dvd = 0x80370000;
    SysMem.sound = 0x803F0000;
    SysMem.fifo = 0x80460000;
    SysMem.xfb = 0x80578000;
    SysMem.core = 0x807AC000;
    SysMem.option = 0x807EC000;
    SysMem.player = 0x80904000;
    SysMem.weapon = 0x80974000;
    SysMem.usb = 0x81800000;
    SysMem.debug = 0x8181FB00;
#else
    // The platform carves the same regions out of its arena (platform/mem.cpp).
    SysMem.heap_end = re4dc_mem.heap_end;
    SysMem.elf_end = re4dc_mem.arena_lo;
    SysMem.dvd = re4dc_mem.dvd;
    SysMem.sound = re4dc_mem.sound;
    SysMem.fifo = (u32) re4dc_gx_fifo();
    SysMem.xfb = (u32) re4dc_frame_buffer(0);
    SysMem.core = re4dc_mem.core;
    SysMem.option = re4dc_mem.option;
    SysMem.player = re4dc_mem.player;
    SysMem.weapon = re4dc_mem.weapon;
    SysMem.usb = re4dc_mem.arena_hi;
    SysMem.debug = re4dc_mem.arena_hi;
#endif
    SysMem.arena_lo = (u32) OSGetArenaLo();
#if defined(__PPC__)
    if (SysMem.arena_lo > 0x8034FFFF) {
#else
    if (SysMem.arena_lo > re4dc_mem.dvd) {
#endif
        OSReport("ELF size overflow\n");
#line 100 "D:/Bio4/Prog/main_mem.cpp"
        HALT();
    }
#if defined(__PPC__)
    arenaLo = SysMem.weapon;
#else
    arenaLo = re4dc_mem.heap;  // SysMem.weapon + 0x70000 on the GameCube
#endif
    arenaHi = (u32) OSGetArenaHi();
    if (SysMem.heap_end > arenaHi) {
        arenaHi = SysMem.heap_end;
    }
    arenaLo = (arenaLo + 0x1F) & ~0x1F;
    arenaHi &= ~0x1F;
    HeapHead = (OSHeapDescriptor*) arenaLo;
#if defined(RE4DC_GAME) && !defined(__PPC__) && (RE4DC_PS2_WORLD_SOURCE_OWNER || RE4DC_PS2_WORLD_R11F_OWNER)
    sourceWorldRetainedReset();
#endif
    arenaLo = (u32) OSInitAlloc((void*) arenaLo, (void*) arenaHi, MEM_HEAP_NUM);
    OSSetArenaLo((void*) arenaLo);
    OSSetArenaHi((void*) arenaHi);
    memInitHeapTbl();
    MemCreateHeap(0, arenaLo, SysMem.heap_end);
    MemSetCurrentHeap(0);
    pMemTile = NULL;
#line 145
    pRK = (char*) MEM_ALLOC(0x40, 1, MEM_HEAP_CURRENT);
    OSSetSaveRegion(pRK, pRK + 0x40);
    if (strcmp(pRK, "_reset_keep_") != 0) {
        memclr_asm(pRK, 0x40);
        strcpy(pRK, "_reset_keep_");
        OSReport("RESET_KEEP_WORK memory clear...\n");
    }
}

// Clears the 13 heap slots and the suspend backups.
void memInitHeapTbl()
{
#if defined(RE4DC_GAME) && !defined(__PPC__) && (RE4DC_PS2_WORLD_SOURCE_OWNER || RE4DC_PS2_WORLD_R11F_OWNER)
    sourceWorldRetainedReset();
#endif
#if defined(RE4DC_GAME) && !defined(__PPC__) && RE4DC_ACTOR_TRANSACTION
    re4dc_actor_forget_all();
#endif

    int i;

    for (i = 0; i < MEM_HEAP_NUM; i++) {
        Heap[i].handle = -1;
        Heap[i].start = 0;
        Heap[i].end = 0;
        Heap[i].status = 0;
    }
    RE4DC_WORLD_HEAP_CHANGED();
    memclr_asm(heap_backup, sizeof(heap_backup));
}

// Suspends heap no: saves its OSAlloc descriptor and empties the live one (allocations from it fail).
void MemSuspendHeap(int no)
{
#if defined(RE4DC_GAME) && !defined(__PPC__) && (RE4DC_PS2_WORLD_SOURCE_OWNER || RE4DC_PS2_WORLD_R11F_OWNER)
    sourceWorldRetainedSuspend(no);
#endif
    int h = Heap[no].handle;

    if (memGetHeapSattus(no) == 0 && h >= 0) {
#if RE4DC_CABIN_SOURCE
        // Suspend/resume preserves live allocations. It cannot silently retire
        // a parked current EVD merely because that EVD has no active readers.
        if(!re4dc_cabin_carriers_suspendable((void*)Heap[no].start,Heap[no].end-Heap[no].start) ||
           !re4dc_movie_world_before_heap_change((void*)Heap[no].start,Heap[no].end-Heap[no].start)){
            re4dc_missing("cabin owner before heap suspension");return;
        }
        // The movie fence may have yielded after the first check.
        if(!re4dc_cabin_carriers_suspendable((void*)Heap[no].start,Heap[no].end-Heap[no].start)){
            re4dc_missing("cabin revalidation before heap suspension");return;
        }
#endif
        heap_backup[h] = HeapHead[h];
        HeapHead[h].free = NULL;
        HeapHead[h].allocated = NULL;
        Heap[no].status = 1;
        RE4DC_WORLD_HEAP_CHANGED();
    }
}

// Resumes a suspended heap from its backup.
void MemSignalHeap(int no)
{
    int h = Heap[no].handle;

    if (memGetHeapSattus(no) == 1 && h >= 0) {
#if defined(RE4DC_GAME) && !defined(__PPC__) && (RE4DC_PS2_WORLD_SOURCE_OWNER || RE4DC_PS2_WORLD_R11F_OWNER)
        sourceWorldRetainedRestore(no);
#endif
        OSHeapDescriptor* hh = HeapHead;
        OSHeapDescriptor* bk = heap_backup;

        *(OSHeapDescriptor*) (h * sizeof(OSHeapDescriptor) + (u32) hh) =
            *(OSHeapDescriptor*) (h * sizeof(OSHeapDescriptor) + (u32) bk);
        Heap[no].status = 0;
        RE4DC_WORLD_HEAP_CHANGED();
    }
}

// 1 when the heap is suspended.
int memGetHeapSattus(int no)
{
    return Heap[no].status;
}

// 1 when the heap is not suspended.
int memCheckHeapActive(int no)
{
    return memGetHeapSattus(no) == 0;
}

// Makes heap no the current allocation heap (and the debug heap); 0 when it is missing/suspended.
int MemSetCurrentHeap(int no)
{
    if (memCheckHeapActive(no) && Heap[no].handle >= 0) {
        CurrentHeap = no;
        OSSetCurrentHeap(Heap[CurrentHeap].handle);
        CurrentDbgHeap = CurrentHeap;
        return 1;
    }
    return 0;
}

// Points the debug heap at the current heap (no must be active).
int MemSetCurrentDbgHeap(int no)
{
    if (memCheckHeapActive(no) && Heap[no].handle >= 0) {
        CurrentDbgHeap = CurrentHeap;
        return 1;
    }
    return 0;
}

// Current heap number.
u8 MemGetCurrentHeap()
{
    return CurrentHeap;
}

// Current debug heap number.
u8 MemGetCurrentDbgHeap()
{
    return CurrentDbgHeap;
}

// Start address of heap no.
u32 MemGetHeapStartAddr(int no)
{
    return Heap[no].start;
}

// End address of heap no.
u32 MemGetHeapEndAddr(int no)
{
    return Heap[no].end;
}

// Highest address in use by heap no (end of its last allocated cell, or the free list start when
// nothing is allocated); 0 when inactive.
// OPEN (-4): the original places `li r3,0` between the compare and the branch and reloads
// d->allocated for the loop init after the if/else join (ours forwards it); if/else, ternary,
// `end = 0` first and HeapHead[h] index forms tried.
u32 MemCheckHeapEnd(int no)
{
    int h = Heap[no].handle;
    OSHeapDescriptor* d;
    OSHeapCell* cell;
    u32 end;

    if (!memCheckHeapActive(no) || h < 0) {
        return 0;
    }
    d = HeapHead;
    d += h;
    // `d = HeapHead; d += h;` loads HeapHead straight into d (a global pseudo), so the block's
    // local qtys are only h*12 and the loaded `allocated` (the 3-qty partial sort would put h*12
    // first). The two-statement then-arm keeps jump1 from hoisting `end = 0` above the branch, so
    // cse1's path ends at the else arm and the loop init reloads `d->allocated`; jump2 hoists the
    // `li r3,0` between the compare and the branch afterwards.
    if (d->allocated == NULL) {
        cell = d->free;
        end = (u32) cell;
    } else {
        end = 0;
    }
    for (cell = d->allocated; cell != NULL; cell = cell->next) {
        if (end < (u32) cell + cell->size) {
            end = (u32) cell + cell->size;
        }
    }
    return end;
}

// Creates (or recreates) heap no over [start, end).
int MemCreateHeap(int no, u32 start, u32 end)
{
#if defined(RE4DC_GAME) && !defined(__PPC__) && (RE4DC_PS2_WORLD_SOURCE_OWNER || RE4DC_PS2_WORLD_R11F_OWNER)
    sourceWorldRetainedCreate(no,start,end);
#endif
    if (!memCheckHeapActive(no)) {
        return 0;
    }
    if (Heap[no].handle >= 0) {
#if RE4DC_CABIN_SOURCE
        if(!MemDestroyHeap(no))return 0;
#else
        MemDestroyHeap(no);
#endif
    }
    OSReport("-- MemCreateHeap %d %08x - %08x  ", no, start, end);
    Heap[no].handle = OSCreateHeap((void*) start, (void*) end);
    RE4DC_WORLD_HEAP_CHANGED();
    if (Heap[no].handle >= 0) {
        Heap[no].start = start;
        Heap[no].end = end;
        OSReport("succeed!!\n");
        return 1;
    }
    OSReport("failed!!\n");
    return 0;
}

// Destroys heap no (resuming it first if suspended).
int MemDestroyHeap(int no)
{
#if defined(RE4DC_GAME) && !defined(__PPC__) && (RE4DC_PS2_WORLD_SOURCE_OWNER || RE4DC_PS2_WORLD_R11F_OWNER)
    sourceWorldRetainedDestroy(no);
#endif
    if (!memCheckHeapActive(no)) {
        MemSignalHeap(no);
    }
    OSReport("-- MemDestroyHeap %d  ", no);
    if (Heap[no].handle >= 0) {
#if defined(RE4DC_GAME) && !defined(__PPC__) && ((defined(RE4DC_MOVIE_WORLD_ARENA) && RE4DC_MOVIE_WORLD_ARENA) || (defined(RE4DC_CABIN_SOURCE) && RE4DC_CABIN_SOURCE))
        if (!re4dc_movie_world_before_heap_change((void*)Heap[no].start, Heap[no].end-Heap[no].start)) {
            re4dc_missing("movie arena reader before heap destruction");
            return 0;
        }
#endif
#if RE4DC_CABIN_SOURCE
        if(!re4dc_cabin_carriers_retire_heap((void*)Heap[no].start,Heap[no].end-Heap[no].start)){
            re4dc_missing("cabin retirement before heap destruction");return 0;
        }
#endif
#if defined(RE4DC_GAME) && !defined(__PPC__) && RE4DC_ACTOR_TRANSACTION
        re4dc_actor_forget_range((void*)Heap[no].start,Heap[no].end-Heap[no].start);
#endif
#if defined(RE4DC_MOTION_CAPACITY) && RE4DC_MOTION_CAPACITY
        if(no==4 && !re4dc_motion_capacity_retire()) {
            re4dc_missing("motion overflow reader before heap destruction");return 0;
        }
#endif
        OSDestroyHeap(Heap[no].handle);
        Heap[no].handle = -1;
        RE4DC_WORLD_HEAP_CHANGED();
        OSReport("succeed!!\n");
#if defined(RE4DC_GAME) && !defined(__PPC__) && defined(RE4DC_SS11_PRELOAD) && RE4DC_SS11_PRELOAD
        // SS11_PRELOAD: the chapter title / results / save screens (SS heap 11) closed: the room preload runs again.
        if (no == 11) re4dc_ui_room_preload_again();
#endif
        return 1;
    }
    OSReport("failed!!\n");
    return 0;
}

// Shrinks heap `from` to what it has in use and creates heap `to` over the freed tail (or over
// `to`'s previous range when `from` does not exist); records the current heap's allocation list
// head in cell_main/game/stage/dll for the checker. 0 on failure.
int MemReplaceHeap(int from, int to)
{
    u32 start;
    u32 end;
    OSHeapDescriptor* hd;  // function scope: a global pseudo, allocated after the blocks' local qtys (lis/cell r9)

    if (CurrentHeap == 0) {
        hd = HeapHead + Heap[CurrentHeap].handle;
        cell_main = hd->allocated;
    }
    if (CurrentHeap == 1) {
        hd = HeapHead + Heap[CurrentHeap].handle;
        cell_game = hd->allocated;
    }
    if (CurrentHeap == 2) {
        hd = HeapHead + Heap[CurrentHeap].handle;
        cell_stage = hd->allocated;
    }
    if (CurrentHeap == 3) {
        hd = HeapHead + Heap[CurrentHeap].handle;
        cell_dll = hd->allocated;
    }
    if (!memCheckHeapActive(from)) {
        return 0;
    }
    if (!memCheckHeapActive(to)) {
        return 0;
    }
#if RE4DC_CABIN_SOURCE
    // Check every carrier without mutation before a media close can yield or
    // either descriptor can be changed. Unit retirement stays at destruction.
    const int cabin_heaps[]={from,to};
    for(int heap:cabin_heaps)if(Heap[heap].handle>=0 &&
       !re4dc_cabin_carriers_before_heap((void*)Heap[heap].start,Heap[heap].end-Heap[heap].start)){
        re4dc_missing("cabin preflight before source heap replacement");return 0;
    }
    for(int heap:cabin_heaps)if(Heap[heap].handle>=0 &&
       !re4dc_movie_world_before_heap_change((void*)Heap[heap].start,Heap[heap].end-Heap[heap].start)){
        re4dc_missing("cabin reader before source heap replacement");return 0;
    }
    // Media fences can yield. Recheck the entire set after their last return.
    for(int heap:cabin_heaps)if(Heap[heap].handle>=0 &&
       !re4dc_cabin_carriers_before_heap((void*)Heap[heap].start,Heap[heap].end-Heap[heap].start)){
        re4dc_missing("cabin revalidation before source heap replacement");return 0;
    }
#endif
#if defined(RE4DC_GAME) && !defined(__PPC__) && (RE4DC_PS2_WORLD_SOURCE_OWNER || RE4DC_PS2_WORLD_R11F_OWNER)
    SourceWorldRetainedTransfer retained;
    if(!sourceWorldRetainedCapture(from,to,&retained))return 0;
#endif
    if (Heap[from].handle >= 0) {
        start = MemCheckHeapEnd(from);
        end = Heap[from].end;
#if defined(RE4DC_HEAP_REPLACE_LOG) && RE4DC_HEAP_REPLACE_LOG
        // Test only: the live cells that set the next heap's base (a save load started heap 2
        // 2.93 MB higher than a new game). Logs the four highest-ending cells with their tags.
        {
            OSHeapDescriptor* d = HeapHead + Heap[from].handle;
            u32 done = 0xFFFFFFFF;
            for (int k = 0; k < 4; k++) {
                OSHeapCell* best = NULL;
                for (OSHeapCell* c = d->allocated; c != NULL; c = c->next) {
                    const u32 e = (u32) c + c->size;
                    if (e < done && (best == NULL || e > (u32) best + best->size)) best = c;
                }
                if (best == NULL) break;
                const u8* t = (const u8*) best + best->size - 0x20;
                re4dc_log("heap replace %d->%d: cell %08x size %u end %08x tag %s\n", from, to, (u32) best,
                          (u32) best->size, (u32) best + best->size,
                          (best->size >= 0x40 && !t[0] && t[1] == 'M' && t[2] == 'A' && t[3] == 'D') ? (const char*) t + 4 : "-");
                done = (u32) best + best->size;
            }
        }
#endif
#if RE4DC_CABIN_SOURCE
        if(!MemDestroyHeap(from))return 0;
#else
        MemDestroyHeap(from);
#endif
    } else {
        start = Heap[to].start;
        end = Heap[to].end;
    }
    if (start == 0) {
        return 0;
    }
#if defined(RE4DC_GAME) && !defined(__PPC__) && ((defined(RE4DC_MOVIE_WORLD_ARENA) && RE4DC_MOVIE_WORLD_ARENA) || (defined(RE4DC_CABIN_SOURCE) && RE4DC_CABIN_SOURCE))
    if (!re4dc_movie_world_before_heap_change((void*)start, end-start)) {
        re4dc_missing("movie arena reader before heap replacement");
        return 0;
    }
#endif
#if defined(RE4DC_GAME) && !defined(__PPC__) && (RE4DC_PS2_WORLD_SOURCE_OWNER || RE4DC_PS2_WORLD_R11F_OWNER)
    const int result=MemCreateHeap(to,start,end);
    sourceWorldRetainedPublish(retained,result);
    return result;
#else
    return MemCreateHeap(to, start, end);
#endif
}

// Destroys every heap (soft reset).
void MemClearAllHeap()
{
#if defined(RE4DC_GAME) && !defined(__PPC__) && (RE4DC_PS2_WORLD_SOURCE_OWNER || RE4DC_PS2_WORLD_R11F_OWNER)
    sourceWorldRetainedReset();
#endif
    u32 i;

#if defined(RE4DC_GAME) && !defined(__PPC__) && ((defined(RE4DC_MOVIE_WORLD_ARENA) && RE4DC_MOVIE_WORLD_ARENA) || (defined(RE4DC_CABIN_SOURCE) && RE4DC_CABIN_SOURCE))
#if RE4DC_CABIN_SOURCE
    for(i=0;i<MEM_HEAP_NUM;++i)if(Heap[i].handle>=0 &&
       !re4dc_cabin_carriers_before_heap((void*)Heap[i].start,Heap[i].end-Heap[i].start)){
        re4dc_missing("cabin preflight before all-heap clear");return;
    }
#endif
    // Ancestor heaps are destroyed first. Retire the overlapping native owner
    // while all descriptors are intact, before any iteration changes a heap.
    for (i = 0; i < MEM_HEAP_NUM; i++) {
        if (Heap[i].handle >= 0 &&
            !re4dc_movie_world_before_heap_change((void*)Heap[i].start, Heap[i].end-Heap[i].start)) {
            re4dc_missing("movie arena reader before all-heap clear");
            return;
        }
    }
#if RE4DC_CABIN_SOURCE
    for(i=0;i<MEM_HEAP_NUM;++i)if(Heap[i].handle>=0 &&
       !re4dc_cabin_carriers_before_heap((void*)Heap[i].start,Heap[i].end-Heap[i].start)){
        re4dc_missing("cabin revalidation before all-heap clear");return;
    }
#endif
#endif
#if defined(RE4DC_MOTION_CAPACITY) && RE4DC_MOTION_CAPACITY
    if(Heap[4].handle>=0 && !re4dc_motion_capacity_retire()) {
        re4dc_missing("motion overflow reader before all-heap clear");return;
    }
#endif
    for (i = 0; i < MEM_HEAP_NUM; i++) {
        if (Heap[i].handle >= 0) {
            MemDestroyHeap(i);
        }
    }
}

// Allocates size (rounded to 32) from `heap` (MEM_HEAP_CURRENT = current) with a 32-byte "MAD"
// tag holding "file(line)" after the block; flag 1 logs allocation failures. NULL when size is 0,
// the heap is suspended or full.
#if defined(RE4DC_HEAP4_WATER) && RE4DC_HEAP4_WATER
// Set by re4dc_mem_alloc_top (SS_POOL_TOP) while it holds every other heap-4 free cell: the free list is empty only for
// that call, so the low-water sample is skipped there (it read free 0 and muted the room's later lines).
static int re4dc_heap4_water_hold;
#endif
void* mem_alloc(u32 size, const char* file, int line, int flag, int heap)
{
    char str[64] = "";
    u8* p;
    char* name;
    u8* tag;

    if (size == 0) {
        return NULL;
    }
    if (heap == MEM_HEAP_CURRENT) {
        heap = CurrentHeap;
    }
    if (!memCheckHeapActive(heap)) {
        return NULL;
    }
    size = (size + 0x1F) & ~0x1F;
    if (file == NULL) {
        p = (u8*) OSAllocFromHeap(Heap[heap].handle, size);
#if defined(RE4DC_FAR_SHELL) && RE4DC_FAR_SHELL
        // FAR_SHELL (platform/far_shell.inc): heap 4 short, the far shell gives its block back and the request retries.
        if (p == NULL && heap == 4 && re4dc_far_shell_shortfall(size, "untagged")) {
            p = (u8*) OSAllocFromHeap(Heap[heap].handle, size);
        }
#endif
#if defined(RE4DC_MOTION_CAPACITY) && RE4DC_MOTION_CAPACITY
        if(p==NULL && heap==4)p=(u8*)re4dc_motion_required_alloc(Heap[heap].handle,size);
#endif
    } else {
        p = (u8*) OSAllocFromHeap(Heap[heap].handle, size + 0x20);
#if defined(RE4DC_FAR_SHELL) && RE4DC_FAR_SHELL
        if (p == NULL && heap == 4 && re4dc_far_shell_shortfall(size + 0x20, file)) {
            p = (u8*) OSAllocFromHeap(Heap[heap].handle, size + 0x20);
        }
#endif
#if defined(RE4DC_MOTION_CAPACITY) && RE4DC_MOTION_CAPACITY
        if(p==NULL && heap==4)p=(u8*)re4dc_motion_required_alloc(Heap[heap].handle,size+0x20);
#endif
        name = strrchr(file, '/');
        if (name == NULL) {
            name = (char*) file;
        } else {
            name++;
        }
#if defined(RE4DC_COPY_LEAN) && RE4DC_COPY_LEAN && defined(__sh__)
        // Same bytes as sprintf(str, "%s(%d)", name, line) (bounded to str), without newlib's
        // vfprintf: every tagged allocation paid ~2 us for it (D367 frontend30).
        {
            char* o = str;
            char* const lim = str + sizeof(str) - 1;
            for (const char* s = name; *s != 0 && o < lim; s++) {
                *o++ = *s;
            }
            char digits[12];
            int nd = 0;
            u32 v = line < 0 ? 0u - (u32) line : (u32) line;
            do {
                digits[nd++] = (char) ('0' + v % 10);
                v /= 10;
            } while (v != 0);
            if (o < lim) *o++ = '(';
            if (line < 0 && o < lim) *o++ = '-';
            while (nd > 0 && o < lim) *o++ = digits[--nd];
            if (o < lim) *o++ = ')';
            *o = 0;
        }
#else
        sprintf(str, "%s(%d)", name, line);
#endif
        str[0x1B] = 0;
        if (p != NULL) {
            tag = p + size;
            tag[0] = 0;
            tag[1] = 'M';
            tag[2] = 'A';
            tag[3] = 'D';
            strcpy((char*) tag + 4, str);
        }
    }
#if !defined(__PPC__)
    // Opt-in boot diagnostics: report room allocations without changing the
    // source allocator or its lifetime. Small successes remain in free totals.
    if (re4dc_diag && heap == 4 && (size >= 1024 || p == NULL)) {
        OSReport("Native room alloc: size=%u addr=%08x free=%d at=%s\n",
                 size, p, OSCheckHeap(Heap[heap].handle), file ? str : "untagged");
    }
#endif
    if (flag == 1 && p == NULL) {
        pLog->err(0, 0, "alloc[%x]:free[%x] %s", size, OSCheckHeap(Heap[heap].handle), str);
    }
#if defined(RE4DC_TRACE_ALLOC) && RE4DC_TRACE_ALLOC
    // TRACE_ALLOC=1 (logic_trace.cpp): a failed required heap-4 allocation is a must-match trace event. Native parts
    // runs are reported by parts_bridge.cpp after its reservation fallback, so only a final failure counts.
    if (flag == 1 && p == NULL && heap == 4 && !(file && strcmp(file, "native parts run") == 0)) {
        extern void re4dc_logic_trace_alloc_fail(unsigned size, const char* site);
        re4dc_logic_trace_alloc_fail(size, str);
    }
#endif
#line 522
#if defined(RE4DC_HEAP_CENSUS) && RE4DC_HEAP_CENSUS
    // Test only: the first failed heap-4 allocation logs what fills heap 4, bytes per tag.
    if (p == NULL && heap == 4) {
        static int census_done;
        if (!census_done && Heap[heap].handle >= 0) {
            census_done = 1;
            enum { kTags = 128 };
            static const char* tags[kTags];
            static u32 bytes[kTags], cells[kTags];
            int n = 0;
            u32 total = 0, count = 0, free_total = 0, free_max = 0, free_cells = 0;
            OSHeapDescriptor* d = HeapHead + Heap[heap].handle;
            for (OSHeapCell* c = d->allocated; c != NULL; c = c->next) {
                const u8* t = (const u8*) c + c->size - 0x20;
                const char* k = (c->size >= 0x40 && !t[0] && t[1] == 'M' && t[2] == 'A' && t[3] == 'D') ? (const char*) t + 4 : "-";
                int j = 0;
                while (j < n && strcmp(tags[j], k) != 0) j++;
                if (j == n) {
                    if (n == kTags) j = kTags - 1, k = tags[j];
                    else { tags[n] = k; bytes[n] = cells[n] = 0; n++; }
                }
                bytes[j] += c->size; cells[j]++;
                total += c->size; count++;
            }
            for (OSHeapCell* c = d->free; c != NULL; c = c->next) {
                free_total += c->size; free_cells++;
                if ((u32) c->size > free_max) free_max = c->size;
            }
            re4dc_log("heap census 4: size %u allocated %u in %u cells, free %u in %u cells (largest %u), failed %u at %s\n",
                      (u32) d->size, total, count, free_total, free_cells, free_max, size, file ? str : "untagged");
            for (int r = 0; r < n; r++) {
                int best = r;
                for (int j = r + 1; j < n; j++) if (bytes[j] > bytes[best]) best = j;
                const char* tt = tags[r]; tags[r] = tags[best]; tags[best] = tt;
                u32 tb = bytes[r]; bytes[r] = bytes[best]; bytes[best] = tb;
                u32 tc = cells[r]; cells[r] = cells[best]; cells[best] = tc;
                re4dc_log("heap census 4: %8u bytes %4u cells %s\n", bytes[r], cells[r], tags[r]);
            }
            // Layout (fragmentation): free cells >= 16 KB and allocated cells >= 32 KB, by address.
            for (OSHeapCell* c = d->free; c != NULL; c = c->next)
                if ((u32) c->size >= 0x4000) re4dc_log("heap map 4: free %08x %u\n", (u32) c, (u32) c->size);
            for (OSHeapCell* c = d->allocated; c != NULL; c = c->next) {
                const u8* t = (const u8*) c + c->size - 0x20;
                const char* k = (c->size >= 0x40 && !t[0] && t[1] == 'M' && t[2] == 'A' && t[3] == 'D') ? (const char*) t + 4 : "-";
                if ((u32) c->size >= 0x8000) re4dc_log("heap map 4: used %08x %u %s\n", (u32) c, (u32) c->size, k);
            }
        }
    }
#endif
#if defined(RE4DC_HEAP4_WATER) && RE4DC_HEAP4_WATER
    // Test only (HEAP4_WATER=1): heap 4's low-water mark per room. After every heap-4 allocation, the free list's
    // total and largest cell; a new room minimum at least 8 KB below the last one logged is reported with the
    // allocation that made it (the last line of a room is its low-water mark; a failure always logs).
    if (heap == 4 && Heap[heap].handle >= 0 && !re4dc_heap4_water_hold) {
        static u32 room, low, logged;
        OSHeapDescriptor* d = HeapHead + Heap[heap].handle;
        u32 free_total = 0, free_max = 0;
        for (OSHeapCell* c = d->free; c != NULL; c = c->next) {
            free_total += c->size;
            if ((u32) c->size > free_max) free_max = c->size;
        }
        if (pG && room != (u32) pG->room_id) {
            room = pG->room_id;
            low = logged = 0xFFFFFFFFu;
        }
        if (free_total < low) low = free_total;
        if (p == NULL || low + 8192 <= logged) {
            logged = low;
            re4dc_log("heap4 water: room %03x free %u largest %u span %u after %u at %s%s\n", (unsigned) room, free_total,
                      free_max, (u32) d->size, size, file ? str : "untagged", p ? "" : " FAILED");
        }
    }
#endif
    return p;
}

#if defined(RE4DC_SS_POOL_TOP) && RE4DC_SS_POOL_TOP
// SS_POOL_TOP (lane ch3found16 2026-10-16): place a tagged block at the top end of the heap's highest free cell.
// Every lower free cell that could take it is held, a filler takes the top cell's low part, then the block takes the
// rest; held cells and the filler are freed again. Same block, same size, only the address. Returns 0 when the top cell
// cannot take it (the caller keeps its first-fit path).
void* re4dc_mem_alloc_top(u32 size, const char* file, int line, int heap)
{
    if (heap == MEM_HEAP_CURRENT) heap = CurrentHeap;
    if (size == 0 || !memCheckHeapActive(heap)) return NULL;
    const int h = Heap[heap].handle;
    OSHeapDescriptor* d = HeapHead + h;
    const u32 need = ((((size + 0x1F) & ~0x1Fu) + 0x20) + 0x20 + 0x1F) & ~0x1Fu;  // tag + cell header
    OSHeapCell* top = NULL;
    for (OSHeapCell* c = d->free; c != NULL; c = c->next)
        if (top == NULL || c > top) top = c;
    if (top == NULL || (u32) top->size < need + 0x80) return NULL;
    void* held[64];
    unsigned n = 0;
    for (;;) {
        OSHeapCell* low = NULL;
        for (OSHeapCell* c = d->free; c != NULL; c = c->next)
            if (c != top && (u32) c->size >= need && (low == NULL || c < low)) low = c;
        if (low == NULL || n == 64) break;
        void* q = OSAllocFromHeap(h, (u32) low->size - 0x20);
        if (q == NULL) break;
        held[n++] = q;
    }
    void* filler = OSAllocFromHeap(h, (u32) top->size - need - 0x20);
    void* p = NULL;
    if (filler != NULL && (u8*) filler == (u8*) top + 0x20) {
#if defined(RE4DC_HEAP4_WATER) && RE4DC_HEAP4_WATER
        re4dc_heap4_water_hold = 1;
#endif
        p = mem_alloc(size, file, line, 1, heap);
#if defined(RE4DC_HEAP4_WATER) && RE4DC_HEAP4_WATER
        re4dc_heap4_water_hold = 0;
#endif
    }
    if (filler != NULL) OSFreeToHeap(h, filler);
    for (unsigned i = 0; i < n; ++i) OSFreeToHeap(h, held[i]);
    if (p != NULL && (u8*) p < (u8*) top) {
        Mem_free_h(p, heap);
        return NULL;
    }
    return p;
}
#endif

// mem_alloc plus zero fill.
void* mem_calloc(u32 size, const char* file, int line, int flag, int heap)
{
    void* p = mem_alloc(size, file, line, flag, heap);

    if (p != NULL) {
        memclr_asm(p, size);
    }
    return p;
}

// Frees a block to the current heap.
#if defined(RE4DC_OSFREE_CHECK) && RE4DC_OSFREE_CHECK
extern "C" void* re4dc_osfree_ra[2];  // OSAlloc.c OSFREE_CHECK: Mem_free / Mem_free_h callers
#endif
void Mem_free(void* p)
{
#if defined(RE4DC_OSFREE_CHECK) && RE4DC_OSFREE_CHECK
    re4dc_osfree_ra[1] = __builtin_return_address(0);
#endif
    Mem_free_h(p, CurrentHeap);
}

// Frees a block (to the OS current heap) when heap `heap` is active.
void Mem_free_h(void* p, int heap)
{
#if RE4DC_CABIN_SOURCE
    if(!re4dc_cabin_carrier_before_free(p)){re4dc_missing("cabin carrier reader before individual free");return;}
#endif
#if defined(RE4DC_GAME) && !defined(__PPC__) && (RE4DC_PS2_WORLD_SOURCE_OWNER || RE4DC_PS2_WORLD_R11F_OWNER)
    sourceWorldRetainedFree(p);
#endif
#if defined(RE4DC_OSFREE_CHECK) && RE4DC_OSFREE_CHECK
    re4dc_osfree_ra[0] = __builtin_return_address(0);
#endif
    if (heap == MEM_HEAP_CURRENT) {
        heap = CurrentHeap;
    }
    if (memCheckHeapActive(heap)) {
#if defined(RE4DC_GAME) && !defined(__PPC__) && RE4DC_ACTOR_TRANSACTION
        if(p) {
            const int bytes=((OSHeapCell*)((u8*)p-0x20))->size;
            if(bytes>=0x20)re4dc_actor_forget_range(p,(unsigned)bytes-0x20);
        }
#endif
        OSFreeToHeap(__OSCurrHeap, p);
    }
}

// Tool mode: Debug_alloc(flag 1) blocks are tagged "toolmem" so ResetDebugAlloc can free them.
void SetDebugAlloc()
{
    Dalloc_flg = 1;
}

// The cell header fields the debug code reads (the real OSHeapCell is 0x20 bytes).
struct MemCellHead {
    OSHeapCell* prev;  // 0x00
    OSHeapCell* next;  // 0x04
    s32 size;          // 0x08
};

// Frees every "toolmem" block of the debug heap and leaves tool mode.
void ResetDebugAlloc()
{
    OSHeapCell* cell;
    MemCellHead tmp;

    Dalloc_flg = 0;
    {
        // pointer + index (the pointer is the first `add` operand, tied to HeapHead's register)
        OSHeapDescriptor* hd = HeapHead + Heap[CurrentDbgHeap].handle;
        cell = hd->allocated;
    }
    for (; cell != NULL; cell = tmp.next) {
        tmp = *(MemCellHead*) cell;
        if (strcmp((char*) cell + cell->size - 8, "toolmem") == 0) {
            Debug_free((u8*) cell + 0x20);
        }
    }
}

// Zeroed allocation from the debug heap (flag 1 in tool mode adds the "toolmem" tag).
void* Debug_alloc(u32 size, int flag)
{
    u8* p;

    if (size == 0) {
        return NULL;
    }
    if (!memCheckHeapActive(CurrentDbgHeap)) {
        return NULL;
    }
    if (Dalloc_flg == 1 && flag == 1) {
        size += 8;
    }
    size = (size + 0x1F) & ~0x1F;
    p = (u8*) OSAllocFromHeap(Heap[CurrentDbgHeap].handle, size);
#if defined(RE4DC_MOTION_CAPACITY) && RE4DC_MOTION_CAPACITY
    if(p==NULL && CurrentDbgHeap==4)p=(u8*)re4dc_motion_required_alloc(Heap[4].handle,size);
#endif
    if (p != NULL) {
        memclr_asm(p, size);
        if (Dalloc_flg == 1 && flag == 1) {
            strcpy((char*) p + size - 8, "toolmem");
        }
    }
    return p;
}

// Frees a debug heap block.
void Debug_free(void* p)
{
    Debug_free_h(p, CurrentDbgHeap);
}

// Frees a debug block after wiping it (poison for stale pointers).
void Debug_free_h(void* p, int heap)
{
#if defined(RE4DC_GAME) && !defined(__PPC__) && (RE4DC_PS2_WORLD_SOURCE_OWNER || RE4DC_PS2_WORLD_R11F_OWNER)
    sourceWorldRetainedFree(p);
#endif
    if (heap == MEM_HEAP_CURRENT) {
        heap = CurrentDbgHeap;
    }
    if (memCheckHeapActive(heap)) {
#if defined(RE4DC_GAME) && !defined(__PPC__) && RE4DC_ACTOR_TRANSACTION
        if(p) {
            const int bytes=((OSHeapCell*)((u8*)p-0x20))->size;
            if(bytes>=0x20)re4dc_actor_forget_range(p,(unsigned)bytes-0x20);
        }
#endif
        memclr_asm(p, ((OSHeapCell*) ((u8*) p - 0x20))->size - 0x20);
        OSFreeToHeap(Heap[CurrentDbgHeap].handle, p);
    }
}

// Game allocation, or a debug-heap allocation when Debug_flg[3] 0x200000 (tool memory mode).
void* MemAlloc(u32 size, int flag)
{
    void* p;

    if (!(pG->Debug_flg[3] & 0x200000)) {
#line 646
        p = MEM_ALLOC(size, 1, MEM_HEAP_CURRENT);
    } else {
        p = Debug_alloc(size, flag);
    }
    return p;
}

// Counterpart of MemAlloc.
void MemFree(void* p)
{
    if (pG->Debug_flg[3] & 0x200000) {
        Debug_free(p);
    } else {
        Mem_free(p);
    }
}

// Debug heap display (debug page 4): one TILE per allocated cell (0x20-byte primitives).
// Matching. Shape (same as datactrl dispDebug): y0/y1 and `x = 498` are function-scope locals
// (y1 is reused for the end marker's height, x is a REG_EQUIV constant that reload rematerialises
// before each `sth x0`, which is what lets the code constant's register be reused), the tile
// stores are in datactrl's order (code, x0, y0, ...; r, g, b), `mt = &tile[0]` precedes the
// end-marker conversion, and the cell loop starts from `hd = HeapHead + handle`.
struct MemTile {
    u32 tag;       // 0x00
    u32 code;      // 0x04
    u8 r, g, b, cd;  // 0x08
    s16 x0, y0;    // 0x0C
    s16 w, h;      // 0x10
    s16 z0;        // 0x14
    u8 pad_16[0x20 - 0x16];
};

struct SysFlagsView {
    u32 flags;  // 0x00  SystemWork::flags
};
extern SysFlagsView* pSysView asm("pSys");
// Reference read: the load stays below the preceding tile stores (see mercenaries.cpp SysRef).
static inline SysFlagsView* SysRef(SysFlagsView*& p) { return p; }
extern u32 MainOt[5];

struct DvdFreeSizeView {
    u32 freeSize;  // 0x00  cDvd::freeSize
    u8 pad_4[0x10];  // (keeps the extern out of small data)
};
extern DvdFreeSizeView DvdView asm("Dvd");

static inline void ISet(int& d, int v) { d = v; }

#define MEM_TAG_OK(tag) ((tag)[0] == 0 && (tag)[1] == 'M' && (tag)[2] == 'A' && (tag)[3] == 'D')

// Debug display (debug_mode 4): draws the heap map (tiles per heap) and lists the allocated cells
// with their "file(line)" tags; C-stick scrolls, Z+Y writes the list to a host file.
void MemCheckUsedHeap()
{
    char* p = NULL;
    char* buf = p;
    int full = 0;
    int write = 0;
    int rest;
    u32 end;
    u32 start;
    u32 heapEnd;
    u32 size;
    int ey;
    int cnt;
    OSHeapCell* cell;
    OSHeapCell* next;
    OSHeapDescriptor* hd;
    MemTile* mt;
    int r;
    int n;
    u32 y0;
    u32 y1;
    int x;
    static int ey_base = 30;
    static MemTile tile[2];

    x = 498;
    if (pG->debug_mode == 4 && (Joy[0].on & 0x10) && (Joy[0].trg & 0x400)) {
        write = 1;
    }
    if (write == 1) {
        buf = (char*) Debug_alloc(0x2000, 1);
        p = buf;
    }
    if (!memCheckHeapActive(CurrentHeap)) {
        return;
    }
    rest = OSCheckHeap(Heap[CurrentHeap].handle) - 0x10000;
    if (rest >= 0) {
        end = MemCheckHeapEnd(CurrentHeap);
    } else {
        end = SysMem.heap_end;
    }
    start = Heap[CurrentHeap].start;
    heapEnd = Heap[CurrentHeap].end;
    eprintf2(8, 16, 440, 404, 0, 0, "%X", rest);
    r = OSCheckHeap(Heap[CurrentDbgHeap].handle);
    if (r >= 0) {
        eprintf2(8, 16, 440, 420, 0, 0, "%X", r);
    } else {
        eprintf2(8, 16, 440, 420, 2, 0, "%X", r);
    }
    if (Joy[0].rep2 & 0x400000) {
        ey_base -= 16;
    }
    if (Joy[0].rep2 & 0x800000) {
        ey_base += 16;
    }
    if (ey_base >= -2000) {
        n = ey_base;
        if (n > 2000) {
            n = 2000;
        }
    } else {
        n = -2000;
    }
    ISet(ey_base, n);
    ey = ey_base;
    size = heapEnd - start;
    mt = (MemTile*) pMemTile;
    cnt = 0;
    hd = HeapHead + Heap[CurrentHeap].handle;
    for (cell = hd->allocated; cell != NULL; cell = cell->next) {
        y0 = (u32) ((f32) ((u32) cell - start) * 400.0f / (f32) size);
        y1 = (u32) ((f32) ((u32) cell + cell->size - start) * 400.0f / (f32) size) + 1;

        u8* tag = (u8*) cell + cell->size - 0x20;
        if ((s32) tag >= 0 || (u32) tag > RE4_MEM_HI) {
            break;
        }
        if (MEM_TAG_OK(tag)) {
            eprintf2(8, 14, 230, ey, 0, 4, "%-18s %6x %08x", tag + 4, cell->size - 0x20, cell);
        } else {
            eprintf2(8, 14, 230, ey, 0, 4, "unknown           %6x %08x", cell->size - 0x20, cell);
        }
        if (write == 1 && cell->size - 0x20 > 0x1000) {
            p += sprintf(p, "%6x %18s\n", cell->size - 0x20, tag + 4);
        }
        ey += 14;
        next = cell->next;
        if (next != NULL && next->next != NULL &&
            ((s32) next->next >= 0 || (u32) next->next > RE4_MEM_HI)) {
            pLog->err(0, 0, "heap next err:%-18s %6x %08x", tag + 4, cell->size - 0x20, cell);
            pLog->err(0, 0, "next addr    : %08x", cell->next);
#line 770
            HALT();
        }
        if (pMemTile != NULL && full == 0) {
            mt->code = 4;
            mt->x0 = x;
            mt->y0 = y0 + 30;
            mt->w = 5;
            mt->h = y1 - y0;
            mt->z0 = full;
            if (rest >= 0) {
                mt->r = 0x60;
                mt->g = 0x60;
                mt->b = 0x80;
            } else {
                mt->r = 0xFF;
                mt->g = 0x20;
                mt->b = 0x20;
            }
            mt->cd = 0xFF;
            if (SysRef(pSysView)->flags & 0x40000000) {
                mt->y0 = (s16) ((f32) mt->y0 / 1.3333334f + 56.0f);
                mt->h = (s16) ((f32) mt->h / 1.3333334f);
            }
            AddPrim(&MainOt[1], (u32*) mt);
            mt++;
            if (cnt++ == 0x1FF) {
                full = 1;
            }
        }
    }
    if (pMemTile == NULL || full == 1) {
        mt = &tile[0];
        y1 = (u32) ((f32) (end - start) * 400.0f / (f32) size);
        mt->code = 4;
        mt->x0 = x;
        mt->y0 = 30;
        mt->z0 = 0;
        mt->w = 5;
        mt->h = y1;
        if (rest >= 0) {
            mt->r = 0x60;
            mt->g = 0x60;
            mt->b = 0x80;
        } else {
            mt->r = 0xFF;
            mt->g = 0x20;
            mt->b = 0x20;
        }
        mt->cd = 0xFF;
        if (SysRef(pSysView)->flags & 0x40000000) {
            mt->y0 = (s16) ((f32) mt->y0 / 1.3333334f + 56.0f);
            mt->h = (s16) ((f32) mt->h / 1.3333334f);
        }
        AddPrim(&MainOt[1], (u32*) mt);
    }
    if (CurrentHeap == 4) {
        for (cell = cell_dll; cell != NULL; cell = cell->next) {
            u8* tag = (u8*) cell + cell->size - 0x20;
            if ((s32) tag >= 0 || (u32) tag > RE4_MEM_HI) {
                break;
            }
            if (MEM_TAG_OK(tag)) {
                eprintf2(8, 14, 230, ey, 22, 4, "%-18s %6x %08x", tag + 4, cell->size - 0x20, cell);
            } else {
                eprintf2(8, 14, 230, ey, 22, 4, "unknown           %6x %08x", cell->size - 0x20, cell);
            }
            ey += 14;
            if (write == 1 && cell->size - 0x20 > 0x1000) {
                p += sprintf(p, "%6x %18s\n", cell->size - 0x20, tag + 4);
            }
            next = cell->next;
            if (next != NULL && next->next != NULL &&
                ((s32) next->next >= 0 || (u32) next->next > RE4_MEM_HI)) {
                pLog->err(0, 0, "heap next err:%-18s %6x %08x", tag + 4, cell->size - 0x20, cell);
                pLog->err(0, 0, "next addr    : %08x", cell->next);
#line 870
                HALT();
            }
        }
        for (cell = cell_stage; cell != NULL; cell = cell->next) {
            u8* tag = (u8*) cell + cell->size - 0x20;
            if ((s32) tag >= 0 || (u32) tag > RE4_MEM_HI) {
                break;
            }
            if (MEM_TAG_OK(tag)) {
                eprintf2(8, 14, 230, ey, 22, 4, "%-18s %6x %08x", tag + 4, cell->size - 0x20, cell);
            } else {
                eprintf2(8, 14, 230, ey, 22, 4, "unknown           %6x %08x", cell->size - 0x20, cell);
            }
            ey += 14;
            if (write == 1 && cell->size - 0x20 > 0x1000) {
                p += sprintf(p, "%6x %18s\n", cell->size - 0x20, tag + 4);
            }
            next = cell->next;
            if (next != NULL && next->next != NULL &&
                ((s32) next->next >= 0 || (u32) next->next > RE4_MEM_HI)) {
                pLog->err(0, 0, "heap next err:%-18s %6x %08x", tag + 4, cell->size - 0x20, cell);
                pLog->err(0, 0, "next addr    : %08x", cell->next);
#line 904
                HALT();
            }
        }
        for (cell = cell_game; cell != NULL; cell = cell->next) {
            u8* tag = (u8*) cell + cell->size - 0x20;
            if ((s32) tag >= 0 || (u32) tag > RE4_MEM_HI) {
                break;
            }
            if (MEM_TAG_OK(tag)) {
                eprintf2(8, 14, 230, ey, 18, 4, "%-18s %6x %08x", tag + 4, cell->size - 0x20, cell);
            } else {
                eprintf2(8, 14, 230, ey, 18, 4, "unknown           %6x %08x", cell->size - 0x20, cell);
            }
            if (write == 1 && cell->size - 0x20 > 0x1000) {
                p += sprintf(p, "%6x %18s\n", cell->size - 0x20, tag + 4);
            }
            ey += 14;
            next = cell->next;
            if (next != NULL && next->next != NULL &&
                ((s32) next->next >= 0 || (u32) next->next > RE4_MEM_HI)) {
                pLog->err(0, 0, "heap next err:%-18s %6x %08x", tag + 4, cell->size - 0x20, cell);
                pLog->err(0, 0, "next addr    : %08x", cell->next);
#line 938
                HALT();
            }
        }
        for (cell = cell_main; cell != NULL; cell = cell->next) {
            u8* tag = (u8*) cell + cell->size - 0x20;
            if ((s32) tag >= 0 || (u32) tag > RE4_MEM_HI) {
                break;
            }
            if (MEM_TAG_OK(tag)) {
                eprintf2(8, 14, 230, ey, 20, 4, "%-18s %6x %08x", tag + 4, cell->size - 0x20, cell);
            } else {
                eprintf2(8, 14, 230, ey, 20, 4, "unknown           %6x %08x", cell->size - 0x20, cell);
            }
            if (write == 1 && cell->size - 0x20 > 0x1000) {
                p += sprintf(p, "%6x %18s\n", cell->size - 0x20, tag + 4);
            }
            ey += 14;
            next = cell->next;
            if (next != NULL && next->next != NULL &&
                ((s32) next->next >= 0 || (u32) next->next > RE4_MEM_HI)) {
                pLog->err(0, 0, "heap next err:%-18s %6x %08x", tag + 4, cell->size - 0x20, cell);
                pLog->err(0, 0, "next addr    : %08x", cell->next);
#line 974
                HALT();
            }
        }
    }
    {
        mt = &tile[1];
        mt->code = 4;
        mt->x0 = x;
        mt->y0 = 30;
        mt->z0 = 0;
        mt->w = 5;
        mt->h = 400;
        mt->b = mt->g = mt->r = 0x20;
        mt->cd = 0xFF;
        if (SysRef(pSysView)->flags & 0x40000000) {
            mt->y0 = 78;
            mt->h = 300;
        }
        AddPrim(&MainOt[1], (u32*) mt);
    }
    eprintf2(10, 16, 30, 0x38, 0, 4, "elf_end   %8x", SysMem.arena_lo);
    eprintf2(10, 16, 30, 0x58, 0, 4, "DVD       %8x", SysMem.elf_end);
    eprintf2(10, 16, 30, 0x68, 0, 4, "SOUND     %8x", SysMem.dvd);
    eprintf2(10, 16, 30, 0x78, 0, 4, "FIFO      %8x", SysMem.sound);
    eprintf2(10, 16, 30, 0x88, 0, 4, "XFB       %8x", SysMem.fifo);
    eprintf2(10, 16, 30, 0x98, 0, 4, "CORE      %8x", SysMem.xfb);
    eprintf2(10, 16, 30, 0xA8, 0, 4, "OPTION    %8x", SysMem.core);
    eprintf2(10, 16, 30, 0xB8, 0, 4, "PLAYER    %8x", SysMem.option);
    eprintf2(10, 16, 30, 0xC8, 0, 4, "WEAPON    %8x", SysMem.player);
    eprintf2(10, 16, 30, 0xD8, 0, 4, "HEAP_TOP  %8x", SysMem.weapon);
    eprintf2(10, 16, 30, 0xE8, 0, 4, "HEAP_SIZE %x", SysMem.heap_end - SysMem.weapon);
    eprintf2(10, 16, 30, 0x108, 0, 4, "NOW_HEAP  %8x", start);
    eprintf2(10, 16, 30, 0x118, 0, 4, " SIZE     %x", size);
    eprintf2(10, 16, 30, 0x128, 0, 4, " REST     %x", rest);
    eprintf2(10, 16, 30, 0x148, 0, 4, "FST_SIZE  %x", DvdView.freeSize);
    eprintf2(10, 16, 30, 0x168, 0, 4, "USB       %8x", SysMem.usb);
    eprintf2(10, 16, 30, 0x178, 0, 4, "DEBUG     %8x", SysMem.debug);
    if (Joy[0].rep2 & 0x400000) {
        _epy_base -= 16;
    }
    if (Joy[0].rep2 & 0x800000) {
        _epy_base += 16;
    }
    _epy = _epy_base;
    if (write == 1) {
        HDWrite("d:\\bio4\\prog\\memlog.txt", buf, p - buf);
        Debug_free(buf);
    }
}

// Counts memset errors (leftover debug hook).
// Dead-stripped helper: only its string and statics survive (STRIP_UNUSED).
static void memSetCheck()
{
    static int memSetErrCnt = 0;

    memSetErrCnt++;
    OSReport("memset error: ");
}

// main_sub's .bss starts 8-aligned; the split object carries the 4-byte pad.
asm(".section .bss; .balign 8");

#if RE4DC_CABIN_SOURCE
extern "C" int re4dc_cabin_source_allocation(const void* pointer,unsigned bytes,int* heap){
    if(!pointer || !bytes || !heap)return 0;
    for(unsigned i=0;i<MEM_HEAP_NUM;++i){
        if(Heap[i].handle<0 || !memCheckHeapActive(i))continue;
        const OSHeapDescriptor& descriptor=HeapHead[Heap[i].handle];
        for(const OSHeapCell* cell=descriptor.allocated;cell;cell=cell->next){
            if((const u8*)cell+0x20!=pointer || cell->size<0x40)continue;
            // Source carriers/modules use tagged mem_alloc blocks. Account for
            // OSAlloc consuming an otherwise unusable final 32-byte remainder.
            unsigned payload=(unsigned)cell->size-0x40;
            bool tag=false;
            for(int tail=32;tail>=0;tail-=32){
                if((unsigned)tail>payload)continue;
                const u8* t=(const u8*)pointer+payload-tail;
                if(t[0]==0 && t[1]=='M' && t[2]=='A' && t[3]=='D'){
                    if(bytes>payload-tail)return 0;tag=true;break;
                }
            }
            if(!tag)return 0;
            *heap=(int)i;return 1;
        }
    }
    return 0;
}
extern "C" void* re4dc_cabin_source_alloc(unsigned bytes,int heap){
    return mem_alloc(bytes,"cabin mutable EVD",0,1,heap);
}
extern "C" int re4dc_cabin_source_free(void* pointer,unsigned bytes,int heap){
    int actual_heap=-1;
    if(!re4dc_cabin_carrier_before_free(pointer) ||
       !re4dc_cabin_source_allocation(pointer,bytes,&actual_heap) || actual_heap!=heap)return 0;
    // The exact live source allocation was checked above. OSFreeToHeap is a
    // synchronous, non-yielding list update and has no fallible return path.
    OSFreeToHeap(Heap[heap].handle,pointer);return 1;
}
#endif
