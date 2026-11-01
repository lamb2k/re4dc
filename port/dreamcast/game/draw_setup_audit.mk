# Build 24: standalone diagnostics and two independent exact rendering fixes.
# Absent/0 adds no CPP flags, objects or changed release defaults.
DRAW_SETUP_AUDIT ?= 0
DRAW_SETUP_AUDIT_WINDOW ?= 300
ACTOR_CLIP_REUSE ?= 0
SCENERY_CLIP_GATHER ?= 0
# DRAW_SETUP_AUDIT_XLU=1 (lane xlu28, 2026-10-28; diagnostics only, needs DRAW_SETUP_AUDIT=1): per path the on-screen
#   pixels of opaque / punch-through / translucent triangles (XA rows) and the top 8 models by work us with parts,
#   triangles, see-through triangles / pixels and light path (XM rows): QA Diagnostics page, link telemetry, RAM log.
# DRAW_SETUP_AUDIT_OCC=1 (needs _XLU=1): a 40x30 CPU depth grid of the opaque triangles; each see-through triangle is
#   tested at the tick's end against every cell of its box (XO rows: likely hidden triangles / pixels, own eval time).
# DRAW_SETUP_AUDIT_XLU_EVERY=N (1..16, default 8): areas and OCC run on one drawn tick in N (rows divide by the sampled
#   ticks), so the observer's cost is spread; model rows run every tick.
DRAW_SETUP_AUDIT_XLU ?= 0
DRAW_SETUP_AUDIT_OCC ?= 0
DRAW_SETUP_AUDIT_XLU_EVERY ?= 8
$(foreach k,DRAW_SETUP_AUDIT ACTOR_CLIP_REUSE SCENERY_CLIP_GATHER DRAW_SETUP_AUDIT_XLU DRAW_SETUP_AUDIT_OCC,$(if $(filter 1,$(words $($(k)))),$(if $(filter-out 0 1,$($(k))),$(error $(k) must be 0 or 1)),$(error $(k) must be one value, 0 or 1)))

ifeq ($(DRAW_SETUP_AUDIT),1)
ifneq ($(QA_MENU)$(WORLD_METER)$(PVR_STREAM),111)
$(error DRAW_SETUP_AUDIT=1 needs QA_MENU=1 WORLD_METER=1 PVR_STREAM=1)
endif
DSA24_GAME_OBJS = $(OBJDIR)/src/game/main.o $(OBJDIR)/src/game/trans.o
DSA24_PLATFORM_OBJS = $(OBJDIR)/platform/native_static.o $(OBJDIR)/platform/native_ps2_world.o $(OBJDIR)/platform/native_actor_fast.o $(OBJDIR)/platform/native_ui.o $(OBJDIR)/platform/native_model.o $(OBJDIR)/qa_menu.o
$(DSA24_GAME_OBJS): GAME_CPPFLAGS += -DRE4DC_DRAW_SETUP_AUDIT=1
$(DSA24_PLATFORM_OBJS): PLATFORM_CPPFLAGS += -DRE4DC_DRAW_SETUP_AUDIT=1
$(OBJDIR)/perf_phase_miss.o: PLATFORM_CPPFLAGS += -DRE4DC_DRAW_SETUP_AUDIT=1
PLATFORM_OBJS += $(OBJDIR)/draw_setup_audit.o
$(TARGET): $(OBJDIR)/draw_setup_audit.o
$(OBJDIR)/draw_setup_audit.o: draw_setup_audit.cpp platform/include/draw_setup_audit.h
	@mkdir -p $(dir $@)
	kos-c++ $(KOS_CFLAGS) $(PLATFORM_CPPFLAGS) -DRE4DC_DRAW_SETUP_AUDIT=1 -DRE4DC_DRAW_SETUP_AUDIT_WINDOW=$(DRAW_SETUP_AUDIT_WINDOW) $(if $(filter 1,$(PERF_PHASE_MISS)),-DRE4DC_PERF_PHASE_MISS=1) -MMD -MP -c $< -o $@
-include $(OBJDIR)/draw_setup_audit.d
ifeq ($(DRAW_SETUP_AUDIT_XLU),1)
DSA28_FLAGS = -DRE4DC_DSA_XLU28=1 -DRE4DC_DSA_XLU28_EVERY=$(DRAW_SETUP_AUDIT_XLU_EVERY) $(if $(filter 1,$(DRAW_SETUP_AUDIT_OCC)),-DRE4DC_DSA_OCC28=1)
$(DSA24_GAME_OBJS) $(OBJDIR)/model_bridge.o: GAME_CPPFLAGS += $(DSA28_FLAGS)
$(DSA24_PLATFORM_OBJS) $(OBJDIR)/perf_phase_miss.o $(OBJDIR)/draw_setup_audit.o: PLATFORM_CPPFLAGS += $(DSA28_FLAGS)
else ifeq ($(DRAW_SETUP_AUDIT_OCC),1)
$(error DRAW_SETUP_AUDIT_OCC=1 needs DRAW_SETUP_AUDIT_XLU=1)
endif
else ifneq ($(DRAW_SETUP_AUDIT_XLU)$(DRAW_SETUP_AUDIT_OCC),00)
$(error DRAW_SETUP_AUDIT_XLU and DRAW_SETUP_AUDIT_OCC need DRAW_SETUP_AUDIT=1)
endif

ifeq ($(ACTOR_CLIP_REUSE),1)
$(OBJDIR)/platform/native_actor_fast.o: PLATFORM_CPPFLAGS += -DRE4DC_ACTOR_CLIP_REUSE=1
endif

ifeq ($(SCENERY_CLIP_GATHER),1)
ifneq ($(SCENERY_STREAM)$(SCENERY_CHUNK)$(MESH_DIRECT)$(PS2_WORLD_MESH),1111)
$(error SCENERY_CLIP_GATHER=1 needs SCENERY_STREAM=1 SCENERY_CHUNK=1 MESH_DIRECT=1 PS2_WORLD_MESH=1)
endif
ifneq ($(SCENERY_EMIT_PREFETCH),0)
$(error SCENERY_CLIP_GATHER=1 requires SCENERY_EMIT_PREFETCH=0)
endif
ifeq ($(CPU_BACKFACE),1)
$(error SCENERY_CLIP_GATHER=1 does not support CPU_BACKFACE=1)
endif
ifeq ($(SCENERY_DEDUP),3)
$(error SCENERY_CLIP_GATHER=1 does not support SCENERY_DEDUP=3)
endif
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_SCENERY_CLIP_GATHER=1
endif
