#if RE4DC_VMU_SAVE  // vmusave.mk
// D367 VMU saves (VMU_SAVE=1): the Dolphin CARD calls of src/game/card.cpp over a virtual memory
// card backed by the VMU (design-vmu/DESIGN.md section 3). The game's card code is unchanged: its
// UI, messages, 20-file list, CRCs and load path run as on the GameCube.
//   bh4_dataNN (0..19) <-> VMS data file RE4DCSnnA / RE4DCSnnB (nn = NN + 1; one live copy)
//   bh4_system         <-> RE4DCSYS (the 56 B SystemWork)
//   [VMU_DEBUG_SLOT]   bh4_data19 (FILE 20) <-> RE4DCDBG, read only here (the chord writes it)
// Blocking VMU IO runs on a worker thread whose 8 KiB stack and every buffer live in the game's own
// CARD work area (0xA000 B, card.cpp workAlloc); the game polls CARDGetResultCode (BUSY) as it
// does on the GameCube. Nothing runs per gameplay frame.
// Error mapping (5.6; user decision: the game never formats): an unformatted or inconsistent VMU
// reports CARD_RESULT_FATAL_ERROR from CARDCheckAsync, which the game shows as its "cannot be
// used" message (msg 3 / boot 0x19) without offering to format; CARDFormatAsync is refused too.
#include <kos.h>
#include <dc/maple.h>
#include <string.h>
#include <stdio.h>
#include "vmu_store.h"
#include "vmu_dialog.h"
#include "lz_small.h"
#include "re4dc_platform.h"

typedef signed long s32;
typedef unsigned long u32;
typedef unsigned long long u64;
typedef unsigned short u16;
typedef unsigned char u8;

#ifndef RE4DC_VMU_SLOT_EST
#define RE4DC_VMU_SLOT_EST 24  // VMU blocks per save the free-space check assumes (retune from S8)
#endif
#ifndef RE4DC_CARD_FIXED_LATENCY
#define RE4DC_CARD_FIXED_LATENCY 0  // test: every async op takes at least this many polls
#endif
#ifndef RE4DC_VMU_GCRAW
#define RE4DC_VMU_GCRAW 0  // test backend (gate G1): GameCube-format images from /cd/dc/gcsave
#endif
#ifndef RE4DC_VMU_DEBUG_SLOT
#define RE4DC_VMU_DEBUG_SLOT 0
#endif

enum {
    CARD_RESULT_READY = 0, CARD_RESULT_BUSY = -1, CARD_RESULT_NOCARD = -3, CARD_RESULT_NOFILE = -4,
    CARD_RESULT_IOERROR = -5, CARD_RESULT_BROKEN = -6, CARD_RESULT_INSSPACE = -9, CARD_RESULT_NOPERM = -10,
    CARD_RESULT_FATAL_ERROR = -128
};

struct CARDFileInfo { s32 chan; s32 fileNo; s32 offset; s32 length; u16 iBlock; };
struct CARDStat {
    char fileName[32]; u32 length; u32 time; u8 gameName[4]; u8 company[2]; u8 bannerFormat; u8 pad;
    u32 iconAddr; u16 iconFormat; u16 iconSpeed; u32 commentAddr; u32 offsetBanner; u32 offsetBannerTlut;
    u32 offsetIcon[8]; u32 offsetIconTlut; u32 offsetData;
};

extern "C" u32 CRCCalc(u8* data, u32 len);  // src/game/card.cpp
extern "C" u32 re4dc_vi_retrace_count(void);
#if RE4DC_VMU_DEBUG_SLOT
extern "C" void re4dc_dbgslot_loaded(const void* extras);  // dbgslot_bridge.cpp
#endif

