# Lane bodysvc20 (2026-10-20, master plan P3): body services under the original enemy AI. APPROXIMATIONS (CLAUDE.md
# approximation rule), each default 0 = off (nothing is compiled). Gate: gameplay equivalence (same kills, triggers,
# doors, waves, room clears, cutscenes) + a look check where visible. BODY_GRID (service 1) is in engine_preview.mk.
#
# BODY_CORPSE=1: a settled Ganado corpse (Die_Cramp's resting state, position unchanged for BODY_CORPSE_TICKS ticks)
#   skips its whole frame step (src/game/em.cpp re4dc_body_corpse_skip); a pending hit or an explosion / fire volume
#   wakes it.
BODY_CORPSE ?= 0
BODY_CORPSE_TICKS ?= 90
ifeq ($(BODY_CORPSE),1)
$(OBJDIR)/src/game/em.o: GAME_CPPFLAGS += -DRE4DC_BODY_CORPSE=1 -DRE4DC_BODY_CORPSE_TICKS=$(BODY_CORPSE_TICKS)
else ifneq ($(BODY_CORPSE),0)
$(error BODY_CORPSE is 0 or 1)
endif
# BODY_LOG=1 (test arms only, never in a recipe): "bodysvc:" counter lines of the services above.
BODY_LOG ?= 0
ifeq ($(BODY_LOG),1)
$(OBJDIR)/src/game/em.o: GAME_CPPFLAGS += -DRE4DC_BODY_LOG=1
endif
#
# BODY_IK=1 (service 3): no foot IK for a Ganado farther than BODY_IK_FAR units from Leon (default 15000) or more than
#   BODY_IK_NEAR (default 5000) away and off screen (src/em10/em10.cpp cEm10::move). Visible: look check.
BODY_IK ?= 0
BODY_IK_FAR ?= 15000
BODY_IK_NEAR ?= 5000
ifeq ($(BODY_IK),1)
$(OBJDIR)/mod/em10g/shared/src/em10/em10.o: GAME_CPPFLAGS += -DRE4DC_BODY_IK=1 -DRE4DC_BODY_IK_FAR=$(BODY_IK_FAR) \
	-DRE4DC_BODY_IK_NEAR=$(BODY_IK_NEAR)
else ifneq ($(BODY_IK),0)
$(error BODY_IK is 0 or 1)
endif
#
# BODY_ROUTE=1 (service 4): a Ganado farther than BODY_ROUTE_FAR units from Leon (default 12000) refreshes its route
#   queries every 16th tick instead of the source's 8th (src/em10/em10.cpp em10RouteCk).
BODY_ROUTE ?= 0
BODY_ROUTE_FAR ?= 12000
ifeq ($(BODY_ROUTE),1)
$(OBJDIR)/mod/em10g/shared/src/em10/em10.o: GAME_CPPFLAGS += -DRE4DC_BODY_ROUTE=1 -DRE4DC_BODY_ROUTE_FAR=$(BODY_ROUTE_FAR)
else ifneq ($(BODY_ROUTE),0)
$(error BODY_ROUTE is 0 or 1)
endif
