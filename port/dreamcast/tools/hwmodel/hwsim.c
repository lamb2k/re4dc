/*
 * hwsim.c - SH7091 (SH-4 @200 MHz) timing model driven by hwtrace frame traces.
 *
 * Input: the game ELF (code bytes for decoding) and one or more trace-NNNNN.bin files written
 * by the hwtrace Flycast build (core/hw/sh4/interpr/hwtrace.h documents the format).
 *
 * Model (per dynamic instruction, in program order):
 *   - in-order dual issue with the SH-4 groups/pairing table (SH-4 Software Manual 6.00, 8.2),
 *     issue rates and latencies from table 8.3, F0 (FTRV/FIPR) and F3 (FDIV/FSQRT) locks;
 *   - branch redirect latency (BT/BF/BRA/BSR 2, JMP/JSR/RTS/BRAF/BSRF 3, RTE 5);
 *   - IC 8 KB direct-mapped, 32 B lines, index addr[12:5] (IIX=0), miss = line fill that
 *     blocks issue;
 *   - OC 16 KB direct-mapped (or 8 KB with --oc-kb 8 = ORA), 32 B lines, index addr[13:5]
 *     (OIX=0) or addr[25],addr[12:5] (OIX=1), copy-back with write-allocate (KOS CCR: CB=1,
 *     WT=0), write-back buffer (victim write overlaps, occupies the bus), MOVCA.L allocates
 *     without a fill, PREF is a non-blocking fill, OCBI/OCBP/OCBWB;
 *   - D-miss = pipeline freeze until the line arrives (charged to the missing instruction);
 *   - one external bus (fills, write-backs, store-queue bursts, uncached accesses serialise);
 *     SDRAM open-row model (4 banks x 2 KB rows): fill = row hit / row miss cost;
 *   - store queues: stores to 0xE0000000 are 1-cycle; PREF to the SQ area starts a 32 B
 *     burst; a store to an SQ still being flushed stalls;
 *   - uncached (P2/area 0/VRAM/Holly/AICA/P4) accesses cost the Sega access-time table.
 *   - DMA from system RAM (trace events 11/12: ch2 to TA/texture, PVR-DMA, G2/AICA, GD-ROM)
 *     occupies the same bus in 32 B bursts at the device's rate; CPU fills, write-backs, SQ
 *     bursts and uncached accesses queue behind a burst in progress (--no-dma to disable).
 * Also computed: the Flycast dynarec cycle charge (Sh4Cycles::countCycles: naive pairing
 * + 2 cycles for each of the first 3 memory ops of a block) for comparison.
 *
 * Output: --out PREFIX writes PREFIX.pcs.tsv (per executed PC counters) and PREFIX.sum.txt.
 */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <math.h>

typedef uint64_t u64; typedef uint32_t u32; typedef uint16_t u16; typedef uint8_t u8; typedef int64_t s64; typedef int32_t s32;

/* ---------------- configuration ---------------- */
static int OC_KB = 16, OIX = 0, IIX = 0;
static double FILL_HIT = 14, FILL_MISS = 24, FILL_OVH = 4;     /* CPU cycles; bus clocks x2 */
static double WB_HIT = 8, WB_MISS = 18;                          /* dirty victim write, bus occupancy */
static double SQ_COST = 14;                                      /* 32 B store-queue burst to TA */
static double ICFILL_EXTRA = 0;                                  /* extra cycles on I-miss */
/* Console-fitted miss penalties (2026-10-15 hwmiss lane): CPU-side latency added to every D fill (first beat and
   line end; the bus is not held longer) and to every I fill, plus extra bus occupancy per dirty write-back.
   0 = the nominal model. Fitted values: see docs/lanes/hwmodel-miss.md (--console-fit). */
static double DMISS_LAT = 0, IMISS_LAT = 0, WB_EXTRA = 0, WMISS_LAT = 0;
/* --console-fit (refit 2026-10-15, lane storemiss, constrained by console Bench A ACTOR_MOVCA ~0 and Bench B MEM_MOVCA
   +0.5 house): D fill +6, I fill +5, store miss 0. --console-fit-w70: the first fit (D 0, I 4, store miss 70), which
   those two console pairs contradict; kept for comparison only. */
#define CF_D 6
#define CF_I 5
#define CF_W 0
#define CF70_D 0
#define CF70_I 4
#define CF70_W 70   /* write-miss extra (WMISS_LAT); WB_EXTRA stays 0 */
static int STREAMPF = 0;                                         /* oracle software prefetch */
static int NO_ICACHE_MISS = 0, NO_DCACHE_MISS = 0;
static int WA_STREAM = 0, WA_NOFILL = 0, NO_DEP = 0;  /* NO_DEP: ideal scheduling bound */   /* write-allocate what-ifs: movca.l / store-queue style full-line writes */
static u64 n_fill, n_wb, n_ifill;
static const char *OUT = "hwsim";
static double FDIV_LAT_OVR = -1;                                  /* fdiv latency in --fdiv-ranges */
static int FDIV_LOCK_OVR = -1;

/* ---------------- memory image ---------------- */
#define RAM_SIZE (16u << 20)
static u8 *ram;
static int ram_valid(u32 a) { return (a & 0x1C000000u) == 0x0C000000u; }
static u16 code_at(u32 pc) { u32 o = pc & 0xFFFFFF; return (u16)(ram[o] | (ram[o + 1] << 8)); }

static void load_elf(const char *path)
{
    FILE *f = fopen(path, "rb"); if (!f) { perror(path); exit(1); }
    u8 eh[52]; if (fread(eh, 1, 52, f) != 52) exit(1);
    u32 phoff = *(u32 *)(eh + 28); u16 phentsize = *(u16 *)(eh + 42), phnum = *(u16 *)(eh + 44);
    for (int i = 0; i < phnum; i++) {
        u8 ph[32]; fseek(f, phoff + i * phentsize, SEEK_SET); if (fread(ph, 1, 32, f) != 32) exit(1);
        u32 type = *(u32 *)ph, off = *(u32 *)(ph + 4), vaddr = *(u32 *)(ph + 8), filesz = *(u32 *)(ph + 16);
        if (type != 1 || !ram_valid(vaddr)) continue;
        fseek(f, off, SEEK_SET);
        if (fread(ram + (vaddr & 0xFFFFFF), 1, filesz, f) != filesz) { fprintf(stderr, "short elf\n"); exit(1); }
    }
    fclose(f);
}

/* ---------------- decoder ---------------- */
enum { G_MT, G_EX, G_BR, G_LS, G_FE, G_CO };
enum { K_LOAD = 1, K_STORE = 2, K_BRC = 4, K_BRCD = 8, K_BRU = 16, K_BRREG = 32, K_FDIV = 64, K_FSQRT = 128,
       K_FTRV = 256, K_FIPR = 512, K_MUL = 1024, K_FSCHG = 2048, K_SHAMT = 4096, K_RTE = 8192, K_FE_RES = 16384,
       K_LOADFP = 32768 };
/* register bits */
#define R(n) (1ull << (n))
#define FR(n) (1ull << (16 + (n)))
#define XF_ALL (0xFFFFull << 32)
#define B_FPUL (1ull << 48)
#define B_MAC (1ull << 49)
#define B_T (1ull << 50)
#define B_PR (1ull << 51)
#define B_GBR (1ull << 52)
#define B_FPSCR (1ull << 53)
#define B_SR (1ull << 54)
#define FV(n) (0xFull << (16 + 4 * (n)))

typedef struct {
    u8 grp, issue, lat, lat2;   /* lat: main defs; lat2: address-register update / secondary */
    u32 kind;
    u64 def, def2, use;
} Dec;
static Dec dtab[65536];

static void D(Dec *d, int grp, int issue, int lat, u64 def, u64 use, u32 kind)
{
    d->grp = grp; d->issue = issue; d->lat = lat; d->def = def; d->use = use; d->kind = kind; d->lat2 = 1; d->def2 = 0;
}

