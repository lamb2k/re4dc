# Optional cause/evidence rows for the existing census. No production enable.
WORLD_CENSUS24_ERRORS ?= 0
ifneq ($(words $(WORLD_CENSUS24_ERRORS)),1)
$(error WORLD_CENSUS24_ERRORS must be one value, 0 or 1)
endif
ifneq ($(filter-out 0 1,$(WORLD_CENSUS24_ERRORS)),)
$(error WORLD_CENSUS24_ERRORS must be 0 or 1)
endif
ifeq ($(WORLD_CENSUS24_ERRORS),1)
ifneq ($(WORLD_CENSUS24),1)
$(error WORLD_CENSUS24_ERRORS=1 needs WORLD_CENSUS24=1)
endif
$(OBJDIR)/world_census24.o $(OBJDIR)/platform/native_static.o $(OBJDIR)/platform/native_ps2_world.o: PLATFORM_CPPFLAGS += -DRE4DC_WORLD_CENSUS24_ERRORS=1
$(OBJDIR)/world_census24.o: platform/include/world_census24_errors.inc
endif
