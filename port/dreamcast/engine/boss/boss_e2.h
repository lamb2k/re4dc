// E2 boss slice (lane eng-boss): engine entry points the E1 shell calls in the BOSS=1 image (boss/boss_e2.cpp).
#ifndef BOSS_E2_H
#define BOSS_E2_H
void e2_room_globals();
void e2_managers_room_init();
void e2_room_init();
void e2_scenario_move(unsigned tick);
void e2_em_move();
void e2_fx_move();
void e2_after_tick();
void e2_trace_tick(unsigned tick, char* out, unsigned cap, unsigned* used);
int e2_construct(class cEm* p, unsigned id, unsigned guid);
void e2_report();
#endif
