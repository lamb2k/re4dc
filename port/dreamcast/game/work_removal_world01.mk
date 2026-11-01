# Default-OFF work-removal spike: retain the complete world binding contract,
# then stop an empty Pick before geometry-only scratch/gather/cache setup.
# No recipe/default, public ABI, selection or lifetime-authority change.
WORLD_EMPTY_PREP01 ?= 0
ifneq ($(WORLD_EMPTY_PREP01),0)
ifneq ($(WORLD_EMPTY_PREP01),1)
$(error WORLD_EMPTY_PREP01 must be 0 or 1)
endif
ifneq ($(SCENERY_CHUNK),1)
$(error WORLD_EMPTY_PREP01 needs SCENERY_CHUNK=1)
endif
ifneq ($(MESH_FASTPATH),1)
$(error WORLD_EMPTY_PREP01 needs MESH_FASTPATH=1)
endif
ifneq ($(MESH_DIRECT),1)
$(error WORLD_EMPTY_PREP01 needs MESH_DIRECT=1)
endif
ifneq ($(PS2_WORLD_MESH),1)
$(error WORLD_EMPTY_PREP01 needs PS2_WORLD_MESH=1)
endif
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_WORLD_EMPTY_PREP01=1
endif
