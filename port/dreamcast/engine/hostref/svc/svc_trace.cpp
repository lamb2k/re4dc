// svc_trace.cpp (PC side; lane eng-svc): the service census of re4ref.
//
// 1. Calls. gen_wraps.py's trampolines call census_hit for every call across an object boundary into a service
//    unit (S) or a math / memory helper (M), with the caller's return address and the first argument (the model
//    for most skeleton and collision entry points). census_sp / census_idx / census_arg are the shadow stack of
//    running service calls (census_idx[0] is the outermost); census_msp / census_mret the helpers'.
// 2. Memory (RE4_SVC_TRACE=1). During each tick the guest arena (16 MiB at 0x8C000000) is PROT_NONE. A fault
//    records the access (instruction, address, read or write, the running service context), opens the arena and
//    single-steps the instruction (EFLAGS.TF); the trap closes it again. So every load and store the tick makes to
//    guest memory is seen once, at the instruction that made it.
//    - per context (outermost service entry, or none = behaviour and host) and actor: accesses, reads, writes and
//      the distinct 32-byte lines (the SH-4 operand cache line) touched per tick, by region;
//    - per instruction into a parts record or a model record: the field offset, read or write, how many ticks,
//      which bones. census.py names the instructions (nm, the link map) and classifies them.
// Output: $RE4_SVC_OUT/{calls,mcalls,mem,fields,actors}.tsv at the end of the run.
#include "hostref.h"
#include "svc_census.h"
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/ucontext.h>
#include <unistd.h>

extern "C" {
unsigned census_sp, census_msp;
unsigned census_ret[4096], census_idx[4096], census_arg[4096], census_mret[4096];
extern unsigned census_nsyms;
extern const char* const census_name[];
extern const char* const census_unit[];
extern const char census_kind[];
}

