// hostref: shared declarations of the host (PC) reference build. See Makefile and PLAYS_RIGHT.md.
//
// Two kinds of host files: the "game side" (host_glue, host_memapi, host_globals, host_mgr, host_em,
// host_stubs, replay) includes the game's headers, whose include/dolphin/types.h brings the game's own
// libc headers (include/libc: FILE, va_list); the "PC side" (host_io, host_mem, host_data, host_trace,
// host_rt) includes the system C library. This header is shared by both, so it uses neither.
#pragma once
#include <stdint.h>
#include <stddef.h>

// Guest memory: the Dreamcast's 16 MiB main RAM window, mapped at the same address on the PC
// (0x8C000000), so the game's RE4_MEM_LO/HI pointer checks and its u32 pointer arithmetic hold.
#define HOST_ARENA_BASE 0x8C000000u
#define HOST_ARENA_SIZE 0x01000000u

struct HostPad {
    unsigned tick;
    uint16_t button;
    int8_t sx, sy, cx, cy;
    uint8_t tl, tr;
};
struct HostFixture {
    unsigned room;
    float pos[3];
    float ang;
    int weapon_no, weapon_type;
    unsigned seed;
    unsigned ticks;
    unsigned npads;
    HostPad pads[4096];
    // resume: after construction, the player continues from a recorded state (an old-game trace tick):
    // position, yaw, and the idle footwork restarted at `frame` with no blend (see replay.cpp)
    int has_resume;
    float resume_pos[3];
    float resume_ang;
    int resume_frame;
    int resume_clear_event;   // also clear be_flag 0x04000000, as the event end (endEvent0) does
    // actors (lane eng-host2): the room's enemy list and the entries the reference creates from it
    int esl;                  // enemy list file etc/emleonNN.esl (-1: none)
    unsigned nactors;
    struct { unsigned tick; unsigned entry; int post; } actors[16];   // EmSetFromList2(entry) before tick's
                                                                       // pass, or after its EmMgr.move (post)
    int god;                  // the old fixtures' god mode: Leon's life refilled every tick (warp `god`)
    unsigned nhits;
    struct { unsigned tick; unsigned entry; unsigned type; } hits[16];   // a weapon hit on that actor
    unsigned nsub;            // partner placement after creation (resume-like): position and yaw
    float sub_pos[3];
    float sub_ang;
};
enum HostControl { HOST_CTL_NONE = 0, HOST_CTL_WALK_SPEED = 1, HOST_CTL_DROP_RNG = 2, HOST_CTL_SHIFT_INPUT = 3,
                   HOST_CTL_DROP_RNG_ACTOR = 4, HOST_CTL_FOLLOW_DIST = 5, HOST_CTL_LATE_HIT = 6 };
struct HostOptions {
    const char* tree;
    const char* fixture;
    const char* out;
    const char* log;
    int control;
    float k;          // walk-speed factor, follow-dist factor
    unsigned tick;    // drop-rng / drop-rng-actor tick
    int shift;        // shift-input ticks, late-hit ticks
    const char* rng_feed;   // old logic trace: the generator state at each tick's start (LT r=)
    int rng_offset;         // its tick = reference tick + offset
};
// One hosted actor's line (A): every live enemy-list work other than the player, in alive-list order.
struct HostActorRecord {
    unsigned t, k;
    unsigned id, entry;
    uint32_t pos[3], ang[3];
    char mot[16];
    uint32_t frame, mstate;
    uint8_t rno[4];
    int hp;
    uint32_t be, flags, ps;
    uint32_t rng_calls;       // generator calls this actor made this tick (its emMove)
};
// Per-caller generator calls this tick (R line): owners 0 other, 1 player, 2 camera, 3 objects, 4 spawn,
// 5.. the alive-list actors in order (A k = owner - 5).
#define HOST_RNG_OWNERS 24
// One trace line (host_trace.cpp writes it; replay.cpp fills it). Floats as their bit patterns.
struct HostTickRecord {
    unsigned t;
    uint16_t button;
    int8_t sx, sy;
    int has_pl;
    uint32_t pos[3], ang[3];
    char mot[16];
    uint32_t frame, mstate;
    uint8_t rno[4];
    uint32_t be, ps, psm;
    uint32_t cam[7];          // pos xyz, at xyz, fovy
    uint32_t rng, rng_calls;
    uint32_t stub_calls, stub_hash;
    const char* stub_names;
};

extern "C" {
// host_mem.cpp
void host_arena_init();
void* host_alloc(uint32_t size, uint32_t align, const char* why);
void host_free(void* p);
uint32_t host_heap_used();
void* host_fixed(uint32_t size, const char* why);   // permanent region below the heap (data archives)
// host_trace.cpp
void host_stub_hit(const char* name);
void host_log(const char* fmt, ...);
void host_fatal(int code, const char* fmt, ...);
void host_stub_tick_reset();
uint32_t host_stub_calls();
uint32_t host_stub_hash();
const char* host_stub_names();
extern unsigned host_rnd_calls;   // rnd.cpp host copy: host_rnd_hook() in Rnd() (prep.py rnd)
unsigned short host_rnd_state(void);
void host_rnd_hook(unsigned short* state);   // every Rnd() call, before it draws: counts it for its owner
extern int host_rnd_owner;                   // the caller the next draws are counted for
extern unsigned host_rnd_owner_calls[HOST_RNG_OWNERS];
extern int host_rnd_drop_owner;              // control drop-rng-actor: the owner whose next call is dropped
extern unsigned host_rnd_dropped;
void host_actor_write(const HostActorRecord* r);
void host_rng_write(unsigned t, const unsigned* calls, int n);
int host_load_rng_feed(const char* path, unsigned short* states, unsigned char* have, unsigned max);
// host_io.cpp
int host_parse_args(int argc, char** argv, HostOptions* o);
int host_parse_fixture(const char* path, HostFixture* f);
int host_open_outputs(const HostOptions* o);
void host_trace_header(const HostOptions* o, const HostFixture* f, const char* fp);
void host_trace_write(const HostTickRecord* r);
void host_close_outputs();
// host_data.cpp: a DVD container or plain file from the data tree into the data region (0: missing)
void* host_load_data(const char* tree, const char* name, const char* why, uint32_t* bytes);
// host_data.cpp: register an archive whose FCV clips keep their keys in dc/mot (the MTC tag), for
// motion.cpp's Re4dcMotionLease (re4dc_motion_acquire)
void host_motion_bind(const char* tree, void* archive, uint32_t bytes);
// host_rt.cpp
void host_fp_init();
}
