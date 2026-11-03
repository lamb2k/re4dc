# Lane bakeall (2026-11-02, render only, default 0; user "it should hit every object we can").
# WORLD_BAKE=1: the bake set's rooms (re4-assets-private bakeall data set, tools/d367/bakeall: every PS2 world row no
#   code, effect, light or module can address merged into one world-space mesh per room, parts by material, 3 m
#   clusters, the release's 64-vertex meshlets) take their swapped WORLD_RECT21 certificate rows
#   (texture_rect21/provenance_certificates_bake.inc, same table size, compile-time check against the base table).
#   The knob and the data set go together (either alone: the bake rooms lose their certified ids / r4tc / room file).
#   Not with SCENERY_N256=1 (the bake set is built on the 64-vertex lineage the release ships).
# WORLD_BAKE=2 (lane lod27, 2026-11-03): the lod27 set instead (no merge: the room recipe's own placements and
#   instancing, LOD clusters 3 m / min gain 0.8 / floor 60; r119 r10e r103; tools/d367/lod27), certificate rows from
#   texture_rect21/provenance_certificates_lod27.inc. Goes with data set lod27.
# WORLD_BAKE=3 (lane roomscan, 2026-11-03, user look call "halving the detail of expensive rooms"): the scan1 set
#   (tools/d367/roomscan plans: coarser LOD levels plus per-cell distance caps, levels 1/2/3 from 8/12/16 m; r10e r107
#   r11d r111 r119 r108 r117 r109 r11e r103), rows from texture_rect21/provenance_certificates_scan1.inc. Data set scan1.
WORLD_BAKE ?= 0
ifneq ($(filter-out 0 1 2 3,$(WORLD_BAKE)),)
$(error WORLD_BAKE must be 0, 1, 2 or 3)
endif
ifneq ($(WORLD_BAKE),0)
ifeq ($(SCENERY_N256),1)
$(error WORLD_BAKE swaps rows of the base (64-vertex) certificate table: not with SCENERY_N256=1)
endif
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_WORLD_BAKE=$(WORLD_BAKE)
endif
# DYN_ID_TRACE=1 (lane bakeall 11-03, diagnostic only, default 0): log the first frame each scroll-bound PS2 world id is
#   hidden / moved / drawn from its source (PS2DYN id=..), the static proof for a bake candidate row.
DYN_ID_TRACE ?= 0
ifeq ($(DYN_ID_TRACE),1)
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_DYN_ID_TRACE=1
endif
