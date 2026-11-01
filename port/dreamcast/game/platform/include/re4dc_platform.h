// Dreamcast platform layer for the recovered RE4 sources: the pieces the game
// units and the platform units share. The game's own headers stay untouched;
// units that need a platform value include this header under
// `#if !defined(__PPC__)`.
#ifndef RE4DC_PLATFORM_H
#define RE4DC_PLATFORM_H

#ifdef __cplusplus
extern "C" {
#endif

// The GameCube bus clock (162 MHz) the sources divide by; the OS tick counter
// the platform keeps runs at the derived timer clock (bus / 4 = 40.5 MHz) so
// every tick computation in the game keeps its original meaning.
#define RE4DC_BUS_CLOCK 162000000u
#define RE4DC_TIMER_CLOCK (RE4DC_BUS_CLOCK / 4)

// Memory layout. The GameCube build places its fixed regions at absolute
// addresses (main_mem.cpp SystemMemInit, read.cpp, snd.cpp); on the Dreamcast
// the platform carves the same regions out of one arena at boot and the game
// reads them from here.
struct Re4dcMemLayout {
    unsigned long arena_lo;   // first byte of the platform arena
    unsigned long arena_hi;   // one past its last byte
    unsigned long dvd;        // legacy lower-bound marker; aliases sound, not DVD staging
    unsigned long sound;      // snd.cpp SND_DATA_TOP (GameCube 0x80370000, 512 KB)
    unsigned long core;       // SysMem.core / read.cpp CORE_DATA_ADDR (0x80578000, CORE_DATA_MAX 0x234000)
    unsigned long option;     // SysMem.option / OPTION_DATA_ADDR (0x807AC000, 0x40000)
    unsigned long player;     // SysMem.player / PL_DATA_ADDR (0x807EC000, 0x118000)
    unsigned long weapon;     // SysMem.weapon / WEP_DATA_ADDR (0x80904000, 0x70000)
    unsigned long heap;       // SysMem.weapon + 0x70000: the OSAlloc arena start (0x80974000)
    unsigned long heap_end;   // SysMem.heap_end (0x817F4000)
};
extern struct Re4dcMemLayout re4dc_mem;

// Carves the arena; called once from OSInit (before SystemMemInit).
void re4dc_mem_init(void);

// Frame buffers / FIFO stand-ins for main_sub.cpp Render_init (the Dreamcast
// renderer owns the real ones; these only give the pointers the game keeps).
void* re4dc_frame_buffer(int index);
void* re4dc_gx_fifo(void);

// Boot diagnostics: printed on the serial console and kept in a RAM ring
// (re4dc_logbuf / re4dc_log_head) the capture tooling reads out of the
// emulator; re4dc_stage is the last platform stage reached.
void re4dc_log(const char* fmt, ...);
void re4dc_watch_set(const void* addr, unsigned long words);
// Game-side state report for the scripted input fixture (b < 0: one value).
void re4dc_fixture_state(const char* name, int a, int b);
extern int re4dc_diag;  // heavy periodic diagnostics (thread dumps) on
// DVD_BUFF_KB (Makefile, lane heap-margin25): the staging area size; default the GameCube's 128 KB. Each reader
// chunks its transfer through it (sound pieces: the whole area; the two halves: memory swap, event swap reload).
#ifndef RE4DC_DVD_BUFF_BYTES
#define RE4DC_DVD_BUFF_BYTES 0x20000
#endif
extern unsigned char re4dc_dvd_buff[RE4DC_DVD_BUFF_BYTES];  // DVD read staging area (GameCube 0x80350000)
void re4dc_set_stage(unsigned long stage);
// A symbol the platform does not implement yet was called: log and halt.
void re4dc_missing(const char* name);
// Routes KOS debug output into the ring and parks the CPU on an unhandled
// exception after logging its context (fault.cpp); called first from OSInit.
void re4dc_fault_init(void);

#ifdef __cplusplus
}
#endif

// TAIL_METER (bench.mk, benchmark discs only; default 0 = empty): the time the game thread spends inside the native
// frame's PVR scene open / close (fences, TA bank waits, scene finish), i.e. the CPU blocked on the graphics chip.
#if defined(RE4DC_TAIL_METER) && RE4DC_TAIL_METER && defined(__cplusplus)
extern "C" void re4dc_tail_gpu(int end);   // bench.cpp
struct Re4dcTailGpuScope { Re4dcTailGpuScope() { re4dc_tail_gpu(0); } ~Re4dcTailGpuScope() { re4dc_tail_gpu(1); } };
#define RE4DC_TAIL_GPU_SCOPE(n) Re4dcTailGpuScope re4dc_tail_gpu_##n
#else
#define RE4DC_TAIL_GPU_SCOPE(n)
#endif

#endif
