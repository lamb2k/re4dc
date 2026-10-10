// DVD interface over the KOS file system: the game's disc tree lives under
// /cd/ with the GameCube paths (lower-cased); entry numbers index a table of
// paths the game asked for; reads are performed synchronously and complete
// through the SDK callback. The source queue-step guard below keeps competing
// source pumps from re-entering its synchronous read before step bookkeeping.
#include <kos.h>
#include <stdio.h>
#include <string.h>
#include <ctype.h>
#include <errno.h>

#include "re4dc_platform.h"
#include "native_io.h"
#ifndef RE4DC_IO_PROBE
#define RE4DC_IO_PROBE 0
#endif
#ifndef RE4DC_DVD_WAIT
#define RE4DC_DVD_WAIT 0
#endif
#ifndef RE4DC_DVD_FDCACHE
#define RE4DC_DVD_FDCACHE 0
#endif
#if RE4DC_DVD_WAIT
#include <kos/genwait.h>
#endif

namespace {
void* dvd_step_owner;
kthread_t* dvd_step_thread;
unsigned dvd_step_depth;
}
extern "C" void* re4dc_dvd_step_begin(){
    const int irq=irq_disable();
    if(dvd_step_owner && dvd_step_thread!=thd_current){
#if RE4DC_DVD_WAIT
        // Check and block atomically (IRQs off); woken when the owner's depth reaches 0, or
        // after 10 ms at most. The caller retries as before.
        genwait_wait(&dvd_step_depth,"dvd_step",10);
        irq_restore(irq);return nullptr;
#else
        irq_restore(irq);thd_sleep(1);return nullptr;
#endif
    }
    // The outer borrow protects shared header save/use/restore. Individual
    // source Read steps on that same thread may enter it recursively. A
    // competing pump yields; IRQs remain enabled while native I/O is active.
    void* token=re4dc_io_begin();
    if(!dvd_step_owner){dvd_step_owner=token;dvd_step_thread=thd_current;}
    ++dvd_step_depth;
    irq_restore(irq);
    return token;
}
extern "C" void re4dc_dvd_step_end(void* token){
    const int irq=irq_disable();
    if(!token || dvd_step_owner!=token || dvd_step_thread!=thd_current || !dvd_step_depth){
        re4dc_missing("DVD source-step owner mismatch");irq_restore(irq);return;
    }
    if(--dvd_step_depth==0){
        dvd_step_owner=nullptr;dvd_step_thread=nullptr;
#if RE4DC_DVD_WAIT
        genwait_wake_all(&dvd_step_depth);
#endif
    }
    re4dc_io_end(token);irq_restore(irq);
}

typedef signed char s8;
typedef unsigned char u8;
typedef signed long s32;
typedef unsigned long u32;
typedef int BOOL;

struct DVDDiskID {
    char gameName[4];
    char company[2];
    u8 diskNumber;
    u8 gameVersion;
    u8 streaming;
    u8 streamingBufSize;
    u8 padding[22];
};

struct DVDCommandBlock;
typedef void (*DVDCBCallback)(s32 result, DVDCommandBlock* block);
struct DVDCommandBlock {
    DVDCommandBlock* next;
    DVDCommandBlock* prev;
    u32 command;
    s32 state;
    u32 offset;
    u32 length;
    void* addr;
    u32 currTransferSize;
    u32 transferredSize;
    DVDDiskID* id;
    DVDCBCallback callback;
    void* userData;
};

struct DVDFileInfo;
typedef void (*DVDCallback)(s32 result, DVDFileInfo* fileInfo);
struct DVDFileInfo {
    DVDCommandBlock cb;
    u32 startAddr;
    u32 length;
    DVDCallback callback;
};

enum { DVD_STATE_END = 0, DVD_STATE_BUSY = 1, DVD_RESULT_FATAL = -1, DVD_RESULT_CANCELED = -3 };

#define MAX_ENTRIES 512
static char g_entryPath[MAX_ENTRIES][64];
static s32 g_entrySize[MAX_ENTRIES];  // -1: not on the disc
static int g_entryCount;
static DVDDiskID g_diskId = {{'G', '4', 'B', 'E'}, {'0', '8'}, 0, 0, 0, 0, {0}};
static const char* g_root = "/cd/";

