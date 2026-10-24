# Build 12: alternate world payloads; absent/0 changes no flags or objects.
SCENERY_LOCAL_INDEXED ?= 0
SCENERY_DIRECT_STRIPS ?= 0
ifneq ($(filter-out 0 1,$(SCENERY_LOCAL_INDEXED) $(SCENERY_DIRECT_STRIPS)),)
$(error SCENERY_LOCAL_INDEXED and SCENERY_DIRECT_STRIPS must be 0 or 1)
endif
ifeq ($(SCENERY_LOCAL_INDEXED)$(SCENERY_DIRECT_STRIPS),11)
$(error Select only one Build 12 world data variant)
endif
ifneq ($(filter 1,$(SCENERY_LOCAL_INDEXED) $(SCENERY_DIRECT_STRIPS)),)
ifneq ($(NATIVE_MESH)$(MESH_LOD)$(PS2_WORLD_DRAW)$(PS2_WORLD_MESH)$(TA_DIRECT)$(MESH_DIRECT)$(IO_ALIGNED),1111111)
$(error World data variants need NATIVE_MESH/MESH_LOD/PS2_WORLD_DRAW/PS2_WORLD_MESH/TA_DIRECT/MESH_DIRECT/IO_ALIGNED=1)
endif
ifeq ($(filter 1 2,$(SCENERY_CHUNK)),)
$(error World data variants need SCENERY_CHUNK=1 or 2)
endif
ifeq ($(filter 1 2,$(PS2_WORLD_ROOMS)),)
$(error World data variants need PS2_WORLD_ROOMS=1 or 2)
endif
ifneq ($(filter-out 0,$(WORLD_VERT) $(SCENERY21_AB) $(SCENERY_DEDUP) $(SCENERY_CONE) $(SCENERY_PIECE_STATE) $(PS2_PVS) $(PS2_INTERIOR_CULL) $(WORLD_RECT21)),)
$(error World data variants do not reuse WORLD_VERT/SCENERY21_AB/SCENERY_DEDUP/SCCN/SCPS/PVS/interior-cell/WORLD_RECT21 certificates)
endif
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_SCENERY_LOCAL_INDEXED=$(SCENERY_LOCAL_INDEXED) -DRE4DC_SCENERY_DIRECT_STRIPS=$(SCENERY_DIRECT_STRIPS)
$(OBJDIR)/platform/native_static.o: ../room/scenery_data_variants.hpp ../room/scenery_direct_strips.hpp
endif
