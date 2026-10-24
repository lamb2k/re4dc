#ifndef RE4DC_PERF_PHASE_MISS_H
#define RE4DC_PERF_PHASE_MISS_H

// Build 14 diagnostic. Included only behind PERF_PHASE_MISS's feature guard.
#include <stdint.h>
#include "world_census24.h"

namespace re4dc { namespace ppm14 {
enum { WorldBins = wc24::PathCount * wc24::PhaseCount,
       WaitBase = WorldBins, Residual = WaitBase + wc24::WaitCount,
       BinCount = Residual + 1, ControlPairs = 8, ControlLoads = 8192,
       ResidentBytes = 2048, MissHeavyBytes = 32768 };
enum Qualification { Unrun, Qualified, Inconclusive, Simulated, CounterBusy, CounterLost };
enum Error { InvalidSample = 1, AccountingOverflow = 2, CensusFault = 4, AllocationFailed = 8 };
struct Control {
    uint64_t resident[ControlPairs], heavy[ControlPairs];
    uint32_t pairs, qualification, errors, peak_buffer_bytes;
};
struct Snapshot {
    uint64_t bins[BinCount], total;
    uint32_t sequence, identity[wc24::IdentityWords], ticks, drawn;
    uint32_t event, qualification, errors, samples, wraps;
};

// All callbacks run on the census owner thread. The census validates nesting;
// identical effective bins do not read the PMU again. No per-vertex callback.
void begin_tick(uint64_t now);
void transition(unsigned census_state, uint64_t now);
void finish_tick(uint64_t now);
void seal(const wc24::Snapshot& census);
void abandon(bool clear_snapshot);
bool run_controls(); // QA paused only; temporary aligned buffers are freed
int snapshot(Snapshot* out);
Control controls();
unsigned line_count();
int format_line(unsigned row, char* out, unsigned capacity);
int summary(char* out, unsigned capacity);
} }
#endif