namespace {
constexpr unsigned kMaxSym = 1024;
constexpr unsigned kActors = 256;      // 0..63 em slots, 64.. obj slots (64 + slot), 250 none
constexpr unsigned kNone = 250;
bool g_on;            // counting (between ready and the end)
bool g_trace;         // memory tracer active (RE4_SVC_TRACE=1)
bool g_armed;         // arena protected now
bool g_in_hit;
unsigned g_tick, g_ticks, g_traced;
unsigned g_from = 0, g_to = ~0u;   // RE4_SVC_TRACE_FROM / _TO: the ticks the memory tracer covers
bool g_tick_traced;
SvcRegion g_reg[SVC_REGIONS];
const uint8_t* g_part_owner;
const uint8_t* g_part_bone;
unsigned g_part_lo, g_part_stride, g_part_n;

unsigned actor_of(unsigned a)
{
    for (int r = SVC_R_EM; r <= SVC_R_OBJ; r++) {
        const SvcRegion& g = g_reg[r];
        if (g.stride && a >= g.lo && a < g.hi) {
            const unsigned c = (r == SVC_R_EM ? 0 : 64) + (a - g.lo) / g.stride;
            return c < kNone ? c : kNone;
        }
    }
    if (g_part_owner && a >= g_part_lo && a < g_part_lo + g_part_n * g_part_stride) return g_part_owner[(a - g_part_lo) / g_part_stride];
    return kNone;
}
extern uint32_t g_svc_lo, g_svc_hi;
// the data loads (host_fixed, wrapped in this build): archives by kind
struct Load { uint32_t lo, hi; int reg; };
Load g_loads[64];
unsigned g_nloads;
int region_of(unsigned a)
{
    for (int r = SVC_R_PARTS; r <= SVC_R_OBJ; r++)
        if (a >= g_reg[r].lo && a < g_reg[r].hi) return r;
    for (unsigned i = 0; i < g_nloads; i++)
        if (a >= g_loads[i].lo && a < g_loads[i].hi) return g_loads[i].reg;
    if (a >= HOST_ARENA_BASE + 0x10000u && a < HOST_ARENA_BASE + HOST_ARENA_SIZE - 0x00600000u) return SVC_R_HEAP;
    if (a >= g_svc_lo && a < g_svc_hi) return SVC_R_SVC;
    return SVC_R_OTHER;
}

// ---- calls ----
struct CallKey { unsigned idx, ret, actor, depth0; uint64_t n; };
constexpr unsigned kCallTab = 1u << 16;
CallKey g_calls[kCallTab];
struct MKey { unsigned idx, ctx, actor; uint64_t n; };
MKey g_mcalls[kCallTab];
uint32_t g_tick_calls[kMaxSym], g_max_calls[kMaxSym];
uint64_t g_tot_calls[kMaxSym];

unsigned hash3(unsigned a, unsigned b, unsigned c)
{
    unsigned h = a * 0x9E3779B1u ^ (b + 0x7F4A7C15u) * 0x85EBCA77u ^ c * 0xC2B2AE3Du;
    return h ^ (h >> 15);
}

// ---- memory ----
struct LineKey { uint32_t stamp; uint16_t ctx; uint8_t actor, pad; uint32_t line; };
constexpr unsigned kLineTab = 1u << 22;
LineKey* g_lines;
struct MemAgg { uint64_t acc, rd, wr, lines; uint32_t lines_max, ticks, lines_tick, last; };
// [ctx][actor][region], ctx = sym idx or kMaxSym (none)
MemAgg* g_mem;
MemAgg& mem(unsigned ctx, unsigned actor, unsigned reg) { return g_mem[((size_t) ctx * kActors + actor) * SVC_REGIONS + reg]; }

// service kind of a census symbol (its unit): 1 skeleton, 2 collision, 3 another service unit, 0 none
uint8_t g_kind[kMaxSym + 1];
void init_kinds()
{
    static const char* skel[] = {"model", "motion", "cMotBase", "ik", "shape", "skel", 0};
    static const char* col[] = {"atari", "at_mod", "at_sub", "at_sub2", "atariInfo", "col", 0};
    for (unsigned i = 0; i < census_nsyms && i < kMaxSym; i++) {
        g_kind[i] = census_kind[i] == 'S' ? 3 : 0;
        for (int k = 0; skel[k]; k++)
            if (!strcmp(census_unit[i], skel[k])) g_kind[i] = 1;
        for (int k = 0; col[k]; k++)
            if (!strcmp(census_unit[i], col[k])) g_kind[i] = 2;
    }
}
struct KindKey { uint32_t stamp; uint8_t kind, actor; uint16_t pad; uint32_t line; };
KindKey* g_klines;
MemAgg* g_kmem;   // [kind 0..3][actor][region]
MemAgg& kmem(unsigned kind, unsigned actor, unsigned reg) { return g_kmem[((size_t) kind * kActors + actor) * SVC_REGIONS + reg]; }

struct FieldKey { uint32_t eip; uint16_t ctx; uint8_t reg, w; uint16_t off, pad; uint32_t n, nticks, last; uint64_t bones; uint32_t used; };
constexpr unsigned kFieldTab = 1u << 18;
FieldKey* g_fields;

void record(unsigned eip, unsigned addr, int w)
{
    const unsigned ctx = census_sp ? census_idx[0] : kMaxSym;
    const unsigned eff = census_msp ? census_mret[0] : eip;
    const unsigned actor = census_sp ? actor_of(census_arg[0]) : actor_of(addr);
    const int reg = region_of(addr);
    MemAgg& m = mem(ctx, actor, reg);
    m.acc++;
    (w ? m.wr : m.rd)++;
    const unsigned line = addr >> 5;
    unsigned h = hash3(line, ctx, actor) & (kLineTab - 1);
    for (;;) {
        LineKey& k = g_lines[h];
        if (k.stamp != g_tick + 1) {
            k.stamp = g_tick + 1; k.ctx = (uint16_t) ctx; k.actor = (uint8_t) actor; k.line = line;
            m.lines_tick++;
            if (m.last != g_tick + 1) { m.last = g_tick + 1; m.ticks++; }
            break;
        }
        if (k.line == line && k.ctx == ctx && k.actor == actor) break;
        h = (h + 1) & (kLineTab - 1);
    }
    {
        const unsigned kind = g_kind[ctx];
        MemAgg& km = kmem(kind, actor, reg);
        km.acc++;
        (w ? km.wr : km.rd)++;
        unsigned kh = hash3(line, kind + 7, actor) & (kLineTab - 1);
        for (;;) {
            KindKey& k = g_klines[kh];
            if (k.stamp != g_tick + 1) {
                k.stamp = g_tick + 1; k.kind = (uint8_t) kind; k.actor = (uint8_t) actor; k.line = line;
                km.lines_tick++;
                if (km.last != g_tick + 1) { km.last = g_tick + 1; km.ticks++; }
                break;
            }
            if (k.line == line && k.kind == kind && k.actor == actor) break;
            kh = (kh + 1) & (kLineTab - 1);
        }
    }
    if (reg == SVC_R_PARTS || reg == SVC_R_EM || reg == SVC_R_OBJ) {
        const SvcRegion& g = g_reg[reg];
        const unsigned slot = (addr - g.lo) / g.stride;
        const unsigned off = (addr - g.lo) % g.stride;
        unsigned bone = 63;
        if (reg == SVC_R_PARTS && g_part_bone) bone = g_part_bone[slot] < 63 ? g_part_bone[slot] : 63;
        unsigned fh = hash3(eff, ctx * 8 + reg * 2 + (w ? 1 : 0), off) & (kFieldTab - 1);
        for (;;) {
            FieldKey& f = g_fields[fh];
            if (!f.used) {
                f.used = 1; f.eip = eff; f.ctx = (uint16_t) ctx; f.reg = (uint8_t) reg; f.w = (uint8_t) (w ? 1 : 0);
                f.off = (uint16_t) off;
            }
            if (f.eip == eff && f.ctx == ctx && f.reg == reg && f.w == (w ? 1 : 0) && f.off == off) {
                f.n++;
                if (f.last != g_tick + 1) { f.last = g_tick + 1; f.nticks++; }
                f.bones |= 1ull << bone;
                break;
            }
            fh = (fh + 1) & (kFieldTab - 1);
        }
    }
}

uint32_t g_svc_lo, g_svc_hi;   // the native services' region (svc_census_watch), traced like the arena
void arena_prot(int prot)
{
    mprotect((void*) (uintptr_t) HOST_ARENA_BASE, HOST_ARENA_SIZE, prot);
    if (g_svc_hi) mprotect((void*) (uintptr_t) g_svc_lo, g_svc_hi - g_svc_lo, prot);
}
bool watched(unsigned a)
{
    return (a >= HOST_ARENA_BASE && a < HOST_ARENA_BASE + HOST_ARENA_SIZE) || (a >= g_svc_lo && a < g_svc_hi);
}
// pages opened for the instruction being stepped (an instruction can touch two pages, or two operands)
uint32_t g_open[8];
unsigned g_nopen;

void on_segv(int, siginfo_t* si, void* ctx)
{
    ucontext_t* uc = (ucontext_t*) ctx;
    const unsigned addr = (unsigned) (uintptr_t) si->si_addr;
    if (!g_armed || !watched(addr) || g_nopen >= 8) {
        signal(SIGSEGV, SIG_DFL);
        return;
    }
    record((unsigned) uc->uc_mcontext.gregs[REG_EIP], addr, (uc->uc_mcontext.gregs[REG_ERR] & 2) != 0);
    // open this page and the next (an unaligned access may straddle them), step the instruction
    uint32_t page = addr & ~4095u;
    const uint32_t top = addr >= g_svc_lo && addr < g_svc_hi ? g_svc_hi : HOST_ARENA_BASE + HOST_ARENA_SIZE;
    uint32_t len = page + 8192 <= top ? 8192 : 4096;
    mprotect((void*) (uintptr_t) page, len, PROT_READ | PROT_WRITE);
    g_open[g_nopen++] = page | (len >> 12);
    uc->uc_mcontext.gregs[REG_EFL] |= 0x100;
}
void on_trap(int, siginfo_t*, void* ctx)
{
    ucontext_t* uc = (ucontext_t*) ctx;
    uc->uc_mcontext.gregs[REG_EFL] &= ~0x100;
    for (unsigned i = 0; i < g_nopen; i++)
        if (g_armed) mprotect((void*) (uintptr_t) (g_open[i] & ~4095u), (g_open[i] & 4095u) << 12, PROT_NONE);
    g_nopen = 0;
}

const char* out_dir() { const char* d = getenv("RE4_SVC_OUT"); return d && *d ? d : "."; }
FILE* out_open(const char* name)
{
    char p[1024];
    snprintf(p, sizeof p, "%s/%s", out_dir(), name);
    FILE* f = fopen(p, "w");
    if (!f) { fprintf(stderr, "svc census: cannot write %s\n", p); exit(4); }
    return f;
}
}   // namespace

