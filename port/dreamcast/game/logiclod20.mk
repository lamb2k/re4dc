# Lane logiclod20 (2026-10-20): game-logic level of detail. APPROXIMATIONS (CLAUDE.md approximation rule), each default
# 0 = off (nothing is compiled). Gate: gameplay equivalence (same kills, triggers, doors, waves, room clears, cutscenes).
#
# LOGIC_LOD_EM=N (2..4): far / off-screen Ganados in a walking or idle routine and the farm animals run their whole
#   frame step every Nth tick (src/game/em.cpp re4dc_logic_lod_skip). Far = LOGIC_LOD_FAR units from Leon (default
#   25000, past the 25 m fog); off screen = more than LOGIC_LOD_NEAR units (default 5000) and over 60 degrees off the
#   camera axis. Never with a hit pending or inside an explosion / fire volume.
LOGIC_LOD_EM ?= 0
LOGIC_LOD_FAR ?= 25000
LOGIC_LOD_NEAR ?= 5000
ifneq ($(LOGIC_LOD_EM),0)
ifneq ($(filter $(LOGIC_LOD_EM),2 3 4),$(LOGIC_LOD_EM))
$(error LOGIC_LOD_EM must be 0 or 2..4 (got $(LOGIC_LOD_EM)))
endif
ifneq ($(ANIMAL_FAR_RATE),)
ifneq ($(ANIMAL_FAR_RATE),0)
$(error LOGIC_LOD_EM covers the animals: leave ANIMAL_FAR_RATE at 0)
endif
endif
$(OBJDIR)/src/game/em.o: GAME_CPPFLAGS += -DRE4DC_LOGIC_LOD_EM=$(LOGIC_LOD_EM) -DRE4DC_LOGIC_LOD_FAR=$(LOGIC_LOD_FAR) \
	-DRE4DC_LOGIC_LOD_NEAR=$(LOGIC_LOD_NEAR)
endif
#
# ESP_LOD=N (2..4): world-parented effects off screen (over 3 m from the camera and over 60 degrees off its axis) or
#   beyond ESP_LOD_FAR units from the camera (default 40000) move every Nth tick (src/game/esp.cpp re4dc_esp_lod_skip).
ESP_LOD ?= 0
ESP_LOD_FAR ?= 40000
ifneq ($(ESP_LOD),0)
ifneq ($(filter $(ESP_LOD),2 3 4),$(ESP_LOD))
$(error ESP_LOD must be 0 or 2..4 (got $(ESP_LOD)))
endif
$(OBJDIR)/src/game/esp.o: GAME_CPPFLAGS += -DRE4DC_ESP_LOD=$(ESP_LOD) -DRE4DC_ESP_LOD_FAR=$(ESP_LOD_FAR)
endif
#
# ESP_CENSUS=1 (test only, default 0): "espc:" lines every 120 frames, live effects by id and by owner (esp.cpp EspMove).
ESP_CENSUS ?= 0
ifeq ($(ESP_CENSUS),1)
$(OBJDIR)/src/game/esp.o $(OBJDIR)/src/game/esp_sub.o: GAME_CPPFLAGS += -DRE4DC_ESP_CENSUS=1
endif
#
# ESP_CUT_EARLY=1 (render only, exact; needs HAZE_SPRITE_CUT=1): sprites HAZE_SPRITE_CUT never draws (mist sheets, haze
#   without a PS2 recipe row) leave EspCommonTrans at its start and are not queued by the coarse sprite pass.
ESP_CUT_EARLY ?= 0
ifeq ($(ESP_CUT_EARLY),1)
ifneq ($(HAZE_SPRITE_CUT),1)
$(error ESP_CUT_EARLY=1 needs HAZE_SPRITE_CUT=1)
endif
$(OBJDIR)/src/game/esp_sub.o: GAME_CPPFLAGS += -DRE4DC_ESP_CUT_EARLY=1
endif
#
# ESP_TYPE_CAP=N (render only, visible approximation; 0 = off): at most N effects of one id spawned by an enemy, animal
#   or object (owner 0x10..0xCF) are queued for drawing per EspTrans pass (esp.cpp). Room and Leon effects uncapped.
ESP_TYPE_CAP ?= 0
ifneq ($(ESP_TYPE_CAP),0)
$(OBJDIR)/src/game/esp.o: GAME_CPPFLAGS += -DRE4DC_ESP_TYPE_CAP=$(ESP_TYPE_CAP)
endif
#
# SCN_CENSUS=1 (test only, default 0): "scnc:" lines every 120 frames, scenery meshlets / corners transformed / corners of
#   meshlets with no strip on screen / strips emitted and culled / triangles (platform/native_static.cpp).
SCN_CENSUS ?= 0
ifeq ($(SCN_CENSUS),1)
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_SCN_CENSUS=1
endif
#
