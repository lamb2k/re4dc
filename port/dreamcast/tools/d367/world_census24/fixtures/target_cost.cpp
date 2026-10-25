// Synthetic callers and explicit external edges for the Build 10 cost receipt.
// The census implementation is compiled separately, unchanged, with its real
// Dreamcast (not HOST) path. None of this fixture is linked into the game.
#include "platform/include/world_census24.h"
#include <kos/thread.h>
#include <arch/timer.h>
#include <stddef.h>
#include <stdint.h>

using namespace re4dc::wc24;

extern "C" {
uint64_t fixture_clock = 1000;
uint64_t fixture_clock_step = 0;
uint32_t fixture_words[4] = {0x80840012, 0x20800440, 0x00000521, 0x00000800};
Snapshot fixture_snapshot;
// The real core reads thd_current directly. It only compares this pointer;
// no synthetic thread object or scheduling work is executed.
kthread_t* thd_current = reinterpret_cast<kthread_t*>(0x220000);

__attribute__((noinline)) timer_val_t __dreamcast_get_ticks() {
    const uint32_t result = uint32_t(fixture_clock);
    fixture_clock += fixture_clock_step;
    // All fixture timestamps stay below one second and are even microseconds:
    // 2 us = 25 raw 80 ns ticks. The real KOS conversion remains in the core.
    return timer_val_t{0, result * 25u / 2u};
}
__attribute__((noinline)) void re4dc_wc24_identity(unsigned out[7]) {
    for (unsigned i = 0; i < 7; ++i) out[i] = 0x2400u + i;
}
__attribute__((noinline)) void re4dc_log(const char*, ...) {}
// Formatting is outside every priced region. The interpreter also skips the
// production summary entry during untimed sealing, before these varargs edges.
__attribute__((noinline)) int snprintf(char*, size_t, const char*, ...) { return 0; }
}

namespace {
unsigned next_tick;
uint32_t outer_token;
void completed() {
    decision(true);
    scene_finished();
    decision_posted(true);
    end_tick();
}
}

extern "C" {
extern const uint32_t fixture_layout[] = {
    1, sizeof(Snapshot), PathCount, PhaseCount, CounterCount,
    offsetof(Snapshot, ticks), offsetof(Snapshot, drawn),
    offsetof(Snapshot, errors), offsetof(Snapshot, wall_us),
    offsetof(Snapshot, phase_us), offsetof(Snapshot, counters),
    offsetof(Snapshot, residual_us), offsetof(Snapshot, wait_us),
};

// mode 0: 299 empty completed frames, followed by the measured frame.
// mode 1: one completed frame, so the measured begin_tick is an ordinary
// accumulation and never enters the once-per-window formatting branch.
__attribute__((noinline)) void fixture_prepare(unsigned mode) {
    fixture_clock = 1000;
    fixture_clock_step = 0;
    next_tick = 0;
    outer_token = UINT32_MAX;
    reset();
    for (unsigned i = 0; i < (mode ? 1u : 299u); ++i) {
        begin_tick(next_tick++, 0x101);
        completed();
    }
    if (!mode) begin_tick(next_tick++, 0x101);
}

__attribute__((noinline)) void fixture_open_outer() {
    outer_token = enter(NearOP, Selection);
}
__attribute__((noinline)) void fixture_close_outer() {
    if (outer_token != UINT32_MAX) leave(outer_token);
    outer_token = UINT32_MAX;
}

__attribute__((noinline)) void fixture_path_pair() { Scope scope(NearOP, Selection); }
__attribute__((noinline)) void fixture_phase_pair() { Scope scope(Transform); }
__attribute__((noinline)) void fixture_wait_pair() { WaitScope scope(PvrWait); }
__attribute__((noinline)) void fixture_phase_switch() { set_phase(Submit); }
__attribute__((noinline)) void fixture_count() { count(Corners, 32); }
__attribute__((noinline)) void fixture_header() { submitted_header(fixture_words); }
__attribute__((noinline)) void fixture_normal_tick() { begin_tick(next_tick++, 0x101); }

// An explicit hypothetical hook schedule, not a captured game frame:
// each piece has 3 nested phase scopes, 4 standalone counts, and one header;
// the frame has one additional outer world scope. No geometry is rendered.
__attribute__((noinline)) void fixture_frame(unsigned pieces) {
    Scope world(NearOP, Selection);
    for (unsigned i = 0; i < pieces; ++i) {
        count(PickedIndexed);
        {
            Scope transform(Transform);
            count(Transformed, 32);
        }
        {
            Scope header(HeaderMaterial);
            submitted_header(fixture_words);
        }
        {
            Scope submit(Submit);
            count(Corners, 32);
            count(StripInputs, 32);
        }
    }
}

// Untimed semantic observation through the public Snapshot API. Preparation
// frames have zero counters and zero elapsed time. Normal-tick tests need more
// empty frames here; the hot-hook tests seal on the first iteration.
__attribute__((noinline)) unsigned fixture_capture() {
    fixture_clock_step = 0;
    fixture_close_outer();
    completed();
    for (unsigned i = 0; i < 301; ++i) {
        begin_tick(next_tick++, 0x101);
        if (snapshot(&fixture_snapshot)) return 1;
        completed();
    }
    return 0;
}

// Keeps the exact production summary entry available to the interpreter's
// explicitly untimed formatting trap without relying on C++ mangling strings.
extern const uintptr_t fixture_summary_entry = reinterpret_cast<uintptr_t>(&summary);
}
