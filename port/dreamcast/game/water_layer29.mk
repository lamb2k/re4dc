# EF13: versioned source-bound water definitions through the existing PS2
# layer consumer. Only espgen45.cpp selects and loads the definitions; the
# native WaterNode queue/emitter ABI and other water units stay unchanged.
WATER_LAYER29 ?= 0
ifneq ($(words $(WATER_LAYER29)),1)
$(error WATER_LAYER29 must be exactly 0 or 1)
endif
ifeq ($(filter $(WATER_LAYER29),0 1),)
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
endif
