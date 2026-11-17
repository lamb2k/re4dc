# Lane partsetup31 (2026-11-11): character per-part setup. Included by the Makefile after actorplan.mk. Every knob
# defaults to 0: nothing is compiled and the image is byte-identical with or without this file.
#
# PS31_CENSUS=1 (diagnostic builds only): "PS31A" lines (re4dc_actor_submit's own path per 120 source frames: parts by
#   Frame mode, Frames prepared, skinned palette entries, meshlets, vertices, lit parts, runs of one info's parts) and
#   "PS31P" lines (trans.cpp: lazy weight palettes resolved, and how many repeat a (model, weight table, count) already
#   resolved this frame).
PS31_CENSUS ?= 0
ifeq ($(filter $(PS31_CENSUS),0 1),)
$(error PS31_CENSUS must be 0 or 1)
endif
ifneq ($(PS31_CENSUS),0)
$(OBJDIR)/platform/native_actor_fast.o: PLATFORM_CPPFLAGS += -DRE4DC_PS31_CENSUS=1
$(OBJDIR)/src/game/trans.o: GAME_CPPFLAGS += -DRE4DC_PS31_CENSUS=1
endif

# PS31_SKIN_MEMO=1 (render only, exact; default 0): the skin registry's lazy lookups (find_skin(info, no arrays) and
#   re4dc_actor_owned_source) answer from a two-entry memo of the scan while the registry is unchanged (a generation
#   moved by every registry write: register, owned_skin_clear, owned_skin_invalidate_frames). A lazily skinned part
#   (the r103 farm props: ~110 parts a picture at p103h) asked the same question four to six times per draw, each a
#   linear scan of up to 112 entries; the owner source scan read the whole table for every prop (console p103h:
#   0.98 ms a picture in one source line, plus find_skin and the inlined lazy_skin scans).
#   =2 (compare build): every lookup also scans and the scan decides; "PS31M ... bad=" counts memo answers that
#   differed (must stay 0). Registry (ACTOR_SKIN_OWNER_POOL=0) builds without SKIN_RECIPE32 / SKIN_ADMISSION32 /
#   ACTOR_SKIN_RESERVE (their writers are not counted), with ACTOR_TRANSACTION=1. 32 bytes of .bss.
PS31_SKIN_MEMO ?= 0
ifeq ($(filter $(PS31_SKIN_MEMO),0 1 2),)
$(error PS31_SKIN_MEMO must be 0, 1 or 2)
endif
ifneq ($(PS31_SKIN_MEMO),0)
ifneq ($(ACTOR_TRANSACTION),1)
$(error PS31_SKIN_MEMO needs ACTOR_TRANSACTION=1)
endif
ifneq ($(filter-out 0,$(ACTOR_SKIN_OWNER_POOL) $(SKIN_RECIPE32) $(SKIN_ADMISSION32) $(ACTOR_SKIN_RESERVE)),)
$(error PS31_SKIN_MEMO covers the registry build only (ACTOR_SKIN_OWNER_POOL, SKIN_RECIPE32, SKIN_ADMISSION32, ACTOR_SKIN_RESERVE = 0))
endif
$(OBJDIR)/platform/native_actor_fast.o: PLATFORM_CPPFLAGS += -DRE4DC_PS31_SKIN_MEMO=$(PS31_SKIN_MEMO)
endif

# PS31_GATE_MAT=1 (render only, exact; default 0; needs PROP_GATE=1 and SKIN_PALETTE_LAZY=1): PROP_GATE's model bound
#   already computes every parts matrix exactly as calcWeightMat does (same inverse and two concatenations per part, same
#   order); it now writes them where calcWeightMat does (pG->mtxPalette) and sets SKIN_PALETTE_LAZY's memo to the model,
#   so a kept farm prop's palette resolves in the same render call do not run calcWeightMat a second time.
#   =2 (compare build): calcWeightMat runs anyway after the gate and every word is compared ("PS31G ... bad=0").
PS31_GATE_MAT ?= 0
ifeq ($(filter $(PS31_GATE_MAT),0 1 2),)
$(error PS31_GATE_MAT must be 0, 1 or 2)
endif
ifneq ($(PS31_GATE_MAT),0)
ifneq ($(PROP_GATE)$(SKIN_PALETTE_LAZY),11)
$(error PS31_GATE_MAT needs PROP_GATE=1 and SKIN_PALETTE_LAZY=1)
endif
$(OBJDIR)/src/game/trans.o: GAME_CPPFLAGS += -DRE4DC_PS31_GATE_MAT=$(PS31_GATE_MAT)
endif
