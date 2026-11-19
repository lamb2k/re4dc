// lab32.h (lane lab32, 2026-11-17): run-time switches for the console lab disc (LAB32=1, QA discs only, never a release).
// Every speed switch that can be chosen at run time is compiled in at its widest setting by lab32.mk and gated here by one
// byte of re4dc_lab32_k[]: 0 = the Test 27.2 release behaviour (the control arm), see qa_menu.cpp (`KNOB <name> <value>` on
// the QA link, `KNOBS` lists them) and tools/qalink/lab32_session.py. Outside LAB32 builds every macro below expands to
// nothing (or to the compile-time value), so a build without LAB32=1 keeps its image.
#ifndef RE4DC_LAB32_H
#define RE4DC_LAB32_H
#if defined(RE4DC_LAB32) && RE4DC_LAB32
enum {
    LK_FXDEAD,      // R10B_FX_DEAD mask 0..3 (bit 2 acts at the next effect spawn: it marks sprites dormant at EspSeqSet)
    LK_FXCUT,       // R10B_FX_CUT mask 0..7 (r10b only)
    LK_QCAP,        // R10B_FX_QCAP 1..8 (only with LK_FXCUT bit 4; boots at 4 = the compile-time default)
    LK_SPAWNCAP,    // R10B_FX_SPAWNCAP n (0 = off; acts at the next effect spawn)
    LK_UNLIVE,      // R10B_FX_UNLIVE 0/1
    LK_FXROOMS,     // FXCUT_ROOMS mask 0..3 in the fxcensus room list
    LK_MAPW,        // ESP_MAP_WORDS: 0 = 32 words (1024 slots), 1 = 57 words (applies at the next room entry)
    LK_FXSKIP31,    // FX_TRANS_SKIP31 0/1
    LK_FXDORM31,    // FX_DORMANT31 0/1
    LK_PSMEMO,      // PS31_SKIN_MEMO 0/1
    LK_PSGATE,      // PS31_GATE_MAT 0/1
    LK_CHARVIS,     // CHAR_VIS31 0/1/2
    LK_SKELIK,      // SKEL_IK_PASS 0/1
    LK_ROPE,        // R10B_ROPE_HALF 0/1
    LK_PREGATE,     // CASTLE_ACTOR_PREGATE 0/1
    LK_PENSUB,      // PEN_CLOTH_LOD_SUB 0/1
    LK_MOVCA,       // WORLD_VCACHE_MOVCA 0/1 (second set of kernels)
    LK_DRAW_MASK, LK_DELAY,
    LK_N
};
extern "C" volatile unsigned char re4dc_lab32_k[LK_N];
enum LabPhase { LabWorld, LabChars, LabFx, LabHud };
extern "C" unsigned re4dc_lab_phase_start();
extern "C" void re4dc_lab_phase_end(unsigned phase, unsigned start);
extern "C" void re4dc_lab_window(char* text, unsigned size, bool reset);
struct LabScope {
    LabPhase phase;
    unsigned start;
    explicit LabScope(LabPhase p, bool measure=true): phase(p), start(measure ? re4dc_lab_phase_start() : 0) {}
    ~LabScope() { re4dc_lab_phase_end(phase,start); }
};
#define LAB_PHASE(p, result) if (re4dc_lab32_k[LK_DRAW_MASK] & (1u << p)) return result; LabScope labScope(p)
#define LABI(i, m) ((re4dc_lab32_k[i] & (m)) != 0) &&
#define LABN(i) (re4dc_lab32_k[i] == 0) ||
#define LABGATE(i) (re4dc_lab32_k[i] != 0)
#define LAB_ESPWORDS() (re4dc_lab32_k[LK_MAPW] ? RE4DC_FX_ESP_WORDS : 32)
#define LAB_SPAWNCAP(c) ((unsigned) re4dc_lab32_k[LK_SPAWNCAP])
#define LAB_FXCUT(c) ((int) re4dc_lab32_k[LK_FXCUT])
#define LAB_QCAP(c) ((unsigned) re4dc_lab32_k[LK_QCAP])
#define LAB_FXROOMS(c) ((int) re4dc_lab32_k[LK_FXROOMS])
#define LAB_PENSUB_KEEP(m) (!re4dc_lab32_k[LK_PENSUB])
#else
#define LAB_PHASE(p, result)
#define LABI(i, m)
#define LABN(i)
#define LABGATE(i) 1
#define LAB_ESPWORDS() RE4DC_FX_ESP_WORDS
#define LAB_SPAWNCAP(c) (c)
#define LAB_FXCUT(c) (c)
#define LAB_QCAP(c) (c)
#define LAB_FXROOMS(c) (c)
#define LAB_PENSUB_KEEP(m) 0
#endif
#endif
