// WORLD_CENSUS24: bounded, observation-only world accounting. See Build 10.
#include "platform/include/world_census24.h"
#include <stdio.h>
#include <string.h>
#include <limits.h>
#if defined(RE4DC_PERF_PHASE_MISS) && RE4DC_PERF_PHASE_MISS
#include "platform/include/perf_phase_miss.h"
#endif

#ifndef RE4DC_WORLD_CENSUS24_WINDOW
#define RE4DC_WORLD_CENSUS24_WINDOW 300
#endif
#if RE4DC_WORLD_CENSUS24_WINDOW < 300 || RE4DC_WORLD_CENSUS24_WINDOW > 600
#error WORLD_CENSUS24_WINDOW must be between 300 and 600 drawn frames
#endif

#if defined(RE4DC_WORLD_CENSUS24_HOST)
extern "C" uint64_t re4dc_wc24_test_clock();
extern "C" uintptr_t re4dc_wc24_test_thread();
extern "C" void re4dc_wc24_test_log(const char*);
static uint64_t clock_us() { return re4dc_wc24_test_clock(); }
static uintptr_t thread_id() { return re4dc_wc24_test_thread(); }
static unsigned lock_irq() { return 0; }
static void unlock_irq(unsigned) {}
static void print_line(const char* s) { re4dc_wc24_test_log(s); }
#else
#include <arch/timer.h>
#include <kos/irq.h>
#include <kos/thread.h>
extern "C" void re4dc_log(const char*, ...);
static uint64_t clock_us() { return timer_us_gettime64(); }
static uintptr_t thread_id() { return reinterpret_cast<uintptr_t>(thd_current); }
static unsigned lock_irq() { return irq_disable(); }
static void unlock_irq(unsigned mask) { irq_restore(mask); }
static void print_line(const char* s) { re4dc_log("%s\n", s); }
#endif

