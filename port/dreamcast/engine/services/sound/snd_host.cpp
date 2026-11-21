// What the hosted sound driver (src/game/snd*.cpp, H-025.1) needs from below it, on the engine (lane eng-snd1).
//
//  - OS: interrupt guards (the driver's calls from game code run with interrupts off, so the 5 ms audio thread cannot
//    run inside them, as the GameCube's audio interrupt could not), the console's sound mode, panic.
//  - ARAM: the GameCube's auxiliary RAM does not exist here. The allocator hands out the driver's addresses
//    (lifted from the old port's audio_stub.cpp, the SDK's stack allocator); a transfer completes without a copy: the
//    sound banks reach the AICA through the engine's room loader (snd_svc.cpp), not through the ARAM queue.
//  - The stream player's disc and DMA I/O (lifted from the old port's audio_strm.cpp): it must run through ready ->
//    playing -> ended whether or not a stream is heard, since scenario code waits on it. Its reads are NOT performed
//    (nothing touches the disc in play: the GameCube ADPCM it would read feeds a GameCube ring no build plays) and its
//    completions are delivered at the next audio frame, before the driver runs, as the GameCube interrupt would; its
//    voices' positions advance in real time (snd_strm_advance), so a stream plays for its length and ends.
//  - Services the driver reaches that the engine does not serve yet, each a logged stub counted by e1_stub_hit
//    (weak: an image that hosts or serves the real one keeps it): the floor-attribute query (FlrAtCheck: footstep
//    material, the floor's BGM volume areas), area volumes (AreaHitCheck), the foot and water effects, the room's
//    timed sound areas (SeAtCheck, se_at.cpp: not hosted).
//  - The room save record the driver reads its room BGM and stream numbers from (cRoomData::getRoomSavePtr), weak:
//    the fight and boss images have their own (fight/fight_stubs.cpp, boss/boss_stubs.cpp).
#include <kos.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include "global.h"
#include "room_data.h"

#include "e1_engine.h"

typedef void (*ARQCallback)(u32);
extern "C" {
void cb_dvd_read_end(s32 result, void* info);   // snd_str2.cpp
void cb_aram_dma_end(u32 task);                 // snd_str2.cpp
}
#define WEAK __attribute__((weak))

// ---------------------------------------------------------------------------
// OS
extern "C" {
WEAK int OSDisableInterrupts(void) { return irq_disable(); }
WEAK int OSRestoreInterrupts(int level) { irq_restore(level); return level; }
WEAK int OSEnableInterrupts(void) { const int old = irq_disable(); irq_enable(); return old; }
WEAK u32 OSGetSoundMode(void) { return 1; }   // stereo
WEAK void OSSetSoundMode(u32) {}
WEAK void DCFlushRange(void*, u32) {}
WEAK void OSPanic(const char* file, int line, const char* msg, ...)
{
    e1_log("E1 SOUND driver OSPanic %s(%d): %s\n", file ? file : "?", line, msg ? msg : "?");
    for (;;) thd_sleep(1000);
}
}

// ---------------------------------------------------------------------------
// ARAM: addresses only (src/lib/ar.c's stack allocator over the GameCube's 16 MB, as the old port's audio_stub.cpp)
namespace {
const u32 kAramSize = 0x1000000;
u32* g_aramBlockLength;
u32 g_aramFreeBlocks, g_aramNext = 0x4000;
int g_aramInit;

struct Pend { void (*dvd)(s32, void*); ARQCallback arq; void* obj; s32 res; };
Pend g_pend[8];
u32 g_pendN;
void pend_push(const Pend& p)
{
    const int old = irq_disable();
    const bool ok = g_pendN < 8;
    if (ok) g_pend[g_pendN++] = p;
    irq_restore(old);
    if (!ok) {   // cannot happen with 4 stream works (one read + one DMA each): complete now
        if (p.dvd) p.dvd(p.res, p.obj);
        else p.arq((u32) p.obj);
    }
}
inline u32 nib_to_sample(u32 nib, u32 frame)
{
    u32 r = nib - frame;
    u32 in = r & 15;
    return (r >> 4) * 14 + (in >= 2 ? in - 2 : 0);
}
}  // namespace

