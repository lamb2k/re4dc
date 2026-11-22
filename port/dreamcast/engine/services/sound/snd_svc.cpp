// The engine's sound service (lane eng-snd1, integrator ruling H-025.1).
//
// The original game's sound driver (src/game/snd*.cpp) is hosted unchanged under the recorded waiver H-025.1; this
// service is the engine around it:
//  - BOOT (once, before play): the driver's work and the four sound system files (bgm/bio4str.hed, bio4midi.hed,
//    doorse.hed, bgmtbl.dat) read by the engine, then the driver started (its own SndDriverInit: the AICA layer,
//    aica.cpp, and its 5 ms callback). The engine's composition of the original SndInit / SndInit2: same work, the
//    files read here instead of through the GameCube read queue, no 128 KB of GameCube stream buffers (the stream
//    player's reads are not performed, snd_host.cpp).
//  - ROOM LOAD (with the room, before play): every sound block the scene uses - CORE (etc/core.das), PL (the
//    player's archive), WEP (the handgun's), ROOM and FOOT (st<n>/r<room>.dar), the hosted enemies' and partner's
//    blocks (their em archives), and the room's BGM (bgm/bio4midi.dat, through the driver's own SndRoomBgmLoad) - read
//    part by part as the original read queue does (dvd.cpp readMain: MRAM part to the block, ARAM part to the sound
//    chip), only the converted image of each ARAM part (not its GameCube padding), then registered with the driver
//    (SndBlkInit). The room's sound header (STB) is read from the room archive and handed to the driver's
//    SndRoomStartInit; then the room's BGM and stream starts, as the original's room init.
//  - TICK (once a tick, after drawing, before the pacer's wait: where the original main loop calls it, after Trans):
//    the driver's game-frame work, SndWatcher.
//  - THE 5 ms AUDIO FRAME: its own KOS thread (aica.cpp, priority 3, above the main thread), every 5 ms; each step
//    (at most two driver frames, the voices' positions, the register flush) runs with interrupts off, so it is one
//    piece, as the GameCube's audio interrupt was. It is not the pacer and does not touch it: the pacer waits on the
//    display's field count (core/frame.cpp), which the vblank interrupt keeps; a step delays that interrupt by at
//    most its own length (the report's "longest step"); the hosted driver's calls from the game run with interrupts
//    off so a step never runs inside them. What it costs is CPU time taken from whatever runs then, and that is what
//    this service counts.
//  - COST (the waiver's ceiling): every microsecond the sound work takes - the audio steps (driver frames and register
//    flush), the tick's SndWatcher, the game's calls into the driver (SndCall, SndStop) and the loads none (they are
//    before play) - is added to the picture it falls in (e1_tick). The report's E1 SOUND line gives the mean and the
//    worst over pictures 41-640 (the selector's window); the selector fails a timing scene over 1.0 ms mean or
//    2.0 ms worst (loader/selector.c).
//  - REQUESTS: every SndCall and SndStop the hosted behaviour makes is a request; in a traced run (no NOTRACE file)
//    each goes into the trace as an SR line (tick, Frame_cnt, kind, block, number, flags, id, position bits), the same
//    fields the PC reference logs (hostref/host_stubs.cpp), for services/sound/tools/sndreq_check.py.
//  - OUTPUT: every audio step reads back one channel the layer owns through the AICA's own channel monitor (aica.cpp
//    probe_step: key on, attenuation, envelope level, current sample address); the report's E1 SOUND PROBE line counts
//    the samples keyed on, audible (envelope above silence, attenuation below total) and moving (the address changed
//    since that channel's previous sample).
// Lab arms (boot files read before play; never build switches): SNDOFF (no sound: the driver is not started, the
// requests are counted and answered 0), SNDMUTE (control of the output check: every channel at total attenuation),
// SNDSLOW (control of the cost ceiling: 1,500 us busy inside every 5 ms audio step), SNDDROP (control of the request
// check: the first SndCall from tick 100 on is not passed to the driver and not logged).
// Hooks into the engine core: game/sound.mk wraps three core functions (e1_load_room, e1_fields_late, e1_report) so
// that no core file changes in this lane; the hand-back asks the integrator to make them three direct calls.
#include <kos.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include "global.h"
#include "main.h"
#include "player.h"
#include "room_data.h"
#define SND_SDK_NO_GX
#define SND_DRV_GAME_API
#include "snd.h"
#include "../../core/e1_clock.h"   // lane eng-mem1: the engine clock for the sound spans (not KOS's)
#include "snd_drv.h"
#include "dvd.h"
#include "e1_engine.h"
#include "e1_core.h"
#include "aica.h"

