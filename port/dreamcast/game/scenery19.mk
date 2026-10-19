# Lane scenery19 (scenery redesign, P2; SCENERY19-STATUS.md). Default 0: no code, image unchanged.
# SCENERY_CHUNK=1 (exact, render only; needs PS2_WORLD_LEAN, PS2_STRIP_GROUPS, MESH_STRIP_LEAN=1, MESH_VP_SCHED=1):
# the PS2 world's per-part draw (native_static.cpp MeshDraw run / clusters / meshlets / strip groups) runs as one
# chunk walker compiled at -O2 with the knob-off expressions for every decision that changes pixels (far rejection,
# LOD), and, when the room has an R4RC 'SCNK' section, each repeated corner position is transformed once.
SCENERY_CHUNK ?= 0
ifneq ($(SCENERY_CHUNK),0)
ifeq ($(filter 1 2,$(SCENERY_CHUNK)),)
$(error SCENERY_CHUNK must be 0, 1 or 2)
endif
ifneq ($(PS2_STRIP_GROUPS),1)
$(error SCENERY_CHUNK needs PS2_STRIP_GROUPS=1)
endif
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_SCENERY_CHUNK=$(SCENERY_CHUNK)
endif