namespace {
// Save image layout (card.cpp).
constexpr unsigned kSaveHdr = 0x2000, kPayload = 0x2200, kSaveCrc = 0xEAF8, kRaw = kSaveCrc - kPayload;
constexpr unsigned kSysWork = 0x1E40, kSysCrc = 0x1E78, kSysWorkLen = kSysCrc - kSysWork;
// File layout: VMS header 128 + icon 512, R4DC header 32, then SaveInfo 512 + LZ stream (saves)
// or SystemWork (system file).
constexpr unsigned kVms = 640, kR4 = 32, kInfo = kVms + kR4, kStream = kInfo + 512;
constexpr unsigned kSysFile = 20, kFiles = 21;
constexpr u8 kKindSave = 1, kKindSys = 2, kKindDbg = 4;

// Work area (the game's 0xA000 B CARD work area).
constexpr unsigned kWorkBytes = 0xA000;
constexpr unsigned kStackOff = 0, kStackBytes = 8192;
constexpr unsigned kRootOff = kStackOff + kStackBytes, kFatOff = kRootOff + 512, kDirOff = kFatOff + 512;
constexpr unsigned kHashOff = kDirOff + 13 * 512, kIoOff = kHashOff + LZS_TABLE_BYTES;
constexpr unsigned kIoBytes = (kWorkBytes - kIoOff) & ~511U;  // 41 blocks

enum Op { kNone, kMount, kInfoRead, kLoad, kSysRead, kSaveWrite, kSysWrite, kDelete };
const char* const kOpName[] = {"none", "mount", "info", "load", "sysread", "save", "syswrite", "delete"};

struct Session {
    u8* work;
    VmuStore st;
    int formatted;             // mount result: 1 file system ok, 0 unusable (never formatted in game)
    char live[kFiles];         // 'A' / 'B' / 'S' (RE4DCSYS) / 'D' (RE4DCDBG) / 0
    char stale[kFiles];        // an older second copy left by an interrupted A/B write
    u32 seq[kFiles];
    u8 created[kFiles];        // CARDCreateAsync (virtual until the write)
    kthread_t* thread;
    volatile int busy;
    int result;
    unsigned polls, t0;
    // current op
    Op op;
    int file;
    u8* buf;
    s32 len, ofs;
};
Session ss{};
#if RE4DC_VMU_DIALOG
#include "vmu_dialog_session.inc"
#endif

void name_of(int file, char which, char* out)
{
    if (file == (int) kSysFile) {
        strcpy(out, "RE4DCSYS");
#if RE4DC_VMU_DEBUG_SLOT
    } else if (file == 19) {
        strcpy(out, "RE4DCDBG");
#endif
    } else {
        sprintf(out, "RE4DCS%02d%c", file + 1, which);
    }
}

int file_of(const char* name)
{
    if (!strcmp(name, "bh4_system")) return (int) kSysFile;
    int n = -1;
    if (sscanf(name, "bh4_data%d", &n) == 1 && n >= 0 && n < 20) return n;
    return -1;
}

u32 be32(const u8* p) { return (u32) p[0] << 24 | (u32) p[1] << 16 | (u32) p[2] << 8 | p[3]; }
void put_be32(u8* p, u32 v) { p[0] = (u8) (v >> 24); p[1] = (u8) (v >> 16); p[2] = (u8) (v >> 8); p[3] = (u8) v; }

// R4DC header (32 B, big-endian): magic, fmt, kind, slot, flags, seq, raw_len, comp_len, crc_raw,
// build tag, reserved.
void r4_header(u8* h, u8 kind, int slot, u32 seq, u32 raw_len, u32 comp_len, u32 crc)
{
    memset(h, 0, kR4);
    memcpy(h, "R4DC", 4);
    h[4] = 1;
    h[5] = kind;
    h[6] = (u8) slot;
    put_be32(h + 8, seq);
    put_be32(h + 12, raw_len);
    put_be32(h + 16, comp_len);
    put_be32(h + 20, crc);
}

// VMS header check over a whole file already in `f` (bytes).
bool vms_ok(u8* f, unsigned bytes, unsigned* payload_len)
{
    const unsigned data_len = f[72] | f[73] << 8 | f[74] << 16 | (u32) f[75] << 24;
    const unsigned icons = f[64] | f[65] << 8;
    if (icons != 1 || f[68] || f[69] || kVms + data_len > bytes) return false;
    const u16 crc = (u16) (f[70] | f[71] << 8);
    f[70] = f[71] = 0;
    const u16 got = net_crc16ccitt(f, (int) (kVms + data_len), 0);
    f[70] = (u8) crc;
    f[71] = (u8) (crc >> 8);
    *payload_len = data_len;
    return got == crc;
}

int map(int vmus_rc)
{
    switch (vmus_rc) {
    case VMUS_OK: return CARD_RESULT_READY;
    case VMUS_NOCARD: return CARD_RESULT_NOCARD;
    case VMUS_FULL: return CARD_RESULT_INSSPACE;
    case VMUS_NOFILE: return CARD_RESULT_NOFILE;
    default: return CARD_RESULT_IOERROR;
    }
}

#if RE4DC_VMU_GCRAW
// ---------------------------------------------------------------- gcraw test backend (G1)
long gc_read(int file, void* dst, unsigned len, unsigned ofs)
{
    char path[48];
    if (file == (int) kSysFile) strcpy(path, "/cd/dc/gcsave/bh4_system");
    else sprintf(path, "/cd/dc/gcsave/bh4_data%02d", file);
    file_t f = fs_open(path, O_RDONLY);
    if (f < 0) return -1;
    if (ofs) fs_seek(f, ofs, SEEK_SET);
    long got = 0;
    while (got < (long) len) {
        const ssize_t r = fs_read(f, (char*) dst + got, len - got);
        if (r <= 0) break;
        got += r;
    }
    fs_close(f);
    // A GameCube card file is sector-rounded (8 KiB): the image's tail past its content is zeros.
    if (got > 0 && got < (long) len) {
        memset((char*) dst + got, 0, len - got);
        got = (long) len;
    }
    return got;
}
#endif

// ---------------------------------------------------------------- worker ops
void qcfg_on_mount(u8* io);  // RE4DCCFG cache (S5, below)

int op_mount()
{
    memset(ss.live, 0, sizeof(ss.live));
    memset(ss.stale, 0, sizeof(ss.stale));
    memset(ss.seq, 0, sizeof(ss.seq));
    ss.formatted = 0;
#if RE4DC_VMU_GCRAW
    for (int f = 0; f < (int) kFiles; ++f) {
        u8 probe[4];
        if (gc_read(f, probe, 4, 0) == 4) ss.live[f] = 'G';
    }
    ss.formatted = 1;
    return CARD_RESULT_READY;
#else
    int rc = vmus_pick(&ss.st);
#if RE4DC_VMU_DIALOG
    card_dialog_publish(false);
#endif
    if (rc) return map(rc);
    rc = vmus_mount(&ss.st, ss.work + kRootOff, ss.work + kFatOff, ss.work + kDirOff);
    if (rc == VMUS_NOFS) return CARD_RESULT_READY;  // mounted, unusable: CARDCheckAsync reports it
    if (rc) return map(rc);
    ss.formatted = 1;
    char name[16];
    u8* blk = ss.work + kIoOff;
    qcfg_on_mount(blk);
    for (int f = 0; f < (int) kFiles; ++f) {
        if (f == (int) kSysFile || (RE4DC_VMU_DEBUG_SLOT && f == 19)) {
            name_of(f, 0, name);
            if (vmus_find(&ss.st, name) >= 0) ss.live[f] = f == (int) kSysFile ? 'S' : 'D';
            continue;
        }
        name_of(f, 'A', name);
        const int a = vmus_find(&ss.st, name);
        name_of(f, 'B', name);
        const int b = vmus_find(&ss.st, name);
        if (a >= 0 && b >= 0) {
            // An interrupted A/B write left both: the newest valid-looking seq wins (block 1 holds
            // the R4DC header at byte 640).
            u32 sa = 0, sb = 0;
            if (vmus_read(&ss.st, a, blk, 1024, 2) == VMUS_OK && !memcmp(blk + kVms, "R4DC", 4)) sa = be32(blk + kVms + 8);
            if (vmus_read(&ss.st, b, blk, 1024, 2) == VMUS_OK && !memcmp(blk + kVms, "R4DC", 4)) sb = be32(blk + kVms + 8);
            ss.live[f] = sb > sa ? 'B' : 'A';
            ss.stale[f] = sb > sa ? 'A' : 'B';
            ss.seq[f] = sb > sa ? sb : sa;
        } else if (a >= 0 || b >= 0) {
            ss.live[f] = a >= 0 ? 'A' : 'B';
        }
    }
    return CARD_RESULT_READY;
#endif
}

#if RE4DC_VMU_SAFE_IO
// The newest copy of a save does not read back: use the older one still on the card (#66).
bool use_older_copy(int file)
{
    if (!ss.stale[file]) return false;
    const char bad = ss.live[file];
    ss.live[file] = ss.stale[file];
    ss.stale[file] = bad;
    re4dc_log("card-vmu: file=%d copy %c damaged, using copy %c\n", file, bad, ss.live[file]);
    return true;
}
#endif

int live_index(int file)
{
    char name[16];
    name_of(file, ss.live[file], name);
    return vmus_find(&ss.st, name);
}

// SaveInfo (image 0x2000..0x2200) of a save: the first 3 blocks.
int op_info()
{
    memset(ss.buf, 0, (size_t) ss.len);
#if RE4DC_VMU_GCRAW
    return gc_read(ss.file, ss.buf, ss.len, ss.ofs) == ss.len ? CARD_RESULT_READY : CARD_RESULT_IOERROR;
#else
    u8* io = ss.work + kIoOff;
    int idx = live_index(ss.file);
    if (idx < 0) return CARD_RESULT_NOFILE;
    int rc = vmus_read(&ss.st, idx, io, kIoBytes, 3);
#if RE4DC_VMU_SAFE_IO
    if ((rc || memcmp(io + kVms, "R4DC", 4)) && use_older_copy(ss.file)) {
        idx = live_index(ss.file);
        if (idx < 0) return CARD_RESULT_NOFILE;
        rc = vmus_read(&ss.st, idx, io, kIoBytes, 3);
    }
#endif
    if (rc) return map(rc);
    if (!memcmp(io + kVms, "R4DC", 4)) {
        const u32 seq = be32(io + kVms + 8);
        if (seq > ss.seq[ss.file]) ss.seq[ss.file] = seq;
        memcpy(ss.buf, io + kInfo, (size_t) ss.len);
    } else {
        memset(ss.buf, 0xFF, (size_t) ss.len);  // fails the game's header CRC: "damaged file"
    }
    return CARD_RESULT_READY;
#endif
}

// A whole save: decode into the game's buffer and rebuild the GameCube image.
int op_load()
{
    u8* img = ss.buf;
    memset(img, 0, (size_t) ss.len);
#if RE4DC_VMU_GCRAW
    if (gc_read(ss.file, img, ss.len, 0) != ss.len) return CARD_RESULT_IOERROR;
#else
    u8* io = ss.work + kIoOff;
#if RE4DC_VMU_SAFE_IO
    for (int attempt = 0;; ++attempt) {
#endif
    const int idx = live_index(ss.file);
    if (idx < 0) return CARD_RESULT_NOFILE;
    const unsigned blocks = vmus_file_blocks(&ss.st, idx);
    if (blocks * 512 > kIoBytes) return CARD_RESULT_IOERROR;
    const int rc = vmus_read(&ss.st, idx, io, kIoBytes, 0);
#if RE4DC_VMU_SAFE_IO
    if (rc && !attempt && use_older_copy(ss.file)) continue;
#endif
    if (rc) return map(rc);
    unsigned plen = 0;
    bool ok = vms_ok(io, blocks * 512, &plen) && !memcmp(io + kVms, "R4DC", 4) && io[kVms + 4] == 1 &&
              be32(io + kVms + 12) == kRaw && kR4 + 512 + be32(io + kVms + 16) <= plen;
    if (ok) {
        memcpy(img + kSaveHdr, io + kInfo, 512);
        ok = lzs_decode(io + kStream, be32(io + kVms + 16), img + kPayload, kRaw) == (int) kRaw &&
             CRCCalc(img + kSaveHdr, kSaveCrc - kSaveHdr) == be32(io + kVms + 20);
    }
#if RE4DC_VMU_SAFE_IO
    if (!ok && !attempt && use_older_copy(ss.file)) continue;
#endif
#if RE4DC_VMU_DEBUG_SLOT
    if (ok && ss.live[ss.file] == 'D') {
        const unsigned extras = kStream + be32(io + kVms + 16);
        if (extras + 256 <= kVms + plen) re4dc_dbgslot_loaded(io + extras);
    }
#endif
    // The game's own check decides: a bad file keeps a wrong image CRC -> "damaged file".
    const u32 crc = CRCCalc(img, kSaveCrc);
    *(u32*) (img + kSaveCrc) = ok ? crc : ~crc;
    re4dc_log("card-vmu: load file=%d %s blocks=%u ok=%d\n", ss.file, ss.live[ss.file] == 'D' ? "RE4DCDBG" : "", blocks, ok);
#if RE4DC_VMU_SAFE_IO
    break;
    }
#endif
#endif
    // Section digest for gate G1 (same bytes from either backend).
    u32 h = 2166136261U;
    for (unsigned i = kSaveHdr; i < kSaveCrc; ++i) h = (h ^ img[i]) * 16777619U;
    re4dc_log("card-vmu: load digest file=%d %08x\n", ss.file, (unsigned) h);
    return CARD_RESULT_READY;
}

int op_sysread()
{
    u8* img = ss.buf;
    memset(img, 0, (size_t) ss.len);
#if RE4DC_VMU_GCRAW
    return gc_read(kSysFile, img, ss.len, 0) == ss.len ? CARD_RESULT_READY : CARD_RESULT_IOERROR;
#else
    u8* io = ss.work + kIoOff;
    const int idx = live_index(kSysFile);
    if (idx < 0) return CARD_RESULT_NOFILE;
    const unsigned blocks = vmus_file_blocks(&ss.st, idx);
    if (blocks * 512 > kIoBytes) return CARD_RESULT_IOERROR;
    const int rc = vmus_read(&ss.st, idx, io, kIoBytes, 0);
    if (rc) return map(rc);
    unsigned plen = 0;
    const bool ok = vms_ok(io, blocks * 512, &plen) && !memcmp(io + kVms, "R4DC", 4) && io[kVms + 5] == kKindSys &&
                    plen >= kR4 + kSysWorkLen;
    if (ok) memcpy(img + kSysWork, io + kVms + kR4, kSysWorkLen);
    const u32 crc = CRCCalc(img, kSysCrc);
    *(u32*) (img + kSysCrc) = ok ? crc : ~crc;
    return CARD_RESULT_READY;
#endif
}

int op_savewrite()
{
#if RE4DC_VMU_GCRAW
    return CARD_RESULT_NOPERM;
#else
    const int f = ss.file;
    if (RE4DC_VMU_DEBUG_SLOT && f == 19) return CARD_RESULT_NOPERM;  // FILE 20 is the chord's
    u8* img = ss.buf;
    u8* io = ss.work + kIoOff;
    unsigned short* hash = (unsigned short*) (ss.work + kHashOff);
    const int comp = lzs_encode(img + kPayload, kRaw, io + kStream, kIoBytes - kStream, hash);
    if (comp < 0) {
        re4dc_log("card-vmu: save file=%d does not fit %u B\n", f, kIoBytes - kStream);
        return CARD_RESULT_INSSPACE;
    }
    if (lzs_verify(io + kStream, (unsigned) comp, img + kPayload, kRaw) != (int) kRaw) {
        re4dc_log("card-vmu: save file=%d write-verify FAILED\n", f);
        return CARD_RESULT_IOERROR;
    }
    const u32 seq = ss.seq[f] + 1;
    r4_header(io + kVms, kKindSave, f, seq, kRaw, (u32) comp, CRCCalc(img + kSaveHdr, kSaveCrc - kSaveHdr));
    memcpy(io + kInfo, img + kSaveHdr, 512);
    char desc[33];
    const u16 room = *(u16*) (img + kSaveHdr + 0x50);
    snprintf(desc, sizeof(desc), "FILE %02d  R%03X", f + 1, (unsigned) room);
    {
        u32 h = 2166136261U;
        for (unsigned i = kSaveHdr; i < kSaveCrc; ++i) h = (h ^ img[i]) * 16777619U;
        re4dc_log("card-vmu: save digest file=%d %08x\n", f, (unsigned) h);
    }
    const unsigned bytes = vmus_package(io, desc, kR4 + 512 + (unsigned) comp);
    const unsigned blocks = bytes / 512;
    char name[16], oldname[16], stalename[16];
    // A stale second copy (interrupted A/B) is released first; it is older than the live one.
    if (ss.stale[f]) {
        name_of(f, ss.stale[f], stalename);
        vmus_delete(&ss.st, stalename);
        ss.stale[f] = 0;
    }
    const char which = ss.live[f] == 'A' ? 'B' : 'A';
    name_of(f, which, name);
    if (ss.live[f]) name_of(f, ss.live[f], oldname);
    int inplace = 0;
    const int rc = vmus_write(&ss.st, name, io, blocks, ss.live[f] ? oldname : nullptr, &inplace);
    re4dc_log("card-vmu: save file=%d name=%s comp=%d blocks=%u free=%u inplace=%d rc=%d\n", f, name, comp, blocks,
              vmus_free_blocks(&ss.st), inplace, rc);
    if (rc) return map(rc);
    ss.live[f] = which;
    ss.seq[f] = seq;
    return CARD_RESULT_READY;
#endif
}

int op_syswrite()
{
#if RE4DC_VMU_GCRAW
    return CARD_RESULT_NOPERM;
#else
    u8* io = ss.work + kIoOff;
    const u32 seq = ss.seq[kSysFile] + 1;
    memcpy(io + kVms + kR4, ss.buf + kSysWork, kSysWorkLen);
    r4_header(io + kVms, kKindSys, 0, seq, kSysWorkLen, kSysWorkLen, CRCCalc(io + kVms + kR4, kSysWorkLen));
    const unsigned blocks = vmus_package(io, "SYSTEM", kR4 + kSysWorkLen) / 512;
    const int idx = vmus_find(&ss.st, "RE4DCSYS");
    int rc, inplace = 0;
    if (idx >= 0 && vmus_file_blocks(&ss.st, idx) == blocks) rc = vmus_rewrite(&ss.st, idx, io, blocks);
    else {
        if (idx >= 0) vmus_delete(&ss.st, "RE4DCSYS");
        rc = vmus_write(&ss.st, "RE4DCSYS", io, blocks, nullptr, &inplace);
    }
    re4dc_log("card-vmu: syswrite blocks=%u rc=%d\n", blocks, rc);
    if (rc) return map(rc);
    ss.live[kSysFile] = 'S';
    ss.seq[kSysFile] = seq;
    return CARD_RESULT_READY;
#endif
}

int op_delete()
{
#if RE4DC_VMU_GCRAW
    return CARD_RESULT_NOPERM;
#else
    const int f = ss.file;
    char name[16];
    int rc = VMUS_NOFILE;
    static const char kWhich[2] = {'A', 'B'};
    for (int k = 0; k < 2; ++k) {
        const char w = f == (int) kSysFile ? 0 : kWhich[k];
        name_of(f, w, name);
        if (vmus_find(&ss.st, name) >= 0) {
            rc = vmus_delete(&ss.st, name);
            if (rc) return map(rc);
        }
        if (f == (int) kSysFile) break;
    }
    ss.live[f] = ss.stale[f] = 0;
    ss.created[f] = 0;
    return rc == VMUS_NOFILE ? CARD_RESULT_NOFILE : CARD_RESULT_READY;
#endif
}

void* worker(void*)
{
    int rc;
    switch (ss.op) {
    case kMount: rc = op_mount(); break;
    case kInfoRead: rc = op_info(); break;
    case kLoad: rc = op_load(); break;
    case kSysRead: rc = op_sysread(); break;
    case kSaveWrite: rc = op_savewrite(); break;
    case kSysWrite: rc = op_syswrite(); break;
    case kDelete: rc = op_delete(); break;
    default: rc = CARD_RESULT_FATAL_ERROR; break;
    }
    re4dc_log("card-vmu: op=%s file=%d vbl=%u rc=%d\n", kOpName[ss.op], ss.file,
              (unsigned) (re4dc_vi_retrace_count() - ss.t0), rc);
    ss.result = rc;
#if RE4DC_VMU_DIALOG
    card_dialog_publish(rc == CARD_RESULT_READY);
#endif
    ss.busy = 0;
    return nullptr;
}

// The one KOS heap allocation on this path is the worker's kthread_t (thd_create_ex, 0x480 B;
// the stack is in the game's work area). KOS malloc has only a few KB free on m1, so the first
// op reserves that block at boot and each op hands it to thd_create_ex (free just before, the
// same-size request takes the same chunk) and takes it back after the join.
constexpr unsigned kThreadReserve = sizeof(kthread_t);
void* thread_reserve;

void join()
{
    if (ss.thread) {
        thd_join(ss.thread, nullptr);
        ss.thread = nullptr;
    }
    if (!thread_reserve) thread_reserve = aligned_alloc(32, kThreadReserve);
}

s32 start(Op op, int file, void* buf, s32 len, s32 ofs)
{
    join();
    if (!ss.work) return ss.result = CARD_RESULT_FATAL_ERROR;
    ss.op = op;
    ss.file = file;
    ss.buf = static_cast<u8*>(buf);
    ss.len = len;
    ss.ofs = ofs;
    ss.polls = 0;
    ss.t0 = re4dc_vi_retrace_count();
    ss.busy = 1;
#if RE4DC_VMU_DIALOG
    card_dialog_begin();
#endif
    kthread_attr_t a;
    memset(&a, 0, sizeof(a));
    a.stack_ptr = ss.work + kStackOff;
    a.stack_size = kStackBytes;
    a.prio = PRIO_DEFAULT;
    a.label = "card-vmu";
    free(thread_reserve);
    thread_reserve = nullptr;
    ss.thread = thd_create_ex(&a, worker, nullptr);
    if (!ss.thread) {
        thread_reserve = aligned_alloc(32, kThreadReserve);
        ss.busy = 0;
        return ss.result = CARD_RESULT_FATAL_ERROR;
    }
    return CARD_RESULT_READY;
}

s32 done_now(s32 rc)
{
    ss.result = rc;
    ss.polls = 0;
    return rc;
}

bool device_ok()
{
#if RE4DC_VMU_GCRAW
    return true;
#else
    if (ss.st.dev) return vmus_present(&ss.st);
    VmuStore probe{};
    return vmus_pick(&probe) == VMUS_OK;
#endif
}
}  // namespace

