# Isolated Leon + complete house A/B/C benchmark. No production recipe enables this.
# Include AFTER bench.mk. Reuses its scenes, resets, logger and timing hooks.
HOUSE_ARENA27 ?= 0
HOUSE_ARENA27_AUTO ?= 0
HOUSE_ARENA27_BEGIN ?= 120
HOUSE_ARENA27_END ?= 300
ifneq ($(words $(HOUSE_ARENA27)),1)
$(error HOUSE_ARENA27 must be one value, 0 or 1)
endif
ifneq ($(filter-out 0 1,$(HOUSE_ARENA27)),)
$(error HOUSE_ARENA27 must be 0 or 1)
endif
ifeq ($(HOUSE_ARENA27),1)
ifneq ($(BENCHMARK)$(TAIL_METER)$(PACE_VMU_GPU),111)
$(error HOUSE_ARENA27=1 needs BENCHMARK=1 TAIL_METER=1 PACE_VMU_GPU=1)
endif
ifneq ($(TA_HASH),4)
$(error HOUSE_ARENA27=1 needs TA_HASH=4, the existing count-only TA meter)
endif
ifneq ($(BENCH_SCENARIO)$(BENCH_CENSUS),00)
$(error HOUSE_ARENA27=1 cannot share BENCH_SCENARIO or BENCH_CENSUS)
endif
ifneq ($(strip $(BENCH_SCENES)),3)
$(error HOUSE_ARENA27=1 needs BENCH_SCENES=3)
endif
ifneq ($(strip $(BENCH_FILES)),)
ifneq ($(BENCH_FILES),3)
$(error HOUSE_ARENA27=1 has exactly three fixture files)
endif
endif
ifneq ($(words $(HOUSE_ARENA27_AUTO)),1)
$(error HOUSE_ARENA27_AUTO must be one value, 0..3)
endif
ifneq ($(filter-out 0 1 2 3,$(HOUSE_ARENA27_AUTO)),)
$(error HOUSE_ARENA27_AUTO is 0 (normal menu), 1 original, 2 simplifiedR4, or 3 baked)
endif
ifneq ($(GAME_TICK_LOG),60)
$(error HOUSE_ARENA27=1 needs GAME_TICK_LOG=60, the existing CPU snapshot window)
endif
# Root-owned renderer filters use the same default-off switch; there is no new timing implementation.
$(OBJDIR)/bench.o $(OBJDIR)/platform/native_static.o $(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_HOUSE_ARENA27=1
$(OBJDIR)/src/game/trans.o $(OBJDIR)/coarse.o $(OBJDIR)/model_bridge.o: GAME_CPPFLAGS += -DRE4DC_HOUSE_ARENA27=1
$(OBJDIR)/bench.o: PLATFORM_CPPFLAGS += -DRE4DC_HOUSE_ARENA27_AUTO=$(HOUSE_ARENA27_AUTO) -DRE4DC_HOUSE_ARENA27_BEGIN=$(HOUSE_ARENA27_BEGIN) -DRE4DC_HOUSE_ARENA27_END=$(HOUSE_ARENA27_END) '-DRE4DC_BENCH_NAME="HOUSE ARENA A/B/C"' '-DRE4DC_BENCH_MENU="X: ORIGINAL ONLY  Y: SIMPLIFIED R4  B: BAKED"'
endif
