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

