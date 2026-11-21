// E1 engine interface shared by core, host adapters and services (lane eng-e1).
#ifndef E1_ENGINE_H
#define E1_ENGINE_H
#ifdef __cplusplus
extern "C" {
#endif
#include <stdint.h>

// ---- main RAM map (fixed addresses: independent of the image size) ----
// Behaviour arena: every allocation of the hosted behaviour (the 13-heap API). Fixed address and size.
#ifdef E2_FIGHT
// lane eng-e2: the fight image draws the village beside the Ganado module and its motion keys; its behaviour arena
// peaks under 1 MB (4 Ganados, waves), so the arena is 1.25 MB and the room-pack region 1.5 MB larger.
#define E1_ARENA_LO 0x8ce00000u   /* lane eng-skel2: 512 KB up (was 0x8cd80000) */
#else
#define E1_ARENA_LO 0x8cc80000u   /* lane eng-skel2: 512 KB up (was 0x8cc00000) */
#endif
#define E1_ARENA_HI 0x8cf40000u   /* 2,883,584 B (lane eng-e1c: the services region follows; lane eng-skel2: 512 KB up) */
// Native services region (lane eng-e1c, host/e1_svc_mem.cpp): the skeleton pool (256 KB), the boot carve (the cloth
// pool, the SVCPROF arm's buffers) and the room carve (collision pieces made in play). Fixed address and size; the KOS
// kernel stack (64 KB) sits at 0x8cff0000. Lane eng-skel2: 512 KB (was 1 MB at 0x8cec0000): the room's collision comes
// baked in the room archive (services/collision/col.h), which the KOS heap holds: the behaviour arena moved up 512 KB
// with the region, so the KOS heap (up to E1_ARENA_LO) has 512 KB more; the room archive takes part of it (r101 +168 KB).
#define E1_SVC_LO 0x8cf40000u
#define E1_SVC_HI 0x8cfc0000u   /* 524,288 B */
// Resident behaviour data the original keeps at fixed addresses: player archive body, weapon archive body, room
// archive (CAM, SAT, EAT, ... sections the hosted code and the services read). Engine room-pack region, loaded at
// room entry, read in place.
extern uint8_t* e1_pl_arc;    /* pG->pPlayer */
extern uint8_t* e1_wep_arc;   /* pG->pWep */
extern uint8_t* e1_room_arc;  /* pG->pRoom */
extern uint8_t* e1_core_arc;  /* pG->pArc */

// ---- stubs into other behaviour: each logs its first calls and counts every call ----
void e1_stub_hit(const char* name, int arg);
void e1_stub_report(void);
// ---- serial / RAM log ----
void e1_log(const char* fmt, ...);
void e1_log_flush(void);   // lane eng-e1e: the lines buffered while the ticks ran (core/globals.cpp)
// ---- loader ----
void* e1_file_load(const char* path, uint32_t* size, uint32_t align);   /* whole file, KOS heap (room-pack region) */

// ---- arena statistics (the behaviour arena high-water mark) ----
typedef struct { uint32_t heap_lo[13], heap_hi[13], used[13], peak[13], fails[13], allocs, frees, refused; } E1ArenaStats;
extern E1ArenaStats e1_arena;
void e1_arena_init(void);
// lane eng-e1e (E1 audit section 6): the heap descriptors' map check (every live heap inside the arena, no two
// overlapping; returns the faults, 0 = valid) and the heap-4 exercise (allocate, free, reuse; boot option HEAPCK).
unsigned e1_heap_map_check(int log);
void e1_heap_exercise(int heap);
int e1_room_heap_create(int no);
void e1_heap_room_checks(void);

// ---- tick state ----
extern volatile uint32_t e1_tick;
#ifdef __cplusplus
}
#endif
#endif