static void decode_all(void)
{
    for (u32 op = 0; op < 65536; op++) {
        Dec *d = &dtab[op];
        int n = (op >> 8) & 15, m = (op >> 4) & 15, lo = op & 15;
        D(d, G_EX, 1, 1, 0, 0, 0);   /* default */
        switch (op >> 12) {
        case 0x0:
            if (lo == 2) { D(d, G_CO, 2, 2, R(n), B_SR | B_GBR, 0); }                       /* stc */
            else if (lo == 3) {
                switch (m) {
                case 0: D(d, G_CO, 2, 3, B_PR, R(n), K_BRREG); break;                        /* bsrf */
                case 2: D(d, G_CO, 2, 3, 0, R(n), K_BRREG); break;                           /* braf */
                case 8: case 9: case 10: case 11: D(d, G_LS, 1, 1, 0, R(n), 0); break;       /* pref/ocb* */
                case 12: D(d, G_LS, 1, 3, 0, R(n) | R(0), K_STORE); break;                   /* movca.l */
                default: break;
                }
            }
            else if (lo >= 4 && lo <= 6) D(d, G_LS, 1, 1, 0, R(n) | R(m) | R(0), K_STORE);
            else if (lo == 7) D(d, G_CO, 2, 4, B_MAC, R(n) | R(m), K_MUL);                    /* mul.l */
            else if (lo == 8) { if (m == 2) D(d, G_CO, 1, 3, B_MAC, 0, 0); else if (m <= 1) D(d, G_MT, 1, 1, B_T, 0, 0); else D(d, G_CO, 1, 1, B_SR, 0, 0); }
            else if (lo == 9) { if (m == 0) D(d, G_MT, 1, 1, 0, 0, 0); else if (m == 1) D(d, G_EX, 1, 1, B_T, 0, 0); else D(d, G_EX, 1, 1, R(n), B_T, 0); }
            else if (lo == 0xB) { if (m == 0) D(d, G_CO, 2, 3, 0, B_PR, K_BRREG); else if (m == 1) D(d, G_CO, 4, 4, 0, 0, 0); else D(d, G_CO, 5, 5, B_SR, 0, K_BRREG | K_RTE); }
            else if (lo >= 0xC && lo <= 0xE) D(d, G_LS, 1, 2, R(n), R(m) | R(0), K_LOAD);
            else if (lo == 0xF) D(d, G_CO, 2, 4, B_MAC | R(n) | R(m), R(n) | R(m) | B_MAC, K_LOAD | K_MUL);
            else if (lo == 0xA) {
                if (m == 5) D(d, G_LS, 1, 3, R(n), B_FPUL, 0);                                  /* sts fpul */
                else if (m == 2) D(d, G_CO, 2, 2, R(n), B_PR, 0);                              /* sts pr */
                else if (m <= 1) D(d, G_CO, 1, 3, R(n), B_MAC, 0);                             /* sts mac */
                else D(d, G_CO, 1, 3, R(n), B_FPSCR, 0);
            }
            break;
        case 0x1: D(d, G_LS, 1, 1, 0, R(n) | R(m), K_STORE); break;
        case 0x2:
            switch (lo) {
            case 0: case 1: case 2: D(d, G_LS, 1, 1, 0, R(n) | R(m), K_STORE); break;
            case 4: case 5: case 6: D(d, G_LS, 1, 1, 0, R(n) | R(m), K_STORE); d->def2 = R(n); break;
            case 7: D(d, G_EX, 1, 1, B_T, R(n) | R(m), 0); break;
            case 8: case 0xC: D(d, G_MT, 1, 1, B_T, R(n) | R(m), 0); break;
            case 9: case 0xA: case 0xB: case 0xD: D(d, G_EX, 1, 1, R(n), R(n) | R(m), 0); break;
            case 0xE: case 0xF: D(d, G_CO, 2, 4, B_MAC, R(n) | R(m), K_MUL); break;
            default: break;
            }
            break;
        case 0x3:
            if (lo == 0 || lo == 2 || lo == 3 || lo == 6 || lo == 7) D(d, G_MT, 1, 1, B_T, R(n) | R(m), 0);
            else if (lo == 5 || lo == 0xD) D(d, G_CO, 2, 4, B_MAC, R(n) | R(m), K_MUL);
            else if (lo == 4 || lo == 0xA || lo == 0xE) D(d, G_EX, 1, 1, R(n) | B_T, R(n) | R(m) | B_T, 0);
            else if (lo == 0xB || lo == 0xF) D(d, G_EX, 1, 1, R(n) | B_T, R(n) | R(m), 0);
            else D(d, G_EX, 1, 1, R(n), R(n) | R(m), 0);
            break;
        case 0x4: {
            int x = op & 0xFF;
            if (lo == 0xC || lo == 0xD) { D(d, G_EX, 1, 1, R(n), R(n) | R(m), K_SHAMT); break; }
            if (lo == 0xF) { D(d, G_CO, 2, 4, B_MAC | R(n) | R(m), R(n) | R(m) | B_MAC, K_LOAD | K_MUL); break; }
            switch (x) {
            case 0x00: case 0x01: case 0x04: case 0x05: case 0x20: case 0x21: case 0x24: case 0x25:
                D(d, G_EX, 1, 1, R(n) | B_T, R(n) | B_T, 0); break;
            case 0x08: case 0x09: case 0x18: case 0x19: case 0x28: case 0x29:
                D(d, G_EX, 1, 1, R(n), R(n), 0); break;
            case 0x10: D(d, G_EX, 1, 1, R(n) | B_T, R(n), 0); break;                                 /* dt */
            case 0x11: case 0x15: D(d, G_MT, 1, 1, B_T, R(n), 0); break;
            case 0x0B: D(d, G_CO, 2, 3, B_PR, R(n), K_BRREG); break;                                 /* jsr */
            case 0x2B: D(d, G_CO, 2, 3, 0, R(n), K_BRREG); break;                                    /* jmp */
            case 0x22: D(d, G_CO, 2, 2, 0, R(n) | B_PR, K_STORE); d->def2 = R(n); break;              /* sts.l pr */
            case 0x26: D(d, G_CO, 2, 3, B_PR, R(n), K_LOAD); d->def2 = R(n); break;                   /* lds.l pr */
            case 0x2A: D(d, G_CO, 2, 3, B_PR, R(n), 0); break;                                       /* lds pr */
            case 0x02: case 0x12: case 0x52: case 0x62: D(d, G_CO, 1, 1, 0, R(n) | B_MAC | B_FPUL | B_FPSCR, K_STORE); d->def2 = R(n); break;
            case 0x06: case 0x16: D(d, G_CO, 1, 3, B_MAC, R(n), K_LOAD); d->def2 = R(n); break;
            case 0x56: D(d, G_CO, 1, 2, B_FPUL, R(n), K_LOAD); d->def2 = R(n); break;
            case 0x66: D(d, G_CO, 1, 4, B_FPSCR, R(n), K_LOAD | K_FSCHG); d->def2 = R(n); break;
            case 0x0A: case 0x1A: D(d, G_CO, 1, 3, B_MAC, R(n), 0); break;
            case 0x5A: D(d, G_LS, 1, 1, B_FPUL, R(n), 0); break;                                      /* lds fpul */
            case 0x6A: D(d, G_CO, 1, 4, B_FPSCR, R(n), K_FSCHG); break;
            case 0x1B: D(d, G_CO, 5, 5, B_T, R(n), K_LOAD | K_STORE); break;                          /* tas.b */
            case 0x1E: D(d, G_CO, 3, 3, B_GBR, R(n), 0); break;
            case 0x17: D(d, G_CO, 3, 3, B_GBR, R(n), K_LOAD); d->def2 = R(n); break;
            case 0x07: D(d, G_CO, 4, 4, B_SR, R(n), K_LOAD); d->def2 = R(n); break;
            case 0x0E: D(d, G_CO, 4, 4, B_SR, R(n), 0); break;
            default:
                if (lo == 3 || lo == 2) { D(d, G_CO, 2, 2, 0, R(n), K_STORE); d->def2 = R(n); }
                else if (lo == 7) { D(d, G_CO, 1, 3, 0, R(n), K_LOAD); d->def2 = R(n); }
                else if (lo == 0xE || lo == 0xA) D(d, G_CO, 1, 3, 0, R(n), 0);
                break;
            }
            break; }
        case 0x5: D(d, G_LS, 1, 2, R(n), R(m), K_LOAD); break;
        case 0x6:
            if (lo <= 2) D(d, G_LS, 1, 2, R(n), R(m), K_LOAD);
            else if (lo == 3) D(d, G_MT, 1, 0, R(n), R(m), 0);
            else if (lo <= 6) { D(d, G_LS, 1, 2, R(n), R(m), K_LOAD); if (n != m) d->def2 = R(m); }
            else if (lo == 0xA) D(d, G_EX, 1, 1, R(n) | B_T, R(m) | B_T, 0);
            else D(d, G_EX, 1, 1, R(n), R(m), 0);
            break;
        case 0x7: D(d, G_EX, 1, 1, R(n), R(n), 0); break;
        case 0x8:
            switch (n) {
            case 0: case 1: D(d, G_LS, 1, 1, 0, R(0) | R(m), K_STORE); break;
            case 4: case 5: D(d, G_LS, 1, 2, R(0), R(m), K_LOAD); break;
            case 8: D(d, G_MT, 1, 1, B_T, R(0), 0); break;
            case 9: case 0xB: D(d, G_BR, 1, 2, 0, B_T, K_BRC); break;
            case 0xD: case 0xF: D(d, G_BR, 1, 2, 0, B_T, K_BRCD); break;
            default: break;
            }
            break;
        case 0x9: case 0xD: D(d, G_LS, 1, 2, R(n), 0, K_LOAD); break;
        case 0xA: D(d, G_BR, 1, 2, 0, 0, K_BRU); break;
        case 0xB: D(d, G_BR, 1, 2, B_PR, 0, K_BRU); break;
        case 0xC:
            switch (n) {
            case 0: case 1: case 2: D(d, G_LS, 1, 1, 0, R(0) | B_GBR, K_STORE); break;
            case 3: D(d, G_CO, 7, 7, B_SR, 0, K_BRREG | K_RTE); break;                               /* trapa */
            case 4: case 5: case 6: D(d, G_LS, 1, 2, R(0), B_GBR, K_LOAD); break;
            case 7: D(d, G_EX, 1, 1, R(0), 0, 0); break;
            case 8: D(d, G_MT, 1, 1, B_T, R(0), 0); break;
            case 9: case 0xA: case 0xB: D(d, G_EX, 1, 1, R(0), R(0), 0); break;
            case 0xC: D(d, G_CO, 3, 3, B_T, R(0) | B_GBR, K_LOAD); break;
            default: D(d, G_CO, 4, 4, 0, R(0) | B_GBR, K_LOAD | K_STORE); break;
            }
            break;
        case 0xE: D(d, G_EX, 1, 1, R(n), 0, 0); break;
        case 0xF:
            switch (lo) {
            case 0: case 1: case 2: D(d, G_FE, 1, 3, FR(n), FR(n) | FR(m), K_FE_RES); break;
            case 3: D(d, G_FE, 1, 12, FR(n), FR(n) | FR(m), K_FDIV); break;
            case 4: case 5: D(d, G_FE, 1, 2, B_T, FR(n) | FR(m), 0); break;
            case 6: D(d, G_LS, 1, 2, FR(n), R(0) | R(m), K_LOAD | K_LOADFP); break;
            case 7: D(d, G_LS, 1, 1, 0, R(0) | R(n) | FR(m), K_STORE); break;
            case 8: D(d, G_LS, 1, 2, FR(n), R(m), K_LOAD | K_LOADFP); break;
            case 9: D(d, G_LS, 1, 2, FR(n), R(m), K_LOAD | K_LOADFP); d->def2 = R(m); break;
            case 0xA: D(d, G_LS, 1, 1, 0, R(n) | FR(m), K_STORE); break;
            case 0xB: D(d, G_LS, 1, 1, 0, R(n) | FR(m), K_STORE); d->def2 = R(n); break;
            case 0xC: D(d, G_LS, 1, 0, FR(n), FR(m), 0); break;
            case 0xE: D(d, G_FE, 1, 3, FR(n), FR(n) | FR(m) | FR(0), K_FE_RES); break;
            case 0xD:
                switch (m) {
                case 0: D(d, G_LS, 1, 0, FR(n), B_FPUL, 0); break;              /* fsts */
                case 1: D(d, G_LS, 1, 0, B_FPUL, FR(n), 0); break;              /* flds */
                case 2: D(d, G_FE, 1, 3, FR(n), B_FPUL, K_FE_RES); break;       /* float */
                case 3: D(d, G_FE, 1, 3, B_FPUL, FR(n), K_FE_RES); break;       /* ftrc */
                case 4: case 5: D(d, G_LS, 1, 0, FR(n), FR(n), 0); break;       /* fneg/fabs */
                case 6: D(d, G_FE, 1, 11, FR(n), FR(n), K_FSQRT); break;
                case 7: D(d, G_FE, 1, 5, FR(n), FR(n), K_FE_RES); break;       /* fsrra: undocumented, 5 assumed */
                case 8: case 9: D(d, G_LS, 1, 0, FR(n), 0, 0); break;           /* fldi */
                case 0xA: case 0xB: D(d, G_FE, 1, 4, FR(n) | B_FPUL, FR(n) | B_FPUL, K_FE_RES); break;
                case 0xE: { int vn = (op >> 10) & 3, vm = (op >> 8) & 3;
                    D(d, G_FE, 1, 4, FR(vn * 4 + 3), FV(vn) | FV(vm), K_FIPR); break; }
                case 0xF:
                    if ((op & 0x3FF) == 0x1FD) { int vn = (op >> 10) & 3; D(d, G_FE, 1, 6, FV(vn), FV(vn) | XF_ALL, K_FTRV); }
                    else if (op == 0xFBFD) D(d, G_FE, 1, 1, FR(0) | XF_ALL, FR(0), K_FSCHG);
                    else if (op == 0xF3FD) D(d, G_FE, 1, 1, B_FPSCR, B_FPSCR, K_FSCHG);
                    else if ((op & 0x1FF) == 0x0FD) { int dn = (op >> 9) & 7; D(d, G_FE, 1, 4, FR(2 * dn) | FR(2 * dn + 1), B_FPUL, K_FE_RES); } /* fsca */
                    break;
                default: break;
                }
                break;
            default: break;
            }
            break;
        }
    }
}

