# Build35 diagnostics. Both controls default0 and add no definitions/objects
# when disabled. Existing audit dependencies remain explicit; no recipe changes.
FALLBACK_AUDIT35 ?= 0
FALLBACK_WINDOW35 ?= 0
ifneq ($(words $(FALLBACK_AUDIT35)),1)
$(error FALLBACK_AUDIT35 must be one value, 0 or 1)
endif
ifneq ($(filter-out 0 1,$(FALLBACK_AUDIT35)),)
$(error FALLBACK_AUDIT35 must be 0 or 1)
endif
FW35_VALUES := 0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 \
               17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 \
               33 34 35 36 37 38 39 40 41 42 43 44 45 46 47 48 \
               49 50 51 52 53 54 55 56 57 58 59 60 61 62 63 64
ifneq ($(words $(FALLBACK_WINDOW35)),1)
$(error FALLBACK_WINDOW35 must be one integer, 0 through 64)
endif
ifneq ($(filter-out $(FW35_VALUES),$(FALLBACK_WINDOW35)),)
$(error FALLBACK_WINDOW35 must be 0 through 64)
endif
ifneq ($(filter-out 0,$(FALLBACK_AUDIT35) $(FALLBACK_WINDOW35)),)
ifneq ($(QA_MENU)$(DRAW_FALLBACK_AUDIT)$(FALLBACK_AUDIT29),111)
$(error Build35 diagnostics need QA_MENU=1 DRAW_FALLBACK_AUDIT=1 FALLBACK_AUDIT29=1)
endif
endif

ifeq ($(FALLBACK_AUDIT35),1)
FA35_GAME_OBJS := $(addprefix $(OBJDIR)/src/game/,cloth.o pendulum.o trans.o espgen.o est.o at_mod.o)
FA35_PLATFORM_OBJS := $(OBJDIR)/platform/native_motion.o
# Every FA29 header consumer must agree on the appended reason registry and
# Snapshot layout, including consumers with no newly instrumented call sites.
$(sort $(FA29_GAME_OBJS) $(FA35_GAME_OBJS)): GAME_CPPFLAGS += -DRE4DC_FALLBACK_AUDIT35=1
$(sort $(FA29_PLATFORM_OBJS) $(FA35_PLATFORM_OBJS) $(OBJDIR)/draw_fallback_audit.o $(OBJDIR)/fallback_audit29.o $(OBJDIR)/fallback_window35.o): PLATFORM_CPPFLAGS += -DRE4DC_FALLBACK_AUDIT35=1
endif

ifneq ($(FALLBACK_WINDOW35),0)
FW35_PLATFORM_OBJS := $(OBJDIR)/draw_fallback_audit.o $(OBJDIR)/fallback_audit29.o $(OBJDIR)/fallback_window35.o $(OBJDIR)/qa_menu.o
$(FW35_PLATFORM_OBJS): PLATFORM_CPPFLAGS += -DRE4DC_FALLBACK_WINDOW35=$(FALLBACK_WINDOW35)
PLATFORM_OBJS += $(OBJDIR)/fallback_window35.o
$(TARGET): $(OBJDIR)/fallback_window35.o
$(OBJDIR)/fallback_window35.o: fallback_window35.cpp platform/include/fallback_window35.h platform/include/fallback_window35_core.hpp platform/include/fallback_audit29.h platform/include/fallback_audit29.def platform/include/fallback_audit35.def platform/include/draw_fallback_audit.h
	@mkdir -p $(dir $@)
	kos-c++ $(KOS_CFLAGS) $(PLATFORM_CPPFLAGS) -MMD -MP -c $< -o $@
-include $(OBJDIR)/fallback_window35.d
endif
