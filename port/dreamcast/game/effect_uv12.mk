# EF12: source GX 2x4 texture matrix on the consumed Esp01/Esp02 strip adapter.
# Render only; default 0 compiles no new code and does not change source state.
EFFECT_UV12 ?= 0
ifneq ($(EFFECT_UV12),0)
ifneq ($(EFFECT_UV12),1)
$(error EFFECT_UV12 must be exactly 0 or 1)
endif
endif
ifeq ($(EFFECT_UV12),1)
ifneq ($(FX_STRIP21)$(NATIVE_DRAW_OUTCOMES)$(EFFECT_SPRITES),111)
$(error EFFECT_UV12 needs FX_STRIP21=1 NATIVE_DRAW_OUTCOMES=1 EFFECT_SPRITES=1)
endif
$(OBJDIR)/src/game/esp_sub.o: GAME_CPPFLAGS += -DRE4DC_EFFECT_UV12=1
endif