/* ---------------- per-PC statistics ---------------- */
enum { C_BASE, C_DEP_LOAD, C_DEP_FPU, C_DEP_FDIV, C_DEP_OTHER, C_FLOCK, C_BRANCH, C_IMISS, C_DMISS, C_PFWAIT, C_SQ,
       C_UNCACHED, C_NCAT };
static const char *catname[C_NCAT] = { "base", "dep_load", "dep_fpu", "dep_fdiv", "dep_other", "flock", "branch",
                                       "imiss", "dmiss", "pfwait", "sq", "uncached" };
typedef struct {
    u64 exec, fly, cyc[C_NCAT];
    u32 imiss, drmiss, dwmiss, wb, pf, pfuse, sqf, stream_miss, uncached, reads, writes, fdiv, induced;
    u64 words_used, fills_owned, evict_victims;
} PcStat;
#define NPC (1u << 23)
static PcStat *ps;     /* indexed by (pc & 0xFFFFFF) >> 1 */
static PcStat other;   /* PCs outside RAM */
static PcStat *PS(u32 pc) { return ram_valid(pc) ? &ps[(pc & 0xFFFFFF) >> 1] : &other; }

/* ---------------- range lists (what-if) ---------------- */
typedef struct { u32 lo, hi; } Range;
typedef struct { Range *r; int n; } RList;
static RList fdiv_ranges, skip_ranges;
static void rl_load(RList *l, const char *path)
{
    FILE *f = fopen(path, "r"); if (!f) { perror(path); exit(1); }
    u32 a, b; l->r = malloc(sizeof(Range) * 200000); l->n = 0;
    while (fscanf(f, "%x %x", &a, &b) == 2) { l->r[l->n].lo = a & 0x1FFFFFFF; l->r[l->n].hi = b & 0x1FFFFFFF; l->n++; }
    fclose(f);
}
static int rl_has(const RList *l, u32 pc)
{
    pc &= 0x1FFFFFFF;
    int lo = 0, hi = l->n - 1;
    while (lo <= hi) { int mid = (lo + hi) / 2; if (pc < l->r[mid].lo) hi = mid - 1; else if (pc >= l->r[mid].hi) lo = mid + 1; else return 1; }
    return 0;
}
/* D remap (--dmap FILE, layout what-if): lines "lo hi delta" (hex, hex, signed decimal bytes); a traced data
   access or DMA source in system RAM with lo <= phys < hi is moved by delta (e.g. IMAGE_PAD_BYTES: everything from
   the pad's position up to the kernel stack). Code fetches are not moved. */
typedef struct { u32 lo, hi; s32 d; } DRange;
static DRange dmap[64]; static int ndmap;
static u32 dmap_addr(u32 a)
{
    u32 p = a & 0x1FFFFFFF;
    if (p < 0x0C000000 || p >= 0x10000000) return a;
    u32 q = p & 0x0CFFFFFF;                   /* RAM mirrors */
    for (int i = 0; i < ndmap; i++)
        if (q >= dmap[i].lo && q < dmap[i].hi) return (u32)(a + dmap[i].d);
    return a;
}
/* C remap (--cmap FILE, same format): instruction fetches in a range are moved by delta bytes (any multiple of 2: a
   sub-line shift changes which 32 B lines a function's code occupies). Literal-pool loads are data: give the same
   ranges to --dmap. */
static DRange cmap[64]; static int ncmap;
static u32 cmap_pc(u32 pc)
{
    u32 q = pc & 0x0CFFFFFF;
    for (int i = 0; i < ncmap; i++)
        if (q >= cmap[i].lo && q < cmap[i].hi) return (u32)(pc + cmap[i].d);
    return pc;
}
static void load_ranges(const char *path, DRange *r, int *n, const char *what)
{
    FILE *f = fopen(path, "r"); u32 lo, hi; int d;
    if (!f) { perror(path); exit(1); }
    while (*n < 64 && fscanf(f, "%x %x %d", &lo, &hi, &d) == 3) {
        r[*n].lo = lo & 0x0CFFFFFF; r[*n].hi = hi & 0x0CFFFFFF; r[*n].d = d; (*n)++;
    }
    fclose(f);
    fprintf(stderr, "%s %d ranges\n", what, *n);
}
/* IC remap: map old code line (32 B) to new line address */
static u32 *icmap;     /* indexed by (pc & 0xFFFFFF) >> 5 : new physical line address or 0 */
static u8 *pinned;     /* OC-RAM what-if: per 32 B line of RAM, 1 = lives in OC RAM (always hits) */
typedef struct { u32 miss, pc; double stall; } LineStat;
static LineStat *lst;  /* per 32 B RAM line: demand misses, stall cycles, first missing PC */

