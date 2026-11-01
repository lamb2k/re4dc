# Lane worldopt26 (2026-10-26, render only, default 0; user 10-26 "yes extend the strip").
# WORLD_SG26=1: data set wsg26 (re4-assets-private/wsg26-20261026): spatial strip groups for every 256-vertex meshlet
#   route room (tools/ps2_strip_groups.py default mode, 4 groups: the opaque / punch strips of a meshlet split into four
#   spatial groups, corners renumbered by first use in group order; translucent strips keep their order). Same mesh
#   bytes, strips (as triangles), bounds, placements, parts and R4PW: only the corner order and so the mesh crc change,
#   so the knob swaps those rooms' WORLD_RECT21 certificate rows (texture_rect21/provenance_certificates_sg26.inc, same
#   table size, compile-time check against the n256 table). r101 is already spatial (unchanged); r103 gains groups.
#   The knob and wsg26 go together (either alone: the rooms lose their certified ids / r4tc / area tables).
# WORLD_SG_CELL=1: the interior cell cull per strip group (platform/include/worldopt26_sg_cell.inc): a meshlet of a
#   placement under PS2_INTERIOR_CULL drops the strip groups hidden from the eye's cell or outside the frustum before
#   the transform (the 64-vertex meshlets were culled piece by piece; n256 boxes reach through the house walls).
WORLD_SG26 ?= 0
WORLD_SG_CELL ?= 0
ifneq ($(filter-out 0 1,$(WORLD_SG26)),)
$(error WORLD_SG26 must be 0 or 1)
endif
ifneq ($(filter-out 0 1,$(WORLD_SG_CELL)),)
$(error WORLD_SG_CELL must be 0 or 1)
endif
ifeq ($(WORLD_SG26),1)
ifneq ($(SCENERY_N256),1)
$(error WORLD_SG26=1 needs SCENERY_N256=1 (it swaps n256 certificate rows))
endif
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_WORLD_SG26=1
endif
ifeq ($(WORLD_SG_CELL),1)
ifneq ($(PS2_STRIP_GROUPS),1)
$(error WORLD_SG_CELL=1 needs PS2_STRIP_GROUPS=1)
endif
ifeq ($(PS2_INTERIOR_CULL),0)
$(error WORLD_SG_CELL=1 needs PS2_INTERIOR_CULL)
endif
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_WORLD_SG_CELL=1
else
# the hook macro on the strip-group line expands to nothing (no line moves in native_static.cpp)
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_WO26_SG_CELL=
endif
