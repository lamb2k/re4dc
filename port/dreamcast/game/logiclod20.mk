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