#if RE4DC_IO_PROBE
// Time a game thread spent blocked on a source DVD read (the whole synchronous read, or
// with DISC_ASYNC the wait for an overlapped read to land). Door-transition telemetry.
static unsigned g_blockN, g_blockWorst;
static unsigned long long g_blockTotal;
static void note_block(unsigned long long us)
{
    ++g_blockN; g_blockTotal += us; if (us > g_blockWorst) g_blockWorst = (unsigned) us;
}
extern "C" void re4dc_dvd_block_stats(unsigned* n, unsigned long long* total_us, unsigned* worst_us, int reset)
{
    *n = g_blockN; *total_us = g_blockTotal; *worst_us = g_blockWorst;
    if (reset) { g_blockN = 0; g_blockTotal = 0; g_blockWorst = 0; }
}
#endif


static void normalise(const char* in, char* out, size_t n)
{
    size_t i = 0;
    while (*in == '/' || *in == '\\') in++;
    for (; *in && i + 1 < n; in++) {
        char c = *in;
        if (c == '\\') c = '/';
        out[i++] = (char) tolower((unsigned char) c);
    }
    out[i] = 0;
}

#if RE4DC_SBB_STUB
// SBB_STUB=1: the GC stream banks need not be on the disc. The recovered stream player (src/game/snd_str*.cpp)
// still opens them (DVDOpen in Snd_str_init; SndStrReq refuses a stream whose FileTbl entry is -1), but its only
// reads go through __wrap_DVDReadAsyncPrio (platform/audio_strm.cpp), which never touches the file; the stream
// headers (lengths, loop points, rates) come from bgm/bio4str.hed, and the heard audio from bgm/aica_str.dat.
// The entry keeps the retail file size, so DVDFileInfo.length is the value the file would give.
static s32 sbbStubSize(const char* rel)
{
    if (strcmp(rel, "bgm/bio4bgm.sbb") == 0) return 139395072;
    if (strcmp(rel, "bgm/bio4evt.sbb") == 0) return 193495040;
    return -1;
}
#endif

static s32 fileSize(const char* rel)
{
#if RE4DC_SBB_STUB
    const s32 stub = sbbStubSize(rel);
    if (stub >= 0) return stub;
#endif
    Re4dcIoScope io;
    char full[96];
    snprintf(full, sizeof(full), "%s%s", g_root, rel);
    re4dc_set_stage(0x2000);
    file_t f = fs_open(full, O_RDONLY);
    re4dc_set_stage(0x2001);
    if (f < 0) {
        return -1;
    }
    s32 size = (s32) fs_total(f);
    re4dc_set_stage(0x2002);
    fs_close(f);
    re4dc_set_stage(0x2003);
    return size;
}

#if RE4DC_WEAPON_HEAP4
// WEAPON_HEAP4: the MRAM bytes a DRS read places (type-0 parts, each rounded to 32, as cDvdQueue sizes an
// allocated destination), from the part table after the 32-byte file header; 0 when unreadable.
extern "C" unsigned re4dc_dvd_mram_parts(const char* rel)
{
    Re4dcIoScope io;
    char full[96];
    static unsigned char head[2048] __attribute__((aligned(32)));
    snprintf(full, sizeof(full), "%s%s", g_root, rel);
    file_t f = fs_open(full, O_RDONLY);
    if (f < 0) {
        return 0;
    }
    const ssize_t got = fs_read(f, head, sizeof(head));
    fs_close(f);
    unsigned total = 0;
    for (unsigned at = 32; got > 0 && at + 32 <= (unsigned) got; at += 32) {
        const unsigned* h = (const unsigned*) (head + at);
        if (h[0] == 0xFFFFFFFFu) {
            return total;
        }
        if (h[0] == 0) {
            total += (h[1] + 31) & ~31u;
        }
    }
    return 0;
}
#endif

