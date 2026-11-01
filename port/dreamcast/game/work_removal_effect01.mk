# Bounded source work removal experiment. Default OFF; no recipe change.
# EFFECT_RECORD_PASS01 keeps EspEstSetSelect's call-local decoded record through
# its immediate EspSeqSet call. Raw/retaining records still pass their original
# archive address. No generator burst cache, timing change, or retained scratch.
EFFECT_RECORD_PASS01 ?= 0
ifneq ("$(EFFECT_RECORD_PASS01)","0")
ifneq ("$(EFFECT_RECORD_PASS01)","1")
$(error EFFECT_RECORD_PASS01 must be exactly 0 or 1)
endif
endif
ifeq ($(EFFECT_RECORD_PASS01),1)
$(OBJDIR)/src/game/esp_sub.o: GAME_CPPFLAGS += -DRE4DC_EFFECT_RECORD_PASS01=1
endif