extern "C" {

void CARDInit(void) {}

#if RE4DC_VMU_SAFE_IO
int re4dc_card_busy(void) { return ss.busy != 0; }
#endif

#if RE4DC_VMU_DIALOG
int re4dc_vmu_dialog_snapshot(Re4dcVmuDialogSnapshot* out)
{
    return card_dialog_read(out);
}
#endif

s32 CARDProbeEx(s32 chan, s32* memSize, s32* sectorSize)
{
    if (chan != 0 || ss.busy == 2) return CARD_RESULT_NOCARD;
    if (!device_ok()) {
#if RE4DC_VMU_DIALOG
        card_dialog_clear();
#endif
        return CARD_RESULT_NOCARD;
    }
    if (memSize) *memSize = 4;
    if (sectorSize) *sectorSize = 0x2000;
    return CARD_RESULT_READY;
}

s32 CARDMountAsync(s32 chan, void* work, void* detach, void* attach)
{
    (void) detach; (void) attach;
    if (chan != 0) return CARD_RESULT_NOCARD;
    join();
    ss.work = static_cast<u8*>(work);
    memset(ss.created, 0, sizeof(ss.created));
    ss.st = VmuStore{};
#if RE4DC_VMU_DIALOG
    card_dialog_clear();
#endif
    return start(kMount, -1, nullptr, 0, 0);
}

s32 CARDUnmount(s32 chan)
{
    if (chan != 0) return CARD_RESULT_NOCARD;
    join();
    ss.busy = 0;
    ss.work = nullptr;   // the game frees its work area after this
    ss.st = VmuStore{};
#if RE4DC_VMU_DIALOG
    card_dialog_clear();
#endif
    return CARD_RESULT_READY;
}

s32 CARDGetResultCode(s32 chan)
{
    if (chan != 0) return CARD_RESULT_NOCARD;
    if (ss.busy) return CARD_RESULT_BUSY;
#if RE4DC_CARD_FIXED_LATENCY
    if (ss.polls++ < (unsigned) RE4DC_CARD_FIXED_LATENCY) return CARD_RESULT_BUSY;
#endif
    return ss.result;
}

s32 CARDCheckAsync(s32 chan, void* cb)
{
    (void) cb;
    if (chan != 0) return CARD_RESULT_NOCARD;
    join();
    return done_now(ss.formatted ? CARD_RESULT_READY : CARD_RESULT_FATAL_ERROR);
}

s32 CARDFormatAsync(s32 chan, void* cb)
{
    (void) cb;
    (void) chan;
    re4dc_log("card-vmu: format refused (format the VMU in the Dreamcast BIOS)\n");
    return done_now(CARD_RESULT_FATAL_ERROR);
}

s32 CARDFreeBlocks(s32 chan, s32* bytes, s32* files)
{
    if (chan != 0) return CARD_RESULT_NOCARD;
    join();
#if RE4DC_VMU_GCRAW
    if (bytes) *bytes = 0;
    if (files) *files = 0;
#else
    const unsigned free_blocks = vmus_free_blocks(&ss.st);
    const unsigned sys_reserve = ss.live[kSysFile] ? 0 : 2;
    const unsigned usable = free_blocks > sys_reserve ? free_blocks - sys_reserve : 0;
    const unsigned gc = 8 * (usable / RE4DC_VMU_SLOT_EST) + (free_blocks >= 2 ? 1 : 0);
    if (bytes) *bytes = (s32) (gc * 0x2000);
    if (files) *files = (s32) vmus_free_dirents(&ss.st);
#endif
    return CARD_RESULT_READY;
}

s32 CARDOpen(s32 chan, const char* name, CARDFileInfo* fi)
{
    if (chan != 0) return CARD_RESULT_NOCARD;
    const int f = file_of(name);
    if (f < 0 || !(ss.live[f] || ss.created[f])) return CARD_RESULT_NOFILE;
    fi->chan = chan;
    fi->fileNo = f;
    fi->offset = 0;
    fi->length = f == (int) kSysFile ? 0x2000 : 0x10000;
    fi->iBlock = 0;
    return CARD_RESULT_READY;
}

s32 CARDClose(CARDFileInfo* fi) { (void) fi; return CARD_RESULT_READY; }

s32 CARDCreateAsync(s32 chan, const char* name, u32 size, CARDFileInfo* fi, void* cb)
{
    (void) size; (void) cb;
    if (chan != 0) return CARD_RESULT_NOCARD;
    const int f = file_of(name);
    if (f < 0) return done_now(CARD_RESULT_NOPERM);
    ss.created[f] = 1;
    CARDOpen(chan, name, fi);
    return done_now(CARD_RESULT_READY);
}

s32 CARDGetStatus(s32 chan, s32 fileNo, CARDStat* stat)
{
    if (chan != 0) return CARD_RESULT_NOCARD;
    if (fileNo < 0 || fileNo >= (s32) kFiles) return CARD_RESULT_NOFILE;
    memset(stat, 0, sizeof(*stat));
    if (fileNo == (s32) kSysFile) strcpy(stat->fileName, "bh4_system");
    else sprintf(stat->fileName, "bh4_data%02d", (int) fileNo);
    stat->length = fileNo == (s32) kSysFile ? 0x2000 : 0x10000;
    memcpy(stat->gameName, "G4BE", 4);
    memcpy(stat->company, "08", 2);
    stat->iconAddr = 0x40;
    stat->commentAddr = 0;  // never 0xFFFFFFFF, which the game reads as a corrupt file
    return CARD_RESULT_READY;
}

s32 CARDSetStatusAsync(s32 chan, s32 fileNo, CARDStat* stat, void* cb)
{
    (void) fileNo; (void) stat; (void) cb;
    if (chan != 0) return CARD_RESULT_NOCARD;
    return done_now(CARD_RESULT_READY);  // the GameCube banner/icon/comment are not stored
}

s32 CARDReadAsync(CARDFileInfo* fi, void* buf, s32 len, s32 ofs, void* cb)
{
    (void) cb;
    const int f = fi->fileNo;
    if (f == (int) kSysFile) return start(kSysRead, f, buf, len, ofs);
    if (ofs == (s32) kSaveHdr && len <= 0x200) return start(kInfoRead, f, buf, len, ofs);
    if (ofs == 0 && len >= (s32) (kSaveCrc + 4)) return start(kLoad, f, buf, len, ofs);
    return done_now(CARD_RESULT_FATAL_ERROR);
}

s32 CARDWriteAsync(CARDFileInfo* fi, void* buf, s32 len, s32 ofs, void* cb)
{
    (void) cb;
    const int f = fi->fileNo;
    if (ofs != 0) return done_now(CARD_RESULT_FATAL_ERROR);
    if (f == (int) kSysFile) return start(kSysWrite, f, buf, len, ofs);
    if (len < (s32) (kSaveCrc + 4)) return done_now(CARD_RESULT_FATAL_ERROR);
    return start(kSaveWrite, f, buf, len, ofs);
}

s32 CARDDeleteAsync(s32 chan, const char* name, void* cb)
{
    (void) cb;
    if (chan != 0) return CARD_RESULT_NOCARD;
    const int f = file_of(name);
    if (f < 0) return done_now(CARD_RESULT_NOFILE);
    return start(kDelete, f, nullptr, 0, 0);
}

s32 CARDGetSerialNo(s32 chan, u64* serial)
{
    if (chan != 0) return CARD_RESULT_NOCARD;
    if (serial) *serial = 0x5245344443ULL;  // constant: saves copied between VMUs still load
    return CARD_RESULT_READY;
}

}  // extern "C"

