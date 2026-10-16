#pragma once
// DOOR_PREFETCH (Makefile; lane doorprefetch16, 2026-10-16; default 0 = image unchanged).
// Forced into game.o and snd.o (-include): with the knob off every hook is an empty statement, so the objects do not
// change. Hooks are appended to existing source lines, so __LINE__ (HALT, pLog) stays the same.
//   RE4DC_DPF_BEGIN(w, room) / RE4DC_DPF_END(w): a wait of the room change in which the drive is idle; the native
//     texture cache (platform/include/door_prefetch.inc, in native_ui.cpp) loads `room`'s known textures into VRAM
//     during it, a little each frame. w = 1: gameDoordemo's wait for the door sound / SE fade (old room still loaded,
//     room = the door's next room); w = 2: gameRoomInit's SndRoomBgmLoad (the old music must let go of its slot; room =
//     the new room).
//   RE4DC_DPF_READ(read): SndStatDisp's door sound read state; window 1 loads only once that read is done.
//   RE4DC_DPF_YIELD(): in SndRoomBgmLoad's busy loop; inside window 2 it sleeps the task one frame per check, so the
//     main loop (and the prefetch step) runs while the old music fades out. Outside window 2 it does nothing.
#if defined(RE4DC_DOOR_PREFETCH) && RE4DC_DOOR_PREFETCH
#ifdef __cplusplus
extern "C" {
#endif
void re4dc_dpf_begin(int window, unsigned room);   // native_ui.cpp (door_prefetch.inc)
void re4dc_dpf_end(int window);
int re4dc_dpf_yield(void);
void re4dc_dpf_read(int read);                      // SndStatDisp: the door sound's read state (nonzero = done)
#ifdef __cplusplus
}
void TaskSleep(int frames);   // game/scheduler.cpp (include/scheduler.h)
#endif
#define RE4DC_DPF_BEGIN(w, r) re4dc_dpf_begin((w), (unsigned) (r))
#define RE4DC_DPF_END(w) re4dc_dpf_end(w)
#define RE4DC_DPF_YIELD() do { if (re4dc_dpf_yield()) TaskSleep(1); } while (0)
#define RE4DC_DPF_READ(r) re4dc_dpf_read(r)
#else
#define RE4DC_DPF_READ(r) ((void) 0)
#define RE4DC_DPF_BEGIN(w, r) ((void) 0)
#define RE4DC_DPF_END(w) ((void) 0)
#define RE4DC_DPF_YIELD() ((void) 0)
#endif
