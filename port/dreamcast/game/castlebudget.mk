# castlebudget.mk (lane castlebudget 2026-11-04): castle frame-cost switches, each default 0 (no effect).
# CASTLE_ACTOR_PREGATE=1 (render only): ot_type 5 enemies (castle zealots em2d, Verdugo) outside the view frustum or past
#   the fogged view far skip their OT entry, skin and submit (src/game/trans.cpp castleActorPregateHidden).
CASTLE_ACTOR_PREGATE ?= 0
ifneq ($(filter-out 0 1,$(CASTLE_ACTOR_PREGATE)),)
$(error CASTLE_ACTOR_PREGATE must be 0 or 1)
endif
ifeq ($(CASTLE_ACTOR_PREGATE),1)
$(OBJDIR)/src/game/trans.o: GAME_CPPFLAGS += -DRE4DC_CASTLE_ACTOR_PREGATE=1
endif
# PEN_CLOTH_LOD_SUB=1 (approximation, needs PEN_CLOTH_LOD 2..4): Ashley's cloth chains follow PEN_CLOTH_LOD's
#   off-screen / far rule too (src/game/pendulum.cpp re4dc_pen_cloth_lod_skip). Leon stays exact.
PEN_CLOTH_LOD_SUB ?= 0
ifneq ($(filter-out 0 1,$(PEN_CLOTH_LOD_SUB)),)
$(error PEN_CLOTH_LOD_SUB must be 0 or 1)
endif
ifeq ($(PEN_CLOTH_LOD_SUB),1)
ifeq ($(filter 2 3 4,$(PEN_CLOTH_LOD)),)
$(error PEN_CLOTH_LOD_SUB=1 needs PEN_CLOTH_LOD=2..4)
endif
$(OBJDIR)/src/game/pendulum.o: GAME_CPPFLAGS += -DRE4DC_PEN_CLOTH_LOD_SUB=1
endif