// ---------------------------------------------------------------- RE4DCCFG (design-vmu S5)
// The quality choice (platform/quality.h Re4dcQualityCfg, 32 B "R4CF") as the 2-block VMS file
// RE4DCCFG (header + icon + record). The only writer: quality.cpp calls the store only when the
// choice changes. Load: every mount (the boot RE4DCSYS mount runs before the title) caches the
// record on the worker; the title reads that cache after joining the worker. Store: synchronous
// in the title's frame (about 25 vblanks: mount + 2 blocks) with a transient game-heap block, so
// the KOS heap is never used; refused while a card op runs or when the VMU is missing/full.
#include "quality.h"
void* mem_alloc(u32 size, const char* file, int line, int a, int b);  // src/game/main_mem.cpp
void Mem_free(void* p);
namespace {
Re4dcQualityCfg qcfg_cache;
int qcfg_state;  // 0 not read, 1 cached, -1 no RE4DCCFG on the mounted VMU
constexpr unsigned kCfgBufBytes = 512 + 512 + 13 * 512 + 2 * 512;

void qcfg_on_mount(u8* io)
{
    const int idx = vmus_find(&ss.st, "RE4DCCFG");
    qcfg_state = -1;
    if (idx >= 0 && vmus_read(&ss.st, idx, io, 1024, 2) == VMUS_OK && !memcmp(io + kVms, "R4CF", 4)) {
        memcpy(&qcfg_cache, io + kVms, sizeof(qcfg_cache));
        qcfg_state = 1;
    }
}
}  // namespace

