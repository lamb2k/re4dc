# D367 charbake (2026-10-10; tools/d367/charbake/README.md): offline character asset options. Every knob defaults
# to 0 and then contributes nothing (identical image).
#   CHARBAKE_HAIR=1    Leon's hair drawn as 2 owned runs, one per hair material, restripified (tools/d367/charbake/
#                      cb_hair.py writes leon_hair_runs_g2.h from the bundle's leon_hair_runs.h), instead of the 14
#                      source-ordered runs: 9 runs per Leon instead of 21 (pl08 10 instead of 22), 2 hair TA headers
#                      instead of 14, 2,131 strip corners instead of 4,317, 11 meshlets instead of 20. The same
#                      triangles, winding, UV words, role 7 palette, bounds and blob flags; coincident triangles keep
#                      their order. Render only: in Flycast about 300 scattered pixels at overlapping hair-card edges
#                      blend in a different order (r100 close-ups, at most 33..49 levels; not visible at 1x), and
#                      Leon's translucent pass costs about half (hw model at 686b550f: -1.5 ms per drawn tick at the
#                      r101 square, -1.4 in the r100 house fight, -0.2 in the r101 fight). CHARBAKE_HAIR_DIR: the
#                      private directory holding leon_hair_runs_g2.h (default COARSE_ACTOR_ASSET_DIR, the play bundle).
#                      Keep it OFF (issue #11, 2026-10-10): on a real console the look test disc (on in every preset)
#                      showed dark notched triangles on the back of Leon's head. Flycast does not show them (same view,
#                      0 vs 1: 74 pixels differ, nothing visible), so the regroup can only be judged on hardware; the
#                      likely cause is the order change across the two hair materials (59 coincident cross-material
#                      pairs no longer adjacent, all of material 2 before material 1). Not in any play recipe.
#   CHARBAKE_TOGGLE=1  test builds: the character texture variants at run time (charbake_variants.h: CUR = the play
#                      textures, AO, SKY, GCB, LVQ = Leon's atlas as VQ, GVQ = GCB with Leon as VQ; coarse_actor.cpp
#                      re4dc_charbake_set / _cycle / _label, which the look toggle's presets call (native_static.cpp,
#                      LOOK_TOGGLE: hold X + press START); DBG_WARP's `charbake <n> [room frame]` sets one at load or
#                      at a frame). The variant packages must be in the disc's tex.pak under their own keys
#                      (charbake.py pak --add). CHARBAKE_VARIANT=<n>: the variant at boot. Render only: AO / SKY / GCB
#                      are the same size and format as the play textures; LVQ / GVQ hold Leon in 66 KB of VRAM.
CHARBAKE_HAIR ?= 0
CHARBAKE_HAIR_DIR ?= $(COARSE_ACTOR_ASSET_DIR)
CHARBAKE_TOGGLE ?= 0
CHARBAKE_VARIANT ?= 0
ifneq ($(filter-out 0 1,$(CHARBAKE_HAIR))$(filter-out 0 1,$(CHARBAKE_TOGGLE)),)
$(error CHARBAKE_HAIR / CHARBAKE_TOGGLE are 0 or 1)
endif
ifeq ($(CHARBAKE_HAIR),1)
ifneq ($(COARSE_LEON)$(ACTOR_TRANSACTION),11)
$(error CHARBAKE_HAIR=1 needs COARSE_LEON=1 ACTOR_TRANSACTION=1 (the owner path draws the hair runs))
endif
ifneq ($(LEON_NATIVE_PIPE),0)
$(error CHARBAKE_HAIR=1 is not proved with LEON_NATIVE_PIPE=1)
endif
$(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -DRE4DC_CHARBAKE_HAIR=1 -I$(CHARBAKE_HAIR_DIR)
$(OBJDIR)/coarse_actor.o: $(CHARBAKE_HAIR_DIR)/leon_hair_runs_g2.h
endif
ifeq ($(CHARBAKE_TOGGLE),1)
ifneq ($(COARSE_LEON)$(COARSE_GANADO_CAST)$(ACTOR_TRANSACTION),111)
$(error CHARBAKE_TOGGLE=1 needs COARSE_LEON=1 COARSE_GANADO_CAST=1 ACTOR_TRANSACTION=1)
endif
$(OBJDIR)/coarse_actor.o $(OBJDIR)/coarse_ganado.o: GAME_CPPFLAGS += -DRE4DC_CHARBAKE_TOGGLE=1 \
	-DRE4DC_CHARBAKE_VARIANT=$(CHARBAKE_VARIANT)
$(OBJDIR)/coarse_actor.o $(OBJDIR)/coarse_ganado.o: charbake_variants.h
$(OBJDIR)/dbgwarp_bridge.o: GAME_CPPFLAGS += -DRE4DC_CHARBAKE_TOGGLE=1
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_CHARBAKE_TOGGLE=1
else
ifneq ($(CHARBAKE_VARIANT),0)
$(error CHARBAKE_VARIANT needs CHARBAKE_TOGGLE=1)
endif
endif
