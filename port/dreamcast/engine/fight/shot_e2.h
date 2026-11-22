// The shot fixture on the engine (lane eng-e1k; fight/shot_e2.cpp): the FIGHT=1 image plays a re4ref fixture file.
#ifndef SHOT_E2_H
#define SHOT_E2_H
#include <stdint.h>
struct E1Pad;
#define E2_SHOT_ACTORS 16
#define E2_SHOT_PADS 64
struct E2ShotActor { unsigned entry, tick; int post; };
struct E2ShotPad { unsigned tick; uint16_t buttons; int8_t sx, sy; uint8_t tr; };
struct E2Shot {
    int active, refused;          // a fixture file was found; it asked for something the engine does not play
    unsigned room, ticks, seed;
    float pos[3], ang;
    int weapon_no, weapon_type, esl, god;
    int has_resume, resume_frame, resume_event;
    float resume_pos[3], resume_ang;
    E2ShotActor actors[E2_SHOT_ACTORS];
    unsigned nactors;
    E2ShotPad pads[E2_SHOT_PADS];
    unsigned npads;
    int ctl_dmg, ctl_late;        // controls SHOTDMG, SHOTLATE
    int ctl_notick;               // control DMGNOTICK (lane eng-e2f): the damage table's tick not run
};
extern E2Shot e2_shot;
void e2_shot_boot();                                   // reads /cd/SHOT.TXT (and the control files), once
void e2_shot_room_init();                              // after Leon and the camera: the resume, the seed
void e2_shot_tick_begin(unsigned tick, E1Pad* out);    // before PadRead: creations, god, the pad
void e2_shot_after_em_move(unsigned tick);             // after the enemy table's move: the post creations
#endif
