# Build32 demand-selected source palette for existing shared-table nominees.
# The default emits no flag. The consumed profile owns primitive retirement and
# uses the one-ticket, non-yielding LAZY1 admission path.
SKIN_RECIPE32 ?= 0
ifneq ($(SKIN_RECIPE32),0)
ifneq ($(SKIN_RECIPE32),1)
$(error SKIN_RECIPE32 must be 0 or 1)
endif
endif
ifeq ($(SKIN_RECIPE32),1)
ifneq ($(SKIN_ADMISSION32)$(ACTOR_TRANSACTION)$(ACTOR_SKIN_RESERVE)$(NATIVE_ACTOR_FAST)$(NATIVE_ACTOR_SKIN_LAZY)$(SKIN_PALETTE_LAZY)$(COARSE_SOURCE_ACTORS),1111111)
$(error SKIN_RECIPE32 requires SKIN_ADMISSION32=1 ACTOR_TRANSACTION=1 ACTOR_SKIN_RESERVE=1 NATIVE_ACTOR_FAST=1 NATIVE_ACTOR_SKIN_LAZY=1 SKIN_PALETTE_LAZY=1 COARSE_SOURCE_ACTORS=1)
endif
ifneq ($(ACTOR_SKIN_OWNER_POOL),0)
$(error SKIN_RECIPE32 requires shared-table ACTOR_SKIN_OWNER_POOL=0)
endif
$(OBJDIR)/src/game/trans.o: GAME_CPPFLAGS += -DRE4DC_SKIN_RECIPE32=1
$(OBJDIR)/platform/native_actor_fast.o: PLATFORM_CPPFLAGS += -DRE4DC_SKIN_RECIPE32=1
$(OBJDIR)/coarse_actor.o: GAME_CPPFLAGS += -DRE4DC_SKIN_RECIPE32=1
$(OBJDIR)/platform/native_actor_fast.o: platform/include/native_actor_skin_recipe32.inc
endif
