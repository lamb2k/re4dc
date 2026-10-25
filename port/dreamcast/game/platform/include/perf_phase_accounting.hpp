#ifndef RE4DC_PERF_PHASE_ACCOUNTING_HPP
#define RE4DC_PERF_PHASE_ACCOUNTING_HPP
#include "perf_phase_miss.h"
#include <limits.h>

namespace re4dc { namespace ppm14 {
// These are integer accounting guards, not a cache/timing model. The generous
// ceiling rejects resets/torn-like values; it does not infer event latency.
inline bool counter_delta(uint64_t before, uint64_t after, uint64_t elapsed_us,
                          uint64_t& delta, bool& wrapped) {
    const uint64_t mask = (uint64_t(1) << 48) - 1;
    if ((before | after) & ~mask || elapsed_us > 60000000ULL) return false;
    delta = (after - before) & mask;
    wrapped = after < before;
    return delta <= (elapsed_us + 1000ULL) * 1024ULL;
}
inline bool accumulate(Snapshot& s, unsigned bin, uint64_t delta, bool wrapped) {
    if (bin >= BinCount || delta > UINT64_MAX - s.total ||
        delta > UINT64_MAX - s.bins[bin] || s.samples == UINT32_MAX ||
        (wrapped && s.wraps == UINT32_MAX)) return false;
    s.total += delta; s.bins[bin] += delta; ++s.samples; s.wraps += wrapped;
    return true;
}
inline unsigned effective_bin(unsigned state) {
    const unsigned path = state & 7U, phase = (state >> 3) & 7U, wait = (state >> 6) & 3U;
    if (wait) return WaitBase + wait - 1;
    if (!path) return Residual;
    return path <= wc24::PathCount && phase < wc24::PhaseCount ?
        (path - 1) * wc24::PhaseCount + phase : unsigned(BinCount);
}
} }
#endif