extern "C" void* __real_host_fixed(uint32_t size, const char* why);
extern "C" void* __wrap_host_fixed(uint32_t size, const char* why)
{
    void* p = __real_host_fixed(size, why);
    if (g_nloads < 64) {
        int reg = SVC_R_CHR;
        if (!strcmp(why, "room")) reg = SVC_R_ROOM;
        else if (!strcmp(why, "core")) reg = SVC_R_CORE;
        g_loads[g_nloads].lo = (uint32_t) (uintptr_t) p;
        g_loads[g_nloads].hi = (uint32_t) (uintptr_t) p + size;
        g_loads[g_nloads].reg = reg;
        g_nloads++;
    }
    return p;
}

extern "C" void census_hit(unsigned idx, unsigned ret, unsigned arg0)
{
    if (!g_on || g_in_hit || idx >= kMaxSym) return;
    g_in_hit = true;
    if (census_kind[idx] == 'S') {
        const unsigned depth0 = census_sp == 0;
        const unsigned actor = depth0 ? actor_of(arg0) : actor_of(census_arg[0]);
        unsigned h = hash3(idx, ret, actor * 2 + depth0) & (kCallTab - 1);
        for (;;) {
            CallKey& k = g_calls[h];
            if (!k.n) { k.idx = idx; k.ret = ret; k.actor = actor; k.depth0 = depth0; }
            if (k.idx == idx && k.ret == ret && k.actor == actor && k.depth0 == depth0) { k.n++; break; }
            h = (h + 1) & (kCallTab - 1);
        }
        g_tick_calls[idx]++;
    } else if (census_msp == 0) {   // helpers called by helpers (PSMTXConcat -> C_MTXConcat) are not counted again
        const unsigned ctx = census_sp ? census_idx[0] : kMaxSym;
        const unsigned actor = census_sp ? actor_of(census_arg[0]) : kNone;
        unsigned h = hash3(idx, ctx, actor) & (kCallTab - 1);
        for (;;) {
            MKey& k = g_mcalls[h];
            if (!k.n) { k.idx = idx; k.ctx = ctx; k.actor = actor; }
            if (k.idx == idx && k.ctx == ctx && k.actor == actor) { k.n++; break; }
            h = (h + 1) & (kCallTab - 1);
        }
        g_tick_calls[idx]++;
    }
    g_in_hit = false;
}

