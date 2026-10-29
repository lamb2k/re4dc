# D367 frontend30: memory-copy audit and GC render front-end trimming. Included at the end of
# the Makefile. Every knob defaults to 0 and then contributes nothing (identical image).
#   COPY_LEAN=1   native renderer staging without redundant work: no zero-fill of scratch that
#                 is written before it is read, word copies instead of SH-4 memcpy libcalls in
#                 the GX state stubs, hash-first compares of deferred lighting, one-pass view
#                 diffs, texture-key lookups indexed instead of scanned (same keys), and no
#                 lighting snapshot for deferred scenery parts that are already lit. On SH-4 also:
#                 no eprintf formatting (the debug-text glyphs go to the GXWGFifo sink, never
#                 shown) and the mem_alloc "file(line)" tag written without sprintf (same bytes).
#   FRONT_LEAN=1  skip recovered-game render preparation the native renderers make redundant:
#                 light selection / GX light objects / normal matrix for scenery whose every
#                 drawn info is an already lit native mesh, and the per-frame draw-plan OT walk
#                 when the registration set is unchanged. Render-only (determinism trace gate).
#   MESH_DIRECT=1 native scenery meshes go to the TA through the store queues instead of
#                 packet slab + pvr_prim copy (needs TA_DIRECT=1; pair with NATIVE_ACTOR_DIRECT=1).
#   HW_LEAN=1     pass 2, SH-4 hardware costs Flycast under-charges (hwmodel): 1/w by fsrra(w*w)
#                 instead of fdiv in the scenery transform and the clipper projection (render only).
#   RELEASE_FLAGS=N  debug-disc boot displays off (debug.cpp ConfigSet): 1 heap/process-bar overlay
#                 (Debug_flg[2] 0x40000000), 2 + pad monitor (0x8000), 3 + debug_mode 0.
#   FRONT_NATIVE=1 models drawn with only the GX state the native bridge reads (trans.cpp): no TEV /
#                 tex-gen / specular / vertex-format stub traffic, no specular matrices; same lights,
#                 matrices, texture objects and parts. 2 = source draw + native replay compared per
#                 part (model_bridge.cpp, "front_native:" log). Render only.
COPY_LEAN ?= 0
FRONT_LEAN ?= 0
MESH_DIRECT ?= 0
HW_LEAN ?= 0
RELEASE_FLAGS ?= 0
FRONT_NATIVE ?= 0
# Build34 EF15: a room/SMD TPL publication token for the FRONT_TEXOBJ cache.
# Only affected game TUs receive the switch. The original full descriptor
# comparison remains the path for every unqualified palette pair.
FRONT_TPL_OWNER ?= 0
ifneq ($(words $(FRONT_TPL_OWNER)),1)
$(error FRONT_TPL_OWNER must be exactly 0 or 1)
endif
ifeq ($(filter $(FRONT_TPL_OWNER),0 1),)
$(error FRONT_TPL_OWNER must be 0 or 1)
endif
ifeq ($(FRONT_TPL_OWNER),1)
ifneq ($(FRONT_NATIVE),1)
$(error FRONT_TPL_OWNER=1 requires FRONT_NATIVE=1)
endif
ifneq ($(FRONT_TEXOBJ),1)
$(error FRONT_TPL_OWNER=1 requires FRONT_TEXOBJ=1)
endif
ifneq ($(RESET_RETIRE_BEFORE_HEAPS),1)
$(error FRONT_TPL_OWNER=1 requires RESET_RETIRE_BEFORE_HEAPS=1)
endif
$(OBJDIR)/src/game/trans.o $(OBJDIR)/src/game/model.o $(OBJDIR)/src/game/scroll.o \
  $(OBJDIR)/src/game/read.o $(OBJDIR)/src/game/game.o $(OBJDIR)/src/game/main.o: GAME_CPPFLAGS += -DRE4DC_FRONT_TPL_OWNER=1
endif
# MODEL_PREP_KEEP=1 (perf-20261004 candidate 5; render only, exact; needs FRONT_LEAN=1): FRONT_LEAN's "unchanged
#   registrations" skip of the draw-plan OT walk (model_asset_bridge.cpp) survives pacing and depth order: a pace-skipped
#   tick (no model OT) on an idle plan owner neither walks nor replaces the last drawn walk's signature, and the
#   signature is a multiset of the registrations (OT depth order changes every frame in a fight). Without it the
#   alternating empty/full OTs made every drawn tick re-walk all parts (r100 h-fight: 222 plan lookups + 490 owner
#   scans, ~1.7 hw ms per drawn tick).
MODEL_PREP_KEEP ?= 0
ifeq ($(filter $(MODEL_PREP_KEEP),0 1),)
$(error MODEL_PREP_KEEP must be 0 or 1)
endif
ifeq ($(MODEL_PREP_KEEP),1)
ifneq ($(FRONT_LEAN),1)
$(error MODEL_PREP_KEEP=1 extends FRONT_LEAN=1)
endif
$(OBJDIR)/model_asset_bridge.o: GAME_CPPFLAGS += -DRE4DC_MODEL_PREP_KEEP=1
endif
ifeq ($(MESH_DIRECT),1)
ifneq ($(TA_DIRECT),1)
$(error MESH_DIRECT=1 requires TA_DIRECT=1 (pipeline30 direct TA API))
endif
endif
.PHONY: frontend30-force
$(OBJDIR)/frontend30.h: frontend30-force
	@mkdir -p $(dir $@)
	@printf '#define RE4DC_COPY_LEAN %s\n#define RE4DC_FRONT_LEAN %s\n#define RE4DC_MESH_DIRECT %s\n#define RE4DC_HW_LEAN %s\n#define RE4DC_RELEASE_FLAGS %s\n#define RE4DC_FRONT_NATIVE %s\n' '$(COPY_LEAN)' '$(FRONT_LEAN)' '$(MESH_DIRECT)' '$(HW_LEAN)' '$(RELEASE_FLAGS)' '$(FRONT_NATIVE)' > $@.tmp
	@cmp -s $@.tmp $@ || mv $@.tmp $@
	@rm -f $@.tmp
FRONTEND30_PLATFORM = $(OBJDIR)/native-reuse/pvr_geometry.o $(OBJDIR)/platform/native_static.o \
	$(OBJDIR)/platform/native_ui.o $(OBJDIR)/platform/gx_stub.o $(OBJDIR)/platform/native_draw_plan_owner.o
FRONTEND30_GAME = $(OBJDIR)/model_asset_bridge.o $(OBJDIR)/src/game/trans.o $(OBJDIR)/src/game/eprintf.o $(OBJDIR)/src/game/main_mem.o $(OBJDIR)/src/game/debug.o \
	$(OBJDIR)/model_bridge.o
$(FRONTEND30_PLATFORM) $(FRONTEND30_GAME): $(OBJDIR)/frontend30.h
$(FRONTEND30_PLATFORM): PLATFORM_CPPFLAGS += -include $(OBJDIR)/frontend30.h
$(FRONTEND30_GAME): GAME_CPPFLAGS += -include $(OBJDIR)/frontend30.h
$(OBJDIR)/platform/native_static.o: platform/include/ta_direct.hpp ../room/mesh_fastpath.hpp
