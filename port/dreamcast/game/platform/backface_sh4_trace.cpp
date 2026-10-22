// CPU_BACKFACE=2 test builds only: hash pieces the assembly actually emitted.
// No facing test or classification is repeated here. The production kernel
// contains no hook call and does not link this translation unit.
#include <cstdint>
#include <cstring>
extern "C" void re4dc_ta_hash(const void*, unsigned);
extern "C" void re4dc_backface_sh4_trace(const void* cache,
                                         const uint8_t* indices,
                                         unsigned n, unsigned mask) {
    const auto* bytes = static_cast<const uint8_t*>(cache);
    const unsigned index_mask = mask & 255u;
    for (unsigned k = 0; k < n; ++k) {
        uint32_t words[8];
        std::memcpy(words, bytes + 32u * (indices[k] & index_mask), 32);
        if (index_mask == 127u) words[0] = 0xe0000000u;
        if (k + 1u == n) words[0] = 0xf0000000u;
        re4dc_ta_hash(words, 32);
    }
}
