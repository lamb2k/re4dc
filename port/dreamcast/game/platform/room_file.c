/* room_file.c: the per-room data file (lane engine19; tools/enginebake/room_compile.py, R4RC v1), loaded at room entry.
 *
 * /cd/dc/native/rXXX/room.r4rc: a 64 B header, a section directory, 16 B aligned sections. Only the sections this
 * program uses are read (GRID with ENGINE_PREVIEW, OCCL with ENEMY_VIS_CULL=1, VIS with =2), into ONE heap-4 block
 * (re4dc_static_alloc: the native package reserve rules apply), freed at room leave. Every check failing (no file,
 * header, directory, extents, an unknown required section, no heap) leaves no section: the users run the source path.
 * Used by platform/actor_rt.c (GRID) and platform/room_vis.c (VIS). No allocation or file access after the entry. */
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <kos/fs.h>
#include "room_file.h"

extern void re4dc_log(const char* fmt, ...);
extern void* re4dc_static_alloc(unsigned bytes);
extern void re4dc_static_free(void* data);
extern int re4dc_static_heap_free(void);
#if defined(RE4DC_GC_ASSET_GATE) && RE4DC_GC_ASSET_GATE
extern void re4dc_gcasset_room_parent_retire(void); /* memory-only revocation */
#endif
#if defined(RE4DC_SCENERY21_AB) && RE4DC_SCENERY21_AB
extern char re4dc_bench_arm(void) __attribute__((weak));
#endif

#ifndef RE4DC_ROOMFILE_SCDD
#define RE4DC_ROOMFILE_SCDD 0   /* SCENERY_DEDUP=2 (lane scenery19): the scenery point-dedup section */
#endif
#ifndef RE4DC_ROOMFILE_SCCN
#define RE4DC_ROOMFILE_SCCN 0   /* SCENERY_CONE (lane scenery21): per strip group back-face cones */
#endif
#ifndef RE4DC_ROOMFILE_SCPS
#define RE4DC_ROOMFILE_SCPS 0   /* SCENERY_PIECE_STATE (lane scenery21): per part header-slot words (written at run time) */
#endif
#ifndef RE4DC_ROOMFILE_GRID
#define RE4DC_ROOMFILE_GRID 0
#endif
#ifndef RE4DC_ROOMFILE_VIS
#define RE4DC_ROOMFILE_VIS 0
#endif
#ifndef RE4DC_ROOMFILE_OCCL
#define RE4DC_ROOMFILE_OCCL 0
#endif

#define MAXSEC 8
static struct {
    unsigned room, nsec, bytes;
    uint8_t* block;
    re4dc_room_header hdr;
    struct { char tag[4]; uint16_t version, flags; uint8_t* data; uint32_t len; } sec[MAXSEC];
} rf;
static unsigned c_loads, c_absent, c_refused;

static inline uint16_t rd16(const uint8_t* p) { return (uint16_t) (p[0] | (p[1] << 8)); }
static inline uint32_t rd32(const uint8_t* p) { return (uint32_t) (p[0] | (p[1] << 8) | (p[2] << 16) | ((uint32_t) p[3] << 24)); }

static int wanted(const uint8_t* tag)
{
    if (RE4DC_ROOMFILE_GRID && !memcmp(tag, "GRID", 4)) return 1;
    if (RE4DC_ROOMFILE_VIS && !memcmp(tag, "VIS\0", 4)) return 1;
    if (RE4DC_ROOMFILE_OCCL && !memcmp(tag, "OCCL", 4)) return 1;
    if (RE4DC_ROOMFILE_SCDD && !memcmp(tag, "SCDD", 4)) return 1;
    if (RE4DC_ROOMFILE_SCCN && !memcmp(tag, "SCCN", 4)) return 1;
    if (RE4DC_ROOMFILE_SCPS && !memcmp(tag, "SCPS", 4)) return 1;
    return 0;
}
#if RE4DC_ROOMFILE_SCDD
const void* re4dc_room_file_block(void) { return rf.block; }
#endif

void re4dc_room_file_leave(void)
{
#if defined(RE4DC_GC_ASSET_GATE) && RE4DC_GC_ASSET_GATE
    re4dc_gcasset_room_parent_retire();
#endif
    if (rf.block) re4dc_static_free(rf.block);
    memset(&rf, 0, sizeof(rf));
}

