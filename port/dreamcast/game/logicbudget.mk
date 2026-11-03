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