extern "C" {

void re4dc_dvd_set_root(const char* root) { g_root = root; }

int re4dc_dvd_native_path(const char* name, char* output, unsigned capacity)
{
    if (!name || !output || !capacity) return 0;
    const int n = snprintf(output, capacity, "%s%s", g_root, name);
    return n >= 0 && (unsigned) n < capacity;
}

s32 DVDConvertPathToEntrynum(const char* path)
{
    char rel[64];
    normalise(path, rel, sizeof(rel));
    for (int i = 0; i < g_entryCount; i++) {
        if (strcmp(g_entryPath[i], rel) == 0) {
            return g_entrySize[i] >= 0 ? i : -1;
        }
    }
    if (g_entryCount >= MAX_ENTRIES) {
        re4dc_log("DVDConvertPathToEntrynum: table full (%s)\n", rel);
        return -1;
    }
    int i = g_entryCount++;
    strcpy(g_entryPath[i], rel);
    g_entrySize[i] = fileSize(rel);
    if (g_entrySize[i] < 0) {
        re4dc_log("dvd: not on disc: %s\n", rel);
        return -1;
    }
    return i;
}

BOOL DVDFastOpen(s32 entrynum, DVDFileInfo* fi)
{
    if (entrynum < 0 || entrynum >= g_entryCount || g_entrySize[entrynum] < 0) {
        return 0;
    }
    memset(fi, 0, sizeof(*fi));
    fi->startAddr = (u32) entrynum;  // the entry doubles as the "disc offset"
    fi->length = (u32) g_entrySize[entrynum];
    fi->cb.state = DVD_STATE_END;
    return 1;
}

BOOL DVDOpen(const char* fileName, DVDFileInfo* fi)
{
    return DVDFastOpen(DVDConvertPathToEntrynum(fileName), fi);
}

BOOL DVDClose(DVDFileInfo* fi)
{
    fi->cb.state = DVD_STATE_END;
    return 1;
}

#if RE4DC_IO_PROBE
// Test-only DVD hold (see src/game/dvd.cpp cDvdQueue::Read): per-door source read frame offsets.
#include <stdlib.h>
extern "C" unsigned re4dc_fixture_source_frame(void);
extern "C" int re4dc_fixture_read(const char* path, char* buffer, unsigned size);
namespace {
unsigned hold_f0, hold_reads, hold_n, hold_tgt[512];   // one target per source read, all doors in order
bool hold_on, hold_loaded;
}
extern "C" void re4dc_dvdhold_begin(void)
{
    if (!hold_loaded) {
        hold_loaded = true;
        static char t[3072];
        const int n = re4dc_fixture_read("/cd/dc/dvdhold.txt", t, sizeof(t) - 1);
        if (n > 0) {
            t[n] = 0;
            for (char* p = t; *p && hold_n < 512;) {
                while (*p == ' ' || *p == '\n' || *p == '\r' || *p == '\t') ++p;
                if (!*p) break;
                hold_tgt[hold_n++] = (unsigned) strtoul(p, &p, 10);
            }
            re4dc_log("dvdhold: %u targets\n", hold_n);
        }
    }
    hold_f0 = re4dc_fixture_source_frame(); hold_on = true;
}
extern "C" void re4dc_dvdhold_end(void) { hold_on = false; }
extern "C" int re4dc_dvdhold(void)
{
    // Held like a contended step (re4dc_dvd_step_begin): yield, so a pumping thread cannot starve the frame.
    // A queue drained inside one frame (MemorySwap: while (chk(0x20)) Read()) cannot reach a later frame:
    // a hold that sees no frame advance for 100 ms releases that request (faster units reach it earlier).
    static unsigned held_frame = ~0U, held_read = ~0U;
    static unsigned long long held_t0;
    const unsigned f = re4dc_fixture_source_frame();
    if (hold_on && hold_reads < hold_n && f - hold_f0 < hold_tgt[hold_reads]) {
        const unsigned long long now = timer_us_gettime64();
        if (f != held_frame || hold_reads != held_read) { held_frame = f; held_read = hold_reads; held_t0 = now; }
        else if (now - held_t0 > 100000) {
            re4dc_log("dvdhold: drain release read=%u df=%u target=%u\n", hold_reads, f - hold_f0, hold_tgt[hold_reads]);
            return 0;
        }
        thd_sleep(1);
        return 1;
    }
    return 0;
}
#endif

#if RE4DC_DVD_FDCACHE
// Two open source files ({entry, fd}, least recently used first out). Held under fd_lock for the
// whole seek + read; a thread that finds it held reads the old way (its own open/close).
namespace {
struct FdSlot { int entry; file_t fd; unsigned used; };
FdSlot fd_slots[2] = {{-1, FILEHND_INVALID, 0}, {-1, FILEHND_INVALID, 0}};
unsigned fd_clock;
mutex_t fd_lock = MUTEX_INITIALIZER;
file_t fd_cached(int entry, const char* full)
{
    FdSlot* slot = nullptr;
    for (auto& s : fd_slots) if (s.entry == entry && s.fd != FILEHND_INVALID) { slot = &s; break; }
    if (!slot) {
        slot = fd_slots[0].used <= fd_slots[1].used ? &fd_slots[0] : &fd_slots[1];
        if (slot->fd != FILEHND_INVALID) fs_close(slot->fd);
        slot->fd = fs_open(full, O_RDONLY);
        slot->entry = slot->fd != FILEHND_INVALID ? entry : -1;
    }
    slot->used = ++fd_clock;
    return slot->fd;
}
void fd_drop(file_t f)
{
    for (auto& s : fd_slots) if (s.fd == f) { fs_close(f); s.fd = FILEHND_INVALID; s.entry = -1; }
}
}
#endif

#if RE4DC_IO_SERIAL
// IO_SERIAL: DVDReadAsyncPrio's file is open (a KOS CD stream may be running on it). Other threads' package
// opens wait for it to close (re4dc_io_serial_wait); the DVD thread itself never waits.
static volatile int g_dvd_reading;
static kthread_t* volatile g_dvd_reader;
extern "C" void re4dc_io_serial_wait(void)
{
    while (g_dvd_reading && g_dvd_reader != thd_current) thd_pass();
}
struct DvdReading {
    DvdReading() { g_dvd_reader = thd_current; ++g_dvd_reading; }
    ~DvdReading() { if (--g_dvd_reading == 0) g_dvd_reader = nullptr; }
};
#endif

s32 DVDReadAsyncPrio(DVDFileInfo* fi, void* addr, s32 length, s32 offset, DVDCallback callback, s32 prio)
{
    Re4dcIoScope io;  // includes callback completion before cancellation can drain
#if RE4DC_IO_SERIAL
    DvdReading reading;
#endif
    (void) prio;
    int entry = (int) fi->startAddr;
    char full[96];
    snprintf(full, sizeof(full), "%s%s", g_root, g_entryPath[entry]);
    fi->cb.addr = addr;
    fi->cb.offset = (u32) offset;
    fi->cb.length = (u32) length;
    fi->cb.state = DVD_STATE_BUSY;
    fi->cb.currTransferSize = (u32) length;
    fi->cb.transferredSize = 0;
    fi->callback = callback;
#if RE4DC_IO_PROBE
    const unsigned long long io_t0 = timer_us_gettime64();
    if (hold_on) re4dc_log("dvdhold: read=%u df=%u\n", hold_reads++, re4dc_fixture_source_frame() - hold_f0);
#endif
    s32 result = DVD_RESULT_FATAL;
#if RE4DC_DVD_FDCACHE
    const bool cached = mutex_trylock(&fd_lock) == 0;
    file_t f = cached ? fd_cached(entry, full) : fs_open(full, O_RDONLY);
#else
    file_t f = fs_open(full, O_RDONLY);
#endif
    if (f >= 0) {
        s32 avail = (s32) fi->length - offset;
        if (avail < 0) avail = 0;
        s32 want = length < avail ? length : avail;
        fs_seek(f, offset, SEEK_SET);
        s32 got = 0;
        while (got < want) {
            ssize_t r = fs_read(f, (u8*) addr + got, (size_t) (want - got));
            if (r <= 0) {
                break;
            }
            got += (s32) r;
        }
#if RE4DC_DVD_FDCACHE
        if (!cached) fs_close(f);
        else if (got != want) fd_drop(f);   // a failed read never leaves a suspect fd cached
#else
        fs_close(f);
#endif
        // The SDK reports the requested (32-byte aligned) length on success.
        result = got == want ? length : got;
        if (got != want) {
            static unsigned short_reads;
            if (++short_reads <= 8)
                re4dc_log("DVDReadAsyncPrio: short read %s got=%d want=%d offset=%d errno=%d\n", full, (int) got,
                          (int) want, (int) offset, errno);
        }
    } else {
        re4dc_log("DVDReadAsyncPrio: open failed %s errno=%d\n", full, errno);
    }
#if RE4DC_DVD_FDCACHE
    if (cached) mutex_unlock(&fd_lock);
#endif
#if RE4DC_IO_PROBE
    { const unsigned long long io_t1 = timer_us_gettime64(); note_block(io_t1 > io_t0 ? io_t1 - io_t0 : 0); }
#endif
    fi->cb.transferredSize = result > 0 ? (u32) result : 0;
    fi->cb.state = DVD_STATE_END;
    if (callback) {
        callback(result, fi);
    }
    return 1;
}

s32 DVDGetTransferredSize(DVDFileInfo* fi) { return (s32) fi->cb.transferredSize; }
s32 DVDGetCommandBlockStatus(const DVDCommandBlock* block) { return block->state; }
s32 DVDGetDriveStatus(void) { return 0; }  // DVD_STATE_END: ready
void* DVDGetFSTLocation(void)
{
    // dvd.cpp Init computes FstSize = SimulatedMemSize - (fst - 0x80000000); give it 1 MB.
    return (void*) (0x80000000u + 0x01800000u - 0x100000u);
}

int DVDCancelAsync(DVDCommandBlock* block, DVDCBCallback callback)
{
    block->state = DVD_STATE_END;
    if (callback) {
        callback(0, block);
    }
    return 1;
}

s32 DVDCancelAll(void)
{
    return 0;
}

DVDDiskID* DVDGetCurrentDiskID(void) { return &g_diskId; }

DVDDiskID* DVDGenerateDiskID(DVDDiskID* id, const char* game, const char* company, u8 diskNum, u8 version)
{
    memset(id, 0, sizeof(*id));
    memcpy(id->gameName, game, 4);
    memcpy(id->company, company, 2);
    id->diskNumber = diskNum;
    id->gameVersion = version;
    return id;
}

int DVDCompareDiskID(const DVDDiskID* a, const DVDDiskID* b)
{
    if (memcmp(a->gameName, b->gameName, 4) != 0) return 0;
    if (memcmp(a->company, b->company, 2) != 0) return 0;
    if (a->diskNumber != b->diskNumber) return 0;
    if (b->gameVersion != 0xFF && a->gameVersion != b->gameVersion) return 0;
    return 1;
}

int DVDChangeDiskAsync(DVDCommandBlock* block, DVDDiskID* id, DVDCBCallback callback)
{
    re4dc_log("DVDChangeDiskAsync: disc %d requested (single-disc build)\n", id->diskNumber);
    block->state = DVD_STATE_END;
    if (callback) {
        callback(0, block);
    }
    return 1;
}


// GD-ROM is the source's ARAM tier (datactrl.cpp): a unit staged "in ARAM" keeps no
// copy; when the source brings it back to MRAM its own disc file is read straight
// into the MRAM destination, blocking the caller like a synchronous ARAM DMA.
int re4dc_aram_file_read(const char* name, void* dst, unsigned bytes)
{
    const uint64_t start = timer_us_gettime64();
    char path[128];
    int ok = 0;
    if (dst && bytes && re4dc_dvd_native_path(name, path, sizeof(path))) {
        Re4dcIoScope io;
        file_t f = fs_open(path, O_RDONLY);
        if (f >= 0) {
            ok = fs_total(f) >= (ssize_t) bytes;
            unsigned char* p = (unsigned char*) dst;
            unsigned n = bytes;
            while (ok && n) {
                const ssize_t got = fs_read(f, p, n);
                if (got <= 0 || (unsigned) got > n) {
                    ok = 0;
                } else {
                    p += got;
                    n -= (unsigned) got;
                }
            }
            fs_close(f);
        }
    }
    const uint64_t us = timer_us_gettime64() - start;
    re4dc_log("aram file: read %s bytes=%u wait_us=%lu success=%d\n", name, bytes,
              (unsigned long) (us > 0xffffffffULL ? 0xffffffffULL : us), ok);
    return ok;
}

}  // extern "C"
