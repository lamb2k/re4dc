# fx31.mk (lane fx31 2026-11-11; review answer 2 section 3; default 0 = off, identical image).
# FX_TRANS_SKIP31=1 (render only, exact: no game state read back): EspTrans steps over dead pool slots through the GAME_FX_SCAN
#   live map; the coarse sprite pass rejects dormant FX_MIST_PS2 mist sheets before classifying them, and does not queue a
#   sprite FX_LEVEL=3 Essential always declines (the stateless cuts FxEssentialSetupCut makes after the queue), so it
#   never pays the OT insert, EspCommonTrans's setup, Ps2fxClass and ChannelSet. Needs GAME_FX_SCAN, COARSE_FX_SPRITES.
# FX_DORMANT31=1 (logic, exact): EspMove clears the live-map bit of a dormant world-parented 0x48 sheet (its move() returns at
#   once and it can never be pushed by the move), so later ticks never touch its slot. No new memory: the existing live
#   map holds the state; a pool resync re-marks the slot and the next move clears it again. QA DIAG fx_live then counts
#   awake effects. Needs GAME_FX_SCAN, FX_MIST_PS2.
FX_TRANS_SKIP31 ?= 0
FX_DORMANT31 ?= 0
ifneq ($(FX_TRANS_SKIP31),0)
$(OBJDIR)/src/game/esp.o $(OBJDIR)/src/game/esp_sub.o: GAME_CPPFLAGS += -DRE4DC_FX_TRANS_SKIP31=1
endif
ifneq ($(FX_DORMANT31),0)
$(OBJDIR)/src/game/esp.o: GAME_CPPFLAGS += -DRE4DC_FX_DORMANT31=1
endif
# FX31_STAT=1 (measurement builds only, log only): "fx31:" counter lines every 300 frames (esp.cpp).
FX31_STAT ?= 0
ifneq ($(FX31_STAT),0)
$(OBJDIR)/src/game/esp.o: GAME_CPPFLAGS += -DRE4DC_FX31_STAT=1
endif
# ESP_NUMLIST31=1 (lane all31 2026-11-11; exact, decisions identical): drops esp_num_list (422 B .bss), which only fed the
#   debug page 0xE per-owner text that eprintf never shows on the Dreamcast.
ESP_NUMLIST31 ?= 0
ifneq ($(ESP_NUMLIST31),0)
$(OBJDIR)/src/game/esp.o: GAME_CPPFLAGS += -DRE4DC_ESP_NUMLIST31=1
endif