void re4dc_room_file_enter(unsigned room)
{
#if defined(RE4DC_GC_ASSET_GATE) && RE4DC_GC_ASSET_GATE
    re4dc_gcasset_room_parent_retire();
#endif
    room &= 0xFFF;
    memset(&rf, 0, sizeof(rf));   /* the previous room's block was freed at re4dc_room_file_leave */
    rf.room = room;
    char path[40];
    snprintf(path, sizeof(path), "/cd/dc/native/r%03x/room.r4rc", room);
#if defined(RE4DC_SCENERY21_AB) && RE4DC_SCENERY21_AB
    /* SCENERY21_AB (bench disc): arm B reads the room's sc21 room file when it has one */
    file_t fd = FILEHND_INVALID;
    if (re4dc_bench_arm && re4dc_bench_arm() == 'B') {
        char apath[48];
        snprintf(apath, sizeof(apath), "/cd/dc/native/r%03x/sc21/room.r4rc", room);
        fd = fs_open(apath, O_RDONLY);
    }
    if (fd == FILEHND_INVALID) fd = fs_open(path, O_RDONLY);
#else
    file_t fd = fs_open(path, O_RDONLY);
#endif
    if (fd == FILEHND_INVALID) { c_absent++; re4dc_log("ROOMFILE r%03x absent: source path\n", room); return; }
    const unsigned size = (unsigned) fs_total(fd);
    uint8_t head[64 + 32 * MAXSEC];
    const char* why = 0;
    unsigned nsec = 0, need = 0;
    if (size < 64 || size > 1048576u || fs_read(fd, head, 64) != 64) why = "size";
    else if (memcmp(head, "R4RC", 4) || rd16(head + 4) != 1 || rd16(head + 6) != 64 || rd32(head + 8) != room ||
             rd32(head + 16) != size) why = "header";
    else if (!(nsec = rd32(head + 12)) || nsec > MAXSEC || fs_read(fd, head + 64, 32 * nsec) != (ssize_t) (32 * nsec))
        why = "directory";
    for (unsigned i = 0; !why && i < nsec; i++) {
        const uint8_t* d = head + 64 + 32 * i;
        const uint32_t off = rd32(d + 8), len = rd32(d + 12);
        if ((off & 15u) || off < 64u + 32u * nsec || off > size || len > size - off) why = "section extent";
        else if (wanted(d)) need += (len + 31u) & ~31u;
        else if ((rd16(d + 6) & 1) && memcmp(d, "SRCB", 4) && memcmp(d, "GRID", 4) && memcmp(d, "VIS\0", 4) &&
                 memcmp(d, "OCCL", 4))
            why = "unknown required section";
    }
    const int before = re4dc_static_heap_free();
    if (!why && need) {
        rf.block = (uint8_t*) re4dc_static_alloc(need);
        if (!rf.block) why = "heap4";
    }
    unsigned at = 0;
    for (unsigned i = 0; !why && i < nsec; i++) {
        const uint8_t* d = head + 64 + 32 * i;
        if (!wanted(d)) continue;
        const uint32_t off = rd32(d + 8), len = rd32(d + 12);
        if (fs_seek(fd, off, SEEK_SET) != (off_t) off || fs_read(fd, rf.block + at, len) != (ssize_t) len) { why = "read"; break; }
        memcpy(rf.sec[rf.nsec].tag, d, 4);
        rf.sec[rf.nsec].version = rd16(d + 4);
        rf.sec[rf.nsec].flags = rd16(d + 6);
        rf.sec[rf.nsec].data = rf.block + at;
        rf.sec[rf.nsec].len = len;
        rf.nsec++;
        at += (len + 31u) & ~31u;
    }
    fs_close(fd);
    if (why) {
#if defined(RE4DC_GC_ASSET_GATE) && RE4DC_GC_ASSET_GATE
        re4dc_gcasset_room_parent_retire();
#endif
        if (rf.block) re4dc_static_free(rf.block);
        memset(&rf, 0, sizeof(rf));
        c_refused++;
        re4dc_log("ROOMFILE r%03x %s: source path (bytes=%u heap4=%d)\n", room, why, size, before);
        return;
    }
    rf.room = room;
    rf.bytes = need;
    rf.hdr.w = rd16(head + 24); rf.hdr.h = rd16(head + 26);
    rf.hdr.cell_mm = rd32(head + 28);
    rf.hdr.x0 = (float) (int32_t) rd32(head + 32); rf.hdr.z0 = (float) (int32_t) rd32(head + 36);
    c_loads++;
    re4dc_log("ROOMFILE r%03x loaded file=%u read=%u sections=%u heap4=%d->%d loads=%u\n", room, size, need, rf.nsec, before,
              re4dc_static_heap_free(), c_loads);
}

const void* re4dc_room_section(const char tag[4], unsigned* len, unsigned* version, unsigned* flags,
                               const re4dc_room_header** hdr)
{
    for (unsigned i = 0; i < rf.nsec; i++)
        if (!memcmp(rf.sec[i].tag, tag, 4)) {
            *len = rf.sec[i].len; *version = rf.sec[i].version; *flags = rf.sec[i].flags; *hdr = &rf.hdr;
            return rf.sec[i].data;
        }
    return 0;
}

unsigned re4dc_room_file_room(void) { return rf.room; }
#if defined(RE4DC_GC_ASSET_GATE) && RE4DC_GC_ASSET_GATE
/* Exact currently borrowed section, not a full parent-file hash. Its owner's
 * mandatory retirement callback revokes old proof serials before reuse/free. */
int re4dc_gcasset_room_span(const void* data, unsigned bytes, unsigned version, unsigned flags, const void* header)
{
    const uintptr_t base = (uintptr_t)rf.block, at = (uintptr_t)data;
    if (!rf.block || !data || !bytes || header != &rf.hdr || at < base || at-base > rf.bytes || bytes > rf.bytes-(at-base)) return 0;
    for (unsigned i=0; i<rf.nsec; ++i)
        if (rf.sec[i].data == data && rf.sec[i].len == bytes && rf.sec[i].version == version && rf.sec[i].flags == flags) return 1;
    return 0;
}
#endif