extern "C" void svc_census_regions(const SvcRegion* r)
{
    for (int i = 0; i < SVC_REGIONS; i++) g_reg[i] = r[i];
    if (census_nsyms > kMaxSym) {
        fprintf(stderr, "svc census: %u symbols, the tables hold %u\n", census_nsyms, kMaxSym);
        exit(4);
    }
    g_trace = getenv("RE4_SVC_TRACE") && atoi(getenv("RE4_SVC_TRACE")) != 0;
    if (getenv("RE4_SVC_TRACE_FROM")) g_from = (unsigned) atoi(getenv("RE4_SVC_TRACE_FROM"));
    if (getenv("RE4_SVC_TRACE_TO")) g_to = (unsigned) atoi(getenv("RE4_SVC_TRACE_TO"));
    if (g_trace) {
        g_lines = (LineKey*) calloc(kLineTab, sizeof(LineKey));
        g_mem = (MemAgg*) calloc((size_t) (kMaxSym + 1) * kActors * SVC_REGIONS, sizeof(MemAgg));
        g_fields = (FieldKey*) calloc(kFieldTab, sizeof(FieldKey));
        g_klines = (KindKey*) calloc(kLineTab, sizeof(KindKey));
        g_kmem = (MemAgg*) calloc((size_t) 4 * kActors * SVC_REGIONS, sizeof(MemAgg));
        init_kinds();
        struct sigaction sa;
        memset(&sa, 0, sizeof sa);
        sa.sa_flags = SA_SIGINFO;
        sa.sa_sigaction = on_segv;
        sigaction(SIGSEGV, &sa, 0);
        sa.sa_sigaction = on_trap;
        sigaction(SIGTRAP, &sa, 0);
    }
    g_on = true;
}

