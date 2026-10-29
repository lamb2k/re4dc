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

# EF08: queued portal completion is separately opt-in; legacy portal stays exact.
WORLD_PORTAL_COMPLETION ?= 0
ifneq ($(words $(WORLD_PORTAL_COMPLETION)),1)
$(error WORLD_PORTAL_COMPLETION must be exactly 0 or 1)
endif
ifneq ($(filter-out 0 1,$(WORLD_PORTAL_COMPLETION)),)
$(error WORLD_PORTAL_COMPLETION must be exactly 0 or 1)
endif
ifeq ($(WORLD_PORTAL_COMPLETION),1)
ifneq ($(WORLD_PORTAL29)$(SCENERY_SUBMIT_BATCH)$(PS2_PVS_BATCH_COMPOSE),111)
$(error WORLD_PORTAL_COMPLETION needs WORLD_PORTAL29=1 SCENERY_SUBMIT_BATCH=1 PS2_PVS_BATCH_COMPOSE=1)
endif
ifneq ($(SCENERY_STREAM)$(SCENERY_CLIP_GATHER)$(SCENERY_CLIP_INDEXED26),000)
$(error WORLD_PORTAL_COMPLETION requires explicit SCENERY_STREAM=0 SCENERY_CLIP_GATHER=0 SCENERY_CLIP_INDEXED26=0)
endif
# These facts were formerly UI-only flags or late native_static header
# defaults. The existing early composition guards must see the actual selected
# Make values, not undefined zero. PVS_BATCH_COMPOSE already requires each=1.
WORLD_PORTAL_COMPLETION_FACTS := TA_DIRECT PS2_WORLD_HDR_CACHE MESH_FASTPATH PVR_STREAM
ifneq ($(strip $(foreach v,$(WORLD_PORTAL_COMPLETION_FACTS),$(if $(filter 1,$($(v))),,bad))),)
$(error WORLD_PORTAL_COMPLETION requires qualified direct/header/mesh/stream facts at 1)
endif
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += $(foreach v,$(WORLD_PORTAL_COMPLETION_FACTS),-DRE4DC_$(v)=$($(v)))
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_WORLD_PORTAL_COMPLETION=1
endif

# EF09 prepared world facts; absent/zero preserves all preceding paths/layouts.
WORLD_PREPARED09 ?= 0
ifneq ($(words $(WORLD_PREPARED09)),1)
$(error WORLD_PREPARED09 must be exactly 0 or 1)
endif
ifneq ($(filter-out 0 1,$(WORLD_PREPARED09)),)
$(error WORLD_PREPARED09 must be exactly 0 or 1)
endif
ifeq ($(WORLD_PREPARED09),1)
ifneq ($(WORLD_PART_PLAN29),1)
$(error WORLD_PREPARED09 needs WORLD_PART_PLAN29=1)
endif
ifneq ($(MOVIE_WORLD_ARENA),1)
$(error WORLD_PREPARED09 needs MOVIE_WORLD_ARENA=1 for existing room-cell lifetime authority)
endif
ifneq ($(STATIC_OBJ_LIFETIME05),1)
$(error WORLD_PREPARED09 needs STATIC_OBJ_LIFETIME05=1 for room-cell incarnation authority)
endif
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_STATIC_OBJ_LIFETIME05=$(STATIC_OBJ_LIFETIME05) -DRE4DC_WORLD_PREPARED09=1
endif

# Build31 review6: page a single source part through the existing 320 picks.
WORLD_PAGES31 ?= 0
ifneq ($(words $(WORLD_PAGES31)),1)
$(error WORLD_PAGES31 must be exactly 0 or 1)
endif
ifneq ($(filter-out 0 1,$(WORLD_PAGES31)),)
$(error WORLD_PAGES31 must be exactly 0 or 1)
endif
ifeq ($(WORLD_PAGES31),1)
ifneq ($(SCENERY_CHUNK)$(WORLD_PREPARED09),11)
$(error WORLD_PAGES31 needs SCENERY_CHUNK=1 WORLD_PREPARED09=1)
endif
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_WORLD_PAGES31=1
endif
