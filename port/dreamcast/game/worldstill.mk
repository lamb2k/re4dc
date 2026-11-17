# WORLD_STILL (lane worlddraw 2026-11-17; default 0 = nothing compiled, image identical).
#   1 = census only: the PS2 world pass logs "WSTILL" every 120 frames: the share of drawn frames whose camera inputs (view,
#       projection, viewport, cull_far, fog, room) equal the previous drawn frame, and the run lengths. Needs NATIVE_FOG=1.
#       Input to the still-camera TA replay design (WORLD-DRAW-PLAN.md of lane worlddraw).
WORLD_STILL ?= 0
ifneq ($(filter $(WORLD_STILL),0 1),$(WORLD_STILL))
$(error WORLD_STILL must be 0 or 1)
endif
ifeq ($(WORLD_STILL),1)
ifneq ($(PS2_WORLD_DRAW)$(NATIVE_FOG),11)
$(error WORLD_STILL=1 needs PS2_WORLD_DRAW=1 NATIVE_FOG=1)
endif
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_WORLD_STILL=1
endif
