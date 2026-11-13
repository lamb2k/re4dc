# Bounded source work removal experiments. Both default OFF; no recipe change.
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

# ESP1B_EDGE_REUSE01 reuses the existing quad's two right corners as the next
# cell's two left corners. Source coordinate additions, order and outcomes stay
# unchanged. No additional row/cache allocation or material/budget batching.
ESP1B_EDGE_REUSE01 ?= 0
ifneq ("$(ESP1B_EDGE_REUSE01)","0")
ifneq ("$(ESP1B_EDGE_REUSE01)","1")
$(error ESP1B_EDGE_REUSE01 must be exactly 0 or 1)
endif
endif
ifeq ($(ESP1B_EDGE_REUSE01),1)
ifneq ($(ESP1B_GRID03),1)
$(error ESP1B_EDGE_REUSE01 needs ESP1B_GRID03=1 EFFECT_UV12=1 NATIVE_DRAW_OUTCOMES=1)
endif
ifneq ($(EFFECT_UV12),1)
$(error ESP1B_EDGE_REUSE01 needs ESP1B_GRID03=1 EFFECT_UV12=1 NATIVE_DRAW_OUTCOMES=1)
endif
ifneq ($(NATIVE_DRAW_OUTCOMES),1)
$(error ESP1B_EDGE_REUSE01 needs ESP1B_GRID03=1 EFFECT_UV12=1 NATIVE_DRAW_OUTCOMES=1)
endif
$(OBJDIR)/src/game/esp_sub.o: GAME_CPPFLAGS += -DRE4DC_ESP1B_EDGE_REUSE01=1
endif
