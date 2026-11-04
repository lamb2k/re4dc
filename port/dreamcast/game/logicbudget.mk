# Lane logicbudget (2026-11-03): non-world frame cost in the heavy rooms. APPROXIMATIONS (CLAUDE.md approximation
# rule), each default 0 = off (nothing is compiled). Gate: gameplay equivalence + look check.
#
# PEN_CLOTH_LOD=N (2..4): pendulum cloth chains (hanging cloth, enemy clothing / hair; not Leon or Ashley) off screen
#   or beyond PEN_CLOTH_LOD_FAR units (default 15000) from the camera step every Nth tick (src/game/pendulum.cpp
#   re4dc_pen_cloth_lod_skip). The wind phase keeps its shared-random draw every tick (same Rnd stream).
PEN_CLOTH_LOD ?= 0
PEN_CLOTH_LOD_FAR ?= 15000
ifneq ($(PEN_CLOTH_LOD),0)
ifneq ($(filter $(PEN_CLOTH_LOD),2 3 4),$(PEN_CLOTH_LOD))
$(error PEN_CLOTH_LOD must be 0 or 2..4 (got $(PEN_CLOTH_LOD)))
endif
$(OBJDIR)/src/game/pendulum.o: GAME_CPPFLAGS += -DRE4DC_PEN_CLOTH_LOD=$(PEN_CLOTH_LOD) -DRE4DC_PEN_CLOTH_LOD_FAR=$(PEN_CLOTH_LOD_FAR)
endif
#
# PARTS_PTR_MEMO=1 (exact while part chains are unchanged): cModel::getPartsPtr resumes a linked chain walk from the
#   last link it returned for the same model (src/game/model.cpp).
PARTS_PTR_MEMO ?= 0
ifeq ($(PARTS_PTR_MEMO),1)
$(OBJDIR)/src/game/model.o: GAME_CPPFLAGS += -DRE4DC_PARTS_PTR_MEMO=1
endif
#
# FX_HAZE_ROOM_INDEX=1 (exact): Ps2fxHazeFor scans only the current room's rows of the PS2 haze table (esp_sub.cpp).
FX_HAZE_ROOM_INDEX ?= 0
ifeq ($(FX_HAZE_ROOM_INDEX),1)
$(OBJDIR)/src/game/esp_sub.o: GAME_CPPFLAGS += -DRE4DC_FX_HAZE_ROOM_INDEX=1
endif
#
# FX_POP_RATE=N (2..4; approximation, render only): the PS2 haze population is rebuilt every Nth tick (esp_sub.cpp).
FX_POP_RATE ?= 0
ifneq ($(FX_POP_RATE),0)
ifneq ($(filter $(FX_POP_RATE),2 3 4),$(FX_POP_RATE))
$(error FX_POP_RATE must be 0 or 2..4 (got $(FX_POP_RATE)))
endif
$(OBJDIR)/src/game/esp_sub.o: GAME_CPPFLAGS += -DRE4DC_FX_POP_RATE=$(FX_POP_RATE)
endif
