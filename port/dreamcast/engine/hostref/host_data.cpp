// hostref: the game data the player and camera read, from a converted (little-endian, Dreamcast) data
// tree on the PC: the core archive (etc/core.das), the player archive (em/pl00.drs), the weapon archive
// (em/wepNN.drs) and the room archive (stN/rNNN.arc, already decoded). The DVD container (dvd.cpp
// cDvdQueue::readMain: 32 bytes of magic, then 32-byte DvdHeader entries to 0xFFFFFFFF) is walked as the
// game walks it: every type-0 part goes to main RAM, one after the other, 32-aligned; nested headers
// (type 4) one level deep; sound and ARAM parts are skipped (no audio in the reference).
// Private game data: nothing here is committed; the tree is a command-line argument.
// PC side (system headers); host_glue.cpp sets the game's pointers from what this loads.
#include "hostref.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

namespace {
struct File {
    uint8_t* data = 0;
    uint32_t size = 0;
};
File read_file(const char* tree, const char* name)
{
    char path[1024];
    snprintf(path, sizeof path, "%s/%s", tree, name);
    File f;
    FILE* fp = fopen(path, "rb");
    if (!fp) return f;
    fseek(fp, 0, SEEK_END);
    f.size = (uint32_t) ftell(fp);
    fseek(fp, 0, SEEK_SET);
    f.data = (uint8_t*) malloc(f.size ? f.size : 1);
    if (fread(f.data, 1, f.size, fp) != f.size) { free(f.data); f.data = 0; f.size = 0; }
    fclose(fp);
    return f;
}
// Open name, or name with its extension replaced by .drs / .das (the Dreamcast tree renames them).
File read_any(const char* tree, const char* name, char* used, size_t used_len)
{
    File f = read_file(tree, name);
    if (f.data) { snprintf(used, used_len, "%s", name); return f; }
    char alt[256];
    snprintf(alt, sizeof alt, "%s", name);
    char* dot = strrchr(alt, '.');
    if (dot) {
        static const char* const exts[2] = {".drs", ".das"};
        for (const char* ext : exts) {
            strcpy(dot, ext);
            f = read_file(tree, alt);
            if (f.data) { snprintf(used, used_len, "%s", alt); return f; }
        }
    }
    used[0] = 0;
    return f;
}

// Size of the main-RAM parts of a DVD container (what ReadCheckInfo's size[0][*] add up to).
uint32_t container_mram(const File& f, uint32_t base, int depth)
{
    uint32_t total = 0;
    for (uint32_t h = base + 0x20; h + 0x20 <= f.size; h += 0x20) {
        const uint32_t* e = (const uint32_t*) (f.data + h);
        if (e[0] == 0xFFFFFFFFu) break;
        if (e[0] == 0 && e[2] == 0) total += (e[1] + 31u) & ~31u;
        if (e[0] == 4 && depth == 0) total += container_mram(f, base + e[3], 1);
    }
    return total;
}
// Copies the main-RAM parts to dst; returns the bytes placed (32-aligned steps, as m_MramAddr).
uint32_t container_place(const File& f, uint32_t base, int depth, uint8_t* dst, uint32_t at, uint32_t* first)
{
    for (uint32_t h = base + 0x20; h + 0x20 <= f.size; h += 0x20) {
        const uint32_t* e = (const uint32_t*) (f.data + h);
        if (e[0] == 0xFFFFFFFFu) break;
        if (e[0] == 0 && e[2] == 0) {
            const uint32_t ofs = base + e[3];
            if (ofs + e[1] > f.size) { fprintf(stderr, "re4ref: container part beyond the file\n"); exit(2); }
            memcpy(dst + at, f.data + ofs, e[1]);
            if (first && *first == 0xFFFFFFFFu) *first = e[1];
            at += (e[1] + 31u) & ~31u;
        } else if (e[0] == 4 && depth == 0) {
            at = container_place(f, base + e[3], 1, dst, at, first);
        }
    }
    return at;
}
}   // namespace

// Loads `name` into a fresh data-region block; returns it (0 when the file is missing).
extern "C" void* host_load_data(const char* tree, const char* name, const char* why, uint32_t* bytes)
{
    char used[256];
    File f = read_any(tree, name, used, sizeof used);
    if (!f.data) {
        fprintf(stderr, "re4ref: %s: %s not in %s\n", why, name, tree);
        return 0;
    }
    void* dst;
    uint32_t n;
    // A .das / .drs file is a DVD container (dvd.cpp skips its 32-byte lead-in without checking it:
    // most carry CA B6 BE 20, the weapon archives a text banner); anything else is a plain file.
    const char* ext = strrchr(used, '.');
    const bool container = ext && (!strcmp(ext, ".das") || !strcmp(ext, ".drs"));
    if (container && f.size >= 0x40) {
        n = container_mram(f, 0, 0);
        dst = host_fixed(n, why);
        container_place(f, 0, 0, (uint8_t*) dst, 0, 0);
    } else {
        n = f.size;
        dst = host_fixed(n, why);
        memcpy(dst, f.data, n);
    }
    host_log("data: %s %s -> %08x (%u bytes)", why, used, (unsigned) (uintptr_t) dst, n);
    free(f.data);
    if (bytes) *bytes = n;
    return dst;
}

