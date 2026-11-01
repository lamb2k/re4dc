# call26 (lane call26, GitHub #60 item 1: radio calls slower than play on console).
# CALL26_DIAG=1 (diagnostic only, default 0): per-info census of the source model parts drawn while the sub screen
# is open ("CALL26 ..." lines every 300 frames).
CALL26_DIAG ?= 0
ifneq ($(filter $(CALL26_DIAG),0 1),$(CALL26_DIAG))
$(error CALL26_DIAG must be 0 or 1)
endif
ifeq ($(CALL26_DIAG),1)
$(OBJDIR)/model_bridge.o: GAME_CPPFLAGS += -DRE4DC_CALL26_DIAG=1
endif

# PACE_CALL26=1 (lane call26, 2026-11-01; default 0: no effect; render pacing only, logic ticks unchanged): the radio
# call (sub screen type 0x20, the codec) joins frame pacing once its area is swapped in. Without it the pacer stands
# down for every sub screen (pace.cpp context_ok), so a call frame over 2 fields slows the whole call (voice text,
# lips, timers) while play holds 100% speed by dropping images. With it a late call tick drops its image like play
# does: the tick runs in full, its Render / model trans / id + message builds are skipped (PACE_TRANS_SKIP), so the
# portraits' skinning and draw are not paid on a dropped tick. Menus, the map and the other sub screens keep the
# old behaviour. Needs PACE_CATCHUP >= 1 and SUBSCREEN=1.
PACE_CALL26 ?= 0
ifneq ($(filter $(PACE_CALL26),0 1),$(PACE_CALL26))
$(error PACE_CALL26 must be 0 or 1)
endif
ifeq ($(PACE_CALL26),1)
ifeq ($(filter $(PACE_CATCHUP),1 2),)
$(error PACE_CALL26=1 needs PACE_CATCHUP=1 or 2)
endif
ifneq ($(SUBSCREEN),1)
$(error PACE_CALL26=1 needs SUBSCREEN=1)
endif
$(OBJDIR)/pace.o $(OBJDIR)/sscrn_bridge.o: GAME_CPPFLAGS += -DRE4DC_PACE_CALL26=1
endif