extern "C" void svc_census_parts(unsigned lo, unsigned stride, unsigned n, const uint8_t* owner, const uint8_t* bone)
{
    g_part_lo = lo; g_part_stride = stride; g_part_n = n; g_part_owner = owner; g_part_bone = bone;
}

extern "C" void svc_census_tick(unsigned t, int begin)
{
    if (begin) {
        g_tick = t;
        memset(g_tick_calls, 0, sizeof g_tick_calls);
        g_tick_traced = g_trace && t >= g_from && t <= g_to;
        if (g_tick_traced) { g_armed = true; arena_prot(PROT_NONE); }
        return;
    }
    if (g_tick_traced) { g_armed = false; arena_prot(PROT_READ | PROT_WRITE); g_traced++; }
    g_ticks++;
    for (unsigned i = 0; i < census_nsyms && i < kMaxSym; i++) {
        g_tot_calls[i] += g_tick_calls[i];
        if (g_tick_calls[i] > g_max_calls[i]) g_max_calls[i] = g_tick_calls[i];
    }
    if (g_tick_traced)
        for (size_t i = 0; i < (size_t) 4 * kActors * SVC_REGIONS; i++) {
            MemAgg& m = g_kmem[i];
            if (!m.lines_tick) continue;
            m.lines += m.lines_tick;
            if (m.lines_tick > m.lines_max) m.lines_max = m.lines_tick;
            m.lines_tick = 0;
        }
    if (g_trace)
        for (size_t i = 0; i < (size_t) (kMaxSym + 1) * kActors * SVC_REGIONS; i++) {
            MemAgg& m = g_mem[i];
            if (!m.lines_tick) continue;
            m.lines += m.lines_tick;
            if (m.lines_tick > m.lines_max) m.lines_max = m.lines_tick;
            m.lines_tick = 0;
        }
}

