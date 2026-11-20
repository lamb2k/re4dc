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
// peaks under 1 MB (4 Ganados, waves), so the arena is 1.75 MB and the room-pack region 2 MB larger.
#define E1_ARENA_LO 0x8ce00000u
#else
#define E1_ARENA_LO 0x8cc00000u
#endif
#define E1_ARENA_HI 0x8cfc0000u   /* 3,932,160 B; the KOS kernel stack (64 KB) sits at 0x8cff0000 */
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
// ---- loader ----
void* e1_file_load(const char* path, uint32_t* size, uint32_t align);   /* whole file, KOS heap (room-pack region) */

// ---- arena statistics (the behaviour arena high-water mark) ----
typedef struct { uint32_t heap_lo[13], heap_hi[13], used[13], peak[13], fails[13], allocs, frees; } E1ArenaStats;
extern E1ArenaStats e1_arena;
void e1_arena_init(void);

// ---- tick state ----
extern volatile uint32_t e1_tick;
#ifdef __cplusplus
}
#endif
#endif
