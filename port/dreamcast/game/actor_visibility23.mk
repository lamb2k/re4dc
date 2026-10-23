# Actor section world-wall experiment; default0 adds no code/data/objects.
ACTOR_VISIBILITY23 ?= 0
ifneq ($(ACTOR_VISIBILITY23),0)
ifneq ($(ACTOR_VISIBILITY23),1)
$(error ACTOR_VISIBILITY23 must be 0 or 1; runtime mode boots0)
endif
ifneq ($(ACTOR_TRANSACTION)$(ENEMY_VIS_CULL),11)
$(error ACTOR_VISIBILITY23 needs ACTOR_TRANSACTION=1 ENEMY_VIS_CULL=1)
endif
ifeq ($(filter 1 2 3,$(PS2_INTERIOR_CULL)),)
$(error ACTOR_VISIBILITY23 requires existing PS2_INTERIOR_CULL=1/2/3 bridge)
endif
ifneq ($(PS2_INTERIOR_ACTORS)$(CROWD_INVIS_SKIP)$(COARSE_GANADO_CAST),211)
$(error ACTOR_VISIBILITY23 requires PS2_INTERIOR_ACTORS=2 CROWD_INVIS_SKIP=1 COARSE_GANADO_CAST=1)
endif
ifneq ($(PS2_WORLD_DYNAMIC)$(PS2_WORLD_PARTS),11)
$(error ACTOR_VISIBILITY23 requires PS2_WORLD_DYNAMIC=1 PS2_WORLD_PARTS=1 for live occluder state)
endif
ifneq ($(filter-out 0,$(MIST_CUT) $(TRANS_POLICY_DEBUG)),)
$(error Actor occluder admission excludes MIST_CUT and TRANS_POLICY_DEBUG)
endif
ifneq ($(DBG_WARP),1)
$(error ACTOR_VISIBILITY23 requires DBG_WARP=1 for its bounded private fixture control)
endif
ifneq ($(filter-out 0,$(WORLD_SCRATCH)),)
$(error Actor visibility and world scratch experiments require separate programmes)
endif
ifneq ($(MESH_FASTPATH)$(HW_LEAN)$(MESH_VP_SCHED)$(WORLD_RECT21),1111)
$(error ACTOR_VISIBILITY23 receipt requires MESH_FASTPATH=1 HW_LEAN=1 MESH_VP_SCHED=1 WORLD_RECT21=1)
endif
ifneq ($(filter-out 0,$(CPU_BACKFACE)),)
$(error Actor cottage receipt currently requires CPU_BACKFACE=0)
endif
ACTOR_VISIBILITY23_CERT ?=
ifeq ($(ACTOR_VISIBILITY23_CERT),)
$(error ACTOR_VISIBILITY23_CERT must name the private prepare_r119.py certificate directory)
endif
ACTOR_VISIBILITY23_SDK ?= $(CURDIR)/.actor-visibility23-sdk
$(OBJDIR)/platform/native_actor_fast.o $(OBJDIR)/platform/actor_visibility23.o $(OBJDIR)/platform/native_static.o $(OBJDIR)/platform/native_ui.o: PLATFORM_CPPFLAGS += -DRE4DC_ACTOR_VISIBILITY23=1 -I$(ACTOR_VISIBILITY23_SDK)/include -I$(ACTOR_VISIBILITY23_CERT)
$(OBJDIR)/coarse_ganado.o: GAME_CPPFLAGS += -DRE4DC_ACTOR_VISIBILITY23=1 -I$(ACTOR_VISIBILITY23_SDK)/include
$(OBJDIR)/platform/actor_visibility23.o: PLATFORM_CPPFLAGS += -DRE4DC_DBG_WARP=1 -O2 -fno-fast-math -ffp-contract=off
OBJS += $(OBJDIR)/platform/actor_visibility23.o $(OBJDIR)/shz_bounds23.o
$(TARGET): $(OBJDIR)/platform/actor_visibility23.o $(OBJDIR)/shz_bounds23.o
$(OBJDIR)/platform/actor_visibility23.o: platform/actor_visibility23.cc platform/include/actor_visibility23.h platform/include/actor_visibility23_window.h $(ACTOR_VISIBILITY23_SDK)/include/sh4zam/shz_bounds.h
	@mkdir -p $(dir $@)
	kos-c++ $(KOS_CFLAGS) $(PLATFORM_CPPFLAGS) -MMD -MP -c $< -o $@
$(OBJDIR)/platform/native_static.o: platform/include/actor_visibility23_world.h $(ACTOR_VISIBILITY23_CERT)/actor_visibility23_r119_certificate.h
$(OBJDIR)/shz_bounds23.o: $(ACTOR_VISIBILITY23_SDK)/source/shz_bounds.c $(ACTOR_VISIBILITY23_SDK)/include/sh4zam/shz_bounds.h
	@mkdir -p $(dir $@)
	kos-cc $(KOS_CFLAGS) -O2 -fno-fast-math -ffp-contract=off -I$(ACTOR_VISIBILITY23_SDK)/include -c $< -o $@
endif
