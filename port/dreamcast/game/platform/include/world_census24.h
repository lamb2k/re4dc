#ifndef RE4DC_WORLD_CENSUS24_H
#define RE4DC_WORLD_CENSUS24_H

// Build 10, diagnostic only. Include this header only inside the feature guard
// so absent/zero builds retain their original preprocessed translation units.
#include <stdint.h>

namespace re4dc { namespace wc24 {
enum Path { NearOP, NearPT, NearTR, FarOP, FarPT, FarTR, PathCount };
enum Phase { Selection, Transform, Clip, HeaderMaterial, Submit, Other, PhaseCount };
enum Wait { PvrWait, VblankWait, PaceWait, WaitCount };
enum Counter {
    Transformed, Corners, Headers, MaterialChanges,
    PickedIndexed, PickedPlain, PickedEmpty, StripInputs, CounterCount
};
enum { IdentityWords = 8 };

struct Presentation {
    uint32_t vblanks, flips, render_starts, render_dones, intervals;
    uint32_t gaps_over_two_fields, max_fields, discontinuities;
    uint64_t interval_us, min_interval_us, max_interval_us;
};
struct Snapshot {
    uint32_t sequence, identity[IdentityWords];
    uint32_t first_tick, last_tick, ticks, draw_attempts, drawn, skipped;
    uint32_t scenes, present_requests, discard_requests, errors;
    uint64_t wall_us, max_tick_us;
    uint64_t phase_us[PathCount][PhaseCount];
    uint64_t wait_us[WaitCount];
    uint64_t counters[PathCount][CounterCount];
    int64_t residual_us;
    Presentation presentation;
};

// Main thread: ticks are measured begin-to-next-begin. end_tick seals logical
// completion; formatting after a window is charged to the following tick.
void begin_tick(uint32_t tick, uint32_t room);
void end_tick();
void decision(bool draw_attempt);
void scene_finished();
void decision_posted(bool present);
void fault(); // incomplete/unsupported world path; invalidates timing acceptance
void pause();
void resume();
void reset();

// IRQ observer: pinned KOS event 1=vblank, 6=render start, 7=render done,
// 8=actual page flip. This never formats, allocates, or changes PVR state.
void pvr_event(unsigned event);

// Integer-only hooks, safe between loading XMTRX and the existing FTRV code.
void count(Counter counter, uint32_t amount = 1);
void submitted_header(const uint32_t words[4]);
uint32_t enter(Path path, Phase phase);
uint32_t enter(Phase phase);
uint32_t enter_wait(Wait wait);
void leave(uint32_t token);
void set_phase(Phase phase);

class Scope {
    uint32_t token_;
    Scope(const Scope&) = delete;
    Scope& operator=(const Scope&) = delete;
public:
    explicit Scope(Phase p) : token_(enter(p)) {}
    Scope(Path path, Phase p) : token_(enter(path, p)) {}
    ~Scope() { leave(token_); }
    void phase(Phase p) { set_phase(p); }
};
class WaitScope {
    uint32_t token_;
    WaitScope(const WaitScope&) = delete;
    WaitScope& operator=(const WaitScope&) = delete;
public:
    explicit WaitScope(Wait wait) : token_(enter_wait(wait)) {}
    ~WaitScope() { leave(token_); }
};

// Last complete window only. 0 while collecting the first valid window.
int snapshot(Snapshot* out);
unsigned line_count();
int format_line(unsigned row, char* out, unsigned capacity);
int summary(char* out, unsigned capacity);
} }

// Renderer owns the seven option/generation words; main supplies room ID.
// View, PVS option, far-shell mode, QA opaque far, QA xlu far, QA shell, epoch.
extern "C" void re4dc_wc24_identity(unsigned out[7]);

#endif