extern "C" {
void __real__Z12e1_load_roomj(unsigned room);
void __real__Z14e1_fields_latej(unsigned tick);
void __real__Z9e1_reportv(void);
u32 __real__Z7SndCallttP3VeciiP5cUnit(u16 blk, u16 no, Vec* pos, int id, int vol, cUnit* obj);
int __real__Z7SndStopmi(u32 id, int time);
}

namespace {

// ---------------------------------------------------------------------------
// The audio thread's log lines go to a ring printed with the report (the engine log is the main thread's).
unsigned g_tlog_lost;   // the audio thread's log lines, counted
kthread_t* g_main_thread;

// ---------------------------------------------------------------------------
// Per-picture cost (us) and the counters of the report line.
const unsigned kPics = E1_TICKS;
uint32_t g_cost[kPics];
// the picture's split (diagnosis of the worst picture): the audio steps' time, their count and the longest one, and
// the main thread's (the game's calls, SndWatcher)
uint16_t g_cost_main[kPics], g_steps[kPics], g_step_max[kPics];
uint32_t g_voices_peak, g_notes_peak;
uint32_t g_requests, g_stops, g_dropped;
uint32_t g_banks, g_banks_missing, g_load_us, g_load_bytes;
int g_on, g_booted, g_trace = -1, g_drop;
char g_missing[96];

inline unsigned pic_now() { const uint32_t t = e1_tick; return t % kPics; }
inline void cost_add(uint32_t us) { g_cost[pic_now()] += us; }
inline void main_add(uint32_t us)
{
    const unsigned k = pic_now();
    g_cost[k] += us;
    g_cost_main[k] = (uint16_t) (g_cost_main[k] + (us > 65535 ? 65535 : us));
}
// A main-thread measurement (the game's call into the driver, the tick's SndWatcher): wall time less what the audio
// thread took meanwhile (it preempts the main thread; its steps are counted by the step hook).
struct MainSpan {
    uint64_t t0;
    uint32_t busy0;
    MainSpan() : t0(e1_clock_us()), busy0(aica_busy_us) {}
    uint32_t us() const
    {
        const uint32_t wall = (uint32_t) (e1_clock_us() - t0), other = aica_busy_us - busy0;
        return wall > other ? wall - other : 0;
    }
};

int boot_file(const char* n)
{
    file_t f = fs_open(n, O_RDONLY);
    if (f < 0) return 0;
    fs_close(f);
    return 1;
}

// One audio step's cost and voices (aica.cpp's thread).
void step_hook(uint32_t us, uint32_t voices, uint32_t notes)
{
    const unsigned k = pic_now();
    g_cost[k] += us;
    if (g_steps[k] < 65535) ++g_steps[k];
    if (us > g_step_max[k]) g_step_max[k] = (uint16_t) (us > 65535 ? 65535 : us);
    if (voices > g_voices_peak) g_voices_peak = voices;
    if (notes > g_notes_peak) g_notes_peak = notes;
}

// ---------------------------------------------------------------------------
// Loading: a file's sound parts (dvd.cpp readMain's sound cases), read before play.
struct DvdRec { u32 type, size, dest, ofs, sndType, sndArg, sndNo, x1C; };
uint8_t* g_mram_owned[14];   // MRAM parts this service allocated (freed when the block is replaced)
uint8_t* g_chunk;            // 16 KB, allocated for a room load and freed after it
const u32 kChunk = 16 * 1024;

bool read_at(file_t f, u32 ofs, void* dst, u32 n)
{
    return fs_seek(f, ofs, SEEK_SET) == (off_t) ofs && fs_read(f, dst, n) == (ssize_t) n;
}

// The MRAM part of block t (the wavetable, the SE tables): a block of its own on the KOS heap.
bool load_mram(file_t f, int t, u32 ofs, u32 size)
{
    uint8_t* m = (uint8_t*) memalign(32, (size + 31) & ~31u);
    if (!m || !read_at(f, ofs, m, size)) {
        free(m);
        snprintf(g_missing + strlen(g_missing), sizeof(g_missing) - strlen(g_missing), " mram%d", t);
        return false;
    }
    if (g_mram_owned[t]) free(g_mram_owned[t]);
    g_mram_owned[t] = m;
    SndMem.blk_mram[t] = m;
    pSndRaw->blk_flag[0] &= ~(1u << t);   // dvd.cpp: a block being read is not loaded
    g_load_bytes += size;
    return true;
}

// The ARAM part of block t: its converted image to the sound chip (the header's `total` bytes after the 96-byte
// header; the GameCube padding after it is not read), then the block registered with the driver.
bool load_aram(file_t f, int t, const DvdRec& r, u32 ofs)
{
    switch (r.sndType) {   // dvd.cpp readMain case 2: the block's ARAM address
    case 8: case 5: case 6:
        SndMem.blk_aram[t] = pSndRaw->aram_base_addr;
        pSndRaw->aram_base_addr += (r.size + 31) & ~31u;
        break;
    case 3:
        pSndRaw->aram_base_addr_bgm -= (r.size + 31) & ~31u;
        SndMem.blk_aram[t] = pSndRaw->aram_base_addr_bgm;
        break;
    case 0: SndMem.blk_aram[0] = 0x4100; break;
    case 1: SndMem.blk_aram[1] = 0x44100; break;
    case 2: SndMem.blk_aram[2] = 0x174100; break;
    case 7: SndMem.blk_aram[7] = 0x1B4100; break;
    }
    UseAramSize[t] = (r.size + 0x1F) / 0x20 * 0x20;
    AicaBankHeader h;
    if (!read_at(f, ofs, &h, sizeof h)) return false;
    bool ok = aica_bank_place(t, SndMem.blk_aram[t], h);
    if (ok) {
        uint8_t* const buf = g_chunk ? g_chunk : (uint8_t*) memalign(32, kChunk);   // a read outside a room load
        for (u32 at = 0; buf && at < h.total;) {
            const u32 n = h.total - at < kChunk ? h.total - at : kChunk;
            if (!read_at(f, ofs + sizeof h + at, buf, (n + 3) & ~3u)) { ok = false; break; }
            aica_bank_copy(at, buf, n);
            at += n;
        }
        if (buf != g_chunk) free(buf);
        aica_bank_done();
        g_load_bytes += sizeof h + h.total;
    }
    SndBlkInit(r.sndType, r.sndArg, r.sndNo);   // dvd.cpp: the block registered once its ARAM part is in
    if (ok) ++g_banks;
    return ok;
}

// A file's header table at `base` (dvd.cpp DvdHeader, 32 bytes a record, from record 1): nested tables (type 4)
// walked, sound parts (type 1 MRAM, type 2 ARAM) loaded; the main data (type 0, 3) is the engine loader's.
void load_parts(file_t f, u32 base, int depth)
{
    DvdRec rec[32];   // 1 KB of stack (the loading thread is the main thread)
    if (depth > 2 || !read_at(f, base, rec, sizeof rec)) return;
    int no = -1;   // the enemy / BGM slot of the part pair (SndEmDataReadCheck / SndBgmDataReadCheck)
    for (int i = 1; i < 32; i++) {
        DvdRec& r = rec[i];
        if (r.type == 0xFFFFFFFFu) break;
        if (r.type == 0xFFFFFFFEu) continue;
        if (r.type == 4) { load_parts(f, base + r.ofs, depth + 1); continue; }
        if (r.type != 1 && r.type != 2) continue;
        int t = (int) r.sndType;
        if (r.type == 1) {
            no = -1;
            if (r.sndType == 8) {
                no = SndEmDataReadCheck(r.sndArg);
                if (no < 0) { ++i; continue; }   // "Snd File not Read": both parts skipped (loaded already, or full)
                t = no + 8;
            } else if (r.sndType == 3) {
                no = SndBgmDataReadCheck(r.sndArg);
                if (no < 0) { ++i; continue; }
                t = no + 3;
            }
            if (t < 0 || t >= 14) continue;
            load_mram(f, t, base + r.ofs, r.size);
        } else {
            if (r.sndType == 8 || r.sndType == 3) {
                if (no < 0) continue;
                r.sndNo = (u32) no;
                t = no + (r.sndType == 8 ? 8 : 3);
            }
            if (t < 0 || t >= 14) continue;
            load_aram(f, t, r, base + r.ofs);
        }
    }
}

bool load_file(const char* path, u32 base)
{
    file_t f = fs_open(path, O_RDONLY);
    if (f < 0) {
        ++g_banks_missing;
        snprintf(g_missing + strlen(g_missing), sizeof(g_missing) - strlen(g_missing), " %s", path + 4);
        e1_log("E1 SOUND load: missing %s (its sounds are silent)\n", path);
        return false;
    }
    load_parts(f, base, 0);
    fs_close(f);
    return true;
}

// A whole small file (the sound system files) on the KOS heap.
void* load_whole(const char* path, u32* size)
{
    void* p = e1_file_load(path, size, 32);
    if (!p) {
        ++g_banks_missing;
        snprintf(g_missing + strlen(g_missing), sizeof(g_missing) - strlen(g_missing), " %s", path + 4);
    } else {
        g_load_bytes += *size;
    }
    return p;
}

// The room's sound header (the room archive's STB sub-file) in a one-entry tagged archive of its own, which the
// driver's SndRoomStartInit reads through GetDataExt (the engine's room archive keeps only the sections the hosted
// behaviour reads).
uint8_t* g_stb_arc;
void load_stb(unsigned room)
{
    char path[48];
    snprintf(path, sizeof path, "/cd/st%u/r%03x.arc", room >> 8, room);
    file_t f = fs_open(path, O_RDONLY);
    if (f < 0) return;
    const u32 total = fs_total(f);
    u32 hdr[4 + 2 * 64];
    if (read_at(f, 0, hdr, 16) && hdr[0] && hdr[0] <= 64 && read_at(f, 0, hdr, 16 + 8 * hdr[0])) {
        const u32 num = hdr[0];
        const u32* offs = hdr + 4;
        const u8* tags = (const u8*) (hdr + 4 + num);
        for (u32 i = 0; i < num; i++) {
            if (memcmp(tags + 4 * i, "STB", 3)) continue;
            u32 end = total;
            for (u32 j = 0; j < num; j++) if (offs[j] > offs[i] && offs[j] < end) end = offs[j];
            const u32 len = end - offs[i];
            free(g_stb_arc);
            g_stb_arc = (uint8_t*) memalign(32, 0x20 + len);
            if (!g_stb_arc) break;
            memset(g_stb_arc, 0, 0x20);
            u32* a = (u32*) g_stb_arc;
            a[0] = 1;                            // one sub-file
            a[4] = 0x20;                         // its offset
            memcpy(g_stb_arc + 0x14, "STB", 4);  // its tag
            if (!read_at(f, offs[i], g_stb_arc + 0x20, len)) { free(g_stb_arc); g_stb_arc = 0; }
            else g_load_bytes += len;
            break;
        }
    }
    fs_close(f);
}

// The room's BGM and stream numbers in its save record, from the BGM table (SndBgmTblInit's rule for one room).
void room_bgm_record(unsigned room)
{
    SndBgmTbl* t = SndMem.bgm_tbl;
    if (!t) return;
    const u16* rl = (const u16*) ((u8*) t + t->list_ofs);
    for (int i = 0; *rl != 0xFFFF; rl++, i++) {
        if (*rl != room) continue;
        SndRoomSave* rs = (SndRoomSave*) RoomData.getRoomSavePtr((u16) room);
        if (!rs) return;
        u32* ofs = (u32*) ((u8*) t + t->room_ofs);
        SndBgmRoom* r = (SndBgmRoom*) ((u8*) ofs + ofs[i]);
        for (int j = 0; j < 6; j++) { rs->bgm[j] = r->e[0].bgm[j]; rs->str[j] = r->e[0].str[j]; }
        return;
    }
}

uint8_t g_str_scratch[64] __attribute__((aligned(32)));   // the stream player's buffers: never read or written

// The engine's SndInit / SndInit2: the driver's work and the sound system files, the driver started.
void driver_boot()
{
    pSndRaw = &Snd;
    static u32 aram_stack[3];
    ARInit(aram_stack, 3);
    ARAlloc(0x6FC000);
    ARQInit();
    memset(&Snd, 0, sizeof(SndWork));
    u32 len = 0;
    void* hed = load_whole("/cd/bgm/bio4str.hed", &len);
    if (hed) {
        for (int i = 0; i < 2; i++) {
            SndMem.str_file[i] = (SndStrFile*) ((u8*) hed + ((u32*) hed)[i]);
            Snd_str_blk_init(i, SndMem.str_file[i]);
        }
        str_flag = 1;
    } else {
        str_flag = 0;
    }
    SndMem.bgm_file = (u32*) load_whole("/cd/bgm/bio4midi.hed", &len);
    SndMem.door_tbl = (SndDoorTbl*) load_whole("/cd/bgm/doorse.hed", &len);
    SndMem.bgm_tbl = (SndBgmTbl*) load_whole("/cd/bgm/bgmtbl.dat", &len);
    ARAM_FREE_BASE = 0x800000;
    SndMem.mram_end = g_str_scratch;   // dvd.cpp's MRAM allocation tops (the engine allocates each part itself)
    for (int i = 0; i < 4; i++) SndMem.str_buf[i] = (u32) g_str_scratch;
    SndDriverInit();                   // hosted: AX / MIX / SYN up (aica.cpp), the 5 ms callback, master volumes
    pSys->sound_mode = Snd_get_sound_mode();
    // SndInit2 (game start), the room-table part done per room (room_bgm_record)
    memset(pSndRaw, 0, sizeof(SndWork));
    pSndRaw->mram_top = SndMem.mram_end;
    pSndRaw->aram_base_addr = 0x1F4100;
    for (int i = 0; i < 6; i++) pSndRaw->snd_em_id[i] = 0xFF;
    pSndRaw->bgm_mram = SndMem.mram_end;
    pSndRaw->aram_base_addr_bgm = 0x700000;
    for (int i = 0; i < 2; i++) pSndRaw->snd_bgm_id[i] = 0xFF;
    pSndRaw->doorse_id = -1;
    memset(UseAramSize, 0, sizeof(u32) * 14);
}

void room_load(unsigned room)
{
    const uint64_t t0 = e1_clock_us();
    if (!g_booted) {
        g_main_thread = thd_current;
        aica_step_hook = step_hook;
        g_on = !boot_file("/cd/SNDOFF");
        aica_mute_all = boot_file("/cd/SNDMUTE");
        aica_slow_us = boot_file("/cd/SNDSLOW") ? 1500 : 0;
        g_drop = boot_file("/cd/SNDDROP");
        g_trace = !boot_file("/cd/NOTRACE");
        g_booted = 1;
        if (!g_on) { e1_log("E1 SOUND off (lab arm SNDOFF): the driver is not started\n"); return; }
        if (aica_mute_all) e1_log("E1 SOUND SNDMUTE: every channel at total attenuation (control of the output check)\n");
        if (aica_slow_us) e1_log("E1 SOUND SNDSLOW: %u us inside every audio step (control of the cost ceiling)\n",
                                 (unsigned) aica_slow_us);
        if (g_drop) e1_log("E1 SOUND SNDDROP: the first request from tick 100 on is dropped (control of the request check)\n");
        driver_boot();
    }
    if (!g_on) return;
    g_chunk = (uint8_t*) memalign(32, kChunk);
    // the room: the room arena emptied, the room's blocks, then the scene's characters' blocks
    aica_room_reset();
    SndReadAddrInit();
    static int resident;
    if (!resident) {   // CORE, PL, WEP: game start (read.cpp; core first: its bank lays out the sound chip)
        load_file("/cd/etc/core.das", 0);
        load_file(pG->pl_costume ? "/cd/em/pl08.drs" : "/cd/em/pl00.drs", 0);
        load_file("/cd/em/wep02.drs", 0);
        resident = 1;
    }
    char path[48];
    snprintf(path, sizeof path, "/cd/st%u/r%03x.dar", room >> 8, room);
    load_file(path, 0);   // ROOM and FOOT
#ifdef E2_FIGHT
    load_file("/cd/em/em15.drs", 0);   // the Ganados of the village square (em10's sounds)
#elif defined(E2_BOSS)
    load_file("/cd/em/em2b.drs", 0);   // El Gigante
#else
    if (e1_scene == E1_SCENE_HILL) load_file("/cd/em/pl11.drs", 0);   // Ashley
#endif
    // the room's sound start (game.cpp gameRoomInit: SndRoomStartInit, SndRoomBgmLoad, SndRoomBgmStartCheck,
    // SndRoomStrStartCheck), the room's sound header read from its archive
    room_bgm_record(room);
    load_stb(room);
    void* const room_arc = pG->pRoom;
    pG->pRoom = g_stb_arc ? g_stb_arc : room_arc;
    SndRoomStartInit();
    pG->pRoom = room_arc;
    SndRoomBgmLoad();
    SndRoomBgmStartCheck(0);
    SndRoomStrStartCheck();
    free(g_chunk);
    g_chunk = 0;
    g_load_us = (uint32_t) (e1_clock_us() - t0);
    e1_log("E1 SOUND load room %03x: banks %u, missing%s, %u bytes read, %u us (before play)\n", room, g_banks,
           g_missing[0] ? g_missing : " none", g_load_bytes, g_load_us);
    aica_start();
}

}  // namespace