/* ---------------- caches ---------------- */
typedef struct { u32 tag; u8 valid, dirty, words, crit, pf; u32 owner_pc; double ready, first; } OLine;
static OLine oc[512];
static u32 ic_tag[256]; static u8 ic_valid[256];
static u32 evict_tag[512], evict_pc[512];
static double bus_free;
/* DMA from system RAM (hwtrace events 11/12): bursts of 32 B that compete with the CPU for the
   SH-4 external bus. A DMA channel issues one burst per dma_ival cycles (its device rate) whenever
   the bus is free; a CPU request that finds a DMA burst in progress waits for it (round robin). */
static double DMA_BURST = 14;               /* 32 B burst on SDRAM, row hit (7 bus clocks) */
static int NO_DMA = 0;
static double dma_left, dma_next, dma_ival = 14, dma_cyc;
static u64 dma_bytes_tot, dma_n;
static double bus_start(double t)
{
    double s = bus_free > t ? bus_free : t;
    while (dma_left > 0) {
        double bs = dma_next > bus_free ? dma_next : bus_free;
        if (bs > s) break;
        bus_free = bs + DMA_BURST; dma_left -= 32; dma_next = bs + dma_ival; dma_cyc += DMA_BURST;
        s = bus_free > t ? bus_free : t;
        if (bs >= t) break;                   /* the CPU was already waiting: it gets the next slot */
    }
    return s;
}
static void dma_start(double t, u32 kind, u32 len)
{
    /* device rates (Sega SH4_access990312), CPU cycles per 32 B: ch2 TA/texture path ~ bus bound,
       PVR-DMA 64.3 MB/s, G2/AICA 11.3 MB/s, GD-ROM 14.4 MB/s */
    static const double ival[8] = { 14, 14, 14, 100, 566, 444, 14, 14 };
    if (NO_DMA || len == 0) return;
    if (dma_left <= 0) dma_next = t;
    dma_left += len; dma_bytes_tot += len; dma_n++;
    dma_ival = ival[kind & 7] > DMA_BURST ? ival[kind & 7] : DMA_BURST;
}
static u32 open_row[4];
static double sq_busy[2];
static u32 dma_kind_pending;

static u32 oc_index(u32 a)
{
    /* ORA: entries 128-255 and 384-511 are RAM; the cache keeps entries 0-127 and 256-383 */
    if (OC_KB == 8) return ((a >> 5) & 0x7F) | ((OIX ? ((a >> 25) & 1) : ((a >> 13) & 1)) << 8);
    return OIX ? ((((a >> 5) & 0xFF) | (((a >> 25) & 1) << 8))) : ((a >> 5) & 0x1FF);
}
/* line fill: returns the full-line time; *first = time to the critical (requested) longword.
   SH-4 fills wrap around from the requested longword and restart the CPU when it arrives
   (Software Manual 4.3.2 / 4.4.2); the rest of the burst (BURST_TAIL) completes in the background. */
static double BURST_TAIL = 6;
static double fill_cost2(u32 phys, double *first)
{
    u32 bank = (phys >> 11) & 3, row = phys >> 13;
    double c = (open_row[bank] == row) ? FILL_HIT : FILL_MISS;
    open_row[bank] = row;
    if (first) *first = c + FILL_OVH - BURST_TAIL;
    return c + FILL_OVH;
}
static double fill_cost(u32 phys) { return fill_cost2(phys, NULL); }
/* arrival time of the 8-byte beat holding phys in a line being filled */
static double beat_time(const OLine *l, u32 phys)
{
    double w = l->first + 2.0 * ((((phys >> 3) & 3) - l->crit) & 3);
    return w < l->ready ? w : l->ready;
}
static double wb_cost(u32 phys)
{
    u32 bank = (phys >> 11) & 3, row = phys >> 13;
    double c = (open_row[bank] == row) ? WB_HIT : WB_MISS;
    open_row[bank] = row;
    return c + WB_EXTRA;
}
/* uncached access costs in CPU cycles (Sega SH4_access990312: bus clocks x2) */
static double uncached_read(u32 a, int size)
{
    u32 p = a & 0x1FFFFFFF;
    if ((a >> 24) >= 0xF0) return 4;      /* P4: cache/TLB arrays and on-chip registers */
    if (p >= 0x0C000000 && p < 0x10000000) return fill_cost(p);
    if (p >= 0x04000000 && p < 0x08000000) return (size == 32 ? 61 : 41) * 2;
    if (p >= 0x005F6800 && p < 0x005F6A00) return 5 * 2;
    if (p >= 0x005F6C00 && p < 0x005F6D00) return 22 * 2;
    if (p >= 0x005F7400 && p < 0x005F7500) return 24 * 2;
    if (p >= 0x005F7800 && p < 0x005F7900) return 38 * 2;
    if (p >= 0x005F7C00 && p < 0x005F7D00) return 24 * 2;
    if (p >= 0x005F8000 && p < 0x005FA000) return 34 * 2;
    if (p >= 0x00700000 && p < 0x01000000) return 40 * 2;
    if (p >= 0x005F7000 && p < 0x005F7100) return 39 * 2;
    if (p < 0x00200000) return 99 * 2;
    return 60 * 2;
}
static double uncached_write(u32 a, int size)
{
    u32 p = a & 0x1FFFFFFF;
    if ((a >> 24) >= 0xF0) return 2;
    if (p >= 0x0C000000 && p < 0x10000000) return 9 * 2;
    if (p >= 0x04000000 && p < 0x08000000) return (size == 32 ? 38 : 12) * 2;
    if (p >= 0x10000000 && p < 0x14000000) return 7 * 2;
    if (p >= 0x005F6800 && p < 0x005F6A00) return 5 * 2;
    if (p >= 0x005F8000 && p < 0x005FA000) return 14 * 2;
    if (p >= 0x00700000 && p < 0x01000000) return 12 * 2;
    return 12 * 2;
}

/* ---------------- pipeline state ---------------- */
static double rready[64];
static u8 rprod[64];          /* producer class for the dependency category */
enum { P_NONE, P_LOAD, P_FPU, P_FDIV, P_OTHER };
static double f0_free, f3_free, f1_free;
static double t_prev = 0;     /* issue time of the previous instruction */
static int prev_grp = G_CO, prev_paired = 1, prev_issue = 1;
static u64 prev_def = 0;
static double floor_t = 0;    /* earliest issue of the next instruction (freeze / branch / issue rate) */
static int floor_cat = C_BASE; static u32 floor_pc = 0; /* who caused the floor */
static int sz_mode = 0;
static u32 cur_iline = 0xFFFFFFFF;
static double fetch_ready = 0, ic_first = 0, ic_full = 0; static u32 ic_crit = 0, ic_line = 0xFFFFFFFF;
/* flycast dynarec charge */
static int fly_last = G_CO, fly_memops = 0, fly_block_end = 0, fly_after_slot = 0;
static double br_t = -1; static u32 br_kind = 0; static u32 br_pc = 0;
/* stream detector per PC (small hash) */
typedef struct { u32 pc, last_line; s32 stride; } Strm;
static Strm strm[65536];

/* totals */
static double tot_cycles, frame_cycles;
static u64 tot_insn, tot_sleep;

static int bitidx(u64 m) { return __builtin_ctzll(m); }

/* Memory stalls found while processing an instruction's accesses are not charged directly: they are
   collected in acc[] and become the freeze floor of the next issue; the delay the next instruction
   actually sees is then split over these categories and charged to the missing instruction. */
static int acc_mode; static double acc[16];
/* ---- bench part attribution (--phase) ---- */
#define NPH 6
static int PH_ON = 0, PH_START = 0, cur_ph = 0, ph_sp = 0, ph_stk[64];
static u32 ph_e_phase, ph_e_push, ph_e_iter; static signed char *ph_site;
static double ph_t0, fph_cyc[NPH], fph_cat[NPH][C_NCAT]; static u64 ph_if0, ph_df0, fph_if[NPH], fph_df[NPH];
static u64 ph_unknown, ph_marks;
/* --ticks ADDR: stores into proc_tick[32] (debug.cpp) stamped with the modelled cycle (frame-relative) */
static u32 TK_LO, TK_HI, TK_ZERO; static double tk_t0, tk_first[33], tk_last[33]; static int tk_n[33];
static void charge(PcStat *s, int cat, double c)
{
    if (c <= 0) return;
    if (PH_ON && !acc_mode) fph_cat[cur_ph][cat] += c;
    if (acc_mode) { acc[cat] += c; return; }
    s->cyc[cat] += (u64)llround(c * 16.0);   /* 1/16 cycle fixed point */
}
#define C_MEMMIX 99
static double fl_comp[16];

/* ---------------- data access ---------------- */
static double sq_store(double t, u32 a, PcStat *s)
{
    int q = (a >> 5) & 1;
    if (sq_busy[q] > t) { double w = sq_busy[q] - t; charge(s, C_SQ, w); return w; }
    return 0;
}

static void writeback_line(u32 idx, double t)
{
    OLine *l = &oc[idx];
    if (l->valid && l->dirty) {
        u32 phys = (l->tag << 10) | ((idx & 0x1FF) << 5);
        double start = bus_start(t);
        bus_free = start + wb_cost(phys & 0x1FFFFFFF);
        l->dirty = 0;
    }
}