extern "C" {
u32 ARInit(u32* stack, u32 n)
{
    if (g_aramInit) return 0x4000;
    g_aramNext = 0x4000;
    g_aramFreeBlocks = n;
    g_aramBlockLength = stack;
    g_aramInit = 1;
    return g_aramNext;
}
u32 ARGetBaseAddress(void) { return 0x4000; }
u32 ARGetSize(void) { return kAramSize; }
u32 ARAlloc(u32 len)
{
    const int old = irq_disable();
    len = (len + 31) & ~31u;
    if (!g_aramInit || g_aramFreeBlocks == 0 || len > kAramSize - g_aramNext) {
        irq_restore(old);
        e1_log("E1 SOUND ARAlloc(%lu) refused\n", (unsigned long) len);
        return 0;
    }
    const u32 a = g_aramNext;
    g_aramNext += len;
    *g_aramBlockLength++ = len;
    g_aramFreeBlocks--;
    irq_restore(old);
    return a;
}
void ARQInit(void) {}
struct ARQRequestView { ARQRequestView* next; u32 owner, type, priority, source, dest, length; ARQCallback callback; };
void ARQPostRequest(void* req, u32 owner, u32 type, u32 prio, u32 src, u32 dst, u32 len, ARQCallback cb)
{
    ARQRequestView* r = (ARQRequestView*) req;
    r->next = NULL;
    r->owner = owner;
    r->type = type;
    r->priority = prio;
    r->source = src;
    r->dest = dst;
    r->length = len;
    r->callback = cb;
    if (cb == cb_aram_dma_end) { pend_push(Pend{ nullptr, cb, req, 0 }); return; }   // the stream player's
    if (cb) cb((u32) req);
}

// The stream player's disc file: opened, read and closed without the disc (see the head of this file).
int DVDOpen(const char* name, void* fi)
{
    (void) name;
    memset(fi, 0, 0x3C);
    return 1;
}
int DVDClose(void* fi) { (void) fi; return 1; }
s32 DVDReadAsyncPrio(void* fi, void* addr, s32 length, s32 offset, void (*cb)(s32, void*), s32 prio)
{
    (void) addr; (void) offset; (void) prio;
    u8* f = (u8*) fi;
    *(s32*) (f + 0x0C) = 1;   // DVDFileInfo cb.state: DVD_STATE_BUSY until the completion
    *(u32*) (f + 0x20) = 0;   // cb.transferredSize
    pend_push(Pend{ cb, nullptr, fi, length });
    return 1;
}
int DVDCancelAsync(void* block, void* cb) { (void) cb; *(s32*) ((u8*) block + 0x0C) = 0; return 1; }
s32 DVDGetCommandBlockStatus(void* block) { return *(s32*) ((u8*) block + 0x0C); }

// The start of every audio frame, before the driver (aica.cpp audio_step): the stream player's completions.
void snd_pend_run(void)
{
    Pend run[8];
    const int old = irq_disable();
    const u32 n = g_pendN;
    memcpy(run, g_pend, n * sizeof(Pend));
    g_pendN = 0;
    irq_restore(old);
    for (u32 i = 0; i < n; i++) {
        if (run[i].dvd) {
            u8* fi = (u8*) run[i].obj;
            *(s32*) (fi + 0x0C) = 0;             // DVD_STATE_END
            *(u32*) (fi + 0x20) = (u32) run[i].res;
            run[i].dvd(run[i].res, run[i].obj);
        } else {
            run[i].arq((u32) run[i].obj);
        }
    }
}

// Moves a stream voice's AXPBADDR (u16 loopFlag, format, loop Hi/Lo, end Hi/Lo, current Hi/Lo) on by `samples`
// (fraction kept in *frac). 1 = it ran past its end address without a loop: the voice has stopped.
int snd_strm_advance(u16* a, float samples, float* frac)
{
    *frac += samples;
    u32 n = (u32) *frac;
    if (!n) return 0;
    *frac -= (float) n;
    u32 nib = ((u32) a[6] << 16) | a[7];
    const u32 end = ((u32) a[4] << 16) | a[5];
    const u32 lp = ((u32) a[2] << 16) | a[3];
    int stopped = 0;
    for (int guard = 0; n && guard < 16; guard++) {
        u32 r = nib & 15;
        if (r < 2) { nib = (nib & ~15u) + 2; r = 2; }   // frame header nibbles hold no sample
        const u32 frame = nib & ~15u;
        if (end < nib) {
            if (a[0]) { nib = lp; continue; }
            stopped = 1;
            break;
        }
        const u32 to_end = nib_to_sample(end, frame) + 1 - (r - 2);   // samples up to and including end
        const u32 k = n < to_end ? n : to_end;
        const u32 s = (r - 2) + k;
        nib = frame + (s / 14) * 16 + 2 + s % 14;
        n -= k;
        if (k == to_end) {
            if (a[0]) nib = lp;
            else { stopped = 1; break; }
        }
    }
    a[6] = (u16) (nib >> 16);
    a[7] = (u16) nib;
    return stopped;
}

// ---------------------------------------------------------------------------
// The driver's platform hooks (services/sound/host/re4dc_platform.h).
struct Re4dcMemLayout { unsigned long arena_lo, arena_hi, dvd, sound, core, option, player, weapon, heap, heap_end; };
Re4dcMemLayout re4dc_mem;   // sound: unused (the engine boots the driver itself, snd_svc.cpp)
void re4dc_log(const char* fmt, ...)
{
    char b[192];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(b, sizeof b, fmt, ap);
    va_end(ap);
    e1_log("E1 SOUND driver: %s", b);
}
void re4dc_watch_set(const void*, unsigned long) {}

// ---------------------------------------------------------------------------
// Services the driver reaches that the engine does not serve yet: logged stubs (weak).
WEAK void* pFlrSys;
}  // extern "C"
WEAK void SeAtCheck() { e1_stub_hit("SeAtCheck", 0); }
WEAK void SeAtInit() { e1_stub_hit("SeAtInit", 0); }
struct FlrAt;
WEAK FlrAt* FlrAtCheck(int type, Vec*, int) { e1_stub_hit("FlrAtCheck", type); return 0; }
WEAK int AreaHitCheck(void*, Vec*) { e1_stub_hit("AreaHitCheck", 0); return 0; }
WEAK void EspFootCall(int no, int, Vec*) { e1_stub_hit("EspFootCall", no); }
WEAK int EspPlWaterCall(int no, Vec*) { e1_stub_hit("EspPlWaterCall", no); return 0; }
// The room save record (weak: the fight and boss images keep theirs). snd_svc.cpp fills its BGM and stream words
// from the BGM table at room load, as SndBgmTblInit does for every room at game start.
static u8 snd_room_save[0x100] __attribute__((aligned(4)));
WEAK u8* cRoomData::getRoomSavePtr(u16 room) { (void) room; return snd_room_save; }
// the object itself: zeroed storage under its symbol (no constructor runs), as host/e1_stubs.cpp's STORAGE
__attribute__((weak, aligned(32))) unsigned char snd_RoomData[sizeof(cRoomData)] asm("_RoomData");
