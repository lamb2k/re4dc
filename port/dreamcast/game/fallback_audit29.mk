# Build29 whole-game diagnostics. The DFA prerequisite supplies the existing
# paged QA/immutable multipart link path without changing another knob's block.
# Absent/0 adds no defines or objects. No recipe enables this diagnostic.
FALLBACK_AUDIT29 ?= 0
ifneq ($(words $(FALLBACK_AUDIT29)),1)
$(error FALLBACK_AUDIT29 must be one value, 0 or 1)
endif
ifneq ($(filter-out 0 1,$(FALLBACK_AUDIT29)),)
$(error FALLBACK_AUDIT29 must be 0 or 1)
endif
ifeq ($(FALLBACK_AUDIT29),1)
ifneq ($(QA_MENU)$(DRAW_FALLBACK_AUDIT),11)
$(error FALLBACK_AUDIT29=1 needs QA_MENU=1 DRAW_FALLBACK_AUDIT=1)
endif
ifeq ($(QA_LINK),1)
ifneq ($(QA_LINK_REVIEW28),1)
$(error FALLBACK_AUDIT29=1 with QA_LINK=1 needs QA_LINK_REVIEW28=1 for bounded complete DIAG delivery)
endif
endif
FA29_GAME_OBJS = $(addprefix $(OBJDIR)/src/game/,main.o motion.o atari.o cloth.o esp.o esp_efm.o trans_ot.o) $(OBJDIR)/model_bridge.o
FA29_PLATFORM_OBJS = $(addprefix $(OBJDIR)/platform/,native_actor_fast.o native_motion.o native_ui.o dvd_read_safe.o audio_aica.o audio_strm.o gx_stub.o) $(OBJDIR)/qa_menu.o
$(FA29_GAME_OBJS): GAME_CPPFLAGS += -DRE4DC_FALLBACK_AUDIT29=1
$(FA29_PLATFORM_OBJS): PLATFORM_CPPFLAGS += -DRE4DC_FALLBACK_AUDIT29=1
PLATFORM_OBJS += $(OBJDIR)/fallback_audit29.o
$(TARGET): $(OBJDIR)/fallback_audit29.o
$(OBJDIR)/fallback_audit29.o: fallback_audit29.cpp platform/include/fallback_audit29.h platform/include/fallback_audit29.def
	@mkdir -p $(dir $@)
	kos-c++ $(KOS_CFLAGS) $(PLATFORM_CPPFLAGS) -DRE4DC_FALLBACK_AUDIT29=1 -MMD -MP -c $< -o $@
-include $(OBJDIR)/fallback_audit29.d
endif
