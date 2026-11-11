# Lane lod31 (2026-11-11; distance levels and part merging for the character path).
# LOD31_COUNT=1 (diagnostic, log only, default 0): LOD31 log lines every 120 frames from native_actor_fast.cpp: actor parts
#   drawn per crowd tier (0 = not a Ganado-family model, 1 near, 2 mid, 3 far) and level, vertices drawn against the
#   level-0 vertices of the same meshlets, parts with no levels (>= 24 triangles / smaller), and for parts that have
#   levels the vertices they would draw if levels were picked at 4 / 8 / 16 px. No draw or game state changes.
LOD31_COUNT ?= 0
ifneq ($(filter-out 0 1,$(LOD31_COUNT)),)
$(error LOD31_COUNT must be 0 or 1)
endif
ifeq ($(LOD31_COUNT),1)
$(OBJDIR)/platform/native_actor_fast.o: PLATFORM_CPPFLAGS += -DRE4DC_LOD31_COUNT=1
endif
