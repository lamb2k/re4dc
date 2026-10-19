# engine_preview.mk: ENGINE_PREVIEW=1, the enemy logic engine (lanes behave18 -> engine19; default 0 = nothing built,
#   image unchanged). Original brain, new body (user 10-18): cEm10's AI (routines, route, decisions, attacks, damage,
#   deaths) runs unchanged; in a room whose data file /cd/dc/native/rXXX/room.r4rc (tools/enginebake/room_compile.py,
#   R4RC v1 GRID) loaded at room entry, the native actor runtime (platform/actor_rt.c) answers its movement collision
#   and foot IK floor queries; the source (SatMgr) decides wherever the grid cannot. The grid is room data in heap 4,
#   not in the program. A logic approximation: its own gameplay-equivalence gate, not STRICT.
ENGINE_PREVIEW ?= 0
ifeq ($(ENGINE_PREVIEW),1)
$(OBJDIR)/mod/em10g/shared/src/em10/em10.o $(OBJDIR)/src/game/ik.o: GAME_CPPFLAGS += -DRE4DC_ENGINE_PREVIEW=1 -Iplatform/include
$(OBJDIR)/ui_bridge.o: GAME_CPPFLAGS += -DRE4DC_ENGINE_PREVIEW=1 -Iplatform/include
PLATFORM_OBJS += $(OBJDIR)/platform/actor_rt.o
$(OBJDIR)/platform/actor_rt.o: platform/actor_rt.c platform/include/actor_rt.h
	@mkdir -p $(dir $@)
	kos-cc $(KOS_CFLAGS) -O2 -Iplatform/include -c $< -o $@
else ifneq ($(ENGINE_PREVIEW),0)
$(error ENGINE_PREVIEW is 0 or 1)
endif
