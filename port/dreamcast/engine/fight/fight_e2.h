// E2 fight slice (lane eng-e2): engine entry points of the village square fight image (FIGHT=1).
#ifndef FIGHT_E2_H
#define FIGHT_E2_H
class cEm;
// Gameplay events, recorded per tick in call order (the plays-right check compares them with the old game's):
// spawn (an enemy constructed on the actor table), gone (destroyed), hit (life down), kill (life reached 0).
enum { E2EV_SPAWN = 1, E2EV_GONE, E2EV_HIT, E2EV_KILL, E2EV_KINDS };
void e2_event(int kind, cEm* em, int arg);
void e2_watch_hp();                 // after the enemy table's move: life changes become hit / kill events
void e2_fx_room_init();             // the effect service's room start (services/effects)
void e2_events_report();
#endif