extern "C" int re4dc_quality_cfg_load(Re4dcQualityCfg* out)
{
    if (ss.busy) return 0;
    join();
    if (qcfg_state != 1) return 0;
    memcpy(out, &qcfg_cache, sizeof(*out));
    return 1;
}

extern "C" int re4dc_quality_cfg_store(const Re4dcQualityCfg* rec)
{
#if RE4DC_VMU_GCRAW
    (void) rec;
    return 0;
#else
    if (ss.busy) return 0;
    join();
#if RE4DC_VMU_DIALOG
    // The independent title writer may change this device through another FAT.
    // Keep presentation counts unknown until the next fresh CARD mount.
    card_dialog_clear();
#endif
    u8* mem = (u8*) mem_alloc(kCfgBufBytes, __FILE__, __LINE__, 0, 13);
    if (!mem) {
        re4dc_log("card-vmu: cfg NOMEM (%u B)\n", kCfgBufBytes);
        return 0;
    }
    const u32 t0 = re4dc_vi_retrace_count();
    u8* io = mem + 512 + 512 + 13 * 512;
    VmuStore st{};
    int rc = vmus_pick(&st);
    if (!rc) rc = vmus_mount(&st, mem, mem + 512, mem + 1024);
    unsigned blocks = 0;
    if (!rc) {
        memset(io, 0, 1024);
        memcpy(io + kVms, rec, sizeof(*rec));
        blocks = vmus_package(io, "GRAPHICS", sizeof(*rec)) / 512;
        const int idx = vmus_find(&st, "RE4DCCFG");
        int inplace = 0;
        if (idx >= 0 && vmus_file_blocks(&st, idx) == blocks) rc = vmus_rewrite(&st, idx, io, blocks);
        else {
            if (idx >= 0) vmus_delete(&st, "RE4DCCFG");
            rc = vmus_write(&st, "RE4DCCFG", io, blocks, nullptr, &inplace);
        }
    }
    Mem_free(mem);
    re4dc_log("card-vmu: cfg store mode=%u blocks=%u vbl=%u rc=%d\n", (unsigned) rec->mode, blocks,
              (unsigned) (re4dc_vi_retrace_count() - t0), rc);
    if (rc) return 0;
    memcpy(&qcfg_cache, rec, sizeof(qcfg_cache));
    qcfg_state = 1;
    return 1;
#endif
}
#else  // RE4DC_VMU_SAVE
// Memory card interface: no card. Every call reports CARD_RESULT_NOCARD, which
// the game's card state machine (src/game/card.cpp) treats as "no memory
// card inserted"; the VMU mapping is a later slice.
typedef signed long s32;
typedef unsigned long u32;
typedef unsigned long long u64;