namespace re4dc { namespace wc24 {
namespace {
const uint32_t NoToken = UINT32_MAX;
struct Frame {
    uint64_t begin, last;
    uint64_t phase_us[PathCount][PhaseCount], wait_us[WaitCount];
    uint32_t counters[PathCount][CounterCount];
    uint32_t header[PathCount][4], header_valid;
    uint32_t tick, scenes, present, discard, errors;
    bool active, complete, attempt, finished;
};
Frame current;
Snapshot window, sealed;
uint32_t key[IdentityWords], sequence, epoch = 1, state;
uintptr_t owner;
bool have_key, have_sealed;
volatile bool paused, gpu_armed;

// Only pvr_event writes these with IRQs masked. Thread-side snapshots/reset
// use the same lock; 64-bit SH4 accesses are never assumed atomic.
Presentation gpu;
uint32_t gpu_fields, last_flip_field;
uint64_t last_flip_us;
bool have_flip;

bool ours() { return current.active && !paused && owner == thread_id(); }
unsigned path_word() { return state & 7u; }
unsigned phase_word() { return (state >> 3) & 7u; }
unsigned wait_word() { return (state >> 6) & 3u; }
unsigned depth() { return (state >> 8) & 63u; }
void bump_epoch() { epoch = (epoch + 1u) & 65535u; if (!epoch) epoch = 1; }

void charge(uint64_t now) {
    if (now < current.last) { ++current.errors; current.last = now; return; }
    const uint64_t delta = now - current.last;
    current.last = now;
    const unsigned wait = wait_word(), path = path_word();
    if (wait) current.wait_us[wait - 1] += delta;
    else if (path) current.phase_us[path - 1][phase_word()] += delta;
}

void clear_gpu(bool boundary) {
    const unsigned irq = lock_irq();
    gpu = Presentation{};
    if (boundary) { gpu_fields = 0; last_flip_field = 0; last_flip_us = 0; have_flip = false; gpu_armed = false; }
    unlock_irq(irq);
}

void clear_collection(bool clear_snapshot) {
#if defined(RE4DC_PERF_PHASE_MISS) && RE4DC_PERF_PHASE_MISS
    ppm14::abandon(clear_snapshot);
#endif
    current = Frame{};
    window = Snapshot{};
    state = 0;
    bump_epoch();
    clear_gpu(true);
    if (clear_snapshot) have_sealed = false;
}

uint64_t sum_phase(const Snapshot& s, unsigned phase) {
    uint64_t result = 0;
    for (unsigned path = 0; path < PathCount; ++path) result += s.phase_us[path][phase];
    return result;
}
uint64_t sum_counter(const Snapshot& s, unsigned counter) {
    uint64_t result = 0;
    for (unsigned path = 0; path < PathCount; ++path) result += s.counters[path][counter];
    return result;
}
uint64_t world_time(const Snapshot& s) {
    uint64_t result = 0;
    for (unsigned phase = 0; phase < PhaseCount; ++phase) result += sum_phase(s, phase);
    return result;
}
uint64_t wait_time(const Snapshot& s) {
    uint64_t result = 0;
    for (unsigned wait = 0; wait < WaitCount; ++wait) result += s.wait_us[wait];
    return result;
}
unsigned mean(uint64_t total, unsigned n) {
    if (!n) return 0;
    const uint64_t value = total / n;
    return value > UINT_MAX ? UINT_MAX : unsigned(value);
}

void finish_tick(uint64_t now) {
#if defined(RE4DC_PERF_PHASE_MISS) && RE4DC_PERF_PHASE_MISS
    ppm14::finish_tick(now);
#endif
    charge(now);
    if (depth()) ++current.errors;
    const uint64_t wall = now >= current.begin ? now - current.begin : 0;
    if (now < current.begin) ++current.errors;
    if (!window.ticks) window.first_tick = current.tick;
    window.last_tick = current.tick;
    ++window.ticks;
    window.draw_attempts += current.attempt;
    window.skipped += !current.attempt;
    window.drawn += current.finished;
    window.scenes += current.scenes;
    window.present_requests += current.present;
    window.discard_requests += current.discard;
    window.errors += current.errors;
    window.wall_us += wall;
    if (wall > window.max_tick_us) window.max_tick_us = wall;
    uint64_t named = 0;
    for (unsigned path = 0; path < PathCount; ++path) {
        for (unsigned phase = 0; phase < PhaseCount; ++phase) {
            const uint64_t value = current.phase_us[path][phase];
            window.phase_us[path][phase] += value;
            named += value;
        }
        for (unsigned counter = 0; counter < CounterCount; ++counter)
            window.counters[path][counter] += current.counters[path][counter];
    }
    for (unsigned wait = 0; wait < WaitCount; ++wait) {
        window.wait_us[wait] += current.wait_us[wait]; named += current.wait_us[wait];
    }
    // Signed residual: a broken partition must remain visible, never clamped.
    window.residual_us += int64_t(wall) - int64_t(named);
    if (named > wall) ++window.errors;
    current.active = false;
    if (window.drawn < RE4DC_WORLD_CENSUS24_WINDOW) return;
    window.sequence = ++sequence;
    for (unsigned k = 0; k < IdentityWords; ++k) window.identity[k] = key[k];
    const unsigned irq = lock_irq();
    window.presentation = gpu;
    gpu = Presentation{}; // intervals belong to the window in which they end
    unlock_irq(irq);
    sealed = window;
#if defined(RE4DC_PERF_PHASE_MISS) && RE4DC_PERF_PHASE_MISS
    ppm14::seal(sealed);
#endif
    have_sealed = true;
    window = Snapshot{};
    char line[240];
    summary(line, sizeof(line));
    print_line(line); // once/window; this cost belongs to the next tick
}

uint32_t enter_state(unsigned next) {
    if (!ours()) return NoToken;
    if (depth() == 63) { ++current.errors; return NoToken; }
#if defined(RE4DC_PERF_PHASE_MISS) && RE4DC_PERF_PHASE_MISS
    const uint64_t now = clock_us();
    ppm14::transition(next,now);
    charge(now);
#else
    charge(clock_us());
#endif
    const uint32_t token = (epoch << 16) | state;
    state = (next & 255u) | ((depth() + 1u) << 8);
    return token;
}
} // namespace

void begin_tick(uint32_t tick, uint32_t room) {
    const uint64_t now = clock_us();
    unsigned fresh[IdentityWords]; fresh[0] = room;
    re4dc_wc24_identity(fresh + 1);
    bool same = have_key;
    for (unsigned k = 0; k < IdentityWords; ++k) if (fresh[k] != key[k]) same = false;
    if (!same) {
        clear_collection(true);
        for (unsigned k = 0; k < IdentityWords; ++k) key[k] = fresh[k];
        have_key = true;
    } else if (current.active) {
        if (current.complete && !paused && owner == thread_id()) finish_tick(now);
        else clear_collection(false); // no partial/restarted/paused sample
    }
    current = Frame{};
    bump_epoch(); // a stale scope must never restore state in a later tick
    current.begin = current.last = now;
    current.tick = tick;
    current.active = true;
    owner = thread_id();
    state = 0;
    paused = false;
    gpu_armed = true;
#if defined(RE4DC_PERF_PHASE_MISS) && RE4DC_PERF_PHASE_MISS
    ppm14::begin_tick(now);
#endif
}
void end_tick() { if (ours()) current.complete = true; }
void decision(bool attempt) { if (ours()) current.attempt = attempt; }
void scene_finished() { if (ours()) { current.finished = true; ++current.scenes; } }
void decision_posted(bool present) {
    if (ours()) { if (present) ++current.present; else ++current.discard; }
}
void fault() { if (ours()) ++current.errors; }
void pause() { paused = true; clear_collection(false); }
void resume() { clear_collection(false); paused = false; }
void reset() { clear_collection(true); have_key = false; paused = false; }

uint32_t enter(Path path, Phase phase) {
    if (unsigned(path) >= PathCount || unsigned(phase) >= PhaseCount) return NoToken;
    return enter_state((state & 192u) | (unsigned(path) + 1u) | (unsigned(phase) << 3));
}
uint32_t enter(Phase phase) {
    if (!path_word() || unsigned(phase) >= PhaseCount) return NoToken;
    return enter_state((state & 199u) | (unsigned(phase) << 3));
}
uint32_t enter_wait(Wait wait) {
    if (unsigned(wait) >= WaitCount) return NoToken;
    return enter_state((state & 63u) | ((unsigned(wait) + 1u) << 6));
}
void leave(uint32_t token) {
    if (token == NoToken || !ours() || (token >> 16) != epoch) return;
    const unsigned previous = token & 65535u;
    if (((previous >> 8) & 63u) + 1u != depth()) { ++current.errors; return; }
#if defined(RE4DC_PERF_PHASE_MISS) && RE4DC_PERF_PHASE_MISS
    const uint64_t now = clock_us();
    ppm14::transition(previous,now);
    charge(now);
#else
    charge(clock_us());
#endif
    state = previous;
}
void set_phase(Phase phase) {
    if (!ours() || !path_word() || unsigned(phase) >= PhaseCount) return;
#if defined(RE4DC_PERF_PHASE_MISS) && RE4DC_PERF_PHASE_MISS
    const uint64_t now = clock_us();
    ppm14::transition((state & ~56u) | (unsigned(phase) << 3),now);
    charge(now);
#else
    charge(clock_us());
#endif
    state = (state & ~56u) | (unsigned(phase) << 3);
}
void count(Counter counter, uint32_t amount) {
    if (!ours() || !path_word() || unsigned(counter) >= CounterCount) return;
    uint32_t& value = current.counters[path_word() - 1][counter];
    if (amount > UINT32_MAX - value) { ++current.errors; value = UINT32_MAX; }
    else value += amount;
}
void submitted_header(const uint32_t words[4]) {
    if (!ours() || !path_word()) return;
    const unsigned path = path_word() - 1;
    bool changed = !(current.header_valid & (1u << path));
    for (unsigned k = 0; k < 4; ++k) {
        if (current.header[path][k] != words[k]) changed = true;
        current.header[path][k] = words[k];
    }
    current.header_valid |= 1u << path;
    count(Headers);
    if (changed) count(MaterialChanges);
}

void pvr_event(unsigned event) {
    if (!gpu_armed || paused) return;
    if (event != 1 && event != 6 && event != 7 && event != 8) return;
    const unsigned irq = lock_irq();
    if (event == 1) { ++gpu.vblanks; ++gpu_fields; }
    else if (event == 6) ++gpu.render_starts;
    else if (event == 7) ++gpu.render_dones;
    else {
        const uint64_t now = clock_us();
        ++gpu.flips;
        if (have_flip && now >= last_flip_us) {
            const uint64_t delta = now - last_flip_us;
            const unsigned fields = gpu_fields - last_flip_field;
            if (!gpu.intervals || delta < gpu.min_interval_us) gpu.min_interval_us = delta;
            if (delta > gpu.max_interval_us) gpu.max_interval_us = delta;
            gpu.interval_us += delta; ++gpu.intervals;
            if (fields > 2) ++gpu.gaps_over_two_fields;
            if (fields > gpu.max_fields) gpu.max_fields = fields;
        } else if (have_flip) ++gpu.discontinuities;
        have_flip = true; last_flip_us = now; last_flip_field = gpu_fields;
    }
    unlock_irq(irq);
}

int snapshot(Snapshot* out) {
    if (!have_sealed) return 0;
    if (out) *out = sealed;
    return 1;
}
int summary(char* out, unsigned capacity) {
    if (!capacity) return 0;
    if (!have_sealed) return snprintf(out, capacity, "WC24 collecting target=%u drawn", unsigned(RE4DC_WORLD_CENSUS24_WINDOW));
    const Snapshot& s = sealed;
    // Per-drawn means, plus both denominators. Full raw totals/pass matrix are
    // retained in Snapshot/QA. Stay within re4dc_log's 256-byte buffer.
    const int n = snprintf(out, capacity,
        "WC24 q=%u room=%03x t=%u d=%u wall=%u world=%u phase=%u,%u,%u,%u,%u,%u wait=%u residual=%lld v=%u c=%u h=%u m=%u pick=%u,%u,%u flip=%u gap=%u err=%u",
        s.sequence, s.identity[0], s.ticks, s.drawn, mean(s.wall_us,s.drawn), mean(world_time(s),s.drawn),
        mean(sum_phase(s,0),s.drawn),mean(sum_phase(s,1),s.drawn),mean(sum_phase(s,2),s.drawn),
        mean(sum_phase(s,3),s.drawn),mean(sum_phase(s,4),s.drawn),mean(sum_phase(s,5),s.drawn),
        mean(wait_time(s),s.drawn), static_cast<long long>(s.drawn?s.residual_us/int64_t(s.drawn):0),
        mean(sum_counter(s,Transformed),s.drawn),mean(sum_counter(s,Corners),s.drawn),
        mean(sum_counter(s,Headers),s.drawn),mean(sum_counter(s,MaterialChanges),s.drawn),
        mean(sum_counter(s,PickedIndexed),s.drawn),mean(sum_counter(s,PickedPlain),s.drawn),
        mean(sum_counter(s,PickedEmpty),s.drawn),s.presentation.flips,s.presentation.gaps_over_two_fields,s.errors);
    if (n < 0 || unsigned(n) >= capacity) return snprintf(out, capacity,
        "WC24 q=%u t=%u d=%u summary_overflow=1 full=QA", s.sequence,s.ticks,s.drawn);
    return n;
}
#if defined(RE4DC_PERF_PHASE_MISS) && RE4DC_PERF_PHASE_MISS
unsigned line_count() { return 25 + ppm14::line_count(); }
#else
unsigned line_count() { return 25; }
#endif
int format_line(unsigned row, char* out, unsigned capacity) {
#if defined(RE4DC_PERF_PHASE_MISS) && RE4DC_PERF_PHASE_MISS
    if (row >= 25) return ppm14::format_line(row-25,out,capacity);
#endif
    if (!capacity) return 0;
    out[0] = 0;
    if (!have_sealed) {
        if (!row) return snprintf(out,capacity,"WORLD CENSUS collecting %u/%u drawn (%u ticks)",
            window.drawn,unsigned(RE4DC_WORLD_CENSUS24_WINDOW),window.ticks);
        if (row == 1) return snprintf(out,capacity,"Complete windows only. Resume starts a fresh window.");
        return 0;
    }
    const Snapshot& s=sealed;
    if (row==0) return snprintf(out,capacity,"WC24 #%u room=%03x ticks=%u drawn=%u try=%u skip=%u",
        s.sequence,s.identity[0],s.ticks,s.drawn,s.draw_attempts,s.skipped);
    if (row==1) return snprintf(out,capacity,"us/tick wall=%u world=%u wait=%u residual=%lld",
        mean(s.wall_us,s.ticks),mean(world_time(s),s.ticks),mean(wait_time(s),s.ticks),
        static_cast<long long>(s.ticks?s.residual_us/int64_t(s.ticks):0));
    if (row==2) return snprintf(out,capacity,"us/draw wall=%u world=%u wait=%u residual=%lld",
        mean(s.wall_us,s.drawn),mean(world_time(s),s.drawn),mean(wait_time(s),s.drawn),
        static_cast<long long>(s.drawn?s.residual_us/int64_t(s.drawn):0));
    if (row==3) return snprintf(out,capacity,"Amortized /draw: select xform clip header submit other");
    static const char* const names[PathCount]={"NEAR OP","NEAR PT","NEAR TR","FAR OP","FAR PT","FAR TR"};
    if (row>=4 && row<10) {const unsigned p=row-4;return snprintf(out,capacity,"%-7s %u %u %u %u %u %u",names[p],
        mean(s.phase_us[p][0],s.drawn),mean(s.phase_us[p][1],s.drawn),mean(s.phase_us[p][2],s.drawn),
        mean(s.phase_us[p][3],s.drawn),mean(s.phase_us[p][4],s.drawn),mean(s.phase_us[p][5],s.drawn));}
    if (row==10) return snprintf(out,capacity,"Counts /draw: xform corners headers changes idx plain nr0");
    if (row>=11 && row<17) {const unsigned p=row-11;return snprintf(out,capacity,"%-7s %u %u %u %u %u %u %u",names[p],
        mean(s.counters[p][0],s.drawn),mean(s.counters[p][1],s.drawn),mean(s.counters[p][2],s.drawn),
        mean(s.counters[p][3],s.drawn),mean(s.counters[p][4],s.drawn),mean(s.counters[p][5],s.drawn),
        mean(s.counters[p][6],s.drawn));}
    if (row==17) return snprintf(out,capacity,"Counts /tick: x=%u c=%u h=%u m=%u idx=%u plain=%u nr0=%u",
        mean(sum_counter(s,0),s.ticks),mean(sum_counter(s,1),s.ticks),mean(sum_counter(s,2),s.ticks),
        mean(sum_counter(s,3),s.ticks),mean(sum_counter(s,4),s.ticks),mean(sum_counter(s,5),s.ticks),mean(sum_counter(s,6),s.ticks));
    if (row==18) return snprintf(out,capacity,"Wait us/draw: PVR=%u VBL=%u PACE=%u (exclusive)",
        mean(s.wait_us[0],s.drawn),mean(s.wait_us[1],s.drawn),mean(s.wait_us[2],s.drawn));
    if (row==19) return snprintf(out,capacity,"Scenes=%u present/discard=%u/%u actual flips=%u vbl=%u",
        s.scenes,s.present_requests,s.discard_requests,s.presentation.flips,s.presentation.vblanks);
    if (row==20) return snprintf(out,capacity,"Flip us min/avg/max=%u/%u/%u n=%u gap>2=%u maxfld=%u",
        mean(s.presentation.min_interval_us,1),mean(s.presentation.interval_us,s.presentation.intervals),
        mean(s.presentation.max_interval_us,1),s.presentation.intervals,s.presentation.gaps_over_two_fields,s.presentation.max_fields);
    if (row==21) return snprintf(out,capacity,"Render start/done=%u/%u max tick=%u us errors=%u/%u",
        s.presentation.render_starts,s.presentation.render_dones,mean(s.max_tick_us,1),s.errors,s.presentation.discontinuities);
    if (row==22) return snprintf(out,capacity,"Source ticks %u..%u; GPU events end in window (overlap)",s.first_tick,s.last_tick);
    if (row==23) return snprintf(out,capacity,"Diagnostic overhead included; no console speedup claimed");
    return snprintf(out,capacity,"Identity: view=%x PVS=%x shell=%x opq=%u xlu=%u QA-shell=%u epoch=%u",
        s.identity[1],s.identity[2],s.identity[3],s.identity[4],s.identity[5],s.identity[6],s.identity[7]);
}
} }

#if !defined(RE4DC_WORLD_CENSUS24_HOST)
// The existing pace observer remains the sole wrapper when it is built.
#if !defined(RE4DC_WC24_PACE_OBSERVER) || !RE4DC_WC24_PACE_OBSERVER
extern "C" void __real_pvr_sync_stats(int event);
extern "C" void __wrap_pvr_sync_stats(int event) {
    __real_pvr_sync_stats(event);
    re4dc::wc24::pvr_event(unsigned(event));
}
#endif
extern "C" int __real_pvr_wait_ready();
extern "C" int __wrap_pvr_wait_ready() {
    re4dc::wc24::WaitScope wait(re4dc::wc24::PvrWait);
    return __real_pvr_wait_ready();
}
extern "C" int __real_pvr_wait_render_done();
extern "C" int __wrap_pvr_wait_render_done() {
    re4dc::wc24::WaitScope wait(re4dc::wc24::PvrWait);
    return __real_pvr_wait_render_done();
}
#endif
