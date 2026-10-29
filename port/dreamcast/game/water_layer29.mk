# EF13: versioned source-bound water definitions through the existing PS2
# layer consumer. read.cpp binds the loaded room member, espgen45.cpp selects
# copied rows, and native_effect.cpp retires the room owner. The native
# WaterNode queue/emitter ABI and other water units stay unchanged.
WATER_LAYER29 ?= 0
ifneq ($(words $(WATER_LAYER29)),1)
$(error WATER_LAYER29 must be exactly 0 or 1)
endif
ifneq ($(filter-out 0 1,$(WATER_LAYER29)),)
$(error WATER_LAYER29 must be exactly 0 or 1)
endif
ifeq ($(WATER_LAYER29),1)
ifneq ($(ROUTE_CH13),1)
$(error WATER_LAYER29 needs ROUTE_CH13=1)
endif
ifneq ($(WATER_PS2),1)
$(error WATER_LAYER29 needs WATER_PS2=1)
endif
$(OBJDIR)/src/game/espgen45.o: GAME_CPPFLAGS += -DRE4DC_WATER_LAYER29=1
$(OBJDIR)/src/game/read.o: GAME_CPPFLAGS += -DRE4DC_WATER_LAYER29=1
$(OBJDIR)/platform/native_effect.o: PLATFORM_CPPFLAGS += -DRE4DC_WATER_LAYER29=1
endif
