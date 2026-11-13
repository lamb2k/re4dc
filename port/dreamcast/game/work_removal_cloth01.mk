# Public cloth normal-work spike. Default OFF; not a release enable.
# Native cloth does not consume pNor. Only Esp4e's existing normal update is
# deferred, and the unchanged calcNormal runs before allowed GX fallback.
CLOTH_NORMALS_DEFER01 ?= 0
ifneq ($(CLOTH_NORMALS_DEFER01),0)
ifneq ($(CLOTH_NORMALS_DEFER01),1)
$(error CLOTH_NORMALS_DEFER01 must be 0 or 1)
endif
endif
ifneq ($(CLOTH_NORMALS_DEFER01),0)
ifneq ($(CLOTH_NATIVE),1)
$(error CLOTH_NORMALS_DEFER01 needs CLOTH_NATIVE=1)
endif
ifneq ($(NATIVE_DRAW_OUTCOMES),1)
$(error CLOTH_NORMALS_DEFER01 needs NATIVE_DRAW_OUTCOMES=1)
endif
$(OBJDIR)/src/game/cloth.o $(OBJDIR)/src/game/esp4e.o: GAME_CPPFLAGS += -DRE4DC_CLOTH_NORMALS_DEFER01=1
endif
