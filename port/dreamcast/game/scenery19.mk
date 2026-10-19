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
# SCENERY_DEDUP=1 (exact, render only; needs SCENERY_CHUNK, MESH_VP_SCHED=1, HW_LEAN): each PS2 world meshlet's corners
# are reordered at room load (repeated grid positions last), and a draw transforms each position once and builds the
# repeats from it. Heap 4: 4 bytes per meshlet + 1 per repeat (r101 ~33 KB), freed with the room's world.
SCENERY_DEDUP ?= 0
# SCENERY_DEDUP=2: the same draw, but the tables are the room file's R4RC 'SCDD' section (scdd_compile.py; data set
# rc19s = rc19 + SCDD): no load-time hashing and no allocation of its own (the room file block, r101 43.9 KB). A room
# without the section, or a section that does not match the package, draws as knob off (SCNDEDUP log line says why).
ifneq ($(SCENERY_DEDUP),0)
ifeq ($(filter 1 2,$(SCENERY_DEDUP)),)
$(error SCENERY_DEDUP must be 0, 1 or 2)
endif
ifeq ($(SCENERY_CHUNK),0)
$(error SCENERY_DEDUP needs SCENERY_CHUNK)
endif
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_SCENERY_DEDUP=$(SCENERY_DEDUP)
endif
# CHUNK_SUBMIT=1: the shared chunk-submit back end (platform/chunk_submit.h / .cpp) for user lanes
# (character-draw-path, rigid models). Default 0: not built.
CHUNK_SUBMIT ?= 0
ifneq ($(CHUNK_SUBMIT),0)
$(OBJDIR)/platform/chunk_submit.o: PLATFORM_CPPFLAGS += -O2 -DRE4DC_CHUNK_SUBMIT=1
endif
