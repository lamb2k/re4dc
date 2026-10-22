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
ACTOR_VISIBILITY23_SDK ?= $(CURDIR)/.actor-visibility23-sdk
$(OBJDIR)/platform/native_actor_fast.o $(OBJDIR)/platform/actor_visibility23.o: PLATFORM_CPPFLAGS += -DRE4DC_ACTOR_VISIBILITY23=1 -I$(ACTOR_VISIBILITY23_SDK)/include
$(OBJDIR)/coarse_ganado.o: GAME_CPPFLAGS += -DRE4DC_ACTOR_VISIBILITY23=1
$(OBJDIR)/platform/actor_visibility23.o: PLATFORM_CPPFLAGS += -O2 -fno-fast-math -ffp-contract=off
OBJS += $(OBJDIR)/platform/actor_visibility23.o $(OBJDIR)/shz_bounds23.o
$(TARGET): $(OBJDIR)/platform/actor_visibility23.o $(OBJDIR)/shz_bounds23.o
$(OBJDIR)/platform/actor_visibility23.o: platform/actor_visibility23.cc platform/include/actor_visibility23.h $(ACTOR_VISIBILITY23_SDK)/include/sh4zam/shz_bounds.h
	@mkdir -p $(dir $@)
	kos-c++ $(KOS_CFLAGS) $(PLATFORM_CPPFLAGS) -MMD -MP -c $< -o $@
$(OBJDIR)/shz_bounds23.o: $(ACTOR_VISIBILITY23_SDK)/source/shz_bounds.c $(ACTOR_VISIBILITY23_SDK)/include/sh4zam/shz_bounds.h
	@mkdir -p $(dir $@)
	kos-cc $(KOS_CFLAGS) -O2 -fno-fast-math -ffp-contract=off -I$(ACTOR_VISIBILITY23_SDK)/include -c $< -o $@
endif