// The AICA layer's log (aica.cpp): the main thread's lines go to the engine log; the audio thread does not format
// (newlib's formatting can take a lock the main thread holds): its lines are only counted.
extern "C" void aica_log(const char* fmt, ...)
{
    if (g_main_thread && thd_current != g_main_thread) { ++g_tlog_lost; return; }
    char b[120];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(b, sizeof b, fmt, ap);
    va_end(ap);
    e1_log("%s", b);
}

// ---------------------------------------------------------------------------
// The driver's disc reads (snd.cpp: SndBgmLoad's BGM file, SndDoorSeLoad's door sounds), synchronous: before play
// they are loading; inside play they would be disc reads in play, counted by core/play_files.c like any other.
// Weak, with the read queue's object and its poll (the fight image keeps generated stubs of both: theirs win there,
// and the synchronous read below has already happened when the driver polls).
// (32 bytes, not the queue's 12.5 KB: nothing in these images reads its members; the poll below ignores it)
__attribute__((weak, aligned(32))) unsigned char snd_Dvd[32] asm("_Dvd");
__attribute__((weak)) int cDvd::ReadCheck(int, int*, int*, void**) { return 1; }
// The DVD file table: only the stream player's two files are named (StrFileTbl: 1 bio4bgm.sbb, 0x5F bio4evt.sbb),
// as present; it opens them without the disc (snd_host.cpp DVDOpen).
#define FT1 {0, -1}
#define FT4 FT1, FT1, FT1, FT1
#define FT16 FT4, FT4, FT4, FT4
__attribute__((weak)) FileTblEntry FileTbl[0x80] = { FT1, {"bgm/bio4bgm.sbb", 0},
    FT16, FT16, FT16, FT16, FT16, FT4, FT4, FT4, FT1,   // 2 .. 0x5E
    {"bgm/bio4evt.sbb", 0} };
