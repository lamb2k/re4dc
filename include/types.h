#ifndef TYPES_H
#define TYPES_H

// Main-memory bounds of the pointer sanity checks spread over the game
// (VALID_PTR / PTR_INVALID / inline range tests): GameCube MEM1 on the
// PowerPC build, the Dreamcast's 16 MB of RAM (P1, cached) on the SH-4.
#if defined(__PPC__)
#define RE4_MEM_LO 0x80000000
#define RE4_MEM_HI 0x82FFFFFF
#else
#define RE4_MEM_LO 0x8C000000
#define RE4_MEM_HI 0x8CFFFFFF
#endif

typedef signed char s8;
typedef signed short s16;
typedef signed long s32;
typedef signed long long s64;
typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned long u32;
typedef unsigned long long u64;
typedef float f32;
typedef double f64;
typedef int BOOL;

// Unaligned halfwords. GameCube data packs u16 arrays straight after byte fields (motion and
// camera-motion parts kinds and shape flags at offset 3 of their headers, Hermite key counts and
// frames after odd-stride key blocks) and the PowerPC reads them in place. The SH-4 raises an
// address error on a misaligned access (Flycast does not, so only hardware shows it); through
// u16_un GCC reads and writes a byte at a time. The plain type on the PowerPC.
#if defined(__PPC__)
typedef u16 u16_un;
#else
typedef u16 u16_un __attribute__((aligned(1)));
#endif

// `register T x asm("rN")` pins reproduce the original register allocation.
// They are PowerPC register names; on any other target the pin is dropped and
// the declaration is an ordinary local.
#if defined(__PPC__) || defined(__powerpc__)
#define PPC_REG(r) asm(r)
#else
#define PPC_REG(r)
#endif

// `inline` members whose out-of-line copy the original compiler emitted for other
// units (GCC 2.95 -fkeep-inline-functions behaviour): ordinary definitions elsewhere.
#if defined(__PPC__) || defined(__powerpc__)
#define RE4_INLINE inline
#else
#define RE4_INLINE
#endif

// HALT(): the original stores to 0x11111111 to stop the game. On the SH-4 that address is in
// area 4 (TA FIFO): Flycast takes the misaligned store as a TA/YUV input word and the game runs
// on, and real hardware raises an address error. The port stops explicitly instead
// (platform/fault.cpp re4dc_halt: file:line to the log, then a deterministic stop).
#if defined(__PPC__)
#define RE4DC_HALT_STORE() (*(volatile u32*) 0x11111111 = 0)
#else
#ifdef __cplusplus
extern "C"
#endif
void re4dc_halt(const char* file, int line);
#define RE4DC_HALT_STORE() re4dc_halt(__FILE__, __LINE__)
#endif

#ifndef NULL
#define NULL 0
#endif

// EM_READ_RETRY (issue #52): a list send / create that still failed after readEmData's retries returns 0; room code
// guarded with EM_OK skips that enemy's part instead of dereferencing 0. Knob off: EM_OK is 1 (original code).
#if defined(RE4DC_EM_READ_RETRY) && RE4DC_EM_READ_RETRY
#define EM_OK(e) ((e) != 0)
#else
#define EM_OK(e) 1
#endif
// EM_MUST(T, expr): a progress-critical spawn (boss, boat): the create inside expr retries until it loads
// (em_set.cpp). Knob off: expr unchanged.
#if defined(RE4DC_EM_READ_RETRY) && RE4DC_EM_READ_RETRY && defined(__cplusplus)
extern "C" int re4dc_emSetMust;
extern "C" void* re4dc_em_must_end(void* em);
#define EM_MUST(T, x) ((T) re4dc_em_must_end((re4dc_emSetMust = 1, (void*) (x))))
#else
#define EM_MUST(T, x) (x)
#endif

#endif
