# EF14 render-only, bounded XMTRX batch for the prepared cloth row consumer.
# Include after game30.mk and effects30.mk. Default zero contributes no flags.
CLOTH_XM_BATCH14 ?= 0
ifneq ($(words $(CLOTH_XM_BATCH14)),1)
$(error CLOTH_XM_BATCH14 must be exactly 0 or 1)
endif
ifneq ($(filter-out 0 1,$(CLOTH_XM_BATCH14)),)
$(error CLOTH_XM_BATCH14 must be 0 or 1)
endif
ifeq ($(CLOTH_XM_BATCH14),1)
ifneq ($(CLOTH_SHEET11)$(GAME_SH4ZAM)$(GAME_SH4ZAM_RENDER_ONLY)$(GAME_SH4ZAM_LOGIC),1110)
$(error CLOTH_XM_BATCH14 needs CLOTH_SHEET11=1 GAME_SH4ZAM=1 GAME_SH4ZAM_RENDER_ONLY=1 GAME_SH4ZAM_LOGIC=0)
endif
$(OBJDIR)/src/game/cloth.o: GAME_CPPFLAGS += -DRE4DC_CLOTH_XM_BATCH14=1
$(OBJDIR)/platform/sh4zam_direct.o: KOS_CFLAGS += -DRE4DC_CLOTH_XM_BATCH14=1
endif
