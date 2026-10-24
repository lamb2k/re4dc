// EM35_DIAG=1 (game30.mk, lane fix-mendez-freeze23 2026-10-23; diagnostic, test discs only, default 0 = image
// unchanged): Mendez (em35) state for the "he stops after an attack" report (#55 item 5). em35.cpp copies its routine
// bytes, motion and attack timers into this record after each move() (reads only, no logic change); ui_bridge.cpp
// counts game frames and logs when a live Mendez has not been moved, or has held one routine and motion frame, too
// long; native_ui.cpp draws both rows next to the speed counter so a console freeze can be photographed.
#ifndef RE4DC_EM35_DIAG_H
#define RE4DC_EM35_DIAG_H
#ifdef __cplusplus
extern "C" {
#endif
typedef struct Re4dcEm35Diag {
    unsigned live;        // 1 once a move() ran in this room (cleared at room change)
    unsigned moves;       // move() calls
    unsigned last_poll;   // poll count at the last move()
    unsigned r;           // r_no_0 << 24 | r_no_1 << 16 | r_no_2 << 8 | r_no_3
    unsigned mot;         // motion index (ARC(n) == pMot), 0xFF unknown, 0xFE none
    int frame10;          // motion frame x10
    int max10;            // motion max frame x10
    unsigned attr;        // Mot_attr << 16 | Mot_state
    unsigned ev;          // motEvent
    int hp;
    unsigned dist;        // horizontal distance to Leon (mm)
    unsigned atk_wait, lock_wait, flags;
    unsigned same;        // consecutive moves with the same routine and motion frame
    unsigned same_r1;     // consecutive moves in the same r_no_0 / r_no_1
    unsigned stuck_logged;
} Re4dcEm35Diag;
extern Re4dcEm35Diag re4dc_em35_diag[2];   // [type 0 whole body, type 1 upper body]
extern unsigned re4dc_em35_diag_polls;
#ifdef __cplusplus
}
#endif
#endif
