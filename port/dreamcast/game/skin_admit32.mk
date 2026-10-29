# Build32 review5: claim a skin-registry slot before source palette allocation.
# Default 0 adds no flags, data or input selection. The enabled profile keeps
# the allocation-to-commit path non-yielding (SKIN_PALETTE_LAZY=1).
SKIN_ADMISSION32 ?= 0
ifneq ($(words $(SKIN_ADMISSION32)),1)
$(error SKIN_ADMISSION32 must be 0 or 1)
endif
ifeq ($(filter $(SKIN_ADMISSION32),0 1),)
$(error SKIN_ADMISSION32 must be 0 or 1)
endif
ifeq ($(SKIN_ADMISSION32),1)
ifneq ($(ACTOR_TRANSACTION)$(NATIVE_ACTOR_FAST)$(NATIVE_ACTOR_SKIN_LAZY)$(SKIN_PALETTE_LAZY),1111)
$(error SKIN_ADMISSION32 requires ACTOR_TRANSACTION=1 NATIVE_ACTOR_FAST=1 NATIVE_ACTOR_SKIN_LAZY=1 SKIN_PALETTE_LAZY=1)
endif
$(OBJDIR)/src/game/trans.o: GAME_CPPFLAGS += -DRE4DC_SKIN_ADMISSION32=1
$(OBJDIR)/platform/native_actor_fast.o: PLATFORM_CPPFLAGS += -DRE4DC_SKIN_ADMISSION32=1
$(OBJDIR)/platform/native_actor_fast.o: platform/include/native_actor_skin_admit32.inc
endif