// ---- motion keys of the Dreamcast tree's prepared enemy archives (lane eng-host2) ----
// The converted enemy archives (em/emNN.drs, em/pl11.drs) end their tag table with "MTC" (R4MOTBL): each FCV
// clip in the archive is a proxy that keeps the clip's header and axis table, and the full clip (keys
// included) is a file of its own, dc/mot/<crc32>-<fnv1a>.fcv. The old port's motion service
// (native_motion.cpp: re4dc_motion_bind / re4dc_motion_acquire, reached by motion.cpp's Re4dcMotionLease
// with every knob off) loads that file and hands motion.cpp the clip's key table with the offsets made
// absolute. The reference does the same, once per clip, with the same identity checks. Archives without an
// MTC tag (core, pl00, wep02) keep their own keys (acquire answers 0, as before).
namespace {
uint32_t word_le(const uint8_t* p) { uint32_t v; memcpy(&v, p, 4); return v; }
struct MotionBinding {
    const uint8_t* archive;
    uint32_t bytes;
    const uint8_t* records;   // MTC + 32: 20-byte records (offset, size, crc32, fnv1a, flags)
    uint32_t count;
    uint8_t** loaded;         // per record: the loaded clip (0 until first use)
};
MotionBinding g_bind[8];
const char* g_mot_tree;
uint32_t prefix_bytes(const uint8_t* p) { const uint32_t n = p[2]; return ((3 + 3 * n + 3) & ~3u) + 4 + 4 * n; }
uint32_t crc32le(const uint8_t* p, uint32_t n)
{
    uint32_t c = 0xFFFFFFFFu;
    for (uint32_t i = 0; i < n; i++) {
        c ^= p[i];
        for (int k = 0; k < 8; k++) c = (c >> 1) ^ (0xEDB88320u & (0u - (c & 1u)));
    }
    return ~c;
}
}

extern "C" void host_motion_bind(const char* tree, void* archive, uint32_t bytes)
{
    g_mot_tree = tree;
    const uint8_t* a = (const uint8_t*) archive;
    const uint32_t n = word_le(a);
    if (bytes < 16 || n > (bytes - 16) / 8) return;
    for (uint32_t i = 0; i < n; i++) {
        if (memcmp(a + 16 + 4 * n + 4 * i, "MTC", 4)) continue;
        const uint8_t* mtc = a + word_le(a + 16 + 4 * i);
        if (memcmp(mtc, "R4MOTBL\0", 8)) { host_log("motion: MTC without R4MOTBL"); return; }
        for (MotionBinding& b : g_bind) {
            if (b.archive) continue;
            b.archive = a;
            b.bytes = bytes;
            b.count = word_le(mtc + 12);
            b.records = mtc + 32;
            b.loaded = (uint8_t**) calloc(b.count, sizeof(uint8_t*));
            host_log("motion: archive %08x bound, %u clips with separate keys", (unsigned) (uintptr_t) a, b.count);
            return;
        }
        host_fatal(2, "motion: too many prepared archives");
    }
}

extern "C" int re4dc_motion_acquire(const void* header, unsigned** table)
{
    const uintptr_t p = (uintptr_t) header;
    for (MotionBinding& b : g_bind) {
        const uintptr_t base = (uintptr_t) b.archive;
        if (!base || p < base || p - base >= b.bytes) continue;
        const uint32_t want = (uint32_t) (p - base);
        for (uint32_t i = 0; i < b.count; i++) {
            const uint8_t* e = b.records + 20 * i;
            if (word_le(e) != want) continue;
            if (!b.loaded[i]) {
                const uint32_t size = word_le(e + 4);
                char name[64];
                snprintf(name, sizeof name, "dc/mot/%08x-%08x.fcv", word_le(e + 8), word_le(e + 12));
                File f = read_file(g_mot_tree, name);
                if (!f.data || f.size != size) host_fatal(2, "motion: %s missing or %u bytes (want %u)", name, f.size, size);
                uint32_t fnv = 2166136261u;
                for (uint32_t j = 0; j < size; j++) fnv = (fnv ^ f.data[j]) * 16777619u;
                const uint32_t head = prefix_bytes(b.archive + want);
                if (crc32le(f.data, size) != word_le(e + 8) || fnv != word_le(e + 12) || memcmp(b.archive + want, f.data, head))
                    host_fatal(2, "motion: %s identity or header mismatch", name);
                uint8_t* data = (uint8_t*) host_fixed((size + 31) & ~31u, "motion keys");
                memcpy(data, f.data, size);
                free(f.data);
                uint32_t* t = (uint32_t*) (data + head - 4 * data[2]);
                for (uint32_t j = 0; j < data[2]; j++) {
                    if (t[j] < head || t[j] >= size) host_fatal(2, "motion: %s key offset", name);
                    t[j] = (uint32_t) (uintptr_t) data + t[j];
                }
                b.loaded[i] = data;
            }
            const uint8_t* d = b.loaded[i];
            *table = (unsigned*) (d + prefix_bytes(d) - 4 * d[2]);
            return 1;
        }
        return 0;   // a clip the MTC table does not list keeps its keys in the archive (native_motion.cpp: no lease)
    }
    return 0;   // an archive with its own keys
}

extern "C" void re4dc_motion_release(int) {}

