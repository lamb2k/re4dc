#ifndef RE4DC_OTHER_PROFILE_H
#define RE4DC_OTHER_PROFILE_H
// Default-off, trace-visible ownership markers. Each marker executes one NOP.
// No clock/counter read or pacing/game-state change. Offline accounting gives
// marker PCs and all bracketed diagnostic work their own instrumentation bucket.
#if defined(RE4DC_OTHER_PROFILE) && RE4DC_OTHER_PROFILE
#if !defined(__sh__)
#error OTHER_PROFILE is an SH-4 trace diagnostic
#endif
#ifndef RE4DC_OTHER_UNIT
#error Set RE4DC_OTHER_UNIT to a unique string before this header
#endif
#define OTHER_MARK_ASM(kind) ".global _re4dc_other_marker_" RE4DC_OTHER_UNIT "_" #kind "_%=\n" \
    "_re4dc_other_marker_" RE4DC_OTHER_UNIT "_" #kind "_%=:\n\tnop\n"
#define OTHER_MARK(kind) asm volatile(OTHER_MARK_ASM(kind) : : : "memory")
#define OTHER_PHASE(p) OTHER_MARK(phase##p)
#define OTHER_INSTR_BEGIN() OTHER_MARK(instr_begin)
#define OTHER_INSTR_END() OTHER_MARK(instr_end)
// Keep the membership result available before ending its diagnostic region.
#define OTHER_INSTR_END_VALUE(value) asm volatile(OTHER_MARK_ASM(instr_end) : "+r"(value) : : "memory")
#else
#define OTHER_PHASE(p) ((void)0)
#endif
#endif
