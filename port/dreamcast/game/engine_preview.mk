# engine_preview.mk: ENGINE_PREVIEW=1, the enemy logic engine (lanes behave18 -> engine19; default 0 = nothing built,
#   image unchanged). Original brain, new body (user 10-18): cEm10's AI (routines, route, decisions, attacks, damage,
#   deaths) runs unchanged; in a room whose data file /cd/dc/native/rXXX/room.r4rc (tools/enginebake/room_compile.py,
#   R4RC v1 GRID) loaded at room entry, the native actor runtime (platform/actor_rt.c) answers its movement collision
#   and foot IK floor queries; the source (SatMgr) decides wherever the grid cannot. The grid is room data in heap 4,
#   not in the program. A logic approximation: its own gameplay-equivalence gate, not STRICT.
ENGINE_PREVIEW ?= 0
# ENGINE_VIS_LOG=1 (diagnostic, test arms only; engine19 Task 2): an EVIS log line per Ganado per tick (em10.cpp).
ENGINE_VIS_LOG ?= 0
ifeq ($(ENGINE_VIS_LOG),1)
$(OBJDIR)/mod/em10g/shared/src/em10/em10.o: GAME_CPPFLAGS += -DRE4DC_ENGINE_VIS_LOG=1
endif
# ENEMY_VIS_CULL=1 (lane engine19, the wall check; render only; default 0 = nothing built): a Ganado that a large
#   opaque occluder of the room's PS2 world hides from the real camera eye (the room data file's OCCL section,
#   tools/enginebake/room_compile.py --world) takes CROWD_INVIS_SKIP's draw-only skip paths, as
#   PS2_INTERIOR_ACTORS's house test does (platform/room_occl.c). Independent of ENGINE_PREVIEW. No room file / no
#   OCCL / fog not believed / within 3 m of Leon or Ashley / the world not as compiled: drawn.
ENEMY_VIS_CULL ?= 0
ROOMFILE_SECTIONS :=
ifeq ($(ENGINE_PREVIEW),1)
$(OBJDIR)/mod/em10g/shared/src/em10/em10.o $(OBJDIR)/src/game/ik.o: GAME_CPPFLAGS += -DRE4DC_ENGINE_PREVIEW=1 -Iplatform/include
$(OBJDIR)/ui_bridge.o: GAME_CPPFLAGS += -DRE4DC_ENGINE_PREVIEW=1
PLATFORM_OBJS += $(OBJDIR)/platform/actor_rt.o
$(OBJDIR)/platform/actor_rt.o: platform/actor_rt.c platform/include/actor_rt.h platform/include/room_file.h
	@mkdir -p $(dir $@)
	kos-cc $(KOS_CFLAGS) -O2 -Iplatform/include -c $< -o $@
ROOMFILE_SECTIONS += -DRE4DC_ROOMFILE_GRID=1
else ifneq ($(ENGINE_PREVIEW),0)
$(error ENGINE_PREVIEW is 0 or 1)
endif
ifneq ($(filter $(ENEMY_VIS_CULL),1 2),)
ifneq ($(CROWD_INVIS_SKIP),1)
$(error ENEMY_VIS_CULL needs CROWD_INVIS_SKIP=1)
endif
ifneq ($(PS2_INTERIOR_ACTORS),2)
$(error ENEMY_VIS_CULL needs PS2_INTERIOR_ACTORS=2)
endif
$(OBJDIR)/ui_bridge.o $(OBJDIR)/coarse_ganado.o: GAME_CPPFLAGS += -DRE4DC_ENEMY_VIS_CULL=1
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_ENEMY_VIS_CULL=1
$(OBJDIR)/coarse_ganado.o: GAME_CPPFLAGS += -Iplatform/include
$(OBJDIR)/coarse_ganado.o: platform/include/room_vis.h
ENEMY_VIS_DEBUG ?= 0
ifeq ($(ENEMY_VIS_DEBUG),1)
$(OBJDIR)/coarse_ganado.o: GAME_CPPFLAGS += -DRE4DC_ENEMY_VIS_DEBUG=1
endif
ifeq ($(ENEMY_VIS_CULL),1)
# =1 (option C, the one to ship): OCCL slab occluders tested from the real eye (platform/room_occl.c)
PLATFORM_OBJS += $(OBJDIR)/platform/room_occl.o
$(OBJDIR)/platform/room_occl.o: platform/room_occl.c platform/include/room_vis.h platform/include/room_file.h
	@mkdir -p $(dir $@)
	kos-cc $(KOS_CFLAGS) -O2 -Iplatform/include -DRE4DC_ENEMY_VIS_DEBUG=$(ENEMY_VIS_DEBUG) -c $< -o $@
ROOMFILE_SECTIONS += -DRE4DC_ROOMFILE_OCCL=1
else
# =2 (VIS v2, cell-to-cell; reference only, not shipped: it hid 0 enemies in the measured scenes)
PLATFORM_OBJS += $(OBJDIR)/platform/room_vis.o
ENEMY_VIS_DEBUG ?= 0
$(OBJDIR)/platform/room_vis.o: platform/room_vis.c platform/include/room_vis.h platform/include/room_file.h
	@mkdir -p $(dir $@)
	kos-cc $(KOS_CFLAGS) -O2 -Iplatform/include -DRE4DC_ENEMY_VIS_DEBUG=$(ENEMY_VIS_DEBUG) -c $< -o $@
ROOMFILE_SECTIONS += -DRE4DC_ROOMFILE_VIS=1
endif
else ifneq ($(ENEMY_VIS_CULL),0)
$(error ENEMY_VIS_CULL is 0, 1 or 2)
endif
ifneq ($(strip $(ROOMFILE_SECTIONS)),)
$(OBJDIR)/ui_bridge.o: GAME_CPPFLAGS += -DRE4DC_ROOM_FILE=1 -Iplatform/include
PLATFORM_OBJS += $(OBJDIR)/platform/room_file.o
$(OBJDIR)/platform/room_file.o: platform/room_file.c platform/include/room_file.h
	@mkdir -p $(dir $@)
	kos-cc $(KOS_CFLAGS) -O2 -Iplatform/include $(ROOMFILE_SECTIONS) -c $< -o $@
endif
# BENCH_SCENES=<n> (engine19 2026-10-19, bench discs only; default empty: nothing changes): RE4DC_BENCH_SCENES for a
#   BENCHMARK=1 disc that runs /cd/dc/bench3.txt, bench4.txt ... (bench.cpp defaults to 2 scenes).
ifneq ($(strip $(BENCH_SCENES)),)
$(OBJDIR)/bench.o: PLATFORM_CPPFLAGS += -DRE4DC_BENCH_SCENES=$(BENCH_SCENES)
endif