enum { CARD_RESULT_NOCARD = -3 };

extern "C" {

void CARDInit(void) {}
s32 CARDCheckAsync(s32 chan, void* cb) { (void) chan; (void) cb; return CARD_RESULT_NOCARD; }
s32 CARDClose(void* fi) { (void) fi; return CARD_RESULT_NOCARD; }
s32 CARDCreateAsync(s32 chan, const char* name, u32 size, void* fi, void* cb) { (void) chan; (void) name; (void) size; (void) fi; (void) cb; return CARD_RESULT_NOCARD; }
s32 CARDDeleteAsync(s32 chan, const char* name, void* cb) { (void) chan; (void) name; (void) cb; return CARD_RESULT_NOCARD; }
s32 CARDFormatAsync(s32 chan, void* cb) { (void) chan; (void) cb; return CARD_RESULT_NOCARD; }
s32 CARDFreeBlocks(s32 chan, s32* bytes, s32* files) { (void) chan; if (bytes) *bytes = 0; if (files) *files = 0; return CARD_RESULT_NOCARD; }
s32 CARDGetResultCode(s32 chan) { (void) chan; return CARD_RESULT_NOCARD; }
s32 CARDGetSerialNo(s32 chan, u64* serial) { (void) chan; if (serial) *serial = 0; return CARD_RESULT_NOCARD; }
s32 CARDGetStatus(s32 chan, s32 fileNo, void* stat) { (void) chan; (void) fileNo; (void) stat; return CARD_RESULT_NOCARD; }
s32 CARDMountAsync(s32 chan, void* work, void* detach, void* attach) { (void) chan; (void) work; (void) detach; (void) attach; return CARD_RESULT_NOCARD; }
s32 CARDOpen(s32 chan, const char* name, void* fi) { (void) chan; (void) name; (void) fi; return CARD_RESULT_NOCARD; }
s32 CARDProbeEx(s32 chan, s32* memSize, s32* sectorSize) { (void) chan; if (memSize) *memSize = 0; if (sectorSize) *sectorSize = 0; return CARD_RESULT_NOCARD; }
s32 CARDReadAsync(void* fi, void* buf, s32 len, s32 ofs, void* cb) { (void) fi; (void) buf; (void) len; (void) ofs; (void) cb; return CARD_RESULT_NOCARD; }
s32 CARDSetStatusAsync(s32 chan, s32 fileNo, void* stat, void* cb) { (void) chan; (void) fileNo; (void) stat; (void) cb; return CARD_RESULT_NOCARD; }
s32 CARDUnmount(s32 chan) { (void) chan; return CARD_RESULT_NOCARD; }
s32 CARDWriteAsync(void* fi, void* buf, s32 len, s32 ofs, void* cb) { (void) fi; (void) buf; (void) len; (void) ofs; (void) cb; return CARD_RESULT_NOCARD; }

}  // extern "C"
#endif  // RE4DC_VMU_SAVE