/* Per-PC stream tracker, run on every cached access before the cache lookup. A PC is streaming when
   two consecutive line changes have the same stride (|stride| <= 256 B). With --streampf the model
   issues the software prefetch a pref-in-loop would: line + stride, when the stream enters a new line. */
static int q_stream_hit;
static void stream_track(double t, u32 a, u32 pc, int type)
{
    u32 lineaddr = (a & 0x1FFFFFFF) & ~31u;
    Strm *q = &strm[(pc >> 1) & 0xFFFF];
    q_stream_hit = 0;
    if (q->pc != pc) { q->pc = pc; q->last_line = lineaddr; q->stride = 0; return; }
    if (lineaddr == q->last_line) { q_stream_hit = q->stride != 0; return; }
    s32 stride = (s32)lineaddr - (s32)q->last_line;
    int streaming = stride == q->stride && abs(stride) <= 256;
    q->stride = abs(stride) <= 256 ? stride : 0; q->last_line = lineaddr;
    q_stream_hit = streaming;
    if (STREAMPF && streaming && type == 2) {   /* software prefetch is for read streams */
        u32 na = lineaddr + stride;
        u32 nidx = oc_index(na | (a & 0xE0000000));
        OLine *nl = &oc[nidx];
        if (!(nl->valid && nl->tag == (na >> 10)) && !(pinned && pinned[(na & 0xFFFFFF) >> 5])) {
            if (nl->valid && nl->dirty) { double s3 = bus_start(t); bus_free = s3 + wb_cost((nl->tag << 10) | ((nidx & 0x1FF) << 5)); }
            double st4 = bus_start(t);
            double fw;
            nl->valid = 1; nl->tag = na >> 10; nl->dirty = 0; nl->words = 0; nl->owner_pc = pc; nl->pf = 1; nl->crit = 0;
            nl->ready = st4 + fill_cost2(na, &fw) + DMISS_LAT; nl->first = st4 + fw + DMISS_LAT; bus_free = nl->ready - DMISS_LAT;
            PS(pc)->pf++;
        }
    }
}

/* returns stall cycles (freeze) for a cached access; type 2 read, 3 write, 8 movca, 4 pref */
static double oc_access(double t, u32 a, int type, u32 pc, PcStat *s, int size)
{
    u32 phys = a & 0x1FFFFFFF;
    u32 lineaddr = phys & ~31u;
    if (pinned && pinned[(phys & 0xFFFFFF) >> 5]) return 0;
    u32 idx = oc_index(a);
    OLine *l = &oc[idx];
    u32 tag = phys >> 10;
    int wordbit = 1 << ((phys >> 2) & 7);
    if (l->valid && l->tag == tag) {
        double st = 0;
        if (l->ready > t) {
            double w = beat_time(l, phys);
            if (w > t && type != 3 && type != 8) {       /* reads wait for their beat; writes merge */
                st = w - t;
                if (l->pf) { charge(s, C_PFWAIT, st); s->pfuse++; } else charge(s, C_DMISS, st);
            }
        }
        if (type == 3 || type == 8) l->dirty = 1;
        l->words |= wordbit;
        if (size == 8) l->words |= wordbit << 1;
        return st;
    }
    if (NO_DCACHE_MISS && type != 4) {  /* perfect D-cache what-if */
        l->valid = 1; l->tag = tag; l->dirty = (type == 3 || type == 8); l->ready = 0; l->pf = 0; l->words = wordbit; l->owner_pc = pc;
        return 0;
    }
    /* miss: victim handling */
    int induced = (evict_tag[idx] == tag && evict_pc[idx] != 0);
    u32 evictor = evict_pc[idx];
    if (l->valid) {
        PcStat *o = PS(l->owner_pc);
        o->words_used += __builtin_popcount(l->words);
        o->fills_owned++;
        evict_tag[idx] = l->tag; evict_pc[idx] = pc;
    }
    double wb_start = t;
    int had_dirty = l->valid && l->dirty;
    u32 vphys = (l->tag << 10) | ((idx & 0x1FF) << 5);
    l->valid = 1; l->tag = tag; l->dirty = 0; l->words = wordbit | (size == 8 ? wordbit << 1 : 0); l->owner_pc = pc;
    double stall = 0;
    if (type == 3 && (WA_NOFILL || (WA_STREAM && q_stream_hit))) type = 8;
    if (type == 8) {                     /* movca: allocate, no fill */
        l->dirty = 1; l->ready = 0; l->pf = 0;
        if (had_dirty) { double st2 = bus_start(t); bus_free = st2 + wb_cost(vphys); n_wb++; }
        return 0;
    }
    double start = bus_start(t);
    double fw;
    double fc = fill_cost2(lineaddr, &fw);
    double arrive = start + fc;
    bus_free = arrive; n_fill++;
    if (had_dirty) { bus_free = arrive + wb_cost(vphys); n_wb++; (void)wb_start; }
    if (induced) { PS(evictor)->induced++; }
    l->ready = arrive + DMISS_LAT; l->first = start + fw + DMISS_LAT; l->crit = (phys >> 3) & 3; l->pf = (type == 4);
    if (type == 4) { s->pf++; return 0; }   /* prefetch: non-blocking */
    if (type == 3) {
        /* copy-back write miss: the store goes into the line at once and the fill runs in the
           background (4.3.3 3c/3e); the CPU only waits for the bus to accept the fill */
        l->dirty = 1; s->dwmiss++;
        stall = start - t + WMISS_LAT;   /* WMISS_LAT: console-fitted extra for a store that misses */
    } else {
        s->drmiss++;
        stall = l->first - t;
    }
    charge(s, C_DMISS, stall);
    { LineStat *L = &lst[(phys & 0xFFFFFF) >> 5]; if (!L->miss) L->pc = pc; L->miss++; L->stall += stall; }
    if (q_stream_hit) s->stream_miss++;
    return stall;
}

static void oc_op(u32 a, int type, double t)
{
    u32 phys = a & 0x1FFFFFFF, idx = oc_index(a);
    OLine *l = &oc[idx];
    if (!(l->valid && l->tag == (phys >> 10))) return;
    if (type == 6 || type == 7) writeback_line(idx, t);
    if (type == 5 || type == 6) l->valid = 0;
    if (type == 5) l->dirty = 0;
}

static int cached_area(u32 a)
{
    u32 area = a >> 29;
    if (area == 5 || area == 7) return 0;                         /* P2, P4 */
    u32 p = a & 0x1FFFFFFF;
    return p >= 0x0C000000 && p < 0x10000000;                     /* only system RAM is cacheable here */
}

/* ---------------- main instruction step ---------------- */
typedef struct { u32 addr, type, size, size_code; } Ev;

