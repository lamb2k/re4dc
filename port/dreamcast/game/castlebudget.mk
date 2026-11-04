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
# ACTOR_PART_FRUSTUM=1 (render only): native actor parts wholly outside the side planes of the view skip all their work
#   (native_actor_fast.cpp pf_hidden: rigid bind sphere; skinned palette-origin box + largest scale bound).
ACTOR_PART_FRUSTUM ?= 0
ifneq ($(filter-out 0 1,$(ACTOR_PART_FRUSTUM)),)
$(error ACTOR_PART_FRUSTUM must be 0 or 1)
endif
ifeq ($(ACTOR_PART_FRUSTUM),1)
$(OBJDIR)/platform/native_actor_fast.o: PLATFORM_CPPFLAGS += -DRE4DC_ACTOR_PART_FRUSTUM=1
endif
# CB_LAYOUT_PAD=N (measurement only, never in a recipe): N bytes of unused code padding in trans.o (layout-noise floor).
CB_LAYOUT_PAD ?= 0
ifneq ($(CB_LAYOUT_PAD),0)
$(OBJDIR)/src/game/trans.o: GAME_CPPFLAGS += -DRE4DC_CB_LAYOUT_PAD=$(CB_LAYOUT_PAD)
endif
