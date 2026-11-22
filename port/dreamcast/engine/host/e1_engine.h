// E1 engine interface shared by core, host adapters and services (lane eng-e1).
#ifndef E1_ENGINE_H
#define E1_ENGINE_H
#ifdef __cplusplus
extern "C" {
#endif
#include <stdint.h>

// ---- main RAM map (fixed addresses: independent of the image size) ----
// One owner (lane eng-mem1, H-031): docs/engine/MEMORY_MAP.md has every block's range per image, its measured peak in
// the worst scene and its margin. From the bottom: KOS and the image (0x8c010000 to _end), the KOS heap (_end to
// E1_ARENA_LO: renderer pack, sound data, archives the services read, loader buffers), the behaviour arena, the native
// services region, 64 KB below the main stack, the main stack (0x8cfd0000), the console loop's hand-off (0x8cfe0000).
// Behaviour arena: every allocation of the hosted behaviour (the 13-heap API), the room archive on its room heap (lane
// eng-load1, as read.cpp decodeData) with the collision baked into it (lane eng-skel2). Fixed address and size.
#ifdef E2_FIGHT
// The fight image: the village, the Ganado module and its motion keys and the effects fill the KOS heap (11.3 MB in
// use after play); its arena peaks at 844,384 B (4 Ganados, waves, the r101 archive): 1 MB (lane eng-mem1: was 1.25 MB,
// the KOS heap then ended play 28,672 B from the arena).
#define E1_ARENA_LO 0x8ce40000u   /* 1,048,576 B */
#else
// E1, BOSS, SENDABLE: the arena peaks at 1,077,984 B (DOOR, the farm's room heap); 2.75 MB holds the largest st1 room
// archive (r106, 993,920 B resident) beside the managers. The renderer's pack keeps frame 0 of its recording only
// (render/native_scene.inc, lane eng-mem1), so the KOS heap has megabytes to spare under this arena.
#define E1_ARENA_LO 0x8cc80000u   /* 2,883,584 B */
#endif
#define E1_ARENA_HI 0x8cf40000u
// Native services region (lane eng-e1c, host/e1_svc_mem.cpp): the skeleton pool (256 KB), the boot carve (the cloth
// pool, the SVCPROF arm's buffers) and the room carve (collision pieces made in play). 512 KB (lane eng-skel2: the
// room's collision comes baked in the room archive). The main thread's stack is 0x8cfd0000-0x8cfe0000.
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