static void step(u32 pc, const Ev *ev, int nev, int taken_next, u32 next_pc)
{
    PcStat *s = PS(pc);
    u16 op = ram_valid(pc) ? code_at(pc) : 0x0009;
    Dec dd = dtab[op];
    Dec *d = &dd;
    if (FDIV_LAT_OVR >= 0 && (d->kind & K_FDIV) && rl_has(&fdiv_ranges, pc)) d->lat = (u8)FDIV_LAT_OVR;
    s->exec++; tot_insn++;
    if (op == 0x001B) tot_sleep++;
    if (d->kind & K_FDIV) s->fdiv++;
    /* SZ handling: fmov with SZ=1 moves pairs */
    if (sz_mode && (op >> 12) == 0xF && ((op & 15) >= 6 && (op & 15) <= 0xC)) {
        for (int b = 16; b < 32; b++) {
            if (d->def >> b & 1) d->def |= 1ull << (16 + ((b - 16) ^ 1));
            if (d->use >> b & 1) d->use |= 1ull << (16 + ((b - 16) ^ 1));
        }
    }
    if (op == 0xF3FD) sz_mode ^= 1;
    else if (d->kind & K_FSCHG && op != 0xFBFD) sz_mode = 0;

    /* ---- Flycast dynarec charge (Sh4Cycles::countCycles, non-STRICT; reset per dynarec block) ---- */
    {
        if (fly_block_end) { fly_last = G_CO; fly_memops = 0; fly_block_end = 0; }
        int unit = d->grp;
        int c = 0;
        if ((d->kind & (K_LOAD | K_STORE)) || ((op & 0xF0FF) == 0x0083)) { if (++fly_memops < 4) c = 2; }
        if (fly_last == G_CO || unit == G_CO || (fly_last == unit && fly_last != G_MT)) { fly_last = unit; c += d->issue; }
        else fly_last = G_CO;
        s->fly += c;
        if (fly_after_slot) { fly_block_end = 1; fly_after_slot = 0; }
        if (d->kind & K_BRC) fly_block_end = 1;
        else if (d->kind & (K_BRCD | K_BRU | K_BRREG)) fly_after_slot = 1;
    }

    /* ---- instruction fetch ---- */
    u32 fpc = ncmap ? cmap_pc(pc) : pc;
    u32 iline = (fpc & 0x1FFFFFFF) >> 5;
    double tf = 0; int icat = C_IMISS;
    if (iline != cur_iline) {
        cur_iline = iline;
        u32 a = fpc;
        if (icmap && ram_valid(pc) && icmap[(pc & 0xFFFFFF) >> 5]) a = icmap[(pc & 0xFFFFFF) >> 5] | 0x80000000u;
        if ((pc >> 29) == 5) {        /* P2: uncached fetch */
            double start = bus_start(t_prev);
            fetch_ready = start + 12 * 2; bus_free = fetch_ready; s->uncached++;
            icat = C_UNCACHED;
        } else {
            u32 idx = IIX ? ((((a >> 5) & 0x7F) | (((a >> 25) & 1) << 7))) : ((a >> 5) & 0xFF);
            u32 tag = (a & 0x1FFFFFFF) >> 10;
            if (!(ic_valid[idx] && ic_tag[idx] == tag)) {
                ic_valid[idx] = 1; ic_tag[idx] = tag;
                if (!NO_ICACHE_MISS) {
                    double start = bus_start(t_prev);
                    double fw;
                    double full = start + fill_cost2(a & 0x1FFFFFFF, &fw) + ICFILL_EXTRA;
                    bus_free = full; n_ifill++;
                    ic_first = start + fw + ICFILL_EXTRA + IMISS_LAT; ic_full = full + IMISS_LAT; ic_crit = (fpc >> 3) & 3; ic_line = iline;
                    fetch_ready = ic_first;
                    s->imiss++;
                }
            }
        }
    }
    tf = fetch_ready;
    if (iline == ic_line && ic_full > t_prev) {           /* later beats of a line still being filled */
        double w = ic_first + 2.0 * ((((fpc >> 3) & 3) - ic_crit) & 3);
        if (w > ic_full) w = ic_full;
        if (w > tf) tf = w;
    }

    /* ---- issue time ---- */
    double base = prev_paired ? t_prev + prev_issue : t_prev + prev_issue;   /* next slot after previous */
    /* dual issue: pair with the previous instruction if allowed */
    int can_pair = !prev_paired && prev_grp != G_CO && d->grp != G_CO && (d->grp != prev_grp || d->grp == G_MT)
                   && !(d->def & prev_def);
    double dep = 0; int dcat = C_DEP_OTHER;
    u64 u = d->use;
    while (u) { int b = bitidx(u); u &= u - 1; if (rready[b] > dep) { dep = rready[b]; int p = rprod[b];
        dcat = p == P_LOAD ? C_DEP_LOAD : p == P_FPU ? C_DEP_FPU : p == P_FDIV ? C_DEP_FDIV : C_DEP_OTHER; } }
    if (NO_DEP) dep = 0;
    double lockt = 0;
    if (d->kind & (K_FDIV | K_FSQRT)) lockt = f3_free;
    if (d->kind & (K_FTRV | K_FIPR)) lockt = lockt > f0_free ? lockt : f0_free;
    if (d->kind & K_MUL) lockt = lockt > f1_free ? lockt : f1_free;
    double t;
    if (can_pair && dep <= t_prev && lockt <= t_prev && tf <= t_prev && floor_t <= t_prev) {
        t = t_prev;
        prev_paired = 1;
        charge(s, C_BASE, 0);
    } else {
        t = base;
        int cat = C_BASE; PcStat *cs = s;
        double b0 = base;
        if (floor_t > t) { t = floor_t; cat = floor_cat; cs = PS(floor_pc); }
        if (dep > t) { t = dep; cat = dcat; cs = s; }
        if (lockt > t) { t = lockt; cat = C_FLOCK; cs = s; }
        if (tf > t) { t = tf; cat = icat; cs = s; }
        charge(s, C_BASE, b0 - t_prev);
        if (cat == C_MEMMIX) {
            double tot = 0; for (int c = 0; c < C_NCAT; c++) tot += fl_comp[c];
            for (int c = 0; c < C_NCAT; c++) if (fl_comp[c] > 0) charge(cs, c, (t - b0) * fl_comp[c] / tot);
        } else charge(cs, cat, t - b0);
        prev_paired = 0;
    }
    floor_t = 0; floor_cat = C_BASE;
    /* results */
    int pcls = (d->kind & K_LOAD) ? P_LOAD : (d->kind & (K_FDIV | K_FSQRT)) ? P_FDIV : (d->grp == G_FE) ? P_FPU : P_OTHER;
    double lat = d->lat;
    /* memory events */
    double stall = 0;
    acc_mode = 1; memset(acc, 0, sizeof(acc));
    for (int i = 0; i < nev; i++) {
        const Ev *e = &ev[i];
        u32 a = e->addr;
        if (e->type == 9) {             /* SQ flush */
            int q = (a >> 5) & 1;
            double start = bus_start(t);
            if (sq_busy[q] > start) start = sq_busy[q];
            sq_busy[q] = start + SQ_COST; bus_free = sq_busy[q]; s->sqf++;
            continue;
        }
        if (e->type == 10) continue;
        if (e->type == 11) { dma_kind_pending = e->size_code; continue; }
        if (e->type == 12) { dma_start(t, dma_kind_pending, a); continue; }
        if (e->type >= 5 && e->type <= 7) { oc_op(a, e->type, t + stall); continue; }
        if ((a >> 26) == 0x38) {        /* store queue area */
            if (e->type == 3) stall += sq_store(t + stall, a, s);
            continue;
        }
        if (TK_HI && e->type == 3 && (((a & 0x1FFFFFFFu) >= TK_LO && (a & 0x1FFFFFFFu) < TK_HI) || (a & 0x1FFFFFFFu) == TK_ZERO)) {
            int k = (a & 0x1FFFFFFFu) == TK_ZERO ? 32 : (int)(((a & 0x1FFFFFFFu) - TK_LO) >> 2);
            double st = t + stall - tk_t0;
            if (!tk_n[k]) tk_first[k] = st;
            tk_last[k] = st; tk_n[k]++;
        }
        if (e->type == 2) s->reads++; else if (e->type == 3 || e->type == 8) s->writes++;
        if (cached_area(a)) {
            if (e->type != 4) stream_track(t + stall, a, pc, e->type); else q_stream_hit = 0;
            stall += oc_access(t + stall, a, e->type, pc, s, e->size);
        } else if (e->type != 4) {
            double c;
            if (e->type == 2) { c = uncached_read(a, e->size); double start = bus_start(t + stall);
                double w = start + c - (t + stall); bus_free = start + c; stall += w; charge(s, C_UNCACHED, w); }
            else { c = uncached_write(a, e->size); double start = bus_start(t + stall);
                double w = start - (t + stall); if (w > 0) { stall += w; charge(s, C_UNCACHED, w); } bus_free = start + c; }
            s->uncached++;
        }
    }
    /* write register results */
    u64 df = d->def;
    while (df) { int b = bitidx(df); df &= df - 1; rready[b] = t + stall + lat; rprod[b] = pcls; }
    u64 d2 = d->def2;
    while (d2) { int b = bitidx(d2); d2 &= d2 - 1; if (!(d->def >> b & 1)) { rready[b] = t + d->lat2; rprod[b] = P_OTHER; } }
    if (d->kind & (K_FDIV | K_FSQRT)) {
        int lk = (d->kind & K_FDIV) ? 10 : 9;
        if (FDIV_LOCK_OVR >= 0 && (d->kind & K_FDIV) && rl_has(&fdiv_ranges, pc)) lk = FDIV_LOCK_OVR;
        f3_free = t + 1 + lk;
    }
    if (d->kind & K_FTRV) f0_free = t + 4;
    if (d->kind & K_FIPR) f0_free = t + 1;
    if (d->kind & K_MUL) f1_free = t + 2;
    acc_mode = 0;
    if (stall > 0) { floor_t = t + stall; floor_cat = C_MEMMIX; floor_pc = pc; memcpy(fl_comp, acc, sizeof(fl_comp)); }
    /* branch redirect: delayed branches redirect from the branch's issue, BT/BF from their own */
    if (taken_next) {
        double r;
        if (d->kind & K_BRC) r = t + 2;
        else if (d->kind & K_RTE) r = t + d->issue;
        else if (br_pc == pc - 2 && br_t >= 0) { r = br_t + ((br_kind & (K_BRREG)) ? 3 : 2); if (r < t + 1) r = t + 1; }
        else r = t + 3;                  /* exception / interrupt entry or re-executed SLEEP */
        if (r > floor_t) { floor_t = r; floor_cat = C_BRANCH; floor_pc = (br_pc == pc - 2) ? br_pc : pc; }
    }
    if (d->kind & (K_BRCD | K_BRU | K_BRREG)) { br_t = t; br_kind = d->kind; br_pc = pc; }
    t_prev = t;
    prev_issue = d->issue;
    prev_grp = d->grp;
    prev_def = d->def;
    if (d->grp == G_CO) prev_paired = 1;   /* CO never pairs with the next */
}

