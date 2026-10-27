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
