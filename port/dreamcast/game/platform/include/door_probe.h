#pragma once
// DOOR_PROBE (Makefile; lane doorpause16, 2026-10-16; diagnostic, log only, default 0).
// Forced into the room-change source files (-include): with the knob off every mark is an empty statement, so the
// objects do not change. Marks are appended to existing source lines, so __LINE__ (HALT, pLog) stays the same.
#if defined(RE4DC_DOOR_PROBE) && RE4DC_DOOR_PROBE
#ifdef __cplusplus
extern "C" {
#endif
void re4dc_doorph(const char* mark, unsigned room);   // platform/door_probe.cpp: a phase mark of the door window
void re4dc_doorph_end(unsigned room);           // the room's first gameMainLoop frame: the window ends
void re4dc_doorspin(int end);                   // main.cpp: the main loop's vblank spin waits (0 begin, 1 end)
#ifdef __cplusplus
}
#endif
#define RE4DC_DOORPH(m) re4dc_doorph(m, (unsigned) pG->room_id)
#define RE4DC_DOORPH_END(r) re4dc_doorph_end(r)
#define RE4DC_DOORSPIN(e) re4dc_doorspin(e)
#else
#define RE4DC_DOORPH(m) ((void) 0)
#define RE4DC_DOORPH_END(r) ((void) 0)
#define RE4DC_DOORSPIN(e) ((void) 0)
#endif