/* ---------------- trace driver ---------------- */
static void ph_switch(int np)
{
    fph_cyc[cur_ph] += t_prev - ph_t0; ph_t0 = t_prev;
    fph_if[cur_ph] += n_ifill - ph_if0; ph_if0 = n_ifill;
    fph_df[cur_ph] += n_fill - ph_df0; ph_df0 = n_fill;
    if (np >= 0 && np < NPH) cur_ph = np;
}
static void ph_enter(u32 a, u32 prun_pc, u32 prun_n)
{
    if (a == ph_e_push) { if (ph_sp < 64) ph_stk[ph_sp++] = cur_ph; ph_switch(2); ph_marks++; return; }
    if (a == ph_e_iter) { ph_switch(4); ph_marks++; return; }
    if (a != ph_e_phase) return;
    int v = 127;
    if (prun_n >= 2) { u32 c = prun_pc + 2 * (prun_n - 2); if (ram_valid(c)) v = ph_site[(c & 0xFFFFFF) >> 1]; }
    if (v == 127 && prun_n >= 1) { u32 c = prun_pc + 2 * (prun_n - 1); if (ram_valid(c)) v = ph_site[(c & 0xFFFFFF) >> 1]; }
    if (v == 126) return;                       /* internal call (push / iter): already handled */
    if (v == -1) { ph_switch(ph_sp > 0 ? ph_stk[--ph_sp] : 4); ph_marks++; return; }
    if (v >= 0 && v < NPH) { ph_switch(v); ph_marks++; return; }
    ph_unknown++;
}
static void run_trace(const char *path)
{
    FILE *f = fopen(path, "rb"); if (!f) { perror(path); exit(1); }
    size_t cap = 1 << 22; u32 *w = malloc(cap * 8);
    Ev *pend = malloc(sizeof(Ev) * (1 << 20)); u32 *pendpc = malloc(4 * (1 << 20)); int npend = 0;
    double t0 = t_prev;
    tk_t0 = t0; memset(tk_n, 0, sizeof(tk_n));
    if (PH_ON) { cur_ph = PH_START; ph_sp = 0; ph_t0 = t_prev; ph_if0 = n_ifill; ph_df0 = n_fill;
                 memset(fph_cyc, 0, sizeof(fph_cyc)); memset(fph_cat, 0, sizeof(fph_cat));
                 memset(fph_if, 0, sizeof(fph_if)); memset(fph_df, 0, sizeof(fph_df)); }
    /* delayed-run processing: we need the next run start to know branch targets */
    u32 prun_pc = 0, prun_n = 0; int have_prev = 0;
    Ev *prun_ev = malloc(sizeof(Ev) * (1 << 20)); u32 *prun_evpc = malloc(4 * (1 << 20)); int prun_nev = 0;
    size_t got;
    #define FLUSH_RUN(next_start) do { if (have_prev) { \
        int ei = 0; \
        for (u32 k = 0; k < prun_n; k++) { \
            u32 pc = prun_pc + 2 * k; \
            int e0 = ei; \
            while (ei < prun_nev && prun_evpc[ei] == ((pc >> 1) & 0xFFFFFF)) ei++; \
            int last = (k == prun_n - 1); \
            if (skip_ranges.n && rl_has(&skip_ranges, pc)) continue; \
            step(pc, prun_ev + e0, ei - e0, last && (next_start) != pc + 2, (next_start)); \
        } } } while (0)
    while ((got = fread(w, 8, cap, f)) > 0) {
        for (size_t i = 0; i < got; i++) {
            u32 a = w[2 * i], b = w[2 * i + 1];
            u32 type = b >> 28;
            if (type == 1) {
                FLUSH_RUN(a);
                if (PH_ON && have_prev) ph_enter(a, prun_pc, prun_n);
                prun_pc = a; prun_n = b & 0x0FFFFFFF; have_prev = 1;
                memcpy(prun_ev, pend, sizeof(Ev) * npend); memcpy(prun_evpc, pendpc, 4 * npend); prun_nev = npend;
                npend = 0;
            } else {
                if (npend < (1 << 20)) {
                    pend[npend].addr = ndmap ? dmap_addr(a) : a; pend[npend].type = type; pend[npend].size = 1 << ((b >> 24) & 3);
                    pend[npend].size_code = (b >> 24) & 15;
                    if (type >= 4 && type <= 7) pend[npend].size = 32;
                    pendpc[npend] = b & 0xFFFFFF; npend++;
                }
            }
        }
    }
    FLUSH_RUN(0xFFFFFFFF);
    if (PH_ON) ph_switch(-1);
    fclose(f);
    frame_cycles = t_prev - t0;
    tot_cycles += frame_cycles;
    free(w); free(pend); free(pendpc); free(prun_ev); free(prun_evpc);
}

static void usage(void)
{
    fprintf(stderr, "hwsim --elf ELF [--out P] [--oc-kb 16|8] [--oix] [--fill-hit C --fill-miss C --fill-ovh C] "
            "[--wb-hit C --wb-miss C] [--dmiss-lat C --imiss-lat C --wb-extra C | --console-fit | --console-fit-w70] [--sq-cost C] [--streampf] [--pin FILE] [--icmap FILE] [--dmap FILE] [--cmap FILE] [--skip FILE] "
            "[--fdiv FILE --fdiv-lat N --fdiv-lock N] [--perfect-ic] [--perfect-dc] [--no-dma] [--dma-burst C] [--burst-tail C] [--wa-stream] [--wa-nofill] [--no-dep] trace...\n");
    exit(2);
}

