// PERF_PHASE_MISS: one fixed PRFC1 event, observed at validated census edges.
#include "platform/include/perf_phase_accounting.hpp"
#include <stdio.h>
#include <stdlib.h>
#include <malloc.h>
#include <string.h>

#ifndef RE4DC_PERF_PHASE_MISS_EVENT
#define RE4DC_PERF_PHASE_MISS_EVENT 15
#endif
#if RE4DC_PERF_PHASE_MISS_EVENT != 15 && RE4DC_PERF_PHASE_MISS_EVENT != 37
#error PERF_PHASE_MISS_EVENT must be 15 (OC misses) or 37 (D-miss freeze cycles)
#endif
#if !defined(RE4DC_WORLD_CENSUS24) || !RE4DC_WORLD_CENSUS24
#error PERF_PHASE_MISS needs WORLD_CENSUS24
#endif
#if defined(RE4DC_PMC_ROW) && RE4DC_PMC_ROW
#error PERF_PHASE_MISS and PMC_ROW both own PRFC1
#endif

#if defined(RE4DC_PERF_PHASE_MISS_HOST)
extern "C" uint64_t re4dc_ppm14_test_clock();
extern "C" uintptr_t re4dc_ppm14_test_thread();
extern "C" bool re4dc_ppm14_test_config(unsigned, unsigned*, unsigned*);
extern "C" void re4dc_ppm14_test_start(unsigned, unsigned);
extern "C" void re4dc_ppm14_test_stop(unsigned);
extern "C" uint64_t re4dc_ppm14_test_count(unsigned);
extern "C" void re4dc_ppm14_test_log(const char*);
extern "C" void* re4dc_ppm14_test_alloc(unsigned, unsigned);
extern "C" void re4dc_ppm14_test_free(void*);
static uint64_t clock_us() { return re4dc_ppm14_test_clock(); }
static uintptr_t thread_id() { return re4dc_ppm14_test_thread(); }
static unsigned lock_irq() { return 0; }
static void unlock_irq(unsigned) {}
static bool configuration(unsigned* e, unsigned* c) { return re4dc_ppm14_test_config(1,e,c); }
static void start_counter() { re4dc_ppm14_test_start(1,RE4DC_PERF_PHASE_MISS_EVENT); }
static void stop_counter() { re4dc_ppm14_test_stop(1); }
static uint64_t count_counter() { return re4dc_ppm14_test_count(1); }
static void print_line(const char* s) { re4dc_ppm14_test_log(s); }
static void* control_alloc(unsigned bytes) { return re4dc_ppm14_test_alloc(32,bytes); }
static void control_free(void* p) { re4dc_ppm14_test_free(p); }
#else
#include <arch/timer.h>
#include <dc/perfctr.h>
#include <kos/irq.h>
#include <kos/thread.h>
extern "C" void re4dc_log(const char*, ...);
static_assert(PMCR_OPERAND_CACHE_MISS_MODE == 15 && PMCR_PIPELINE_FREEZE_BY_DCACHE_MISS_MODE == 37,
              "KOS event definitions differ from the qualified source");
static uint64_t clock_us() { return timer_us_gettime64(); }
static uintptr_t thread_id() { return reinterpret_cast<uintptr_t>(thd_current); }
static unsigned lock_irq() { return irq_disable(); }
static void unlock_irq(unsigned mask) { irq_restore(mask); }
static bool configuration(unsigned* e, unsigned* c) {
    perf_cntr_event_t event; perf_cntr_clock_t clock;
    const bool running = perf_cntr_config(PRFC1,&event,&clock);
    *e = unsigned(event); *c = unsigned(clock); return running;
}
static void start_counter() {
    // KOS start clears the selected counter itself. Never touch PRFC0.
    perf_cntr_start(PRFC1,static_cast<perf_cntr_event_t>(RE4DC_PERF_PHASE_MISS_EVENT),PMCR_COUNT_CPU_CYCLES);
}
static void stop_counter() { perf_cntr_stop(PRFC1); }
static uint64_t count_counter() { return perf_cntr_count(PRFC1); }
static void print_line(const char* s) { re4dc_log("%s\n",s); }
static void* control_alloc(unsigned bytes) { return memalign(32,bytes); }
static void control_free(void* p) { free(p); }
#endif

