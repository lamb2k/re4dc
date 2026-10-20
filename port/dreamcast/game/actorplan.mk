# Lane actorplan17 (2026-10-16): the character draw plan (CPU-SAVINGS-PLAN-20261015.md step 2) and its profiler.
# Included by the Makefile after native_model_registry.mk. Every knob defaults to 0: nothing is compiled and the image is
# byte-identical with or without this file. Doc: docs/lanes/actorplan17.md.
#
# ACTOR_PROF=1 (diagnostic builds only, never a play image): SH-4 cycle counts (PRFC0) of the owned character path per
#   class (Leon, Ganado, other) and phase (plan, semantics, crowd, acquire, palettes, preflights, pass checks, submit,
#   one_chunk with positions / lights / pack, the PS2 world flush it triggers), "APROF" lines every 300 source frames
#   (platform/include/actor_prof.h). The counter reads cost a few hundred cycles per call: compare two ACTOR_PROF arms.
ACTOR_PROF ?= 0
ifeq ($(filter $(ACTOR_PROF),0 1),)
$(error ACTOR_PROF must be 0 or 1)
endif
ifneq ($(ACTOR_PROF),0)
ifneq ($(ACTOR_TRANSACTION),1)
$(error ACTOR_PROF times the ACTOR_TRANSACTION owner path (ACTOR_TRANSACTION=1))
endif
ifneq ($(NATIVE_MODEL_REGISTRY),1)
$(error ACTOR_PROF instruments the NATIVE_MODEL_REGISTRY=1 transaction branch)
endif
$(OBJDIR)/coarse_actor.o $(OBJDIR)/coarse_ganado.o: GAME_CPPFLAGS += -DRE4DC_ACTOR_PROF=1
$(OBJDIR)/platform/native_actor_fast.o: PLATFORM_CPPFLAGS += -DRE4DC_ACTOR_PROF=1
endif

# ACTOR_PLAN=1 (render only, exact; default 0): the character draw plan (CPU-SAVINGS-PLAN step 2). The owned character
#   path keeps the proofs it already made and replays them instead of proving the same facts again, per call and per
#   frame (platform/include/actor_plan.h lists the reuses; docs/lanes/actorplan17.md has the audit of each). Every
#   reuse is keyed on what its proof read: the transaction call, the lifetime serial (every adopt / retire / revoke /
#   forget / stream pending / binding refresh moves it), the binding revision and the live model / info / bone state,
#   which is still read every frame. Nothing about what is drawn changes: the same vertices, colours and TA words.
#   =2 (compare build): every original proof also runs and decides; "APLAN" lines count reuses whose verdict differed
#   (bad must stay 0). The runtime switch re4dc_actor_plan_on (1) turns every reuse off for the benchmark disc's A/B
#   (BENCH_LEVERS lever "noplan").
ACTOR_PLAN ?= 0
ifeq ($(filter $(ACTOR_PLAN),0 1 2),)
$(error ACTOR_PLAN must be 0, 1 or 2)
endif
ifneq ($(ACTOR_PLAN),0)
ifneq ($(ACTOR_TRANSACTION)$(COARSE_ONE_SUBMIT)$(ACTOR_PROOF_LEAN)$(ACTOR_BIND_REUSE)$(ACTOR_MATERIAL_RECORD)$(NATIVE_MODEL_REGISTRY),111111)
$(error ACTOR_PLAN needs ACTOR_TRANSACTION=1 COARSE_ONE_SUBMIT=1 ACTOR_PROOF_LEAN=1 ACTOR_BIND_REUSE=1 ACTOR_MATERIAL_RECORD=1 NATIVE_MODEL_REGISTRY=1)
endif
ifneq ($(filter-out 0,$(LEON_NATIVE_PIPE)),)
$(error ACTOR_PLAN and LEON_NATIVE_PIPE are separate experiments)
endif
$(OBJDIR)/coarse_actor.o $(OBJDIR)/coarse_ganado.o $(OBJDIR)/dbgwarp_bridge.o: GAME_CPPFLAGS += -DRE4DC_ACTOR_PLAN=$(ACTOR_PLAN)
$(OBJDIR)/platform/native_actor_fast.o: PLATFORM_CPPFLAGS += -DRE4DC_ACTOR_PLAN=$(ACTOR_PLAN)
endif
# ACTOR_PLAN_AB=1 (BENCHMARK=1 console A/B disc only): four scenes on the start screen's menu (bench.cpp
#   RE4DC_BENCH_SCENES): the r101 cross with the plan off / on, the r103 farm with the plan off / on (each scene's
#   `actorplan 0|1` warp line; one program image, so both arms share one code layout).
ACTOR_PLAN_AB ?= 0
ifeq ($(ACTOR_PLAN_AB),1)
ifneq ($(BENCHMARK)$(filter-out 0,$(ACTOR_PLAN)),11)
$(error ACTOR_PLAN_AB needs BENCHMARK=1 and ACTOR_PLAN=1)
endif
$(OBJDIR)/bench.o: PLATFORM_CPPFLAGS += -DRE4DC_BENCH_SCENES=4 '-DRE4DC_BENCH_NAME="ACTOR PLAN A/B"' '-DRE4DC_BENCH_MENU="X: CROSS OFF  Y: CROSS ON  B: FARM OFF"'
endif
