#pragma once

#include <atomic>
#include <cstdint>

namespace re4dc { namespace log_publication16 {
// No blocking locks or application retry loops. The selected SH-4 compiler's
// lock-free atomics require KOS exception-entry soft-gUSA rollback support.
static_assert(ATOMIC_BOOL_LOCK_FREE == 2 && ATOMIC_INT_LOCK_FREE == 2,
              "logger requires lock-free bool and unsigned atomics");
constexpr unsigned window = 255;
enum Result : unsigned { accepted, busy, context, invalid, terminal, abandoned, results };

// Copied evidence only: never retain a context/stack/file pointer for a reader.
// Two first-claim slots, each immutable after ready publication. A nested fault
// can publish the second slot even if the first writer cannot return.
struct Evidence {
    std::uint32_t kind, code, pc, pr, sp, sr, expevt, tea, inside, flags;
    std::uint32_t thread, tid, stack, stack_bytes, frame, r[16];
    char file[64];
};
static_assert(sizeof(Evidence) == 188, "fixed copied evidence layout");
struct Slot {
    std::atomic_flag claimed = ATOMIC_FLAG_INIT;
    std::atomic<bool> ready{false};
    Evidence evidence{};
};
struct State {
    std::atomic_flag writer = ATOMIC_FLAG_INIT;
    std::atomic<bool> stopped{false};
    // Sticky seen/lost state, not counters or whole-record certificates. These
    // idempotent stores cannot wrap or lose an overflow marker to abandonment.
    std::atomic<unsigned> outcome[results]{};
    std::atomic<unsigned> evidence_lost{0};
    Slot slots[2];

    Result report(Result result) { outcome[result].store(1, std::memory_order_relaxed); return result; }
    Result claim() {
        if (stopped.load(std::memory_order_acquire)) return terminal;
        if (writer.test_and_set(std::memory_order_acquire)) return busy;
        if (stopped.load(std::memory_order_acquire)) {
            release();
            return terminal;
        }
        return accepted;
    }
    void release() { writer.clear(std::memory_order_release); }
    bool capture(const Evidence& source) {
        for (auto& slot : slots) {
            if (!slot.claimed.test_and_set(std::memory_order_acquire)) {
                slot.evidence = source;
                slot.ready.store(true, std::memory_order_release);
                return true;
            }
        }
        evidence_lost.store(1, std::memory_order_release);
        return false;
    }
};

// Fixed automatic encoder; no libc or retained pointers in fault/halt logging.
struct Line {
    char bytes[window];
    unsigned size = 0;
    void text(const char* source) {
        while (*source && size < window) bytes[size++] = *source++;
    }
    void hex(std::uint32_t value) {
        constexpr char digits[] = "0123456789abcdef";
        for (int shift = 28; shift >= 0 && size < window; shift -= 4)
            bytes[size++] = digits[(value >> shift) & 15];
    }
};
}} // namespace re4dc::log_publication16

extern "C" {
extern re4dc::log_publication16::State re4dc_log_publication16_state;
int re4dc_log_write16(const char*, unsigned long);
int re4dc_log_terminal16(const re4dc::log_publication16::Evidence*);
}
