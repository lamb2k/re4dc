# Build 26: independent diagnostics and two near-plane fallback candidates.
# Absent/0 adds no source defines or linked objects; no recipe is enabled.
DRAW_FALLBACK_AUDIT ?= 0
ACTOR_CLIP_FRONT26 ?= 0
SCENERY_CLIP_INDEXED26 ?= 0
$(foreach k,DRAW_FALLBACK_AUDIT ACTOR_CLIP_FRONT26 SCENERY_CLIP_INDEXED26,$(if $(filter 1,$(words $($(k)))),$(if $(filter-out 0 1,$($(k))),$(error $(k) must be 0 or 1)),$(error $(k) must be one value, 0 or 1)))

ifeq ($(DRAW_FALLBACK_AUDIT),1)
ifneq ($(QA_MENU),1)
$(error DRAW_FALLBACK_AUDIT=1 needs QA_MENU=1)
endif
DFA26_GAME_OBJS = $(OBJDIR)/src/game/main.o $(OBJDIR)/src/game/esp_sub.o $(OBJDIR)/model_bridge.o
DFA26_PLATFORM_OBJS = $(OBJDIR)/platform/native_static.o $(OBJDIR)/platform/native_ps2_world.o $(OBJDIR)/platform/chunk_submit.o $(OBJDIR)/platform/native_actor_fast.o $(OBJDIR)/platform/native_model.o $(OBJDIR)/platform/native_ui.o $(OBJDIR)/qa_menu.o
$(DFA26_GAME_OBJS): GAME_CPPFLAGS += -DRE4DC_DRAW_FALLBACK_AUDIT=1
$(DFA26_PLATFORM_OBJS): PLATFORM_CPPFLAGS += -DRE4DC_DRAW_FALLBACK_AUDIT=1
PLATFORM_OBJS += $(OBJDIR)/draw_fallback_audit.o
$(TARGET): $(OBJDIR)/draw_fallback_audit.o
$(OBJDIR)/draw_fallback_audit.o: draw_fallback_audit.cpp $(wildcard platform/include/draw_fallback_*.def) platform/include/draw_fallback_audit.h
	@mkdir -p $(dir $@)
	kos-c++ $(KOS_CFLAGS) $(PLATFORM_CPPFLAGS) -DRE4DC_DRAW_FALLBACK_AUDIT=1 -MMD -MP -c $< -o $@
-include $(OBJDIR)/draw_fallback_audit.d
endif

ifeq ($(ACTOR_CLIP_FRONT26),1)
ifneq ($(NATIVE_ACTOR)$(NATIVE_ACTOR_FAST),11)
$(error ACTOR_CLIP_FRONT26=1 needs NATIVE_ACTOR=1 NATIVE_ACTOR_FAST=1)
endif
$(OBJDIR)/platform/native_actor_fast.o: PLATFORM_CPPFLAGS += -DRE4DC_ACTOR_CLIP_FRONT26=1
endif

ifeq ($(SCENERY_CLIP_INDEXED26),1)
ifneq ($(SCENERY_STREAM)$(SCENERY_CHUNK)$(MESH_FASTPATH)$(MESH_DIRECT)$(PS2_WORLD_MESH),11111)
$(error SCENERY_CLIP_INDEXED26=1 needs SCENERY_STREAM/SCENERY_CHUNK/MESH_FASTPATH/MESH_DIRECT/PS2_WORLD_MESH=1)
endif
ifneq ($(SCENERY_EMIT_PREFETCH),0)
$(error SCENERY_CLIP_INDEXED26=1 needs SCENERY_EMIT_PREFETCH=0)
endif
ifeq ($(CPU_BACKFACE),1)
$(error SCENERY_CLIP_INDEXED26=1 does not support CPU_BACKFACE=1)
endif
ifeq ($(SCENERY_DEDUP),3)
$(error SCENERY_CLIP_INDEXED26=1 does not support SCENERY_DEDUP=3)
endif
$(OBJDIR)/platform/native_static.o: PLATFORM_CPPFLAGS += -DRE4DC_SCENERY_CLIP_INDEXED26=1
endif
