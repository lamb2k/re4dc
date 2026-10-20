# Lane rigid20 (props-new-path, P2; RIGID20-STATUS.md). Default 0: no code, image unchanged.
# RIGID_CENSUS=1 (diagnostic only, never in a recipe): rigid (unskinned) native actor parts are not drawn, and an RGC
# line every 600 frames counts them (parts, meshlets, vertices). A/B against the same build without it = their cost.
# RIGID_CENSUS=2 (benchmark census discs only, lane cache20): rigid parts are counted every frame and hidden only while the
# run-time switch re4dc_rigid_hide is set (warp line `rigid <frame> off|on`, BENCH_CENSUS=1).
RIGID_CENSUS ?= 0
ifneq ($(filter-out 0 1 2,$(RIGID_CENSUS)),)
$(error RIGID_CENSUS is 0, 1 or 2)
endif
ifneq ($(RIGID_CENSUS),0)
$(OBJDIR)/platform/native_actor_fast.o: PLATFORM_CPPFLAGS += -DRE4DC_RIGID_CENSUS=$(RIGID_CENSUS)
endif
# RIGID_CHUNK=1 (render only, approximation; needs CHUNK_SUBMIT=1 and NATIVE_ACTOR_DIRECT=1): rigid models (unskinned
# native actor parts: trucks, carts, doors, boats, breakables, weapons, cObj props) take their own path
# (platform/native_actor_rigid.inc): one object matrix per part, a screen-size rule from the bind sphere (below
# RIGID_CULL_PX pixels not drawn; below RIGID_FLAT_PX one light colour per part + the coarsest LOD level), and strips
# through the shared chunk-submit back end (chunk_submit.h v1.1 direct vertices), as the PS2 world scenery.
RIGID_CHUNK ?= 0
RIGID_CULL_PX ?= 0.75f
RIGID_FLAT_PX ?= 12.0f
ifneq ($(RIGID_CHUNK),0)
ifneq ($(RIGID_CHUNK),1)
$(error RIGID_CHUNK must be 0 or 1)
endif
ifneq ($(CHUNK_SUBMIT),1)
$(error RIGID_CHUNK=1 needs CHUNK_SUBMIT=1 (the shared back end, scenery19.mk))
endif
$(OBJDIR)/platform/native_actor_fast.o: PLATFORM_CPPFLAGS += -DRE4DC_RIGID_CHUNK=1 -DRE4DC_RIGID_CULL_PX=$(RIGID_CULL_PX) -DRE4DC_RIGID_FLAT_PX=$(RIGID_FLAT_PX)
endif
