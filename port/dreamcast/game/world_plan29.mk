# Build31. Definitions are absent when controls are zero, including explicit 0.
WORLD_PORTAL29 ?= 0
WORLD_PART_PLAN29 ?= 0
$(foreach knob,WORLD_PORTAL29 WORLD_PART_PLAN29,$(if $(filter 1,$(words $($(knob)))),,$(error $(knob) must be one value, 0 or 1)))
ifneq ($(filter-out 0 1,$(WORLD_PORTAL29) $(WORLD_PART_PLAN29)),)
$(error WORLD_PORTAL29 and WORLD_PART_PLAN29 must be 0 or 1)
endif
ifeq ($(WORLD_PART_PLAN29),1)
ifneq ($(NATIVE_PKG_HIGH),1)
$(error WORLD_PART_PLAN29=1 needs NATIVE_PKG_HIGH=1 for optional allocation without eviction)
endif
ifneq ($(PS2_WORLD_MESH),1)
$(error WORLD_PART_PLAN29=1 needs PS2_WORLD_MESH=1)
endif
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_WORLD_PART_PLAN29=1
$(OBJDIR)/ui_bridge.o: GAME_CPPFLAGS += -DRE4DC_WORLD_PART_PLAN29=1
endif
ifeq ($(WORLD_PORTAL29),1)
ifneq ($(NATIVE_PKG_HIGH),1)
$(error WORLD_PORTAL29=1 needs NATIVE_PKG_HIGH=1 for optional allocation without eviction)
endif
ifneq ($(MESH_FASTPATH)$(MESH_DIRECT)$(MESH_VP_SCHED)$(HW_LEAN)$(SCENERY_CHUNK),11111)
$(error WORLD_PORTAL29=1 needs MESH_FASTPATH=1 MESH_DIRECT=1 MESH_VP_SCHED=1 HW_LEAN=1 SCENERY_CHUNK=1)
endif
ifneq ($(PS2_PVS),1)
$(error WORLD_PORTAL29=1 needs PS2_PVS=1 for scene and opaque-submission proof)
endif
ifeq ($(filter 1 2,$(PS2_INTERIOR_CULL)),)
$(error WORLD_PORTAL29=1 needs PS2_INTERIOR_CULL=1 or 2)
endif
ifneq ($(PS2_WORLD_DYNAMIC)$(PS2_WORLD_MESH)$(MESH_LOD),111)
$(error WORLD_PORTAL29=1 needs PS2_WORLD_DYNAMIC=1 PS2_WORLD_MESH=1 MESH_LOD=1)
endif
ifeq ($(filter 1 2 3,$(PS2_WORLD_ROOMS)),)
$(error WORLD_PORTAL29=1 needs PS2_WORLD_ROOMS=1, 2 or 3)
endif
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_WORLD_PORTAL29=1
$(OBJDIR)/ui_bridge.o: GAME_CPPFLAGS += -DRE4DC_WORLD_PORTAL29=1
endif
