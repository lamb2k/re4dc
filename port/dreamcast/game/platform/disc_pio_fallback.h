#pragma once
// DISC_PIO_FALLBACK only. The native and synthetic drivers run this same
// command/ownership policy. No allocation, callback, worker or per-read log.
#include <stddef.h>
#include <stdint.h>

namespace re4dc { namespace disc_pio {

enum class Result { ok, io, timeout, missing, no_disc, disc_changed, unsafe, invalid, lock_timeout };
enum class Command { pending, done, failed, no_disc, disc_changed };
struct Request { void* buffer; uint32_t sector; size_t count; };
struct State {
    uint8_t failures = 0;
    bool session_pio = false;
    bool retry_pio = false;
    bool poisoned = false;
    bool validating = false;
    bool validation_dma = false;
    bool validation_fault = false;
    bool validation_rejected = false;

    void dma_failed() {
        if (failures < 2) ++failures;
        if (failures == 2) session_pio = true;
        if (validating) validation_fault = true;
    }
    void dma_succeeded() {
        // Landing is not acceptance while the caller still has a semantic
        // check to run. Otherwise two corrupt completed reads never latch.
        if (validating) validation_dma = true;
        else failures = 0;
    }
    void validation_begin() {
        validating = true;
        validation_dma = validation_fault = validation_rejected = false;
    }
    bool validation_reject() {
        if (!validating || validation_rejected) return false;
        const bool switching = !session_pio && !retry_pio;
        // A timed-out DMA already counted by read() is not a second failure.
        // Nor can a bad PIO result be called another failed DMA attempt.
        if (validation_dma && !validation_fault) dma_failed();
        validation_rejected = true;
        retry_pio = true;  // held across the whole logical-file reread
        return switching;
    }
    void validation_end() {
        if (validating && validation_dma && !validation_fault && !validation_rejected)
            failures = 0;
        validating = validation_dma = validation_fault = validation_rejected = false;
        retry_pio = false;  // session_pio, once set, is never cleared
    }
};

inline bool valid(const Request& r) {
    return r.buffer && !((uintptr_t) r.buffer & 1u) && r.count &&
           r.count <= UINT32_MAX / 2048u && r.count - 1 <= UINT32_MAX - r.sector;
}
inline unsigned timeout_ms(size_t count) { return 5000u + 8u * (unsigned) count; }

template<class Driver>
Result wait_command(Driver& d, int handle, unsigned limit) {
    const uint64_t start = d.now();
    for (unsigned spins = 0;; ++spins) {
        const Command s = d.check(handle);
        if (s == Command::done) return Result::ok;
        if (s == Command::failed) return Result::io;
        if (s == Command::no_disc) return Result::no_disc;
        if (s == Command::disc_changed) return Result::disc_changed;
        if (d.now() - start >= limit) return Result::timeout;
        d.pause(start, spins, false);
    }
}

template<class Driver>
bool wait_idle(Driver& d, unsigned limit) {
    const uint64_t start = d.now();
    for (unsigned spins = 0; d.engine_busy(); ++spins) {
        if (d.now() - start >= limit) return false;
        d.pause(start, spins, true);
    }
    return true;
}

// G1 is owned throughout. A failed retirement poisons the reader: the native
// caller must fail-stop without returning the possibly still-owned buffer.
template<class Driver>
bool retire(Driver& d, int handle) {
    d.disable_dma();
    bool aborted = true;
    if (handle > 0) {
        d.abort(handle);
        const Result r = wait_command(d, handle, 1000);
        aborted = r != Result::timeout;
    }
    if (!aborted || !wait_idle(d, 1000)) {
        d.reset();  // BIOS reset/init; each syscall must itself return
        if (!wait_idle(d, 1000)) return false;
        // A reset loses the data-sector mode. Restore it while still owning
        // G1, before any retry; the ordinary reinit wrapper would re-lock G1.
        const int init = d.submit_init();
        if (init <= 0 || wait_command(d, init, 6000) != Result::ok || !d.sector_mode_2048())
            return false;
    }
    if (!wait_idle(d, 1000)) return false;
    d.clear_events();  // only GD DMA completion/overrun/illegal-address bits
    d.enable_dma();
    return true;
}

template<class Driver>
Result transfer(Driver& d, const Request& r, bool dma, int& handle) {
    d.prepare(r, dma);
    const uint64_t start = d.now();
    for (unsigned spins = 0;; ++spins) {
        handle = d.submit(r, dma);
        if (handle > 0) break;
        if (d.now() - start >= 200) return Result::io;
        d.pause(start, spins, false);
    }
    const Result result = wait_command(d, handle, timeout_ms(r.count));
    if (result != Result::ok) return result;
    // Command completion is not permission to reuse a DMA destination.
    if (!wait_idle(d, 1000u + 8u * (unsigned) r.count)) return Result::timeout;
    const uint64_t landing = d.now();
    for (unsigned spins = 0; !d.landed(r); ++spins) {
        if (d.now() - landing >= 250) return Result::missing;
        d.pause(landing, spins, true);
    }
    d.clear_events();
    handle = 0;
    return Result::ok;
}

template<class Driver>
Result read(Driver& d, State& s, const Request& r, bool requested_dma) {
    if (!valid(r)) return Result::invalid;
    if (!d.acquire()) return Result::lock_timeout;
    if (s.poisoned) { d.release(); return Result::unsafe; }
    const bool dma = requested_dma && !((uintptr_t) r.buffer & 31u) &&
                     !s.session_pio && !s.retry_pio;
    int handle = 0;
    Result result = transfer(d, r, dma, handle);
    if (result == Result::ok) {
        if (dma) s.dma_succeeded();
        d.release();
        return result;
    }
    if (!retire(d, handle)) {
        s.poisoned = true;
        d.release();
        return Result::unsafe;
    }
    if (!dma || result == Result::no_disc || result == Result::disc_changed) {
        d.release();
        return result;
    }
    s.dma_failed();
    d.switched(result, s.session_pio, s.failures);
    // The request is immutable: exact original buffer, LBA and sector count.
    result = transfer(d, r, false, handle);
    if (result != Result::ok && !retire(d, handle)) {
        s.poisoned = true;
        result = Result::unsafe;
    }
    // Successful PIO does not clear the consecutive DMA-failure streak.
    d.release();
    return result;
}

}}  // namespace re4dc::disc_pio