static_assert(sizeof(FileTbl) == 0x80 * sizeof(FileTblEntry), "FileTbl");
extern "C" int DvdRead(int fileNo, void* dst, u32 aram, u32 ofs, u32 length, int mode, const char* file, int line)
{
    (void) dst; (void) aram; (void) length; (void) mode; (void) file; (void) line;
    switch (fileNo) {
    case 0x61: load_file("/cd/bgm/bio4midi.dat", ofs); return 1;
    case 0x69: load_file("/cd/bgm/doorse.dat", ofs); return 1;
    default:
        e1_stub_hit("DvdRead(sound file)", fileNo);
        return -1;
    }
}

// ---------------------------------------------------------------------------
// The behaviour's sound requests (game/sound.mk: --wrap of SndCall and SndStop): counted, timed, traced.
static inline uint32_t fbits(const float f) { uint32_t u; memcpy(&u, &f, 4); return u; }
static void request_line(char kind, u16 blk, u16 no, Vec* pos, int id, int vol)
{
    if (g_trace != 1) return;
    char b[160];
    int n;
    if (pos)
        n = snprintf(b, sizeof b, "SR t=%lu f=%lu k=%c b=%u n=%u v=%08x i=%d p=%08lx,%08lx,%08lx\n", (unsigned long) e1_tick,
                     (unsigned long) pG->Frame_cnt, kind, blk, no, (unsigned) vol, id, (unsigned long) fbits(pos->x),
                     (unsigned long) fbits(pos->y), (unsigned long) fbits(pos->z));
    else
        n = snprintf(b, sizeof b, "SR t=%lu f=%lu k=%c b=%u n=%u v=%08x i=%d p=-\n", (unsigned long) e1_tick,
                     (unsigned long) pG->Frame_cnt, kind, blk, no, (unsigned) vol, id);
    e1_trace_put(b, (unsigned) n);
}
extern "C" u32 __wrap__Z7SndCallttP3VeciiP5cUnit(u16 blk, u16 no, Vec* pos, int id, int vol, cUnit* obj)
{
    if (g_drop == 1 && e1_tick >= 100) { g_drop = 2; ++g_dropped; return 0; }   // SNDDROP (control)
    ++g_requests;
    request_line('C', blk, no, pos, id, vol);
    if (!g_on || !g_booted) return 0;
    const MainSpan span;
    const u32 r = __real__Z7SndCallttP3VeciiP5cUnit(blk, no, pos, id, vol, obj);
    main_add(span.us());
    return r;
}
extern "C" int __wrap__Z7SndStopmi(u32 id, int time)
{
    ++g_stops;
    request_line('S', (u16) (id >> 16), (u16) id, 0, (int) id, time);
    if (!g_on || !g_booted) return 0;
    const MainSpan span;
    const int r = __real__Z7SndStopmi(id, time);
    main_add(span.us());
    return r;
}

