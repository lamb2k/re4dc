T = '/root/probe/lanes-20261016/ch4found/tree/'
def sub(s, old, new):
    assert s.count(old) == 1, old[:70]
    return s.replace(old, new)

p = T + 'port/dreamcast/game/platform/native_motion.cpp'; s = open(p).read()
s = sub(s, """#if RE4DC_MOTION_RESERVE_SPILL || RE4DC_MOTION_COLD_POOL
extern "C" int re4dc_static_heap_free();   // ui_bridge.cpp: heap 4 free bytes (-1 when inactive)
#endif""", """#if RE4DC_MOTION_RESERVE_SPILL || RE4DC_MOTION_COLD_POOL
extern "C" int re4dc_static_heap_free();   // ui_bridge.cpp: heap 4 free bytes (-1 when inactive)
#endif
#ifndef RE4DC_MOTION_COLD_POOL_CASTLE
#define RE4DC_MOTION_COLD_POOL_CASTLE 0
#endif
#if RE4DC_MOTION_COLD_POOL_CASTLE
// MOTION_COLD_POOL_CASTLE=<bytes> (game30.mk, lane ch4found16): the cold pool's heap 4 margin in the castle rooms
// (r2xx) instead of MOTION_COLD_POOL's.
extern "C" unsigned re4dc_room_id_now();   // ui_bridge.cpp: pG->room_id (0x226), 0 before the game starts
static inline unsigned cold_pool_margin() {
    return (re4dc_room_id_now()>>8)==2?unsigned(RE4DC_MOTION_COLD_POOL_CASTLE):unsigned(RE4DC_MOTION_COLD_POOL);
}
#else
#define cold_pool_margin() unsigned(RE4DC_MOTION_COLD_POOL)
#endif""")
s = sub(s, "re4dc_static_heap_free()>=int(bytes+RE4DC_MOTION_COLD_POOL)) {",
           "re4dc_static_heap_free()>=int(bytes+cold_pool_margin())) {")
open(p, 'w').write(s)

p = T + 'port/dreamcast/game/ui_bridge.cpp'; s = open(p).read()
s = sub(s, "extern \"C\" int re4dc_static_heap_free(){", """#if defined(RE4DC_MOTION_COLD_POOL_CASTLE) && RE4DC_MOTION_COLD_POOL_CASTLE
extern "C" unsigned re4dc_room_id_now(){return pG?unsigned(pG->room_id):0u;}   // native_motion.cpp
#endif
extern "C" int re4dc_static_heap_free(){""")
open(p, 'w').write(s)

p = T + 'port/dreamcast/game/game30.mk'; s = open(p).read()
s = sub(s, """$(OBJDIR)/platform/native_motion.o: PLATFORM_CPPFLAGS += -DRE4DC_MOTION_COLD_POOL=$(MOTION_COLD_POOL)
endif
""", """$(OBJDIR)/platform/native_motion.o: PLATFORM_CPPFLAGS += -DRE4DC_MOTION_COLD_POOL=$(MOTION_COLD_POOL)
endif
# MOTION_COLD_POOL_CASTLE=<bytes> (lane ch4found16 2026-10-17; needs MOTION_COLD_POOL; render and I/O only, default 0 =
# image unchanged): the cold pool's heap 4 margin in the castle rooms (room 0x2xx) instead of MOTION_COLD_POOL's.
# Why: r226's six em11 Zealots (GC-prepared archive, all keys cold) need ~130 KB of keys at once; with the test 15
# margin (262144) the pool stops at heap 4 272 KB free and the keys cycle through the two slabs: 3 disc reads + CRC
# per frame, ~0.9 s frames from the first death (Flycast). 131072 keeps the pool going (B3/B5 sends reached in 60 s).
MOTION_COLD_POOL_CASTLE ?= 0
ifneq ($(MOTION_COLD_POOL_CASTLE),0)
ifeq ($(MOTION_COLD_POOL),0)
$(error MOTION_COLD_POOL_CASTLE needs MOTION_COLD_POOL)
endif
$(OBJDIR)/platform/native_motion.o: PLATFORM_CPPFLAGS += -DRE4DC_MOTION_COLD_POOL_CASTLE=$(MOTION_COLD_POOL_CASTLE)
$(OBJDIR)/ui_bridge.o: GAME_CPPFLAGS += -DRE4DC_MOTION_COLD_POOL_CASTLE=$(MOTION_COLD_POOL_CASTLE)
endif
""")
open(p, 'w').write(s)
print('ok')