extern "C" void svc_census_finish(const char* actors_tsv)
{
    if (!g_on) return;
    g_on = false;
    if (g_trace) { g_armed = false; arena_prot(PROT_READ | PROT_WRITE); }
    FILE* f = out_open("calls.tsv");
    fprintf(f, "# ticks\t%u\n# idx\tname\tunit\tkind\tcaller_ret\tdepth0\tactor\tcount\n", g_ticks);
    for (unsigned i = 0; i < kCallTab; i++)
        if (g_calls[i].n)
            fprintf(f, "%u\t%s\t%s\tS\t%08x\t%u\t%u\t%llu\n", g_calls[i].idx, census_name[g_calls[i].idx], census_unit[g_calls[i].idx],
                    g_calls[i].ret, g_calls[i].depth0, g_calls[i].actor, (unsigned long long) g_calls[i].n);
    fclose(f);
    f = out_open("mcalls.tsv");
    fprintf(f, "# ticks\t%u\n# idx\tname\tunit\tctx\tctx_name\tactor\tcount\n", g_ticks);
    for (unsigned i = 0; i < kCallTab; i++)
        if (g_mcalls[i].n)
            fprintf(f, "%u\t%s\t%s\t%u\t%s\t%u\t%llu\n", g_mcalls[i].idx, census_name[g_mcalls[i].idx], census_unit[g_mcalls[i].idx],
                    g_mcalls[i].ctx, g_mcalls[i].ctx < kMaxSym ? census_name[g_mcalls[i].ctx] : "-", g_mcalls[i].actor,
                    (unsigned long long) g_mcalls[i].n);
    fclose(f);
    f = out_open("totals.tsv");
    fprintf(f, "# ticks\t%u\n# idx\tname\tunit\tkind\ttotal\tmax_per_tick\n", g_ticks);
    for (unsigned i = 0; i < census_nsyms && i < kMaxSym; i++)
        if (g_tot_calls[i])
            fprintf(f, "%u\t%s\t%s\t%c\t%llu\t%u\n", i, census_name[i], census_unit[i], census_kind[i],
                    (unsigned long long) g_tot_calls[i], g_max_calls[i]);
    fclose(f);
    if (g_trace) {
        static const char* rn[SVC_REGIONS] = {"parts", "em", "obj", "room", "chr", "core", "heap", "svc", "other"};
        f = out_open("mem.tsv");
        fprintf(f, "# ticks\t%u\n# ctx\tctx_name\tctx_unit\tactor\tregion\taccesses\treads\twrites\tlines_sum\tlines_max\tticks_seen\n", g_traced);
        for (unsigned c = 0; c <= kMaxSym; c++)
            for (unsigned a = 0; a < kActors; a++)
                for (unsigned r = 0; r < SVC_REGIONS; r++) {
                    MemAgg& m = mem(c, a, r);
                    if (!m.acc) continue;
                    fprintf(f, "%u\t%s\t%s\t%u\t%s\t%llu\t%llu\t%llu\t%llu\t%u\t%u\n", c, c < kMaxSym ? census_name[c] : "-",
                            c < kMaxSym ? census_unit[c] : "-", a, rn[r], (unsigned long long) m.acc, (unsigned long long) m.rd,
                            (unsigned long long) m.wr, (unsigned long long) m.lines, m.lines_max, m.ticks);
                }
        fclose(f);
        f = out_open("memk.tsv");
        fprintf(f, "# ticks\t%u\n# kind\tactor\tregion\taccesses\treads\twrites\tlines_sum\tlines_max\tticks_seen\n", g_traced);
        static const char* kn[4] = {"none", "skeleton", "collision", "other"};
        for (unsigned kd = 0; kd < 4; kd++)
            for (unsigned a = 0; a < kActors; a++)
                for (unsigned r = 0; r < SVC_REGIONS; r++) {
                    MemAgg& m = kmem(kd, a, r);
                    if (!m.acc) continue;
                    fprintf(f, "%s\t%u\t%s\t%llu\t%llu\t%llu\t%llu\t%u\t%u\n", kn[kd], a, rn[r], (unsigned long long) m.acc,
                            (unsigned long long) m.rd, (unsigned long long) m.wr, (unsigned long long) m.lines, m.lines_max, m.ticks);
                }
        fclose(f);
        f = out_open("fields.tsv");
        fprintf(f, "# ticks\t%u\n# eip\tctx\tctx_name\tregion\toffset\tw\tcount\tticks\tbones\n", g_traced);
        for (unsigned i = 0; i < kFieldTab; i++) {
            FieldKey& k = g_fields[i];
            if (!k.used) continue;
            fprintf(f, "%08x\t%u\t%s\t%s\t%u\t%u\t%u\t%u\t%016llx\n", k.eip, k.ctx, k.ctx < kMaxSym ? census_name[k.ctx] : "-", rn[k.reg],
                    k.off, k.w, k.n, k.nticks, (unsigned long long) k.bones);
        }
        fclose(f);
    }
    f = out_open("actors.tsv");
    fputs(actors_tsv, f);
    fclose(f);
}

// Load-time work the PC build does lazily (the motion-key binding): not counted. The engine image does it at load.
extern "C" void svc_census_pause(int on)
{
    if (!g_tick_traced) return;
    if (on) { g_armed = false; arena_prot(PROT_READ | PROT_WRITE); }
    else { g_armed = true; arena_prot(PROT_NONE); }
}

extern "C" void svc_census_watch(uint32_t lo, uint32_t bytes)
{
    g_svc_lo = lo;
    g_svc_hi = lo + bytes;
}
