// vib_table.h (lane eng-e1h): the core archive's rumble table (core.das, section VIB: VibDataTbl, then each pattern's
// VibData) in the machine's byte order. The disc tree carries that section in the GameCube's big-endian order (the
// tree's converter left it as it was: the offsets read 0x04010000 for 0x104, the first pattern's count 0x01000000), so a
// pattern address fell outside the archive: the PC reference crashed on the first shot's rumble, and the engine image
// read rumble patterns from wherever the bad address pointed. Both loaders (hostref/host_glue.cpp, core/loader.cpp)
// convert the section in place once at load. A table already in the machine's order is left as it is.
#pragma once
#include <stdint.h>

namespace vib_table {

inline uint32_t bswap32(uint32_t v) { return (v >> 24) | ((v >> 8) & 0xFF00u) | ((v << 8) & 0xFF0000u) | (v << 24); }
inline uint16_t bswap16(uint16_t v) { return (uint16_t) ((v >> 8) | (v << 8)); }

// 1 when the table at t (bytes long) read in the machine's order is not a table and byte-swapped is one.
inline int swapped(const void* t, uint32_t bytes)
{
    if (!t || bytes < 4) return 0;
    const uint32_t n = *(const uint32_t*) t;
    return n > 0xFFFFu && bswap32(n) <= 0xFFFFu && 4 + 4 * bswap32(n) <= bytes;
}

// Converts the table and every pattern it points at (each once, whatever shares it). Returns the patterns converted,
// 0 when the table was already in the machine's order, -1 when it is not a table (an offset or a count runs past
// `bytes`; nothing past that point is touched).
inline int to_host(void* t, uint32_t bytes)
{
    if (!swapped(t, bytes)) return 0;
    uint8_t* base = (uint8_t*) t;
    uint32_t* w = (uint32_t*) t;
    const uint32_t n = bswap32(w[0]);
    w[0] = n;
    for (uint32_t i = 0; i < n; i++) w[1 + i] = bswap32(w[1 + i]);
    int done = 0;
    for (uint32_t i = 0; i < n; i++) {
        const uint32_t o = w[1 + i];
        if (!o) continue;
        int seen = 0;
        for (uint32_t j = 0; j < i; j++) seen |= w[1 + j] == o;
        if (seen) continue;
        if (o + 4 > bytes) return -1;
        uint32_t* d = (uint32_t*) (base + o);
        const uint32_t m = bswap32(d[0]);
        if (o + 4 + 8 * m > bytes) return -1;
        d[0] = m;
        uint16_t* e = (uint16_t*) (d + 1);
        for (uint32_t k = 0; k < m; k++, e += 4) {   // {u16 type, u16 wait, u16 time, u8 lvl0, u8 lvl1}
            e[0] = bswap16(e[0]);
            e[1] = bswap16(e[1]);
            e[2] = bswap16(e[2]);
        }
        done++;
    }
    return done;
}

}   // namespace vib_table
