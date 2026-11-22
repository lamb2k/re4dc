// The hosted sound driver's view of the platform (lane eng-snd1, H-025.1). The driver units (src/game/snd*.cpp)
// include "re4dc_platform.h" outside the PowerPC build for three things: the sound data region (snd.cpp SND_DATA_TOP
// = re4dc_mem.sound), the boot log and a debug watch. This stand-in declares only those, so the driver is compiled
// unchanged without the old port's platform headers; services/sound/snd_svc.cpp defines them. The layout of
// Re4dcMemLayout is the old port's (port/dreamcast/game/platform/include/re4dc_platform.h); only `sound` is used.
#ifndef RE4DC_PLATFORM_H
#define RE4DC_PLATFORM_H
#ifdef __cplusplus
extern "C" {
#endif
struct Re4dcMemLayout {
    unsigned long arena_lo, arena_hi, dvd;
    unsigned long sound;      // snd.cpp SND_DATA_TOP: unused by the engine (its own boot, services/sound/snd_svc.cpp)
    unsigned long core, option, player, weapon, heap, heap_end;
};
extern struct Re4dcMemLayout re4dc_mem;
void re4dc_log(const char* fmt, ...);
void re4dc_watch_set(const void* addr, unsigned long words);
#ifdef __cplusplus
}
#endif
#endif