int main(int argc, char **argv)
{
    const char *elf = NULL; const char *pinf = NULL, *icf = NULL, *phf = NULL;
    int ntr = 0; const char *tr[4096];
    for (int i = 1; i < argc; i++) {
        const char *a = argv[i];
        #define ARG (i + 1 < argc ? argv[++i] : (usage(), ""))
        if (!strcmp(a, "--elf")) elf = ARG;
        else if (!strcmp(a, "--out")) OUT = ARG;
        else if (!strcmp(a, "--oc-kb")) OC_KB = atoi(ARG);
        else if (!strcmp(a, "--oix")) OIX = 1;
        else if (!strcmp(a, "--fill-hit")) FILL_HIT = atof(ARG);
        else if (!strcmp(a, "--fill-miss")) FILL_MISS = atof(ARG);
        else if (!strcmp(a, "--fill-ovh")) FILL_OVH = atof(ARG);
        else if (!strcmp(a, "--burst-tail")) BURST_TAIL = atof(ARG);
        else if (!strcmp(a, "--wb-hit")) WB_HIT = atof(ARG);
        else if (!strcmp(a, "--wb-miss")) WB_MISS = atof(ARG);
        else if (!strcmp(a, "--sq-cost")) SQ_COST = atof(ARG);
        else if (!strcmp(a, "--dmiss-lat")) DMISS_LAT = atof(ARG);
        else if (!strcmp(a, "--imiss-lat")) IMISS_LAT = atof(ARG);
        else if (!strcmp(a, "--wb-extra")) WB_EXTRA = atof(ARG);
        else if (!strcmp(a, "--wmiss-lat")) WMISS_LAT = atof(ARG);
        else if (!strcmp(a, "--console-fit")) { DMISS_LAT = CF_D; IMISS_LAT = CF_I; WMISS_LAT = CF_W; }
        else if (!strcmp(a, "--console-fit-w70")) { DMISS_LAT = CF70_D; IMISS_LAT = CF70_I; WMISS_LAT = CF70_W; }
        else if (!strcmp(a, "--streampf")) STREAMPF = 1;
        else if (!strcmp(a, "--pin")) pinf = ARG;
        else if (!strcmp(a, "--icmap")) icf = ARG;
        else if (!strcmp(a, "--dmap")) load_ranges(ARG, dmap, &ndmap, "dmap");
        else if (!strcmp(a, "--cmap")) load_ranges(ARG, cmap, &ncmap, "cmap");
        else if (!strcmp(a, "--skip")) rl_load(&skip_ranges, ARG);
        else if (!strcmp(a, "--fdiv")) rl_load(&fdiv_ranges, ARG);
        else if (!strcmp(a, "--fdiv-lat")) FDIV_LAT_OVR = atof(ARG);
        else if (!strcmp(a, "--fdiv-lock")) FDIV_LOCK_OVR = atoi(ARG);
        else if (!strcmp(a, "--perfect-ic")) NO_ICACHE_MISS = 1;
        else if (!strcmp(a, "--perfect-dc")) NO_DCACHE_MISS = 1;
        else if (!strcmp(a, "--no-dma")) NO_DMA = 1;
        else if (!strcmp(a, "--dma-burst")) DMA_BURST = atof(ARG);
        else if (!strcmp(a, "--wa-stream")) WA_STREAM = 1;
        else if (!strcmp(a, "--no-dep")) NO_DEP = 1;
        else if (!strcmp(a, "--wa-nofill")) WA_NOFILL = 1;
        else if (!strcmp(a, "--phase")) phf = ARG;
        else if (!strcmp(a, "--phase-start")) PH_START = atoi(ARG);
        else if (!strcmp(a, "--tick-zero")) TK_ZERO = (u32)strtoul(ARG, NULL, 16) & 0x1FFFFFFFu;
        else if (!strcmp(a, "--ticks")) { TK_LO = (u32)strtoul(ARG, NULL, 16) & 0x1FFFFFFFu; TK_HI = TK_LO + 128; }
        else if (a[0] == '-') usage();
        else tr[ntr++] = a;
    }
    if (!elf || !ntr) usage();
    ram = calloc(RAM_SIZE + 16, 1);
    load_elf(elf);
    decode_all();
    ps = calloc(NPC, sizeof(PcStat));
    lst = calloc(RAM_SIZE / 32, sizeof(LineStat));
    if (!ps) { fprintf(stderr, "oom\n"); return 1; }
    if (pinf) {
        pinned = calloc(RAM_SIZE / 32, 1);
        FILE *f = fopen(pinf, "r"); u32 a; int n = 0;
        while (f && fscanf(f, "%x", &a) == 1) { pinned[(a & 0xFFFFFF) >> 5] = 1; n++; }
        if (f) fclose(f);
        fprintf(stderr, "pinned %d lines (%d bytes)\n", n, n * 32);
    }
    if (icf) {
        icmap = calloc(RAM_SIZE / 32, 4);
        FILE *f = fopen(icf, "r"); u32 a, b; int n = 0;
        while (f && fscanf(f, "%x %x", &a, &b) == 2) { icmap[(a & 0xFFFFFF) >> 5] = b & 0x1FFFFFE0; n++; }
        if (f) fclose(f);
        fprintf(stderr, "icmap %d lines\n", n);
    }
    FILE *pf = NULL;
    if (phf) {
        ph_site = malloc(NPC); memset(ph_site, 127, NPC);
        FILE *f = fopen(phf, "r"); char kw[16], val[16], fn[512]; u32 a; int n = 0;
        char line[1024];
        while (f && fgets(line, sizeof(line), f)) {
            if (sscanf(line, "%15s %x %15s %511s", kw, &a, val, fn) < 3) continue;
            if (!strcmp(kw, "entry")) {
                if (!strcmp(val, "phase")) ph_e_phase = a; else if (!strcmp(val, "push")) ph_e_push = a; else if (!strcmp(val, "iter")) ph_e_iter = a;
            } else if (!strcmp(kw, "site") && ram_valid(a)) {
                ph_site[(a & 0xFFFFFF) >> 1] = !strcmp(val, "pop") ? -1 : (signed char)atoi(val); n++;
            }
        }
        if (f) fclose(f);
        /* calls from inside push / iter themselves: mark every halfword of those functions as internal */
        for (u32 x = ph_e_push; x < ph_e_push + 0x24; x += 2) ph_site[(x & 0xFFFFFF) >> 1] = 126;
        for (u32 x = ph_e_iter; x < ph_e_iter + 0x640; x += 2) ph_site[(x & 0xFFFFFF) >> 1] = 126;
        PH_ON = 1;
        fprintf(stderr, "phase table: %d sites, entries %08x %08x %08x\n", n, ph_e_phase, ph_e_push, ph_e_iter);
    }
    char path[1024];
    if (PH_ON) {
        snprintf(path, sizeof(path), "%s.phases.tsv", OUT); pf = fopen(path, "w");
        fprintf(pf, "trace\tcycles");
        for (int p = 0; p < NPH; p++) fprintf(pf, "\tcyc%d\timiss%d\tdmiss%d\tpfwait%d\tsq%d\tunc%d\tifill%d\tdfill%d", p, p, p, p, p, p, p, p);
        fprintf(pf, "\tunknown\tmarks\n");
    }
    FILE *tkf = NULL;
    if (TK_HI) { snprintf(path, sizeof(path), "%s.ticks.tsv", OUT); tkf = fopen(path, "w");
                 fprintf(tkf, "trace\tidx\tfirst\tlast\tn\tframe_cycles\n"); }
    snprintf(path, sizeof(path), "%s.frames.tsv", OUT);
    FILE *ff = fopen(path, "w");
    fprintf(ff, "trace\tcycles\tms\n");
    for (int i = 0; i < ntr; i++) {
        /* caches stay warm across traced frames only if contiguous; we reset timing per frame */
        run_trace(tr[i]);
        fprintf(ff, "%s\t%.0f\t%.3f\n", tr[i], frame_cycles, frame_cycles / 200000.0);
        if (tkf) { for (int k = 0; k < 33; k++) if (tk_n[k])
                       fprintf(tkf, "%s\t%d\t%.0f\t%.0f\t%d\t%.0f\n", tr[i], k, tk_first[k], tk_last[k], tk_n[k], frame_cycles);
                   fflush(tkf); }
        if (pf) {
            fprintf(pf, "%s\t%.0f", tr[i], frame_cycles);
            for (int p = 0; p < NPH; p++) fprintf(pf, "\t%.0f\t%.0f\t%.0f\t%.0f\t%.0f\t%.0f\t%llu\t%llu", fph_cyc[p], fph_cat[p][C_IMISS],
                fph_cat[p][C_DMISS], fph_cat[p][C_PFWAIT], fph_cat[p][C_SQ], fph_cat[p][C_UNCACHED],
                (unsigned long long)fph_if[p], (unsigned long long)fph_df[p]);
            fprintf(pf, "\t%llu\t%llu\n", (unsigned long long)ph_unknown, (unsigned long long)ph_marks); fflush(pf);
            ph_unknown = 0; ph_marks = 0;
        }
        fflush(ff);
    }
    fclose(ff);
    if (tkf) fclose(tkf);
    snprintf(path, sizeof(path), "%s.pcs.tsv", OUT);
    FILE *o = fopen(path, "w");
    fprintf(o, "pc\texec\tfly");
    for (int c = 0; c < C_NCAT; c++) fprintf(o, "\t%s", catname[c]);
    fprintf(o, "\timiss_n\tdrmiss\tdwmiss\tpf\tpfuse\tsqf\tstream_miss\tuncached_n\treads\twrites\tfdiv\tinduced\twords_used\tfills_owned\n");
    for (u32 i = 0; i < NPC; i++) {
        PcStat *s = &ps[i];
        if (!s->exec && !s->induced && !s->fills_owned && !s->cyc[C_DMISS] && !s->cyc[C_BRANCH]) continue;
        fprintf(o, "%08x\t%llu\t%llu", 0x8C000000u | (i << 1), (unsigned long long)s->exec, (unsigned long long)s->fly);
        for (int c = 0; c < C_NCAT; c++) fprintf(o, "\t%.2f", s->cyc[c] / 16.0);
        fprintf(o, "\t%u\t%u\t%u\t%u\t%u\t%u\t%u\t%u\t%u\t%u\t%u\t%u\t%llu\t%llu\n", s->imiss, s->drmiss, s->dwmiss, s->pf, s->pfuse,
                s->sqf, s->stream_miss, s->uncached, s->reads, s->writes, s->fdiv, s->induced,
                (unsigned long long)s->words_used, (unsigned long long)s->fills_owned);
    }
    {
        PcStat *s = &other;
        fprintf(o, "%08x\t%llu\t%llu", 0u, (unsigned long long)s->exec, (unsigned long long)s->fly);
        for (int c = 0; c < C_NCAT; c++) fprintf(o, "\t%.2f", s->cyc[c] / 16.0);
        fprintf(o, "\t%u\t%u\t%u\t%u\t%u\t%u\t%u\t%u\t%u\t%u\t%u\t%u\t%llu\t%llu\n", s->imiss, s->drmiss, s->dwmiss, s->pf, s->pfuse,
                s->sqf, s->stream_miss, s->uncached, s->reads, s->writes, s->fdiv, s->induced,
                (unsigned long long)s->words_used, (unsigned long long)s->fills_owned);
    }
    fclose(o);
    snprintf(path, sizeof(path), "%s.lines.tsv", OUT);
    FILE *lo = fopen(path, "w");
    fprintf(lo, "line\tmiss\tstall\tpc\n");
    for (u32 i = 0; i < RAM_SIZE / 32; i++) if (lst[i].miss)
        fprintf(lo, "%08x\t%u\t%.0f\t%08x\n", 0x8C000000u | (i << 5), lst[i].miss, lst[i].stall, lst[i].pc);
    fclose(lo);
    snprintf(path, sizeof(path), "%s.sum.txt", OUT);
    FILE *sm = fopen(path, "w");
    fprintf(sm, "dma_bytes_per_frame %.0f\ndma_starts_per_frame %.1f\ndma_bus_cycles_per_frame %.0f\n", (double)dma_bytes_tot / ntr, (double)dma_n / ntr, dma_cyc / ntr);
    fprintf(sm, "dfills_per_frame %.0f\nifills_per_frame %.0f\nwritebacks_per_frame %.0f\n", (double)n_fill / ntr, (double)n_ifill / ntr, (double)n_wb / ntr);
    fprintf(sm, "frames %d\ninsns %llu\nsleep_insns %llu\ncycles %.0f\nms_per_frame %.3f\ninsn_per_frame %.0f\n", ntr,
            (unsigned long long)tot_insn, (unsigned long long)tot_sleep, tot_cycles, tot_cycles / 200000.0 / ntr, (double)tot_insn / ntr);
    fclose(sm);
    fprintf(stderr, "frames %d  model %.2f ms/frame  insns/frame %.0f\n", ntr, tot_cycles / 200000.0 / ntr, (double)tot_insn / ntr);
    return 0;
}
