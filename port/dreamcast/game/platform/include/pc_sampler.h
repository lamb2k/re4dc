#pragma once
// Default-off statistical PC sampler (Makefile PC_SAMPLER=1, platform/pc_sampler.cpp).
// TMU1 (the one TMU channel KOS leaves free) interrupts at RE4DC_PC_SAMPLER_HZ;
// the handler stores the interrupted PC/PR/tid into a fixed RAM ring that the
// harness streams out of the emulator (read_pcs.py) and symbolizes offline
// (pcs_symbolize.py). With the knob off every entry point below is an empty
// inline, so hook sites compile to nothing and the ELF is unchanged.
#ifndef RE4DC_PC_SAMPLER
#define RE4DC_PC_SAMPLER 0
#endif

// Readback ABI (host tools depend on these exact values).
// re4dc_pcs = { uint32_t header[32]; uint32_t records[capacity][2]; }
#define RE4DC_PCS_MAGIC        0x31534350u  // "PCS1" little-endian
#define RE4DC_PCS_VERSION      1u
#define RE4DC_PCS_HEADER_WORDS 32u
enum Re4dcPcsHeader {
    RE4DC_PCS_H_MAGIC = 0, RE4DC_PCS_H_VERSION, RE4DC_PCS_H_HEADER_WORDS, RE4DC_PCS_H_CAPACITY,
    RE4DC_PCS_H_HZ, RE4DC_PCS_H_PERIOD_TICKS, RE4DC_PCS_H_JITTER_MASK, RE4DC_PCS_H_STATE,
    RE4DC_PCS_H_HEAD,          // records written (samples + markers), monotonic; published last
    RE4DC_PCS_H_SAMPLES, RE4DC_PCS_H_MARKERS,
    RE4DC_PCS_H_LAT_SUM_LO, RE4DC_PCS_H_LAT_SUM_HI, // sum of 80 ns ticks from underflow to handler
    RE4DC_PCS_H_LAT_MAX, RE4DC_PCS_H_LATE,          // max latency; samples later than LATE_TICKS
    RE4DC_PCS_H_LATE_TICKS, RE4DC_PCS_H_LAST_FRAME, RE4DC_PCS_H_STAGE_SOURCE,
    RE4DC_PCS_H_START_SECS, RE4DC_PCS_H_START_TICKS, // TMU2 uptime at start (secs, 80 ns ticks)
    RE4DC_PCS_H_COUNT
};
enum Re4dcPcsState { RE4DC_PCS_IDLE = 0, RE4DC_PCS_RUNNING = 1, RE4DC_PCS_STOPPED = 2, RE4DC_PCS_BUSY = 3 };
// Sample record (8 bytes):
//   w0 = tid[31:23] | (pc  & 0xFFFFFF) >> 1     (pc in 0x0C000000 RAM mirror, P1/P2)
//   w1 = flags[31:28] | stage[27:23] | (pr & 0xFFFFFF) >> 1
//   flags: bit28 pc outside RAM, bit29 pr outside RAM, bit30 late, bit31 frame marker
// Marker record: w0 = frame number, w1 = 0x80000000 | tid.
// stage = native_render_profile Stage while its frame is active, 31 otherwise.
// With PC_SAMPLER_PHASE=1 (header STAGE_SOURCE = 2) stage = id of the last game-phase marker
// (debug.cpp ProcessTickGet / ProcessTickInit; ids from the "PCSPH id=N no=K name=..." log
// lines, 30 = ids exhausted, 31 = no marker yet). A sample tagged P ran after marker P.
#define RE4DC_PCS_F_PC_FOREIGN 0x10000000u
#define RE4DC_PCS_F_PR_FOREIGN 0x20000000u
#define RE4DC_PCS_F_LATE       0x40000000u
#define RE4DC_PCS_F_MARKER     0x80000000u
#define RE4DC_PCS_STAGE_NONE   31u
#define RE4DC_PCS_PHASE_OTHER  30u
#define RE4DC_PCS_STAGE_SRC_PHASE 2u
#ifndef RE4DC_PC_SAMPLER_PHASE
#define RE4DC_PC_SAMPLER_PHASE 0
#endif

#ifdef __cplusplus
extern "C" {
#endif
#if RE4DC_PC_SAMPLER
void re4dc_pcs_start(void);                 // idempotent; logs and refuses if TMU1 is in use
void re4dc_pcs_stop(void);                  // stops TMU1 and restores KOS's default handler
void re4dc_pcs_frame(unsigned frame);       // optional frame-boundary marker (thread context)
#if RE4DC_PC_SAMPLER_PHASE
void re4dc_pcs_phase_mark(int no, const char* name);  // debug.cpp phase marker (game thread)
#endif
#else
static inline void re4dc_pcs_start(void) {}
static inline void re4dc_pcs_stop(void) {}
static inline void re4dc_pcs_frame(unsigned frame) { (void) frame; }
#endif
#ifdef __cplusplus
}
#endif
