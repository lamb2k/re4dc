#pragma once
// Enabled Build17 boot-table check. No offset arithmetic before its bounds.
#include <stdint.h>
#include <string.h>

namespace re4dc { namespace disc_pio {
inline uint32_t table_word(const unsigned char* p) {
    uint32_t value;
    memcpy(&value, p, sizeof(value));
    return value;
}
inline bool stream_table_valid(const void* buffer, int length, unsigned rit_alignment) {
    if (!buffer || length < 12 || !rit_alignment) return false;
    const auto* data = static_cast<const unsigned char*>(buffer);
    const uint32_t size = (uint32_t) length;
    for (unsigned b = 0; b < 2; ++b) {
        const uint32_t offset = table_word(data + 4 * b);
        if ((offset & 3u) || offset > size - 12u) return false;
        const unsigned char* h = data + offset;
        const uint32_t count = table_word(h), first = table_word(h + 4), second = table_word(h + 8);
        if (count > 0x10000u || (first & 3u) || second % rit_alignment ||
            first >= size - offset || second >= size - offset) return false;
    }
    return true;
}
}}
