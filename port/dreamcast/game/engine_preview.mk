# engine_preview.mk: ENGINE_PREVIEW=1 (lane behave18, 2026-10-18; default 0 = nothing built, image unchanged). VIEWING
#   ONLY, never in a release until gated. In r101 the Ganados' (cEm10) chase steering and movement collision run on the
#   native actor runtime (platform/actor_rt.c): one shared flow field toward Leon over the offline r101 grid
#   (tools/enginebake/build_grid.py, EDGR v1) and grid wall/floor collision in place of the polygon world check where the
#   grid can decide. cEm10 stays the facade: damage, deaths, attacks (the game's Ctrl12 attack slots), events, spawns,
#   the cap, animation and drawing are the game's own. Not STRICT by design (a logic approximation).
#   ENGINE_PREVIEW_GRID = the private grid file (80,272 B, sha256 c4fd50bb..., re4-assets-private\edemo18-20261018\grid\c1000).
ENGINE_PREVIEW ?= 0
ENGINE_PREVIEW_GRID ?= /root/re4data/private/behave18/r101_grid.bin
ifeq ($(ENGINE_PREVIEW),1)
ifeq ($(wildcard $(ENGINE_PREVIEW_GRID)),)
$(error ENGINE_PREVIEW=1: no grid file $(ENGINE_PREVIEW_GRID))
endif
$(OBJDIR)/mod/em10g/shared/src/em10/em10.o $(OBJDIR)/src/game/ik.o: GAME_CPPFLAGS += -DRE4DC_ENGINE_PREVIEW=1 -Iplatform/include
PLATFORM_OBJS += $(OBJDIR)/platform/actor_rt.o $(OBJDIR)/platform/actor_rt_grid.o
$(OBJDIR)/platform/actor_rt.o: platform/actor_rt.c platform/include/actor_rt.h
	@mkdir -p $(dir $@)
	kos-cc $(KOS_CFLAGS) -O2 -Iplatform/include -c $< -o $@
$(OBJDIR)/platform/actor_rt_grid.o: platform/actor_rt_grid.S $(ENGINE_PREVIEW_GRID)
	@mkdir -p $(dir $@)
	kos-cc -c -DRE4DC_RT_GRID_FILE='"$(ENGINE_PREVIEW_GRID)"' $< -o $@
else ifneq ($(ENGINE_PREVIEW),0)
$(error ENGINE_PREVIEW is 0 or 1)
endif
