# Build 13: an explicit v4 world reader; absent/0 adds no flags or objects.
SCENERY_RECORD_SPLIT ?= 0
ifneq ($(filter-out 0 1,$(SCENERY_RECORD_SPLIT)),)
$(error SCENERY_RECORD_SPLIT must be 0 or 1)
endif
ifeq ($(SCENERY_RECORD_SPLIT),1)
ifneq ($(NATIVE_MESH)$(MESH_LOD)$(PS2_WORLD_DRAW)$(PS2_WORLD_MESH)$(TA_DIRECT)$(MESH_DIRECT)$(IO_ALIGNED),1111111)
$(error SCENERY_RECORD_SPLIT needs NATIVE_MESH/MESH_LOD/PS2_WORLD_DRAW/PS2_WORLD_MESH/TA_DIRECT/MESH_DIRECT/IO_ALIGNED=1)
endif
ifeq ($(filter 1 2,$(SCENERY_CHUNK)),)
$(error SCENERY_RECORD_SPLIT needs SCENERY_CHUNK=1 or 2)
endif
ifeq ($(filter 1 2,$(PS2_WORLD_ROOMS)),)
$(error SCENERY_RECORD_SPLIT needs PS2_WORLD_ROOMS=1 or 2)
endif
ifneq ($(filter-out 0,$(WORLD_VERT) $(SCENERY21_AB) $(SCENERY_DEDUP) $(SCENERY_CONE) $(SCENERY_PIECE_STATE) $(PS2_PVS) $(PS2_INTERIOR_CULL) $(WORLD_RECT21)),)
$(error SCENERY_RECORD_SPLIT does not reuse mesh-bound WORLD_VERT/SCENERY21_AB/dedup/SCCN/SCPS/PVS/interior/WORLD_RECT21 certificates)
endif
ifneq ($(filter-out 0,$(SCENERY_LOCAL_INDEXED) $(SCENERY_DIRECT_STRIPS)),)
$(error SCENERY_RECORD_SPLIT has not qualified Build12 payload/lineage composition)
endif
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_SCENERY_RECORD_SPLIT=1
$(OBJDIR)/platform/native_static.o: ../room/scenery_record_split.hpp platform/include/scenery_chunk_select.inc platform/include/scenery_select_lean2.inc
endif
