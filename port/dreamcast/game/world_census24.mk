# Build 10 Gate 0 census. Diagnostic only; absent/0 adds no flags or objects.
WORLD_CENSUS24 ?= 0
WORLD_CENSUS24_WINDOW ?= 300
ifneq ($(filter-out 0 1,$(WORLD_CENSUS24)),)
$(error WORLD_CENSUS24 must be 0 or 1)
endif
ifeq ($(WORLD_CENSUS24),1)
ifneq ($(QA_MENU),1)
$(error WORLD_CENSUS24=1 needs QA_MENU=1 for the sealed census page)
endif
ifneq ($(PS2_WORLD_DRAW)$(PS2_WORLD_MESH)$(PVR_STREAM)$(MESH_DIRECT)$(TA_DIRECT),11111)
$(error WORLD_CENSUS24=1 needs PS2_WORLD_DRAW/PS2_WORLD_MESH/PVR_STREAM/MESH_DIRECT/TA_DIRECT=1)
endif
ifneq ($(filter 2,$(MESH_VP_SCHED) $(MESH_STRIP_LEAN) $(MESH_CLIP_ACCEPT) $(PS2_INTERIOR_CULL) $(SG_SELECT_LEAN)),)
$(error WORLD_CENSUS24 rejects duplicate-work comparison modes set to 2)
endif
ifeq ($(SCENERY_DEDUP_CHECK),1)
$(error WORLD_CENSUS24 rejects SCENERY_DEDUP_CHECK reference-transform comparisons)
endif
WC24_GAME_OBJS = $(OBJDIR)/src/game/main.o $(OBJDIR)/pace.o $(OBJDIR)/pace_present.o
WC24_PLATFORM_OBJS = $(OBJDIR)/platform/native_static.o $(OBJDIR)/platform/native_ps2_world.o $(OBJDIR)/platform/native_ui.o $(OBJDIR)/qa_menu.o $(OBJDIR)/native-reuse/gpu_lifecycle.o
$(WC24_GAME_OBJS): GAME_CPPFLAGS += -DRE4DC_WORLD_CENSUS24=1
$(WC24_PLATFORM_OBJS): PLATFORM_CPPFLAGS += -DRE4DC_WORLD_CENSUS24=1
PLATFORM_OBJS += $(OBJDIR)/world_census24.o
$(TARGET): $(OBJDIR)/world_census24.o
WC24_PACE_OBSERVER := $(if $(filter-out 0,$(PACE_CATCHUP)),$(if $(filter 1,$(PACE_VMU)),$(if $(filter 1,$(PACE_VMU_GPU)),1,0),0),0)
ifeq ($(WC24_PACE_OBSERVER),0)
GAME_LDFLAGS += -Wl,--wrap=pvr_sync_stats
endif
GAME_LDFLAGS += -Wl,--wrap=pvr_wait_ready -Wl,--wrap=pvr_wait_render_done
$(OBJDIR)/world_census24.o: world_census24.cpp platform/include/world_census24.h
	@mkdir -p $(dir $@)
	kos-c++ $(KOS_CFLAGS) $(PLATFORM_CPPFLAGS) -DRE4DC_WORLD_CENSUS24=1 -DRE4DC_WORLD_CENSUS24_WINDOW=$(WORLD_CENSUS24_WINDOW) -DRE4DC_WC24_PACE_OBSERVER=$(WC24_PACE_OBSERVER) -MMD -MP -c $< -o $@
-include $(OBJDIR)/world_census24.d
endif
