# census30.mk - CENSUS30 (lane perf30-census 2026-11-10; diagnostic, measurement builds only, log only; default 0 =
#   no code, identical image). Sizes the 30 fps plan's Phase 1 items (PERF-PLAN-30FPS-20261110.md) on Flycast: per tick,
#   effects live / moved versus drawn with the draw cut that stopped each live effect (ESP_TYPE_CAP, HAZE_SPRITE_CUT,
#   FX_LEVEL=3 Essential, FX_TRIM, FX_LEVEL, FX_PS2_NONE_CUT), and skeleton world passes (cModel::partsWorldCalc), repeats,
#   MotionMove, IK, pen cloth and Cloth::move per actor, split by whether the tick's picture was drawn or dropped by the
#   pacer. getPartsPtr / partsWorldCalc callers by return address. census30.cpp; hooks are same-line C30_* macros
#   (include/census30.h, from include/types.h). Every CENSUS30_WIN ticks: c30w / c30e / c30o / c30s / c30r lines
#   (tools/d367/perf30/census30.py).
CENSUS30 ?= 0
CENSUS30_WIN ?= 300
ifneq ($(filter-out 0 1,$(CENSUS30)),)
$(error CENSUS30 is 0 or 1)
endif
ifneq ($(CENSUS30),0)
PLATFORM_OBJS += $(OBJDIR)/census30.o
$(OBJDIR)/census30.o: census30.cpp
	@mkdir -p $(dir $@)
	kos-c++ $(KOS_CFLAGS) $(GAME_CPPFLAGS) -DRE4DC_CENSUS30=1 -DRE4DC_CENSUS30_WIN=$(CENSUS30_WIN) -MMD -MP -c $< -o $@
$(OBJDIR)/src/game/main.o $(OBJDIR)/src/game/em.o $(OBJDIR)/src/game/model.o $(OBJDIR)/src/game/motion.o $(OBJDIR)/src/game/pendulum.o $(OBJDIR)/src/game/cloth.o $(OBJDIR)/src/game/esp.o $(OBJDIR)/src/game/esp_sub.o: GAME_CPPFLAGS += -DRE4DC_CENSUS30=1
$(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_CENSUS30=1
endif
