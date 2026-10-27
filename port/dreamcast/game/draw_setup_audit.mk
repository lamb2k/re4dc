# Build 24: standalone diagnostics and two independent exact rendering fixes.
# Absent/0 adds no CPP flags, objects or changed release defaults.
DRAW_SETUP_AUDIT ?= 0
DRAW_SETUP_AUDIT_WINDOW ?= 300
ACTOR_CLIP_REUSE ?= 0
SCENERY_CLIP_GATHER ?= 0
$(foreach k,DRAW_SETUP_AUDIT ACTOR_CLIP_REUSE SCENERY_CLIP_GATHER,$(if $(filter 1,$(words $($(k)))),$(if $(filter-out 0 1,$($(k))),$(error $(k) must be 0 or 1)),$(error $(k) must be one value, 0 or 1)))

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