namespace re4dc { namespace ppm14 {
namespace {
Snapshot window, sealed;
Control control;
uintptr_t owner;
uint64_t previous_count, previous_us;
unsigned bin = Residual;
bool owned, running, active, have_sealed;
bool paused = true, lost;
volatile uint32_t control_sink;
#if defined(RE4DC_DRAW_SETUP_AUDIT) && RE4DC_DRAW_SETUP_AUDIT
uint32_t audit_generation;
#endif

bool ours() { return !owner || owner == thread_id(); }
const char* status_name(unsigned q) {
    static const char* const names[] = {"UNRUN","QUALIFIED","INCONCLUSIVE","SIMULATED","COUNTER_BUSY","COUNTER_LOST"};
    return q <= CounterLost ? names[q] : "INVALID";
}
const char* units() { return RE4DC_PERF_PHASE_MISS_EVENT == 15 ? "misses" : "freeze cycles"; }
void lose_counter() {
    // Sticky: even a later matching configuration cannot establish ownership.
    // Do not stop, read or reconfigure a possible new owner's counter.
    lost = true; owned = running = active = false;
    control.qualification = CounterLost;
}
bool matches(bool expected_running) {
    unsigned event, clock;
    const bool is_running = configuration(&event,&clock);
    return is_running == expected_running && event == RE4DC_PERF_PHASE_MISS_EVENT && clock == 0;
}
bool start_owned() {
    if (lost) return false;
    const unsigned irq = lock_irq();
    if (owned) {
        if (!matches(false)) { lose_counter(); unlock_irq(irq); return false; }
    } else {
        unsigned event, clock;
        if (configuration(&event,&clock) || event != 0 || clock != 0) {
            control.qualification = CounterBusy; lost = true; unlock_irq(irq); return false;
        }
    }
    start_counter();
#if defined(RE4DC_DRAW_SETUP_AUDIT) && RE4DC_DRAW_SETUP_AUDIT
    if(!++audit_generation)++audit_generation;
#endif
    owned = true;
    if (!matches(true)) { lose_counter(); unlock_irq(irq); return false; }
    running = true; unlock_irq(irq); return true;
}
bool read_owned(uint64_t& value) {
    if (lost || !owned || !running) return false;
    const unsigned irq = lock_irq();
    if (!matches(true)) { lose_counter(); unlock_irq(irq); return false; }
    // Pinned KOS reads high-low-high and retries a changing high word.
    value = count_counter(); unlock_irq(irq); return true;
}
void stop_owned() {
    if (lost || !owned || !running) return;
    const unsigned irq = lock_irq();
    if (!matches(true)) { lose_counter(); unlock_irq(irq); return; }
    stop_counter(); running = false; unlock_irq(irq);
}
void invalid(unsigned error) {
    window.errors |= error;
    control.errors |= error; // an explicit new QA control run is required
    stop_owned(); active = false;
}
void sample(uint64_t now) {
    if (!active) return;
    uint64_t value, delta; bool wrapped;
    if (!read_owned(value)) return;
    if (now < previous_us || !counter_delta(previous_count,value,now-previous_us,delta,wrapped)) {
        invalid(InvalidSample); return;
    }
    if (!accumulate(window,bin,delta,wrapped)) { invalid(AccountingOverflow); return; }
    previous_count = value; previous_us = now;
}
uint64_t sum(unsigned first,unsigned count) {
    uint64_t total = 0;
    for (unsigned i=0;i<count;++i) total += sealed.bins[first+i];
    return total;
}
uint64_t mean(uint64_t total,unsigned n) { return n ? total/n : 0; }

// Same dependent volatile-load loop for both footprints. No prefetch, cache
// manipulation, unrolling request, inline assembly or event reconfiguration.
__attribute__((noinline)) uint32_t chase(volatile uint32_t* nodes,unsigned count) {
    uint32_t index = 0;
    for (unsigned i=0;i<count;++i) index = nodes[index];
    return index;
}
void prepare(uint32_t* nodes,unsigned bytes) {
    const unsigned lines = bytes/32;
    for (unsigned i=0;i<lines;++i) nodes[i*8] = ((i+17)&(lines-1))*8;
}
bool measure(uint32_t* nodes,uint64_t& result) {
    control_sink = chase(nodes,4096); // warm instruction path and chosen ring
    const uint64_t before_us = clock_us();
    uint64_t before,after;
    if (!read_owned(before)) return false;
    control_sink = chase(nodes,ControlLoads);
    if (!read_owned(after)) return false;
    const uint64_t after_us = clock_us(); bool wrapped;
    if (after_us < before_us || !counter_delta(before,after,after_us-before_us,result,wrapped)) {
        control.errors |= InvalidSample; return false;
    }
    return true;
}
void range(const uint64_t values[ControlPairs],uint64_t& low,uint64_t& median,uint64_t& high) {
    uint64_t sorted[ControlPairs];
    for (unsigned i=0;i<ControlPairs;++i) {
        unsigned j=i;
        while(j && sorted[j-1]>values[i]) { sorted[j]=sorted[j-1]; --j; }
        sorted[j]=values[i];
    }
    low=sorted[0];median=sorted[ControlPairs/2];high=sorted[ControlPairs-1];
}
} // namespace

void begin_tick(uint64_t now) {
    if (!ours()) return;
    owner = thread_id(); paused = false;
    if (active || lost || control.qualification == Unrun || control.errors) return;
    if (!start_owned()) return;
    if (!read_owned(previous_count)) return;
    if (previous_count >> 48) { invalid(InvalidSample); return; }
    previous_us=now; bin=Residual; active=true;
}
void transition(unsigned state,uint64_t now) {
    if (!ours() || paused || !active) return;
    const unsigned next = effective_bin(state);
    if (next >= BinCount) { invalid(AccountingOverflow); return; }
    if (next == bin) return;
    sample(now); bin=next;
}
void finish_tick(uint64_t now) {
    if (!ours() || paused) return;
    sample(now); bin=Residual;
}
void abandon(bool clear_snapshot) {
    if (!ours()) return;
    stop_owned(); active=false; paused=true; bin=Residual;
    window=Snapshot{};
    if (clear_snapshot) have_sealed=false;
}
void seal(const wc24::Snapshot& census) {
    if (!ours()) return;
    window.sequence=census.sequence; window.ticks=census.ticks; window.drawn=census.drawn;
    memcpy(window.identity,census.identity,sizeof(window.identity));
    window.event=RE4DC_PERF_PHASE_MISS_EVENT; window.qualification=control.qualification;
    if (census.errors) window.errors |= CensusFault;
    if (lost || control.errors) window.errors |= InvalidSample;
    sealed=window; have_sealed=true; window=Snapshot{};
    char line[240];summary(line,sizeof(line));print_line(line);
}
bool run_controls() {
    if (!ours() || !paused || lost) return false;
    have_sealed=false; window=Snapshot{}; // do not pair an old window with new controls
    owner=thread_id(); control=Control{};control.qualification=Inconclusive;
    const unsigned bytes=ResidentBytes+MissHeavyBytes;
    uint32_t* const buffer=static_cast<uint32_t*>(control_alloc(bytes));
    if (!buffer) { control.errors=AllocationFailed;return false; }
    control.peak_buffer_bytes=bytes;
    prepare(buffer,ResidentBytes);prepare(buffer+ResidentBytes/4,MissHeavyBytes);
    if (start_owned()) {
        for (unsigned i=0;i<ControlPairs;++i) {
            const unsigned first=i&1U;
            bool okay=true;
            for (unsigned arm=0;arm<2 && okay;++arm) {
                const bool heavy=(first^arm)!=0;
                okay=measure(buffer+(heavy?ResidentBytes/4:0),heavy?control.heavy[i]:control.resident[i]);
            }
            if(!okay)break;
            ++control.pairs;
        }
        stop_owned();
    }
    control_free(buffer); // control memory is absent from subsequent gameplay
    if (!lost && !control.errors && control.pairs == ControlPairs) {
        uint64_t rmin,rmed,rmax,hmin,hmed,hmax;
        range(control.resident,rmin,rmed,rmax);range(control.heavy,hmin,hmed,hmax);
        const uint64_t floor=RE4DC_PERF_PHASE_MISS_EVENT==15?ControlLoads/2:ControlLoads;
        if (hmin>=floor && rmax <= (UINT64_MAX-64)/4 && hmin>rmax*4+64) {
#if defined(RE4DC_PERF_PHASE_MISS_HOST)
            control.qualification=Simulated;
#else
            control.qualification=Qualified;
#endif
        }
    }
    char line[240];
    snprintf(line,sizeof(line),"PM14 control ev=%02x ctl=%s pairs=%u loads=%u bytes=%u err=%u; raw=QA",
        unsigned(RE4DC_PERF_PHASE_MISS_EVENT),status_name(control.qualification),control.pairs,
        unsigned(ControlLoads),control.peak_buffer_bytes,control.errors);
    print_line(line);
    return control.qualification==Qualified || control.qualification==Simulated;
}
int snapshot(Snapshot* out) { if(!have_sealed)return 0;if(out)*out=sealed;return 1; }
#if defined(RE4DC_DRAW_SETUP_AUDIT) && RE4DC_DRAW_SETUP_AUDIT
bool read_audit_sample(AuditSample* out) {
    if(!out)return false;
    *out=AuditSample{};out->generation=audit_generation;
    out->event=RE4DC_PERF_PHASE_MISS_EVENT;out->qualification=control.qualification;
    if(!ours()||paused||!active||control.errors||
       (control.qualification!=Qualified&&control.qualification!=Simulated))return false;
    const bool ok=read_owned(out->value);
    out->qualification=control.qualification; // a lost counter is sticky
    return ok;
}
#endif
Control controls() { return control; }
int summary(char* out,unsigned cap) {
    if(!cap)return 0;
    if(!have_sealed)return snprintf(out,cap,"PM14 ev=%02x %s ctl=%s collecting; QA X runs controls",
        unsigned(RE4DC_PERF_PHASE_MISS_EVENT),units(),status_name(control.qualification));
    const bool valid=sealed.qualification==Qualified && !sealed.errors && sealed.samples;
    const int n=snprintf(out,cap,"PM14 q=%u room=%03x ev=%02x ctl=%s valid=%u t=%u d=%u total=%llu world=%llu wait=%llu residual=%llu samples=%u wrap=%u err=%u",
        sealed.sequence,sealed.identity[0],sealed.event,status_name(sealed.qualification),valid,
        sealed.ticks,sealed.drawn,(unsigned long long)sealed.total,(unsigned long long)sum(0,WorldBins),
        (unsigned long long)sum(WaitBase,wc24::WaitCount),(unsigned long long)sealed.bins[Residual],
        sealed.samples,sealed.wraps,sealed.errors);
    if(n<0 || unsigned(n)>=cap)return snprintf(out,cap,"PM14 q=%u ev=%02x summary_overflow=1 full=QA",sealed.sequence,sealed.event);
    return n;
}
unsigned line_count() { return 29; }
int format_line(unsigned row,char* out,unsigned cap) {
    if(!cap)return 0;
    out[0]=0;
    if(row==0)return snprintf(out,cap,"PM14 PRFC1 ev=%02x %s controls=%s",unsigned(RE4DC_PERF_PHASE_MISS_EVENT),units(),status_name(control.qualification));
    if(row==1)return snprintf(out,cap,"X: run controls while paused. Separate event15/37 builds/runs.");
    if(row==2 || row==3) {
        const uint64_t* v=row==2?control.resident:control.heavy;
        uint64_t a,b,c;range(v,a,b,c);
        return snprintf(out,cap,"%s min/upper-median/max=%llu/%llu/%llu",row==2?"2KB resident":"32KB heavy",
            (unsigned long long)a,(unsigned long long)b,(unsigned long long)c);
    }
    if(row==4)return snprintf(out,cap,"Control pairs=%u/8 loads=%u each peak buffers=%u bytes err=%u",control.pairs,unsigned(ControlLoads),control.peak_buffer_bytes,control.errors);
    if(row==5)return snprintf(out,cap,"Pass: heavy MIN > resident MAX*4+64 and >=%u; no event latency inferred",unsigned(RE4DC_PERF_PHASE_MISS_EVENT==15?ControlLoads/2:ControlLoads));
    if(row==20)return snprintf(out,cap,"Raw control pairs (same event, alternating test order):");
    if(row>=21 && row<29)return snprintf(out,cap,"Pair%u resident=%llu heavy=%llu",row-20,
        (unsigned long long)control.resident[row-21],(unsigned long long)control.heavy[row-21]);
    if(row==6) {
        if(!have_sealed)return snprintf(out,cap,"No complete PM14 window. Resume begins a fresh census window.");
        return snprintf(out,cap,"PM14 #%u room=%03x ticks=%u drawn=%u ctl=%s err=%u",sealed.sequence,sealed.identity[0],sealed.ticks,sealed.drawn,status_name(sealed.qualification),sealed.errors);
    }
    if(!have_sealed)return 0;
    if(row==7)return snprintf(out,cap,"%s/draw: select xform clip header submit other",units());
    static const char* const names[wc24::PathCount]={"NEAR OP","NEAR PT","NEAR TR","FAR OP","FAR PT","FAR TR"};
    if(row>=8 && row<14) {
        const unsigned p=row-8;const uint64_t* v=sealed.bins+p*wc24::PhaseCount;
        return snprintf(out,cap,"%-7s %llu %llu %llu %llu %llu %llu",names[p],
            (unsigned long long)mean(v[0],sealed.drawn),(unsigned long long)mean(v[1],sealed.drawn),
            (unsigned long long)mean(v[2],sealed.drawn),(unsigned long long)mean(v[3],sealed.drawn),
            (unsigned long long)mean(v[4],sealed.drawn),(unsigned long long)mean(v[5],sealed.drawn));
    }
    if(row==14)return snprintf(out,cap,"Wait/draw PVR=%llu VBL=%llu PACE=%llu",(unsigned long long)mean(sealed.bins[WaitBase],sealed.drawn),
        (unsigned long long)mean(sealed.bins[WaitBase+1],sealed.drawn),(unsigned long long)mean(sealed.bins[WaitBase+2],sealed.drawn));
    if(row==15)return snprintf(out,cap,"/tick total=%llu world=%llu wait=%llu residual=%llu",(unsigned long long)mean(sealed.total,sealed.ticks),
        (unsigned long long)mean(sum(0,WorldBins),sealed.ticks),(unsigned long long)mean(sum(WaitBase,wc24::WaitCount),sealed.ticks),(unsigned long long)mean(sealed.bins[Residual],sealed.ticks));
    if(row==16)return snprintf(out,cap,"Raw total=%llu named+wait+residual=%llu samples=%u wrap=%u",(unsigned long long)sealed.total,
        (unsigned long long)sum(0,BinCount),sealed.samples,sealed.wraps);
    if(row==17)return snprintf(out,cap,"Identity view=%x PVS=%x shell=%x opq=%u xlu=%u QA-shell=%u epoch=%u",sealed.identity[1],sealed.identity[2],sealed.identity[3],sealed.identity[4],sealed.identity[5],sealed.identity[6],sealed.identity[7]);
    if(row==18)return snprintf(out,cap,"Global CPU events include observer/interrupt/background work. No exclusive CPU owner.");
    return snprintf(out,cap,"QUALIFIED: target control response. Hardware evidence requires a console run.");
}
} }
