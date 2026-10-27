# Private, r101-only visual reconstruction experiment. No recipe enables this.
WORLD_REBUILD27 ?= 0
WORLD_REBUILD27_DIR ?=
ifneq ($(words $(WORLD_REBUILD27)),1)
$(error WORLD_REBUILD27 must be one value, 0 or 1)
endif
ifneq ($(filter-out 0 1,$(WORLD_REBUILD27)),)
$(error WORLD_REBUILD27 must be 0 or 1)
endif
ifeq ($(WORLD_REBUILD27),1)
ifneq ($(WORLD_RECT21)$(SCENERY_N256)$(WORLD_SG26),111)
$(error WORLD_REBUILD27=1 requires WORLD_RECT21=1 SCENERY_N256=1 WORLD_SG26=1)
endif
ifneq ($(words $(WORLD_REBUILD27_DIR)),1)
$(error WORLD_REBUILD27=1 requires one private certificate directory without spaces)
endif
ifeq ($(wildcard $(WORLD_REBUILD27_DIR)/world_rebuild27_certificates.inc),)
$(error Missing private world_rebuild27_certificates.inc)
endif
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_WORLD_REBUILD27=1 -I$(WORLD_REBUILD27_DIR)
endif

# Separate bounded setup control: omit only r101 parts empty at EVERY LOD.
WORLD_REBUILD27_LIVE_MASK ?= 0
ifneq ($(words $(WORLD_REBUILD27_LIVE_MASK)),1)
$(error WORLD_REBUILD27_LIVE_MASK must be one value, 0 or 1)
endif
ifneq ($(filter-out 0 1,$(WORLD_REBUILD27_LIVE_MASK)),)
$(error WORLD_REBUILD27_LIVE_MASK must be 0 or 1)
endif
ifeq ($(WORLD_REBUILD27_LIVE_MASK),1)
ifneq ($(WORLD_REBUILD27),1)
$(error WORLD_REBUILD27_LIVE_MASK=1 requires WORLD_REBUILD27=1)
endif
ifneq ($(PS2_PASS_MASK),1)
$(error WORLD_REBUILD27_LIVE_MASK=1 requires PS2_PASS_MASK=1)
endif
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_WORLD_REBUILD27_LIVE_MASK=1
endif

# Separate PS2-only baked-detail house control. Private data, never a recipe default.
WORLD_REBUILD27_BAKE ?= 0
ifneq ($(words $(WORLD_REBUILD27_BAKE)),1)
$(error WORLD_REBUILD27_BAKE must be one value, 0 or 1)
endif
ifneq ($(filter-out 0 1,$(WORLD_REBUILD27_BAKE)),)
$(error WORLD_REBUILD27_BAKE must be 0 or 1)
endif
ifeq ($(WORLD_REBUILD27_BAKE),1)
ifneq ($(WORLD_REBUILD27)$(SCENERY_CHUNK)$(SCENERY_SELECT_ONLY)$(SCENERY_REPLAY_LEAN)$(PS2_PRELOAD_LEAN),11111)
$(error WORLD_REBUILD27_BAKE needs WORLD_REBUILD27, SCENERY_CHUNK, SCENERY_SELECT_ONLY, SCENERY_REPLAY_LEAN and PS2_PRELOAD_LEAN)
endif
ifneq ($(PS2_PVS)$(SCENERY_RECORD_SPLIT)$(SCENERY_DEDUP),000)
$(error WORLD_REBUILD27_BAKE has not qualified alternate selection paths)
endif
ifeq ($(wildcard $(WORLD_REBUILD27_DIR)/world_rebuild27_bake_certificates.inc),)
$(error Missing private world_rebuild27_bake_certificates.inc)
endif
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_WORLD_REBUILD27_BAKE=1
endif