// ---------------------------------------------------------------------------
// The audio frame's three parts (game/sound.mk wraps): the longest of each, for the report.
extern "C" {
void __real_Snd_iss_manager(void);
void __real_Snd_stream_player(void);
void __real_Snd_midi_sequencer(void);
}
static uint32_t g_part_max[3], g_part_max_tick[3];
static inline void part_time(int k, void (*f)(void))
{
    const uint64_t t0 = e1_clock_us();
    f();
    const uint32_t us = (uint32_t) (e1_clock_us() - t0);
    if (us > g_part_max[k]) { g_part_max[k] = us; g_part_max_tick[k] = e1_tick; }
}
extern "C" void __wrap_Snd_iss_manager(void) { part_time(0, __real_Snd_iss_manager); }
extern "C" void __wrap_Snd_stream_player(void) { part_time(1, __real_Snd_stream_player); }
extern "C" void __wrap_Snd_midi_sequencer(void) { part_time(2, __real_Snd_midi_sequencer); }

// ---------------------------------------------------------------------------
// The hooks into the engine core (game/sound.mk wraps).
// The service's three entry points (the core reaches them through the wraps below; the integrator may call them
// directly from the core instead: hand-back request R3).
extern "C" void snd_svc_room_load(unsigned room) { room_load(room); }
extern "C" void snd_svc_tick(void)
{
    if (g_on && g_booted) {   // the original main loop's SndWatcher, after Trans
        const MainSpan span;
        SndWatcher();
        main_add(span.us());
    }
}
extern "C" void snd_svc_report(void);
extern "C" void __wrap__Z12e1_load_roomj(unsigned room)
{
    __real__Z12e1_load_roomj(room);
    snd_svc_room_load(room);
}
extern "C" void __wrap__Z14e1_fields_latej(unsigned tick)
{
    snd_svc_tick();
    __real__Z14e1_fields_latej(tick);
}
extern "C" void __wrap__Z9e1_reportv(void)
{
    snd_svc_report();
    __real__Z9e1_reportv();
}
extern "C" void snd_svc_report(void)
{
    // the cost per picture over the selector's window (pictures 41-640: rows 41..640, e1_tick 41..640)
    const unsigned ticks = e1_state[2];
    uint64_t sum = 0;
    uint32_t worst = 0, wpic = 0, n = 0;
    for (unsigned k = 41; k <= 640 && k <= ticks && k < kPics; k++) {
        const uint32_t c = g_cost[k];
        sum += c;
        ++n;
        if (c > worst) { worst = c; wpic = k; }
    }
    const uint32_t mean = n ? (uint32_t) (sum / n) : 0;
    if (wpic)   // the worst picture's split
        e1_log("E1 SOUND worst picture %lu: audio steps %u (%lu us, longest %u us), game calls and SndWatcher %u us\n",
               (unsigned long) wpic, g_steps[wpic], (unsigned long) (g_cost[wpic] - g_cost_main[wpic]), g_step_max[wpic],
               g_cost_main[wpic]);
    e1_log("E1 SOUND longest step %lu us: %lu driver frames %lu us, voices %lu us, register flush %lu us (%lu register "
           "writes; most in a step %lu)\n",
           (unsigned long) aica_stats.long_us, (unsigned long) aica_stats.long_frames, (unsigned long) aica_stats.long_drv,
           (unsigned long) aica_stats.long_vox, (unsigned long) aica_stats.long_flush,
           (unsigned long) aica_stats.long_writes, (unsigned long) aica_stats.max_writes);
    e1_log("E1 SOUND frame parts longest: voice manager %lu us (tick %lu), stream player %lu us (tick %lu), sequencer %lu us "
           "(tick %lu)\n", (unsigned long) g_part_max[0], (unsigned long) g_part_max_tick[0], (unsigned long) g_part_max[1],
           (unsigned long) g_part_max_tick[1], (unsigned long) g_part_max[2], (unsigned long) g_part_max_tick[2]);
    if (g_tlog_lost) e1_log("E1 SOUND audio thread: %u log lines not formatted\n", g_tlog_lost);
    const AicaStats& s = aica_stats;
    e1_log("E1 SOUND %s pictures %u cost-us mean %lu worst %lu (picture %lu) voices-peak %lu notes-peak %lu "
           "stream-bytes-per-picture 0 requests %lu stops %lu banks %lu missing %lu\n", g_on ? "on" : "off", n,
           (unsigned long) mean, (unsigned long) worst, (unsigned long) wpic, (unsigned long) g_voices_peak,
           (unsigned long) g_notes_peak, (unsigned long) g_requests, (unsigned long) g_stops, (unsigned long) g_banks,
           (unsigned long) g_banks_missing);
    const AicaProbe& p = aica_probe_counts;
    e1_log("E1 SOUND PROBE samples %lu keyed %lu audible %lu moving %lu | se-starts %lu unmapped %lu notes %lu keyons %lu "
           "steps %lu drv-us %lu flush-us %lu aica-bytes %lu blocks-skipped %lu dropped %lu max-frames-a-step %lu "
           "debt-drops %lu\n",
           (unsigned long) p.samples, (unsigned long) p.keyed, (unsigned long) p.audible, (unsigned long) p.moving,
           (unsigned long) s.se_starts, (unsigned long) s.se_unmapped, (unsigned long) s.note_on, (unsigned long) s.keyons,
           (unsigned long) s.frames, (unsigned long) s.drv_us, (unsigned long) s.flush_us, (unsigned long) s.aica_used,
           (unsigned long) s.blocks_skipped, (unsigned long) g_dropped, (unsigned long) s.max_ticks, (unsigned long) s.debt_drops);
}
